-- Renderiza blocos ```mermaid.
--   HTML: vira <pre class="mermaid"> e o mermaid.js desenha no navegador.
--   PDF/EPUB/outros: chama o mermaid-cli (mmdc) e insere um PNG,
--   guardado em build/mermaid/<sha1-do-conteudo>.png (cache).
--
-- Atributos opcionais no bloco: {.mermaid width="60%" caption="..."}
local outdir = os.getenv("MERMAID_OUT") or "build/mermaid"
local mmdc   = os.getenv("MMDC") or "npx -y @mermaid-js/mermaid-cli@11"

local function file_exists(path)
  local f = io.open(path, "rb")
  if f then f:close() return true end
  return false
end

function CodeBlock(el)
  if not el.classes:includes("mermaid") then return nil end

  if FORMAT:match("html") then
    return pandoc.RawBlock("html", '<pre class="mermaid">\n' .. el.text .. '\n</pre>')
  end

  os.execute("mkdir -p " .. outdir)
  local base = outdir .. "/" .. pandoc.sha1(el.text)
  local src, png = base .. ".mmd", base .. ".png"

  if not file_exists(png) then
    local w = io.open(src, "w"); w:write(el.text); w:close()
    local ok = os.execute(mmdc .. " -i " .. src .. " -o " .. png .. " -s 2 -b white -q")
    if not ok then
      io.stderr:write("mermaid: falha ao renderizar " .. src .. "; mantendo o bloco como código\n")
      return nil
    end
  end

  local caption = el.attributes.caption or ""
  local width   = el.attributes.width or "80%"
  -- No Typst, caminhos começando com "/" são relativos à raiz do projeto
  -- (o Makefile compila sempre a partir da raiz do repositório).
  local src_path = FORMAT:match("typst") and ("/" .. png) or png
  local img = pandoc.Image({pandoc.Str(caption)}, src_path, "", {width = width})
  return pandoc.Para({img})
end
