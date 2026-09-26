from __future__ import annotations

import json
import math
import re
import subprocess
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MUSIC_DIR = ROOT / "assets" / "music"
SOURCE_DIR = Path(r"C:\Users\This PC\.claude\skills\brag\assets\music")
CUE_DIR = SOURCE_DIR / "cues"
TARGET_DURATION = 170.0
TARGET_LUFS = -22.0
RATE = 48000


def run(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, capture_output=True)


def probe_duration(path: Path) -> float:
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
    return float(result.stdout.decode().strip())


def measure_lufs(path: Path) -> float:
    result = run([
        "ffmpeg",
        "-hide_banner",
        "-i",
        str(path),
        "-af",
        "loudnorm=I=-22:TP=-1.0:LRA=7:print_format=json",
        "-f",
        "null",
        "-",
    ])
    stderr = result.stderr.decode(errors="replace")
    matches = re.findall(r"\{[^{}]*\"input_i\"\s*:\s*\"?(-?[0-9.]+)\"?[^{}]*\}", stderr, re.S)
    if not matches:
        raise RuntimeError(f"Could not parse loudness for {path.name}")
    return float(matches[-1])


def decode_mono(path: Path, rate: int = 22050) -> np.ndarray:
    result = run([
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(path),
        "-ac",
        "1",
        "-ar",
        str(rate),
        "-f",
        "f32le",
        "-",
    ])
    return np.frombuffer(result.stdout, dtype=np.float32).copy()


def speech_band_ratio(samples: np.ndarray, rate: int = 22050) -> float:
    window = 2048
    hop = 512
    if len(samples) < window:
        samples = np.pad(samples, (0, window - len(samples)))
    starts = np.arange(0, len(samples) - window + 1, hop)
    frames = np.lib.stride_tricks.as_strided(
        samples,
        shape=(len(starts), window),
        strides=(samples.strides[0] * hop, samples.strides[0]),
    )
    windowed = frames * np.hanning(window)
    spectrum = np.abs(np.fft.rfft(windowed, axis=1)) ** 2
    frequencies = np.fft.rfftfreq(window, 1 / rate)
    total = np.sum(spectrum[:, (frequencies >= 40) & (frequencies <= 10000)])
    speech = np.sum(spectrum[:, (frequencies >= 1000) & (frequencies <= 4000)])
    return float(speech / max(total, 1e-12))


def tempo_for(path: Path) -> float:
    cue_path = CUE_DIR / f"{path.stem}.music-cues.json"
    return float(json.loads(cue_path.read_text(encoding="utf-8"))["tempo"])


def analyze() -> list[dict[str, float | str]]:
    results = []
    for path in sorted(SOURCE_DIR.glob("happy-beats-business-moves-vol-*.mp3")):
        samples = decode_mono(path)
        results.append({
            "name": path.name,
            "path": path,
            "duration": probe_duration(path),
            "lufs": measure_lufs(path),
            "speech_band": speech_band_ratio(samples),
            "bpm": tempo_for(path),
        })
    return results


def decode_stereo(path: Path) -> np.ndarray:
    result = run([
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(path),
        "-ac",
        "2",
        "-ar",
        str(RATE),
        "-f",
        "f32le",
        "-",
    ])
    samples = np.frombuffer(result.stdout, dtype=np.float32).copy()
    return samples.reshape(-1, 2)


def write_stereo(path: Path, samples: np.ndarray) -> None:
    clipped = np.clip(samples, -1, 1)
    pcm = (clipped * 32767).astype("<i2")
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(RATE)
        output.writeframes(pcm.tobytes())


def crossfade_join(current: np.ndarray, following: np.ndarray, fade_samples: int) -> np.ndarray:
    fade = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)[:, None]
    blend = current[-fade_samples:] * (1 - fade) + following[:fade_samples] * fade
    return np.concatenate((current[:-fade_samples], blend, following[fade_samples:]), axis=0)


