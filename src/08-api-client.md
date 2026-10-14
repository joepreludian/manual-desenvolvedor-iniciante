# Consumindo APIs: um cliente HTTP com httpx

## Por que isso importa

Até aqui o projeto `pontos` só **respondeu** requisições: alguém abre o mapa,
o navegador pede `api/lugares.geojson`, o Django devolve. Mas quase nenhum
sistema de verdade vive sozinho. Mais cedo ou mais tarde o seu código
precisa **perguntar** alguma coisa a outro sistema: o CEP que o cliente
digitou é de qual cidade? Qual é a coordenada deste endereço? Vai chover
na hora da entrega? O boleto foi pago? Cada uma dessas perguntas é feita a
uma **API** de outra empresa ou de outra equipe, pela internet, usando o
mesmo HTTP que o seu Django já fala.

Neste capítulo o `pontos` deixa de ser só servidor e vira também
**cliente**. A ferramenta é o **httpx**, uma biblioteca Python para fazer
requisições HTTP. Vamos começar pelo básico (uma URL, uma resposta), passar
por tudo o que uma requisição carrega (querystring, cabeçalhos, método,
corpo), aprender a lidar com erro e timeout, e terminar com uma classe que
encapsula o acesso a uma API de verdade: o Nominatim, o geocodificador do
OpenStreetMap, que transforma "Avenida Paulista, 1578" em latitude e
longitude. Essa classe ganha um comando de gerenciamento e testes que não
dependem da internet.

Por fim, um assunto que todo iniciante aprende do jeito mais caro: **onde
guardar as chaves** que as APIs exigem. Chave no código vai parar no git, e
do git não sai mais. Vamos ver o problema acontecer e as duas formas certas
de evitar.

Todas as APIs do capítulo são públicas e funcionam sem cadastro, então
você pode rodar cada bloco enquanto lê. Os resultados impressos foram
obtidos de verdade; os seus podem variar um pouco (a temperatura de São
Paulo muda, os servidores mudam de versão), e isso é parte da lição.

## Uma requisição por dentro

Antes de escrever Python, vale olhar uma conversa HTTP crua. O `curl -i`
mostra a resposta inteira, cabeçalhos incluídos, do ViaCEP, um serviço
gratuito que devolve o endereço de um CEP:

```bash
curl -i https://viacep.com.br/ws/01310100/json/
# HTTP/1.1 200 OK
# Server: nginx/1.22.0
# Date: Tue, 13 Oct 2026 21:46:33 GMT
# Content-Type: application/json; charset=utf-8
# Cache-Control: max-age=3600
# Access-Control-Allow-Origin: *
# ...
#
# {
#   "cep": "01310-100",
#   "logradouro": "Avenida Paulista",
#   "complemento": "de 612 a 1510 - lado par",
#   "bairro": "Bela Vista",
#   "localidade": "São Paulo",
#   "uf": "SP",
#   "ibge": "3550308",
#   "ddd": "11",
#   ...
# }
```

Toda requisição HTTP tem a mesma anatomia, e toda resposta também:

```{.mermaid width="85%"}
sequenceDiagram
    participant C as Seu código (httpx)
    participant S as Servidor da API
    C->>S: GET /ws/01310100/json/?chave=valor
    Note over C,S: Host: viacep.com.br<br/>User-Agent: pontos/1.0<br/>Accept: application/json<br/>(corpo, se houver)
    S-->>C: 200 OK
    Note over C,S: Content-Type: application/json<br/>Cache-Control: max-age=3600<br/>{"cep": "01310-100", ...}
```

- **Método**: o verbo. `GET` lê, `POST` cria, `PUT`/`PATCH` alteram,
  `DELETE` apaga. É o mesmo `request.method` que você testou nas views.
- **URL**: o caminho do recurso e, depois do `?`, a **querystring**,
  pares `chave=valor` para filtrar, paginar, escolher formato.
- **Cabeçalhos** (*headers*): metadados sobre a requisição ou a resposta.
  Quem está pedindo (`User-Agent`), o que aceita receber (`Accept`), o
  tipo do corpo (`Content-Type`), credenciais (`Authorization`).
- **Corpo** (*body*): os dados em si. `GET` normalmente não tem; `POST`
  leva o JSON do que está sendo criado; a resposta traz o resultado.
- **Status**: o número que resume o que aconteceu. `2xx` deu certo, `3xx`
  foi redirecionado, `4xx` o erro é seu, `5xx` o erro é do servidor.

Uma API HTTP é só uma convenção sobre esses cinco elementos: quais
caminhos existem, quais parâmetros aceitam, qual formato devolvem. A
**documentação** da API é onde essa convenção está escrita, e lê-la é
sempre o primeiro passo. Tudo o que o httpx faz é montar essas peças por
você e desmontar a resposta.

## httpx: o primeiro GET

Python traz o módulo `urllib` na biblioteca padrão, mas ele é verboso e
baixo nível. Por muitos anos a resposta foi a biblioteca `requests`; o
httpx nasceu com a mesma interface simples e acrescentou o que faltava:
HTTP/2, suporte a `async`, timeouts por padrão e um modo de teste sem rede
que vamos usar no fim do capítulo. Se você já viu código com `requests`,
quase tudo é igual.

Instale no projeto:

```bash
uv add httpx
uv run python -c "import httpx; print(httpx.__version__)"
# 0.28.1
```

E refaça o `curl` em Python, num `uv run python`:

```python
import httpx

resposta = httpx.get("https://viacep.com.br/ws/01310100/json/")
print(resposta)
# <Response [200 OK]>
print(resposta.status_code)
# 200
print(resposta.headers["content-type"])
# application/json; charset=utf-8
print(type(resposta.text), resposta.text[:40])
# <class 'str'> {
#   "cep": "01310-100",
#   "logradouro":
dados = resposta.json()
print(type(dados))
# <class 'dict'>
print(dados["logradouro"], "-", dados["bairro"], "-", dados["localidade"])
# Avenida Paulista - Bela Vista - São Paulo
```

Repare na diferença entre `.text` e `.json()`. O primeiro é a resposta
crua, uma string; o segundo interpreta essa string como JSON e devolve
dicionários e listas Python, prontos para indexar. Se o corpo não for JSON
válido, `.json()` levanta um erro; é por isso que a gente confere o
`Content-Type` (ou o status) antes de confiar nele.

O objeto `resposta` guarda também a **requisição** que o gerou, e vale
espiar o que o httpx mandou sem você pedir:

```python
print(resposta.request.method, resposta.request.url)
# GET https://viacep.com.br/ws/01310100/json/
print(resposta.request.headers)
# Headers({'host': 'viacep.com.br', 'accept': '*/*', 'accept-encoding': 'gzip, deflate',
#          'connection': 'keep-alive', 'user-agent': 'python-httpx/0.28.1'})
```

Cinco cabeçalhos automáticos. O `user-agent` padrão, `python-httpx/0.28.1`,
vai nos causar um problema daqui a pouco.

### Duas APIs, dois formatos

A BrasilAPI responde a mesma pergunta, mas o JSON tem outra cara: chaves em
inglês, e, nessa versão, até coordenadas:

```python
r = httpx.get("https://brasilapi.com.br/api/cep/v2/01310100")
print(r.status_code)
# 200
print(r.json())
# {'cep': '01310100', 'state': 'SP', 'city': 'São Paulo', 'neighborhood': 'Bela Vista',
#  'street': 'Avenida Paulista', 'service': 'open-cep', ...,
#  'location': {'type': 'Point', 'coordinates': {'longitude': '-46.63611', 'latitude': '-23.5475'}}}
```

