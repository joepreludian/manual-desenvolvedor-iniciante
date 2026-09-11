# Manual do desenvolvedor iniciante

Um "toolbox" em formato de livro para quem está começando em Python e Django.
Escrito em português do Brasil, com foco em **motivação**, **exemplos
executáveis** e **referências** ao fim de cada capítulo.

## Requisitos

```bash
brew install pandoc typst
brew install --cask calibre   # só para gerar o MOBI
```

## Como construir

```bash
make pdf     # gera build/manual.pdf
make html    # gera build/manual.html (blocos de código viram editores Ace)
make epub    # gera build/manual.epub (capa = primeira página do PDF)
make mobi    # gera build/manual.mobi (precisa do Calibre)
make all     # pdf + html
make ebooks  # epub + mobi
make serve   # serve o HTML em http://localhost:8000/manual.html
make clean   # apaga build/
```

O HTML carrega o [Ace Editor](https://ace.c9.io/) de um CDN, então precisa de
internet na primeira abertura. Sem rede, os blocos de código aparecem como
texto normal.

## CI

O workflow em `.github/workflows/build.yml` roda só quando uma tag `vX.Y.Z`
(a mesma versão de `metadata.yaml`) é enviada, ou por disparo manual na aba
Actions. Ele gera PDF, EPUB e MOBI, publica os três como artefato e os anexa
a uma release do GitHub:

```bash
git tag v1.0.0 && git push origin main --tags
```

## Estrutura

```
metadata.yaml        título, autores, versão, stack coberta (capa), opções de layout
src/                 capítulos em Markdown, na ordem do prefixo numérico
  01-introducao.md   introdução (escrita pelo Jon)
  02-terminal.md     capítulo 1: Usando o Terminal
templates/
  book.typst         template pandoc → Typst (capa, cabeçalho, estilos)
  book.html          template pandoc → HTML (capa, sumário lateral)
assets/
  style.css          estilo do HTML
  epub.css           estilo do EPUB/MOBI
  ace-blocks.js      transforma blocos de código em editores Ace
build/               saída gerada (ignorada pelo git)
```

## Como adicionar um capítulo

1. Crie `src/NN-nome.md` com o próximo número livre.
2. Siga o formato dos capítulos existentes:
   - `# Título` (nível 1)
   - `## Por que isso importa` (motivação)
   - corpo com blocos ```bash / ```python executáveis
   - `## Tabela de referência rápida` (quando fizer sentido)
   - `## Exercícios`
   - `## Referências` (de onde a informação foi tirada)
3. Acrescente a tecnologia à lista `stack` e suba `version` em `metadata.yaml`.
4. `make all`.
