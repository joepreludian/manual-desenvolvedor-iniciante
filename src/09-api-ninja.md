# Criando APIs: JSON com Django Ninja

## Por que isso importa

No capítulo anterior o `pontos` aprendeu a **consumir** APIs: perguntou o
CEP ao ViaCEP, a coordenada ao Nominatim, o tempo ao Open-Meteo. Agora é a
vez de ele ser consultado. Um aplicativo de celular quer mostrar os lugares
no mapa; uma planilha quer importar a lista de cafés; o script de outra
equipe quer cadastrar lugares novos toda noite. Nenhum deles quer HTML. Eles
querem **dados**, em JSON, numa URL previsível, com regras claras do que
entra e do que sai. Isso é uma **API REST**, e saber construir uma é a
diferença entre um sistema que só serve a si mesmo e um sistema que conversa
com o resto do mundo.

Você até já fez isso, de um jeito artesanal: as views `lugares_geojson` e
`onde` montam dicionários na mão e devolvem com `JsonResponse`. Funciona,
mas cada view repete o mesmo trabalho (ler parâmetro, converter, validar,
devolver erro se vier errado), ninguém documenta o que a API aceita, e quem
for usar precisa ler o código-fonte para descobrir. O **Django Ninja**
resolve esses três problemas de uma vez: você escreve funções Python comuns
com **anotações de tipo**, e ele cuida da conversão, da validação e da
documentação. A documentação, aliás, vem com uma página interativa (o
**Swagger UI**) onde qualquer pessoa testa a API pelo navegador, sem
escrever uma linha de código.

Neste capítulo vamos construir a API do `pontos` do zero: um endpoint de
"olá", parâmetros com validação automática, listagem e detalhe de lugares,
criação e remoção. Vamos entender o que é a especificação **OpenAPI** que
alimenta o Swagger, e por fim proteger as operações de escrita com um
**token** guardado num model do Django, conferido a cada chamada. Tudo
simples, sem truques, no estilo que você já conhece dos capítulos
anteriores.

## O que é REST, afinal

A sigla vem de *Representational State Transfer* e nasceu em 2000, na tese
de doutorado de Roy Fielding, um dos autores da especificação do HTTP. A
ideia dele não foi inventar um protocolo novo, mas descrever o estilo que
fez a web dar certo e dizer: "use isso para APIs também". REST não é um
padrão com certificado; é um conjunto de convenções. As que importam para
nós:

- **Tudo é um recurso, e cada recurso tem uma URL.** Os lugares ficam em
  `/api/lugares`; o lugar de id 4 fica em `/api/lugares/4`. A URL nomeia a
  **coisa** (substantivo), não a ação.
- **A ação é o método HTTP.** `GET` lê, `POST` cria, `PUT`/`PATCH` alteram,
  `DELETE` remove. Em vez de `/api/apagarLugar?id=4`, você faz
  `DELETE /api/lugares/4`.
- **O resultado é o código de status.** `200` deu certo, `201` criou,
  `204` fez e não tem nada a dizer, `400` o pedido veio errado, `401` não
  sei quem você é, `404` não existe, `422` entendi o pedido mas os dados
  não passaram na validação.
- **A representação é JSON.** O recurso no banco é uma linha do Postgres
  com uma geometria; na API ele vira um JSON com `longitude` e `latitude`.
  Quem consome não precisa saber como você guarda.
- **Cada requisição se basta.** O servidor não lembra da anterior. Se é
  preciso provar quem você é, prova-se **em toda chamada** (voltamos a isso
  na autenticação).

A tabela resume o que vamos construir:

| Operação                  | Método e URL                 | Resposta             |
|:--------------------------|:-----------------------------|:---------------------|
| Listar lugares            | `GET /api/lugares`           | `200` + lista JSON   |
| Ver um lugar              | `GET /api/lugares/4`         | `200` + JSON ou `404`|
| Criar um lugar            | `POST /api/lugares` + JSON   | `201` + JSON criado  |
| Apagar um lugar           | `DELETE /api/lugares/4`      | `204` sem corpo      |
| Pedido malformado         | qualquer                     | `422` + lista de erros|
| Sem credencial            | `POST`, `DELETE`             | `401`                |

Repare que a tabela inteira cabe na cabeça. É esse o ganho: quem conhece
uma API REST decente já sabe adivinhar como funciona a próxima.

## Instalando o Django Ninja

O Django Ninja é uma biblioteca pequena que fica em cima do Django e do
**Pydantic**, a biblioteca de validação de dados mais usada em Python. A
ideia central dos dois é a mesma: você descreve o formato dos dados com
anotações de tipo (`nome: str`, `aberto: bool`) e eles fazem o resto.

```bash
uv add django-ninja
# Resolved 11 packages in 424ms
# ...
# Installed 7 packages in 6ms
#  + annotated-types==0.8.0
#  + django-ninja==1.7.1
#  + pydantic==2.14.1
#  + pydantic-core==2.50.1
#  + typing-extensions==4.16.0
#  + typing-inspection==0.4.4
```

Não precisa mexer em `INSTALLED_APPS`: o Ninja não tem models nem
templates próprios para o Django descobrir. Ele é só código Python que você
importa.

### Anotações de tipo, em dois parágrafos

Se você nunca escreveu `def soma(a: int, b: int) -> int`, saiba que o Python
não liga: as anotações não mudam como a função roda. `soma("2", "3")`
continua devolvendo `"23"`. Elas são documentação legível por máquina, e o
Ninja é uma das máquinas que lê. Quando ele vê `a: int`, entende "o
parâmetro `a` vem da URL como texto; converta para inteiro; se não der,
recuse com erro 422".

