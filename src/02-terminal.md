# Usando o Terminal

## Por que isso importa

Quase tudo que você vai fazer como desenvolvedor Python/Django passa pelo
terminal: criar um projeto, instalar bibliotecas, rodar o servidor, executar
testes, usar o Git, subir para produção. Dá para fazer algumas dessas coisas
clicando em botões, mas o terminal é onde as ferramentas "de verdade" moram e
onde a documentação, os tutoriais e os colegas mais experientes vão apontar.

Aprender a se mover pelo terminal é como aprender a andar antes de correr. Não
precisa decorar centenas de comandos. Precisa de um punhado deles, entender
onde você está, para onde quer ir e como olhar em volta. Este capítulo é sobre
exatamente isso.

## Uma história curta: Unix, POSIX e a beleza das coisas simples

No fim dos anos 1960, um grupo de pesquisadores do Bell Labs (entre eles Ken
Thompson e Dennis Ritchie) começou a escrever um sistema operacional para um
computador pequeno e barato que sobrou no laboratório. Eles tinham acabado de
sair de um projeto enorme e complicado chamado Multics, e queriam o oposto:
algo pequeno, que uma pessoa conseguisse entender por inteiro. Como piada com
o nome do projeto anterior, chamaram o novo sistema de **Unix**.

O Unix ficou famoso não só pelo que fazia, mas pelo *jeito* de pensar que ele
carregava. Mais tarde, Doug McIlroy resumiu esse jeito em uma frase que virou
a "filosofia Unix":

> Faça cada programa fazer uma coisa só, e fazê-la bem. Escreva programas que
> trabalhem juntos. Escreva programas que lidem com fluxos de texto, porque
> texto é uma interface universal.

Na prática, isso significa que, em vez de um programa gigante que faz tudo,
você tem dezenas de programas pequenos: um que lista arquivos (`ls`), um que
conta linhas (`wc`), um que procura texto (`grep`), um que ordena (`sort`). E
você conecta um ao outro com um "cano" (o caractere `|`, chamado de *pipe*):
a saída de um vira a entrada do próximo.

```bash
# Quantos arquivos e pastas existem na sua pasta pessoal?
ls ~ | wc -l
```

Repare que ninguém escreveu um comando "conte-os-arquivos-da-minha-pasta".
Dois programas simples, combinados, resolveram o problema. Essa é a ideia.

O Unix se espalhou por universidades e empresas, e cada uma fez a sua versão,
com pequenas diferenças. Para evitar que um programa escrito em um Unix não
rodasse em outro, criou-se um padrão chamado **POSIX** (*Portable Operating
System Interface*), publicado pelo IEEE a partir de 1988. O POSIX define o
comportamento esperado do sistema e de um conjunto de comandos básicos. É por
isso que `ls`, `cd`, `cp`, `mv` funcionam praticamente igual em qualquer
sistema "tipo Unix".

E onde o seu Mac e o Linux entram nessa história?

- O **macOS** descende diretamente do Unix: por baixo da interface bonita há um
  sistema chamado Darwin, herdeiro do BSD (a versão do Unix feita em
  Berkeley). O macOS é, inclusive, certificado oficialmente como Unix.
- O **Linux** foi escrito do zero por Linus Torvalds em 1991, mas seguindo a
  mesma filosofia e o padrão POSIX. As ferramentas de linha de comando (a
  maioria do projeto GNU) fazem ele se comportar como um Unix.

Resultado: o que você aprender aqui no Mac vale quase inteiro no Linux, que é
onde os servidores Django geralmente rodam. Esse é um investimento que paga
duas vezes.

## As ferramentas para prosperar nessa estrada

Você não precisa de muita coisa. Estas são as peças que vale conhecer pelo
nome:

