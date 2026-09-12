# Django: a estrutura básica

## Por que isso importa

Um site dinâmico precisa resolver sempre os mesmos problemas: receber uma
requisição HTTP, decidir o que fazer com ela, ler e gravar em um banco de
dados, montar uma página HTML, cuidar de login, senhas e permissões, proteger
contra ataques comuns. Dá para escrever tudo isso do zero, mas você levaria
meses e cometeria os erros que outras pessoas já cometeram.

Um **framework web** é esse trabalho já feito. O Django é o framework mais
usado do mundo Python e tem uma característica que o define: vem com
"baterias inclusas". ORM, migrações, sistema de templates, autenticação,
painel administrativo, formulários, proteção contra CSRF e injeção de SQL:
tudo vem na caixa e funciona junto. Você aprende uma forma de fazer as coisas
e ela serve para o projeto inteiro.

Este capítulo apresenta as peças principais e como elas se encaixam. Vamos
construir um projeto pequeno de verdade, um cadastro de pontos de interesse,
que o capítulo de GeoDjango vai continuar.

## Uma história curta: de um jornal do Kansas ao mundo

Em 2003, dois programadores de um jornal em Lawrence, no Kansas, Adrian
Holovaty e Simon Willison, precisavam publicar sites novos em dias, não em
meses. Um jornal não pode esperar. Eles extraíram das ferramentas internas um
framework reutilizável e, em 2005, o liberaram como software livre. O nome
homenageia o guitarrista Django Reinhardt.

Em 2008 foi criada a Django Software Foundation, uma organização sem fins
lucrativos que mantém o projeto até hoje. Durante muitos anos o Django lançou
uma versão a cada oito meses, e a cada dois anos uma delas era marcada como
**LTS** (*long-term support*), com três anos de correções: a preferida para
produção. Isso está mudando: pela DEP 20, o projeto passa a um ciclo anual, e
as versões que seriam 7.0 e 7.1 vão se chamar "Django 2028" e "Django 2029".
A 6.1, de agosto de 2026, é a última com a numeração antiga. Neste livro
usamos sempre a versão mais recente disponível.

## Preparando o terreno com o uv

O `uv` é uma ferramenta única que substitui `pip`, `venv` e `pyenv`: instala
a versão do Python que você pedir, cria o ambiente virtual, gerencia as
dependências em `pyproject.toml` e trava as versões exatas em `uv.lock`. É
rápido e evita o clássico "funciona na minha máquina".

```bash
brew install uv
uv --version
```

Crie a pasta do projeto e inicialize um projeto Python mínimo. A opção
`--bare` gera só o `pyproject.toml`, sem pastas extras que o Django não usa:

```bash
mkdir pontos && cd pontos
uv init --bare --python 3.14
cat pyproject.toml
```

Adicione o Django. O `uv add` baixa o Python 3.14 se você ainda não tiver,
cria o `.venv/`, instala o pacote e registra a dependência:

```bash
uv add django
uv run django-admin --version
```

Repare no `uv run`: ele executa qualquer comando **dentro** do ambiente
virtual do projeto, sem você precisar "ativar" nada. Vamos usá-lo na frente
de todo comando Python deste capítulo.

## Projeto e apps

O Django separa duas coisas:

- O **projeto** é o site como um todo: configurações, URLs de entrada,
  ponto de partida do servidor.
- Um **app** é um pedaço com uma responsabilidade: "lugares", "usuários",
  "blog". Um projeto tem vários apps, e um app bem feito pode ser reusado
  em outro projeto.

Crie o projeto na pasta atual (o `.` no fim é importante) chamando a pasta
de configurações de `config`, e depois um app chamado `lugares`:

```bash
uv run django-admin startproject config .
uv run python manage.py startapp lugares
```

O resultado:

```
pontos/
|-- pyproject.toml      dependências (gerenciado pelo uv)
|-- uv.lock             versões exatas travadas
|-- .venv/              ambiente virtual (não vai para o Git)
|-- manage.py           a ferramenta de linha de comando do projeto
|-- config/             o projeto
|   |-- settings.py     todas as configurações
|   |-- urls.py         as URLs de entrada
|   |-- asgi.py         ponto de entrada para servidores assíncronos
|   `-- wsgi.py         ponto de entrada para servidores tradicionais
`-- lugares/            o app
    |-- models.py       as tabelas do banco, em Python
    |-- views.py        o que fazer com cada requisição
    |-- admin.py        como o painel administrativo mostra os modelos
    |-- apps.py         metadados do app
    |-- tests.py        testes automatizados
    `-- migrations/     histórico de mudanças no banco