Outras formas que vão aparecer: `str | None = None` quer dizer "pode ser
texto ou nada, e se não vier é nada" (parâmetro opcional); `list[LugarOut]`
quer dizer "uma lista em que cada item é um `LugarOut`". Só isso.

## O primeiro endpoint

A convenção é concentrar a API num arquivo `api.py` do app. Comece pequeno:

```python
# lugares/api.py
from ninja import NinjaAPI

api = NinjaAPI(
    title="API do pontos",
    version="1.0.0",
    description="Lugares com localização, para outros sistemas consultarem.",
)


@api.get("/ola", tags=["teste"])
def ola(request, nome: str = "mundo"):
    return {"mensagem": f"Olá, {nome}!"}
```

Três coisas para notar. O objeto `api` é o equivalente do `urlpatterns`:
ele acumula as rotas. O decorador `@api.get("/ola")` diz "esta função
responde a `GET /ola`". E a função recebe `request` como primeiro
argumento, igual a uma view, mas o que vem depois são os **parâmetros da
API**: `nome` é um parâmetro de querystring, opcional, com padrão `"mundo"`.
O dicionário devolvido vira JSON.

Monte a API no `urls.py` do projeto, ao lado do admin:

```python
# config/urls.py
from django.contrib import admin
from django.urls import include, path

from lugares.api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("lugares/", include("lugares.urls")),
    path("api/", api.urls),
]
```

Suba o servidor e converse com ele. Como no capítulo de GeoJSON, o `jq`
deixa a resposta legível (sem ele você veria `Olá`, que é o mesmo
texto com o acento escapado):

```bash
uv run python manage.py runserver
```

```bash
curl -s localhost:8000/api/ola | jq -c
# {"mensagem":"Olá, mundo!"}
curl -s 'localhost:8000/api/ola?nome=Ana' | jq -c
# {"mensagem":"Olá, Ana!"}
curl -si localhost:8000/api/ola | head -4
# HTTP/1.1 200 OK
# Date: Wed, 14 Oct 2026 02:16:33 GMT
# Server: WSGIServer/0.2 CPython/3.14.8
# Content-Type: application/json; charset=utf-8
```

Pronto: uma função Python, uma rota, JSON com o `Content-Type` certo. Agora
vamos ver o que acontece entre a URL e a sua função.

```{.mermaid width="70%"}
flowchart TD
  C[Cliente] -->|"GET /api/soma?a=2&b=tres"| U[urls.py]
  U --> A{Autenticação}
  A -->|recusou| E1[401 Unauthorized]
  A -->|ok| V{Validação dos parâmetros}
  V -->|falhou| E2[422 + lista de erros]
  V -->|ok| F[sua função]
  F --> S[Schema de saída]
  S -->|JSON| C
```

A autenticação só existe quando você pede (mais adiante). A validação vem
de graça, e é o próximo assunto.

## Parâmetros: a URL conversa com a função

Acrescente uma função com dois parâmetros obrigatórios:

```python
@api.get("/soma", tags=["teste"])
def soma(request, a: int, b: int):
    return {"a": a, "b": b, "resultado": a + b}
```

Sem valor padrão, o parâmetro é obrigatório. Com `int`, ele é convertido:

```bash
curl -s 'localhost:8000/api/soma?a=2&b=3' | jq -c
# {"a":2,"b":3,"resultado":5}
```

Agora mande algo que não é número, e depois esqueça um parâmetro:

```bash
curl -si 'localhost:8000/api/soma?a=2&b=tres' | sed -n '1p;$p'
# HTTP/1.1 422 Unprocessable Content
# {"detail": [{"type": "int_parsing", "loc": ["query", "b"],
#              "msg": "Input should be a valid integer, unable to parse string as an integer"}]}
curl -s 'localhost:8000/api/soma?a=2' | jq -c
# {"detail":[{"type":"missing","loc":["query","b"],"msg":"Field required"}]}
```

A sua função **nem rodou**. O Ninja leu `b: int`, tentou converter `tres`,
não conseguiu, e respondeu `422` com uma lista de erros dizendo **onde**
(`loc`: na querystring, campo `b`), **o quê** (`type`) e **por quê**
(`msg`). Compare com a view `onde` do capítulo de polígonos, que precisava
de `try`/`except ValueError` e de um `HttpResponseBadRequest` escrito à
mão. Aqui o código de validação simplesmente não existe, e por isso não tem
como estar errado.

Os parâmetros podem vir de três lugares, e a assinatura da função diz de
qual:

| De onde            | Como declarar                                 | Exemplo de URL/corpo                 |
|:-------------------|:----------------------------------------------|:-------------------------------------|
| Querystring        | `nome: str = "mundo"` (sem chaves na rota)    | `/api/ola?nome=Ana`                  |
| Caminho da URL     | `{lugar_id}` na rota e `lugar_id: int`        | `/api/lugares/4`                     |
| Corpo JSON         | `dados: LugarIn` (um `Schema`, ver adiante)   | `POST` com `{"nome": ...}`           |

## Schemas: o formato da resposta

Até agora devolvemos dicionários. Para devolver um `Lugar`, que é um objeto
do Django com uma geometria dentro, precisamos dizer ao Ninja **quais
campos** mostrar e **em que formato**. Isso é um **Schema**: uma classe que
lista campos e tipos. Pense nele como o `ModelForm` da API, só que para a
saída:

```python
# lugares/api.py (continuação)
from ninja import NinjaAPI, Schema

from .models import Lugar


class LugarOut(Schema):
    id: int
    nome: str
    categoria: str
    endereco: str
    aberto: bool
    longitude: float
    latitude: float

    @staticmethod
    def resolve_categoria(lugar):
        return lugar.categoria.nome

    @staticmethod
    def resolve_longitude(lugar):
        return lugar.localizacao.x

    @staticmethod
    def resolve_latitude(lugar):
        return lugar.localizacao.y
```