**O terminal.** É o programa com a janela onde você digita. No Mac ele já vem
instalado: abra o Spotlight (`⌘ + Espaço`), digite `Terminal` e aperte Enter.
Muita gente prefere instalar o [iTerm2](https://iterm2.com/), que tem mais
recursos, mas o Terminal.app padrão funciona bem para começar. No Linux, o
nome varia (GNOME Terminal, Konsole, etc.), mas a ideia é a mesma.

**O shell.** É o programa que roda *dentro* do terminal e interpreta o que você
digita. O terminal é a janela; o shell é quem entende os comandos. No macOS
moderno o shell padrão é o **zsh**; em muitos Linux é o **bash**. Os dois são
quase idênticos para o uso do dia a dia. Para saber qual você está usando:

```bash
echo $SHELL
```

**As páginas de manual (`man`).** Praticamente todo comando vem com um manual
embutido. É a documentação oficial, sempre à mão, sem internet:

```bash
man ls
```

Use as setas para rolar, `/` seguido de uma palavra para procurar, e `q` para
sair. No começo o manual parece assustador, mas ele tem uma estrutura fixa
(nome, sinopse, descrição, opções) e você aprende a ler só a parte que
interessa. Uma versão mais curta e amigável é o `tldr`, que pode ser instalado
depois (`brew install tldr`).

**Um gerenciador de pacotes.** No Mac, é o [Homebrew](https://brew.sh/). Ele
instala programas de linha de comando com um comando só, por exemplo
`brew install git`. No Linux, o equivalente é o `apt` (Debian/Ubuntu), `dnf`
(Fedora) ou `pacman` (Arch).

**Um editor de texto.** Você vai passar muito tempo dentro de um editor. Um
editor gráfico como o VS Code é uma ótima escolha. Vale também conhecer o
mínimo do `nano`, que roda dentro do terminal e serve para editar um arquivo
rápido em um servidor.

**Autocompletar com Tab.** Esta é a ferramenta mais importante e a mais
subestimada. Ao digitar o começo de um nome de arquivo, pasta ou comando,
aperte `Tab`: o shell completa o resto para você. Se houver mais de uma
opção, aperte `Tab` duas vezes para ver todas. Isso evita erros de digitação e
faz você navegar muito mais rápido. Use sem moderação.

## Como o Mac é organizado por dentro

Um sistema Unix organiza tudo (arquivos, pastas, discos, até dispositivos)
em uma única árvore. A raiz dessa árvore é a pasta `/`, chamada simplesmente
de "raiz" (*root*). Tudo o mais está pendurado abaixo dela.

```
/
|-- Applications/        Programas gráficos (Safari, VS Code...)
|-- Library/             Configurações e dados compartilhados por todos os usuários
|-- System/              O macOS em si. Não mexa aqui.
|-- Users/               As pastas pessoais de cada usuário
|   `-- jon/             A SUA pasta pessoal (chamada de "home")
|       |-- Desktop/
|       |-- Documents/
|       |-- Downloads/
|       |-- Library/     Configurações e caches só do seu usuário (oculta no Finder)
|       `-- .zshrc       Arquivo de configuração do seu shell (oculto)
|-- Volumes/             Discos externos, pendrives e imagens montadas
|-- bin/                 Comandos essenciais (ls, cp, mv...)
|-- usr/                 Mais programas e bibliotecas do sistema
|   |-- bin/             A maior parte dos comandos que você usa
|   `-- local/           Programas instalados por você ou por instaladores
|-- opt/
|   `-- homebrew/        Onde o Homebrew instala tudo em Macs com chip Apple
|-- etc/                 Configurações do sistema (aponta para /private/etc)
|-- tmp/                 Temporários; o sistema apaga sozinho (aponta para /private/tmp)
`-- private/             Onde etc, tmp e var realmente moram no macOS
```

Alguns pontos que valem atenção:

- **Sua pasta pessoal** fica em `/Users/<seu-usuário>`. É ali que você vai
  criar seus projetos. O shell tem um atalho para ela: o til, `~`. Escrever
  `~/Documents` é o mesmo que escrever `/Users/jon/Documents`.
- **`/System` e `/usr/bin` são do sistema.** Você raramente precisa entrar ali
  e o macOS protege essas pastas contra alterações.
- **Programas que você instala** (Python de verdade, Git novo, Node...)
  costumam ir para `/opt/homebrew` (chip Apple) ou `/usr/local` (Intel).
- **O Linux é parecido, mas não igual.** Lá as pastas pessoais ficam em
  `/home/<usuário>` em vez de `/Users`, não existe `/Applications`, e `/etc`
  e `/tmp` são pastas reais em vez de atalhos. O resto (`/bin`, `/usr`,
  `/tmp`, `/var`) segue a mesma lógica.

## Se localizando e se movendo

O terminal tem sempre um "lugar onde você está": o **diretório de trabalho
atual** (*current working directory*). Todo comando que mexe com arquivos
parte dali. Por isso os três primeiros comandos que você precisa aprender são
"onde estou?", "o que tem aqui?" e "quero ir para lá".

### Onde estou? (`pwd`)

```bash
pwd
```

`pwd` significa *print working directory*. Ele imprime o caminho completo da
pasta em que você está. Ao abrir o terminal, você quase sempre começa na sua
pasta pessoal, então a resposta deve ser algo como `/Users/jon`.

### O que tem aqui? (`ls`)

```bash
ls
```

`ls` (*list*) mostra o conteúdo da pasta atual. Ele tem algumas opções muito
usadas, e você pode combiná-las:

```bash
ls -l      # formato longo: permissões, dono, tamanho, data
ls -a      # mostra também os arquivos ocultos (que começam com ponto)
ls -la     # os dois juntos
ls -lh     # tamanhos "humanos": 4.0K, 1.2M em vez de bytes
ls ~/Downloads   # lista outra pasta, sem precisar entrar nela
```

### Quero ir para lá (`cd`)

```bash
cd Documents
```

`cd` (*change directory*) muda a pasta atual. Ele aceita um caminho **relativo**
(a partir de onde você está, como `Documents`) ou **absoluto** (a partir da
raiz, começando com `/`, como `/Users/jon/Documents`). Alguns atalhos que você
vai usar o tempo todo:

```bash
cd            # sem nada: volta para a sua pasta pessoal
cd ~          # mesma coisa, explicitamente
cd ..         # sobe um nível (para a pasta "pai")
cd ../..      # sobe dois níveis
cd -          # volta para a pasta em que você estava antes
cd /          # vai para a raiz do sistema
```

Os dois nomes especiais `.` e `..` existem em toda pasta: `.` é "a pasta
atual" e `..` é "a pasta acima". Você vai vê-los quando rodar `ls -a`.

Um roteiro completo para sentir isso na prática:

```bash
cd ~                 # começa de casa
pwd                  # /Users/jon
cd Documents         # entra em Documents (caminho relativo)
pwd                  # /Users/jon/Documents
cd ..                # sobe
pwd                  # /Users/jon
cd /usr/bin          # pula para outro lugar (caminho absoluto)
ls | head            # os 10 primeiros programas de lá
cd -                 # volta para /Users/jon
```

### Caminhos com espaço e o Tab

Pastas com espaço no nome, como `Meus Projetos`, precisam de aspas ou de uma
barra invertida antes do espaço:

```bash
cd "Meus Projetos"
cd Meus\ Projetos
```

Ou, mais simples: digite `cd Meus` e aperte `Tab`. O shell completa e escapa
tudo sozinho.

## Arquivos ocultos

No Unix, qualquer arquivo ou pasta cujo nome começa com um ponto (`.`) é
considerado **oculto**. Não há nada de especial na proteção deles: é só uma
convenção para não poluir a listagem. Por padrão, `ls` e o Finder não os
mostram.

É neles que moram configurações. Alguns que você vai encontrar na sua pasta
pessoal:

| Arquivo/pasta | O que é                                                   |
|:--------------|:----------------------------------------------------------|
| `.zshrc`      | Configuração do zsh: aliases, variáveis, o que carregar     |
| `.gitconfig`  | Seu nome, e-mail e preferências do Git                     |
| `.ssh/`       | Chaves para acessar servidores e o GitHub                  |
| `.config/`    | Configurações de vários programas modernos                 |
| `.DS_Store`   | Metadados do Finder (aparece em toda pasta; pode ignorar)  |

Para ver os ocultos, use `ls -a`:

```bash
cd ~
ls -a
```

Dentro de um projeto Django você vai ver arquivos ocultos importantes, como
`.git/` (o histórico do Git), `.env` (segredos e configurações) e
`.gitignore` (o que o Git deve ignorar).

No Finder, o atalho `⌘ + Shift + .` alterna a exibição de arquivos ocultos.

## Criando, copiando, movendo e apagando

Depois de saber andar, você vai querer mexer nas coisas.

```bash
mkdir projetos               # cria uma pasta
mkdir -p projetos/site/app   # cria toda a cadeia de pastas de uma vez
touch notas.txt              # cria um arquivo vazio (ou atualiza a data de um existente)
cp notas.txt copia.txt       # copia um arquivo
cp -r projetos backup        # copia uma pasta inteira (-r = recursivo)
mv copia.txt rascunho.txt    # renomeia (mover e renomear são a mesma operação)
mv rascunho.txt projetos/    # move para dentro de uma pasta
rm rascunho.txt              # apaga um arquivo
rm -r backup                 # apaga uma pasta e tudo dentro dela
```

> **Cuidado com `rm`.** No terminal não existe Lixeira. O que você apaga com
> `rm` vai embora de verdade. Antes de rodar `rm -r`, use `ls` para
> conferir o que está prestes a apagar. E nunca rode `rm -rf /` ou variações
> que alguém "engraçadinho" mande na internet.

## Olhando dentro dos arquivos

```bash
cat notas.txt          # imprime o arquivo inteiro na tela
less arquivo-grande.log   # abre página por página (q para sair, / para procurar)
head -n 20 arquivo.txt # as 20 primeiras linhas
tail -n 20 arquivo.txt # as 20 últimas linhas
tail -f servidor.log   # fica acompanhando o fim do arquivo em tempo real (ótimo para logs)
```

E para descobrir onde um programa está instalado ou se ele existe:

```bash
which python3
which git
```

## Tabela de referência rápida

| Comando            | Objetivo                                                     |
|:-------------------|:-------------------------------------------------------------|
| `pwd`              | Mostrar em que pasta você está                               |
| `ls`, `ls -la`     | Listar o conteúdo de uma pasta (com ocultos e detalhes)      |
| `cd <pasta>`       | Entrar em uma pasta                                          |
| `cd ..`            | Subir um nível                                               |
| `cd` ou `cd ~`     | Voltar para a pasta pessoal                                  |
| `cd -`             | Voltar para a pasta anterior                                 |
| `mkdir -p <a/b/c>` | Criar pasta(s), inclusive intermediárias                     |
| `touch <arquivo>`  | Criar arquivo vazio                                          |
| `cp <de> <para>`   | Copiar (com `-r` para pastas)                                |
| `mv <de> <para>`   | Mover ou renomear                                            |
| `rm <arquivo>`     | Apagar (com `-r` para pastas). Sem lixeira!                  |
| `cat <arquivo>`    | Mostrar o conteúdo de um arquivo                             |
| `less <arquivo>`   | Ler um arquivo grande com paginação                          |
| `head`, `tail`     | Ver o começo ou o fim de um arquivo                          |
| `grep <texto> <arquivo>` | Procurar um texto dentro de arquivos                   |
| `find . -name "*.py"`  | Procurar arquivos pelo nome a partir da pasta atual      |
| `echo <texto>`     | Imprimir texto (útil para ver variáveis: `echo $HOME`)       |
| `which <programa>` | Descobrir onde um programa está instalado                    |
| `man <comando>`    | Abrir o manual de um comando                                 |
| `open .`           | (Mac) Abrir a pasta atual no Finder                          |
| `clear` ou `Ctrl+L`| Limpar a tela                                                |
| `Ctrl+C`           | Interromper o comando que está rodando                       |
| `Tab`              | Autocompletar nomes                                          |
| `↑` / `↓`          | Navegar pelo histórico de comandos                           |
| `history`          | Ver os últimos comandos digitados                            |
| &#124; (pipe)      | Ligar a saída de um comando à entrada de outro               |

## Exercícios

Faça todos no seu próprio terminal. Não copie e cole sem ler: digite, erre,
corrija. O objetivo é criar memória nos dedos.

### Exercício 1: onde estou?

Abra um terminal novo.

1. Descubra em que pasta você está com `pwd`.
2. Confirme que essa pasta é a mesma que `~` apontando: rode `echo ~` e
   compare.
3. Rode `echo $HOME`. A variável `HOME` é de onde o shell tira o valor de `~`.

Pergunta para responder por escrito: o que aconteceria com `~` se você
estivesse logado com outro usuário?

### Exercício 2: entrando e saindo de pastas

1. Vá para `~/Documents` usando um caminho relativo.
2. Volte para a pasta pessoal com `cd ..`.
3. Vá para `~/Documents` de novo, agora usando o caminho **absoluto**
   (começando com `/Users/`).
4. Pule para `/tmp` e confirme com `pwd`. Repare que no Mac o `pwd` pode
   mostrar `/private/tmp`: `/tmp` é um atalho para lá.
5. Use `cd -` para voltar para onde estava. Use `cd -` de novo. O que
   aconteceu?

### Exercício 3: montando uma arvore de pastas

1. A partir da pasta pessoal, crie de uma só vez a estrutura
   `~/laboratorio/projeto1/app` usando `mkdir -p`.
2. Entre em `~/laboratorio/projeto1/app` e crie ali um arquivo vazio chamado
   `main.py` com `touch`.
3. Ainda dentro de `app`, liste o conteúdo de `~/laboratorio` **sem sair** de
   onde você está (dica: `ls` aceita um caminho).
4. Suba dois níveis com um único `cd` e confirme com `pwd`.

### Exercício 4: arquivos ocultos

1. Na sua pasta pessoal, rode `ls` e depois `ls -a`. Anote três nomes que só
   aparecem na segunda listagem.
2. Veja se existe um arquivo `.zshrc`. Se existir, mostre o conteúdo com
   `cat ~/.zshrc`. Se não existir, crie um vazio com `touch ~/.zshrc`.
3. Dentro de `~/laboratorio`, crie um arquivo chamado `.segredo` com o
   comando `echo "senha123" > ~/laboratorio/.segredo`.
4. Prove que ele está lá com `ls -a` e leia o conteúdo com `cat`.
5. No Finder, abra `~/laboratorio` (`open ~/laboratorio`) e use
   `⌘ + Shift + .` para ver o arquivo aparecer e sumir.

### Exercício 5: copiar, mover, renomear, apagar

Continue dentro de `~/laboratorio`.

1. Copie `projeto1` inteiro para `projeto2` (lembre do `-r`).
2. Renomeie `projeto2/app/main.py` para `projeto2/app/manage.py` usando `mv`.
3. Mova o arquivo `.segredo` para dentro de `projeto1`.
4. Liste tudo de forma recursiva com `ls -R ~/laboratorio` e confira se a
   árvore ficou como você esperava.
5. Apague `projeto2` com `rm -r`. Antes de apertar Enter, rode `ls projeto2`
   para conferir o que vai embora.

### Exercício 6: lendo o manual e combinando comandos

1. Abra `man ls` e descubra o que a opção `-t` faz. Saia com `q`.
2. Use `ls -lt ~/Downloads | head -n 5` para ver os 5 arquivos mais recentes
   da sua pasta de downloads. Explique, com suas palavras, o que cada pedaço
   desse comando faz.
3. Descubra quantos arquivos ocultos existem na sua pasta pessoal combinando
   `ls -a ~`, `grep "^\."` e `wc -l` com pipes.
4. Use `which python3` e depois `ls -l` no caminho que apareceu. Se aparecer
   uma seta (`->`), o arquivo é um *link simbólico*: um atalho para outro
   lugar. Para onde ele aponta?

Quando terminar, apague a pasta `~/laboratorio` inteira. Você já sabe como.

## Referências

Estas são as fontes de onde as informações deste capítulo foram tiradas.
Vale a pena visitar as que despertarem curiosidade.

- **A filosofia Unix e a frase de Doug McIlroy**: prefácio do *Bell System
  Technical Journal*, vol. 57, nº 6, 1978, reproduzido em
  <https://en.wikipedia.org/wiki/Unix_philosophy>.
- **A história do Unix no Bell Labs**: Dennis Ritchie, "The Evolution of the
  Unix Time-sharing System", 1979,
  <https://www.bell-labs.com/usr/dmr/www/hist.html>.
- **O padrão POSIX**: IEEE Std 1003.1 / The Open Group Base Specifications,
  <https://pubs.opengroup.org/onlinepubs/9799919799/>. A lista de utilitários
  padronizados está em
  <https://pubs.opengroup.org/onlinepubs/9799919799/utilities/contents.html>.
- **macOS como Unix certificado**: registro do Open Group,
  <https://www.opengroup.org/openbrand/register/>.
- **Estrutura de pastas do macOS**: Apple, "File System Basics",
  <https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/FileSystemProgrammingGuide/FileSystemOverview/FileSystemOverview.html>.
  Também a página de manual `man hier` no próprio Mac.
- **Estrutura de pastas do Linux**: Filesystem Hierarchy Standard (FHS) 3.0,
  <https://refspecs.linuxfoundation.org/FHS_3.0/fhs/index.html>.
- **Manuais dos comandos**: GNU Coreutils,
  <https://www.gnu.org/software/coreutils/manual/coreutils.html>, e as
  páginas `man pwd`, `man ls`, `man cd`, `man mkdir`, `man cp`, `man mv`,
  `man rm`, `man cat`, `man less` no macOS.
- **Terminal do macOS**: Apple, "Terminal User Guide",
  <https://support.apple.com/guide/terminal/welcome/mac>.
- **zsh**: manual oficial, <https://zsh.sourceforge.io/Doc/>.
- **Homebrew**: <https://brew.sh/>.
- **tldr pages**: <https://tldr.sh/>.
