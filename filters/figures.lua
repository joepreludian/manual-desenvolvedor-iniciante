-- Imagens estáticas (ex.: assets/figuras/*.svg) referenciadas no Markdown.
--   Typst: o PDF é compilado a partir de um arquivo temporário, então o
--          caminho precisa começar com "/" (relativo à raiz do projeto).
--   HTML:  o manual.html é um arquivo só; um SVG é embutido inline para não
--          depender da pasta assets/ ao lado.
--   EPUB e outros: o pandoc resolve o caminho pelo --resource-path.

local function file_exists(path)
  local f = io.open(path, "rb")
  if f then f:close() return true end
  return false
end

function Image(el)
  local src = el.src
  if src:match("^https?://") or src:match("^/") then return nil end

  if FORMAT:match("typst") then
    el.src = "/" .. src
    return el
  end

  if FORMAT:match("html") and src:match("%.svg$") and file_exists(src) then
    local f = io.open(src, "rb")
    local svg = f:read("*a")
    f:close()
    local width = el.attributes.width or "100%"
    local alt = pandoc.utils.stringify(el.caption)
    local html = '<span class="figura" role="img" aria-label="' .. alt ..
                 '" style="display:inline-block;max-width:' .. width .. '">' .. svg .. '</span>'
    return pandoc.RawInline("html", html)
  end

  return nil
end