Para cada campo, o Ninja procura um atributo com o mesmo nome no objeto:
`id`, `nome`, `endereco` e `aberto` saem direto do model. Quando o nome não
existe no objeto, ou existe mas não no formato que você quer, você escreve
um **resolvedor**: um método estático `resolve_<campo>` que recebe o
objeto e devolve o valor. `categoria` no model é um objeto `Categoria`; na
API queremos só o nome. `localizacao` é um `Point`; na API queremos dois
números. O cliente da API nunca fica sabendo que existe PostGIS por trás,
e é assim que deve ser.

Com o schema pronto, a listagem e o detalhe:

```python
from django.shortcuts import get_object_or_404


class Mensagem(Schema):
    detail: str


@api.get("/lugares", response=list[LugarOut], tags=["lugares"])
def listar_lugares(request, categoria: str | None = None, aberto: bool | None = None):
    """Lista os lugares. Os dois filtros são opcionais e podem ser combinados."""
    lugares = Lugar.objects.select_related("categoria")
    if categoria is not None:
        lugares = lugares.filter(categoria__nome=categoria)
    if aberto is not None:
        lugares = lugares.filter(aberto=aberto)
    return lugares


@api.get("/lugares/{lugar_id}", response={200: LugarOut, 404: Mensagem}, tags=["lugares"])
def detalhar_lugar(request, lugar_id: int):
    return get_object_or_404(Lugar, pk=lugar_id)
```

O argumento `response=` fecha o contrato: "esta rota devolve uma lista de
`LugarOut`". Você devolve o queryset e o Ninja converte cada item. Na rota
de detalhe, `response` é um dicionário de código para schema: documenta que
pode sair `200` com um lugar ou `404` com uma mensagem. O
`get_object_or_404` é o mesmo das views; o Ninja apenas transforma o `404`
em JSON em vez de HTML. O `select_related("categoria")`, do capítulo de
Django, evita uma consulta por lugar quando o resolvedor pede
`lugar.categoria.nome`.

```bash
curl -s localhost:8000/api/lugares | jq
# [
#   {
#     "id": 1,
#     "nome": "Café da Esquina",
#     "categoria": "Café",
#     "endereco": "",
#     "aberto": true,
#     "longitude": -46.6333,
#     "latitude": -23.5505
#   },
#   {
#     "id": 3,
#     "nome": "Café do Rio",
#     "categoria": "Café",
#     "endereco": "",
#     "aberto": true,
#     "longitude": -43.1729,
#     "latitude": -22.9068
#   },
#   ...
# ]
curl -s 'localhost:8000/api/lugares?categoria=Caf%C3%A9' | jq -c '[.[].nome]'
# ["Café da Esquina","Café do Rio"]
curl -s 'localhost:8000/api/lugares?aberto=false' | jq -c
# []
curl -s 'localhost:8000/api/lugares?aberto=talvez' | jq -c
# {"detail":[{"type":"bool_parsing","loc":["query","aberto"],"msg":"Input should be a valid boolean, unable to interpret input"}]}
```

O `%C3%A9` é o `é` escapado para a URL, como vimos no capítulo anterior
(o httpx faz isso sozinho com `params=`). O filtro `aberto` aceita `true`/`false`,
`1`/`0`, `yes`/`no` e variantes parecidas; qualquer outra coisa é `422`.

```bash
curl -s localhost:8000/api/lugares/4 | jq -c
# {"id":4,"nome":"MASP","categoria":"Museu","endereco":"","aberto":true,"longitude":-46.6558,"latitude":-23.5614}
curl -si localhost:8000/api/lugares/999 | sed -n '1p;$p'
# HTTP/1.1 404 Not Found
# {"detail": "Not Found: No Lugar matches the given query."}
curl -s localhost:8000/api/lugares/abc | jq -c
# {"detail":[{"type":"int_parsing","loc":["path","lugar_id"],"msg":"Input should be a valid integer, unable to parse string as an integer"}]}
```

Três respostas, três situações diferentes, três códigos diferentes. Quem
consome a API consegue distinguir "não existe" de "você pediu errado" sem
ler texto nenhum, só pelo número.

## Recebendo dados: `POST` com um schema de entrada

Para criar um lugar, o cliente manda um JSON no corpo. O formato desse JSON
também é um `Schema`, e aqui vale separar entrada de saída: quem cria não
manda `id` (o banco gera), mas manda `categoria` como texto e as
coordenadas como dois números.

```python
from django.contrib.gis.geos import Point
from ninja import NinjaAPI, Schema, Status
from ninja.errors import HttpError

from .models import Categoria, Lugar


class LugarIn(Schema):
    nome: str
    categoria: str
    endereco: str = ""
    aberto: bool = True
    longitude: float
    latitude: float


@api.post("/lugares", response={201: LugarOut, 400: Mensagem}, tags=["lugares"])
def criar_lugar(request, dados: LugarIn):
    """Cria um lugar. A categoria precisa existir."""
    try:
        categoria = Categoria.objects.get(nome=dados.categoria)
    except Categoria.DoesNotExist:
        raise HttpError(400, f"Categoria '{dados.categoria}' não existe")
    lugar = Lugar.objects.create(
        nome=dados.nome,
        categoria=categoria,
        endereco=dados.endereco,
        aberto=dados.aberto,
        localizacao=Point(dados.longitude, dados.latitude, srid=4326),
    )
    return Status(201, lugar)
```

