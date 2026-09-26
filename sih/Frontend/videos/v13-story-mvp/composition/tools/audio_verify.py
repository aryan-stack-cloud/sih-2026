from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VOICE_DIR = ROOT / "assets" / "voice"
MUSIC_DIR = ROOT / "assets" / "music"
SFX_DIR = ROOT / "assets" / "sfx"


def run(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, capture_output=True)


def probe_duration(path: Path) -> float:
    result = run([
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=sample_rate,channels,codec_name,sample_fmt",
        "-of",
        "json",
        str(path),
    ])
    return float(json.loads(result.stdout)["format"]["duration"])


def loudness(path: Path, concat: bool = False) -> tuple[float, float]:
    command = ["ffmpeg", "-hide_banner"]
    if concat:
        command.extend(["-f", "concat", "-safe", "0"])
    command.extend([
        "-i",
        str(path),
        "-af",
        "loudnorm=I=-18:TP=-1.0:LRA=7:print_format=json",
        "-f",
        "null",
        "-",
    ])
    result = run(command)
    stderr = result.stderr.decode(errors="replace")
    blocks = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", stderr, re.S)
    if not blocks:
        raise RuntimeError(f"Could not parse loudness for {path}")
    data = json.loads(blocks[-1])
    return float(data["input_i"]), float(data["input_tp"])


def main() -> None:
    lines = [line for line in (ROOT / "narration.txt").read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [line.split("|", 1)[0] for line in lines]
    durations = json.loads((VOICE_DIR / "durations.json").read_text(encoding="utf-8"))
    issues = []
    scene_totals: dict[str, float] = defaultdict(float)
    for clip_id in ids:
        path = VOICE_DIR / f"{clip_id}.wav"
        if not path.exists():
            issues.append(f"missing voice {clip_id}")
            continue
        duration = probe_duration(path)
        if abs(duration - float(durations.get(clip_id, -1))) > 0.001:
            issues.append(f"duration mismatch {clip_id}")
        scene_totals[clip_id.split("_")[0]] += round(duration, 3)
        _, true_peak = loudness(path)
        if true_peak > -1.0:
            issues.append(f"voice true peak {clip_id}: {true_peak:.2f} dBTP")
        if (VOICE_DIR / f"{clip_id}.raw.wav").exists():
            issues.append(f"raw voice remains {clip_id}")
    concat_path = VOICE_DIR / "_verify_concat.txt"
    concat_path.write_text("".join(f"file '{(VOICE_DIR / f'{clip_id}.wav').as_posix()}'\n" for clip_id in ids), encoding="utf-8")
    concat_lufs, concat_tp = loudness(concat_path, concat=True)
    concat_path.unlink(missing_ok=True)
    if abs(concat_lufs + 18.0) > 0.2:
        issues.append(f"voice concat loudness {concat_lufs:.2f} LUFS")
    if concat_tp > -1.0:
        issues.append(f"voice concat true peak {concat_tp:.2f} dBTP")
    bed = MUSIC_DIR / "bed.wav"
    bed_duration = probe_duration(bed)
    bed_lufs, bed_tp = loudness(bed)
    if bed_duration < 170:
        issues.append(f"bed duration {bed_duration:.2f}s")
    if abs(bed_lufs + 22.0) > 0.2:
        issues.append(f"bed loudness {bed_lufs:.2f} LUFS")
    sfx = sorted(SFX_DIR.glob("*.wav"))
    if len(sfx) != 29:
        issues.append(f"SFX count {len(sfx)}")
    sfx_rows = []
    for path in sfx:
        duration = probe_duration(path)
        _, true_peak = loudness(path)
        sfx_rows.append({"name": path.stem, "duration": round(duration, 3), "true_peak": round(true_peak, 2)})
        if true_peak > -1.0:
            issues.append(f"SFX peak {path.stem}: {true_peak:.2f} dBTP")
    report = {
        "voice_clips": len(ids),
        "voice_total": durations.get("_total"),
        "scene_totals": {key: round(value, 3) for key, value in scene_totals.items()},
        "voice_concat_lufs": round(concat_lufs, 2),
        "voice_concat_true_peak": round(concat_tp, 2),
        "bed_duration": round(bed_duration, 3),
        "bed_lufs": round(bed_lufs, 2),
        "bed_true_peak": round(bed_tp, 2),
        "sfx": sfx_rows,
        "issues": issues,
    }
    print(json.dumps(report, indent=2))
    if issues:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
