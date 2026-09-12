# GeoDjango: modelos e admin com mapas

## Por que isso importa

Muita informação do mundo real tem um **lugar**: uma loja, uma entrega, um
sensor, uma ocorrência, uma rota. Enquanto o endereço é só um texto, o banco
consegue responder "quais lugares têm 'Paulista' no endereço?", mas não
"quais lugares estão a menos de 2 km de mim?", "qual é o mais próximo?" ou
"quais caem dentro deste bairro?". Para isso os dados precisam ser
**geográficos de verdade**: pontos, linhas e polígonos que o banco entende e
consegue medir, comparar e indexar.

O **GeoDjango** é o módulo do Django (`django.contrib.gis`) que faz isso.
Ele estende o ORM com campos e consultas espaciais, e o admin com um mapa
para clicar. Neste capítulo pegamos o projeto `pontos` do capítulo anterior
e damos a cada lugar uma localização real. No fim, o admin mostra um mapa e
o shell responde "o que está perto de mim?".

## As peças por baixo do GeoDjango

O GeoDjango não faz as contas geográficas sozinho. Ele se apoia em
bibliotecas em C que são o padrão da indústria, e o banco de dados precisa
saber armazenar geometrias. As peças:

| Peça      | O que faz                                                          | Onde roda        |
|:----------|:-------------------------------------------------------------------|:-----------------|
| **GEOS**  | Operações com geometrias: distância, interseção, "está dentro de"  | Sua máquina      |
| **GDAL**  | Lê e escreve dezenas de formatos geográficos (Shapefile, GeoJSON…) e converte entre sistemas de coordenadas | Sua máquina |
| **PROJ**  | As fórmulas de projeção cartográfica usadas pelo GDAL              | Sua máquina      |
| **PostGIS** | Extensão do PostgreSQL que adiciona tipos, funções e índices espaciais ao banco | Docker (container `db`) |

No Mac, as três bibliotecas vêm pelo Homebrew:

```bash
brew install gdal geos proj
```

E o PostGIS vem no Docker, com o `docker-compose.yml` do capítulo anterior. Crie
o arquivo na raiz do projeto `pontos`:

```yaml
services:
  db:
    image: imresamu/postgis:17-3.5
    environment:
      POSTGRES_DB: pontos
      POSTGRES_USER: pontos
      POSTGRES_PASSWORD: pontos
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pontos -d pontos"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  pgdata:
```

Suba e confira que o PostGIS está ativo:

```bash
docker compose up -d --wait
docker compose exec db psql -U pontos -d pontos -c "SELECT postgis_version();"
```

Por fim, o Django precisa de um driver para falar com o PostgreSQL. O `uv`
cuida disso:

```bash
uv add "psycopg[binary]"
```

## Modelos comuns e modelos GIS: o que muda

Esta é a pergunta central do capítulo, então vale ir devagar. Um modelo GIS
**é** um modelo Django. Tudo o que você aprendeu (campos, `Meta`, `__str__`,
migrações, admin, QuerySets) continua valendo. O que o GeoDjango faz é
**acrescentar**, em cinco pontos:

**1. A importação.** Em vez de `from django.db import models`, você escreve
`from django.contrib.gis.db import models`. Esse módulo contém todos os
campos normais (`CharField`, `ForeignKey`...) **mais** os geográficos. Por
isso um único `import` serve para o arquivo inteiro.

**2. Os campos geográficos.** Os tipos novos representam geometrias:

| Campo                  | Guarda                                    | Exemplo de uso              |
|:-----------------------|:------------------------------------------|:----------------------------|
| `PointField`           | Um ponto (x, y)                           | Endereço, sensor, foto      |
| `LineStringField`      | Uma sequência de pontos                   | Rota, rua, rio              |
| `PolygonField`         | Uma área fechada, com possíveis buracos   | Bairro, lote, área de entrega |
| `MultiPointField`, `MultiLineStringField`, `MultiPolygonField` | Vários de cada | Município com ilhas |
| `GeometryField`        | Qualquer um dos acima                     | Quando o tipo varia         |

No banco, cada um vira uma coluna do tipo `geometry` do PostGIS, com um
índice espacial criado automaticamente.

