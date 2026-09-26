"""Finish the voice pass: synthesize only missing raw clips, then trim, loudness-match and write
durations.json (reuses tools/audio_voice.py), then build the music bed (tools/audio_music.py)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import audio_voice as av  # noqa: E402

entries = av.parse_lines()
for clip_id, text in entries:
    (av.VOICE_DIR / f"{clip_id}.txt").write_text(text + "\n", encoding="utf-8")
for clip_id, _ in entries:
    raw = av.VOICE_DIR / f"{clip_id}.raw.wav"
    if not raw.exists() and not (av.VOICE_DIR / f"{clip_id}.wav").exists():
        print("synthesizing", clip_id, flush=True)
        av.synthesize(clip_id)
todo = [c for c, _ in entries if (av.VOICE_DIR / f"{c}.raw.wav").exists()]
trimmed = [av.trim(c) for c in todo]
lufs = av.measure_concat_loudness(trimmed)
gain = av.TARGET_LUFS - lufs
print(f"measured {lufs:.2f} LUFS, gain {gain:.2f} dB", flush=True)
durations = {}
for c, t in zip(todo, trimmed):
    durations[c] = round(av.duration(av.finalize(c, t, gain)), 3)
durations["_total"] = round(sum(durations.values()), 3)
(av.VOICE_DIR / "durations.json").write_text(json.dumps(durations, indent=2) + "\n", encoding="utf-8")
print("voice total", durations["_total"], flush=True)

import audio_music  # noqa: E402
if hasattr(audio_music, "main"):
    audio_music.main()
print("DONE", flush=True)