E as duas discordam sobre o que fazer quando o CEP não existe:

```python
r = httpx.get("https://viacep.com.br/ws/00000000/json/")
print(r.status_code, r.json())
# 200 {'erro': 'true'}
r = httpx.get("https://brasilapi.com.br/api/cep/v2/00000000")
print(r.status_code, r.json())
# 404 {'name': 'CepPromiseError', 'message': 'Todos os serviços de CEP retornaram erro.', ...}
```

A BrasilAPI usa o HTTP como manda o figurino: `404`, não achei. O ViaCEP
devolve `200 OK` com um `{"erro": "true"}` dentro (e repare: a string
`"true"`, não o booleano). Nenhuma das duas está "errada"; cada API tem
suas convenções, e o seu código precisa conhecer as da API que usa. Isso é
o primeiro argumento para encapsular o acesso numa classe, como faremos
adiante: quem chama a classe não deveria precisar saber dessas manias.

## Querystring: `params`

Quase toda API aceita parâmetros na URL. Dá para montar a string na mão
com uma f-string, mas isso quebra na primeira vírgula, espaço ou acento.
O httpx monta e **escapa** a querystring por você a partir de um
dicionário. A Open-Meteo, uma API de previsão do tempo sem cadastro, serve
de exemplo com a coordenada do Café da Esquina:

```python
r = httpx.get(
    "https://api.open-meteo.com/v1/forecast",
    params={
        "latitude": -23.5505,
        "longitude": -46.6333,
        "current": ["temperature_2m", "relative_humidity_2m"],
        "timezone": "America/Sao_Paulo",
    },
)
print(r.url)
# https://api.open-meteo.com/v1/forecast?latitude=-23.5505&longitude=-46.6333
#   &current=temperature_2m&current=relative_humidity_2m&timezone=America%2FSao_Paulo
print(r.json()["current"])
# {'time': '2026-10-13T18:45', 'interval': 900, 'temperature_2m': 21.1, 'relative_humidity_2m': 77}
print(r.json()["current_units"])
# {'time': 'iso8601', 'interval': 'seconds', 'temperature_2m': '°C', 'relative_humidity_2m': '%'}
```

Três coisas aconteceram na URL impressa. Números viraram texto. A lista
`current` virou **dois** parâmetros com o mesmo nome, que é a convenção
mais comum para listas (algumas APIs preferem `a,b` numa string só; leia a
documentação). E a barra de `America/Sao_Paulo` virou `%2F`, porque uma
barra crua mudaria o caminho. Esse escape chama-se *percent-encoding*, e é
fácil ver como ele trata acentos e símbolos:

```python
print(httpx.URL("https://exemplo.com/busca", params={"q": "café & pão", "pagina": 2}))
# https://exemplo.com/busca?q=caf%C3%A9+%26+p%C3%A3o&pagina=2
```

Sem o escape, o `&` do meio de `café & pão` seria lido pelo servidor como
o separador entre dois parâmetros. Deixe o httpx fazer isso sempre.

## Cabeçalhos: quem é você?

O Nominatim, geocodificador do OpenStreetMap, é mantido por voluntários e
tem uma política de uso: identifique a sua aplicação com um `User-Agent`
próprio e não passe de uma requisição por segundo. Ele leva isso a sério.
Com o `User-Agent` padrão do httpx:

```python
URL = "https://nominatim.openstreetmap.org/search"
params = {"q": "Avenida Paulista 1578, São Paulo", "format": "jsonv2", "limit": 1}

r = httpx.get(URL, params=params)
print(r.status_code, r.text)
# 403 Access denied. See https://operations.osmfoundation.org/policies/nominatim/
```

`403 Forbidden`: o servidor entendeu o pedido e recusou. O conserto é um
cabeçalho, passado como dicionário em `headers`. A política pede o nome da
aplicação e um contato:

```python
r = httpx.get(URL, params=params, headers={"User-Agent": "pontos/1.0 (me@jon.dev.br)"})
print(r.status_code)
# 200
resultado = r.json()[0]
print(resultado["display_name"])
# Avenida Paulista, 1578, 1600, Avenida Paulista, Cerqueira César, Jardim Paulista,
#   São Paulo, Região Sudeste, 01311-200, Brasil
print(resultado["lat"], resultado["lon"], type(resultado["lat"]))
# -23.5616836 -46.6565685 <class 'str'>
```

Funciona, e já aparece outra mania: o Nominatim manda latitude e longitude
como **strings**. Vamos ter que converter com `float()` antes de montar um
`Point`. (Isso é mais comum do que parece: JSON não tem um jeito único de
representar decimais, e muita API prefere não arredondar.)

Cabeçalhos são a forma padronizada de dizer coisas **sobre** a requisição,
e os mais frequentes são poucos:

| Cabeçalho          | Direção   | Para que serve                                                   |
|:-------------------|:----------|:-----------------------------------------------------------------|
| `User-Agent`       | pedido    | Quem é o cliente. Várias APIs exigem um valor próprio            |
| `Accept`           | pedido    | Formato que você quer receber (`application/json`)               |
| `Accept-Language`  | pedido    | Idioma preferido para textos (`pt-BR`)                           |
| `Content-Type`     | ambos     | Formato do corpo que está sendo enviado ou devolvido             |
| `Authorization`    | pedido    | Credenciais (veremos adiante)                                    |
| `Cache-Control`    | resposta  | Por quanto tempo a resposta pode ser reaproveitada               |
| `Retry-After`      | resposta  | Quantos segundos esperar depois de um `429` ou `503`             |
| `X-...`            | ambos     | Cabeçalhos inventados pela API (`X-RateLimit-Remaining`, etc.)   |

O httpx trata nomes de cabeçalho sem distinguir maiúsculas:
`r.headers["content-type"]` e `r.headers["Content-Type"]` são a mesma
coisa, e `r.headers.get("retry-after")` devolve `None` em vez de quebrar
quando o cabeçalho não veio.

## Métodos: POST, PUT, PATCH, DELETE

Para ler, `GET`. Para escrever, os outros verbos, e aí entra o **corpo**
da requisição. O httpbin.org é um serviço feito para isso: ele devolve, em
JSON, exatamente o que recebeu, então dá para ver o que o httpx mandou.
O jeito mais comum de enviar dados hoje é JSON, com o argumento `json=`:

```python
novo = {"nome": "Padaria Estrela", "categoria": "Café"}
r = httpx.post("https://httpbin.org/post", json=novo)
print(r.status_code)
# 200
eco = r.json()
print(eco["headers"]["Content-Type"])
# application/json
print(eco["data"])
# {"nome":"Padaria Estrela","categoria":"Café"}
print(eco["json"])
# {'categoria': 'Café', 'nome': 'Padaria Estrela'}
```

O httpx serializou o dicionário, pôs o `Content-Type: application/json` e
o servidor entendeu. Compare com `data=`, que manda os dados como um
**formulário HTML** (o formato que um `<form method="post">` sem
JavaScript envia):

```python
r = httpx.post("https://httpbin.org/post", data=novo)
eco = r.json()
print(eco["headers"]["Content-Type"])
# application/x-www-form-urlencoded
print(eco["form"])
# {'categoria': 'Café', 'nome': 'Padaria Estrela'}
print(eco["json"])
# None
```

