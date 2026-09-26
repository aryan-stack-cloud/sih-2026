"""Re-voice selected clips with the same TTS settings and the same gain as the full pass."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import audio_voice as av
GAIN = 4.45  # measured in the full pass (-22.45 LUFS -> -18 LUFS)
ids = sys.argv[1:]
lines = dict(av.parse_lines())
dur = json.loads((av.VOICE_DIR / "durations.json").read_text(encoding="utf-8"))
for c in ids:
    (av.VOICE_DIR / f"{c}.txt").write_text(lines[c] + "\n", encoding="utf-8")
    av.synthesize(c)
    dur[c] = round(av.duration(av.finalize(c, av.trim(c), GAIN)), 3)
    print(c, dur[c], flush=True)
dur["_total"] = round(sum(v for k, v in dur.items() if k != "_total"), 3)
(av.VOICE_DIR / "durations.json").write_text(json.dumps(dur, indent=2) + "\n", encoding="utf-8")
