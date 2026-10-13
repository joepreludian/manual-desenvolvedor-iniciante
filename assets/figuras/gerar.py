#!/usr/bin/env python3
"""Gera as figuras SVG do capítulo de polígonos.

Uso: python3 assets/figuras/gerar.py
Saída: assets/figuras/dados-capitulo.svg e assets/figuras/anatomia-poligono.svg

Sem dependências: só a biblioteca padrão. As coordenadas são as mesmas que o
capítulo usa no shell, projetadas em quilômetros (equirretangular, com a
longitude corrigida pelo cosseno da latitude) para as formas não saírem
esticadas.
"""

import math
from pathlib import Path

AQUI = Path(__file__).resolve().parent
FONTE = "Helvetica Neue, Helvetica, Arial, sans-serif"
TINTA = "#1f2933"
CINZA = "#868e96"
AZUL = "#1c7ed6"
LARANJA = "#e8590c"
VERDE = "#2f9e44"
VERMELHO = "#c92a2a"
ESCALA_FONTE = 1.3   # os SVGs são reduzidos no PDF; compensa o tamanho do texto

# Dados do capítulo (lon, lat)
LUGARES_SP = {
    "Café da Esquina": (-46.6333, -23.5505),
    "MASP": (-46.6558, -23.5614),
    "Parque Ibirapuera": (-46.6575, -23.5874),
}
CENTRO = (-46.665, -23.570, -46.620, -23.530)    # xmin, ymin, xmax, ymax
PARAISO = (-46.670, -23.600, -46.640, -23.555)
MOEMA = (-46.670, -23.620, -46.640, -23.600)
PRACA = (-46.640, -23.555, -46.630, -23.545)     # o buraco da seção "Anatomia"
NA_BORDA = (-46.665, -23.550)


def esc(texto):
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def texto(x, y, s, size=11, fill=TINTA, anchor="start", weight="normal", extra=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONTE}" font-size="{size * ESCALA_FONTE:.1f}" '
            f'fill="{fill}" text-anchor="{anchor}" font-weight="{weight}" {extra}>{esc(s)}</text>')