```

Todo app precisa ser registrado no projeto. Abra `config/settings.py` e
adicione `'lugares'` ao fim da lista `INSTALLED_APPS`. Aproveite para
ajustar idioma e fuso horário:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'lugares',
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
```

Suba o servidor de desenvolvimento e abra `http://127.0.0.1:8000` no
navegador. Você deve ver o foguete do Django:

```bash
uv run python manage.py runserver
```

Deixe esse terminal aberto e use outro para os próximos comandos. O servidor
recarrega sozinho a cada arquivo salvo. Para parar, `Ctrl+C`.

## O ciclo de uma requisição

Antes de escrever código, vale ter na cabeça o caminho que uma requisição
percorre. Tudo no Django gira em torno deste ciclo:

```{.mermaid width="85%"}
flowchart LR
  B[Navegador] -->|GET /lugares/| U[urls.py]
  U -->|casa a rota| V[views.py]
  V -->|consulta| M[models.py]
  M <-->|SQL| DB[(Banco)]
  V -->|dados| T[template .html]
  T -->|HTML pronto| B
```

1. O navegador pede uma URL.
2. `urls.py` descobre qual **view** cuida daquela URL.
3. A view usa os **models** para ler ou gravar no banco.
4. A view entrega os dados a um **template**, que gera o HTML.
5. O HTML volta para o navegador.

Cada arquivo do app corresponde a um passo. Vamos percorrê-los na ordem em
que você normalmente os escreve: model, admin, view, URL, template.

## Models: as tabelas em Python

Um model é uma classe Python que descreve uma tabela. Cada atributo é uma
coluna. O Django cria a tabela, escreve o SQL e converte linhas em objetos.
Esse tradutor entre objetos e tabelas se chama **ORM** (*Object-Relational
Mapper*).

Substitua o conteúdo de `lugares/models.py`:

```python
from django.db import models


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

    class Meta:
        verbose_name = "lugar"
        verbose_name_plural = "lugares"
        ordering = ["nome"]

    def __str__(self):
        return self.nome
```

O que cada parte faz:

- `CharField`, `TextField`, `BooleanField`, `DateTimeField` são tipos de
  coluna. `max_length` é obrigatório em `CharField`.
- `ForeignKey` cria a relação "um lugar pertence a uma categoria".
  `on_delete=models.PROTECT` impede apagar uma categoria que ainda tenha
  lugares. `related_name="lugares"` permite escrever
  `categoria.lugares.all()`.
- `blank=True` torna o campo opcional nos formulários. O primeiro argumento
  em texto (`"endereço"`) é o rótulo exibido para humanos, útil quando o nome
  do atributo não pode ter acento.
- `auto_now_add=True` preenche a data na criação e nunca mais mexe.
- `class Meta` guarda opções da tabela: nome legível e ordem padrão.
- `__str__` define como o objeto aparece no admin e no shell. Sem ele você
  veria "Lugar object (1)".

Um model só vira tabela depois de duas etapas. `makemigrations` lê os models
e escreve um arquivo em `migrations/` descrevendo o que mudou; `migrate`
aplica esses arquivos no banco:

```bash
uv run python manage.py makemigrations
uv run python manage.py migrate
```

Os arquivos de migração vão para o Git. Eles são o histórico do seu banco, e
é com eles que o banco de um colega, ou o de produção, chega ao mesmo estado
que o seu. Por padrão o Django usa SQLite, um banco em arquivo
(`db.sqlite3`) que não precisa de instalação. Serve muito bem para começar.

### Conversando com o banco pelo shell

O `shell` abre um Python já configurado com o projeto. Desde a versão 5.2 ele
importa automaticamente todos os models, então dá para ir direto ao ponto:

```bash
uv run python manage.py shell
```

```python
cafe = Categoria.objects.create(nome="Café")
parque = Categoria.objects.create(nome="Parque")

Lugar.objects.create(nome="Café da Esquina", categoria=cafe, endereco="Rua A, 10")
Lugar.objects.create(nome="Parque da Cidade", categoria=parque)
Lugar.objects.create(nome="Café Fechado", categoria=cafe, aberto=False)

Lugar.objects.count()                              # 3
Lugar.objects.filter(aberto=True)                  # <QuerySet [<Lugar: Café da Esquina>, <Lugar: Parque da Cidade>]>
Lugar.objects.filter(nome__icontains="café")       # busca sem diferenciar maiúsculas
Lugar.objects.get(pk=1).categoria                  # <Categoria: Café>
cafe.lugares.count()                               # 2, graças ao related_name
Lugar.objects.filter(aberto=True).values_list("nome", flat=True)
```

