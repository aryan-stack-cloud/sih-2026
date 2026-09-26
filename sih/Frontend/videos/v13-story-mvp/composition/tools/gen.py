"""Procedural SVG pieces for v11 scenes (placeholder: {{gen <name> id=... [args]}})."""

from __future__ import annotations

import math


def _pt(cx: float, cy: float, r: float, deg: float) -> tuple[float, float]:
    a = math.radians(deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def dial(id: str, n: str = "16", size: str = "800", cls: str = "", style: str = "", **_) -> str:
    """Clock-style dial with n numbered band slots and a 2-slot wedge hand (id-hand)."""
    n = int(n)
    c = 400
    r_slot = 300
    parts = [f'<circle cx="{c}" cy="{c}" r="372" fill="#2B2A6E" stroke="#5A62B5" stroke-width="14"/>',
             f'<circle cx="{c}" cy="{c}" r="226" fill="#1D1B4F"/>']
    for i in range(n):
        a0 = -90 + i * 360 / n
        x1, y1 = _pt(c, c, 238, a0)
        x2, y2 = _pt(c, c, 362, a0)
        parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#3D3C8F" stroke-width="4"/>')
    span = 2 * 360 / n
    ax, ay = _pt(c, c, 364, -90)
    bx, by = _pt(c, c, 364, -90 + span)
    parts.append(f'<g id="{id}-hand"><path d="M{c} {c} L{ax:.1f} {ay:.1f} A364 364 0 0 1 {bx:.1f} {by:.1f} Z" '
                 f'fill="#FFC43D" fill-opacity="0.33" stroke="#FFC43D" stroke-width="8" stroke-linejoin="round"/>'
                 f'<circle cx="{c}" cy="{c}" r="44" fill="#FFC43D"/><circle cx="{c}" cy="{c}" r="18" fill="#1F2340"/></g>')
    for i in range(1, n + 1):
        x, y = _pt(c, c, r_slot, -90 + (i - 0.5) * 360 / n)
        parts.append(
            f'<g id="{id}-slot-{i}"><circle cx="{x:.1f}" cy="{y:.1f}" r="40" fill="#20224A" stroke="#5A62B5" stroke-width="7"/>'
            f'<circle id="{id}-slot-{i}-lit" cx="{x:.1f}" cy="{y:.1f}" r="34" fill="#FFD166" opacity="0"/>'
            f'<circle id="{id}-slot-{i}-red" cx="{x:.1f}" cy="{y:.1f}" r="34" fill="#E63946" opacity="0"/>'
            f'<circle id="{id}-slot-{i}-green" cx="{x:.1f}" cy="{y:.1f}" r="34" fill="#2DB86B" opacity="0"/>'
            f'<text x="{x:.1f}" y="{y + 11:.1f}" text-anchor="middle" font-family="Montserrat" font-weight="800" '
            f'font-size="30" fill="#FDFCF8">{i}</text></g>')
    st = f' style="{style}"' if style else ""
    return (f'<svg id="{id}" class="{cls}" viewBox="0 0 800 800" xmlns="http://www.w3.org/2000/svg"{st}>'
            + "".join(parts) + "</svg>")


PALETTE = ["#3A86FF", "#2EC4B6", "#FFC43D", "#E0457B", "#2DB86B", "#FF9F5A", "#7FB2FF", "#8E2C80"]


def wheel(id: str, n: str = "8", weights: str = "", labels: str = "", cls: str = "", style: str = "", **_) -> str:
    """Prize wheel face with n slices (ids id-slice-i), radius 290, centre 300. Optional weights."""
    n = int(n)
    w = [float(x) for x in weights.split(",")] if weights else [1.0] * n
    tot = sum(w)
    lab = labels.split(",") if labels else [str(i + 1) for i in range(n)]
    c, r = 300, 290
    parts = [f'<circle cx="{c}" cy="{c}" r="298" fill="#1F2340"/>']
    a0 = -90.0
    for i in range(n):
        a1 = a0 + 360 * w[i] / tot
        x0, y0 = _pt(c, c, r, a0)
        x1, y1 = _pt(c, c, r, a1)
        large = 1 if a1 - a0 > 180 else 0
        tx, ty = _pt(c, c, r * 0.66, (a0 + a1) / 2)
        fs = 38 if a1 - a0 >= 40 else 28
        parts.append(f'<path id="{id}-slice-{i + 1}" d="M{c} {c} L{x0:.1f} {y0:.1f} A{r} {r} 0 {large} 1 {x1:.1f} {y1:.1f} Z" '
                     f'fill="{PALETTE[i % len(PALETTE)]}" stroke="#FDFCF8" stroke-width="6"/>')
        parts.append(f'<text x="{tx:.1f}" y="{ty + fs * 0.36:.1f}" text-anchor="middle" font-family="Montserrat" '
                     f'font-weight="800" font-size="{fs}" fill="#1F2340">{lab[i]}</text>')
        a0 = a1
    for i in range(n * 2):
        x, y = _pt(c, c, 282, -90 + i * 180 / n)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="#FDFCF8"/>')
    st = f' style="{style}"' if style else ""
    return (f'<svg id="{id}" class="{cls}" viewBox="0 0 600 600" xmlns="http://www.w3.org/2000/svg"{st}>'
            + "".join(parts) + "</svg>")


def waffle(id: str, n: str = "100", cols: str = "10", cell: str = "46", gap: str = "8", cls: str = "", style: str = "", **_) -> str:
    """n rounded squares in a grid; ids id-c1..id-cN for lighting."""
    n, cols, cell, gap = int(n), int(cols), int(cell), int(gap)
    rows = (n + cols - 1) // cols
    w = cols * cell + (cols - 1) * gap
    h = rows * cell + (rows - 1) * gap
    parts = []
    for i in range(n):
        x = (i % cols) * (cell + gap)
        y = (i // cols) * (cell + gap)
        parts.append(f'<rect id="{id}-c{i + 1}" x="{x}" y="{y}" width="{cell}" height="{cell}" rx="10" fill="#3D3C8F"/>')
    st = f' style="{style}"' if style else ""
    return (f'<svg id="{id}" class="{cls}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg"{st}>'
            + "".join(parts) + "</svg>")


def slot(id: str, label: str = "9-10", cls: str = "", style: str = "", **_) -> str:
    """Classic slot machine (viewBox 380 x 560). Parts: id-light, id-strip (reel labels), id-lever
    (pivot 300 300), id-tray. The reel strip scrolls in 110-unit rows and rests on `label`."""
    lab = label.replace("-", "–")
    strip_labels = ["1–2", "5–6", "9–10", "13–14", "3–4", "11–12", lab]
    rows = "".join(
        f'<text x="165" y="{268 + i * 110}" text-anchor="middle" font-family="Montserrat" font-weight="800" '
        f'font-size="64" fill="#1F2340">{t}</text>' for i, t in enumerate(strip_labels))
    bulbs = "".join(
        f'<circle cx="{165 + 118 * math.cos(math.radians(a)):.1f}" cy="{150 - 100 * math.sin(math.radians(a)):.1f}" r="9" fill="#FDFCF8"/>'
        for a in range(10, 180, 20))
    svg = f'''<svg id="{id}" class="{cls}" viewBox="0 0 380 560" xmlns="http://www.w3.org/2000/svg"{f' style="{style}"' if style else ''}>
<defs><clipPath id="{id}-clip"><rect x="80" y="180" width="170" height="140" rx="16"/></clipPath></defs>
<ellipse cx="170" cy="546" rx="150" ry="12" fill="rgba(20,18,60,0.25)"/>
<path d="M40 150 C40 60 100 30 165 30 C230 30 290 60 290 150 Z" fill="#FFC43D"/>
<path d="M232 44 C270 62 290 100 290 150 L262 150 C262 104 252 70 232 44 Z" fill="#F2B632"/>
{bulbs}
<circle id="{id}-light" cx="165" cy="78" r="30" fill="#FFE066"/>
<rect x="30" y="140" width="270" height="390" rx="36" fill="#E63946"/>
<path d="M258 140 L264 140 Q300 140 300 176 L300 494 Q300 530 264 530 L258 530 Z" fill="rgba(20,18,60,0.22)"/>
<rect x="30" y="140" width="270" height="22" rx="11" fill="#F2B632"/>
<rect x="64" y="166" width="202" height="168" rx="24" fill="#1F2340"/>
<rect x="80" y="180" width="170" height="140" rx="16" fill="#FDFCF8"/>
<g clip-path="url(#{id}-clip)"><g id="{id}-strip" transform="translate(0,-660)">{rows}</g></g>
<rect x="80" y="180" width="170" height="22" rx="10" fill="rgba(20,18,60,0.12)"/>
<rect x="80" y="298" width="170" height="22" rx="10" fill="rgba(20,18,60,0.12)"/>
<rect x="100" y="364" width="130" height="16" rx="8" fill="#1F2340"/>
<rect x="150" y="360" width="30" height="24" rx="6" fill="#F2B632"/>
<g id="{id}-tray"><rect x="66" y="420" width="198" height="72" rx="18" fill="#1F2340"/><rect x="80" y="434" width="170" height="30" rx="10" fill="#2B2A6E"/></g>
<g id="{id}-lever" data-pivot="300 300">
  <rect x="296" y="160" width="14" height="148" rx="7" fill="#D8DEEA"/>
  <circle cx="303" cy="150" r="28" fill="#E63946"/><circle cx="294" cy="140" r="8" fill="#FDFCF8" opacity="0.7"/>
</g>
<circle cx="303" cy="304" r="20" fill="#1F2340"/>
</svg>'''
    return svg


def robot(id: str, cls: str = "", style: str = "", **_) -> str:
    """Friendly robot head with a glass-dome neural 'brain' (viewBox 600 x 660).
    Parts: id-eye-l, id-eye-r (blink), id-node-1..9 (pulse), id-links, id-antenna."""
    nodes = [(220, 190), (300, 150), (380, 190), (190, 250), (265, 235), (335, 235), (410, 250), (250, 120), (350, 120)]
    links = [(0, 1), (1, 2), (0, 4), (1, 4), (1, 5), (2, 5), (3, 4), (4, 5), (5, 6), (7, 1), (8, 1), (7, 0), (8, 2), (3, 0), (6, 2)]
    lk = "".join(f'<line x1="{nodes[a][0]}" y1="{nodes[a][1]}" x2="{nodes[b][0]}" y2="{nodes[b][1]}" stroke="#3DDCFF" stroke-width="5" stroke-opacity="0.6"/>' for a, b in links)
    nd = "".join(f'<circle id="{id}-node-{i + 1}" cx="{x}" cy="{y}" r="16" fill="#3DDCFF"/>' for i, (x, y) in enumerate(nodes))
    return f'''<svg id="{id}" class="{cls}" viewBox="0 0 600 660" xmlns="http://www.w3.org/2000/svg"{f' style="{style}"' if style else ''}>
<ellipse cx="300" cy="646" rx="200" ry="12" fill="rgba(20,18,60,0.22)"/>
<rect x="215" y="540" width="170" height="96" rx="26" fill="#2B2A6E"/>
<rect x="150" y="600" width="300" height="40" rx="20" fill="#3A86FF"/>
<rect x="56" y="330" width="46" height="120" rx="20" fill="#2B2A6E"/>
<rect x="498" y="330" width="46" height="120" rx="20" fill="#2B2A6E"/>
<rect x="90" y="250" width="420" height="300" rx="80" fill="#3A86FF"/>
<path d="M440 262 Q510 280 510 330 L510 470 Q510 540 440 550 Q480 480 480 400 Q480 320 440 262 Z" fill="rgba(20,18,60,0.18)"/>
<rect x="140" y="300" width="320" height="190" rx="58" fill="#16204A"/>
<rect id="{id}-eye-l" x="200" y="350" width="64" height="72" rx="32" fill="#3DDCFF"/>
<rect id="{id}-eye-r" x="336" y="350" width="64" height="72" rx="32" fill="#3DDCFF"/>
<circle cx="222" cy="372" r="10" fill="#FDFCF8"/><circle cx="358" cy="372" r="10" fill="#FDFCF8"/>
<path d="M262 450 Q300 474 338 450" fill="none" stroke="#3DDCFF" stroke-width="10" stroke-linecap="round"/>
<path d="M130 262 C130 120 210 64 300 64 C390 64 470 120 470 262 Z" fill="#3DDCFF" fill-opacity="0.12" stroke="#FDFCF8" stroke-opacity="0.55" stroke-width="8"/>
<g id="{id}-links">{lk}</g>
<g>{nd}</g>
<path d="M170 180 C190 120 230 96 270 88" fill="none" stroke="#FDFCF8" stroke-opacity="0.6" stroke-width="10" stroke-linecap="round"/>
<rect x="292" y="26" width="16" height="44" rx="8" fill="#2B2A6E"/>
<circle id="{id}-antenna" cx="300" cy="22" r="20" fill="#FFC43D"/>
</svg>'''


def wheelstand(id: str, part: str = "back", cls: str = "", style: str = "", **_) -> str:
    """Prize-wheel stand (viewBox 700 x 820, wheel centre 350,350 r 300).
    part=back: base + post. part=top: hub + pointer (id-pointer, pivot 350 16)."""
    st = f' style="{style}"' if style else ""
    if part == "back":
        inner = ('<ellipse cx="350" cy="800" rx="230" ry="14" fill="rgba(20,18,60,0.25)"/>'
                 '<rect x="322" y="360" width="56" height="400" rx="20" fill="#4B519A"/>'
                 '<rect x="350" y="360" width="28" height="400" rx="12" fill="rgba(20,18,60,0.2)"/>'
                 '<path d="M190 800 L240 730 L460 730 L510 800 Z" fill="#2D3A6B"/>'
                 '<rect x="232" y="716" width="236" height="26" rx="13" fill="#F2B632"/>'
                 '<circle cx="350" cy="350" r="318" fill="#F2B632"/>'
                 '<circle cx="350" cy="350" r="304" fill="#1F2340"/>')
    else:
        inner = ('<circle cx="350" cy="350" r="46" fill="#F2B632"/><circle cx="350" cy="350" r="20" fill="#1F2340"/>'
                 f'<g id="{id}-pointer" data-pivot="350 16"><path d="M322 10 L378 10 L350 86 Z" fill="#E63946"/>'
                 '<circle cx="350" cy="16" r="22" fill="#FFC43D"/></g>')
    return f'<svg id="{id}" class="{cls}" viewBox="0 0 700 820" xmlns="http://www.w3.org/2000/svg"{st}>{inner}</svg>'


def net(id: str, scores: str = "", cls: str = "", style: str = "", **_) -> str:
    """Neural-network diagram for a 1000 x 520 screen: 16 band inputs -> 2 hidden layers -> 16
    output score bars (ids id-out-1..16, scaleX from the left), nodes id-h1-i / id-h2-i, links groups."""
    sc = [float(x) for x in scores.split(",")] if scores else [0.3] * 16
    ys = [40 + i * 29.5 for i in range(16)]
    h1 = [70 + i * 54 for i in range(8)]
    h2 = [70 + i * 54 for i in range(8)]
    x_in, x_h1, x_h2, x_out = 90, 360, 560, 760
    links1 = "".join(f'<line x1="{x_in + 26}" y1="{ys[i] + 12}" x2="{x_h1}" y2="{h1[(i * 3 + k) % 8]}" stroke="#3DDCFF" stroke-opacity="0.28" stroke-width="3"/>'
                     for i in range(16) for k in range(2))
    links2 = "".join(f'<line x1="{x_h1}" y1="{a}" x2="{x_h2}" y2="{b}" stroke="#3DDCFF" stroke-opacity="0.2" stroke-width="3"/>'
                     for a in h1 for b in h2)
    links3 = "".join(f'<line x1="{x_h2}" y1="{h2[(i * 5 + k) % 8]}" x2="{x_out - 6}" y2="{ys[i] + 12}" stroke="#3DDCFF" stroke-opacity="0.28" stroke-width="3"/>'
                     for i in range(16) for k in range(2))
    ins = "".join(f'<rect id="{id}-in-{i + 1}" x="{x_in}" y="{ys[i]}" width="26" height="24" rx="6" fill="#5A62B5"/>'
                  f'<text x="{x_in - 12}" y="{ys[i] + 20}" text-anchor="end" font-family="Montserrat" font-weight="800" font-size="22" fill="#C9CCEA">{i + 1}</text>'
                  for i in range(16))
    n1 = "".join(f'<circle id="{id}-h1-{i + 1}" cx="{x_h1}" cy="{y}" r="17" fill="#3DDCFF"/>' for i, y in enumerate(h1))
    n2 = "".join(f'<circle id="{id}-h2-{i + 1}" cx="{x_h2}" cy="{y}" r="17" fill="#3DDCFF"/>' for i, y in enumerate(h2))
    outs = "".join(f'<rect x="{x_out}" y="{ys[i]}" width="150" height="24" rx="8" fill="#20224A"/>'
                   f'<rect id="{id}-out-{i + 1}" x="{x_out}" y="{ys[i]}" width="{150 * sc[i]:.1f}" height="24" rx="8" fill="#7FB2FF"/>'
                   for i in range(16))
    st = f' style="{style}"' if style else ""
    return (f'<svg id="{id}" class="{cls}" viewBox="0 0 1000 520" xmlns="http://www.w3.org/2000/svg"{st}>'
            f'<g id="{id}-links1">{links1}</g><g id="{id}-links2">{links2}</g><g id="{id}-links3">{links3}</g>'
            f'<g id="{id}-ins">{ins}</g><g id="{id}-n1">{n1}</g><g id="{id}-n2">{n2}</g><g id="{id}-outs">{outs}</g></svg>')


# ------------------------------------------------------------------------------ maze (v13 Q-learning)
MAZE_COLS, MAZE_ROWS, MAZE_TILE, MAZE_GAP, MAZE_PAD = 6, 4, 130, 12, 30
# the path from START (bottom-left) to the signal (top-right); cells are (col, row), row 0 = top
MAZE_PATH = [(0, 3), (1, 3), (1, 2), (2, 2), (3, 2), (3, 1), (4, 1), (5, 1), (5, 0)]
MAZE_ALTS = [((1, 3), (2, 3)), ((3, 2), (3, 3)), ((1, 2), (0, 2)), ((5, 1), (5, 2))]   # moves that never lead to the signal
MAZE_WALLS = [((0, 2), (0, 3)), ((1, 1), (1, 2)), ((2, 2), (2, 3)), ((2, 1), (2, 2)),
              ((3, 2), (4, 2)), ((4, 1), (4, 2)), ((4, 0), (5, 0)), ((3, 0), (3, 1)), ((0, 0), (0, 1)), ((2, 0), (2, 1))]


def maze_cell_center(c: int, r: int) -> tuple[float, float]:
    """Centre of a maze cell in the maze's own viewBox units."""
    step = MAZE_TILE + MAZE_GAP
    return MAZE_PAD + c * step + MAZE_TILE / 2, MAZE_PAD + r * step + MAZE_TILE / 2


def _maze_arrow(aid: str, a: tuple[int, int], b: tuple[int, int], fill: str, opacity: float = 1.0) -> str:
    (x1, y1), (x2, y2) = maze_cell_center(*a), maze_cell_center(*b)
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
    # a chunky arrow centred on the shared edge, pointing along the move
    shape = ('<rect x="-40" y="-9" width="52" height="18" rx="9"/>'
             '<path d="M8 -24 L42 0 L8 24 Z" stroke-linejoin="round"/>')
    return (f'<g id="{aid}" transform="translate({mx:.1f},{my:.1f}) rotate({ang:.0f})" fill="{fill}" opacity="{opacity}">'
            f'{shape}</g>')


def maze(id: str, cls: str = "", style: str = "", **_) -> str:
    """Top-down maze board for the Q-learning scene (viewBox 900 x 616).
    Parts: id-board, id-tile-c{c}r{r}, id-glow-c{c}r{r} (green path glow, hidden), id-walls, id-start,
    id-goal, id-goal-glow, id-arrow-1..8 (the path moves, start to goal), id-alt-1..4 (dead-end moves)."""
    step = MAZE_TILE + MAZE_GAP
    w = 2 * MAZE_PAD + MAZE_COLS * MAZE_TILE + (MAZE_COLS - 1) * MAZE_GAP
    h = 2 * MAZE_PAD + MAZE_ROWS * MAZE_TILE + (MAZE_ROWS - 1) * MAZE_GAP
    tiles, glows = [], []
    for r in range(MAZE_ROWS):
        for c in range(MAZE_COLS):
            x, y = MAZE_PAD + c * step, MAZE_PAD + r * step
            tiles.append(f'<g id="{id}-tile-c{c}r{r}"><rect x="{x}" y="{y}" width="{MAZE_TILE}" height="{MAZE_TILE}" rx="22" fill="#3A3F7A"/>'
                         f'<rect x="{x}" y="{y}" width="{MAZE_TILE}" height="{MAZE_TILE * 0.42:.0f}" rx="22" fill="#4B519A" opacity="0.55"/></g>')
            if (c, r) in MAZE_PATH:
                glows.append(f'<rect id="{id}-glow-c{c}r{r}" x="{x}" y="{y}" width="{MAZE_TILE}" height="{MAZE_TILE}" rx="22" fill="#2DB86B" opacity="0"/>')
    walls = []
    for (a, b) in MAZE_WALLS:
        (c1, r1), (c2, r2) = a, b
        if c1 == c2:   # horizontal wall between two rows
            y = MAZE_PAD + max(r1, r2) * step - MAZE_GAP / 2
            x = MAZE_PAD + c1 * step
            walls.append(f'<rect x="{x - 8}" y="{y - 9:.0f}" width="{MAZE_TILE + 16}" height="18" rx="9" fill="#C9CCEA"/>')
        else:          # vertical wall between two columns
            x = MAZE_PAD + max(c1, c2) * step - MAZE_GAP / 2
            y = MAZE_PAD + r1 * step
            walls.append(f'<rect x="{x - 9:.0f}" y="{y - 8}" width="18" height="{MAZE_TILE + 16}" rx="9" fill="#C9CCEA"/>')
    arrows = "".join(_maze_arrow(f"{id}-arrow-{k + 1}", MAZE_PATH[k], MAZE_PATH[k + 1], "#FDFCF8") for k in range(len(MAZE_PATH) - 1))
    alts = "".join(_maze_arrow(f"{id}-alt-{j + 1}", a, b, "#8E93C4") for j, (a, b) in enumerate(MAZE_ALTS))
    sx, sy = maze_cell_center(*MAZE_PATH[0])
    gx, gy = maze_cell_center(*MAZE_PATH[-1])
    star = " ".join(f"{gx + (46 if i % 2 == 0 else 20) * math.cos(math.radians(-90 + 36 * i)):.1f},"
                    f"{gy + (46 if i % 2 == 0 else 20) * math.sin(math.radians(-90 + 36 * i)):.1f}" for i in range(10))
    st = f' style="{style}"' if style else ""
    return (f'<svg id="{id}" class="{cls}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg"{st}>'
            f'<defs><radialGradient id="{id}-gg"><stop offset="0" stop-color="#FFE066" stop-opacity="0.95"/>'
            f'<stop offset="1" stop-color="#FFB703" stop-opacity="0"/></radialGradient></defs>'
            f'<rect id="{id}-board" x="0" y="0" width="{w}" height="{h}" rx="36" fill="#1D1B4F"/>'
            f'<rect x="0" y="{h - 16}" width="{w}" height="16" rx="8" fill="#141338" opacity="0.6"/>'
            f'{"".join(tiles)}<g id="{id}-glows">{"".join(glows)}</g><g id="{id}-walls">{"".join(walls)}</g>'
            f'<circle id="{id}-start" cx="{sx:.1f}" cy="{sy:.1f}" r="44" fill="#2B2A6E" stroke="#7FB2FF" stroke-width="6" stroke-dasharray="10 9"/>'
            f'<circle id="{id}-goal-glow" cx="{gx:.1f}" cy="{gy:.1f}" r="92" fill="url(#{id}-gg)"/>'
            f'<polygon id="{id}-goal" points="{star}" fill="#FFC43D"/>'
            f'<g id="{id}-alts">{alts}</g><g id="{id}-arrows">{arrows}</g></svg>')


GEN = {"dial": dial, "wheel": wheel, "waffle": waffle, "slot": slot, "robot": robot, "wheelstand": wheelstand, "net": net,
       "maze": maze}
