from __future__ import annotations

import json
import math
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VOICE_DIR = ROOT / "assets" / "voice"
NARRATION = ROOT / "narration.txt"
TARGET_LUFS = -18.0


def run(command: list[str], stdin=subprocess.DEVNULL) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, stdin=stdin, text=True, capture_output=True)


def parse_lines() -> list[tuple[str, str]]:
    lines = []
    for raw in NARRATION.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        clip_id, text = raw.split("|", 1)
        lines.append((clip_id.strip(), text.strip()))
    return lines


def synthesize(clip_id: str) -> None:
    text_path = VOICE_DIR / f"{clip_id}.txt"
    raw_path = VOICE_DIR / f"{clip_id}.raw.wav"
    run([
        "npx.cmd",
        "--yes",
        "hyperframes@0.8.73",
        "tts",
        str(text_path),
        "-o",
        str(raw_path),
        "-v",
        "af_heart",
        "-s",
        "1.1",
    ])


def trim(clip_id: str) -> Path:
    raw_path = VOICE_DIR / f"{clip_id}.raw.wav"
    trim_path = VOICE_DIR / f"{clip_id}.trim.wav"
    filter_graph = (
        "silenceremove=start_periods=1:start_duration=0.05:start_threshold=-45dB:detection=peak,"
        "areverse,"
        "silenceremove=start_periods=1:start_duration=0.08:start_threshold=-45dB:detection=peak,"
        "areverse,adelay=40:all=1,apad=pad_dur=0.10,aresample=48000"
    )
    run([
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(raw_path),
        "-af",
        filter_graph,
        "-ar",
        "48000",
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        str(trim_path),
    ])
    return trim_path


def measure_concat_loudness(trimmed: list[Path]) -> float:
    concat_path = VOICE_DIR / "_concat.txt"
    concat_path.write_text(
        "".join(f"file '{path.name}'\n" for path in trimmed),
        encoding="utf-8",
    )
    result = run([
        "ffmpeg",
        "-hide_banner",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_path),
        "-af",
        "loudnorm=I=-18:TP=-1.0:LRA=7:print_format=json",
        "-f",
        "null",
        "-",
    ])
    matches = re.findall(r"\{[^{}]*\"input_i\"\s*:\s*\"?(-?[0-9.]+)\"?[^{}]*\}", result.stderr, re.S)
    if not matches:
        raise RuntimeError("Could not parse concatenated narration loudness")
    concat_path.unlink(missing_ok=True)
    return float(matches[-1])


def finalize(clip_id: str, trim_path: Path, gain_db: float) -> Path:
    final_path = VOICE_DIR / f"{clip_id}.wav"
    filter_graph = (
        f"volume={gain_db:.4f}dB,"
        "alimiter=limit=0.891251:attack=5:release=50:level=disabled,"
        "aresample=48000"
    )
    run([
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(trim_path),
        "-af",
        filter_graph,
        "-ar",
        "48000",
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        str(final_path),
    ])
    (VOICE_DIR / f"{clip_id}.raw.wav").unlink(missing_ok=True)
    trim_path.unlink(missing_ok=True)
    return final_path


def duration(path: Path) -> float:
    result = run([
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=nw=1:nk=1",
        str(path),
    ])
    return float(result.stdout.strip())


def main() -> None:
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    entries = parse_lines()
    for clip_id, text in entries:
        (VOICE_DIR / f"{clip_id}.txt").write_text(text + "\n", encoding="utf-8")
    for index, (clip_id, _) in enumerate(entries, 1):
        print(f"[{index}/{len(entries)}] synthesizing {clip_id}", flush=True)
        synthesize(clip_id)
    trimmed = [trim(clip_id) for clip_id, _ in entries]
    measured_lufs = measure_concat_loudness(trimmed)
    gain_db = TARGET_LUFS - measured_lufs
    print(f"Measured {measured_lufs:.2f} LUFS; applying {gain_db:.2f} dB", flush=True)
    durations: dict[str, float] = {}
    for clip_id, trim_path in zip((entry[0] for entry in entries), trimmed):
        final_path = finalize(clip_id, trim_path, gain_db)
        durations[clip_id] = round(duration(final_path), 3)
    durations["_total"] = round(sum(value for key, value in durations.items() if key != "_total"), 3)
    (VOICE_DIR / "durations.json").write_text(
        json.dumps(durations, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Voice total: {durations['_total']:.3f}s", flush=True)


if __name__ == "__main__":
    main()