Mesmo dicionário, outro `Content-Type`, e o servidor o encontra em outro
lugar. Trocar `json=` por `data=` sem querer é um dos erros mais comuns de
quem começa: a API responde `400 Bad Request` ou `415 Unsupported Media
Type` dizendo que o corpo veio no formato errado. Quando a documentação
diz "envie um JSON", é `json=`.

Os outros verbos seguem o mesmo molde:

```python
r = httpx.put("https://httpbin.org/put", json={"nome": "Padaria Estrela", "categoria": "Café", "aberto": False})
print(r.status_code, r.json()["json"])
# 200 {'aberto': False, 'categoria': 'Café', 'nome': 'Padaria Estrela'}
r = httpx.patch("https://httpbin.org/patch", json={"aberto": False})
print(r.status_code, r.json()["json"])
# 200 {'aberto': False}
r = httpx.delete("https://httpbin.org/delete")
print(r.status_code, r.json()["json"], r.json()["data"])
# 200 None
```

A convenção que a maioria das APIs REST segue: `PUT` substitui o recurso
**inteiro** (por isso mandamos todos os campos), `PATCH` altera **só os
campos enviados**, `DELETE` não leva corpo. Repare que `False` virou
`false` no caminho: o httpx converte os tipos do Python para os do JSON e
de volta.

Cabeçalhos próprios também vão em `headers`, e o eco mostra tudo junto:

```python
r = httpx.get("https://httpbin.org/get", headers={"Accept": "application/json", "X-Projeto": "pontos"})
print(r.json()["headers"])
# {'Accept': 'application/json', 'Accept-Encoding': 'gzip, deflate', 'Host': 'httpbin.org',
#  'User-Agent': 'python-httpx/0.28.1', 'X-Amzn-Trace-Id': 'Root=1-...', 'X-Projeto': 'pontos'}
```

## Quando dá errado

Uma requisição pela internet pode falhar de três jeitos bem diferentes, e
tratar os três do mesmo modo é receita para programa que "às vezes trava".

**1. O servidor respondeu, mas com erro.** O status é `4xx` ou `5xx`. Isso
**não** levanta exceção sozinho; a resposta volta normalmente, e cabe a
você conferir. O jeito curto é `raise_for_status()`, que levanta
`HTTPStatusError` se o status for de erro e não faz nada se for `2xx`:

```python
r = httpx.get("https://httpbin.org/status/404")
print(r.status_code, r.is_success, r.is_error, r.reason_phrase)
# 404 False True NOT FOUND
try:
    r.raise_for_status()
except httpx.HTTPStatusError as e:
    print("HTTPStatusError:", e)
    print(e.response.status_code, e.request.url)
# HTTPStatusError: Client error '404 NOT FOUND' for url 'https://httpbin.org/status/404'
# For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/404
# 404 https://httpbin.org/status/404
```

A exceção carrega a resposta e a requisição, então dá para registrar o
corpo do erro (muitas APIs explicam o problema no JSON) e decidir o que
fazer por família de status:

| Família | Significado                 | O que o cliente costuma fazer                                   |
|:--------|:----------------------------|:----------------------------------------------------------------|
| `2xx`   | Deu certo                   | Usar a resposta                                                 |
| `3xx`   | Redirecionamento            | O httpx **não** segue sozinho; use `follow_redirects=True`      |
| `400`   | Pedido malformado           | Corrigir o código: parâmetro faltando, JSON errado              |
| `401`   | Não autenticado             | Faltou ou expirou a credencial                                  |
| `403`   | Autenticado, mas proibido   | Sem permissão, ou política violada (o `User-Agent` do Nominatim) |
| `404`   | Não existe                  | Tratar como "não achei", não como falha do sistema              |
| `422`   | Dados inválidos             | Mostrar o erro ao usuário; o corpo diz qual campo               |
| `429`   | Pedidos demais              | Esperar (`Retry-After`) e tentar de novo                        |
| `5xx`   | Erro do servidor            | Tentar de novo com intervalo; se persistir, avisar              |

**2. O servidor nem respondeu.** DNS não resolveu, conexão recusada, rede
caiu. Aí sim o httpx levanta exceção, da família `TransportError`:

```python
try:
    httpx.get("https://nao-existe.exemplo.invalido/")
except httpx.ConnectError as e:
    print("ConnectError:", e)
# ConnectError: [Errno -2] Name or service not known
```

**3. O servidor demorou demais.** Este é o mais traiçoeiro, porque sem um
limite o seu programa fica parado para sempre esperando. O httpx tem um
timeout padrão de 5 segundos, mas é bom ser explícito e, em código de
produção, mais curto. O httpbin tem um endpoint que demora de propósito:

```python
try:
    httpx.get("https://httpbin.org/delay/5", timeout=2.0)
except httpx.ReadTimeout as e:
    print("ReadTimeout:", repr(e))
# ReadTimeout: ReadTimeout('The read operation timed out')
```

Um timeout tem várias fases (conectar, escrever, ler), e dá para
controlá-las separadamente quando a API costuma aceitar a conexão rápido
mas pensar muito antes de responder:

```python
print(httpx.Timeout(5.0))
# Timeout(timeout=5.0)
print(httpx.Timeout(10.0, connect=3.0))
# Timeout(connect=3.0, read=10.0, write=10.0, pool=10.0)
```

As exceções do httpx formam uma árvore, e isso simplifica o `except`.
Todas descendem de `HTTPError`; os timeouts descendem de
`TimeoutException`, que descende de `TransportError`:

```python
print(issubclass(httpx.HTTPStatusError, httpx.HTTPError),
      issubclass(httpx.ConnectError, httpx.TransportError),
      issubclass(httpx.ReadTimeout, httpx.TimeoutException))
# True True True
```

Na prática você pega `httpx.HTTPStatusError` quando quer olhar o status,
`httpx.TimeoutException` quando quer tentar de novo, e `httpx.HTTPError`
como rede de segurança para "qualquer coisa deu errado com essa chamada".

### Tentar de novo, com educação

Erros `429` e `5xx` costumam ser passageiros. A resposta certa não é
desistir nem martelar o servidor: é esperar um pouco, de preferência o
tempo que ele pedir em `Retry-After`, e tentar de novo um número limitado
de vezes, aumentando a espera a cada tentativa:

```python
import time
import httpx


def get_com_tentativas(url, tentativas=3, **kwargs):
    for tentativa in range(1, tentativas + 1):
        try:
            r = httpx.get(url, **kwargs)
            if r.status_code in (429, 500, 502, 503, 504) and tentativa < tentativas:
                espera = float(r.headers.get("retry-after", 2 ** tentativa))
                print(f"tentativa {tentativa}: {r.status_code}, esperando {espera:.0f}s")
                time.sleep(espera)
                continue
            r.raise_for_status()
            return r
        except httpx.TimeoutException:
            if tentativa == tentativas:
                raise
            print(f"tentativa {tentativa}: timeout")


r = get_com_tentativas("https://httpbin.org/status/503", timeout=5.0)
# tentativa 1: 503, esperando 2s
# tentativa 2: 503, esperando 4s
# Traceback (most recent call last):
#   ...
# httpx.HTTPStatusError: Server error '503 SERVICE UNAVAILABLE' for url 'https://httpbin.org/status/503'
```

Note o que a função **não** faz: não tenta de novo em `400` ou `404`
(repetir um pedido errado não o torna certo) nem em `POST` que já pode ter
sido processado. Esse último caso é sutil: se o servidor criou o recurso
mas a resposta se perdeu, repetir o `POST` cria dois. APIs bem desenhadas
oferecem uma **chave de idempotência** para isso; se a sua tiver, use.

