# GeoJSON e Leaflet: mapas na web

## Por que isso importa

No capítulo anterior os lugares ganharam coordenadas e o admin passou a
mostrar um mapa. Só que o admin é para **você**, que cadastra os dados. As
pessoas que usam o sistema nunca vão vê-lo. Elas querem abrir uma página e
ver os cafés, os parques e os bairros desenhados num mapa, clicar num ponto
e ler o nome.

Para isso, duas coisas precisam conversar: o **banco**, onde as geometrias
moram (no PostGIS), e o **navegador**, onde o mapa é desenhado (em
JavaScript). Elas falam línguas diferentes. O PostGIS guarda geometrias num
formato binário, e o navegador só entende texto, de preferência JSON. A
ponte entre os dois é o **GeoJSON**: um JSON com regras para descrever
pontos, linhas e polígonos. Praticamente toda ferramenta de mapas fala
GeoJSON: Leaflet, OpenLayers, Mapbox, Google Maps, QGIS, o GitHub (que
desenha um arquivo `.geojson` como mapa) e o próprio GeoDjango.

Neste capítulo você vai:

1. entender o formato GeoJSON lendo um exemplo escrito à mão;
2. criar um model com polígono, o `Bairro`;
3. escrever views que devolvem os lugares e os bairros em GeoJSON, sem
   instalar nenhum pacote novo;
4. montar uma página HTML com o **Leaflet**, a biblioteca de mapas mais
   usada na web, que busca esse GeoJSON e desenha tudo;
5. fazer o mapa pedir só os pontos que estão na tela, usando a consulta
   espacial `__within` do capítulo anterior.

O ponto de partida é o projeto `pontos` como ficou no fim do capítulo de
GeoDjango: app `lugares`, PostGIS no Docker e model `Lugar` com
`localizacao`.

## O caminho dos dados

Antes do código, o desenho completo. Vale voltar a ele sempre que alguma
parte parecer solta:

```{.mermaid width="90%"}
sequenceDiagram
  participant N as Navegador
  participant D as Django
  participant P as PostGIS
  N->>D: GET /lugares/mapa/
  D-->>N: HTML com Leaflet
  N->>D: fetch /lugares/api/lugares.geojson
  D->>P: SELECT ... (geometria)
  P-->>D: linhas com geometrias
  D-->>N: GeoJSON (FeatureCollection)
  N->>N: L.geoJSON(dados) desenha os pontos
```

Repare que são **duas** requisições. A primeira traz a página, que é só a
"moldura" com o mapa vazio. A segunda, feita pelo JavaScript da própria
página com `fetch`, traz os dados. Separar as duas coisas tem uma vantagem
enorme: a mesma URL de dados serve para o mapa, para um app de celular, para
um script Python ou para qualquer pessoa que queira baixar o GeoJSON.

## O formato GeoJSON

