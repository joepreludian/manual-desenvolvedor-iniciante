"""Gera a tabela de novidades da homepage a partir do CHANGELOG.md.

Uso: python3 scripts/changelog.py CHANGELOG.md site/index.html

Lê as seções "## vX.Y.Z — AAAA-MM-DD" e seus itens "- ..." e substitui o
trecho entre <!-- changelog:start --> e <!-- changelog:end --> no HTML.
Só usa a biblioteca padrão; o markdown aceito nos itens é **negrito** e `código`.
"""

import html
import re
import sys

HEADING = re.compile(r"^## (v\d+\.\d+\.\d+)\s+—\s+(\d{4})-(\d{2})-(\d{2})\s*$")
START, END = "<!-- changelog:start -->", "<!-- changelog:end -->"


def parse(text):
    releases = []
    for line in text.splitlines():
        if m := HEADING.match(line):
            version, y, mo, d = m.groups()
            releases.append({"version": version, "date": f"{d}/{mo}/{y}", "items": []})
        elif releases and line.startswith("- "):
            releases[-1]["items"].append(line[2:].strip())
        elif releases and releases[-1]["items"] and line.startswith("  "):
            # continuação de um item quebrado em várias linhas
            releases[-1]["items"][-1] += " " + line.strip()
    return releases


def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r'<strong class="text-ink">\1</strong>', text)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", text)


def render(releases, indent="      "):
    rows = []
    for r in releases:
        items = "".join(f"<li>{inline(i)}</li>" for i in r["items"])
        rows.append(
            f'{indent}  <tr class="border-t border-line align-top">\n'
            f'{indent}    <td class="py-3 pr-4 whitespace-nowrap">'
            f'<span class="font-bold text-accent">{r["version"]}</span>'
            f'<span class="block text-xs text-muted">{r["date"]}</span></td>\n'
            f'{indent}    <td class="py-3"><ul class="list-disc space-y-1 pl-4 text-muted">{items}</ul></td>\n'
            f"{indent}  </tr>"
        )
    return (
        f'{indent}<table class="w-full text-left text-sm">\n'
        f'{indent}  <thead><tr class="text-xs tracking-widest text-muted">'
        f'<th class="pb-2 pr-4 font-semibold">VERSÃO</th>'
        f'<th class="pb-2 font-semibold">O QUE MUDOU</th></tr></thead>\n'
        f"{indent}  <tbody>\n" + "\n".join(rows) + f"\n{indent}  </tbody>\n"
        f"{indent}</table>"
    )


def main(changelog_path, html_path):
    with open(changelog_path, encoding="utf-8") as f:
        releases = parse(f.read())
    if not releases:
        sys.exit(f"nenhuma versão encontrada em {changelog_path}")

    with open(html_path, encoding="utf-8") as f:
        page = f.read()
    if START not in page or END not in page:
        sys.exit(f"marcadores {START} / {END} não encontrados em {html_path}")

    before, rest = page.split(START, 1)
    _, after = rest.split(END, 1)
    page = f"{before}{START}\n{render(releases)}\n      {END}{after}"

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"{len(releases)} versões escritas em {html_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