A política do Nominatim (uma requisição por segundo) é o irmão preventivo
do `429`: em vez de esperar o servidor reclamar, o cliente espera antes.
O comando de gerenciamento do fim do capítulo faz exatamente isso com um
`time.sleep(1)` entre chamadas.

## `httpx.Client`: uma conexão para várias requisições

Cada `httpx.get(...)` solto abre uma conexão TCP, negocia o TLS, faz a
requisição e fecha tudo. Para uma chamada, tanto faz. Para várias ao mesmo
servidor, é desperdício: a negociação custa mais do que a requisição em
si. O `httpx.Client` mantém a conexão aberta e a reaproveita, e de brinde
guarda a configuração comum (URL base, cabeçalhos, timeout) num lugar só.

```python
import time
import httpx

inicio = time.perf_counter()
for cep in ["01310100", "20040020", "70040010"]:
    r = httpx.get(f"https://viacep.com.br/ws/{cep}/json/")
    print(cep, r.json()["localidade"])
print(f"sem Client: {time.perf_counter() - inicio:.2f}s")
# 01310100 São Paulo
# 20040020 Rio de Janeiro
# 70040010 Brasília
# sem Client: 1.01s

inicio = time.perf_counter()
with httpx.Client(base_url="https://viacep.com.br/ws", timeout=10.0) as cliente:
    for cep in ["01310100", "20040020", "70040010"]:
        r = cliente.get(f"/{cep}/json/")
        print(cep, r.json()["localidade"], r.url)
print(f"com Client: {time.perf_counter() - inicio:.2f}s")
# 01310100 São Paulo https://viacep.com.br/ws/01310100/json/
# 20040020 Rio de Janeiro https://viacep.com.br/ws/20040020/json/
# 70040010 Brasília https://viacep.com.br/ws/70040010/json/
# com Client: 0.51s
```

Metade do tempo, e o código ficou mais limpo: o `base_url` é declarado uma
vez e cada chamada só diz o caminho. O `with` garante que a conexão seja
fechada no fim, mesmo se der erro no meio. Tudo o que você passa ao
construtor vira padrão para todas as requisições:

```python
cliente = httpx.Client(
    base_url="https://httpbin.org",
    headers={"User-Agent": "pontos/1.0 (me@jon.dev.br)", "Accept": "application/json"},
    timeout=httpx.Timeout(10.0, connect=3.0),
)
r = cliente.get("/get", params={"x": 1})
print(r.json()["headers"]["User-Agent"], r.json()["url"])
# pontos/1.0 (me@jon.dev.br) https://httpbin.org/get?x=1
cliente.close()
cliente.get("/get")
# RuntimeError: Cannot send a request, as the client has been closed.
```

Regra prática: **um `Client` por API, vivo enquanto você estiver falando
com ela.** Num script, dentro de um `with`. Numa aplicação, um objeto
criado uma vez e reutilizado. É esse objeto que a nossa classe vai
embrulhar.

> O httpx também tem o `httpx.AsyncClient`, com a mesma interface e
> `await` na frente de cada chamada, para programas que fazem muitas
> requisições ao mesmo tempo (um raspador, um servidor que agrega várias
> APIs). Vale saber que existe, mas no Django tradicional, síncrono, o
> `Client` comum resolve, e é ele que usamos aqui.

## Autenticação: provando quem você é

As APIs deste capítulo são abertas; a maioria das que você vai usar no
trabalho não é. Elas exigem uma **credencial** em cada requisição, e há
três jeitos de mandá-la. O httpbin simula os dois primeiros.

**Basic**: usuário e senha, codificados em Base64 no cabeçalho
`Authorization`. O httpx faz a codificação com o argumento `auth=`:

```python
r = httpx.get("https://httpbin.org/basic-auth/ana/segredo123")
print(r.status_code, r.headers.get("www-authenticate"))
# 401 Basic realm="Fake Realm"
r = httpx.get("https://httpbin.org/basic-auth/ana/segredo123", auth=("ana", "segredo123"))
print(r.status_code, r.json())
# 200 {'authenticated': True, 'user': 'ana'}
print(r.request.headers["authorization"])
# Basic YW5hOnNlZ3JlZG8xMjM=
```

Sem a credencial, `401 Unauthorized`, e o cabeçalho `WWW-Authenticate` diz
qual esquema o servidor espera. Com ela, passa. E repare: Base64 **não é
criptografia**. Qualquer um decodifica:

```python
import base64
print(base64.b64decode("YW5hOnNlZ3JlZG8xMjM="))
# b'ana:segredo123'
```

É por isso que credenciais só podem viajar por HTTPS: o `s` é o que
impede alguém no meio do caminho de ler o cabeçalho.

**Bearer**: um *token*, uma string longa que a API gerou para você, no
mesmo cabeçalho. É o formato mais comum hoje, inclusive para os tokens
que o OAuth produz:

```python
r = httpx.get("https://httpbin.org/bearer")
print(r.status_code, r.headers.get("www-authenticate"))
# 401 Bearer
r = httpx.get("https://httpbin.org/bearer", headers={"Authorization": "Bearer tok_abc123"})
print(r.status_code, r.json())
# 200 {'authenticated': True, 'token': 'tok_abc123'}
```

**Chave de API** (*API key*): uma string fixa que você recebe ao se
cadastrar, mandada onde a documentação disser, geralmente num cabeçalho
próprio ou na querystring:

```python
r = httpx.get("https://httpbin.org/get", headers={"X-API-Key": "abc123"})
print(r.json()["headers"]["X-Api-Key"])
# abc123
r = httpx.get("https://httpbin.org/get", params={"api_key": "abc123"})
print(r.json()["url"])
# https://httpbin.org/get?api_key=abc123
```

Prefira o cabeçalho quando a API deixar escolher: a URL vai parar no log
do servidor, no histórico do navegador e em telas de erro; o cabeçalho,
normalmente, não.

Em qualquer dos três casos, a credencial é um valor que o seu código
precisa **ter** sem **conter**. A seção final do capítulo é sobre essa
diferença. Antes, vamos construir a classe que vai precisar dela.

## Encapsulando: a classe `Nominatim`

Você já viu quatro manias do Nominatim: exige `User-Agent`, devolve
coordenadas como string, devolve lista vazia quando não encontra, e pede
no máximo uma requisição por segundo. Se cada lugar do projeto que
precisa de uma coordenada tiver que lembrar das quatro, o conhecimento
sobre a API se espalha e qualquer mudança nela vira caça ao tesouro. A
solução clássica é concentrar tudo numa **classe cliente**, com três
responsabilidades:

1. Guardar o `httpx.Client` configurado (URL base, cabeçalhos, timeout).
2. Expor métodos com nomes do **seu** domínio (`buscar(endereco)`), que
   recebem e devolvem tipos **seus** (`Coordenada`), não dicionários
   crus.
3. Traduzir os erros do httpx para **uma** exceção sua, para quem chama
   não precisar conhecer a árvore de exceções da biblioteca.

Crie `lugares/geocodificacao.py`:

```python
"""Cliente do Nominatim, o geocodificador do OpenStreetMap."""

from dataclasses import dataclass

import httpx


class ErroDeGeocodificacao(Exception):
    """O serviço não respondeu ou respondeu com erro."""


@dataclass(frozen=True)
class Coordenada:
    latitude: float
    longitude: float
    descricao: str


class Nominatim:
    """Transforma endereços em coordenadas usando a API pública do Nominatim.

    Uso:
        with Nominatim(user_agent="meu-app/1.0 (eu@exemplo.com)") as geo:
            coordenada = geo.buscar("Avenida Paulista, 1578, São Paulo")
    """

    BASE_URL = "https://nominatim.openstreetmap.org"

    def __init__(self, user_agent: str, timeout: float = 10.0, transport=None):
        self._cliente = httpx.Client(
            base_url=self.BASE_URL,
            headers={"User-Agent": user_agent, "Accept-Language": "pt-BR"},
            timeout=timeout,
            transport=transport,
        )

    def buscar(self, endereco: str) -> Coordenada | None:
        """Devolve a melhor coordenada para o endereço, ou None se não achar."""
        try:
            resposta = self._cliente.get(
                "/search", params={"q": endereco, "format": "jsonv2", "limit": 1}
            )
            resposta.raise_for_status()
        except httpx.HTTPError as erro:
            raise ErroDeGeocodificacao(f"Nominatim falhou para {endereco!r}: {erro}") from erro

        resultados = resposta.json()
        if not resultados:
            return None
        melhor = resultados[0]
        return Coordenada(
            latitude=float(melhor["lat"]),
            longitude=float(melhor["lon"]),
            descricao=melhor["display_name"],
        )

    def close(self):
        self._cliente.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
```

Alguns detalhes de projeto que valem a pena:

- **`Coordenada` é uma dataclass congelada.** Quem chama `buscar` recebe
  um objeto com nomes claros e `float` de verdade, e nunca precisa saber
  que o Nominatim chama latitude de `lat` e manda como string. Se a API
  mudar, só este arquivo muda.
- **"Não achei" é `None`; "deu errado" é exceção.** São situações
  diferentes e o chamador trata de jeitos diferentes: um endereço
  inexistente é um aviso ao usuário; um `503` é um problema de
  infraestrutura. Misturar as duas numa só é um erro comum.
- **`except httpx.HTTPError`** pega tudo o que a chamada pode levantar
  (status de erro, timeout, conexão) e re-levanta como
  `ErroDeGeocodificacao`, mantendo o erro original encadeado com `from`.
  Quem usa a classe só precisa conhecer uma exceção.
- **`transport=None`** é a porta para os testes. Em produção fica
  `None` e o httpx usa a rede; nos testes passaremos um transporte falso.
  Esse parâmetro custa uma linha e torna a classe testável sem internet.
- **`__enter__` e `__exit__`** fazem a classe funcionar num `with`, igual
  ao `httpx.Client` que ela embrulha, para a conexão ser fechada sempre.

### Um comando que usa a classe

Os lugares do `pontos` têm um campo `endereco` que até agora era só
decorativo, e coordenadas digitadas na mão. O comando `geocodificar`
pede ao Nominatim a coordenada de cada endereço e mostra quanto o ponto
"andou". Primeiro, no shell, dê endereços a três lugares:

```python
from lugares.models import Lugar

Lugar.objects.filter(nome="MASP").update(endereco="Avenida Paulista, 1578, São Paulo")
Lugar.objects.filter(nome="Parque Ibirapuera").update(endereco="Parque Ibirapuera, São Paulo")
Lugar.objects.filter(nome="Café do Rio").update(endereco="Praça Mauá, Rio de Janeiro")
```

O comando lê o `User-Agent` de uma configuração do Django, e não de uma
string no código, por motivos que a próxima seção explica. Acrescente ao
fim de `config/settings.py`:

```python
# Serviços externos. Valores vêm do ambiente; o padrão serve só para desenvolvimento.
NOMINATIM_USER_AGENT = os.environ.get("NOMINATIM_USER_AGENT", "pontos-dev/0.1")
```

E crie `lugares/management/commands/geocodificar.py`, no molde do
`importar_lugares` do capítulo de Django:

```python
import time

from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError

from lugares.geocodificacao import ErroDeGeocodificacao, Nominatim
from lugares.models import Lugar


class Command(BaseCommand):
    help = "Recalcula a localização dos lugares a partir do endereço, via Nominatim."

    def add_arguments(self, parser):
        parser.add_argument(
            "nomes", nargs="*", help="nomes dos lugares (padrão: todos com endereço)"
        )
        parser.add_argument(
            "--simular",
            action="store_true",
            help="mostra o que faria, mas não grava nada no banco",
        )

    def handle(self, *args, **options):
        lugares = Lugar.objects.exclude(endereco="")
        if options["nomes"]:
            lugares = lugares.filter(nome__in=options["nomes"])
        if not lugares.exists():
            raise CommandError("Nenhum lugar com endereço para geocodificar.")

        atualizados = nao_encontrados = 0
        with Nominatim(user_agent=settings.NOMINATIM_USER_AGENT) as geo:
            for numero, lugar in enumerate(lugares):
                if numero:
                    time.sleep(1)  # política do Nominatim: no máximo 1 requisição por segundo
                try:
                    coordenada = geo.buscar(lugar.endereco)
                except ErroDeGeocodificacao as erro:
                    raise CommandError(str(erro))

                if coordenada is None:
                    aviso = f"{lugar}: endereço não encontrado ({lugar.endereco})"
                    self.stdout.write(self.style.WARNING(aviso))
                    nao_encontrados += 1
                    continue

                novo = Point(coordenada.longitude, coordenada.latitude, srid=4326)
                antigo = lugar.localizacao
                metros = antigo.transform(31983, clone=True).distance(
                    novo.transform(31983, clone=True)
                )
                self.stdout.write(
                    f"{lugar}: {antigo.coords} -> {novo.coords} (moveu {metros:.0f} m)"
                )
                if options["verbosity"] >= 2:
                    self.stdout.write(f"  {coordenada.descricao}")

                if not options["simular"]:
                    lugar.localizacao = novo
                    lugar.save(update_fields=["localizacao"])
                atualizados += 1

        resumo = f"{atualizados} atualizados, {nao_encontrados} não encontrados"
        if options["simular"]:
            self.stdout.write(self.style.NOTICE(f"[simulação] {resumo}; nada foi gravado"))
        else:
            self.stdout.write(self.style.SUCCESS(resumo))
```

Repare como o `handle` ficou legível: ele fala de lugares, endereços e
coordenadas. Nenhum `httpx`, nenhum `lat` como string, nenhum `403`. Tudo
isso está na classe. A distância usa o truque do capítulo anterior
(`transform(31983)` para medir em metros). Rode primeiro simulando:

```bash
uv run python manage.py geocodificar --simular
# Café do Rio: (-43.1729, -22.9068) -> (-43.1810211, -22.8964635) (moveu 1416 m)
# MASP: (-46.6558, -23.5614) -> (-46.6559677, -23.5614961) (moveu 20 m)
# Parque Ibirapuera: (-46.6575, -23.5874) -> (-46.6585214, -23.5877126) (moveu 110 m)
# [simulação] 3 atualizados, 0 não encontrados; nada foi gravado
```

O MASP estava a 20 metros do lugar certo; o Café do Rio, a 1,4 km (a
coordenada era chutada). Agora de verdade, com `-v 2` para ver o endereço
completo que o Nominatim entendeu:

```bash
uv run python manage.py geocodificar -v 2
# Café do Rio: (-43.1729, -22.9068) -> (-43.1810211, -22.8964635) (moveu 1416 m)
#   Praça Mauá, Centro, Rio de Janeiro, Região Sudeste, Brasil
# MASP: (-46.6558, -23.5614) -> (-46.6559677, -23.5614961) (moveu 20 m)
#   Museu de Arte de São Paulo, 1578, Avenida Paulista, Morro dos Ingleses, Bela Vista,
#   São Paulo, Região Sudeste, 01310-200, Brasil
# Parque Ibirapuera: (-46.6575, -23.5874) -> (-46.6585214, -23.5877126) (moveu 110 m)
#   Parque Ibirapuera, Moema, São Paulo, Região Sudeste, 04002-010, Brasil
# 3 atualizados, 0 não encontrados
```