GeoJSON é um padrão aberto, descrito na RFC 7946. A melhor forma de
entendê-lo é ler um. Este arquivo tem dois itens: um café (um ponto) e um
bairro (um polígono):

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "id": 1,
      "properties": { "nome": "Café da Esquina", "categoria": "Café" },
      "geometry": {
        "type": "Point",
        "coordinates": [-46.6333, -23.5505]
      }
    },
    {
      "type": "Feature",
      "id": 2,
      "properties": { "nome": "Centro" },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [-46.665, -23.570],
          [-46.620, -23.570],
          [-46.620, -23.530],
          [-46.665, -23.530],
          [-46.665, -23.570]
        ]]
      }
    }
  ]
}
```

Lendo de fora para dentro:

- **`FeatureCollection`** é a "tabela": uma lista de itens em `features`.
  É quase sempre o que uma API devolve.
- Cada **`Feature`** é uma "linha": um objeto do mundo real. Ela tem duas
  partes: `geometry` (onde está) e `properties` (o que é). O `id` é
  opcional.
- **`properties`** é um objeto livre: coloque ali o que o mapa precisar
  mostrar (nome, categoria, cor, link...). O GeoJSON não impõe nada.
- **`geometry`** tem um `type` e as `coordinates`. O formato das
  coordenadas muda com o tipo, como mostra a tabela abaixo.

| Tipo de geometria | Formato de `coordinates`                    | Campo no GeoDjango   |
|:------------------|:--------------------------------------------|:---------------------|
| `Point`           | `[lon, lat]`                                | `PointField`         |
| `LineString`      | `[[lon, lat], [lon, lat], ...]`             | `LineStringField`    |
| `Polygon`         | `[[[lon, lat], ...]]` (lista de anéis)      | `PolygonField`       |
| `MultiPoint`, `MultiLineString`, `MultiPolygon` | uma lista a mais de profundidade | `Multi...Field` |

Três regras que pegam todo iniciante:

1. **A ordem é `[longitude, latitude]`.** É a mesma pegadinha do `Point` do
   GeoDjango: x antes de y. A boa notícia é que GeoDjango e GeoJSON
   concordam, então os números passam de um para o outro sem troca.
2. **O polígono é uma lista de anéis.** O primeiro anel é a borda de fora;
   os seguintes, se existirem, são buracos. Por isso os colchetes triplos
   `[[[ ]]]`, mesmo quando não há buraco.
3. **O anel precisa fechar.** O último ponto é igual ao primeiro. Repare no
   exemplo: `[-46.665, -23.570]` aparece no começo e no fim. Um anel de
   quatro cantos tem, portanto, cinco pontos.

O padrão também diz que as coordenadas estão em graus, no sistema WGS 84,
o SRID 4326 do capítulo anterior. Não há como declarar outro sistema no
GeoJSON moderno: se seus dados estiverem em outro SRID, eles precisam ser
convertidos antes de sair.

Você já viu GeoJSON sair do GeoDjango no capítulo anterior. Abra o shell e
confira de novo:

```bash
uv run python manage.py shell
```

```python
lugar = Lugar.objects.get(nome="Café da Esquina")
lugar.localizacao.geojson
# '{ "type": "Point", "coordinates": [ -46.6333, -23.5505 ] }'
```

Isso é só a `geometry`. Uma `Feature` completa precisa das `properties`, e
uma `FeatureCollection` precisa de todas as features juntas. Montar isso à
mão para cada model seria chato; o Django faz por nós, como veremos.

> **Experimente no geojson.io.** Copie o exemplo acima, abra
> <https://geojson.io> e cole no painel da direita. O ponto e o retângulo
> aparecem no mapa, em São Paulo. Mova um ponto e veja o JSON mudar. É a
> forma mais rápida de conferir se um GeoJSON está certo.

## Um model com polígono: o `Bairro`

Até aqui só temos pontos. Para ter algo com área, crie o model `Bairro` em
`lugares/models.py`. Se você fez o exercício 4 do capítulo anterior, ele já
existe; confira se está igual:

```python
class Bairro(models.Model):
    nome = models.CharField(max_length=100)
    area = models.PolygonField("área", srid=4326)

    class Meta:
        verbose_name = "bairro"
        verbose_name_plural = "bairros"
        ordering = ["nome"]

    def __str__(self):
        return self.nome
```

Registre-o no admin, em `lugares/admin.py`, para poder desenhar bairros
clicando:

```python
@admin.register(Bairro)
class BairroAdmin(GISModelAdmin):
    search_fields = ["nome"]
```

(Lembre de acrescentar `Bairro` no `from .models import ...`.) Gere e
aplique a migração:

```bash
uv run python manage.py makemigrations
uv run python manage.py migrate
```

Agora os dados. Além dos três lugares do capítulo anterior (um em São
Paulo, um em Brasília, um no Rio), crie mais dois em São Paulo e um bairro
retangular em volta do centro da cidade:

```bash
uv run python manage.py shell
```

```python
from django.contrib.gis.geos import Point, Polygon

museu = Categoria.objects.create(nome="Museu")
parque = Categoria.objects.get(nome="Parque")

Lugar.objects.create(nome="MASP", categoria=museu,
                     localizacao=Point(-46.6558, -23.5614, srid=4326))
Lugar.objects.create(nome="Parque Ibirapuera", categoria=parque,
                     localizacao=Point(-46.6575, -23.5874, srid=4326))

