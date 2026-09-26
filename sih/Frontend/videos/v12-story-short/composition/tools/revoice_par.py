"""revoice.py, but synthesizes the clips in parallel (TTS start-up dominates) and retries a failed
synthesis once. Same voice, speed and gain as the full pass.

Usage: python tools/revoice_par.py s11_1 s11_2 ...
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import audio_voice as av  # noqa: E402

GAIN = 4.45  # same as revoice.py (importing it would run its loop)

ids = sys.argv[1:]
lines = dict(av.parse_lines())
for c in ids:
    (av.VOICE_DIR / f"{c}.txt").write_text(lines[c] + "\n", encoding="utf-8")


def synth(c):
    for attempt in (1, 2):
        try:
            av.synthesize(c)
            return c
        except subprocess.CalledProcessError:
            if attempt == 2:
                raise


with ThreadPoolExecutor(max_workers=3) as pool:
    for c in pool.map(synth, ids):
        print("synthesized", c, flush=True)

dur = json.loads((av.VOICE_DIR / "durations.json").read_text(encoding="utf-8"))
for c in ids:
    dur[c] = round(av.duration(av.finalize(c, av.trim(c), GAIN)), 3)
    print(c, dur[c], flush=True)
dur["_total"] = round(sum(v for k, v in dur.items() if k != "_total"), 3)
(av.VOICE_DIR / "durations.json").write_text(json.dumps(dur, indent=2) + "\n", encoding="utf-8")
