# Manual do desenvolvedor — Python/Django
#
# Alvos:
#   make pdf    -> build/manual.pdf   (pandoc + typst)
#   make html   -> build/manual.html  (pandoc + Ace Editor)
#   make epub   -> build/manual.epub  (pandoc, capa gerada pelo typst)
#   make mobi   -> build/manual.mobi  (calibre ebook-convert a partir do epub)
#   make all    -> pdf + html
#   make ebooks -> epub + mobi
#   make serve  -> abre um servidor local para ler o HTML
#   make clean  -> apaga build/

SHELL    := /bin/bash
PANDOC   ?= pandoc
TYPST    ?= typst
# No macOS o Calibre instala o ebook-convert dentro do .app
EBOOK_CONVERT ?= $(shell command -v ebook-convert 2>/dev/null || echo /Applications/calibre.app/Contents/MacOS/ebook-convert)
BUILD    := build
SRC      := $(sort $(wildcard src/*.md))
META     := metadata.yaml
OUT_PDF  := $(BUILD)/manual.pdf
OUT_HTML := $(BUILD)/manual.html
OUT_EPUB := $(BUILD)/manual.epub
OUT_MOBI := $(BUILD)/manual.mobi
COVER    := $(BUILD)/cover.png

COMMON_FLAGS := --from markdown+smart --metadata-file=$(META) --toc \
                --syntax-highlighting=assets/vscode-dark.theme --resource-path=.:src \
                --lua-filter=filters/mermaid.lua

.PHONY: all ebooks pdf html epub mobi cover serve clean check-tools

all: pdf html

ebooks: epub mobi

pdf: check-tools $(OUT_PDF)

html: $(OUT_HTML)

epub: check-tools $(OUT_EPUB)

mobi: $(OUT_MOBI)

cover: check-tools $(COVER)

$(BUILD):
	mkdir -p $(BUILD)

$(OUT_PDF): $(SRC) $(META) templates/book.typst filters/mermaid.lua filters/typst-code.lua assets/vscode-dark.tmTheme | $(BUILD)
	$(PANDOC) $(COMMON_FLAGS) \
	  --to pdf --pdf-engine=$(TYPST) \
	  --syntax-highlighting=none \
	  --lua-filter=filters/typst-code.lua \
	  --template=templates/book.typst \
	  -V page-numbering="1" \
	  -o $@ $(SRC)
	@echo "PDF gerado em $@"

$(OUT_HTML): $(SRC) $(META) templates/book.html assets/style.css assets/ace-blocks.js filters/mermaid.lua assets/vscode-dark.theme | $(BUILD)
	$(PANDOC) $(COMMON_FLAGS) \
	  --to html5 --standalone --section-divs \
	  --template=templates/book.html \
	  --include-in-header=<(printf '<style>\n'; cat assets/style.css; printf '\n</style>\n') \
	  --include-after-body=<(printf '<script>\n'; cat assets/ace-blocks.js; printf '\n</script>\n') \
	  -o $@ $(SRC)
	@echo "HTML gerado em $@"

# A capa do EPUB é a primeira página do PDF, renderizada em PNG pelo typst.
$(COVER): $(SRC) $(META) templates/book.typst | $(BUILD)
	$(PANDOC) $(COMMON_FLAGS) \
	  --to typst --syntax-highlighting=none \
	  --lua-filter=filters/typst-code.lua \
	  --template=templates/book.typst \
	  -V page-numbering="1" \
	  -o $(BUILD)/manual.typ $(SRC)
	$(TYPST) compile --root . --format png --ppi 150 --pages 1 $(BUILD)/manual.typ $@
	@echo "Capa gerada em $@"

$(OUT_EPUB): $(SRC) $(META) $(COVER) assets/epub.css assets/vscode-dark.theme | $(BUILD)
	$(PANDOC) $(COMMON_FLAGS) \
	  --to epub3 \
	  --css=assets/epub.css \
	  --epub-cover-image=$(COVER) \
	  --epub-title-page=false \
	  -o $@ $(SRC)
	@echo "EPUB gerado em $@"

$(OUT_MOBI): $(OUT_EPUB)
	@command -v "$(EBOOK_CONVERT)" >/dev/null || { echo "ebook-convert (Calibre) não encontrado: brew install --cask calibre"; exit 1; }
	"$(EBOOK_CONVERT)" $< $@ --output-profile kindle
	@echo "MOBI gerado em $@"

serve: html
	@echo "Abra http://localhost:8000/manual.html"
	cd $(BUILD) && python3 -m http.server 8000

check-tools:
	@command -v $(PANDOC) >/dev/null || { echo "pandoc não encontrado: brew install pandoc"; exit 1; }
	@command -v $(TYPST)  >/dev/null || { echo "typst não encontrado: brew install typst"; exit 1; }

clean:
	rm -rf $(BUILD)