# Um anel fechado: o último ponto repete o primeiro
centro = Polygon(
    ((-46.665, -23.570), (-46.620, -23.570), (-46.620, -23.530),
     (-46.665, -23.530), (-46.665, -23.570)),
    srid=4326,
)
Bairro.objects.create(nome="Centro", area=centro)

Lugar.objects.filter(localizacao__within=centro)
# <QuerySet [<Lugar: Café da Esquina>, <Lugar: MASP>]>
```

Se você esquecer de repetir o primeiro ponto no fim, o GEOS reclama na hora:
aparece a linha `GEOS_ERROR: ... do not form a closed linestring` seguida
de um `GEOSException` meio críptico. "Closed linestring" é o anel fechado.
É a regra 3 do GeoJSON aparecendo de novo, agora do lado do Python.

## A view que devolve GeoJSON

O Django tem um sistema de **serializadores**: código que transforma um
QuerySet em texto (JSON, XML, YAML) e de volta. É o que os comandos
`dumpdata` e `loaddata` usam por baixo. O GeoDjango acrescenta um
serializador chamado `"geojson"`, que já monta a `FeatureCollection`
completa. Nenhum pacote novo é necessário.

Experimente no shell:

```python
from django.core import serializers

print(serializers.serialize(
    "geojson",
    Lugar.objects.all()[:1],
    geometry_field="localizacao",
    fields=["nome", "categoria"],
))
# {"type": "FeatureCollection", "features": [{"type": "Feature", "id": 1,
#  "properties": {"nome": "Café da Esquina", "categoria": 1},
#  "geometry": {"type": "Point", "coordinates": [-46.6333, -23.5505]}}]}
```

Os parâmetros:

- `geometry_field` diz qual campo vira a `geometry`. Se o model tiver só um
  campo geográfico, ele é achado sozinho, mas ser explícito não custa nada.
- `fields` escolhe o que vai para `properties`. **Sempre** use: sem ele,
  todos os campos saem, e um dia alguém acrescenta um campo que não devia
  ser público.

Repare num detalhe: `"categoria": 1`. Uma `ForeignKey` sai como o `id` da
categoria, o que não ajuda nada no popup do mapa. A solução é dizer ao
Django como identificar uma categoria pelo **nome**, a chamada *natural
key*. Acrescente um método ao model `Categoria`:

```python
class Categoria(models.Model):
    # ... campos e Meta como antes ...

    def natural_key(self):
        return (self.nome,)
```

E passe `use_natural_foreign_keys=True` ao serializador. Agora sai
`"categoria": ["Café"]`. É uma lista porque uma natural key pode ter vários
campos; como a nossa tem um só, a lista tem um item. No JavaScript, ao ser
colocada num texto, a lista `["Café"]` vira simplesmente `Café`.

Hora das views. Edite `lugares/views.py` e acrescente:

```python
from django.core import serializers
from django.http import HttpResponse

from .models import Bairro, Lugar


def geojson_response(queryset, geometry_field, fields):
    dados = serializers.serialize(
        "geojson",
        queryset,
        geometry_field=geometry_field,
        fields=fields,
        use_natural_foreign_keys=True,
    )
    return HttpResponse(dados, content_type="application/geo+json")


def lugares_geojson(request):
    lugares = Lugar.objects.filter(aberto=True).select_related("categoria")
    return geojson_response(lugares, "localizacao", ["nome", "categoria"])


def bairros_geojson(request):
    return geojson_response(Bairro.objects.all(), "area", ["nome"])


def mapa(request):
    return render(request, "lugares/mapa.html")
