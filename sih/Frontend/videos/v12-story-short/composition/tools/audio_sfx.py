from __future__ import annotations

import math
import re
import subprocess
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SFX_DIR = ROOT / "assets" / "sfx"
SOURCE_DIR = Path(r"C:\Users\This PC\.claude\skills\brag\assets\sfx")
RATE = 48000
PEAK = 10 ** (-3 / 20)


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


def peak_db(path: Path) -> float:
    result = run([
        "ffmpeg",
        "-hide_banner",
        "-i",
        str(path),
        "-af",
        "volumedetect",
        "-f",
        "null",
        "-",
    ])
    stderr = result.stderr.decode(errors="replace")
    match = re.search(r"max_volume:\s*(-?[0-9.]+) dB", stderr)
    if not match:
        raise RuntimeError(f"Could not measure peak for {path}")
    return float(match.group(1))


def convert_source(name: str, relative: str) -> dict[str, str | float]:
    source = SOURCE_DIR / relative
    output = SFX_DIR / f"{name}.wav"
    duration = probe_duration(source)
    gain = -3.0 - peak_db(source)
    fade_out = max(0.0, duration - 0.015)
    filters = (
        "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.005,"
        "areverse,"
        "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.02,"
        f"areverse,afade=t=in:st=0:d=0.003,afade=t=out:st={fade_out:.6f}:d=0.015,"
        f"volume={gain:.3f}dB,alimiter=limit={PEAK:.6f}:attack=2:release=20:level=disabled"
    )
    run([
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-af",
        filters,
        "-ar",
        str(RATE),
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        str(output),
    ])
    return {
        "name": name,
        "duration": probe_duration(output),
        "description": f"Library conversion from {relative}",
        "volume": "0.35",
    }


def time_axis(duration: float) -> np.ndarray:
    return np.arange(int(duration * RATE), dtype=np.float64) / RATE


def edge_fade(samples: np.ndarray, seconds: float = 0.003) -> np.ndarray:
    result = samples.copy()
    count = min(len(result), int(seconds * RATE))
    if count:
        ramp = np.linspace(0, 1, count, endpoint=True)
        result[:count] *= ramp
        result[-count:] *= ramp[::-1]
    return result


def normalize_peak(samples: np.ndarray, target_db: float = -3.0) -> np.ndarray:
    target = 10 ** (target_db / 20)
    peak = float(np.max(np.abs(samples)))
    return samples * (target / max(peak, 1e-12))


