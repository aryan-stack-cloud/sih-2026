"""Render SVG files to PNG previews and a labelled contact sheet.

Usage:
    python tools/render_svg.py assets/art/props            # every *.svg in the folder
    python tools/render_svg.py assets/art/props/dice.svg   # one file
Options:
    --bg "#2B2A6E"   background colour behind each SVG (default: checker-free mid grey)
    --size 900       longest side of each preview in pixels (default 900)

Writes <name>.png next to a `_preview/` folder inside the target folder, plus
`_preview/contact-sheet.png`. Uses the headless Chrome that HyperFrames already installed.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CHROME_CANDIDATES = [
    Path.home() / ".cache/puppeteer/chrome-headless-shell/win64-151.0.7922.71/chrome-headless-shell-win64/chrome-headless-shell.exe",
    Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
]


def chrome() -> Path:
    for c in CHROME_CANDIDATES:
        if c.exists():
            return c
    found = sorted((Path.home() / ".cache/puppeteer/chrome-headless-shell").glob("*/*/chrome-headless-shell.exe"))
    if found:
        return found[-1]
    sys.exit("No headless Chrome found")


def viewbox(svg_text: str) -> tuple[float, float]:
    m = re.search(r'viewBox\s*=\s*"([-\d.\s,]+)"', svg_text)
    if not m:
        return 1000.0, 1000.0
    parts = [float(p) for p in re.split(r"[\s,]+", m.group(1).strip())]
    return parts[2], parts[3]


def render(svg: Path, out: Path, bg: str, size: int) -> None:
    text = svg.read_text(encoding="utf-8")
    w, h = viewbox(text)
    scale = size / max(w, h)
    pw, ph = max(1, round(w * scale)), max(1, round(h * scale))
    html = f"""<!doctype html><html><head><style>
html,body{{margin:0;background:{bg};width:{pw}px;height:{ph}px;overflow:hidden}}
img{{display:block;width:{pw}px;height:{ph}px}}</style></head>
<body><img src="{svg.resolve().as_uri()}"></body></html>"""
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        page = Path(f.name)
    subprocess.run(
        [str(chrome()), "--headless", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
         f"--window-size={pw},{ph}", f"--screenshot={out}", page.as_uri()],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    page.unlink(missing_ok=True)


def contact_sheet(pngs: list[Path], out: Path) -> None:
    thumbs = []
    for p in pngs:
        im = Image.open(p).convert("RGB")
        im.thumbnail((420, 300))
        thumbs.append((p.stem, im))
    cols = 4
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 440, rows * 340), "#111111")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
    for i, (name, im) in enumerate(thumbs):
        x, y = (i % cols) * 440 + 10, (i // cols) * 340 + 10
        sheet.paste(im, (x + (420 - im.width) // 2, y))
        draw.text((x, y + 305), name, fill="#EEEEEE", font=font)
    sheet.save(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--bg", default="#8A8FA8")
    ap.add_argument("--size", type=int, default=900)
    args = ap.parse_args()
    target = Path(args.target)
    svgs = [target] if target.is_file() else sorted(target.glob("*.svg"))
    if not svgs:
        sys.exit(f"No SVG files in {target}")
    prev = (target.parent if target.is_file() else target) / "_preview"
    prev.mkdir(exist_ok=True)
    pngs = []
    for s in svgs:
        out = prev / f"{s.stem}.png"
        render(s, out, args.bg, args.size)
        pngs.append(out)
        print(f"rendered {out}")
    if len(pngs) > 1:
        contact_sheet(pngs, prev / "contact-sheet.png")
        print(f"contact sheet {prev / 'contact-sheet.png'}")


if __name__ == "__main__":
    main()
