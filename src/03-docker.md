# Docker e Docker Compose

## Por que isso importa

Todo projeto de verdade depende de "serviços": um banco de dados, um cache,
uma fila de tarefas, às vezes um servidor de e-mail de teste. Instalar cada um
deles direto no seu Mac funciona por um tempo, mas logo aparecem os problemas:
o projeto A precisa do PostgreSQL 15 e o projeto B do 17; o colega não
consegue reproduzir o seu ambiente; a máquina nova leva um dia inteiro para
ficar pronta.

O Docker resolve isso empacotando cada serviço em um **container**: um
processo isolado, com o seu próprio sistema de arquivos, que você liga e
desliga com um comando e apaga sem deixar rastro. Neste livro, o Docker vai
ter um papel bem definido: **rodar os serviços** (como o PostGIS do capítulo
de GeoDjango). O código Python continua rodando direto na sua máquina, com o
`uv`. Essa combinação é a mais simples para quem está começando e é bem comum
em times profissionais.

## Uma história curta: de máquinas virtuais a containers

Antes do Docker, isolar um ambiente significava criar uma **máquina virtual**:
um computador inteiro simulado, com seu próprio sistema operacional, ocupando
gigabytes e levando minutos para ligar. Funcionava, mas era pesado.

O Linux, no entanto, já tinha há anos duas peças que permitiam algo mais leve:
os *namespaces* (que fazem um processo enxergar só uma parte do sistema) e os
*cgroups* (que limitam quanto de CPU e memória ele pode usar). Em 2013, uma
empresa chamada dotCloud juntou essas peças com um formato de imagem fácil de
compartilhar e uma ferramenta de linha de comando amigável. Chamou tudo de
Docker. A ideia pegou tão rápido que a empresa mudou o próprio nome.

A diferença fundamental: uma máquina virtual simula o hardware e roda um
sistema operacional completo; um container **compartilha o kernel** do
sistema que já está rodando e isola só o processo. Por isso um container sobe
em menos de um segundo e pesa poucos megabytes.

No Mac há um detalhe curioso: como o macOS não tem o kernel do Linux, o Docker
Desktop roda uma máquina virtual Linux bem pequena por baixo dos panos, e os
containers vivem dentro dela. Você não precisa se preocupar com isso, mas
explica por que o Docker no Mac usa um pouco mais de memória do que no Linux.

## Os três conceitos que você precisa entender

**Imagem.** É o "molde": um pacote somente-leitura com um sistema de arquivos
e um programa pronto para rodar. `postgres:17` é uma imagem. `nginx:alpine` é
outra. Elas ficam guardadas em um registro público, o Docker Hub, e são
baixadas na primeira vez que você usa.

**Container.** É uma imagem em execução. Da mesma imagem você pode criar
quantos containers quiser, cada um isolado dos outros. Quando um container é
removido, tudo o que foi escrito dentro dele some.

**Volume.** É a exceção à regra acima: uma pasta gerenciada pelo Docker que
sobrevive à remoção do container. É onde o banco de dados guarda os dados de
verdade. Sem volume, cada `docker compose down` apagaria o seu banco.

Para fixar, o ciclo completo:

```{.mermaid width="85%"}
flowchart LR
  Hub[(Docker Hub)] -->|docker pull| Img[Imagem]
  Img -->|docker run| C1[Container]
  Img -->|docker run| C2[Outro container]
  C1 <-->|grava dados| V[(Volume)]
  C1 -->|docker stop / rm| X[Removido]
  V -. sobrevive .-> V
```

## Instalando

No Mac, instale o Docker Desktop. Ele traz o `docker`, o `docker compose` e
a máquina virtual Linux que roda por baixo:

```bash
brew install --cask docker
```

Depois abra o aplicativo **Docker** uma vez (ele fica na barra de menus, com
uma baleia). Só quando a baleia parar de se mexer o `docker` está pronto.
Confira:

```bash
docker --version
docker compose version
docker run --rm hello-world
```