```

Algumas escolhas que valem explicar:

- `geojson_response` é uma função auxiliar, não uma view. As duas views
  fazem a mesma coisa com models diferentes, então o código comum fica num
  lugar só.
- Usamos `HttpResponse`, e não `JsonResponse`, porque o serializador já
  devolve o texto JSON pronto. O `JsonResponse` tentaria transformá-lo em
  JSON de novo.
- `application/geo+json` é o *content type* oficial do GeoJSON, definido na
  mesma RFC. Ferramentas que o reconhecem sabem que ali há um mapa.
- `filter(aberto=True)` e `select_related` são os mesmos do capítulo de
  Django: só lugares abertos, e a categoria vindo na mesma consulta SQL.

Agora as URLs. Em `lugares/urls.py`, acrescente três linhas à lista que já
existe:

```python
urlpatterns = [
    path("", views.lista_lugares, name="lista"),
    path("<int:pk>/", views.detalhe_lugar, name="detalhe"),
    path("mapa/", views.mapa, name="mapa"),
    path("api/lugares.geojson", views.lugares_geojson, name="lugares_geojson"),
    path("api/bairros.geojson", views.bairros_geojson, name="bairros_geojson"),
]
```

O `.geojson` no fim da URL não é obrigatório; é só uma convenção simpática
que diz, a quem lê, o que vem ali. Suba o servidor e teste com o `curl`
antes de ter qualquer mapa. O `jq` (do capítulo de terminal) deixa o
resultado legível:

```bash
uv run python manage.py runserver
```

Em outro terminal:

```bash
curl -s localhost:8000/lugares/api/lugares.geojson | jq '.features[0]'
curl -s localhost:8000/lugares/api/bairros.geojson | jq '.features[0].geometry.type'
curl -sI localhost:8000/lugares/api/lugares.geojson | grep -i content-type
```

Testar a API sozinha primeiro é um hábito que economiza horas. Se o mapa
não mostrar nada, você já sabe que o problema está no JavaScript, e não no
Django.

## A página com Leaflet

O **Leaflet** é uma biblioteca JavaScript de mapas, pequena (cerca de 42 KB)
e com uma documentação excelente. Ele não tem mapa próprio: ele desenha
**tiles**, as imagens quadradas de 256 pixels que formam o fundo do mapa,
buscadas de um servidor de tiles como o do OpenStreetMap. Por cima delas,
desenha as suas camadas: marcadores, linhas, polígonos. E sabe ler GeoJSON
diretamente.

Não é preciso instalar nada: o Leaflet é carregado de uma CDN, direto no
HTML. Crie `lugares/templates/lugares/mapa.html`:

```html
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="referrer" content="strict-origin-when-cross-origin">
  <title>Mapa dos lugares</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
        integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="">
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
          integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
  <style>
    html, body { height: 100%; margin: 0; }
    #mapa { height: 100%; }
  </style>
</head>
<body>
  <div id="mapa"></div>

  <script>
    // 1. O mapa, centrado no Brasil. Aqui a ordem é [latitude, longitude]!
    const mapa = L.map("mapa").setView([-15.79, -47.88], 4);

    // 2. As imagens de fundo (tiles) do OpenStreetMap
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(mapa);

    // 3. Os bairros: polígonos azuis, com o nome no popup
    fetch("{% url 'lugares:bairros_geojson' %}")
      .then((resposta) => resposta.json())
      .then((dados) => {
        L.geoJSON(dados, {
          style: { color: "#1c7ed6", weight: 2, fillOpacity: 0.15 },
          onEachFeature: (feature, camada) => {
            camada.bindPopup(`<strong>${feature.properties.nome}</strong>`);
          },
        }).addTo(mapa);
      });

    // 4. Os lugares: um marcador por ponto
    fetch("{% url 'lugares:lugares_geojson' %}")
      .then((resposta) => resposta.json())
      .then((dados) => {
        const camada = L.geoJSON(dados, {
          onEachFeature: (feature, camada) => {
            const p = feature.properties;
            camada.bindPopup(`<strong>${p.nome}</strong><br>${p.categoria}`);
          },
        }).addTo(mapa);
        mapa.fitBounds(camada.getBounds(), { padding: [30, 30] });
      });
  </script>
