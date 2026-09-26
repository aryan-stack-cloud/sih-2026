"""Derive index-novoice.html from index.html: same picture, no narration.

For presenting live over the video. Drops every voiceover clip and the score's
voiceover carve (there is no voice left to make room for), and lifts the score
slightly. Re-run after any edit to index.html:

    python tools/make_novoice.py
    npx hyperframes render -c index-novoice.html -q delivery -o ../v7-solution-eg-no-voice.mp4
"""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()

out, n_vo = re.subn(r'\s*<audio id="vo-[^"]+"[^>]*></audio>', "", src)
assert n_vo == 10, f"expected 10 narration clips, found {n_vo}"

m = re.search(r'<audio id="bed-score"[^>]*>', out)
assert m, "score bed not found"
tag = m.group(0)
clean = re.sub(r'\s+data-fx-(carve|chain)="[^"]*"', "", tag)
clean = re.sub(r'\s+data-automation="[^"]*"', "", clean)
clean = clean.replace('data-volume="0.6"', 'data-volume="0.72"')
out = out.replace(tag, clean)
out = out.replace("<title>The Guard and the Spectrum</title>", "<title>The Guard and the Spectrum (no voice)</title>")

open(os.path.join(ROOT, "index-novoice.html"), "w", encoding="utf-8").write(out)
print("wrote index-novoice.html; removed", n_vo, "voice clips; score tag:", clean[:160])