O último comando baixa uma imagem minúscula, roda um container que imprime
uma mensagem e o remove (`--rm`). Se apareceu "Hello from Docker!", está
tudo certo.

No Linux, instale o Docker Engine seguindo a documentação oficial da sua
distribuição e adicione o seu usuário ao grupo `docker` para não precisar
de `sudo`.

## Os comandos do dia a dia

### Rodar algo rapidinho

```bash
# roda um comando dentro de um container Alpine e descarta o container
docker run --rm alpine echo "olá do alpine"

# abre um terminal interativo dentro do container (-it) e sai com exit
docker run -it --rm alpine sh
```

Repare em `-it`: `-i` mantém a entrada aberta e `-t` aloca um terminal. Você
vai usar essa dupla sempre que quiser "entrar" em um container.

### Rodar um serviço em segundo plano

```bash
# sobe um nginx, dá um nome a ele e liga a porta 8088 do Mac à porta 80 do container
docker run -d --name meu-nginx -p 8088:80 nginx:alpine

# confere no navegador ou com curl
curl http://localhost:8088
```

`-d` (*detached*) devolve o terminal para você. `-p 8088:80` significa
"porta 8088 da minha máquina → porta 80 dentro do container". A ordem é
sempre **fora:dentro**.

### Ver o que está rodando

```bash
docker ps            # containers em execução
docker ps -a         # inclui os parados
docker images        # imagens baixadas
docker logs meu-nginx        # o que o container escreveu na saída
docker logs -f meu-nginx     # acompanha em tempo real (Ctrl+C para sair)
docker stats                 # CPU e memória de cada container
```

### Entrar em um container que já está rodando

```bash
docker exec -it meu-nginx sh
# dentro dele: cat /etc/os-release, ls /usr/share/nginx/html, exit
```

`exec` é o jeito de rodar um comando extra dentro de um container em
execução. É assim que você vai abrir o `psql` dentro do PostGIS mais adiante.

### Parar, remover, limpar

```bash
docker stop meu-nginx        # para (o container continua existindo)
docker start meu-nginx       # liga de novo
docker rm meu-nginx          # remove (precisa estar parado, ou use rm -f)
docker rmi nginx:alpine      # remove a imagem
docker system prune          # apaga containers parados, redes sem uso e cache
docker system df             # mostra quanto espaço o Docker está usando
```

> **`docker system prune` é seu amigo.** O Docker acumula gigabytes de
> imagens e camadas antigas sem avisar. Rode de vez em quando. Com `-a`
> ele remove também imagens que não estão sendo usadas por nenhum container;
> elas serão baixadas de novo quando precisar.

## Docker Compose: descrevendo os serviços em um arquivo

Digitar `docker run` com dez opções toda vez é chato e propenso a erro. O
**Docker Compose** resolve isso: você descreve os serviços em um arquivo
`docker-compose.yml` na raiz do projeto e sobe tudo com um comando. O arquivo vai
para o Git, e qualquer pessoa que clonar o projeto tem o mesmo ambiente.

Este é o `docker-compose.yml` que vamos usar no capítulo de GeoDjango. Ele sobe
um PostgreSQL 17 com a extensão PostGIS:

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

Lendo linha a linha:

- `services:` lista os containers. Aqui só um, chamado `db`. O nome é você
  quem escolhe e vira o nome de host dentro da rede do Compose.
- `image:` qual imagem usar. A imagem oficial `postgis/postgis` ainda não
  tem versão para Macs com chip Apple (arm64); `imresamu/postgis` é a
  alternativa mantida por um dos autores da oficial e recomendada por ela.
- `environment:` variáveis de ambiente que a imagem lê na primeira
  inicialização para criar o banco, o usuário e a senha.
- `ports:` liga a porta 5432 do Mac à 5432 do container. Assim o Django, que
  roda fora do Docker, enxerga o banco em `localhost:5432`.
- `volumes:` guarda os dados do PostgreSQL no volume `pgdata`, que sobrevive
  a `docker compose down`.