def write_mono(name: str, samples: np.ndarray, target_db: float = -3.0) -> dict[str, str | float]:
    output = SFX_DIR / f"{name}.wav"
    processed = normalize_peak(edge_fade(samples), target_db)
    pcm = (np.clip(processed, -1, 1) * 32767).astype("<i2")
    with wave.open(str(output), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(pcm.tobytes())
    return {"name": name, "duration": probe_duration(output)}


def chirp(duration: float, start_hz: float, end_hz: float, amplitude: np.ndarray | float = 1.0, phase_offset: float = 0.0) -> np.ndarray:
    t = time_axis(duration)
    frequency = start_hz + (end_hz - start_hz) * (t / max(duration, 1e-9))
    phase = 2 * np.pi * np.cumsum(frequency) / RATE + phase_offset
    return np.asarray(amplitude) * np.sin(phase)


def add_event(buffer: np.ndarray, event: np.ndarray, start: float, gain: float = 1.0) -> np.ndarray:
    offset = int(start * RATE)
    end = min(len(buffer), offset + len(event))
    if offset < len(buffer) and end > offset:
        buffer[offset:end] += event[:end - offset] * gain
    return buffer


def make_whoosh(duration: float, low_hz: float, high_hz: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = time_axis(duration)
    progress = t / duration
    rise = np.sin(np.pi * np.minimum(progress / 0.5, 1.0) * 0.5)
    fall = np.sin(np.pi * np.minimum(np.maximum((progress - 0.5) / 0.5, 0.0), 1.0) * 0.5)
    envelope = rise * fall
    frequency = low_hz + (high_hz - low_hz) * np.sin(np.pi * progress) ** 2
    carrier = np.sin(2 * np.pi * np.cumsum(frequency) / RATE)
    noise = rng.normal(0, 1, len(t))
    shaped = 0.78 * noise * carrier + 0.22 * carrier
    return shaped * envelope


def make_pop(soft: bool) -> np.ndarray:
    duration = 0.12 if soft else 0.10
    t = time_axis(duration)
    frequency = (360 if soft else 720) - ((180 if soft else 420) * t / duration)
    phase = 2 * np.pi * np.cumsum(frequency) / RATE
    envelope = np.exp(-t * (24 if soft else 34))
    tone = np.sin(phase) + (0.18 if soft else 0.35) * np.sin(2 * phase)
    return tone * envelope


def make_ding() -> np.ndarray:
    t = time_axis(0.9)
    signal = np.zeros_like(t)
    for frequency, gain, decay in ((880, 1.0, 5.5), (1320, 0.45, 7.0), (1760, 0.22, 8.5), (2640, 0.08, 11.0)):
        signal += gain * np.sin(2 * np.pi * frequency * t) * np.exp(-decay * t)
    return signal


def make_success() -> np.ndarray:
    buffer = np.zeros(int(0.8 * RATE))
    for start, frequency in ((0.0, 523.25), (0.18, 659.25), (0.36, 783.99)):
        duration = 0.38
        t = time_axis(duration)
        event = (np.sin(2 * np.pi * frequency * t) + 0.25 * np.sin(4 * np.pi * frequency * t)) * np.exp(-5.5 * t)
        add_event(buffer, event, start)
    return buffer


def make_fail() -> np.ndarray:
    t = time_axis(0.5)
    frequency = 330 * np.exp(-1.5 * t) + 95
    phase = 2 * np.pi * np.cumsum(frequency) / RATE
    envelope = np.sin(np.pi * np.clip(t / 0.5, 0, 1)) * np.exp(-1.2 * t)
    buzz = np.sin(phase) + 0.32 * np.sin(2 * phase) + 0.14 * np.sin(3 * phase)
    return buzz * envelope


def make_tick(frequency: float, duration: float = 0.06, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = time_axis(duration)
    noise = rng.normal(0, 1, len(t))
    click = np.sin(2 * np.pi * frequency * t) + 0.18 * noise
    return click * np.exp(-75 * t)


def make_riser() -> np.ndarray:
    duration = 1.6
    t = time_axis(duration)
    rng = np.random.default_rng(19)
    progress = t / duration
    frequency = 180 * (1 + 6.0 * progress ** 1.7)
    tone = np.sin(2 * np.pi * np.cumsum(frequency) / RATE)
    noise = rng.normal(0, 1, len(t))
    envelope = progress ** 2.2 * (1 - np.exp(-25 * t))
    return (0.72 * noise * progress + 0.55 * tone) * envelope


def make_coin_drop() -> np.ndarray:
    buffer = np.zeros(int(0.6 * RATE))
    events = ((0.0, 2050, 1.0), (0.065, 2780, 0.8), (0.14, 3320, 0.62), (0.28, 1900, 0.52), (0.41, 3020, 0.4))
    for start, frequency, gain in events:
        duration = 0.22
        t = time_axis(duration)
        event = (np.sin(2 * np.pi * frequency * t) + 0.35 * np.sin(3.8 * np.pi * frequency * t)) * np.exp(-16 * t)
        add_event(buffer, event, start, gain)
    return buffer


def click_train(duration: float, count: int, start_interval: float, end_interval: float, start_hz: float, end_hz: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    intervals = np.geomspace(start_interval, end_interval, count - 1)
    times = np.concatenate(([0.0], np.cumsum(intervals)))
    times = times[times < duration]
    buffer = np.zeros(int(duration * RATE))
    for index, start in enumerate(times):
        progress = start / duration
        frequency = start_hz + (end_hz - start_hz) * progress
        event_duration = min(0.045, max(0.012, end_interval * 0.32))
        t = time_axis(event_duration)
        jitter = rng.uniform(0.82, 1.18, len(t))
        event = (np.sin(2 * np.pi * frequency * t) + 0.22 * rng.normal(0, 1, len(t))) * np.exp(-55 * t) * jitter
        gain = 0.85 - 0.2 * progress
        add_event(buffer, event, start, gain)
    return buffer


def make_robot_bleeps() -> np.ndarray:
    buffer = np.zeros(int(0.8 * RATE))
    for start, frequency in ((0.05, 720), (0.31, 880), (0.54, 1040)):
        duration = 0.12
        t = time_axis(duration)
        event = (np.sin(2 * np.pi * frequency * t) + 0.2 * np.sin(4 * np.pi * frequency * t)) * np.sin(np.pi * t / duration)
        add_event(buffer, event, start, 0.75)
    return buffer


def make_marker() -> np.ndarray:
    duration = 0.6
    t = time_axis(duration)
    rng = np.random.default_rng(23)
    noise = rng.normal(0, 1, len(t))
    spectrum = np.fft.rfft(noise)
    frequencies = np.fft.rfftfreq(len(t), 1 / RATE)
    spectrum[(frequencies < 1200) | (frequencies > 7200)] = 0
    filtered = np.fft.irfft(spectrum, n=len(t))
    wobble = 0.45 + 0.55 * np.abs(np.sin(2 * np.pi * 19 * t) * np.sin(2 * np.pi * 7 * t))
    envelope = np.sin(np.pi * np.clip(t / duration, 0, 1)) ** 0.5
    tone = 0.22 * np.sin(2 * np.pi * 2450 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 31 * t))
    return (filtered + tone) * wobble * envelope


def make_sparkle() -> np.ndarray:
    buffer = np.zeros(int(0.8 * RATE))
    for start, end, gain in ((0.0, 4600, 0.7), (0.18, 5200, 0.58), (0.39, 6100, 0.46), (0.58, 7000, 0.34)):
        duration = 0.22
        event = chirp(duration, 1800, end) * np.exp(-9 * time_axis(duration))
        add_event(buffer, event, start, gain)
    return buffer


def make_zap() -> np.ndarray:
    duration = 0.25
    t = time_axis(duration)
    rng = np.random.default_rng(31)
    swept = chirp(duration, 1600, 180)
    noise = rng.normal(0, 1, len(t))
    return (0.8 * swept + 0.2 * noise * np.exp(-14 * t)) * np.exp(-9 * t)


def make_sweep_tick() -> np.ndarray:
    duration = 0.12
    t = time_axis(duration)
    event = chirp(duration, 1350, 620) * np.exp(-24 * t)
    return event


def generated_sfx() -> list[dict[str, str | float]]:
    generated = []
    generated.append({**write_mono("whoosh", make_whoosh(0.40, 650, 2800, 7)), "description": "Band-limited noise sweep rising then falling", "volume": "0.32"})
    generated.append({**write_mono("whoosh_big", make_whoosh(0.75, 180, 1300, 11)), "description": "Deeper, longer transition whoosh", "volume": "0.38"})
    generated.append({**write_mono("pop", make_pop(False)), "description": "Bubbly speech-bubble pop", "volume": "0.28"})
    generated.append({**write_mono("pop_soft", make_pop(True), -8.0), "description": "Quieter rounded speech-bubble pop", "volume": "0.20"})
    generated.append({**write_mono("ding", make_ding()), "description": "Bright bell-like confirmation chime", "volume": "0.32"})
    generated.append({**write_mono("success", make_success()), "description": "Three rising happy confirmation notes", "volume": "0.34"})
    generated.append({**write_mono("fail", make_fail()), "description": "Soft comic descending wah", "volume": "0.28"})
    generated.append({**write_mono("tick", make_tick(1850, seed=41)), "description": "Clock tick", "volume": "0.18"})
    generated.append({**write_mono("tock", make_tick(1420, seed=43)), "description": "Clock tock", "volume": "0.18"})
    generated.append({**write_mono("riser", make_riser()), "description": "Rising noise and tone build", "volume": "0.30"})
    generated.append({**write_mono("coin_drop", make_coin_drop()), "description": "Cluster of metallic coin pings", "volume": "0.30"})
    generated.append({**write_mono("slot_spin", click_train(1.4, 28, 0.018, 0.16, 1300, 1850, 53)), "description": "Ratchet clicks slowing to a stop", "volume": "0.24"})
    generated.append({**write_mono("wheel_spin", click_train(2.4, 44, 0.016, 0.18, 2700, 1650, 59)), "description": "Prize-wheel clicks slowing to a stop", "volume": "0.24"})
    generated.append({**write_mono("robot_bleeps", make_robot_bleeps()), "description": "Cute computer bleep sequence", "volume": "0.26"})
    generated.append({**write_mono("marker", make_marker()), "description": "Whiteboard marker squeak and scribble", "volume": "0.22"})
    generated.append({**write_mono("sparkle", make_sparkle()), "description": "Twinkling high glissando", "volume": "0.20"})
    generated.append({**write_mono("zap", make_zap()), "description": "Soft electric torch or radio flash", "volume": "0.28"})
    generated.append({**write_mono("sweep_tick", make_sweep_tick()), "description": "Soft UI scanning tick", "volume": "0.18"})
    return generated


def write_manifest(items: list[dict[str, str | float]]) -> None:
    rows = ["| Name | Duration | Description | Suggested volume |", "|---|---:|---|---:|"]
    for item in items:
        rows.append(f"| `{item['name']}.wav` | {float(item['duration']):.3f} s | {item['description']} | {item['volume']} |")
    content = "# SFX Manifest\n\nAll files are 48 kHz, mono, 16-bit PCM. Volumes are linear gain multipliers for placement under narration.\n\n" + "\n".join(rows) + "\n"
    (SFX_DIR / "MANIFEST.md").write_text(content, encoding="utf-8")


def main() -> None:
    SFX_DIR.mkdir(parents=True, exist_ok=True)
    library = [
        convert_source("dice_shake", "casino/dice-shake-2.ogg"),
        convert_source("dice_throw", "casino/dice-throw-3.ogg"),
        convert_source("chips", "casino/chips-stack-2.ogg"),
        convert_source("card_slide", "casino/card-slide-1.ogg"),
        convert_source("click", "ui/click1.ogg"),
        convert_source("switch", "ui/switch1.ogg"),
        convert_source("stamp", "impact/impactPunch_heavy_000.ogg"),
        convert_source("clunk", "impact/impactMetal_medium_000.ogg"),
        convert_source("bell", "impact/impactBell_heavy_000.ogg"),
        convert_source("footstep", "impact/footstep_concrete_000.ogg"),
        convert_source("key", "keyboard/keypress-001.wav"),
    ]
    items = library + generated_sfx()
    write_manifest(items)
    print(f"Wrote {len(items)} SFX files")


if __name__ == "__main__":
    main()