`objects` é o **manager**: a porta de entrada das consultas. `filter`
devolve um **QuerySet**, que é preguiçoso: o SQL só roda quando você
percorre o resultado. `get` devolve um único objeto e dá erro se não achar
ou se achar mais de um. Os sufixos `__icontains`, `__gte`, `__in` e outros
são os *lookups*, o jeito do ORM de escrever `WHERE`. Saia com `exit()`.

## Admin: o painel que vem de graça

O admin é o motivo pelo qual muita gente escolhe o Django. Com meia dúzia de
linhas você tem uma interface completa para cadastrar, editar, buscar e
filtrar qualquer model. Edite `lugares/admin.py`:

```python
from django.contrib import admin

from .models import Categoria, Lugar


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    search_fields = ["nome"]


@admin.register(Lugar)
class LugarAdmin(admin.ModelAdmin):
    list_display = ["nome", "categoria", "aberto", "criado_em"]
    list_filter = ["categoria", "aberto"]
    search_fields = ["nome", "endereco"]
    ordering = ["nome"]
```

- `@admin.register(Model)` liga a classe de configuração ao model.
- `list_display` escolhe as colunas da listagem.
- `list_filter` cria a barra lateral de filtros.
- `search_fields` liga a caixa de busca a esses campos.

Crie um usuário administrador e entre em `http://127.0.0.1:8000/admin/`:

```bash
uv run python manage.py createsuperuser
```

Cadastre alguns lugares por lá. Tudo o que você fizer no admin vai para as
mesmas tabelas que o shell usou.

## Views e URLs: respondendo a requisições

Uma **view** é uma função (ou classe) que recebe um objeto `request` e
devolve um `response`. Edite `lugares/views.py`:

```python
from django.shortcuts import get_object_or_404, render

from .models import Lugar


def lista_lugares(request):
    lugares = Lugar.objects.filter(aberto=True).select_related("categoria")
    return render(request, "lugares/lista.html", {"lugares": lugares})


def detalhe_lugar(request, pk):
    lugar = get_object_or_404(Lugar, pk=pk)
    return render(request, "lugares/detalhe.html", {"lugar": lugar})
```

- `render` monta um template com um dicionário de dados (o **contexto**) e
  devolve a resposta HTTP.
- `get_object_or_404` busca o objeto ou responde com a página 404, sem você
  precisar tratar a exceção.
- `select_related("categoria")` traz a categoria na mesma consulta SQL, em
  vez de uma consulta extra por lugar. É o remédio para o famoso problema
  "N+1".

Agora as URLs. Cada app tem o seu `urls.py`, e o do projeto inclui os dos
apps. Crie `lugares/urls.py`:

```python
from django.urls import path

from . import views

app_name = "lugares"

urlpatterns = [
    path("", views.lista_lugares, name="lista"),
    path("<int:pk>/", views.detalhe_lugar, name="detalhe"),
]
```

E ligue-o em `config/urls.py`:

```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("lugares/", include("lugares.urls")),
]
```

`<int:pk>` captura um número da URL e o passa para a view como argumento
`pk`. O `name` e o `app_name` permitem se referir à rota como
`lugares:detalhe` nos templates, em vez de escrever o caminho na mão. Se um
dia a URL mudar, nada mais precisa mudar.

### Views baseadas em classe

O Django também oferece views prontas como classes. Uma listagem de objetos
é tão comum que existe a `ListView`:

```python
from django.views.generic import ListView


class LugarListView(ListView):
    model = Lugar
    template_name = "lugares/lista.html"
    context_object_name = "lugares"

    def get_queryset(self):
        return Lugar.objects.filter(aberto=True).select_related("categoria")
```

Na URL, ela entra como `LugarListView.as_view()`. Faz o mesmo que
`lista_lugares`, com menos código nos casos padrão e mais pontos de extensão.
Comece pelas funções: elas mostram o que está acontecendo. Passe para as
classes quando reconhecer o padrão se repetindo.

## Templates: o HTML com lacunas

Um template é um arquivo HTML com uma linguagem pequena dentro: `{{ }}` mostra
um valor e `{% %}` executa uma tag (laço, condição, herança). O Django procura
templates na pasta `templates/` de cada app. A convenção é criar uma subpasta
com o nome do app para evitar conflitos.