Note os três segundos que o comando leva: dois `sleep(1)` entre as três
chamadas. É o preço de ser um bom vizinho de uma API gratuita. Recarregue
o mapa do capítulo anterior e o MASP continua em cima do MASP, só que
agora por mérito.

### Testando sem internet

Testes que chamam APIs de verdade são lentos, quebram quando a rede cai,
e, no caso do Nominatim, violam a política de uso toda vez que a suíte
roda. O parâmetro `transport` resolve isso: um `httpx.MockTransport`
recebe uma função que **faz o papel do servidor**, recebendo a requisição
e devolvendo a resposta que você quiser. Acrescente a `lugares/tests.py`:

```python
from io import StringIO
from unittest.mock import patch

import httpx
from django.contrib.gis.geos import Point
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from .geocodificacao import Coordenada, ErroDeGeocodificacao, Nominatim
from .models import Categoria, Lugar


class NominatimTests(SimpleTestCase):
    def nominatim_falso(self, resposta):
        """Um Nominatim cujo transporte devolve sempre `resposta`, sem rede."""

        def responder(requisicao):
            self.ultima_requisicao = requisicao
            return resposta

        return Nominatim(user_agent="teste/1.0", transport=httpx.MockTransport(responder))

    def test_encontra_coordenada(self):
        resposta = httpx.Response(
            200,
            json=[{"lat": "-23.5616836", "lon": "-46.6565685", "display_name": "MASP, São Paulo"}],
        )
        with self.nominatim_falso(resposta) as geo:
            coordenada = geo.buscar("Avenida Paulista, 1578, São Paulo")

        self.assertEqual(coordenada, Coordenada(-23.5616836, -46.6565685, "MASP, São Paulo"))
        self.assertEqual(self.ultima_requisicao.url.path, "/search")
        self.assertEqual(
            self.ultima_requisicao.url.params["q"], "Avenida Paulista, 1578, São Paulo"
        )
        self.assertEqual(self.ultima_requisicao.headers["User-Agent"], "teste/1.0")

    def test_endereco_desconhecido(self):
        with self.nominatim_falso(httpx.Response(200, json=[])) as geo:
            self.assertIsNone(geo.buscar("Rua que não existe, 0"))

    def test_erro_do_servidor(self):
        with self.nominatim_falso(httpx.Response(503)) as geo:
            with self.assertRaises(ErroDeGeocodificacao):
                geo.buscar("Avenida Paulista, 1578, São Paulo")


class GeocodificarTests(TestCase):
    def test_atualiza_localizacao(self):
        museu = Categoria.objects.create(nome="Museu")
        masp = Lugar.objects.create(
            nome="MASP",
            categoria=museu,
            endereco="Avenida Paulista, 1578, São Paulo",
            localizacao=Point(-46.6333, -23.5505, srid=4326),
        )
        coordenada = Coordenada(-23.5616836, -46.6565685, "MASP, São Paulo")
        saida = StringIO()
        with patch.object(Nominatim, "buscar", return_value=coordenada):
            call_command("geocodificar", stdout=saida)

        masp.refresh_from_db()
        self.assertAlmostEqual(masp.localizacao.x, -46.6565685)
        self.assertAlmostEqual(masp.localizacao.y, -23.5616836)
        self.assertIn("1 atualizados", saida.getvalue())
```

Os três primeiros testes exercitam a classe nos três cenários (achou, não
achou, deu erro) e ainda conferem que a requisição saiu certa: caminho,
parâmetro `q`, `User-Agent`. São `SimpleTestCase` porque não tocam no
banco. O quarto testa o comando, e aí a estratégia muda: em vez de um
transporte falso, um `patch.object` substitui o método `buscar` inteiro
por um que devolve a `Coordenada` pronta. O comando não precisa saber
nada de HTTP, então o teste dele também não.

```bash
uv run python manage.py test lugares.tests.NominatimTests lugares.tests.GeocodificarTests
# ....
# ----------------------------------------------------------------------
# Ran 4 tests in 0.033s
#
# OK
```

Quatro testes em 33 milissegundos, sem um byte na rede.

## Onde guardar credenciais

O Nominatim só pede um `User-Agent`, mas a API que você vai usar no
trabalho vai pedir uma chave, e a chave de uma API paga é dinheiro: quem a
tiver gasta a **sua** cota, e, se for de um gateway de pagamento ou de um
serviço de e-mail, faz muito pior que gastar. Há três lugares onde a chave
pode morar, e o primeiro é uma armadilha.

### 1. No código (não faça isso)

```python
# lugares/geocodificacao.py
GEOCODER_API_KEY = "sk_live_9f8e7d6c5b4a"   # NUNCA
```

Parece inofensivo num projeto pessoal. O problema é o git. Veja o cenário
completo num repositório descartável: a chave entra, alguém percebe e
"remove":

```bash
git log --oneline
# 6315f34 fix: remove chave do codigo
# 3044f18 feat: adiciona cliente do geocodificador
grep -c sk_live config.py
# 0
```

Sumiu do arquivo. Mas não do histórico:

```bash
git log -p | grep sk_live
# -GEOCODER_API_KEY = "sk_live_9f8e7d6c5b4a"
# +GEOCODER_API_KEY = "sk_live_9f8e7d6c5b4a"
git log --oneline -S sk_live_9f8e7d6c5b4a
# 6315f34 fix: remove chave do codigo
# 3044f18 feat: adiciona cliente do geocodificador
```

Qualquer pessoa com acesso ao repositório recupera a chave com um comando.
Se o repositório for público, robôs fazem isso em **minutos**: há
serviços que varrem o GitHub procurando padrões como `sk_live_`,
`AKIA...` e `ghp_...` e usam ou revendem as chaves encontradas. Reescrever
o histórico (`git filter-repo`) é possível, mas trabalhoso, e não desfaz
os clones que já existem. A regra é simples e sem exceção: **se a chave
entrou no git, considere-a vazada e gere outra.** O conserto não é
apagar; é **revogar**.

Outros lugares onde chaves vazam sem querer: *prints* de depuração que vão
para o log, telas de erro, capturas de tela em issues, e o próprio
`settings.py` quando é commitado com valores de produção.

### 2. Numa variável de ambiente

A alternativa é o código **não conter** a chave, só saber **onde
buscá-la** em tempo de execução. O lugar padrão é o **ambiente** do
processo, as variáveis que o shell passa a todo programa que inicia. Você
já conhece uma: `PATH`. O Python as lê em `os.environ`:

```bash
export GEOCODER_API_KEY=sk_live_9f8e7d6c5b4a
uv run python -c "import os; print(os.environ['GEOCODER_API_KEY'])"
# sk_live_9f8e7d6c5b4a
```

O `export` vale para aquele terminal; feche-o e a variável se foi. Numa
outra janela, sem o `export`:

```bash
uv run python -c "import os; print(os.environ['GEOCODER_API_KEY'])"
# KeyError: 'GEOCODER_API_KEY'
```

Esse `KeyError` é um comportamento desejável para uma chave obrigatória:
melhor quebrar na largada com uma mensagem clara do que rodar com a chave
errada. Para configurações opcionais, `os.environ.get("NOME", "padrão")`
devolve o padrão quando a variável não existe, que foi o que usamos para
o `NOMINATIM_USER_AGENT`.