Como o parâmetro `dados` é um `Schema`, o Ninja sabe que ele vem do corpo
da requisição. Quando a função roda, `dados` já é um objeto validado:
`dados.nome` é uma string, `dados.longitude` é um `float`, e os campos com
valor padrão (`endereco`, `aberto`) foram preenchidos se o cliente não
mandou. A conversão para o model acontece em um `create` comum, e o
`Point` é o mesmo do capítulo de GeoDjango.

Duas novidades. `HttpError(400, "...")` é o jeito de responder um erro que
**você** detectou (a categoria não existe); o Ninja transforma em
`{"detail": "..."}` com o código pedido. E `Status(201, lugar)` escolhe o
código de sucesso: criar devolve `201 Created`, não `200`. O lugar criado
volta no corpo, passando pelo `LugarOut`, para que o cliente saiba o `id`
que o banco deu.

```bash
curl -s -X POST localhost:8000/api/lugares \
  -H 'Content-Type: application/json' \
  -d '{"nome": "Padaria Estrela", "categoria": "Café", "endereco": "Rua das Flores, 10",
       "longitude": -46.64, "latitude": -23.56, "aberto": false}' | jq
# {
#   "id": 6,
#   "nome": "Padaria Estrela",
#   "categoria": "Café",
#   "endereco": "Rua das Flores, 10",
#   "aberto": false,
#   "longitude": -46.64,
#   "latitude": -23.56
# }
curl -s 'localhost:8000/api/lugares?aberto=false' | jq -c '[.[].nome]'
# ["Padaria Estrela"]
```

E os erros, cada um com seu código:

```bash
# categoria inexistente: erro seu, 400
curl -si -X POST localhost:8000/api/lugares -H 'Content-Type: application/json' \
  -d '{"nome": "Mercado", "categoria": "Mercado", "longitude": -46.64, "latitude": -23.56}' | sed -n '1p;$p'
# HTTP/1.1 400 Bad Request
# {"detail": "Categoria 'Mercado' não existe"}

# campos faltando: erro do Ninja, 422, um item por campo
curl -s -X POST localhost:8000/api/lugares -H 'Content-Type: application/json' \
  -d '{"nome": "Mercado", "categoria": "Café"}' | jq -c '.detail[] | [.loc, .msg]'
# [["body","dados","longitude"],"Field required"]
# [["body","dados","latitude"],"Field required"]

# tipo errado
curl -s -X POST localhost:8000/api/lugares -H 'Content-Type: application/json' \
  -d '{"nome": "Mercado", "categoria": "Café", "longitude": "oeste", "latitude": -23.56}' | jq -c '.detail[0].msg'
# "Input should be a valid number, unable to parse string as a number"
```

Repare em `loc`: `["body", "dados", "longitude"]`. O erro diz que está no
corpo, no parâmetro `dados`, campo `longitude`. Um cliente bem escrito usa
isso para marcar o campo certo do formulário.

### `DELETE`: fez e não tem o que dizer

```python
@api.delete("/lugares/{lugar_id}", response={204: None, 404: Mensagem}, tags=["lugares"])
def apagar_lugar(request, lugar_id: int):
    lugar = get_object_or_404(Lugar, pk=lugar_id)
    lugar.delete()
    return Status(204, None)
```

`204 No Content` é a resposta certa para "apaguei": sucesso, corpo vazio.
Por isso `response={204: None}`.

```bash
curl -si -X DELETE localhost:8000/api/lugares/6 | sed -n '1p'
# HTTP/1.1 204 No Content
curl -si -X DELETE localhost:8000/api/lugares/6 | sed -n '1p;$p'
# HTTP/1.1 404 Not Found
# {"detail": "Not Found: No Lugar matches the given query."}
```

A segunda chamada dá `404` porque o lugar já não existe. É o
comportamento esperado de REST: a mesma URL, o mesmo verbo, e a resposta
reflete o estado atual.

Você acabou de perceber o problema: **qualquer pessoa** na internet pode
criar e apagar lugares. Vamos resolver isso daqui a pouco. Antes, a parte
que faz o Django Ninja valer a pena mesmo quando você escreve uma API de
três rotas.

## Documentação de graça: OpenAPI e Swagger

Abra `http://localhost:8000/api/docs` no navegador. Você vai ver uma
página com o título "API do pontos", a descrição que passou ao `NinjaAPI`,
e as rotas agrupadas pelas `tags` que usou: **teste** com `/api/ola` e
`/api/soma`, **lugares** com as quatro operações. Cada uma abre e mostra os
parâmetros, com tipo e se é obrigatório, as respostas possíveis com o
formato de cada uma, e um botão **Try it out** que monta e envia a
requisição dali mesmo, mostrando o `curl` equivalente, o código e o corpo
da resposta. A docstring de cada função aparece como descrição; o nome da
função, em título ("Listar Lugares"), como resumo.

Você não escreveu nada disso. Essa página é o **Swagger UI**, um
visualizador genérico, e o que ele visualiza é um arquivo JSON que o Ninja
gera a partir do seu código:

```bash
curl -s localhost:8000/api/openapi.json | jq '{openapi, info, paths: (.paths | keys)}'
# {
#   "openapi": "3.1.0",
#   "info": {
#     "title": "API do pontos",
#     "version": "1.0.0",
#     "description": "Lugares com localização, para outros sistemas consultarem."
#   },
#   "paths": [
#     "/api/lugares",
#     "/api/lugares/{lugar_id}",
#     "/api/ola",
#     "/api/soma"
#   ]
# }
```