Crie `lugares/templates/lugares/base.html`, a "moldura" de todas as páginas:

```html
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>{% block titulo %}Pontos de interesse{% endblock %}</title>
</head>
<body>
  <header>
    <h1><a href="{% url 'lugares:lista' %}">Pontos de interesse</a></h1>
  </header>
  <main>
    {% block conteudo %}{% endblock %}
  </main>
</body>
</html>
```

Depois `lugares/templates/lugares/lista.html`, que **herda** da base e
preenche os blocos:

```html
{% extends "lugares/base.html" %}

{% block titulo %}Lugares abertos{% endblock %}

{% block conteudo %}
  <h2>Lugares abertos</h2>
  {% if lugares %}
    <ul>
      {% for lugar in lugares %}
        <li>
          <a href="{% url 'lugares:detalhe' lugar.pk %}">{{ lugar.nome }}</a>
          <small>({{ lugar.categoria }})</small>
        </li>
      {% endfor %}
    </ul>
  {% else %}
    <p>Nenhum lugar cadastrado ainda.</p>
  {% endif %}
{% endblock %}
```

E `lugares/templates/lugares/detalhe.html`:

```html
{% extends "lugares/base.html" %}

{% block titulo %}{{ lugar.nome }}{% endblock %}

{% block conteudo %}
  <h2>{{ lugar.nome }}</h2>
  <p><strong>Categoria:</strong> {{ lugar.categoria }}</p>
  {% if lugar.endereco %}<p><strong>Endereço:</strong> {{ lugar.endereco }}</p>{% endif %}
  {% if lugar.descricao %}<p>{{ lugar.descricao|linebreaks }}</p>{% endif %}
  <p><small>Cadastrado em {{ lugar.criado_em|date:"d/m/Y H:i" }}</small></p>
  <p><a href="{% url 'lugares:lista' %}">Voltar</a></p>
{% endblock %}
```

Três coisas para reparar:

- `{% extends %}` e `{% block %}` são a herança: a base define os buracos, as
  páginas filhas os preenchem. Mudou o cabeçalho? Muda em um lugar só.
- `{% url 'lugares:detalhe' lugar.pk %}` gera o endereço a partir do nome da
  rota. Nunca escreva `/lugares/3/` na mão.
- `|linebreaks` e `|date:"..."` são **filtros**: pequenas transformações
  aplicadas ao valor. Todo texto vindo do banco é escapado automaticamente,
  então um `<script>` cadastrado por alguém vira texto inofensivo.

Abra `http://127.0.0.1:8000/lugares/` e clique nos lugares. Está tudo
ligado: URL, view, model, template.

## A ferramenta de linha de comando

Você já usou `django-admin` e `manage.py`. São a mesma ferramenta; a
diferença é que `manage.py` já sabe qual é o `settings.py` do seu projeto.
Use `django-admin` só para o `startproject`, e `manage.py` para todo o resto.

Os comandos que você vai usar todo dia:

| Comando                              | O que faz                                                  |
|:-------------------------------------|:-----------------------------------------------------------|
| `runserver`                          | Servidor de desenvolvimento com recarga automática         |
| `startapp <nome>`                    | Cria a estrutura de um app                                 |
| `makemigrations`                     | Gera migrações a partir das mudanças nos models            |
| `migrate`                            | Aplica as migrações no banco                               |
| `showmigrations`                     | Mostra quais migrações já foram aplicadas                  |
| `shell`                              | Python interativo com o projeto carregado                  |
| `createsuperuser`                    | Cria um usuário para o admin                               |
| `check`                              | Procura problemas de configuração sem rodar o servidor     |
| `test`                               | Roda os testes automatizados                               |
| `dbshell`                            | Abre o cliente do banco (`sqlite3`, `psql`...)             |
| `collectstatic`                      | Junta os arquivos estáticos para produção                  |
| `help`                               | Lista todos os comandos; `help <cmd>` detalha um           |

Todos com `uv run python manage.py` na frente. Se cansar de digitar, crie um
alias no seu `~/.zshrc`: `alias dj="uv run python manage.py"`.

## Comandos próprios: automatizando tarefas do projeto

Cedo ou tarde aparece uma tarefa que não é uma página do site: importar uma
planilha que o cliente mandou, apagar registros antigos, recalcular um campo,
enviar um relatório toda segunda-feira. O primeiro impulso é escrever um
`importa.py` solto na raiz do projeto e rodar com `python importa.py`. Faça o
teste:

```python
# importa.py
from lugares.models import Lugar

print(Lugar.objects.count())
```

```bash
uv run python importa.py
# django.core.exceptions.ImproperlyConfigured: Requested setting INSTALLED_APPS,
# but settings are not configured. ...
```

O script quebra antes da primeira linha útil. O motivo: o ORM só funciona
depois que o Django carrega o `settings.py` e registra os apps. É o
`manage.py` quem faz isso. Dá para imitar (definir a variável de ambiente
`DJANGO_SETTINGS_MODULE` e chamar `django.setup()` no topo do script), mas
você estaria reinventando, pior, algo que o Django já oferece: os
**comandos de gerenciamento** (*management commands*).

Um comando próprio é um arquivo Python dentro do app que o `manage.py`
descobre sozinho. Em troca de seguir uma pequena convenção, você ganha:

- **O projeto já carregado.** Settings, apps, banco: tudo pronto quando o
  seu código começa.
- **Argumentos de linha de comando de graça.** Você declara as opções e o
  Django gera o `--help`, valida os tipos e converte os valores, usando o
  `argparse` da biblioteca padrão.
- **As opções que todo comando tem.** `--verbosity`, `--settings`,
  `--traceback`, `--no-color` funcionam sem você escrever nada.
- **Um lugar previsível.** Quem entra no projeto roda `manage.py help` e vê a
  lista de tarefas disponíveis. Um `importa.py` perdido na raiz ninguém
  encontra.
- **Testável.** `call_command("nome")` roda o comando de dentro de um teste
  automatizado.
- **Pronto para o cron e para produção.** Servidores e agendadores rodam
  `manage.py comando` do mesmo jeito que você roda na sua máquina.

### A convenção

O Django procura comandos em `app/management/commands/nome_do_comando.py`.
Cada arquivo define uma classe chamada `Command`, herdando de `BaseCommand`,
com o método `handle`. As duas pastas precisam do `__init__.py`:

```bash
mkdir -p lugares/management/commands
touch lugares/management/__init__.py lugares/management/commands/__init__.py
```

### Exemplo: importar lugares de um CSV

Suponha um arquivo `lugares.csv` assim (a última linha, sem nome, está aí de
propósito):

```
nome,categoria,endereco,aberto
Café da Esquina,Café,"Rua A, 10",sim
Parque da Cidade,Parque,,sim
Café Fechado,Café,"Av. B, 200",não
,Café,,sim
```

Crie `lugares/management/commands/importar_lugares.py`:

```python
import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from lugares.models import Categoria, Lugar


class Command(BaseCommand):
    help = "Importa lugares de um CSV (colunas: nome, categoria, endereco, aberto)."

    def add_arguments(self, parser):
        parser.add_argument("arquivo", type=Path, help="caminho do arquivo CSV")
        parser.add_argument(
            "--separador", default=",", help="separador de colunas (padrão: vírgula)"
        )
        parser.add_argument(
            "--atualizar",
            action="store_true",
            help="atualiza lugares que já existem (pelo nome) em vez de pulá-los",
        )
        parser.add_argument(
            "--simular",
            action="store_true",
            help="mostra o que faria, mas não grava nada no banco",
        )

    def handle(self, *args, **options):
        arquivo: Path = options["arquivo"]
        if not arquivo.exists():
            raise CommandError(f"Arquivo não encontrado: {arquivo}")

        criados = atualizados = pulados = 0

        with arquivo.open(newline="", encoding="utf-8") as f, transaction.atomic():
            leitor = csv.DictReader(f, delimiter=options["separador"])
            obrigatorias = {"nome", "categoria"}
            if not obrigatorias.issubset(leitor.fieldnames or []):
                raise CommandError(
                    f"O CSV precisa das colunas {sorted(obrigatorias)}; "
                    f"encontrei {leitor.fieldnames}"
                )

            for numero, linha in enumerate(leitor, start=2):  # linha 1 é o cabeçalho
                nome = linha["nome"].strip()
                if not nome:
                    aviso = f"linha {numero}: sem nome, pulando"
                    self.stdout.write(self.style.WARNING(aviso))
                    pulados += 1
                    continue

                categoria, _ = Categoria.objects.get_or_create(
                    nome=linha["categoria"].strip()
                )
                aberto = (linha.get("aberto") or "sim").strip().lower()
                dados = {
                    "categoria": categoria,
                    "endereco": (linha.get("endereco") or "").strip(),
                    "aberto": aberto in ("sim", "s", "1", "true"),
                }

                if options["atualizar"]:
                    _, criado = Lugar.objects.update_or_create(
                        nome=nome, defaults=dados
                    )
                    if criado:
                        criados += 1
                    else:
                        atualizados += 1
                else:
                    _, criado = Lugar.objects.get_or_create(
                        nome=nome, defaults=dados
                    )
                    if criado:
                        criados += 1
                    else:
                        pulados += 1

                if options["verbosity"] >= 2:
                    self.stdout.write(f"linha {numero}: {nome} ({categoria})")

            if options["simular"]:
                transaction.set_rollback(True)

        resumo = f"{criados} criados, {atualizados} atualizados, {pulados} pulados"
        if options["simular"]:
            self.stdout.write(
                self.style.NOTICE(f"[simulação] {resumo}; nada foi gravado")
            )
        else:
            self.stdout.write(self.style.SUCCESS(resumo))
```