Digitar `export` toda vez é chato, e aí entra o arquivo **`.env`**: um
texto com uma variável por linha, que as ferramentas carregam no ambiente
antes de rodar o programa. Crie na raiz do projeto:

```
NOMINATIM_USER_AGENT=pontos/1.0 (me@jon.dev.br)
GEOCODER_API_KEY=sk_live_9f8e7d6c5b4a
```

O `uv` lê esse arquivo com `--env-file`:

```bash
uv run --env-file .env python manage.py geocodificar --simular
```

E o Docker Compose faz o mesmo pelos serviços, com `env_file` no
`docker-compose.yml`, para quando a aplicação rodar num contêiner:

```yaml
services:
  app:
    env_file: .env
```

O `.env` é a chave em texto puro no disco, então ele tem **duas** regras:
nunca entra no git, e ganha um irmão que entra. Acrescente ao
`.gitignore`:

```
.env
```

E commite um `.env.example` com os nomes das variáveis e valores de
mentira, para quem clonar o projeto saber o que precisa preencher:

```
NOMINATIM_USER_AGENT=meu-app/1.0 (meu@email.com)
GEOCODER_API_KEY=coloque-sua-chave-aqui
```

Em produção não há `.env`: o servidor, o painel da hospedagem ou o
orquestrador de contêineres injetam as variáveis direto no ambiente do
processo. O código não muda uma linha, e é exatamente esse o ponto: **a
mesma imagem roda em qualquer ambiente, só o ambiente muda.** Essa ideia
tem nome, é o terceiro dos "doze fatores" para aplicações modernas, e a
referência está no fim do capítulo.

### 3. Via `settings.py` do Django

Ler `os.environ` espalhado pelo código traz de volta o problema da seção
anterior em outra roupa: o nome da variável aparece em dez arquivos, e
ninguém sabe a lista completa do que o projeto precisa para rodar. No
Django o lugar certo para esse conhecimento é o `settings.py`, que é
**ele** quem lê o ambiente, uma vez, e o resto do código lê de
`settings`. Foi o que fizemos com o `NOMINATIM_USER_AGENT`; para uma chave
obrigatória, vale uma mensagem melhor que `KeyError`:

```python
# config/settings.py
import os

from django.core.exceptions import ImproperlyConfigured


def variavel_obrigatoria(nome):
    try:
        return os.environ[nome]
    except KeyError:
        raise ImproperlyConfigured(f"Defina a variável de ambiente {nome}")


NOMINATIM_USER_AGENT = os.environ.get("NOMINATIM_USER_AGENT", "pontos-dev/0.1")
GEOCODER_API_KEY = variavel_obrigatoria("GEOCODER_API_KEY")
```

E no resto do projeto, sempre:

```python
from django.conf import settings

cliente = httpx.Client(headers={"Authorization": f"Bearer {settings.GEOCODER_API_KEY}"})
```

Três ganhos. O `settings.py` vira o **inventário** de tudo o que o projeto
precisa do ambiente. Os testes podem trocar um valor com
`@override_settings(GEOCODER_API_KEY="teste")` sem mexer em variável de
ambiente nenhuma. E um detalhe de segurança que o Django faz por você:
quando `DEBUG=True` e uma página quebra, a tela de erro mostra todas as
configurações, **exceto** as cujo nome contém `KEY`, `SECRET`, `TOKEN`, `AUTH`,
`PASS`, `SIGNATURE` ou `API`, que aparecem como asteriscos. Por isso
`GEOCODER_API_KEY` é um nome melhor que `GEOCODER`. Dê às suas chaves
nomes que digam que são chaves.

Resumindo o fluxo, de fora para dentro:

```
.env (dev) ou painel da hospedagem (produção)
    -> variáveis de ambiente do processo
        -> config/settings.py (lê uma vez, valida, dá nome)
            -> from django.conf import settings (o resto do código)
```

A chave existe em exatamente um lugar fora do código, o código tem um
único ponto que a lê, e o git nunca a vê.

## Tabela de referência rápida

| O que                                  | Como                                                                        |
|:---------------------------------------|:----------------------------------------------------------------------------|
| Instalar                               | `uv add httpx`                                                              |
| GET simples                            | `r = httpx.get(url)`; `r.status_code`, `r.headers`, `r.text`, `r.json()`    |
| Querystring                            | `httpx.get(url, params={"q": "café", "limit": 1})` (escapa sozinho)         |
| Cabeçalhos                             | `headers={"User-Agent": "app/1.0 (contato)", "Accept": "application/json"}` |
| Corpo JSON                             | `httpx.post(url, json={...})` (`Content-Type: application/json`)            |
| Corpo de formulário                    | `httpx.post(url, data={...})` (`application/x-www-form-urlencoded`)         |
| Outros verbos                          | `httpx.put`, `httpx.patch`, `httpx.delete`                                  |
| Ver o que foi enviado                  | `r.request.method`, `r.request.url`, `r.request.headers`                    |
| Status é de erro?                      | `r.is_success`, `r.is_error`, `r.raise_for_status()`                        |
| Exceção por status                     | `except httpx.HTTPStatusError as e: e.response.status_code`                 |
| Exceção de rede / timeout              | `httpx.ConnectError`, `httpx.TimeoutException`; `httpx.HTTPError` pega todas |
| Timeout                                | `timeout=5.0` ou `timeout=httpx.Timeout(10.0, connect=3.0)`                 |
| Seguir redirecionamentos               | `follow_redirects=True`                                                     |
| Conexão reaproveitada                  | `with httpx.Client(base_url=..., headers=..., timeout=...) as c: c.get("/x")` |
| Basic auth                             | `auth=("usuario", "senha")`                                                 |
| Bearer / API key                       | `headers={"Authorization": "Bearer <token>"}`, `headers={"X-API-Key": ...}` |
| Respeitar limite de requisições        | `time.sleep(1)` entre chamadas; em `429`/`503`, esperar `Retry-After`       |
| Classe cliente                         | Embrulha o `Client`; métodos do domínio; devolve dataclass; uma exceção própria |
| Testar sem rede                        | `transport=httpx.MockTransport(funcao)`; `funcao(request)` devolve `httpx.Response(...)` |
| Testar quem usa o cliente              | `patch.object(Classe, "metodo", return_value=...)`                          |
| Variável de ambiente                   | `os.environ["NOME"]` (obrigatória), `os.environ.get("NOME", "padrão")`       |
| Arquivo `.env`                         | `uv run --env-file .env ...`; `env_file: .env` no Compose; `.env` no `.gitignore` |
| Chave no Django                        | `settings.py` lê o ambiente; o resto usa `from django.conf import settings` |
| Chave vazou no git                     | Revogar e gerar outra. Apagar do arquivo não apaga do histórico             |

## Exercícios

### Exercício 1: um comando de CEP

1. Crie um comando `cep` que recebe um CEP e imprime logradouro, bairro,
   cidade e UF usando o ViaCEP. Lembre que ele devolve `200` com
   `{"erro": "true"}` para CEP inexistente: trate isso como
   `CommandError`, não como sucesso.
2. Acrescente a opção `--fonte brasilapi` que usa a BrasilAPI no lugar.
   As chaves do JSON são diferentes; faça o comando imprimir o mesmo
   formato nos dois casos.
3. Rode com um CEP com hífen (`01310-100`). Funcionou nas duas fontes?
   Normalize a entrada antes de montar a URL.