**3. O SRID.** Toda geometria precisa dizer em qual **sistema de referência
espacial** suas coordenadas estão. É o parâmetro `srid`. O padrão, e o que
você vai usar quase sempre, é o **4326**: latitude e longitude em graus,
o mesmo do GPS e do Google Maps. Cuidado com uma pegadinha: no GeoDjango a
ordem é `Point(longitude, latitude)`, isto é, `(x, y)`, o contrário do que se
fala no dia a dia.

**4. Os lookups espaciais.** Além de `__icontains`, `__gte` e companhia, os
campos geográficos aceitam lookups como `__distance_lte`, `__within`,
`__intersects`, `__contains`, `__dwithin`. Eles viram funções do PostGIS
(`ST_DWithin`, `ST_Within`...) no SQL. Existem também funções para anotar
consultas, como `Distance` e `Area`.

**5. O backend do banco.** O `ENGINE` em `settings.py` passa a ser
`django.contrib.gis.db.backends.postgis`, e `'django.contrib.gis'` entra em
`INSTALLED_APPS`. O SQLite comum não serve: ele não sabe o que é uma
geometria. (Existe o SpatiaLite, uma extensão do SQLite, mas a instalação no
Mac é frágil; PostGIS no Docker é o caminho mais previsível.)

Resumindo em uma tabela:

| Aspecto            | Modelo comum                        | Modelo GIS                                          |
|:-------------------|:------------------------------------|:----------------------------------------------------|
| Import             | `django.db.models`                  | `django.contrib.gis.db.models`                      |
| Campos             | `CharField`, `IntegerField`...      | Os mesmos **mais** `PointField`, `PolygonField`...  |
| Coluna no banco    | `varchar`, `integer`...             | `geometry(Point, 4326)` com índice GiST             |
| Coordenadas        | não se aplica                       | Exigem um `srid` (padrão 4326)                      |
| Valores em Python  | `str`, `int`, `datetime`...         | `Point`, `Polygon`... de `django.contrib.gis.geos`  |
| Lookups            | `__icontains`, `__gte`, `__in`      | Os mesmos **mais** `__distance_lte`, `__within`...  |
| Banco              | SQLite, PostgreSQL, MySQL...        | PostGIS (ou SpatiaLite, Oracle, MySQL com limites)  |
| Admin              | `ModelAdmin`                        | `GISModelAdmin`, que desenha um mapa                |
| Bibliotecas        | Nenhuma extra                       | GEOS, GDAL, PROJ na máquina                         |

Uma curiosidade histórica que você vai encontrar em tutoriais antigos: até o
Django 1.9 era preciso declarar `objects = models.GeoManager()` em cada
modelo GIS. Isso **não existe mais**; o manager padrão já entende consultas
espaciais. Se um tutorial mandar usar `GeoManager`, ele está desatualizado.

## Migrando o projeto para o PostGIS

Três mudanças em `config/settings.py`. Primeiro, registre o app GIS:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'lugares',
]
```

Segundo, troque o banco:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'pontos',
        'USER': 'pontos',
        'PASSWORD': 'pontos',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

Terceiro, uma particularidade do Mac. O Python instalado pelo `uv` não
procura bibliotecas em `/opt/homebrew/lib`, então o Django não encontra o
GDAL sozinho e reclama com "Could not find the GDAL library". A solução é
apontar o caminho. Acrescente ao fim do `settings.py`:

```python
# GeoDjango no macOS com Homebrew: o Python do uv não procura em /opt/homebrew/lib,
# então apontamos as bibliotecas explicitamente.
import platform

if platform.system() == "Darwin":
    GDAL_LIBRARY_PATH = "/opt/homebrew/lib/libgdal.dylib"
    GEOS_LIBRARY_PATH = "/opt/homebrew/lib/libgeos_c.dylib"
```

(Em Macs com processador Intel o Homebrew fica em `/usr/local` em vez de
`/opt/homebrew`. No Linux esse bloco é ignorado e as bibliotecas do sistema
são encontradas normalmente.)

Agora o model. Troque o `import` e acrescente o campo de localização em
`lugares/models.py`:

```python
from django.contrib.gis.db import models