</body>
</html>
```

Abra <http://localhost:8000/lugares/mapa/>. O mapa abre no Brasil,
enquadra os cinco lugares e mostra o retângulo do Centro em São Paulo. Dê
zoom lá e clique num marcador ou no bairro.

Vamos por partes.

**O `<head>`.** O `leaflet.css` e o `leaflet.js` vêm do unpkg, uma CDN que
serve qualquer pacote do npm. O `@1.9.4` fixa a versão, para o mapa não
quebrar sozinho quando sair uma nova. O `integrity` é uma impressão digital
do arquivo: se alguém alterar o arquivo na CDN, o navegador se recusa a
rodá-lo. Os valores vêm da página de download do Leaflet; copie-os de lá,
nunca invente. O `<style>` dá altura ao mapa: uma `div` vazia tem altura
zero, e um mapa de altura zero é invisível. Esse é o erro número um de
quem começa com Leaflet.

**Passo 1, o mapa.** `L.map("mapa")` cria o mapa dentro da `div` com
`id="mapa"`. O `L` é o objeto global do Leaflet: tudo começa com ele.
`setView([lat, lon], zoom)` diz onde abrir. **Atenção**: aqui a ordem é
`[latitude, longitude]`, o contrário do GeoJSON! O Leaflet segue o costume
do dia a dia, e o GeoJSON segue o `(x, y)` da matemática. É o mesmo lugar
escrito de dois jeitos. Quando você passa GeoJSON ao Leaflet, ele faz a
troca sozinho; só as coordenadas que você digita em JavaScript usam
`[lat, lon]`.

**Passo 2, os tiles.** `L.tileLayer` recebe um modelo de URL: `{z}` é o
zoom, `{x}` e `{y}` a posição do quadrado. O Leaflet calcula quais
quadrados cabem na tela e busca cada um. A `attribution` não é enfeite: a
licença do OpenStreetMap **exige** o crédito visível.

**Passos 3 e 4, os dados.** `fetch` busca a URL e `resposta.json()`
transforma o texto em objeto JavaScript. `{% url '...' %}` é o Django
escrevendo o caminho certo antes da página sair do servidor, igual nos
templates do capítulo de Django. Depois, `L.geoJSON(dados, opções)` faz o
trabalho pesado: percorre as features e cria um marcador para cada `Point`
e uma forma para cada `Polygon`. As opções:

- `style` define cor, espessura da borda (`weight`) e transparência do
  preenchimento (`fillOpacity`) de linhas e polígonos.
- `onEachFeature` é chamada uma vez por feature, com a feature do GeoJSON
  e a camada que o Leaflet criou para ela. É o lugar de ligar popups,
  eventos de clique e afins. `bindPopup` recebe o HTML que aparece ao
  clicar.

Por fim, `fitBounds` ajusta zoom e centro para caber tudo o que chegou, e
`padding` deixa uma margem para os marcadores não ficarem colados na borda.

> **Mapa cinza com "Access blocked" ou erro 403 nos tiles?** O servidor de
> tiles do OpenStreetMap é mantido por voluntários e recusa pedidos que não
> dizem de qual site vieram (o cabeçalho `Referer`). Acontece que o Django,
> por segurança, manda o navegador **não** enviar esse cabeçalho para
> outros sites: o `SecurityMiddleware` responde com
> `Referrer-Policy: same-origin`. A linha
> `<meta name="referrer" content="strict-origin-when-cross-origin">` no
> `<head>` libera o envio só do endereço do site (sem o caminho da página)
> para o servidor de tiles. Sem ela, os tiles ficam bloqueados.

> **Cuidado com HTML nos popups.** O `bindPopup` interpreta o texto como
> HTML. Se um usuário cadastrar um lugar chamado `<img src=x onerror=...>`,
> esse código roda no navegador de quem clicar. Aqui só você cadastra pelo
> admin, então tudo bem; mas, se os dados vierem de fora, escape o texto
> antes (o exercício 7 mostra como).

## Filtrando pelo que está na tela

Com cinco lugares, mandar todos de uma vez é ótimo. Com cinquenta mil, a
página demora, o navegador engasga e ninguém vê nada, porque os marcadores
ficam empilhados. A solução clássica é pedir ao servidor só o que cabe na
parte do mapa que está visível, a chamada **bounding box** (ou *bbox*): o
retângulo definido por oeste, sul, leste e norte.

Do lado do Django, a view aceita um parâmetro `?bbox=xmin,ymin,xmax,ymax`
e usa o `__within` do capítulo anterior. Troque a `lugares_geojson` por
esta versão (e acrescente os imports novos no topo):

```python
from django.contrib.gis.geos import Polygon
from django.http import HttpResponse, HttpResponseBadRequest


