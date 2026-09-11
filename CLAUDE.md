# CLAUDE.md

"Manual do desenvolvedor iniciante": livro-toolbox para um iniciante em
Python/Django, escrito por Jon Trigueiro e Claude. Cresce um capítulo por
missão.

## Build

```bash
make pdf | html | epub | mobi | all | ebooks | serve | clean
```

- pandoc + typst (`brew install pandoc typst`); MOBI precisa do Calibre.
- Saída em `build/` (ignorado). Capítulos em `src/`, ordenados pelo prefixo numérico.
- Sem Chrome local: para conferir o PDF, renderize páginas com
  `typst compile --format png`.
- CI roda só em tags `vX.Y.Z` e anexa PDF/EPUB/MOBI à release.

## Conteúdo

- Português do Brasil, linguagem simples e um pouco verbosa, foco em motivação.
- Cada capítulo: `# Título` → `## Por que isso importa` → corpo com blocos
  ```bash / ```python executáveis → tabela de referência (se couber) →
  `## Exercícios` (5–6) → `## Referências` (URLs de onde veio a informação).
- `src/01-introducao.md` é do Jon; não reescrever.
- Diagramas: blocos ```mermaid (filtro em `filters/mermaid.lua`).
- Sem caracteres de desenho de caixa (├──) em blocos de código: use ASCII.

## Ao adicionar um capítulo

1. Criar `src/NN-nome.md`.
2. Em `metadata.yaml`: acrescentar a tecnologia em `stack` e subir `version`.
3. `make all` e conferir o PDF.

## Git

- Conventional commits; não fazer push sem pedir.
- Não commitar `docs/specs/` (já ignorado).
