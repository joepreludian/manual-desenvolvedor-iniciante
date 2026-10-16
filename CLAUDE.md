# CLAUDE.md

"Manual do desenvolvedor iniciante": livro-toolbox para um iniciante em
Python/Django, escrito por Jon Trigueiro e Claude. Cresce um capítulo por
missão.

## Build

```bash
make pdf | html | epub | mobi | all | ebooks | serve | changelog | clean
```

- pandoc + typst (`brew install pandoc typst`); MOBI precisa do Calibre.
- Saída em `build/` (ignorado). Capítulos em `src/`, ordenados pelo prefixo numérico.
- Sem Chrome local: para conferir o PDF, renderize páginas com
  `typst compile --root . --format png --ppi 72 --pages 86-90 build/manual.typ out/p{p}.png`
  (a página N do Typst é a N-1 impressa no rodapé; para achar o intervalo de
  um capítulo, `uv run --with pypdf python` e procure o título no texto).
- `make all` gera só PDF e HTML; `make ebooks` gera EPUB/MOBI.
- Se um diagrama mermaid sair no PDF como bloco de código, o mermaid-cli não
  achou o navegador: `npx -y puppeteer browsers install chrome-headless-shell`
  (a versão que ele pede aparece no erro), depois `touch src/NN-x.md` e
  `make pdf` para o `.typ` ser gerado de novo.
- CI roda só em tags `vX.Y.Z` e anexa PDF/EPUB/MOBI à release.

## Conteúdo

- Português do Brasil, linguagem simples e um pouco verbosa, foco em motivação.
- Cada capítulo: `# Título` → `## Por que isso importa` → corpo com blocos
  ```bash / ```python executáveis → tabela de referência (se couber) →
  `## Exercícios` (5–6) → `## Referências` (URLs de onde veio a informação).
- Saídas de comandos aparecem como comentários `# ...` dentro do bloco e devem
  vir de execução real; APIs públicas usadas: ViaCEP, BrasilAPI, Nominatim
  (exige `User-Agent`), Open-Meteo, httpbin.org.
- Antes de fechar um capítulo, confira as URLs das referências:
  `grep -o 'https://[^>)]*' src/NN-x.md | sort -u | xargs -n1 curl -sIL -o /dev/null -w '%{http_code} %{url_effective}\n'`.
- `src/01-introducao.md` é do Jon; não reescrever.
- Diagramas: blocos ```mermaid (filtro em `filters/mermaid.lua`).
  Em `sequenceDiagram`, texto de várias linhas vai em `Note over A,B` com
  `<br/>`, não no rótulo da seta (sobrepõe a linha no PNG).
- Figuras estáticas: SVG em `assets/figuras/`, gerados por
  `assets/figuras/gerar.py`, incluídos com `![legenda](assets/figuras/x.svg){width=..}`
  (filtro em `filters/figures.lua`: caminho para o Typst, SVG inline no HTML).
- Sem caracteres de desenho de caixa (├──) em blocos de código: use ASCII.
- Arquivo do Compose chama-se `docker-compose.yml` (nunca `compose.yaml`).
- Serviços rodam no Docker Compose; o código Python roda local com `uv run`.

## Ao adicionar um capítulo

A introdução não conta na numeração do PDF: o "capítulo N" é `src/(N+1)-nome.md`.

1. Criar `src/NN-nome.md`.
2. Em `metadata.yaml`: acrescentar a tecnologia em `stack` e subir `version`.
   Acrescentar a mesma tecnologia na lista de `site/index.html`.
3. Registrar a versão no topo de `CHANGELOG.md` (correções com
   `**Correção:**`) e rodar `make changelog` para atualizar a tabela da homepage.
4. `make all` e conferir o PDF.

## Homepage

- `site/` (Tailwind via CDN, mesmas cores da capa) é publicada no GitHub Pages
  por `.github/workflows/pages.yml` a cada push na main que mexa em `site/`.
- Domínio: manual-desenvolvedor-iniciante.jon.dev.br (`site/CNAME`).
- Downloads apontam para `releases/latest/download/manual.{pdf,epub,mobi}`.

## Git

- Conventional commits; não fazer push sem pedir.
- Não commitar `docs/specs/` (já ignorado).