class Categoria(models.Model):
    nome = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = "categoria"
        verbose_name_plural = "categorias"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Lugar(models.Model):
    nome = models.CharField(max_length=100)
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name="lugares"
    )
    endereco = models.CharField("endereço", max_length=200, blank=True)
    descricao = models.TextField("descrição", blank=True)
    aberto = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    localizacao = models.PointField("localização", srid=4326)

    class Meta:
        verbose_name = "lugar"
        verbose_name_plural = "lugares"
        ordering = ["nome"]

    def __str__(self):
        return self.nome
```

Repare: o único campo novo é `localizacao`. O resto é idêntico, só que agora
vem de `django.contrib.gis.db`.

Como trocamos de banco, o novo está vazio. Gere a migração (o campo novo é
obrigatório, e como não há linhas ainda, não há o que preencher) e aplique:

```bash
uv run python manage.py makemigrations
uv run python manage.py migrate
uv run python manage.py createsuperuser
```

> Se você tivesse dados no SQLite e quisesse mantê-los, o caminho seria
> `dumpdata` antes e `loaddata` depois, dando um valor padrão temporário ao
> campo novo. Para este capítulo, recomeçar do zero é mais simples.

Abra o `psql` e veja o que o Django criou:

```bash
docker compose exec db psql -U pontos -d pontos -c "\d lugares_lugar"
```

Você vai ver a coluna `localizacao | geometry(Point,4326)` e, no fim, um
índice `USING gist (localizacao)`. É esse índice que torna as consultas
espaciais rápidas mesmo com milhões de linhas.

## Admin com mapa

Troque `ModelAdmin` por `GISModelAdmin` em `lugares/admin.py`:

```python
from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import Categoria, Lugar


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    search_fields = ["nome"]


@admin.register(Lugar)
class LugarAdmin(GISModelAdmin):
    list_display = ["nome", "categoria", "aberto", "criado_em"]
    list_filter = ["categoria", "aberto"]
    search_fields = ["nome", "endereco"]
    # Centraliza o mapa do formulário em Brasília, com zoom de país
    gis_widget_kwargs = {
        "attrs": {"default_lon": -47.88, "default_lat": -15.79, "default_zoom": 4},
    }
```

Suba o servidor, entre no admin e clique em "Adicionar lugar". No lugar de
uma caixa de texto para `localização`, há um mapa do OpenStreetMap (desenhado
pela biblioteca OpenLayers). Clique para colocar o ponto, arraste para
ajustar, use o botão de apagar para recomeçar. Ao salvar, o Django grava a
geometria no PostGIS.

`gis_widget_kwargs` configura o mapa: `default_lon` e `default_lat` definem
onde ele abre, `default_zoom` o nível de zoom. Sem isso o mapa abre no meio
do oceano Atlântico (longitude 0, latitude 0), o que confunde qualquer
pessoa.

## Consultas espaciais

Cadastre alguns lugares pelo admin ou pelo shell. Aqui vão três cidades, com
coordenadas reais, para ter o que medir:

```bash
uv run python manage.py shell
```

```python
from django.contrib.gis.geos import Point

cafe = Categoria.objects.create(nome="Café")
parque = Categoria.objects.create(nome="Parque")

# Lembre: Point(longitude, latitude)
Lugar.objects.create(nome="Café da Esquina", categoria=cafe,
                     localizacao=Point(-46.6333, -23.5505, srid=4326))   # São Paulo
Lugar.objects.create(nome="Parque da Cidade", categoria=parque,
                     localizacao=Point(-47.8825, -15.7942, srid=4326))   # Brasília
Lugar.objects.create(nome="Café do Rio", categoria=cafe,
                     localizacao=Point(-43.1729, -22.9068, srid=4326))   # Rio de Janeiro
```

Agora as perguntas que só um banco geográfico responde. "O que está a até
500 km de São Paulo?":

```python
from django.contrib.gis.measure import D