Vamos pelas partes que importam:

- **`help`** é o texto que aparece em `manage.py help` e no `--help` do
  comando. Escreva sempre.
- **`add_arguments(parser)`** recebe um parser do `argparse`. Argumentos
  sem traço (`arquivo`) são **posicionais** e obrigatórios. Os com `--` são
  **opções**: `--separador` recebe um valor, e `action="store_true"` faz
  `--atualizar` e `--simular` virarem simples ligado/desligado. O
  `type=Path` converte o texto em um objeto `Path` antes de chegar em você.
- **`handle(*args, **options)`** é o corpo. Tudo o que foi declarado chega no
  dicionário `options`, junto com as opções padrão, como `verbosity`.
- **`CommandError`** é o jeito certo de abortar: o Django imprime a mensagem
  em vermelho, sem *traceback*, e termina com código de saída 1 (o que
  scripts e o cron entendem como falha). Com `--traceback` você vê a pilha
  completa.
- **`self.stdout.write`** em vez de `print`: permite capturar a saída nos
  testes e respeita `--no-color`. `self.style.SUCCESS`, `WARNING` e
  `NOTICE` colorem o texto.
- **`transaction.atomic()`** envolve a importação inteira em uma transação:
  se algo der errado no meio, nada fica pela metade. E `set_rollback(True)`
  no fim é o truque do `--simular`: faz tudo, conta tudo, e desfaz.
- **`get_or_create` e `update_or_create`** evitam duplicar registros ao
  rodar o comando duas vezes. Um comando de importação deve ser seguro de
  repetir; esse é o significado de *idempotente*.

### Rodando e explorando os argumentos

O `--help` é gerado a partir do que você declarou, mais as opções que todo
comando tem:

```bash
uv run python manage.py importar_lugares --help
```

```
usage: manage.py importar_lugares [-h] [--separador SEPARADOR] [--atualizar]
                                  [--simular] [--version] [-v {0,1,2,3}]
                                  [--settings SETTINGS] [--pythonpath PYTHONPATH]
                                  [--traceback] [--no-color] [--force-color]
                                  [--skip-checks]
                                  arquivo

Importa lugares de um CSV (colunas: nome, categoria, endereco, aberto).

positional arguments:
  arquivo               caminho do arquivo CSV

options:
  --separador SEPARADOR separador de colunas (padrão: vírgula)
  --atualizar           atualiza lugares que já existem (pelo nome) em vez de pulá-los
  --simular             mostra o que faria, mas não grava nada no banco
  -v, --verbosity {0,1,2,3}
                        Verbosity level; 0=minimal output, 1=normal output, ...
  --settings SETTINGS   The Python path to a settings module ...
  --traceback           Display a full stack trace on CommandError exceptions.
  --no-color            Don't colorize the command output.
```

Primeiro em modo de simulação, para ver o que aconteceria:

```bash
uv run python manage.py importar_lugares lugares.csv --simular
# linha 5: sem nome, pulando
# [simulação] 3 criados, 0 atualizados, 1 pulados; nada foi gravado
```

Agora de verdade, e depois de novo, para ver que repetir é seguro:

```bash
uv run python manage.py importar_lugares lugares.csv
# 3 criados, 0 atualizados, 1 pulados

uv run python manage.py importar_lugares lugares.csv
# 0 criados, 0 atualizados, 4 pulados
```

Mude um endereço no CSV e rode com `--atualizar`, pedindo mais detalhes com
`-v 2`:

```bash
uv run python manage.py importar_lugares lugares.csv --atualizar -v 2
# linha 2: Café da Esquina (Café)
# linha 3: Parque da Cidade (Parque)
# linha 4: Café Fechado (Café)
# linha 5: sem nome, pulando
# 0 criados, 3 atualizados, 1 pulados
```

Um arquivo separado por ponto e vírgula, como o Excel em português costuma
exportar, e um erro de arquivo inexistente:

```bash
uv run python manage.py importar_lugares planilha.csv --separador ";"
uv run python manage.py importar_lugares nao-existe.csv
# CommandError: Arquivo não encontrado: nao-existe.csv
echo $?
# 1
```

E o comando aparece na lista do projeto, sob o nome do app:

```bash
uv run python manage.py help
# ...
# [lugares]
#     importar_lugares
```

### Testando o comando

Como é só uma classe Python, dá para rodá-lo de dentro de um teste com
`call_command`, capturando a saída:

```python
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase

from .models import Lugar


class ImportarLugaresTests(TestCase):
    def test_importa_csv(self):
        with TemporaryDirectory() as pasta:
            csv = Path(pasta) / "lugares.csv"
            csv.write_text("nome,categoria,endereco,aberto\nCafé X,Café,Rua 1,sim\n")
            saida = StringIO()
            call_command("importar_lugares", str(csv), stdout=saida)
        self.assertEqual(Lugar.objects.count(), 1)
        self.assertIn("1 criados", saida.getvalue())
```

## Tabela de referência rápida

| Conceito             | Onde mora                  | Para que serve                                     |
|:---------------------|:---------------------------|:---------------------------------------------------|
| Projeto              | `config/`                  | Configurações e URLs de entrada do site            |
| App                  | `lugares/`                 | Um pedaço do site com uma responsabilidade         |
| Model                | `models.py`                | Descreve uma tabela; o ORM traduz para SQL         |
| Migração             | `migrations/`              | Histórico versionado das mudanças no banco         |
| Manager / QuerySet   | `Model.objects`            | Consultas: `filter`, `get`, `create`, `count`      |
| Admin                | `admin.py`                 | Painel de cadastro pronto                          |
| View                 | `views.py`                 | Recebe `request`, devolve `response`               |
| URLconf              | `urls.py`                  | Liga caminhos a views; rotas nomeadas              |
| Template             | `templates/<app>/`         | HTML com `{{ }}`, `{% %}`, herança e filtros       |
| `settings.py`        | `config/settings.py`       | Apps instalados, banco, idioma, fuso, etc.         |
| `manage.py`          | raiz do projeto            | Linha de comando do projeto                        |
| Comando próprio      | `management/commands/`     | Tarefas do projeto com argumentos e `--help`       |

## Exercícios

Todos no projeto `pontos` deste capítulo.

### Exercício 1: um campo novo

1. Adicione ao model `Lugar` um campo `site = models.URLField(blank=True)`.
2. Rode `makemigrations` e leia o arquivo gerado em `lugares/migrations/`.
3. Rode `migrate`. Depois `showmigrations lugares`.
4. Mostre o campo no admin (em `list_display`) e no template de detalhe,
   como um link.

### Exercício 2: explorando o ORM

No `shell`, descubra como fazer cada uma destas consultas e anote o resultado:

1. Todos os lugares de uma categoria, usando `related_name`.
2. Lugares cujo nome termina com "Cidade" (dica: `__endswith`).
3. Lugares criados hoje (dica: `criado_em__date`).
4. Quantidade de lugares por categoria, usando
   `Categoria.objects.annotate(total=Count("lugares"))`. Você vai precisar
   importar `Count` de `django.db.models`.
5. Rode `print(Lugar.objects.filter(aberto=True).query)` e leia o SQL que o
   ORM gerou.

### Exercício 3: uma página nova

1. Crie a view `lugares_por_categoria(request, categoria_id)` que lista só os
   lugares daquela categoria.
2. Adicione a rota `categoria/<int:categoria_id>/` com o nome `por-categoria`.
3. No template de lista, faça o nome da categoria de cada lugar virar um link
   para essa página.

### Exercício 4: trocando função por classe

1. Reescreva `detalhe_lugar` usando `DetailView` (de
   `django.views.generic`).
2. Troque a rota para usar `.as_view()` e confira que a página continua
   funcionando.
3. Leia o código-fonte de `DetailView` com `uv run python -c "import
   django.views.generic.detail as d; print(d.__file__)"` e abra o arquivo.
   Que método busca o objeto?

