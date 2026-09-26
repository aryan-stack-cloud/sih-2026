"""Render the cast in a few poses to tools/_cast_preview.png for visual review."""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cast import guard, engineer, intruder  # noqa: E402
from render_svg import chrome  # noqa: E402

OUT = Path(__file__).parent / "_cast_preview.png"

cells = [
    ("Guard", guard("g1")),
    ("Guard talking + torch", guard("g2", torch=True).replace('id="g2-mouth-open" opacity="0"', 'id="g2-mouth-open" opacity="1"').replace('<g id="g2-mouth-closed">', '<g id="g2-mouth-closed" opacity="0">')),
    ("Engineer + tablet", engineer("e1", tablet=True)),
    ("Engineer talking", engineer("e2", marker=True).replace('id="e2-mouth-open" opacity="0"', 'id="e2-mouth-open" opacity="1"').replace('<g id="e2-mouth-closed">', '<g id="e2-mouth-closed" opacity="0">')),
    ("Intruder", intruder("i1")),
    ("Intruder torch on", intruder("i2").replace('id="i2-beam" opacity="0"', 'id="i2-beam" opacity="1"')),
]

html = """<!doctype html><html><head><style>
body{margin:0;background:#2B2A6E;width:1920px;height:1080px;display:grid;grid-template-columns:repeat(6,1fr);align-items:end;font:600 22px Arial;color:#fff}
.cell{height:1000px;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;padding-bottom:20px;border-right:1px solid #3D3C8F}
.cell svg{width:300px;height:auto;max-height:640px}
.cell.big svg{width:300px}
p{margin:10px 0 0}
</style></head><body>""" + "".join(
    f'<div class="cell">{svg}<p>{name}</p></div>' for name, svg in cells) + "</body></html>"

page = Path(__file__).parent / "_cast_preview.html"
page.write_text(html, encoding="utf-8")
subprocess.run([str(chrome()), "--headless", "--disable-gpu", "--hide-scrollbars", "--window-size=1920,1080",
                f"--screenshot={OUT}", page.resolve().as_uri()], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print(OUT)