Esse arquivo segue a **especificação OpenAPI**, um padrão aberto para
descrever APIs HTTP: quais URLs existem, que métodos aceitam, que
parâmetros, que corpo, que respostas, que autenticação. A especificação
começou em 2010 com o nome **Swagger**, dentro de uma empresa; em 2015 foi
doada à Linux Foundation e renomeada OpenAPI, e a palavra Swagger ficou
para as ferramentas (Swagger UI, Swagger Editor). Hoje é o jeito universal
de descrever uma API. Veja como a rota de detalhe ficou descrita:

```bash
curl -s localhost:8000/api/openapi.json | jq '.paths["/api/lugares/{lugar_id}"].get'
# {
#   "operationId": "lugares_api_detalhar_lugar",
#   "summary": "Detalhar Lugar",
#   "parameters": [
#     {
#       "in": "path",
#       "name": "lugar_id",
#       "schema": {
#         "title": "Lugar Id",
#         "type": "integer"
#       },
#       "required": true
#     }
#   ],
#   "responses": {
#     "200": {
#       "description": "OK",
#       "content": {
#         "application/json": {
#           "schema": {
#             "$ref": "#/components/schemas/LugarOut"
#           }
#         }
#       }
#     },
#     "404": {
#       "description": "Not Found",
#       "content": {
#         "application/json": {
#           "schema": {
#             "$ref": "#/components/schemas/Mensagem"
#           }
#         }
#       }
#     }
#   },
#   "tags": [
#     "lugares"
#   ]
# }
```

Tudo veio de `@api.get("/lugares/{lugar_id}", response={200: LugarOut,
404: Mensagem})` e de `lugar_id: int`. E o `LugarIn` virou isto:

```bash
curl -s localhost:8000/api/openapi.json | jq -c '.components.schemas.LugarIn | {required, campos: (.properties | keys)}'
# {"required":["nome","categoria","longitude","latitude"],"campos":["aberto","categoria","endereco","latitude","longitude","nome"]}
```

Os campos com valor padrão não estão em `required`. Isso importa porque o
arquivo OpenAPI não serve só para a página bonita: existem ferramentas que
leem esse JSON e **geram** um cliente em Python, TypeScript, Java ou o que
for, com uma classe `LugarIn` e um método `criar_lugar` prontos. O
aplicativo de celular que citamos no início pode ser escrito sem que
ninguém leia o seu código Django. É o código que documenta, e a
documentação nunca fica desatualizada, porque é gerada toda vez.

Duas opções úteis do `NinjaAPI`: `docs_url=None` esconde a página mas
mantém o JSON; `openapi_url=None` desliga os dois. Em produção, decida
conscientemente; na maioria dos casos a documentação pública é uma
vantagem.

## Autenticação: um token guardado no banco

Hora de fechar a porta. A ideia mais simples seria pedir usuário e senha
em toda chamada, mas isso significa que o script da outra equipe teria a
**senha** de alguém gravada em algum lugar, com o poder de entrar no admin
e trocar a senha. Em vez disso, as APIs usam **tokens**: uma string longa
e aleatória, gerada pelo sistema, que vale só para a API e pode ser
revogada sem mexer na senha de ninguém. Você usou um no capítulo anterior
(`Authorization: Bearer ...`); agora vai emitir e conferir o seu.

### O model

Um token é uma linha no banco: a quem pertence, qual é a chave, se ainda
vale.

```python
# lugares/models.py
import secrets

from django.conf import settings
from django.contrib.gis.db import models


def gerar_chave():
    """Uma chave aleatória, longa e impossível de adivinhar."""
    return secrets.token_urlsafe(32)


class TokenDeAPI(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tokens"
    )
    chave = models.CharField(max_length=64, unique=True, default=gerar_chave)
    descricao = models.CharField("descrição", max_length=100, blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "token de API"
        verbose_name_plural = "tokens de API"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.descricao or 'token'} de {self.usuario}"
```

O módulo `secrets` da biblioteca padrão existe exatamente para isso: gerar
segredos com aleatoriedade boa para segurança (o `random` não serve).
`token_urlsafe(32)` devolve 43 caracteres de letras, números, `-` e `_`,
seguros para viajar numa URL ou num cabeçalho. Passar a **função** (sem
parênteses) como `default` faz o Django chamá-la a cada token novo. O
`settings.AUTH_USER_MODEL` é o jeito certo de apontar para o usuário, em
vez de importar `User` direto. E `ativo` permite revogar: desligar o token
sem apagar o histórico.

```bash
uv run python manage.py makemigrations lugares
# Migrations for 'lugares':
#   lugares/migrations/0002_tokendeapi.py
#     + Create model TokenDeAPI
uv run python manage.py migrate
# Running migrations:
#   Applying lugares.0002_tokendeapi... OK
```

Registre no admin, com a chave só para leitura (ninguém deve digitar uma
chave; ela é gerada):

```python
# lugares/admin.py
from .models import Bairro, Categoria, Lugar, TokenDeAPI


@admin.register(TokenDeAPI)
class TokenDeAPIAdmin(admin.ModelAdmin):
    list_display = ["descricao", "usuario", "ativo", "criado_em"]
    list_filter = ["ativo"]
    readonly_fields = ["chave", "criado_em"]
```

Crie um token para o usuário que você fez com `createsuperuser` (pelo
admin, em "Tokens de API", ou pelo shell):

```bash
uv run python manage.py shell
```

```python
from django.contrib.auth import get_user_model
from lugares.models import TokenDeAPI

usuario = get_user_model().objects.get(username="admin")
token = TokenDeAPI.objects.create(usuario=usuario, descricao="script de importação")
print(token)
# script de importação de admin
print(token.chave)
# bgEQ2_GKArPlK6qpLIhheeSylLrmdLHvN6L-ap4inl4
print(len(token.chave))
# 43
```