### Exercício 5: o primeiro teste

1. Em `lugares/tests.py`, escreva um teste que cria uma categoria e um lugar
   e confere que `str(lugar)` devolve o nome.
2. Escreva outro que usa `self.client.get("/lugares/")` e confere
   `response.status_code == 200` e que o nome do lugar aparece no HTML.
3. Rode `uv run python manage.py test`.

### Exercício 6: um comando de exportação

1. Crie o comando `exportar_lugares` que escreve um CSV com todos os lugares
   (use `csv.DictWriter` e `self.stdout` como destino, para o resultado ir
   para a tela ou para um arquivo com `>`).
2. Adicione a opção `--categoria NOME` para exportar só uma categoria, e
   `--apenas-abertos` (`store_true`).
3. Rode `--help` e confira que as suas opções aparecem com as descrições.
4. Exporte, apague todos os lugares no shell e importe de volta com
   `importar_lugares`. O ciclo fechou?

### Exercício 7: quebrando de propósito

1. Remova `'lugares'` de `INSTALLED_APPS` e rode `check`. Leia o erro.
2. Volte, e agora troque `on_delete=models.PROTECT` por `models.CASCADE`.
   No shell, apague a categoria "Café". O que aconteceu com os lugares?
3. Restaure o `PROTECT`, gere a migração e aplique. Tente apagar a categoria
   de novo.

## Referências

- **Documentação oficial do Django** (versão mais recente):
  <https://docs.djangoproject.com/en/stable/>. O tutorial oficial em sete
  partes: <https://docs.djangoproject.com/en/stable/intro/tutorial01/>.
- **Notas da versão 6.1** (Python suportado, novidades, numeração por ano):
  <https://docs.djangoproject.com/en/6.1/releases/6.1/>.
- **Política de versões e LTS**:
  <https://docs.djangoproject.com/en/stable/internals/release-process/>.
- **Models e campos**:
  <https://docs.djangoproject.com/en/stable/topics/db/models/> e
  <https://docs.djangoproject.com/en/stable/ref/models/fields/>.
- **Consultas (QuerySet, lookups)**:
  <https://docs.djangoproject.com/en/stable/topics/db/queries/> e
  <https://docs.djangoproject.com/en/stable/ref/models/querysets/>.
- **Migrações**: <https://docs.djangoproject.com/en/stable/topics/migrations/>.
- **Admin**: <https://docs.djangoproject.com/en/stable/ref/contrib/admin/>.
- **Views, URLs e views genéricas**:
  <https://docs.djangoproject.com/en/stable/topics/http/views/>,
  <https://docs.djangoproject.com/en/stable/topics/http/urls/>,
  <https://docs.djangoproject.com/en/stable/topics/class-based-views/>.
- **Templates**: <https://docs.djangoproject.com/en/stable/topics/templates/>
  e a referência de tags e filtros,
  <https://docs.djangoproject.com/en/stable/ref/templates/builtins/>.
- **`manage.py` e `django-admin`**:
  <https://docs.djangoproject.com/en/stable/ref/django-admin/>.
- **Comandos próprios (`BaseCommand`, `add_arguments`, `CommandError`,
  `call_command`)**:
  <https://docs.djangoproject.com/en/stable/howto/custom-management-commands/>
  e <https://docs.djangoproject.com/en/stable/ref/django-admin/#running-management-commands-from-your-code>.
- **`argparse`** (a biblioteca por trás dos argumentos):
  <https://docs.python.org/3/library/argparse.html>.
- **Transações (`atomic`, `set_rollback`)**:
  <https://docs.djangoproject.com/en/stable/topics/db/transactions/>.
- **`get_or_create` e `update_or_create`**:
  <https://docs.djangoproject.com/en/stable/ref/models/querysets/#get-or-create>.
- **Shell com importação automática** (desde o 5.2):
  <https://docs.djangoproject.com/en/stable/ref/django-admin/#shell>.
- **uv**: guia de projetos, <https://docs.astral.sh/uv/guides/projects/>; e
  `uv init`, `uv add`, `uv run`,
  <https://docs.astral.sh/uv/reference/cli/>.
- **História do Django**: Django Software Foundation, "Django's history",
  <https://www.djangoproject.com/foundation/>, e a entrevista com Adrian
  Holovaty e Simon Willison na Wikipédia,
  <https://en.wikipedia.org/wiki/Django_(web_framework)>.