# ---------------------------------------------------------------- figura 1
def figura_dados():
    lon0, lon1 = -46.700, -46.600
    lat0, lat1 = -23.635, -23.515
    lat_media = (lat0 + lat1) / 2
    km_lon = 111.32 * math.cos(math.radians(lat_media))   # km por grau de longitude
    km_lat = 110.574                                       # km por grau de latitude
    ppk = 44                                               # pixels por km
    ml, mt, mr, mb = 70, 24, 250, 54                       # margens
    larg = (lon1 - lon0) * km_lon * ppk
    alt = (lat1 - lat0) * km_lat * ppk
    W, H = ml + larg + mr, mt + alt + mb

    def px(lon, lat):
        return ml + (lon - lon0) * km_lon * ppk, mt + (lat1 - lat) * km_lat * ppk

    def rect(bbox, cor, opac, stroke=None):
        x0, y0 = px(bbox[0], bbox[3])
        x1, y1 = px(bbox[2], bbox[1])
        borda = f'stroke="{stroke or cor}" stroke-width="2"' if stroke != "none" else 'stroke="none"'
        return (f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{x1 - x0:.1f}" height="{y1 - y0:.1f}" '
                f'fill="{cor}" fill-opacity="{opac}" {borda}/>')

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
         f'viewBox="0 0 {W:.0f} {H:.0f}" font-family="{FONTE}">',
         '<defs><pattern id="hachura" patternUnits="userSpaceOnUse" width="8" height="8" '
         'patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="8" '
         f'stroke="{LARANJA}" stroke-width="2.5"/></pattern></defs>',
         f'<rect width="{W:.0f}" height="{H:.0f}" fill="white"/>',
         f'<rect x="{ml}" y="{mt}" width="{larg:.1f}" height="{alt:.1f}" fill="#f8f9fa" stroke="{CINZA}"/>']

    # grade e eixos
    lon = lon0
    while lon <= lon1 + 1e-9:
        x, _ = px(lon, lat0)
        o.append(f'<line x1="{x:.1f}" y1="{mt}" x2="{x:.1f}" y2="{mt + alt:.1f}" stroke="#dee2e6" stroke-width="1"/>')
        o.append(texto(x, mt + alt + 16, f"{lon:.2f}", 10, CINZA, "middle"))
        lon += 0.02
    lat = lat1
    while lat >= lat0 - 1e-9:
        _, y = px(lon0, lat)
        o.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{ml + larg:.1f}" y2="{y:.1f}" stroke="#dee2e6" stroke-width="1"/>')
        o.append(texto(ml - 6, y + 3.5, f"{lat:.2f}", 10, CINZA, "end"))
        lat -= 0.02
    o.append(texto(ml + larg / 2, mt + alt + 38, "longitude (graus, SRID 4326)", 10, CINZA, "middle"))
    o.append(texto(14, mt + alt / 2, "latitude", 10, CINZA, "middle",
                   extra=f'transform="rotate(-90 14 {mt + alt / 2:.1f})"'))

    # bairros
    o.append(rect(CENTRO, AZUL, 0.15))
    o.append(rect(PARAISO, LARANJA, 0.15))
    o.append(rect(MOEMA, VERDE, 0.15))
    inter = (max(CENTRO[0], PARAISO[0]), max(CENTRO[1], PARAISO[1]),
             min(CENTRO[2], PARAISO[2]), min(CENTRO[3], PARAISO[3]))
    o.append(rect(inter, "url(#hachura)", 1, stroke="none"))
    for bbox, nome, cor in ((CENTRO, "Centro", AZUL), (MOEMA, "Moema", VERDE)):
        x, y = px(bbox[0], bbox[3])
        o.append(texto(x + 6, y + 15, nome, 12, cor, weight="bold"))
    x, y = px(PARAISO[0], PARAISO[1])          # canto inferior esquerdo, longe da hachura
    o.append(texto(x + 6, y - 8, "Paraíso", 12, LARANJA, weight="bold"))
    xi, yi = px(inter[0], inter[1])            # canto inferior esquerdo da interseção
    o.append(f'<rect x="{xi + 3:.1f}" y="{yi - 31:.1f}" width="118" height="30" rx="3" fill="white" fill-opacity="0.85"/>')
    o.append(texto(xi + 6, yi - 18, "Centro ∩ Paraíso", 10, LARANJA, weight="bold"))
    o.append(texto(xi + 6, yi - 6, "(4,24 km²)", 10, LARANJA))

    # círculo de 500 m em volta do café
    cx, cy = px(*LUGARES_SP["Café da Esquina"])
    r = 0.5 * ppk
    o.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{AZUL}" fill-opacity="0.08" '
             f'stroke="{AZUL}" stroke-width="1.5" stroke-dasharray="5 4"/>')
    o.append(texto(cx + r + 4, cy - 10, "raio de 500 m", 10, AZUL))

    # ponto na borda
    bx, by = px(*NA_BORDA)
    o.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="5" fill="white" stroke="{VERMELHO}" stroke-width="2"/>')
    o.append(texto(bx - 9, by + 4, "na_borda", 10, VERMELHO, "end"))

    # lugares
    for nome, (lon, lat) in LUGARES_SP.items():
        x, y = px(lon, lat)
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{TINTA}" stroke="white" stroke-width="1.5"/>')
        dx, dy = (9, 4) if nome != "MASP" else (9, -6)
        o.append(texto(x + dx, y + dy, nome, 11, TINTA, weight="bold"))

    # escala
    sx, sy = ml + 12, mt + alt - 14
    o.append(f'<line x1="{sx}" y1="{sy}" x2="{sx + ppk}" y2="{sy}" stroke="{TINTA}" stroke-width="3"/>')
    o.append(texto(sx + ppk / 2, sy - 6, "1 km", 10, TINTA, "middle"))

    # legenda
    lx, ly = ml + larg + 16, mt + 8
    itens = [
        (f'<rect x="{lx}" y="{ly}" width="18" height="12" fill="{AZUL}" fill-opacity="0.15" stroke="{AZUL}" stroke-width="2"/>', "Bairro (PolygonField)"),
        (f'<rect x="{lx}" y="{ly + 22}" width="18" height="12" fill="url(#hachura)"/>', "Sobreposição de bairros"),
        (f'<circle cx="{lx + 9}" cy="{ly + 50}" r="5" fill="{TINTA}"/>', "Lugar (PointField)"),
        (f'<circle cx="{lx + 9}" cy="{ly + 72}" r="5" fill="white" stroke="{VERMELHO}" stroke-width="2"/>', "Ponto exatamente na borda"),
        (f'<circle cx="{lx + 9}" cy="{ly + 94}" r="6" fill="none" stroke="{AZUL}" stroke-width="1.5" stroke-dasharray="3 2"/>', "buffer(500) em metros"),
    ]
    for i, (simbolo, rotulo) in enumerate(itens):
        o.append(simbolo)
        o.append(texto(lx + 26, ly + 11 + 22 * i, rotulo, 10, TINTA))
    o.append(texto(lx, ly + 130, "Fora do mapa:", 10, CINZA, weight="bold"))
    o.append(texto(lx, ly + 144, "Café do Rio (359 km)", 10, CINZA))
    o.append(texto(lx, ly + 158, "Parque da Cidade (870 km)", 10, CINZA))

    o.append("</svg>")
    return "\n".join(o)