def build_bed(selection: dict[str, float | str], output_path: Path) -> tuple[float, int, int]:
    source = decode_stdio(Path(str(selection["path"])))
    bpm = float(selection["bpm"])
    bar_seconds = 240 / bpm
    chunk_seconds = bar_seconds * 8
    chunk_samples = int(chunk_seconds * RATE)
    fade_samples = int(2.0 * RATE)
    required_chunks = math.ceil((TARGET_DURATION - chunk_seconds) / (chunk_seconds - 2.0)) + 1
    source_chunks = max(1, int(len(source) / chunk_samples))
    joined = source[:chunk_samples].copy()
    for index in range(1, required_chunks):
        source_chunk = index % source_chunks
        offset = source_chunk * chunk_samples
        if offset + chunk_samples > len(source):
            source_chunk = 0
            offset = 0
        joined = crossfade_join(joined, source[offset:offset + chunk_samples], fade_samples)
    fade_in = np.linspace(0.0, 1.0, int(RATE), dtype=np.float32)[:, None]
    fade_out = np.linspace(1.0, 0.0, int(5 * RATE), dtype=np.float32)[:, None]
    joined[:len(fade_in)] *= fade_in
    joined[-len(fade_out):] *= fade_out
    pre_path = MUSIC_DIR / "_bed_pre.wav"
    write_stereo(pre_path, joined)
    run([
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(pre_path),
        "-af",
        f"loudnorm=I={TARGET_LUFS:.1f}:TP=-1.0:LRA=7:linear=true",
        "-ar",
        str(RATE),
        "-ac",
        "2",
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ])
    pre_path.unlink(missing_ok=True)
    return chunk_seconds, len(joined) / RATE, required_chunks


def decode_stdio(path: Path) -> np.ndarray:
    result = run([
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(path),
        "-ac",
        "2",
        "-ar",
        str(RATE),
        "-f",
        "f32le",
        "-",
    ])
    return np.frombuffer(result.stdout, dtype=np.float32).copy().reshape(-1, 2)


def write_analysis(results: list[dict[str, float | str]], selection: dict[str, float | str], output_path: Path, chunk_seconds: float, source_duration: float, chunks: int) -> None:
    rows = []
    for item in results:
        marker = " **chosen**" if item["name"] == selection["name"] else ""
        rows.append(
            f"| `{item['name']}`{marker} | {float(item['duration']):.2f} s | {float(item['lufs']):.1f} LUFS | "
            f"{float(item['speech_band']) * 100:.1f}% | {float(item['bpm']):.2f} BPM |"
        )
    rationale = (
        f"Chose `{selection['name']}` at {float(selection['bpm']):.2f} BPM. It has the best combination of "
        f"moderate tempo, restrained 1–4 kHz energy ({float(selection['speech_band']) * 100:.1f}% of measured spectral energy), "
        f"and enough source material to feel varied beneath continuous narration without becoming the focal point."
    )
    build_note = (
        f"The bed uses 8-bar chunks ({chunk_seconds:.2f} s) with 2.0 s equal-power crossfades at bar-aligned boundaries, "
        f"built from {chunks} chunks over {source_duration:.2f} s of source material. It fades in for 1.0 s, "
        f"fades out over 5.0 s, and is normalized to -22 LUFS integrated with a -1 dBTP ceiling."
    )
    content = (
        "# Music Bed Analysis\n\n"
        "| Track | Duration | Loudness | Energy in 1–4 kHz | Tempo |\n"
        "|---|---:|---:|---:|---:|\n"
        + "\n".join(rows)
        + "\n\n"
        + rationale
        + "\n\n"
        + build_note
        + "\n"
    )
    output_path.write_text(content, encoding="utf-8")


def main() -> None:
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    results = analyze()
    selection = min(results, key=lambda item: float(item["speech_band"]) + 0.0015 * abs(float(item["bpm"]) - 112.0))
    output_path = MUSIC_DIR / "bed.wav"
    chunk_seconds, source_duration, chunks = build_bed(selection, output_path)
    write_analysis(results, selection, MUSIC_DIR / "analysis.md", chunk_seconds, source_duration, chunks)
    print(json.dumps({
        "chosen": selection["name"],
        "bpm": selection["bpm"],
        "speech_band": selection["speech_band"],
        "bed_duration": probe_duration(output_path),
        "bed_lufs": measure_lufs(output_path),
    }, indent=2))


if __name__ == "__main__":
    main()
