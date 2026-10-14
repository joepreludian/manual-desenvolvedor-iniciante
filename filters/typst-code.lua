-- Para a saída Typst: mantém a linguagem do bloco de código, para que o
-- próprio Typst faça o realce de sintaxe (pandoc a descarta quando
-- --syntax-highlighting=none). Emite #raw(block: true, lang: "...", "...").
--
-- Linhas de saída (comentários "# ...") com trechos longos sem espaço, como
-- um JSON compacto de `jq -c`, não quebram no PDF e vazam para fora do bloco.
-- Nesses trechos inserimos um espaço de largura zero (U+200B) depois de
-- `,` `;` e `:`, que o Typst usa como ponto de quebra. Comandos ficam
-- intactos, para copiar e colar sem surpresas.
if not FORMAT:match("typst") then return {} end

local ZWSP = "\226\128\139"
local LONG_TOKEN = 60

local function typst_string(s)
  s = s:gsub("\\", "\\\\"):gsub('"', '\\"'):gsub("\n", "\\n")
  return '"' .. s .. '"'
end

local function wrap_output_lines(text)
  local lines = {}
  for line in (text .. "\n"):gmatch("(.-)\n") do
    if line:match("^%s*#") then
      line = line:gsub("%S+", function(token)
        if #token > LONG_TOKEN then
          return (token:gsub("([,;:])", "%1" .. ZWSP))
        end
      end)
    end
    lines[#lines + 1] = line
  end
  return table.concat(lines, "\n")
end

function CodeBlock(el)
  local lang = el.classes[1]
  local head = "#raw(block: true, "
  if lang and lang ~= "" then
    head = head .. 'lang: "' .. lang .. '", '
  end
  return pandoc.RawBlock("typst", head .. typst_string(wrap_output_lines(el.text)) .. ")")
end