- `healthcheck:` como o Docker sabe que o banco está pronto para receber
  conexões, e não só "ligado". Útil com a opção `--wait` logo abaixo.

Os comandos que você vai usar o tempo todo:

```bash
docker compose up -d           # sobe todos os serviços em segundo plano
docker compose up -d --wait    # idem, mas só volta quando o healthcheck passar
docker compose ps              # estado dos serviços deste projeto
docker compose logs -f db      # logs de um serviço
docker compose exec db psql -U pontos -d pontos   # abre o psql dentro do banco
docker compose stop            # para, mantendo containers e dados
docker compose down            # para e remove containers (dados no volume ficam)
docker compose down -v         # idem e apaga os volumes: recomeça do zero
docker compose pull            # baixa versões novas das imagens
```

O Compose sempre procura o `docker-compose.yml` na pasta atual (ou em uma
pasta acima). Ele também aceita os nomes `compose.yaml` e `compose.yml`, que
você vai ver em projetos mais novos. Por isso rode esses comandos de dentro
da pasta do projeto. Ele
também usa o nome da pasta como prefixo dos containers: em um projeto chamado
`pontos`, o container do banco se chama `pontos-db-1`.

## Um projeto, uma pasta, um Compose

A convenção que este livro segue e que você vai encontrar em muitos times:

```
pontos/
|-- docker-compose.yml serviços (banco, cache...) que rodam no Docker
|-- pyproject.toml    o projeto Python, gerenciado pelo uv
|-- manage.py         o Django, rodando direto na sua máquina
`-- ...
```

O que roda **no Docker**: bancos de dados, Redis, filas, coisas que você não
edita. O que roda **na sua máquina**: o código que você está escrevendo. Isso
mantém o ciclo "editar e ver o resultado" instantâneo, sem reconstruir imagens,
e ao mesmo tempo dá a todo mundo o mesmo banco, na mesma versão.

Colocar o próprio Django dentro de um container é útil para produção e para
projetos maiores. Fica para um capítulo futuro.

## Tabela de referência rápida

| Comando                                  | Objetivo                                              |
|:-----------------------------------------|:------------------------------------------------------|
| `docker run --rm <imagem> <cmd>`         | Rodar um comando avulso e descartar o container       |
| `docker run -it --rm <imagem> sh`        | Abrir um shell interativo em um container novo        |
| `docker run -d --name <n> -p A:B <img>`  | Subir um serviço em segundo plano com nome e porta    |
| `docker ps` / `docker ps -a`             | Listar containers rodando / todos                     |
| `docker images`                          | Listar imagens baixadas                               |
| `docker logs -f <container>`             | Acompanhar a saída de um container                    |
| `docker exec -it <container> <cmd>`      | Rodar um comando dentro de um container em execução   |
| `docker stop` / `start` / `rm`           | Parar, religar, remover um container                  |
| `docker system prune`                    | Limpar containers parados e cache                     |
| `docker compose up -d --wait`            | Subir os serviços do `docker-compose.yml` e esperar ficarem prontos |
| `docker compose ps`                      | Estado dos serviços do projeto                        |
| `docker compose logs -f <serviço>`       | Logs de um serviço                                    |
| `docker compose exec <serviço> <cmd>`    | Comando dentro de um serviço (ex.: `psql`)            |
| `docker compose down`                    | Parar e remover os containers (volumes ficam)         |
| `docker compose down -v`                 | Idem, apagando os volumes (zera o banco)              |

## Exercícios

### Exercício 1: primeiro contato

1. Rode `docker run --rm hello-world` e leia a mensagem inteira. Ela explica,
   em quatro passos, o que aconteceu.
2. Rode `docker images` e encontre a imagem `hello-world`. Qual o tamanho
   dela?
3. Rode `docker ps -a`. O container do hello-world aparece? Por que sim ou
   por que não? (Dica: `--rm`.)

### Exercício 2: explorando um container por dentro

1. Abra um shell no Alpine: `docker run -it --rm alpine sh`.
2. Dentro dele, rode `ls /`, `cat /etc/os-release` e `ps`. Compare com o
   seu Mac: quantos processos existem dentro do container?
3. Crie um arquivo: `echo oi > /tmp/teste.txt`. Saia com `exit`.
4. Abra um novo shell no Alpine e procure o arquivo. Ele existe? O que isso
   ensina sobre containers?

### Exercício 3: um serviço com porta

1. Suba um nginx com `docker run -d --name web -p 8088:80 nginx:alpine`.
2. Abra `http://localhost:8088` no navegador.
3. Veja os logs com `docker logs web`. Recarregue a página e rode os logs de
   novo: apareceu uma linha nova?