# ---------------------------------------------------------------- figura 2
def figura_anatomia():
    PW, PH = 320, 280          # cada painel
    W, H = PW * 3, PH + 10
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONTE}">',
         '<defs><marker id="seta" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
         f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{TINTA}"/></marker></defs>',
         f'<rect width="{W}" height="{H}" fill="white"/>']

    def titulo(px0, s, sub, cor=TINTA):
        o.append(texto(px0 + PW / 2, 20, s, 12, cor, "middle", "bold"))
        o.append(texto(px0 + PW / 2, 36, sub, 10, CINZA, "middle"))

    # -- painel (a): polígono com buraco, nas coordenadas do Centro
    px0 = 0
    titulo(px0, "(a) Polygon(borda, praca)", "um anel de fora e um buraco")
    lon0, lon1, lat0, lat1 = CENTRO[0], CENTRO[2], CENTRO[1], CENTRO[3]
    ax, ay, aw, ah = px0 + 60, 58, 200, 178

    def pa(lon, lat):
        return ax + (lon - lon0) / (lon1 - lon0) * aw, ay + (lat1 - lat) / (lat1 - lat0) * ah

    hx0, hy0 = pa(PRACA[0], PRACA[3])
    hx1, hy1 = pa(PRACA[2], PRACA[1])
    # fill-rule evenodd: o segundo anel vira buraco de verdade
    o.append(f'<path d="M {ax} {ay} h {aw} v {ah} h -{aw} z M {hx0:.1f} {hy0:.1f} h {hx1 - hx0:.1f} v {hy1 - hy0:.1f} h -{hx1 - hx0:.1f} z" '
             f'fill="{AZUL}" fill-opacity="0.15" fill-rule="evenodd" stroke="{AZUL}" stroke-width="2"/>')
    o.append(texto(ax + 6, ay + 14, "anel 1: borda", 10, AZUL, weight="bold"))
    o.append(texto(hx0 + (hx1 - hx0) / 2, hy0 - 5, "anel 2: buraco", 9, AZUL, "middle", "bold"))
    # ponto no buraco e ponto no bairro
    x, y = pa(-46.635, -23.550)
    o.append(f'<line x1="{x - 5}" y1="{y - 5}" x2="{x + 5}" y2="{y + 5}" stroke="{VERMELHO}" stroke-width="2.5"/>')
    o.append(f'<line x1="{x - 5}" y1="{y + 5}" x2="{x + 5}" y2="{y - 5}" stroke="{VERMELHO}" stroke-width="2.5"/>')
    o.append(texto(x, y + 36, "contains → False", 9, VERMELHO, "middle"))
    x, y = pa(-46.658, -23.563)
    o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{TINTA}"/>')
    o.append(texto(x + 9, y + 4, "contains → True", 9, TINTA, "start"))
    o.append(texto(ax, ay + ah + 16, "(-46.665, -23.570)", 9, CINZA, "start"))
    o.append(texto(ax + aw, ay - 4, "(-46.620, -23.530)", 9, CINZA, "end"))

    # -- painéis (b) e (c): coordenadas de 0 a 1
    def painel_quadrado(px0, ordem):
        bx, by, bs = px0 + 80, 64, 160        # origem (0,0) no canto inferior esquerdo

        def pb(x, y):
            return bx + x * bs, by + bs - y * bs

        pts = [pb(*p) for p in ordem]
        return pb, pts

    # (b) gravata borboleta
    px0 = PW
    titulo(px0, "(b) a gravata borboleta", "valid = False, area = 0", VERMELHO)
    ordem = [(0, 0), (1, 1), (1, 0), (0, 1)]
    pb, pts = painel_quadrado(px0, ordem)
    cx, cy = pb(0.5, 0.5)
    # os dois triângulos que make_valid() devolve
    o.append(f'<polygon points="{pts[0][0]},{pts[0][1]} {cx},{cy} {pts[3][0]},{pts[3][1]}" fill="{LARANJA}" fill-opacity="0.25"/>')
    o.append(f'<polygon points="{pts[1][0]},{pts[1][1]} {cx},{cy} {pts[2][0]},{pts[2][1]}" fill="{VERDE}" fill-opacity="0.25"/>')
    for i in range(4):
        (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % 4]
        o.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{VERMELHO}" stroke-width="2" marker-end="url(#seta)"/>')
    rotulos = {(0, 0): (-8, 14, "end"), (1, 1): (8, -6, "start"), (1, 0): (8, 14, "start"), (0, 1): (-8, -6, "end")}
    for i, p in enumerate(ordem):
        x, y = pts[i]
        o.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{TINTA}"/>')
        dx, dy, anc = rotulos[p]
        o.append(texto(x + dx, y + dy, f"{i + 1}º ({p[0]}, {p[1]})", 10, TINTA, anc))
    o.append(f'<circle cx="{cx}" cy="{cy}" r="6" fill="white" stroke="{VERMELHO}" stroke-width="2.5"/>')
    o.append(f'<line x1="{cx}" y1="{cy - 8}" x2="{cx}" y2="{64 + 28}" stroke="{VERMELHO}" stroke-width="1" stroke-dasharray="3 2"/>')
    o.append(texto(cx, 64 + 12, "Self-intersection", 9, VERMELHO, "middle", "bold"))
    o.append(texto(cx, 64 + 25, "[0.5 0.5]", 9, VERMELHO, "middle"))
    o.append(texto(px0 + PW / 2, 64 + 160 + 34, "make_valid() devolve os dois triângulos", 9, CINZA, "middle"))

    # (c) mesmos cantos, ordem certa
    px0 = PW * 2
    titulo(px0, "(c) os mesmos cantos, na ordem certa", "valid = True, area = 1", VERDE)
    ordem = [(0, 0), (1, 0), (1, 1), (0, 1)]
    pb, pts = painel_quadrado(px0, ordem)
    o.append(f'<polygon points="{" ".join(f"{x},{y}" for x, y in pts)}" fill="{VERDE}" fill-opacity="0.15"/>')
    for i in range(4):
        (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % 4]
        o.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{VERDE}" stroke-width="2" marker-end="url(#seta)"/>')
    for i, p in enumerate(ordem):
        x, y = pts[i]
        o.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{TINTA}"/>')
        dx, dy, anc = rotulos[p]
        o.append(texto(x + dx, y + dy, f"{i + 1}º ({p[0]}, {p[1]})", 10, TINTA, anc))
    o.append(texto(px0 + PW / 2, 64 + 160 + 34, "o 5º ponto repete o 1º e fecha o anel", 9, CINZA, "middle"))

    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    (AQUI / "dados-capitulo.svg").write_text(figura_dados() + "\n", encoding="utf-8")
    (AQUI / "anatomia-poligono.svg").write_text(figura_anatomia() + "\n", encoding="utf-8")
    print("figuras geradas em", AQUI)
