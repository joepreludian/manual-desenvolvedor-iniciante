# Manual do desenvolvedor — Python/Django
#
# Alvos:
#   make pdf    -> build/manual.pdf   (pandoc + typst)
#   make html   -> build/manual.html  (pandoc + Ace Editor)
#   make all    -> os dois
#   make serve  -> abre um servidor local para ler o HTML
#   make clean  -> apaga build/

SHELL    := /bin/bash
PANDOC   ?= pandoc
TYPST    ?= typst
BUILD    := build
SRC      := $(sort $(wildcard src/*.md))
META     := metadata.yaml
OUT_PDF  := $(BUILD)/manual.pdf
OUT_HTML := $(BUILD)/manual.html

COMMON_FLAGS := --from markdown+smart --metadata-file=$(META) --toc \
                --syntax-highlighting=tango --resource-path=.:src

.PHONY: all pdf html serve clean check-tools

all: pdf html

pdf: check-tools $(OUT_PDF)

html: $(OUT_HTML)

$(BUILD):
	mkdir -p $(BUILD)

$(OUT_PDF): $(SRC) $(META) templates/book.typst | $(BUILD)
	$(PANDOC) $(COMMON_FLAGS) \
	  --to pdf --pdf-engine=$(TYPST) \
	  --syntax-highlighting=none \
	  --template=templates/book.typst \
	  -V page-numbering="1" \
	  -o $@ $(SRC)
	@echo "PDF gerado em $@"

$(OUT_HTML): $(SRC) $(META) templates/book.html assets/style.css assets/ace-blocks.js | $(BUILD)
	$(PANDOC) $(COMMON_FLAGS) \
	  --to html5 --standalone --section-divs \
	  --template=templates/book.html \
	  --include-in-header=<(printf '<style>\n'; cat assets/style.css; printf '\n</style>\n') \
	  --include-after-body=<(printf '<script>\n'; cat assets/ace-blocks.js; printf '\n</script>\n') \
	  -o $@ $(SRC)
	@echo "HTML gerado em $@"

serve: html
	@echo "Abra http://localhost:8000/manual.html"
	cd $(BUILD) && python3 -m http.server 8000

check-tools:
	@command -v $(PANDOC) >/dev/null || { echo "pandoc não encontrado: brew install pandoc"; exit 1; }
	@command -v $(TYPST)  >/dev/null || { echo "typst não encontrado: brew install typst"; exit 1; }

clean:
	rm -rf $(BUILD)