def lugares_geojson(request):
    lugares = Lugar.objects.filter(aberto=True).select_related("categoria")

    bbox = request.GET.get("bbox")
    if bbox:
        try:
            xmin, ymin, xmax, ymax = (float(v) for v in bbox.split(","))
        except ValueError:
            return HttpResponseBadRequest("bbox deve ser xmin,ymin,xmax,ymax")
        area = Polygon.from_bbox((xmin, ymin, xmax, ymax))
        area.srid = 4326
        lugares = lugares.filter(localizacao__within=area)

    return geojson_response(lugares, "localizacao", ["nome", "categoria"])
```

- `request.GET.get("bbox")` lê o parâmetro da URL, ou `None` se não veio.
  Sem bbox, a view continua devolvendo tudo, como antes.
- O `try` protege contra lixo: `?bbox=abc` ou números a menos causam um
  `ValueError`, e respondemos com **400 Bad Request** em vez de deixar o
  servidor quebrar com um erro 500. Dado que vem da URL é dado que vem do
  usuário, e dado do usuário nunca é confiável.
- `Polygon.from_bbox` monta o retângulo, e o índice GiST do PostGIS torna
  essa consulta rápida mesmo com milhões de linhas.

Teste com o `curl` um retângulo em volta de São Paulo, e depois um bbox
inválido:

```bash
curl -s "localhost:8000/lugares/api/lugares.geojson?bbox=-46.7,-23.6,-46.6,-23.5" \
  | jq '[.features[].properties.nome]'
# [ "Café da Esquina", "MASP", "Parque Ibirapuera" ]

curl -s -o /dev/null -w "%{http_code}\n" "localhost:8000/lugares/api/lugares.geojson?bbox=abc"
# 400
```

Do lado do Leaflet, troque o passo 4 do template por este:

```javascript
    // 4. Os lugares: recarregados a cada vez que o mapa para de se mover
    const camadaLugares = L.geoJSON(null, {
      onEachFeature: (feature, camada) => {
        const p = feature.properties;
        camada.bindPopup(`<strong>${p.nome}</strong><br>${p.categoria}`);
      },
    }).addTo(mapa);

    function carregarLugares() {
      const bbox = mapa.getBounds().toBBoxString();  // "oeste,sul,leste,norte"
      fetch(`{% url 'lugares:lugares_geojson' %}?bbox=${bbox}`)
        .then((resposta) => resposta.json())
        .then((dados) => {
          camadaLugares.clearLayers();
          camadaLugares.addData(dados);
          console.log(`${dados.features.length} lugares na tela`);
        });
    }

    mapa.on("moveend", carregarLugares);
    carregarLugares();