aqui = Point(-46.6333, -23.5505, srid=4326)
Lugar.objects.filter(localizacao__distance_lte=(aqui, D(km=500)))
# <QuerySet [<Lugar: Café da Esquina>, <Lugar: Café do Rio>]>
```

`D` é um objeto de distância que aceita `km`, `m`, `mi` e converte por você.
"Qual é o mais perto?", ordenando por distância:

```python
from django.contrib.gis.db.models.functions import Distance

for lugar in Lugar.objects.annotate(dist=Distance("localizacao", aqui)).order_by("dist"):
    print(f"{lugar.nome}: {lugar.dist.km:.0f} km")
# Café da Esquina: 0 km
# Café do Rio: 361 km
# Parque da Cidade: 872 km
```

Como o SRID 4326 está em graus, o PostGIS calcula essas distâncias sobre a
esfera terrestre (a função `ST_DistanceSphere`), em metros; `.km` converte.
E os valores estão certos: São Paulo–Rio são mesmo cerca de 360 km em linha
reta.

A geometria em si é um objeto Python com métodos úteis:

```python
lugar = Lugar.objects.get(nome="Café da Esquina")
lugar.localizacao.x, lugar.localizacao.y   # (-46.6333, -23.5505)
lugar.localizacao.wkt                      # 'POINT (-46.6333 -23.5505)'
lugar.localizacao.geojson                  # '{ "type": "Point", "coordinates": [ -46.6333, -23.5505 ] }'
lugar.localizacao.srid                     # 4326
```

WKT (*Well-Known Text*) é o formato de texto padrão para geometrias e serve
para criar uma a partir de uma string: `GEOSGeometry("POINT(-46.6 -23.5)",
srid=4326)`. GeoJSON é o que você vai devolver em uma API para desenhar em
um mapa no navegador.

Para um polígono, o raciocínio é o mesmo. Um retângulo tosco cobrindo o
Sudeste e a pergunta "quem está dentro?":

```python
from django.contrib.gis.geos import Polygon

