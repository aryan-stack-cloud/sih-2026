"""Persist the carve attributes that carve.mjs wrote onto the bed, keyed to the voice timing."""
import html, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build  # noqa: E402

doc = (ROOT / "index.html").read_text(encoding="utf-8")
m = re.search(r'<audio id="bed"[^>]*>', doc)
tag = m.group(0)
out = {}
for k in ("data-fx-carve", "data-fx-chain", "data-automation"):
    mm = re.search(k + r"""=(?:'([^']*)'|"([^"]*)")""", tag)
    if mm:
        out[k] = html.unescape(mm.group(1) if mm.group(1) is not None else mm.group(2))
t = json.loads((ROOT / "timing.json").read_text(encoding="utf-8"))
scenes = [{"id": k, "start": v["start"], "dur": v["dur"], "cues": {c: tuple(x) for c, x in v["cues"].items()}} for k, v in t["scenes"].items()]
out["total"] = t["total"]
out["voice_sig"] = build.voice_sig(scenes)
(ROOT / "assets/music/carve.json").write_text(json.dumps(out), encoding="utf-8")
print("saved", {k: len(v) if isinstance(v, str) else v for k, v in out.items() if k != "voice_sig"})
