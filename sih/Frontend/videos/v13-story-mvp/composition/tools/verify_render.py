"""Verify the rendered MP4 and package it: probe, loudness, scene-midpoint contact sheet, poster,
and a copy with the poster embedded as cover art.

Usage: python tools/verify_render.py ../v13-story-mvp.mp4
"""

import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
mp4 = (ROOT / sys.argv[1]).resolve()
out_dir = mp4.parent
work = ROOT / "snapshots" / "_render_check"
work.mkdir(parents=True, exist_ok=True)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


probe = json.loads(run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration,size,bit_rate:stream=codec_type,codec_name,width,height,r_frame_rate,channels,sample_rate",
                        "-of", "json", str(mp4)]).stdout)
print("format:", probe["format"])
for s in probe["streams"]:
    print("stream:", s)

loud = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(mp4), "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
i_lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", loud)
tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", loud)
print("integrated LUFS:", i_lufs[-1] if i_lufs else "?", " true peak dBFS:", tp[-1] if tp else "?")

timing = json.loads((ROOT / "timing.json").read_text(encoding="utf-8"))
frames = []
for sid, sc in timing["scenes"].items():
    t = sc["start"] + sc["dur"] * 0.62
    png = work / f"{sid}.png"
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(mp4), "-frames:v", "1", str(png)])
    frames.append((sid, t, png))

cols, tw, th = 4, 480, 270
rows = (len(frames) + cols - 1) // cols
sheet = Image.new("RGB", (cols * (tw + 8) + 8, rows * (th + 40) + 8), "#111111")
draw = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype("arial.ttf", 20)
except OSError:
    font = ImageFont.load_default()
for i, (sid, t, png) in enumerate(frames):
    im = Image.open(png).convert("RGB").resize((tw, th))
    x, y = 8 + (i % cols) * (tw + 8), 8 + (i // cols) * (th + 40)
    sheet.paste(im, (x, y + 30))
    draw.text((x, y + 4), f"{sid}  t={t:.1f}s", fill="#EEEEEE", font=font)
sheet_path = out_dir / "v13-contact-sheet.jpg"
sheet.save(sheet_path, quality=90)
print("contact sheet:", sheet_path)

# poster: the Turing scoreboard (all four learners more than double the old sweep)
s12 = timing["scenes"]["s12"]
poster_t = s12["start"] + s12["cues"]["s12_3"][0] + 3.4
poster = out_dir / "v13-poster.jpg"
run(["ffmpeg", "-y", "-v", "error", "-ss", f"{poster_t:.3f}", "-i", str(mp4), "-frames:v", "1", "-q:v", "2", str(poster)])
print("poster:", poster, f"(t={poster_t:.2f}s)")

# embed the poster as cover art (stream copy, no re-encode)
tmp = mp4.with_name(mp4.stem + ".cover.mp4")
r = run(["ffmpeg", "-y", "-v", "error", "-i", str(mp4), "-i", str(poster), "-map", "0", "-map", "1", "-c", "copy",
         "-disposition:v:1", "attached_pic", str(tmp)])
if r.returncode == 0 and tmp.exists() and tmp.stat().st_size > mp4.stat().st_size * 0.9:
    tmp.replace(mp4)
    print("cover art embedded")
else:
    print("cover art skipped:", r.stderr[-300:])