sudeste = Polygon.from_bbox((-51.0, -25.5, -39.0, -19.0))  # (xmin, ymin, xmax, ymax)
sudeste.srid = 4326
Lugar.objects.filter(localizacao__within=sudeste)
# <QuerySet [<Lugar: Café da Esquina>, <Lugar: Café do Rio>]>
```

## Tabela de referência rápida

| O que                     | Como                                                                 |
|:--------------------------|:---------------------------------------------------------------------|
| Import dos models         | `from django.contrib.gis.db import models`                           |
| Campo de ponto            | `models.PointField(srid=4326)`                                       |
| Criar um ponto            | `Point(lon, lat, srid=4326)` de `django.contrib.gis.geos`            |
| Distância                 | `D(km=5)` de `django.contrib.gis.measure`                            |
| Perto de                  | `.filter(campo__distance_lte=(ponto, D(km=5)))`                      |
| Ordenar por distância     | `.annotate(d=Distance("campo", ponto)).order_by("d")`                |
| Dentro de uma área        | `.filter(campo__within=poligono)`                                    |
| Admin com mapa            | `class XAdmin(GISModelAdmin)` de `django.contrib.gis.admin`          |
| Centro do mapa do admin   | `gis_widget_kwargs = {"attrs": {"default_lon": ..., "default_lat": ..., "default_zoom": ...}}` |
| Backend do banco          | `django.contrib.gis.db.backends.postgis`                             |
| Ver a tabela no PostGIS   | `docker compose exec db psql -U pontos -d pontos -c "\d lugares_lugar"` |
| GDAL não encontrado (Mac) | `GDAL_LIBRARY_PATH` e `GEOS_LIBRARY_PATH` no `settings.py`           |

## Exercícios

### Exercício 1: o mapa do admin

1. Cadastre pelo admin três lugares da sua cidade, clicando no mapa.
2. Mude `default_lon`, `default_lat` e `default_zoom` para o mapa abrir já
   na sua cidade (procure as coordenadas no OpenStreetMap: o link
   "Compartilhar" mostra latitude e longitude).
3. No shell, imprima o `wkt` de cada um dos lugares cadastrados.

### Exercício 2: o mais próximo

1. No shell, crie um `Point` com a sua localização atual.
2. Liste os lugares ordenados por distância e imprima a distância em metros
   (`lugar.dist.m`).
3. Pegue só o primeiro com `.first()`.

### Exercício 3: a pegadinha da ordem

1. Crie um lugar com as coordenadas de São Paulo **invertidas**:
   `Point(-23.5505, -46.6333, srid=4326)`.
2. Abra-o no admin. Onde o ponto apareceu no mapa? Por quê?
3. Apague-o.

### Exercício 4: polígonos

1. Adicione ao projeto um model `Bairro` com `nome` e
   `area = models.PolygonField(srid=4326)`. Gere e aplique a migração.
2. Registre-o no admin com `GISModelAdmin` e desenhe um bairro em volta de
   um dos seus lugares.
3. No shell, liste os lugares dentro daquele bairro com `__within`, e os
   bairros que contêm um dado ponto com `__contains`.

### Exercício 5: o SQL por trás

1. Rode `print(Lugar.objects.filter(localizacao__distance_lte=(aqui, D(km=500))).query)`
   e encontre a função do PostGIS usada (dica: começa com `ST_`).
2. Copie a consulta e rode-a no `psql` via `docker compose exec`.
3. Rode `EXPLAIN` na frente dela e procure a palavra "Index" no resultado.
   O índice GiST foi usado?

## Referências

- **GeoDjango, visão geral e tutorial oficial**:
  <https://docs.djangoproject.com/en/stable/ref/contrib/gis/> e
  <https://docs.djangoproject.com/en/stable/ref/contrib/gis/tutorial/>.
- **Instalação e bibliotecas (GEOS, GDAL, PROJ), incluindo
  `GDAL_LIBRARY_PATH` e `GEOS_LIBRARY_PATH`**:
  <https://docs.djangoproject.com/en/stable/ref/contrib/gis/install/> e
  <https://docs.djangoproject.com/en/stable/ref/contrib/gis/install/geolibs/>.
- **Campos geográficos e SRID**:
  <https://docs.djangoproject.com/en/stable/ref/contrib/gis/model-api/>.
- **Lookups espaciais e funções (`distance_lte`, `within`, `Distance`)**:
  <https://docs.djangoproject.com/en/stable/ref/contrib/gis/geoquerysets/>,
  <https://docs.djangoproject.com/en/stable/ref/contrib/gis/functions/> e
  <https://docs.djangoproject.com/en/stable/ref/contrib/gis/db-api/>.
- **Objetos GEOS (`Point`, `Polygon`, `GEOSGeometry`, `wkt`, `geojson`)**:
  <https://docs.djangoproject.com/en/stable/ref/contrib/gis/geos/>.
- **Medidas (`D`)**:
  <https://docs.djangoproject.com/en/stable/ref/contrib/gis/measure/>.
- **`GISModelAdmin` e `gis_widget_kwargs`**:
  <https://docs.djangoproject.com/en/stable/ref/contrib/gis/admin/>.
- **Remoção do `GeoManager`** (Django 1.9):
  <https://docs.djangoproject.com/en/1.9/releases/1.9/#geomanager-and-geoqueryset-custom-methods>.
- **Versões mínimas no Django 6.1** (PostGIS 3.2+, GEOS 3.10+, GDAL 3.3+):
  <https://docs.djangoproject.com/en/6.1/releases/6.1/>.
- **PostGIS**: documentação, <https://postgis.net/docs/>; e a página do
  índice espacial, <https://postgis.net/workshops/postgis-intro/indexing.html>.
- **SRID 4326 (WGS 84)**: registro EPSG, <https://epsg.org/crs_4326/WGS-84.html>,
  e a explicação do "por que lon, lat" em
  <https://macwright.com/lonlat/>.
- **GEOS, GDAL e PROJ**: <https://libgeos.org/>, <https://gdal.org/> e
  <https://proj.org/>.
- **Formatos WKT e GeoJSON**: OGC Simple Features,
  <https://www.ogc.org/standards/sfa/>, e RFC 7946,
  <https://datatracker.ietf.org/doc/html/rfc7946>.
- **psycopg 3**: <https://www.psycopg.org/psycopg3/docs/>.