### Exercício 2: o tempo em cada lugar

1. Escreva uma função `temperatura_atual(lugar)` que chama a Open-Meteo
   com `lugar.localizacao.y` e `.x` (lembre: `y` é latitude) e devolve a
   temperatura em °C.
2. Faça um comando `clima` que imprime a temperatura de todos os lugares,
   usando **um** `httpx.Client` para todas as chamadas. Meça o tempo com
   e sem o `Client`, como fizemos com o ViaCEP.
3. Inclua a temperatura nas `properties` do `lugares_geojson` do
   capítulo de GeoJSON e mostre-a no popup do mapa. O mapa ficou mais
   lento? Quantas requisições à Open-Meteo cada carregamento do mapa faz
   agora? Isso é aceitável? (Dica: `Cache-Control: max-age` na resposta
   da Open-Meteo sugere uma resposta.)

### Exercício 3: tentativas como classe

1. Transforme o `get_com_tentativas` numa classe `ClienteResiliente` que
   embrulha um `httpx.Client` e repete a lógica de tentativas em um
   método `get`. Faça o número de tentativas e a espera inicial serem
   parâmetros do construtor.
2. Teste-a com `MockTransport`: faça a função do transporte devolver
   `503` nas duas primeiras chamadas e `200` na terceira (um contador
   resolve), e confira que `get` devolve a resposta `200`. Substitua o
   `time.sleep` por algo que o teste possa controlar, ou o teste vai
   demorar 6 segundos.
3. Faça a classe **não** repetir um `404` e escreva o teste que prova.

### Exercício 4: um segundo geocodificador

1. A BrasilAPI devolve coordenadas junto com o CEP (chave `location`).
   Crie uma classe `BrasilAPI` em `geocodificacao.py` com um método
   `buscar_cep(cep) -> Coordenada | None`, mesma `Coordenada`, mesma
   `ErroDeGeocodificacao`. Repare que nem todo CEP vem com coordenadas:
   `location["coordinates"]` pode ser `{}`.
2. As duas classes repetem o `__init__`, o `close` e o `with`. Extraia uma
   classe base `ClienteHTTP` com essa parte comum e faça as duas herdarem
   dela.
3. Acrescente ao comando `geocodificar` uma opção `--fonte` que escolhe a
   classe. Quando a fonte for a BrasilAPI, o que o comando deve usar como
   consulta, já que ela quer CEP e não endereço livre?

### Exercício 5: a chave fora do código

1. Use o `httpbin.org/bearer` como uma API protegida de mentira. Escreva
   uma função `chamar_api_protegida()` que lê `settings.API_PROTEGIDA_TOKEN`
   e faz o `GET` com `Authorization: Bearer`. Sem o cabeçalho, ela deve
   levantar uma exceção sua, não deixar o `401` passar.
2. Defina a setting lendo o ambiente com a função `variavel_obrigatoria`.
   Rode `manage.py check` sem a variável e veja o `ImproperlyConfigured`.
   Depois crie um `.env`, rode com `--env-file .env` e confira que passa.
3. Confira que `.env` está no `.gitignore` com `git check-ignore -v .env`
   e crie o `.env.example`. Faça `git status` e garanta que só o exemplo
   aparece.
4. Provoque um erro numa view com `DEBUG=True` (um `1/0` serve) e procure
   `API_PROTEGIDA_TOKEN` na tela de erro. O que aparece no lugar do
   valor? Renomeie a setting para `API_PROTEGIDA` e repita. Volte ao nome
   com `TOKEN`.

### Exercício 6: o vazamento e o conserto

1. Num repositório descartável (`git init` numa pasta nova), repita o
   experimento da seção de credenciais: commite um arquivo com uma chave
   falsa, remova a chave num segundo commit e recupere-a com
   `git log -p` e com `git log -S`.
2. Leia a página do `git filter-repo` (nas referências) e use-o para
   remover a string do histórico. Confira com `git log -S` que ela sumiu.
   Agora reflita: se esse repositório tivesse sido clonado por mais
   alguém antes do conserto, a chave estaria segura?
3. Escreva, em três linhas, o procedimento que você seguiria se
   descobrisse hoje que uma chave de verdade foi commitada no projeto
   da sua equipe. Qual é o **primeiro** passo? (Não é `git rm`.)

## Referências

- **httpx, guia rápido (`get`, `params`, `headers`, `json`, `data`,
  status, exceções)**: <https://www.python-httpx.org/quickstart/>.
- **httpx, `Client` (conexões reaproveitadas, `base_url`, cabeçalhos e
  timeouts padrão, `with`)**: <https://www.python-httpx.org/advanced/clients/>.
- **httpx, timeouts (`Timeout`, fases `connect`/`read`/`write`/`pool`)**:
  <https://www.python-httpx.org/advanced/timeouts/>.
- **httpx, árvore de exceções (`HTTPError`, `TransportError`,
  `TimeoutException`, `HTTPStatusError`)**:
  <https://www.python-httpx.org/exceptions/>.
- **httpx, autenticação (`auth=`, Basic, Digest, classes próprias)**:
  <https://www.python-httpx.org/advanced/authentication/>.
- **httpx, transportes e `MockTransport` para testes**:
  <https://www.python-httpx.org/advanced/transports/>.
- **httpx, `AsyncClient`**: <https://www.python-httpx.org/async/>.
- **Métodos HTTP e códigos de status (MDN)**:
  <https://developer.mozilla.org/pt-BR/docs/Web/HTTP/Methods>,
  <https://developer.mozilla.org/pt-BR/docs/Web/HTTP/Status>.
- **Cabeçalhos HTTP (MDN)**:
  <https://developer.mozilla.org/pt-BR/docs/Web/HTTP/Headers>.
- **Nominatim: API de busca e política de uso (`User-Agent`
  obrigatório, 1 requisição/segundo)**:
  <https://nominatim.org/release-docs/latest/api/Search/>,
  <https://operations.osmfoundation.org/policies/nominatim/>.
- **ViaCEP**: <https://viacep.com.br/>.
  **BrasilAPI (CEP v2 com coordenadas)**:
  <https://brasilapi.com.br/docs#tag/CEP-V2>.
- **Open-Meteo**: <https://open-meteo.com/en/docs>.
- **httpbin (eco de requisições, `/status`, `/delay`, `/basic-auth`,
  `/bearer`)**: <https://httpbin.org/>.
- **The Twelve-Factor App, fator III: configuração no ambiente**:
  <https://12factor.net/pt_br/config>.
- **Django: `settings`, `override_settings` e `ImproperlyConfigured`**:
  <https://docs.djangoproject.com/en/stable/topics/settings/>,
  <https://docs.djangoproject.com/en/stable/topics/testing/tools/#django.test.override_settings>.
- **Django: filtragem de settings sensíveis na página de erro
  (`SafeExceptionReporterFilter`)**:
  <https://docs.djangoproject.com/en/stable/howto/error-reporting/#filtering-sensitive-information>.
- **uv: `--env-file`**: <https://docs.astral.sh/uv/configuration/files/#env>.
- **Docker Compose: `env_file`**:
  <https://docs.docker.com/reference/compose-file/services/#env_file>.
- **Remover segredos do histórico (`git filter-repo`) e por que revogar
  mesmo assim**:
  <https://docs.github.com/pt/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository>.
- **`unittest.mock.patch.object`**:
  <https://docs.python.org/pt-br/3/library/unittest.mock.html#patch-object>.
- **`dataclasses`**: <https://docs.python.org/pt-br/3/library/dataclasses.html>.