```

O que mudou:

- A camada é criada **uma vez só**, vazia (`L.geoJSON(null, ...)`), e
  reaproveitada: a cada resposta, `clearLayers()` apaga os marcadores
  antigos e `addData()` desenha os novos, com as mesmas opções de popup.
- `mapa.getBounds().toBBoxString()` devolve o retângulo visível já na ordem
  que a view espera: longitude oeste, latitude sul, longitude leste,
  latitude norte. Ou seja, `xmin,ymin,xmax,ymax`. Não é coincidência: essa
  ordem é o padrão de bbox do GeoJSON também.
- `mapa.on("moveend", ...)` registra a função para rodar toda vez que o
  usuário termina de arrastar ou dar zoom. A última linha a chama uma vez
  no começo, para o mapa não abrir vazio.
- O `fitBounds` saiu: agora é o mapa que manda no que é carregado, e não o
  contrário.

Abra o console do navegador (Cmd+Option+J no Chrome) e dê zoom em São
Paulo. A mensagem passa de `5 lugares na tela` para `3 lugares na tela`.
Na aba **Network** dá para ver cada requisição saindo, com o bbox na URL.

## Tabela de referência rápida

| O que                              | Como                                                                  |
|:-----------------------------------|:----------------------------------------------------------------------|
| Queryset para GeoJSON              | `serializers.serialize("geojson", qs, geometry_field=..., fields=[...])` |
| FK pelo nome em vez do id          | `natural_key()` no model + `use_natural_foreign_keys=True`            |
| Uma geometria só                   | `objeto.campo.geojson`                                                |
| Content type do GeoJSON            | `application/geo+json`                                                |
| Ordem no GeoJSON e no GeoDjango    | `[longitude, latitude]`                                               |
| Ordem no Leaflet (`setView`, `L.marker`) | `[latitude, longitude]`                                          |
| Criar o mapa                       | `L.map("id-da-div").setView([lat, lon], zoom)`                        |
| Fundo do OpenStreetMap             | `L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {attribution})` |
| Desenhar GeoJSON                   | `L.geoJSON(dados, {style, onEachFeature}).addTo(mapa)`                |
| Popup                              | `camada.bindPopup("<strong>texto</strong>")`                          |
| Enquadrar os dados                 | `mapa.fitBounds(camada.getBounds())`                                  |
| Retângulo visível                  | `mapa.getBounds().toBBoxString()`                                     |
| Reagir a arrasto e zoom            | `mapa.on("moveend", funcao)`                                          |
| Trocar os dados de uma camada      | `camada.clearLayers(); camada.addData(dados)`                         |
| Filtrar por bbox no Django         | `Polygon.from_bbox((xmin, ymin, xmax, ymax))` + `__within`            |
| Tiles com 403                      | `<meta name="referrer" content="strict-origin-when-cross-origin">`    |

## Exercícios

### Exercício 1: brincando no geojson.io

1. Abra <https://geojson.io>, desenhe um polígono em volta do seu bairro e
   copie o GeoJSON gerado.
2. Conte os pontos do anel. O último é igual ao primeiro?
3. No shell, crie um `Bairro` com essa geometria usando
   `GEOSGeometry('{"type": "Polygon", ...}')` (só a parte `geometry`).
   Recarregue o mapa e ache seu bairro.

### Exercício 2: do Django para um arquivo, antes de qualquer HTML

Antes de escrever uma linha de JavaScript, dá para ver se os dados estão
certos: salve o GeoJSON num arquivo e abra-o num visualizador online.

1. Com o servidor rodando, salve a resposta da API num arquivo:

   ```bash
   curl -s localhost:8000/lugares/api/lugares.geojson -o lugares.geojson
   curl -s localhost:8000/lugares/api/bairros.geojson -o bairros.geojson
   ```

2. Abra <https://geojson.io> e arraste o `lugares.geojson` para cima do
   mapa (ou use o menu **Open**). Os pontos aparecem? Estão nas cidades
   certas? Clique num deles e confira as `properties`.
3. Faça o mesmo com o `bairros.geojson`. O retângulo cobre o centro de São
   Paulo?
4. Agora gere o arquivo sem servidor nenhum, direto do banco, com o
   `dumpdata` (o mesmo serializador, usado pela linha de comando):

   ```bash
   uv run python manage.py dumpdata lugares.Lugar --format geojson --indent 2 -o todos.geojson
   ```

   Abra o `todos.geojson` no editor e compare com o `lugares.geojson`.
   Quais `properties` a mais apareceram? Por que a view usa `fields=[...]`?
   E o que muda se você acrescentar `--natural-foreign` ao comando?
5. Estrague o arquivo de propósito: troque a ordem de um par de
   coordenadas para `[latitude, longitude]` e abra de novo no geojson.io.
   Onde o ponto foi parar?

Esse é um hábito de profissional: quando um mapa "não mostra nada", separe
o problema em dois. Se o arquivo aparece certo no geojson.io, os dados
estão bons e o erro está na página; se não aparece, o erro está no Django
ou no banco.

### Exercício 3: a pegadinha, versão Leaflet

1. No template, troque o `setView([-15.79, -47.88], 4)` por
   `setView([-47.88, -15.79], 4)`.
2. Onde o mapa abre? Por que o Leaflet não reclama?
3. Desfaça a troca. Agora explique, com suas palavras, por que os pontos
   que vêm do GeoJSON aparecem no lugar certo mesmo o Leaflet usando
   `[lat, lon]`.

### Exercício 4: uma cor por categoria

1. Os marcadores padrão do Leaflet são todos azuis. Troque-os por
   círculos coloridos com a opção `pointToLayer` do `L.geoJSON`:

   ```javascript
   const cores = { "Café": "#e8590c", "Parque": "#2f9e44", "Museu": "#7048e8" };
   // dentro das opções de L.geoJSON:
   pointToLayer: (feature, latlng) =>
     L.circleMarker(latlng, { radius: 8, color: cores[feature.properties.categoria] }),
   ```

2. Por que `cores[["Café"]]` funciona, mesmo a categoria sendo uma lista?
   (Dica: como o JavaScript transforma uma chave de objeto em texto?)
3. Crie uma categoria nova sem cor no dicionário. O que acontece com o
   círculo? Dê uma cor padrão com `cores[...] || "#868e96"`.

### Exercício 5: filtro por categoria

1. Faça a view `lugares_geojson` aceitar também `?categoria=Café`,
   filtrando com `categoria__nome`. Teste com o `curl`.
2. Ele precisa funcionar junto com o bbox: `?bbox=...&categoria=Café`.
3. Acrescente ao HTML um `<select>` com as categorias. Ao mudar a opção,
   chame `carregarLugares()` passando a categoria escolhida na URL.

### Exercício 6: uma rota

1. Crie um model `Rota` com `nome` e `trajeto = models.LineStringField(srid=4326)`.
2. Cadastre uma rota do Café da Esquina até o MASP (pelo admin ou com
   `LineString((lon, lat), (lon, lat), srid=4326)`).
3. Faça o endpoint `/lugares/api/rotas.geojson` e desenhe as rotas no mapa
   com uma linha tracejada (`style: { dashArray: "6 6" }`).

### Exercício 7: popups seguros

1. Cadastre pelo admin um lugar chamado `<em>Teste</em>`. Como ele aparece
   no popup? Por quê?
2. Escreva uma função `escapar(texto)` em JavaScript que troque `&`, `<`,
   `>`, `"` e `'` pelas entidades HTML, e use-a no `bindPopup`.