A sua chave será outra, claro. Trate-a como senha: ela vai para a variável
de ambiente do script que consome a API (capítulo anterior, "Onde guardar
credenciais"), nunca para o código.

### A classe de autenticação

O Ninja tem classes prontas para cada esquema de autenticação do HTTP. A
que lê `Authorization: Bearer <chave>` chama-se `HttpBearer`, e ela só
pede que você escreva **um método**: dado o token que veio no cabeçalho,
quem é essa pessoa?

```python
# lugares/autenticacao.py
from ninja.security import HttpBearer

from .models import TokenDeAPI


class AutenticacaoPorToken(HttpBearer):
    """Aceita `Authorization: Bearer <chave>` se a chave existir e estiver ativa."""

    def authenticate(self, request, token):
        try:
            registro = TokenDeAPI.objects.get(chave=token, ativo=True)
        except TokenDeAPI.DoesNotExist:
            return None
        return registro.usuario
```

O contrato é simples: devolva algo verdadeiro (aqui, o usuário dono do
token) e a chamada continua, com esse valor disponível em `request.auth`;
devolva `None` e o Ninja responde `401` antes de chegar na sua função. A
`HttpBearer` cuida do resto: se o cabeçalho não veio, ou veio sem a
palavra `Bearer`, ela nem chama o seu método. Repare que é **uma consulta
ao banco por chamada**, e está tudo bem: é simples, é correto, e se um dia
virar gargalo você mede antes de otimizar.

Agora aplique nas rotas de escrita, com `auth=`:

```python
# lugares/api.py
from .autenticacao import AutenticacaoPorToken


@api.post(
    "/lugares",
    response={201: LugarOut, 400: Mensagem, 401: Mensagem},
    auth=AutenticacaoPorToken(),
    tags=["lugares"],
)
def criar_lugar(request, dados: LugarIn):
    ...


@api.delete(
    "/lugares/{lugar_id}",
    response={204: None, 401: Mensagem, 404: Mensagem},
    auth=AutenticacaoPorToken(),
    tags=["lugares"],
)
def apagar_lugar(request, lugar_id: int):
    ...
```

As leituras (`GET`) continuam públicas de propósito: o mapa e o aplicativo
precisam delas sem login. Se quisesse proteger tudo, passaria
`auth=AutenticacaoPorToken()` ao `NinjaAPI(...)` e liberaria uma rota ou
outra com `auth=None`.

```bash
# sem cabeçalho
curl -si -X POST localhost:8000/api/lugares -H 'Content-Type: application/json' \
  -d '{"nome": "Padaria Estrela", "categoria": "Café", "longitude": -46.64, "latitude": -23.56}' | sed -n '1p;$p'
# HTTP/1.1 401 Unauthorized
# {"detail": "Unauthorized"}

# chave inventada
curl -s -X POST localhost:8000/api/lugares -H 'Authorization: Bearer chave-inventada' \
  -H 'Content-Type: application/json' \
  -d '{"nome": "Padaria Estrela", "categoria": "Café", "longitude": -46.64, "latitude": -23.56}' | jq -c
# {"detail":"Unauthorized"}

# a chave certa
export PONTOS_TOKEN=bgEQ2_GKArPlK6qpLIhheeSylLrmdLHvN6L-ap4inl4
curl -s -X POST localhost:8000/api/lugares -H "Authorization: Bearer $PONTOS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"nome": "Padaria Estrela", "categoria": "Café", "endereco": "Rua das Flores, 10",
       "longitude": -46.64, "latitude": -23.56, "aberto": false}' | jq -c
# {"id":7,"nome":"Padaria Estrela","categoria":"Café","endereco":"Rua das Flores, 10","aberto":false,"longitude":-46.64,"latitude":-23.56}
curl -si -X DELETE localhost:8000/api/lugares/7 | sed -n '1p'
# HTTP/1.1 401 Unauthorized
curl -si -X DELETE localhost:8000/api/lugares/7 -H "Authorization: Bearer $PONTOS_TOKEN" | sed -n '1p'
# HTTP/1.1 204 No Content
```

Note que a mensagem de erro é a mesma para "sem token" e "token errado".
Isso é de propósito: a API não deve ajudar quem está tentando adivinhar.
E revogar é desligar o `ativo` no admin (ou no shell):

```bash
curl -s -X POST localhost:8000/api/lugares -H "Authorization: Bearer $PONTOS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"nome": "X", "categoria": "Café", "longitude": -46.64, "latitude": -23.56}' | jq -c
# {"detail":"Unauthorized"}
```

Volte ao `/api/docs`. As duas rotas protegidas ganharam um cadeado, e no
topo apareceu o botão **Authorize**: cole a chave ali e o "Try it out"
passa a mandar o cabeçalho sozinho. Isso também veio do OpenAPI:

```bash
curl -s localhost:8000/api/openapi.json | jq -c '.components.securitySchemes'
# {"AutenticacaoPorToken":{"type":"http","scheme":"bearer"}}
```

Um detalhe honesto: estamos guardando a chave em texto puro no banco, como
fizemos para manter o capítulo simples. Se alguém copiar a tabela, tem
todos os tokens. Sistemas maiores guardam um **hash** da chave (como o
Django faz com senhas) e mostram a chave em claro uma única vez, na
criação. Fica como exercício; a estrutura é a mesma.

### E o login com usuário e senha?

Para **pessoas** no navegador, a resposta já existe: a sessão do Django,
a mesma que o admin usa. O Ninja a expõe como `django_auth`, e `auth=`
aceita uma lista, que ele testa em ordem:

```python
from ninja.security import django_auth


@api.get("/quem-sou", auth=[AutenticacaoPorToken(), django_auth], tags=["teste"])
def quem_sou(request):
    """Diz quem está autenticado, por token ou pela sessão do navegador."""
    return {"usuario": request.auth.username}
```

Um script passa o token; uma pessoa logada no admin abre `/api/docs` na
mesma aba e o "Try it out" funciona pelo cookie de sessão. Nos dois casos
`request.auth` é o usuário, porque foi isso que o `authenticate` devolveu.

```bash
curl -si localhost:8000/api/quem-sou | sed -n '1p'
# HTTP/1.1 401 Unauthorized
curl -s localhost:8000/api/quem-sou -H "Authorization: Bearer $PONTOS_TOKEN" | jq -c
# {"usuario":"admin"}
```

Usuário e senha **a cada chamada** (o Basic do capítulo anterior) também
existe no Ninja (`HttpBasicAuth`), mas evite: além de espalhar a senha,
obriga o Django a recalcular o hash dela em toda requisição, e isso é lento
de propósito.

## Testando a API

Os endpoints são views do Django, então o `Client` de testes que você já
usa funciona sem nada extra. Ele serializa um dicionário como JSON quando
você passa `content_type="application/json"`, e aceita cabeçalhos em
`headers=`:

```python
# lugares/tests.py
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.test import TestCase

from .models import Categoria, Lugar, TokenDeAPI


class ApiLugaresTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nome="Café")
        self.lugar = Lugar.objects.create(
            nome="Café Teste",
            categoria=self.categoria,
            localizacao=Point(-46.63, -23.55, srid=4326),
        )
        usuario = get_user_model().objects.create_user("ana", password="segredo")
        self.token = TokenDeAPI.objects.create(usuario=usuario, descricao="testes")
        self.novo_lugar = {
            "nome": "Padaria Estrela",
            "categoria": "Café",
            "longitude": -46.64,
            "latitude": -23.56,
        }

    def test_lista_lugares(self):
        resposta = self.client.get("/api/lugares")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.json()), 1)
        self.assertEqual(resposta.json()[0]["nome"], "Café Teste")

    def test_detalhe_inexistente_da_404(self):
        resposta = self.client.get("/api/lugares/999")
        self.assertEqual(resposta.status_code, 404)

    def test_criar_sem_token_e_negado(self):
        resposta = self.client.post(
            "/api/lugares", self.novo_lugar, content_type="application/json"
        )
        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(Lugar.objects.count(), 1)

    def test_criar_com_token(self):
        resposta = self.client.post(
            "/api/lugares",
            self.novo_lugar,
            content_type="application/json",
            headers={"Authorization": f"Bearer {self.token.chave}"},
        )
        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(resposta.json()["categoria"], "Café")
        self.assertEqual(Lugar.objects.count(), 2)

    def test_token_desativado_e_negado(self):
        self.token.ativo = False
        self.token.save()
        resposta = self.client.post(
            "/api/lugares",
            self.novo_lugar,
            content_type="application/json",
            headers={"Authorization": f"Bearer {self.token.chave}"},
        )
        self.assertEqual(resposta.status_code, 401)
```

```bash
uv run python manage.py test lugares.tests.ApiLugaresTests
# Found 5 test(s).
# .....
# ----------------------------------------------------------------------
# Ran 5 tests in 0.935s
#
# OK
```

Repare no que cada teste protege: a listagem, o `404`, e os três caminhos
da autenticação (sem token, com token, token revogado). O teste de "sem
token" ainda confere que **nada foi gravado**: um `401` que deixasse o
lugar criado seria pior do que não ter autenticação. O Ninja também traz
um `ninja.testing.TestClient` que chama a função direto, sem passar pelas
URLs e pelo middleware; é mais rápido, mas o `Client` do Django testa o
caminho inteiro, que é o que o usuário percorre.

## Tabela de referência rápida

| O que                          | Como                                                                       |
|:-------------------------------|:---------------------------------------------------------------------------|
| Instalar                       | `uv add django-ninja`                                                      |
| Criar a API                    | `api = NinjaAPI(title=..., version=..., description=...)` em `app/api.py`  |
| Montar no projeto              | `path("api/", api.urls)` em `config/urls.py`                               |
| Rota                           | `@api.get("/x")`, `@api.post`, `@api.patch`, `@api.delete`                 |
| Parâmetro de querystring       | `def f(request, nome: str = "x")` (opcional) ou `nome: str` (obrigatório)  |
| Parâmetro opcional             | `categoria: str` ou `None`, com `= None` no fim (veja `listar_lugares`)    |
| Parâmetro de caminho           | `"/lugares/{lugar_id}"` e `lugar_id: int`                                  |
| Corpo JSON                     | `dados: LugarIn`, com `class LugarIn(Schema)`                              |
| Formato da resposta            | `response=LugarOut`, `response=list[LugarOut]`                             |
| Vários códigos                 | `response={200: LugarOut, 404: Mensagem}`; `return Status(201, obj)`       |
| Sem corpo                      | `response={204: None}`; `return Status(204, None)`                         |
| Campo calculado no schema      | `@staticmethod def resolve_campo(obj): ...`                                |
| Erro seu                       | `raise HttpError(400, "mensagem")` devolve `{"detail": "mensagem"}`        |
| Erro de validação              | automático, `422`, `{"detail": [{"loc", "msg", "type"}]}`                  |
| 404                            | `get_object_or_404` funciona; vira JSON                                    |
| Agrupar na documentação        | `tags=["lugares"]`; docstring vira descrição; nome da função vira resumo   |
| Documentação                   | `/api/docs` (Swagger UI), `/api/openapi.json` (OpenAPI 3.1)                |
| Esconder documentação          | `NinjaAPI(docs_url=None)` ou `NinjaAPI(openapi_url=None)`                  |
| Token no banco                 | model com `chave = CharField(unique=True, default=gerar_chave)`, `ativo`   |
| Gerar chave                    | `secrets.token_urlsafe(32)`                                                |
| Classe de autenticação         | `class X(HttpBearer): def authenticate(self, request, token): ...`         |
| Proteger rota / API inteira    | `@api.post(..., auth=X())` / `NinjaAPI(auth=X())` e `auth=None` para abrir |
| Sessão do navegador            | `auth=django_auth`; lista `auth=[X(), django_auth]` tenta em ordem         |
| Quem está autenticado          | `request.auth` (o que `authenticate` devolveu)                             |
| Testar                         | `self.client.post(url, dados, content_type="application/json", headers={...})` |

## Exercícios

### Exercício 1: abrir e fechar

1. Crie `PATCH /api/lugares/{lugar_id}` que altera só `aberto` e
   `endereco`. O schema de entrada deve ter os dois campos opcionais
   (`aberto: bool | None = None`); altere no model apenas o que veio.
2. Proteja com o token e devolva o lugar atualizado com `LugarOut`.
3. Escreva um teste que manda só `{"aberto": false}` e confere que o
   `endereco` não mudou.

### Exercício 2: categorias como recurso

1. Crie `GET /api/categorias` (lista) e `POST /api/categorias` (cria,
   protegido). Devolva `400` se o nome já existir.
2. Mude `LugarOut` para que `categoria` seja um objeto `{"id": 1, "nome":
   "Café"}` em vez de texto, usando um schema aninhado `CategoriaOut`.
3. Veja no `/api/docs` como o `LugarOut` mudou em "Schemas".

### Exercício 3: a caixa no mapa

1. Acrescente a `GET /api/lugares` um filtro `bbox` como o do capítulo de
   GeoJSON: uma string `"lon1,lat1,lon2,lat2"`.
2. Converta em quatro `float` e filtre com `localizacao__within` e
   `Polygon.from_bbox`. Se a string não tiver quatro números, responda
   `422` com `HttpError` (ou descubra como declarar `bbox: list[float]`
   e deixar o Ninja validar).
3. Teste com a mesma caixa de São Paulo do capítulo de GeoJSON.

### Exercício 4: um comando para emitir tokens

1. Crie o comando `criar_token --usuario ana --descricao "aplicativo"`,
   que cria o `TokenDeAPI` e imprime a chave **uma vez**.
2. Faça o comando falhar com `CommandError` se o usuário não existir.
3. Acrescente `revogar_token <chave>` que desliga o `ativo`.

### Exercício 5: tokens que expiram

1. Acrescente `expira_em = DateTimeField(null=True, blank=True)` ao model.
2. Em `authenticate`, recuse o token se `expira_em` já passou
   (`django.utils.timezone.now()`).
3. Teste os dois casos: token sem validade e token vencido.

### Exercício 6: o seu próprio cliente

1. Com o httpx do capítulo anterior, escreva `PontosClient`, uma classe
   com `listar(categoria=None)`, `criar(nome, categoria, lon, lat)` e
   `apagar(id)`, lendo o token de uma variável de ambiente.
2. Trate `401` como uma exceção própria `TokenInvalido`.
3. Teste sem rede com `MockTransport`, incluindo o caso `401`.

## Referências

- **Django Ninja, documentação**: <https://django-ninja.dev/>.
- **Django Ninja, parâmetros de caminho, querystring e corpo**:
  <https://django-ninja.dev/guide/path-params/>,
  <https://django-ninja.dev/guide/query-params/>,
  <https://django-ninja.dev/guide/body/>.
- **Django Ninja, schemas e resolvedores**:
  <https://django-ninja.dev/guide/schemas/>,
  <https://django-ninja.dev/guide/model-schema/>.
- **Django Ninja, respostas (`response=`, vários códigos, `Status`)**:
  <https://django-ninja.dev/guide/responses/>.
- **Django Ninja, erros (`HttpError`, formato do `422`)**:
  <https://django-ninja.dev/guide/errors/>.
- **Django Ninja, autenticação (`HttpBearer`, `APIKeyHeader`,
  `django_auth`)**: <https://django-ninja.dev/guide/authentication/>.
- **Django Ninja, OpenAPI e documentação**:
  <https://django-ninja.dev/guide/openapi/>,
  <https://django-ninja.dev/guide/operations/>.
- **Django Ninja, testes**: <https://django-ninja.dev/guide/testing/>.
- **Pydantic**: <https://pydantic.dev/docs/validation/latest/get-started/>.
- **Especificação OpenAPI**: <https://spec.openapis.org/oas/latest.html>,
  <https://www.openapis.org/>.
- **Swagger UI**: <https://github.com/swagger-api/swagger-ui>.
- **REST, a tese de Roy Fielding (capítulo 5)**:
  <https://ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm>.
- **Métodos HTTP e códigos de status (MDN)**:
  <https://developer.mozilla.org/pt-BR/docs/Web/HTTP/Reference/Methods>,
  <https://developer.mozilla.org/pt-BR/docs/Web/HTTP/Reference/Status>.
- **Python, módulo `secrets`**:
  <https://docs.python.org/pt-br/3/library/secrets.html>.
- **Python, anotações de tipo**:
  <https://docs.python.org/pt-br/3/library/typing.html>.
- **Django, `AUTH_USER_MODEL`**:
  <https://docs.djangoproject.com/en/stable/topics/auth/customizing/#referencing-the-user-model>.
- **Django, cliente de testes (`headers`, `content_type`)**:
  <https://docs.djangoproject.com/en/stable/topics/testing/tools/#django.test.Client.post>.