4. Entre no container com `docker exec -it web sh` e troque o conteúdo de
   `/usr/share/nginx/html/index.html` usando `echo "<h1>Oi</h1>" > ...`.
   Recarregue o navegador.
5. Pare e remova: `docker stop web && docker rm web`.

### Exercício 4: seu primeiro Compose

1. Crie uma pasta `laboratorio-docker`, entre nela e crie um `docker-compose.yml`
   com um único serviço `web` usando a imagem `nginx:alpine` e a porta
   `8088:80`.
2. Suba com `docker compose up -d` e confira com `docker compose ps`.
3. Rode `docker ps` e repare no nome do container. De onde veio o prefixo?
4. Derrube com `docker compose down`.

### Exercício 5: volumes e persistência

1. No mesmo `docker-compose.yml`, adicione o serviço `db` do exemplo deste capítulo
   (o PostGIS), incluindo o volume `pgdata`.
2. Suba com `docker compose up -d --wait`.
3. Entre no banco: `docker compose exec db psql -U pontos -d pontos` e rode
   `CREATE TABLE teste (id int);` e depois `\dt`. Saia com `\q`.
4. Rode `docker compose down` e depois `docker compose up -d --wait`. Entre
   no banco de novo e rode `\dt`. A tabela sobreviveu?
5. Agora rode `docker compose down -v` e suba de novo. E agora?

### Exercício 6: faxina

1. Rode `docker system df` e anote quanto espaço o Docker está usando.
2. Rode `docker system prune` (leia a pergunta antes de confirmar).
3. Rode `docker system df` de novo e compare.

## Referências

- **Visão geral e conceitos (imagens, containers, volumes)**: Docker,
  "Docker overview", <https://docs.docker.com/get-started/docker-overview/>.
- **Instalação no Mac**: Docker, "Install Docker Desktop on Mac",
  <https://docs.docker.com/desktop/setup/install/mac-install/>. Fórmula do
  Homebrew: <https://formulae.brew.sh/cask/docker>.
- **Referência da linha de comando**: `docker run`, `docker exec`,
  `docker compose` e demais comandos,
  <https://docs.docker.com/reference/cli/docker/>.
- **Arquivo Compose**: especificação e todas as chaves (`services`,
  `volumes`, `healthcheck`...),
  <https://docs.docker.com/reference/compose-file/>.
- **Volumes**: <https://docs.docker.com/engine/storage/volumes/>.
- **A história do Docker**: Solomon Hykes, apresentação na PyCon US 2013,
  <https://www.youtube.com/watch?v=wW9CAH9nSLs>; e a página da Wikipédia,
  <https://en.wikipedia.org/wiki/Docker_(software)>.
- **Namespaces e cgroups do Linux**: `man 7 namespaces` e `man 7 cgroups`,
  disponíveis em <https://man7.org/linux/man-pages/man7/namespaces.7.html>
  e <https://man7.org/linux/man-pages/man7/cgroups.7.html>.
- **Imagem PostGIS**: oficial, <https://hub.docker.com/r/postgis/postgis>
  (que indica a alternativa para arm64); alternativa usada aqui,
  <https://hub.docker.com/r/imresamu/postgis>.
- **Imagem oficial do PostgreSQL** (variáveis `POSTGRES_*`):
  <https://hub.docker.com/_/postgres>.