3. Confirme que o nome agora aparece com os sinais de menor e maior,
   em vez de itálico.

## Referências

- **Especificação do GeoJSON (RFC 7946)**, incluindo a ordem das
  coordenadas, anéis de polígono, bbox e o content type
  `application/geo+json`: <https://datatracker.ietf.org/doc/html/rfc7946>.
- **Serializador GeoJSON do GeoDjango** (`geometry_field`, `fields`,
  `id_field`, `srid`):
  <https://docs.djangoproject.com/en/stable/ref/contrib/gis/serializers/>.
- **Serialização no Django e natural keys**
  (`natural_key`, `use_natural_foreign_keys`):
  <https://docs.djangoproject.com/en/stable/topics/serialization/>.
- **Objetos GEOS (`.geojson`, `Polygon.from_bbox`, `GEOSGeometry`)**:
  <https://docs.djangoproject.com/en/stable/ref/contrib/gis/geos/>.
- **`SecurityMiddleware` e `SECURE_REFERRER_POLICY`**:
  <https://docs.djangoproject.com/en/stable/ref/middleware/#referrer-policy>.
- **Leaflet**: download e hashes do `integrity`,
  <https://leafletjs.com/download.html>; guia de início rápido,
  <https://leafletjs.com/examples/quick-start/>; tutorial de GeoJSON,
  <https://leafletjs.com/examples/geojson/>; referência da API
  (`L.geoJSON`, `getBounds`, `toBBoxString`, eventos),
  <https://leafletjs.com/reference.html>.
- **Política de uso dos tiles do OpenStreetMap** (atribuição, `Referer`):
  <https://operations.osmfoundation.org/policies/tiles/> e a página de
  bloqueio, <https://wiki.openstreetmap.org/wiki/Blocked_tiles>.
- **Atribuição e licença do OpenStreetMap**:
  <https://www.openstreetmap.org/copyright>.
- **`Referrer-Policy` e a tag `<meta name="referrer">`** (MDN):
  <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Referrer-Policy>.
- **Fetch API** (MDN): <https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API>.
- **geojson.io**, editor e visualizador de GeoJSON: <https://geojson.io>.
