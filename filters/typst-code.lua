-- Para a saída Typst: mantém a linguagem do bloco de código, para que o
-- próprio Typst faça o realce de sintaxe (pandoc a descarta quando
-- --syntax-highlighting=none). Emite #raw(block: true, lang: "...", "...").
if not FORMAT:match("typst") then return {} end

local function typst_string(s)
  s = s:gsub("\\", "\\\\"):gsub('"', '\\"'):gsub("\n", "\\n")
  return '"' .. s .. '"'
end

function CodeBlock(el)
  local lang = el.classes[1]
  local head = "#raw(block: true, "
  if lang and lang ~= "" then
    head = head .. 'lang: "' .. lang .. '", '
  end
  return pandoc.RawBlock("typst", head .. typst_string(el.text) .. ")")
end
