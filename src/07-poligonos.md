# Polígonos: regiões e o que cai dentro delas

## Por que isso importa

Até agora o projeto `pontos` responde perguntas sobre **pontos**: o que
está perto, o que está na tela. Mas boa parte das perguntas de verdade é
sobre **regiões**. Uma loja de delivery quer saber se o endereço do cliente
está dentro da zona de entrega. Uma prefeitura quer saber quantas
ocorrências caíram em cada bairro. Um app de transporte quer saber em qual
área de cobertura o carro está agora. Em todos esses casos existe um
polígono desenhado no mapa, e a pergunta é sempre uma destas três:

1. **Dado um ponto, em qual região ele cai?** ("Entrego aí?")
2. **Dada uma região, quais pontos estão dentro, e quantos?** ("Quantos
   clientes tenho neste bairro?")
3. **Duas regiões se cruzam?** ("Minha zona de entrega invade a do outro
   restaurante?")

O model `Bairro` do capítulo anterior já tem um `PolygonField`. O que falta
é saber **criar** polígonos sem sofrer (de vários jeitos, inclusive com um
formulário com mapa na sua própria aplicação, não só no admin) e fazer o
PostGIS responder as três perguntas. É isso que este capítulo faz. No fim,
o mapa do capítulo anterior ganha duas coisas: cada bairro fica colorido
pelo número de lugares que tem, e clicar em qualquer ponto responde "você
está em tal bairro".

O ponto de partida é o projeto como ficou no fim do capítulo de GeoJSON:
cinco lugares, o bairro "Centro" e a página `lugares/mapa/`. Ao longo do
capítulo entram dois bairros, "Paraíso" e "Moema", desenhados de propósito
para que um invada o Centro e o outro só encoste no Paraíso. A figura abaixo
mostra tudo isso junto e em escala; volte a ela sempre que um resultado
impresso parecer estranho.

![Os dados do capítulo, em São Paulo: três lugares, três bairros, o pedaço
em que Centro e Paraíso se sobrepõem, um círculo de 500 m em volta do Café
da Esquina e um ponto exatamente sobre a borda do Centro. Café do Rio e
Parque da Cidade ficam a centenas de quilômetros, fora do
mapa.](assets/figuras/dados-capitulo.svg){width=88%}

## Anatomia de um polígono

Antes de criar polígonos, vale entender o que o GEOS e o PostGIS exigem de
um. As regras são poucas, mas quando uma delas é quebrada o erro é
críptico.

- Um polígono é feito de **anéis**. O primeiro é a **borda externa**; os
  seguintes, se existirem, são **buracos** (uma praça que não faz parte do
  bairro, um lago dentro de um parque).
- Todo anel é **fechado**: o último ponto repete o primeiro. Um retângulo
  tem, portanto, cinco pontos, e um anel precisa de no mínimo quatro.
- Os anéis **não podem se cruzar**, nem a si mesmos nem uns aos outros. Um
  anel que se cruza forma uma "gravata borboleta", e o resultado é um
  polígono **inválido**: o banco aceita gravá-lo sem reclamar, mas a área
  sai errada (no exemplo abaixo, zero, porque os dois triângulos se
  cancelam) e várias funções passam a devolver bobagem.
- Um lugar feito de **vários pedaços separados** (um município com ilhas)
  não é um `Polygon`: é um `MultiPolygon`, e precisa de um
  `MultiPolygonField`.
- O sentido do anel (horário ou anti-horário) **não importa** para o
  PostGIS. O GeoJSON recomenda anti-horário para a borda externa, mas pede
  que os leitores aceitem os dois.

A figura mostra as três situações que o shell vai confirmar em seguida: um
polígono com buraco, a gravata borboleta e os mesmos quatro cantos na ordem
certa.

![(a) Um polígono com dois anéis: o de fora é a borda, o de dentro é um
buraco, e um ponto dentro do buraco está fora do polígono. (b) Os cantos
(0, 0), (1, 1), (1, 0) e (0, 1), nessa ordem: as duas diagonais se cruzam em
(0.5, 0.5) e o polígono é inválido, com área zero; `make_valid()` o separa
nos dois triângulos coloridos. (c) Os mesmos cantos visitados em volta,
(0, 0), (1, 0), (1, 1), (0, 1): um quadrado válido de área
1.](assets/figuras/anatomia-poligono.svg){width=100%}

Vamos conferir isso no shell com o bairro que já existe:

```bash
uv run python manage.py shell
```

```python
centro = Bairro.objects.get(nome="Centro")
centro.area.geom_type            # 'Polygon'
centro.area.num_points           # 5  (quatro cantos + o fechamento)
len(centro.area)                 # 1  (um anel: só a borda externa)
centro.area.num_interior_rings   # 0  (nenhum buraco)
centro.area.exterior_ring.wkt
# 'LINEARRING (-46.665 -23.57, -46.62 -23.57, -46.62 -23.53, -46.665 -23.53, -46.665 -23.57)'
centro.area.valid                # True
```

Agora um polígono com buraco. Os anéis vão como argumentos separados: o
primeiro é a borda, os seguintes são buracos:

```python
from django.contrib.gis.geos import Point, Polygon

borda = ((-46.665, -23.570), (-46.620, -23.570), (-46.620, -23.530),
         (-46.665, -23.530), (-46.665, -23.570))
praca = ((-46.640, -23.555), (-46.630, -23.555), (-46.630, -23.545),
         (-46.640, -23.545), (-46.640, -23.555))
com_buraco = Polygon(borda, praca, srid=4326)
com_buraco.num_interior_rings    # 1
com_buraco.contains(Point(-46.635, -23.550, srid=4326))   # False: cai no buraco
```

E a gravata borboleta, o erro clássico de quem desenha os cantos na ordem
errada (repare que os pontos vão de `(0, 0)` a `(1, 1)`, depois a `(1, 0)`
e a `(0, 1)`: as duas diagonais se cruzam no meio):

```python
gravata = Polygon(((0, 0), (1, 1), (1, 0), (0, 1), (0, 0)), srid=4326)
gravata.valid           # False
gravata.valid_reason    # 'Self-intersection[0.5 0.5]'
gravata.area            # 0.0  (os dois triângulos se cancelam)
consertada = gravata.make_valid()
consertada.geom_type    # 'MultiPolygon'
consertada.num_geom     # 2  (virou dois triângulos)
```

(O GEOS imprime uma linha `GEOS_NOTICE: Self-intersection at or near point
0.5 0.5` junto; é só um aviso.) `make_valid()` conserta o polígono sem
perder nenhum vértice, mas repare no resultado: um `MultiPolygon`, que não
cabe num `PolygonField`. Vale mais a pena desenhar certo. Por fim, um anel
com poucos pontos nem chega a existir:

```python
Polygon(((0, 0), (1, 1), (1, 0)), srid=4326)
# ValueError: LinearRing requires at least 4 points, got 3.
```

## Quatro jeitos de criar um polígono

Desenhar polígono por polígono digitando coordenadas não escala. Na
prática você vai usar uma destas formas, dependendo de onde o polígono
vem. Ao longo desta seção criamos dois bairros novos, que as
consultas mais adiante usam.

### 1. Desenhando no admin

O `GISModelAdmin` do capítulo de GeoDjango já faz isso. Abra "Adicionar
bairro" no admin: cada clique no mapa coloca um canto, e **clicar de novo
no primeiro canto** (ou no último) fecha o anel. Depois de fechado, dá para
arrastar um canto para ajustar, arrastar o meio de um lado para criar um
canto novo e apagar um canto com Shift+clique. O link "Deletar todas os
elementos" abaixo do mapa (a tradução do Django é assim mesmo; em inglês,
"Delete all Features") apaga tudo para recomeçar. Um `PolygonField`
aceita um polígono só; depois de fechar o primeiro, o mapa não deixa
desenhar outro.

É o jeito certo quando quem desenha é **você**, olhando o mapa. O
formulário da próxima seção é o mesmo mapa, só que na sua aplicação.

### 2. Um retângulo com `from_bbox`

Para uma área aproximada, um retângulo basta, e `Polygon.from_bbox`
monta um a partir de `(xmin, ymin, xmax, ymax)`, isto é, (oeste, sul,
leste, norte). Você já usou isso no filtro por bbox do capítulo anterior.
Crie um bairro ao sul do Centro, que **invade** parte dele de propósito:

```python
paraiso = Polygon.from_bbox((-46.670, -23.600, -46.640, -23.555))
paraiso.srid          # None
paraiso.srid = 4326
paraiso.wkt
# 'POLYGON ((-46.67 -23.6, -46.67 -23.555, -46.64 -23.555, -46.64 -23.6, -46.67 -23.6))'
Bairro.objects.create(nome="Paraíso", area=paraiso)
```

A pegadinha é a segunda linha: `from_bbox` devolve um polígono **sem
SRID**. Nos filtros (`__within`, `__intersects`) o Django deixa passar,
assumindo em silêncio o SRID do campo, e o `create` também grava sem
reclamar. Mas `transform()` falha com "Calling transform() with no SRID
set is not supported", e funções do banco como `Distance` reclamam com
"SRID is required for all geometries". Atribua `srid = 4326` logo depois
de criar e esqueça o problema.

### 3. Um círculo em volta de um ponto: `buffer` em metros

"Tudo a até 500 m do café" é um círculo, e um círculo também é um polígono
(com muitos lados). O método `buffer(distancia)` cria esse polígono. O
problema é a unidade: o `buffer` trabalha nas unidades da geometria, e no
SRID 4326 a unidade é o **grau**. Veja o estrago:

```python
cafe = Lugar.objects.get(nome="Café da Esquina")
errado = cafe.localizacao.buffer(500)
errado.extent
# (-546.6333, -523.5505, 453.3667, 476.4495)
```

Quinhentos **graus** para cada lado: um "círculo" maior que o planeta. A
solução é converter o ponto para um sistema de coordenadas em **metros**,
fazer o buffer lá e converter de volta. Para o Brasil, o sistema certo é o
SIRGAS 2000 em UTM; São Paulo, Rio e Brasília caem na zona 23S, que é o
SRID **31983**:

```python
raio = cafe.localizacao.transform(31983, clone=True)   # uma cópia, em metros
raio.srid, f"{raio.x:.0f} {raio.y:.0f}"
# (31983, '333288 7394588')
raio = raio.buffer(500)                                # agora sim: 500 metros
raio.num_points                                        # 33 pontos: 32 lados + o fechamento
raio.transform(4326)                                   # de volta para graus, no lugar
[round(v, 4) for v in raio.extent]
# [-46.6382, -23.555, -46.6284, -23.546]
```

Vamos por partes.

- `transform(31983, clone=True)` converte as coordenadas para a zona UTM
  e devolve uma **cópia**; sem `clone=True`, ele altera a geometria no
  lugar e devolve `None`. Nas coordenadas UTM, `x` e `y` são metros.
- `buffer(500)` agora significa 500 metros. O resultado é um polígono de
  32 lados mais o fechamento, que no mapa parece um círculo.
- `transform(4326)` sem `clone` muda o `raio` no lugar, de volta para
  graus. Repare no `extent`: cerca de 0,01 grau de largura, que nessa
  latitude são mesmo uns 1000 metros.

Vale uma pausa no número 31983, porque ele volta em todo projeto
geográfico feito no Brasil. A Terra é curva, e para medir com régua é
preciso **projetá-la** num plano. Projetar o planeta inteiro de uma vez
deforma demais (é o que faz o mapa-múndi em que a Groenlândia parece maior
que a América do Sul). O **UTM** (*Universal Transverse Mercator*) resolve
isso cortando o globo em **60 fusos** (também chamados de zonas) de 6 graus
de longitude cada, numerados de 1 a 60 a partir do antimeridiano, e
projetando cada fuso separadamente. Dentro do seu fuso a deformação fica
abaixo de 0,1%: 1000 m no mapa são 1000 m no chão, com erro de menos de
1 m. O fuso 23 vai de 48°W a 42°W, com o meridiano central em 45°W; o
**S** indica a metade sul do fuso, no hemisfério sul, que tem uma contagem
própria para o `y`.

Os números que o `transform` imprimiu contam essa história. O `x`
(*easting*) mede metros a partir de uma linha imaginária 500 km a oeste do
meridiano central: 333 288 significa que o café está uns 167 km a oeste de
45°W. O `y` (*northing*) no hemisfério sul conta a partir de 10 000 km ao
sul do equador, para nunca ficar negativo: 7 394 588 significa que o café
está 2605 km ao sul do equador. Esses 500 km e 10 000 km são convenções,
chamadas de *falso leste* e *falso norte*.

Falta o **datum**: o modelo da forma da Terra e o ponto de amarração que
dizem onde o "zero" fica de fato. O oficial do Brasil, definido pelo IBGE,
é o **SIRGAS 2000**; na prática ele coincide com o WGS 84 do GPS a menos
de 1 m. Fuso, hemisfério e datum juntos formam um sistema de coordenadas,
e cada combinação ganha um número no registro EPSG, que é o SRID. O Brasil
ocupa os fusos 18 a 25:

| Fuso | Longitudes   | SRID (SIRGAS 2000) | Exemplos                                |
|:-----|:-------------|:-------------------|:----------------------------------------|
| 18S  | 78°W a 72°W  | 31978              | Cruzeiro do Sul                         |
| 19S  | 72°W a 66°W  | 31979              | Rio Branco                              |
| 20S  | 66°W a 60°W  | 31980              | Manaus, Porto Velho                     |
| 21S  | 60°W a 54°W  | 31981              | Cuiabá, Campo Grande                    |
| 22S  | 54°W a 48°W  | 31982              | Curitiba, Porto Alegre, Belém, Goiânia  |
| 23S  | 48°W a 42°W  | 31983              | São Paulo, Rio, Brasília, Belo Horizonte |
| 24S  | 42°W a 36°W  | 31984              | Salvador, Fortaleza, Vitória            |
| 25S  | 36°W a 30°W  | 31985              | Recife, Natal, João Pessoa              |

(Ao norte do equador, em Roraima e no Amapá, a letra vira N e os SRIDs são
31974 a 31976.) Escolha o fuso da sua cidade; se os seus dados cruzarem a
fronteira de dois fusos, use o fuso em que está a maior parte deles. A
distorção cresce devagar fora do fuso, então para uma cidade na borda o
erro ainda é pequeno; para o país inteiro, ele deixa de ser. Para conferir
qualquer SRID, procure o número em <https://epsg.io>.

O polígono pronto serve em qualquer consulta, exatamente como o `sudeste`
do capítulo de GeoDjango:

```python
Lugar.objects.filter(localizacao__within=raio)
# <QuerySet [<Lugar: Café da Esquina>]>
Bairro.objects.filter(area__intersects=raio)
# <QuerySet [<Bairro: Centro>]>
```

O mesmo truque de "converter, medir, voltar" vale para calcular áreas e
perímetros, como veremos.

### 4. Colando GeoJSON do geojson.io

Quando o polígono já existe em algum lugar (um arquivo que alguém mandou,
um desenho feito no <https://geojson.io>), o caminho é `GEOSGeometry`, que
lê WKT e GeoJSON. Desenhe um polígono no geojson.io, copie só a parte
`geometry` e cole no shell. Aqui vai um ao sul do Paraíso, encostado nele
pela borda de cima:

```python
from django.contrib.gis.geos import GEOSGeometry

moema = GEOSGeometry('''{
  "type": "Polygon",
  "coordinates": [[
    [-46.670, -23.620], [-46.640, -23.620], [-46.640, -23.600],
    [-46.670, -23.600], [-46.670, -23.620]
  ]]
}''')
moema.srid         # 4326  (GeoJSON é sempre WGS 84, e o Django sabe disso)
moema.geom_type    # 'Polygon'
Bairro.objects.create(nome="Moema", area=moema)
Bairro.objects.all()
# <QuerySet [<Bairro: Centro>, <Bairro: Moema>, <Bairro: Paraíso>]>
```

Ao contrário do `from_bbox`, aqui o SRID já vem preenchido, porque a
especificação do GeoJSON fixa o WGS 84. Recarregue
<http://localhost:8000/lugares/mapa/> e veja os três retângulos: o
Paraíso cobre um pedaço do Centro, e o Moema encosta no Paraíso sem
invadi-lo. Essa geometria foi escolhida de propósito para as consultas da
seção seguinte.

## O jeito 1 na sua aplicação: um formulário com mapa

O admin é para quem administra. Se a pessoa que desenha as zonas de
entrega é a dona do restaurante, ela precisa de uma página **sua**, com o
mesmo mapa. A boa notícia: o mapa do admin não é do admin. Ele é um
**widget de formulário** do GeoDjango, e qualquer `ModelForm` de um model
com `PolygonField` ganha um. Em quatro arquivos, mais uma linha no
`settings.py`, a página fica pronta.

Primeiro o formulário, em `lugares/forms.py` (arquivo novo):

```python
from django.contrib.gis import forms

from .models import Bairro


class BairroForm(forms.ModelForm):
    class Meta:
        model = Bairro
        fields = ["nome", "area"]
        widgets = {
            "area": forms.OSMWidget(
                attrs={"default_lon": -46.64, "default_lat": -23.56, "default_zoom": 12}
            ),
        }
```

- `django.contrib.gis.forms` tem tudo o que `django.forms` tem, mais os
  campos e widgets geográficos. Um único `import` serve para o arquivo
  inteiro, como nos models.
- `ModelForm` é o formulário que o Django monta **a partir do model**: um
  campo de formulário para cada campo listado em `fields`, com os
  validadores que o model já tem. É o primeiro formulário do livro; até
  aqui só o admin escrevia no banco. Como o model tem um `PolygonField`,
  o campo `area` vira automaticamente um `forms.PolygonField`, que só
  aceita polígonos.
- O `widgets` troca o widget padrão pelo `OSMWidget`, o mapa do
  OpenStreetMap que o admin usa. Sem essa linha o formulário usa um mapa
  de satélite da NASA com pouco zoom, ruim para desenhar um bairro. Os
  `attrs` são os mesmos `gis_widget_kwargs` do admin: sem eles o mapa abre
  no leste da França.

Segundo, a view, em `lugares/views.py`. É o padrão clássico de
formulário no Django (ainda não tínhamos visto um), sem nenhuma novidade
geográfica:

```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import BairroForm


@login_required
def novo_bairro(request):
    if request.method == "POST":
        form = BairroForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("lugares:mapa")
    else:
        form = BairroForm()
    return render(request, "lugares/novo_bairro.html", {"form": form})
```

A mesma view atende duas visitas diferentes. Na primeira, o navegador
pede a página com `GET`: cai no `else`, cria um formulário vazio e o
`render` desenha o HTML. Quando a pessoa clica em "Salvar", o navegador
manda os campos de volta com `POST`: `BairroForm(request.POST)` carrega
o formulário com o que chegou, `is_valid()` roda os validadores (nome
preenchido, polígono de verdade) e `save()` grava o `Bairro`. Se algo
estiver errado, o `if` falha, e o fim da função renderiza o mesmo
formulário de novo, agora com as mensagens de erro ao lado dos campos. O
`redirect` no final é de propósito: depois de gravar, mandamos o
navegador para **outra** URL, e um F5 na página do mapa não cadastra o
bairro duas vezes.

E o `@login_required`? Uma página que **escreve** no banco não pode ser
aberta por qualquer visitante da internet: sem o decorador, qualquer um
que descobrisse a URL cadastraria bairros à vontade. Com ele, quem não
está logado é mandado para a página de login (a `LOGIN_URL` do
`settings.py`) e volta sozinho depois de entrar. O projeto ainda não tem
uma tela de login própria, então aproveitamos a do admin. Acrescente ao
fim de `config/settings.py`:

```python
LOGIN_URL = "/admin/login/"
```

Terceiro, a URL, em `lugares/urls.py`:

```python
    path("bairros/novo/", views.novo_bairro, name="novo_bairro"),
```

Quarto, o template `lugares/templates/lugares/novo_bairro.html`:

```html
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="referrer" content="strict-origin-when-cross-origin">
  <title>Novo bairro</title>
  {{ form.media }}
  <style>
    body { font-family: sans-serif; max-width: 760px; margin: 2rem auto; }
    /* Fora do admin, o tamanho do mapa é por nossa conta */
    .dj_map { width: 100%; height: 400px; }
    .dj_map_wrapper { float: none; }
  </style>
</head>
<body>
  <h1>Novo bairro</h1>
  <p>Clique no mapa para colocar os cantos; clique no primeiro canto para fechar.</p>
  <form method="post">
    {% csrf_token %}
    {{ form }}
    <button type="submit">Salvar</button>
    <a href="{% url 'lugares:mapa' %}">Ver o mapa</a>
  </form>
</body>
</html>
```

Abra <http://localhost:8000/lugares/bairros/novo/>. Se você não estiver
logado, a tela de login do admin aparece primeiro e, depois de entrar, a
página do formulário abre sozinha. Desenhe um bairro em volta do Parque
Ibirapuera, dê um nome (por exemplo "Teste") e salve. A página
redireciona para o mapa, e o bairro novo está lá.

Agora **apague esse bairro de teste** no admin (ou com
`Bairro.objects.filter(nome="Teste").delete()` no shell): todos os
resultados impressos daqui até o fim do capítulo assumem exatamente três
bairros, Centro, Paraíso e Moema. Se você fez o exercício 1 do capítulo
anterior e tem um bairro a mais, ele vai aparecer como uma linha extra em
cada lista; não é erro.

Três linhas desse template merecem explicação, porque sem elas o mapa
simplesmente não aparece:

**`{{ form.media }}`.** Um widget pode declarar os arquivos CSS e JS de
que precisa, e `form.media` junta os de todos os widgets do formulário.
Aqui ele imprime quatro tags: o CSS e o JS do OpenLayers (a biblioteca
de mapas que o widget usa) vindos de uma CDN, e dois arquivos do próprio
Django servidos em `/static/gis/...`. Esqueça essa linha e o campo `area`
vira um `<textarea>` escondido, sem mapa nenhum.

**`.dj_map { height: 400px }`.** O widget desenha o mapa numa `div` com a
classe `dj_map`. O tamanho dela vem de um CSS do **admin**, que a sua
página não carrega. É o mesmo "mapa de altura zero" do Leaflet no capítulo
anterior, só que mais difícil de perceber, porque o resto do formulário
aparece normalmente.

**`<meta name="referrer">`.** O mesmo motivo do capítulo anterior: sem
ela, os tiles do OpenStreetMap são bloqueados.

O `{% csrf_token %}` é obrigatório em todo formulário com `POST`: é um
carimbo secreto que prova que o envio partiu de uma página sua, e não de
um site malicioso que mandou o navegador da pessoa fazer o `POST`
escondido. Sem ele o Django responde 403.

Como o widget sabe que o campo é um polígono? Ele recebe do campo o
`geom_type` (`POLYGON`), desenha só polígonos e, ao salvar, escreve a
geometria no `<textarea>` escondido como GeoJSON. Do outro lado, o
`forms.PolygonField` valida o tipo: se por algum motivo chegar um ponto ou
uma linha, o formulário volta com o erro "Tipo geométrico inválido."; se o
anel não fechar, "Valor geométrico inválido.". O bairro só entra no banco
se for um polígono de verdade.

Um formulário merece um teste. Como não dá para clicar no mapa num
teste, mandamos a geometria em texto, no formato **EWKT**: um WKT com o
SRID na frente. O arquivo `lugares/tests.py` já tem o teste do comando de
importação do capítulo de Django; acrescente ao **fim** dele os imports
que faltam e a classe nova:

```python
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.urls import reverse

from .models import Bairro


class NovoBairroTests(TestCase):
    def setUp(self):
        # A página exige login; o cliente de testes entra sem senha
        usuaria = get_user_model().objects.create_user("ana")
        self.client.force_login(usuaria)

    def test_cria_bairro_por_post(self):
        resposta = self.client.post(
            reverse("lugares:novo_bairro"),
            {
                "nome": "Pinheiros",
                # EWKT: o SRID na frente evita que o widget assuma 3857
                "area": "SRID=4326;POLYGON((-46.70 -23.58, -46.67 -23.58, "
                        "-46.67 -23.55, -46.70 -23.55, -46.70 -23.58))",
            },
        )
        self.assertRedirects(resposta, reverse("lugares:mapa"))
        bairro = Bairro.objects.get(nome="Pinheiros")
        self.assertEqual(bairro.area.srid, 4326)
        self.assertTrue(bairro.area.contains(Point(-46.68, -23.56, srid=4326)))

    def test_rejeita_ponto(self):
        resposta = self.client.post(
            reverse("lugares:novo_bairro"),
            {"nome": "Errado", "area": "SRID=4326;POINT(-46.6 -23.5)"},
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("area", resposta.context["form"].errors)
        self.assertFalse(Bairro.objects.filter(nome="Errado").exists())

    def test_exige_login(self):
        self.client.logout()
        resposta = self.client.get(reverse("lugares:novo_bairro"))
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/admin/login/", resposta.url)
```

(`TestCase` já estava importado no topo do arquivo.) O `setUp` roda antes
de cada teste: cria uma usuária e a loga com `force_login`, que pula a
senha, porque o que queremos testar é o formulário, não o login. O
terceiro teste faz o caminho inverso: sai e confere que a página manda
para o login. Rode só a classe nova:

```bash
uv run python manage.py test lugares.tests.NovoBairroTests
# Ran 3 tests in ...
# OK
```

Por que só a classe nova? Porque `uv run python manage.py test` sem
argumentos roda também o `ImportarLugaresTests` do capítulo de Django, e
ele **quebrou** no capítulo de GeoDjango sem ninguém perceber: o comando
`importar_lugares` cria `Lugar` sem `localizacao`, e esse campo virou
obrigatório. O teste falha com `IntegrityError: null value in column
"localizacao"`. Não é o seu formulário que está errado. O conserto é no
comando (dê a ele um `Point` padrão, ou acrescente colunas `lon` e `lat`
ao CSV e monte o `Point` a partir delas); fica como tarefa no exercício 1.

O comentário sobre o `SRID=4326;` esconde uma pegadinha real. O mapa do
widget trabalha internamente no SRID **3857** (a projeção do Google Maps e
do OpenStreetMap, em metros), e o Django converte para 4326 ao salvar. Por
isso o widget **assume** que qualquer GeoJSON ou WKT sem SRID que chega
pelo formulário está em 3857. Se o seu teste mandar um GeoJSON em graus,
ele é lido como metros, "convertido" e vira um polígono microscópico perto
da costa da África. Com o SRID explícito no EWKT, o Django vê que já está
em 4326 e não converte nada. (O cliente de testes também não exige o token
CSRF, por isso o `post` funciona sem ele.)

## Consultas: pontos e regiões

Com três bairros e cinco lugares, dá para responder as duas primeiras
perguntas do capítulo. Abra o shell de novo.

### De um ponto para as regiões

"Em qual bairro fica o MASP?" é `area__contains=ponto`: os bairros cuja
área **contém** o ponto.

```python
from django.contrib.gis.geos import Point

masp = Point(-46.6558, -23.5614, srid=4326)
Bairro.objects.filter(area__contains=masp)
# <QuerySet [<Bairro: Centro>, <Bairro: Paraíso>]>
Bairro.objects.filter(area__contains=masp).count()
# 2
brasilia = Point(-47.8825, -15.7942, srid=4326)
Bairro.objects.filter(area__contains=brasilia)
# <QuerySet []>
```

Repare: o MASP está em **dois** bairros, porque o Paraíso invade o Centro.
Isso não é erro, é a realidade dos dados. Regiões podem se sobrepor (zonas
de entrega de restaurantes diferentes, por exemplo), e a resposta de "em
qual região?" é sempre uma **lista**, que pode ter zero, um ou vários
itens. Se no seu sistema um ponto só pode pertencer a uma região, é o seu
código que precisa garantir isso, não o banco.

Por baixo, o Django gera a função `ST_Contains` do PostGIS:

```python
print(Bairro.objects.filter(area__contains=masp).query)
# SELECT ... FROM "lugares_bairro"
#   WHERE ST_Contains("lugares_bairro"."area", ST_GeomFromEWKB(...))
#   ORDER BY "lugares_bairro"."nome" ASC
```

E aqui mora um detalhe que um dia vai morder você. Para o PostGIS, "conter"
exige que o ponto esteja no **interior**: um ponto exatamente **sobre a
borda** não é contido. Para incluir a borda existe `covers`:

```python
na_borda = Point(-46.665, -23.550, srid=4326)   # sobre o lado oeste do Centro
Bairro.objects.filter(area__contains=na_borda)
# <QuerySet []>
Bairro.objects.filter(area__covers=na_borda)
# <QuerySet [<Bairro: Centro>]>
```

Com coordenadas de GPS isso quase nunca acontece por acaso, mas acontece
sempre que os pontos foram **gerados** a partir das bordas: o centro de
uma quadra, um endereço geocodificado na esquina, o canto compartilhado de
dois lotes. A própria documentação do PostGIS recomenda `covers` para
evitar a surpresa. Neste capítulo usamos `contains` nas explicações, por
ser o nome que todo mundo conhece, e `covers` na API no fim, onde um
clique na borda merece resposta.

### De uma região para os pontos

A pergunta inversa é `localizacao__within=poligono`, que você já usou com
o retângulo do Sudeste. Agora com um bairro do banco:

```python
centro = Bairro.objects.get(nome="Centro")
Lugar.objects.filter(localizacao__within=centro.area)
# <QuerySet [<Lugar: Café da Esquina>, <Lugar: MASP>]>
Lugar.objects.filter(localizacao__within=centro.area).count()
# 2
Lugar.objects.filter(localizacao__within=centro.area, categoria__nome="Café")
# <QuerySet [<Lugar: Café da Esquina>]>
```

`within` é o espelho de `contains`: "A está dentro de B" é o mesmo que "B
contém A"; no SQL vira `ST_Within`. E, como todo lookup, ele se mistura
com os filtros comuns: cafés dentro do Centro, lugares abertos dentro do
Paraíso, e assim por diante. A versão que inclui a borda chama-se
`coveredby`.

Essa pergunta é tão comum que merece virar um método do model. Em
`lugares/models.py`, acrescente ao `Bairro`:

```python
    def lugares(self):
        """Os lugares cujo ponto cai dentro deste bairro."""
        return Lugar.objects.filter(localizacao__within=self.area)
```

`Lugar` está no mesmo arquivo, então pode ser usado direto. Depois de
salvar o `models.py`, saia do shell e abra de novo: o shell não enxerga
métodos acrescentados depois que ele subiu. E o uso fica legível:

```python
Bairro.objects.get(nome="Paraíso").lugares()
# <QuerySet [<Lugar: MASP>, <Lugar: Parque Ibirapuera>]>
```

### Quantos pontos em cada região

A primeira versão de "quantos lugares em cada bairro" é um laço:

```python
for bairro in Bairro.objects.all():
    print(bairro.nome, bairro.lugares().count())
# Centro 2
# Moema 0
# Paraíso 2
```

Funciona, e para dez bairros está ótimo. Mas é uma consulta por bairro,
o problema N+1 do capítulo de Django. Com mil bairros são mil consultas.
A versão em **uma consulta só** usa `Subquery` e `OuterRef`:

```python
from django.db.models import Count, IntegerField, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce

lugares_dentro = (
    Lugar.objects.filter(localizacao__within=OuterRef("area"))
    .order_by()
    .annotate(grupo=Value(1)).values("grupo")
    .annotate(total=Count("pk"))
    .values("total")
)
bairros = Bairro.objects.annotate(
    total=Coalesce(Subquery(lugares_dentro, output_field=IntegerField()), 0)
)
list(bairros.values_list("nome", "total"))
# [('Centro', 2), ('Moema', 0), ('Paraíso', 2)]
```

Vamos por partes, porque cada linha está ali por um motivo.

- `OuterRef("area")` é "o campo `area` do bairro da consulta de fora".
  Lookups espaciais aceitam isso do lado direito, como aceitam um
  polígono. Assim, `lugares_dentro` é "os lugares dentro **deste**
  bairro", para cada bairro.
- `.order_by()` vazio apaga o `ordering = ["nome"]` do `Meta` do `Lugar`.
  Dentro de uma subconsulta com agregação, a ordenação só atrapalha.
- `.annotate(grupo=Value(1)).values("grupo")` é o truque. Um
  `values(...)` seguido de `annotate(Count(...))` é o jeito de dizer ao
  ORM "agrupe por estas colunas e conte"; sem o `values`, o `Count` viraria
  uma anotação em **cada** `Lugar`, e a subconsulta devolveria uma linha
  por lugar. Quando existe uma `ForeignKey`, você agrupa por ela; entre
  `Lugar` e `Bairro` não há nenhuma, a relação é geométrica. Então
  agrupamos por uma constante: um grupo só, uma linha só. E, como agrupar
  por uma constante não separa nada, o Django nem escreve o `GROUP BY` no
  SQL final (confira abaixo).
- `.annotate(total=Count("pk"))` conta, e `.values("total")` deixa só essa
  coluna, porque uma subconsulta usada como valor tem que devolver uma
  coluna e uma linha.
- `Coalesce(..., 0)`: para um bairro sem lugares a subconsulta devolve
  `NULL`, e `Coalesce` troca por zero. Sem isso, Moema apareceria como
  `None`.

Imprima o SQL e veja que ficou simples:

```python
print(bairros.query)
# SELECT ..., COALESCE((SELECT COUNT("U0"."id") AS "total" FROM "lugares_lugar" "U0"
#   WHERE ST_Within("U0"."localizacao", "lugares_bairro"."area")), 0) AS "total"
# FROM "lugares_bairro" ORDER BY "lugares_bairro"."nome" ASC
```

Uma consulta, um `COUNT` correlacionado por bairro, e o índice GiST
trabalhando no `ST_Within`. Esse `bairros` é o que a API do fim do capítulo
vai usar. Se a pergunta for só "quais bairros têm **algum** lugar?", nem
contar é preciso:

```python
from django.db.models import Exists

Bairro.objects.filter(Exists(Lugar.objects.filter(localizacao__within=OuterRef("area"))))
# <QuerySet [<Bairro: Centro>, <Bairro: Paraíso>]>
```

## Consultas: regiões entre si

A terceira pergunta é sobre duas regiões. Aqui o vocabulário é mais rico,
porque duas áreas podem se relacionar de várias maneiras: uma dentro da
outra, invadindo-se, só encostadas, separadas. Nossos três bairros cobrem
os casos: o Paraíso invade o Centro, o Moema encosta no Paraíso, e o Moema
não toca o Centro.

```python
centro = Bairro.objects.get(nome="Centro")
paraiso = Bairro.objects.get(nome="Paraíso")

Bairro.objects.filter(area__intersects=centro.area)
# <QuerySet [<Bairro: Centro>, <Bairro: Paraíso>]>
Bairro.objects.filter(area__intersects=centro.area).exclude(pk=centro.pk)
# <QuerySet [<Bairro: Paraíso>]>
Bairro.objects.filter(area__overlaps=centro.area)
# <QuerySet [<Bairro: Paraíso>]>
Bairro.objects.filter(area__touches=paraiso.area)
# <QuerySet [<Bairro: Moema>]>
Bairro.objects.filter(area__disjoint=centro.area)
# <QuerySet [<Bairro: Moema>]>
Bairro.objects.filter(area__intersects=paraiso.area)
# <QuerySet [<Bairro: Centro>, <Bairro: Moema>, <Bairro: Paraíso>]>
```

- `intersects` é o mais amplo: **qualquer** ponto em comum, inclusive só
  um pedaço da borda. Por isso um bairro intersecta a si mesmo, e o Moema,
  que só encosta no Paraíso, aparece na última consulta.
- `overlaps` é "invade": os interiores se cruzam, mas nenhum contém o
  outro por inteiro. Encostar não conta, e estar totalmente dentro também
  não.
- `touches` é só a borda em comum, sem interior em comum.
- `disjoint` é nada em comum. Prefira `.exclude(area__intersects=...)`:
  dá o mesmo resultado e o PostGIS consegue usar o índice.

A tabela resume a semântica, com `A` sendo o campo e `B` a geometria
passada ao filtro:

| Lookup              | Lê-se como                                  | Borda conta?        |
|:--------------------|:--------------------------------------------|:--------------------|
| `A__contains=B`     | A contém B                                  | Não (B só na borda não é contido) |
| `A__within=B`       | A está dentro de B                          | Não                 |
| `A__covers=B`       | A cobre B (nenhum ponto de B fora de A)     | Sim                 |
| `A__coveredby=B`    | A está coberto por B                        | Sim                 |
| `A__intersects=B`   | A e B têm algum ponto em comum              | Sim                 |
| `A__overlaps=B`     | A e B se invadem, sem um conter o outro     | Só borda não basta  |
| `A__touches=B`      | A e B só se encostam pela borda             | Só a borda          |
| `A__disjoint=B`     | A e B não têm nada em comum                 | Borda em comum já não é disjoint |

### Medindo: a interseção e a armadilha da área

Saber que o Paraíso invade o Centro é bom; saber **quanto** é melhor. A
função `Intersection` devolve a geometria em comum, e `Area` mede. Mas
lembre do `buffer`: no 4326, medir é em graus. A função `Transform` faz no
banco o que `transform()` fez no Python:

```python
from django.contrib.gis.db.models.functions import Area, Intersection, Transform

vizinhos = Bairro.objects.filter(area__overlaps=centro.area).annotate(
    comum=Intersection("area", centro.area),
    comum_m2=Area(Transform(Intersection("area", centro.area), 31983)),
)
for b in vizinhos:
    print(b.nome, b.comum.wkt, f"{b.comum_m2.sq_km:.2f} km²")
# Paraíso POLYGON ((-46.64 -23.555, -46.64 -23.57, -46.665 -23.57, -46.665 -23.555, -46.64 -23.555)) 4.24 km²
```

`Area` devolve um objeto de medida parecido com o `D` das distâncias:
`.sq_m`, `.sq_km`, `.ha` convertem. Agora a armadilha, que vale um aviso
em negrito. **`Area("area")` direto num campo 4326 devolve graus
quadrados, mas rotulados como metros quadrados**:

```python
Bairro.objects.annotate(a=Area("area")).get(nome="Centro").a
# Area(sq_m=0.0018000000000000299)
```

O PostGIS calcula `ST_Area` nas unidades do SRID, que são graus, e o
Django embrulha o número como `sq_m` sem conferir. O resultado parece uma
medida e não é. Sempre projete antes de medir:

```python
for b in Bairro.objects.annotate(a=Area(Transform("area", 31983))).order_by("-a"):
    print(f"{b.nome}: {b.a.sq_km:.2f} km² ({b.a.ha:.0f} ha)")
# Centro: 20.35 km² (2035 ha)
# Paraíso: 15.26 km² (1526 ha)
# Moema: 6.78 km² (678 ha)
```

Vinte quilômetros quadrados para um retângulo de 4,6 km por 4,5 km: agora
sim. Para filtrar por área, o valor tem que ser um objeto de medida, o
`A` (de *Area*), irmão do `D`:

```python
from django.contrib.gis.measure import A

Bairro.objects.annotate(a=Area(Transform("area", 31983))).filter(a__gt=A(sq_km=10))
# <QuerySet [<Bairro: Centro>, <Bairro: Paraíso>]>
```

### Juntando, centralizando e medindo distâncias

Três funções que aparecem o tempo todo em relatórios e mapas. `Union`,
como **agregação**, junta todas as áreas em uma geometria só:

```python
from django.contrib.gis.db.models import Union

tudo = Bairro.objects.aggregate(Union("area"))["area__union"]
tudo.geom_type    # 'Polygon'  (os três se encostam, então viram um só)
Lugar.objects.exclude(localizacao__within=tudo)
# <QuerySet [<Lugar: Café do Rio>, <Lugar: Parque da Cidade>]>
```

"Quem está fora de qualquer bairro" numa linha. Se os bairros fossem
separados, `tudo` seria um `MultiPolygon`; o lookup funciona igual. (A
documentação avisa que `Union` é pesado; para milhares de polígonos,
`Collect` junta sem dissolver as bordas e é muito mais rápido.)

`Centroid` dá o **centro** de um polígono, um `Point`. Serve, por
exemplo, para saber onde colocar o rótulo do bairro no mapa. Existe como
propriedade no Python e como função no banco:

```python
from django.contrib.gis.db.models.functions import Centroid

centro.area.centroid.wkt
# 'POINT (-46.6425 -23.55)'
for b in Bairro.objects.annotate(c=Centroid("area")):
    print(f"{b.nome}: {b.c.x:.4f}, {b.c.y:.4f}")
# Centro: -46.6425, -23.5500
# Moema: -46.6550, -23.6100
# Paraíso: -46.6550, -23.5775
```

(Num polígono em forma de "U" o centroide pode cair fora dele; nesse caso
`PointOnSurface` devolve um ponto garantidamente dentro.)

E `Distance` e `distance_lte`, do capítulo de GeoDjango, aceitam um
polígono tanto quanto um ponto. A distância de quem está dentro é zero:

```python
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D

for l in Lugar.objects.annotate(d=Distance("localizacao", centro.area)).order_by("d"):
    print(f"{l.nome}: {l.d.km:.1f} km")
# Café da Esquina: 0.0 km
# MASP: 0.0 km
# Parque Ibirapuera: 1.9 km
# Café do Rio: 359.0 km
# Parque da Cidade: 869.6 km
Lugar.objects.filter(localizacao__distance_lte=(centro.area, D(km=3)))
# <QuerySet [<Lugar: Café da Esquina>, <Lugar: MASP>, <Lugar: Parque Ibirapuera>]>
```

Você vai encontrar também o lookup `dwithin`, que é mais rápido porque usa
o índice. Só que, em um campo 4326, ele exige a distância em **graus**
(`localizacao__dwithin=(ponto, 0.01)`); passar `D(km=1)` dá
`ValueError`. Para distâncias em metros, fique com `distance_lte`.

## Uma API e um mapa que respondem "onde estou?"

Hora de levar isso para o navegador, no mesmo estilo do capítulo anterior:
primeiro a API, testada com `curl`, depois o Leaflet.

### A view `onde`

Ela recebe `?lon=&lat=` e devolve, em GeoJSON, os bairros que cobrem o
ponto. Em `lugares/views.py`:

```python
from django.contrib.gis.geos import Point, Polygon


def onde(request):
    try:
        lon = float(request.GET["lon"])
        lat = float(request.GET["lat"])
    except (KeyError, ValueError):
        return HttpResponseBadRequest("use ?lon=<longitude>&lat=<latitude>")
    ponto = Point(lon, lat, srid=4326)
    bairros = Bairro.objects.filter(area__covers=ponto)
    return geojson_response(bairros, "area", ["nome"])
```

O `try` protege dos dois erros possíveis: parâmetro faltando (`KeyError`)
e parâmetro que não é número (`ValueError`), ambos virando 400. O
`geojson_response` é o auxiliar do capítulo anterior; a lista vazia vira
uma `FeatureCollection` sem features, que é uma resposta válida ("você não
está em bairro nenhum"), e não um erro. E usamos `covers`, não `contains`:
quem clicar exatamente na linha da borda também recebe resposta.

### O `bairros_geojson` com o total de lugares

Para colorir cada bairro pelo número de lugares, o GeoJSON dos bairros
precisa levar o `total` em `properties`. A tentação é anotar o queryset e
passar `fields=["nome", "total"]` ao serializador. Experimente no shell,
com o `bairros` da seção anterior:

```python
from django.core import serializers

print(serializers.serialize("geojson", bairros, geometry_field="area", fields=["nome", "total"]))
# {"type": "FeatureCollection", "features": [{"type": "Feature", "id": 1,
#  "properties": {"nome": "Centro"}, "geometry": ...
```

O `total` sumiu. O serializador só conhece **campos do model**; anotações
são invisíveis para ele. Quando o serializador pronto não serve, montamos
o GeoJSON à mão, e é menos trabalho do que parece, porque a estrutura é a
que você leu no capítulo anterior. Troque a `bairros_geojson` por esta
versão:

```python
import json

from django.db.models import Count, IntegerField, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse


def bairros_geojson(request):
    # Quantos lugares abertos caem em cada bairro, numa consulta só
    lugares_dentro = (
        Lugar.objects.filter(aberto=True, localizacao__within=OuterRef("area"))
        .order_by()
        .annotate(grupo=Value(1))
        .values("grupo")
        .annotate(total=Count("pk"))
        .values("total")
    )
    bairros = Bairro.objects.annotate(
        total=Coalesce(Subquery(lugares_dentro, output_field=IntegerField()), 0)
    )

    features = [
        {
            "type": "Feature",
            "id": bairro.pk,
            "properties": {"nome": bairro.nome, "total": bairro.total},
            "geometry": json.loads(bairro.area.geojson),
        }
        for bairro in bairros
    ]
    return JsonResponse(
        {"type": "FeatureCollection", "features": features},
        content_type="application/geo+json",
    )
```

- A subconsulta é a mesma da seção de contagem, com um `aberto=True` a
  mais, para o total bater com os marcadores que o mapa mostra.
- Cada `Feature` é um dicionário Python com a mesma forma do GeoJSON.
  `bairro.area.geojson` devolve a `geometry` como **texto**; o
  `json.loads` transforma em dicionário para encaixar no todo (sem isso, a
  geometria sairia como uma string entre aspas).
- Agora é `JsonResponse`, e não `HttpResponse`, porque desta vez temos um
  dicionário, não um texto pronto. O `content_type` mantém o tipo oficial
  do GeoJSON.

Registre a URL nova em `lugares/urls.py`:

```python
    path("api/onde/", views.onde, name="onde"),
```

E teste as duas com o servidor rodando:

```bash
curl -s "localhost:8000/lugares/api/onde/?lon=-46.6558&lat=-23.5614" | jq -c '[.features[].properties.nome]'
# ["Centro","Paraíso"]
curl -s "localhost:8000/lugares/api/onde/?lon=-47.8825&lat=-15.7942" | jq -c '.features'
# []
curl -s -o /dev/null -w "%{http_code}\n" "localhost:8000/lugares/api/onde/?lon=abc"
# 400
curl -s localhost:8000/lugares/api/bairros.geojson | jq -c '[.features[] | [.properties.nome, .properties.total]]'
# [["Centro",2],["Moema",0],["Paraíso",2]]
```

### O mapa

Duas mudanças em `lugares/templates/lugares/mapa.html`. A primeira troca o
passo 3 (os bairros): a cor de preenchimento passa a depender do `total`,
e o nome com o total aparece ao passar o mouse:

```javascript
    // 3. Os bairros: a cor depende de quantos lugares caem dentro
    function corDoBairro(total) {
      return total >= 2 ? "#d9480f" : total === 1 ? "#f59f00" : "#adb5bd";
    }

    // Texto vindo do banco vira HTML no tooltip e no popup: escape antes
    function escapar(texto) {
      return String(texto).replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
      })[c]);
    }

    fetch("{% url 'lugares:bairros_geojson' %}")
      .then((resposta) => resposta.json())
      .then((dados) => {
        L.geoJSON(dados, {
          style: (feature) => ({
            color: "#495057",
            weight: 1,
            fillColor: corDoBairro(feature.properties.total),
            fillOpacity: 0.4,
          }),
          onEachFeature: (feature, camada) => {
            const p = feature.properties;
            camada.bindTooltip(`${escapar(p.nome)}: ${p.total} lugar(es)`);
          },
        }).addTo(mapa);
      });
```

A segunda acrescenta um passo 5, depois do `carregarLugares()`, que
reage ao clique em qualquer ponto do mapa:

```javascript
    // 5. Clique em qualquer ponto: "em que bairro estou?"
    mapa.on("click", (evento) => {
      const { lat, lng } = evento.latlng;
      fetch(`{% url 'lugares:onde' %}?lon=${lng}&lat=${lat}`)
        .then((resposta) => resposta.json())
        .then((dados) => {
          const nomes = dados.features.map((f) => escapar(f.properties.nome));
          const texto = nomes.length
            ? `Você está em: <strong>${nomes.join(", ")}</strong>`
            : "Fora de qualquer bairro";
          L.popup().setLatLng(evento.latlng).setContent(texto).openOn(mapa);
        });
    });
```

O que mudou:

- `style` agora é uma **função**, chamada para cada feature, em vez de um
  objeto fixo. É assim que a cor depende dos dados. Um mapa em que a cor
  de cada região codifica um número chama-se **coroplético**, e é
  provavelmente o mapa temático mais comum que existe.
- `bindTooltip` é o primo do `bindPopup` que aparece ao passar o mouse,
  sem clique. Tiramos o popup dos bairros de propósito: o clique agora é
  do mapa.
- `escapar` é a função do exercício 7 do capítulo anterior (se você não
  fez, está aí). Lá o aviso era "só você cadastra pelo admin, então tudo
  bem"; agora existe um formulário, e amanhã ele pode ser aberto a mais
  gente. Um nome de bairro como `<img src=x onerror=...>` entraria no
  tooltip e no popup como HTML e rodaria no navegador de todo mundo. O
  `login_required` limita quem escreve; o `escapar` garante que, escreva
  quem escrever, o texto é só texto.
- `mapa.on("click", ...)` recebe um evento com `latlng`, a posição
  geográfica do clique. De novo a pegadinha da ordem: o Leaflet entrega
  `lat` e `lng`, e a nossa API quer `lon` primeiro; a URL é montada com
  cada um no lugar certo.
- A resposta é uma `FeatureCollection`, então os nomes estão em
  `features[i].properties.nome`; `map` extrai a lista. `L.popup()` abre
  um balão solto no ponto clicado; `openOn(mapa)` fecha o anterior sozinho.

Recarregue o mapa e dê zoom em São Paulo. Os bairros com dois lugares
estão laranja-escuro, o Moema, vazio, cinza. Clique no MASP e veja "Você
está em: Centro, Paraíso"; clique no oceano e veja "Fora de qualquer
bairro". Clique num marcador: o popup do lugar abre e o do bairro não,
porque marcadores não repassam o clique ao mapa. Abra a aba Network e
veja a requisição a `api/onde/` sair a cada clique.

## Tabela de referência rápida

| O que                                 | Como                                                                   |
|:--------------------------------------|:-----------------------------------------------------------------------|
| Polígono a partir de cantos           | `Polygon(((x, y), ..., (x, y)), srid=4326)`, anel fechado              |
| Polígono com buraco                   | `Polygon(borda, buraco, srid=4326)`                                    |
| Retângulo                             | `Polygon.from_bbox((xmin, ymin, xmax, ymax))` e depois `.srid = 4326`  |
| De GeoJSON ou WKT                     | `GEOSGeometry('{"type": "Polygon", ...}')`, `GEOSGeometry("SRID=4326;POLYGON(...)")` |
| Círculo de N metros                   | `p.transform(31983, clone=True).buffer(N)` e depois `.transform(4326)` |
| Conferir validade                     | `geom.valid`, `geom.valid_reason`, `geom.make_valid()`                 |
| Anatomia                              | `num_points`, `num_interior_rings`, `exterior_ring`, `len(poly)`       |
| Formulário com mapa                   | `forms.ModelForm` + `widgets = {"area": forms.OSMWidget(attrs={...})}` |
| Template do formulário                | `{{ form.media }}` no `<head>` + CSS `.dj_map { height: 400px }`       |
| Página só para quem está logado       | `@login_required` na view + `LOGIN_URL = "/admin/login/"`              |
| Testar uma view com login             | `self.client.force_login(usuario)` no `setUp`                          |
| Geometria em texto num teste          | `"SRID=4326;POLYGON((x y, ..., x y))"` (EWKT)                          |
| Ponto → regiões                       | `Bairro.objects.filter(area__contains=ponto)` (`__covers` inclui a borda) |
| Região → pontos                       | `Lugar.objects.filter(localizacao__within=bairro.area)`                |
| Contagem por região, uma consulta     | `Subquery` com `OuterRef("area")`, `Value(1)`, `Count`, `Coalesce`     |
| Regiões que se tocam / invadem        | `area__intersects`, `area__overlaps`, `area__touches`                  |
| Área em km²                           | `Area(Transform("area", 31983))` e `.sq_km` (nunca `Area("area")` em 4326) |
| Filtrar por área                      | `.filter(a__gt=A(sq_km=10))` de `django.contrib.gis.measure`           |
| Interseção                            | `Intersection("area", outra_geometria)`                                |
| Juntar tudo                           | `Bairro.objects.aggregate(Union("area"))["area__union"]`               |
| Centro do polígono                    | `Centroid("area")` no banco, `poligono.centroid` no Python             |
| Distância até um polígono             | `Distance("localizacao", bairro.area)`, `__distance_lte=(area, D(km=3))` |
| GeoJSON com campos calculados         | Montar o `dict` da `FeatureCollection` e devolver com `JsonResponse`   |
| Clique no mapa                        | `mapa.on("click", (e) => { const { lat, lng } = e.latlng; ... })`      |
| Texto do banco no Leaflet             | `escapar(texto)` antes de `bindTooltip`, `bindPopup`, `setContent`     |
| Cor por valor no Leaflet              | `style: (feature) => ({ fillColor: cor(feature.properties.x) })`       |

## Exercícios

### Exercício 1: o seu bairro, no seu formulário

1. Abra `/lugares/bairros/novo/`, mude os `attrs` do `OSMWidget` para o
   mapa abrir na sua cidade e desenhe o seu bairro de verdade, contornando
   as ruas. Salve.
2. No shell, crie um `Point` com a sua casa e confira com `__covers` que
   o bairro novo a cobre. Quantos dos seus lugares dos capítulos
   anteriores caem nele? Use o método `lugares()`.
3. Desenhe um segundo bairro de propósito com os cantos na ordem errada
   (uma gravata borboleta) e salve. O formulário aceitou? Rode
   `Bairro.objects.filter(area__isvalid=False)` e veja o que aparece.
   Depois apague-o: um polígono inválido estraga as consultas de área.
4. Conserte o comando `importar_lugares` do capítulo de Django, que ficou
   para trás quando `localizacao` virou obrigatório: acrescente colunas
   `lon` e `lat` ao CSV, monte o `Point(lon, lat, srid=4326)` no comando e
   atualize o `ImportarLugaresTests`. No fim, `uv run python manage.py
   test` sem argumentos tem que passar inteiro.

### Exercício 2: a borda e o SQL por trás

1. Pegue um canto exato do Centro, por exemplo `Point(-46.620, -23.530,
   srid=4326)`, e rode `area__contains`, `area__covers`, `area__touches`
   e `area__intersects` com ele. Antes de rodar, escreva o que você espera
   de cada um; depois confira.
2. Imprima `.query` da consulta com `__covers` e encontre a função do
   PostGIS.
3. Copie o SQL de `Bairro.objects.filter(area__contains=masp)` e rode-o
   no `psql` com `EXPLAIN` na frente. Procure duas linhas: `Index Cond`,
   com o operador `~` (a comparação rápida de retângulos envolventes, que
   usa o índice GiST), e `Filter`, com `st_contains` (a conferência exata,
   só nas linhas que passaram pelo índice). Por que o PostGIS faz em dois
   passos?

### Exercício 3: raio de entrega

1. Para cada lugar da categoria "Café", crie um bairro chamado
   `"Entrega: <nome do café>"` com um círculo de 1 km em volta dele,
   usando o truque do `transform(31983, clone=True)` e `buffer(1000)`.
2. Recarregue o mapa e veja os círculos. Agora crie mais um com
   `buffer(0.01)` direto em graus, sem transformar, e compare o tamanho e
   a forma com os outros. Ele é um círculo de verdade? (Dica: fora do
   equador, um grau de longitude é mais curto que um grau de latitude.)
3. Com `__distance_lte` e `D(km=1)`, liste os lugares a até 1 km do Café
   da Esquina. O resultado bate com `__within` usando o círculo? Deveria?

### Exercício 4: regiões sobrepostas

1. Faça a contagem inversa da que fizemos: para cada **lugar**, em
   quantos bairros ele cai. Use um `Subquery` sobre
   `Bairro.objects.filter(area__contains=OuterRef("localizacao"))` com o
   mesmo truque do `Value(1)`. O MASP deve dar 2; Café do Rio e Parque
   da Cidade, 0.
2. Desenhe no formulário um bairro que invada **os dois**, Centro e
   Paraíso. Liste com `__overlaps` quem ele invade e, com `Intersection`
   e `Area(Transform(..., 31983))`, quanto de cada um.
3. Some a área de todos os bairros com `Transform` e `Area`, e compare com
   a área do `Union` de todos. Por que a soma é maior? Qual dos dois
   números é "a área coberta pelos bairros"?

### Exercício 5: ranking de áreas

1. Liste os bairros do maior para o menor em km², com uma casa decimal.
2. Acrescente o perímetro de cada um, em km, com `Perimeter(Transform("area",
   31983))`. (Sem o `Transform`, o Django se recusa a calcular perímetro
   em graus; experimente para ver a mensagem.)
3. Mostre, lado a lado, `Area("area")` e `Area(Transform("area", 31983))`
   para o mesmo bairro, e explique com suas palavras por que o primeiro
   número é inútil mesmo dizendo `sq_m`.
4. Inclua a área em km² nas `properties` do `bairros_geojson` e mostre-a
   no tooltip do mapa.

### Exercício 6: buracos e ilhas

1. Crie um bairro que tenha um buraco (uma praça que não faz parte dele),
   com `Polygon(borda, buraco, srid=4326)`. Cadastre um lugar dentro do
   buraco e confira que `__within` não o encontra, mas que ele está
   dentro do `envelope` (o retângulo envolvente) do bairro. Veja o buraco
   no mapa.
2. Crie um model `Cidade` com `nome` e
   `limite = models.MultiPolygonField(srid=4326)`, gere a migração e
   cadastre uma cidade com ilhas (Florianópolis é o exemplo clássico) com
   dois ou três retângulos: `MultiPolygon(p1, p2, srid=4326)`.
3. Tente gravar esse `MultiPolygon` no campo `area` de um `Bairro`. Qual
   é o erro? E se você gravar `cidade.limite[0]` (o primeiro polígono)?

## Referências

- **Lookups espaciais (`contains`, `within`, `covers`, `coveredby`,
  `intersects`, `overlaps`, `touches`, `disjoint`, `dwithin`,
  `distance_lte`, `isvalid`) e agregações (`Union`, `Collect`, `Extent`)**:
  <https://docs.djangoproject.com/en/stable/ref/contrib/gis/geoquerysets/>.
- **Funções de banco (`Area`, `Intersection`, `Transform`, `Centroid`,
  `PointOnSurface`, `Distance`, `Perimeter`, `MakeValid`)**:
  <https://docs.djangoproject.com/en/stable/ref/contrib/gis/functions/>.
- **API GEOS (`Polygon`, `LinearRing`, `MultiPolygon`, `from_bbox`,
  `buffer`, `transform`, `valid`, `make_valid`, `GEOSGeometry` a partir de
  GeoJSON e EWKT)**:
  <https://docs.djangoproject.com/en/stable/ref/contrib/gis/geos/>.
- **Medidas (`D`, `A`, `sq_km`, `ha`)**:
  <https://docs.djangoproject.com/en/stable/ref/contrib/gis/measure/>.
- **API de banco do GeoDjango (unidades, distâncias em campos geográficos,
  `dwithin` em graus)**:
  <https://docs.djangoproject.com/en/stable/ref/contrib/gis/db-api/>.
- **Campos geográficos (`PolygonField`, `MultiPolygonField`, `srid`)**:
  <https://docs.djangoproject.com/en/stable/ref/contrib/gis/model-api/>.
- **Formulários do GeoDjango (`forms.PolygonField`, `OpenLayersWidget`,
  `OSMWidget`, `attrs`)**:
  <https://docs.djangoproject.com/en/stable/ref/contrib/gis/forms-api/>.
- **`GISModelAdmin`, `gis_widget` e `gis_widget_kwargs`**:
  <https://docs.djangoproject.com/en/stable/ref/contrib/gis/admin/>.
- **Serializador GeoJSON (só campos do model)**:
  <https://docs.djangoproject.com/en/stable/ref/contrib/gis/serializers/>.
- **`ModelForm`**:
  <https://docs.djangoproject.com/en/stable/topics/forms/modelforms/>;
  **`form.media`**:
  <https://docs.djangoproject.com/en/stable/topics/forms/media/>;
  **CSRF**: <https://docs.djangoproject.com/en/stable/howto/csrf/>;
  **formulários e o ciclo GET/POST**:
  <https://docs.djangoproject.com/en/stable/topics/forms/>.
- **`login_required` e `LOGIN_URL`**:
  <https://docs.djangoproject.com/en/stable/topics/auth/default/#the-login-required-decorator>
  e <https://docs.djangoproject.com/en/stable/ref/settings/#login-url>.
- **`Subquery`, `OuterRef`, `Exists` e agregação dentro de subconsulta**:
  <https://docs.djangoproject.com/en/stable/ref/models/expressions/>.
- **`JsonResponse` e `HttpResponseBadRequest`**:
  <https://docs.djangoproject.com/en/stable/ref/request-response/>.
- **Cliente de testes (`post`, `force_login`, `assertRedirects`, CSRF
  desligado)**:
  <https://docs.djangoproject.com/en/stable/topics/testing/tools/>.
- **PostGIS**: `ST_Contains` (e por que a borda não conta),
  <https://postgis.net/docs/ST_Contains.html>; `ST_Within`,
  <https://postgis.net/docs/ST_Within.html>; `ST_Covers`,
  <https://postgis.net/docs/ST_Covers.html>; `ST_Intersects`,
  <https://postgis.net/docs/ST_Intersects.html>; `ST_Overlaps`,
  <https://postgis.net/docs/ST_Overlaps.html>; `ST_Touches`,
  <https://postgis.net/docs/ST_Touches.html>; `ST_Area` (unidades do SRID),
  <https://postgis.net/docs/ST_Area.html>; `ST_Buffer`,
  <https://postgis.net/docs/ST_Buffer.html>; `ST_DWithin`,
  <https://postgis.net/docs/ST_DWithin.html>; `ST_IsValid` e
  `ST_MakeValid`, <https://postgis.net/docs/ST_IsValid.html> e
  <https://postgis.net/docs/ST_MakeValid.html>; `ST_Transform`,
  <https://postgis.net/docs/ST_Transform.html>.
- **PostGIS, validade de polígonos e índices GiST**:
  <https://postgis.net/docs/using_postgis_dbmanagement.html>,
  <https://postgis.net/workshops/postgis-intro/validity.html> e
  <https://postgis.net/workshops/postgis-intro/indexing.html>.
- **Relações espaciais e a matriz DE-9IM**:
  <https://postgis.net/docs/using_postgis_query.html> e
  <https://postgis.net/workshops/postgis-intro/spatial_relationships.html>.
- **SRID 31983 (SIRGAS 2000 / UTM zona 23S)**: <https://epsg.io/31983>;
  o datum SIRGAS 2000, <https://epsg.io/4674>. As outras zonas (31978 a
  31985) seguem o mesmo padrão, por exemplo <https://epsg.io/31982> para
  a zona 22S.
- **A projeção UTM** (fusos de 6 graus, falso leste e falso norte), na
  documentação do PROJ:
  <https://proj.org/en/stable/operations/projections/utm.html>.
- **OGC Simple Features**: <https://www.ogc.org/standards/sfa/>;
  **GeoJSON (RFC 7946), anéis e regra da mão direita**:
  <https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.6>.
- **Leaflet 1.9.4**: eventos do mapa (`click`, `latlng`), `L.popup`,
  `bindTooltip`, `style` como função,
  <https://leafletjs.com/reference.html> (a página diz qual versão
  reflete; outras versões em <https://leafletjs.com/reference-versions.html>);
  tutorial de mapa coroplético, <https://leafletjs.com/examples/choropleth/>.
- **OpenLayers, interação de desenho (como fechar e editar o polígono)**:
  <https://openlayers.org/en/latest/examples/draw-features.html>.
- **geojson.io**: <https://geojson.io>.
