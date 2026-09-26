"""Offline score + sound design for v7 (no network, no generative model).

Writes two stems into assets/audio/:
  score.wav — the music bed (carved under the narration afterwards)
  sfx.wav   — practical sounds + ambience, timed to the picture

Every time below mirrors a beat in index.html (ROUTE, the S4/S5 step clocks,
the torch click, the split, the morph, the statement).
Bundled SFX come from the media-use skill (Pixabay Content License).
"""

import os
import subprocess

import numpy as np
from scipy import signal as sg
from scipy.io import wavfile

SR = 48000
DUR = 40.0
N = int(SR * DUR)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "assets", "audio")
SFX_DIR = os.path.join(os.path.expanduser("~"), ".claude", "skills", "media-use", "audio", "assets", "sfx")
rng = np.random.default_rng(7)
t = np.arange(N) / SR


def sos(kind, f, order=2):
    return sg.butter(order, f, btype=kind, fs=SR, output="sos")


def filt(x, kind, f, order=2):
    return sg.sosfilt(sos(kind, f, order), x)


def ramp(a, b, t0, t1):
    """0 before t0, linear to 1 at t1 (a..b amplitude)."""
    r = np.clip((t - t0) / max(1e-6, t1 - t0), 0, 1)
    return a + (b - a) * r


def window(t0, t1, fin=0.5, fout=0.5):
    up = np.clip((t - t0) / fin, 0, 1)
    dn = np.clip((t1 - t) / fout, 0, 1)
    return np.minimum(up, dn)


def saw(f):
    return 2 * ((t * f) % 1.0) - 1


def place(dst, clip, at, gain=1.0):
    i = int(at * SR)
    if i >= len(dst):
        return
    j = min(len(dst), i + len(clip))
    dst[i:j] += clip[: j - i] * gain


def load_sfx(name):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", os.path.join(SFX_DIR, name), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
        capture_output=True,
        check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def tone(f, dur, decay, attack=0.004):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    e = np.minimum(tt / attack, 1) * np.exp(-tt / decay)
    return np.sin(2 * np.pi * f * tt) * e


def thump(dur=0.5, f0=95, f1=42):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-tt / 0.05)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-tt / 0.16) * np.minimum(tt / 0.003, 1)


def mix(*parts):
    """Sum clips of different lengths (zero-padded)."""
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[: len(p)] += p
    return out


def noise_burst(dur, lo, hi, decay):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    x = rng.standard_normal(n)
    x = sg.sosfilt(sg.butter(2, [lo, hi], btype="bandpass", fs=SR, output="sos"), x)
    return x * np.exp(-tt / decay)


# ---------------------------------------------------------------- score ----
score = np.zeros(N)

# 1. drone — the building at night (0 → morph)
drone = 0.55 * np.sin(2 * np.pi * 55 * t) + 0.22 * np.sin(2 * np.pi * 82.41 * t + 0.4)
drone += 0.35 * filt(saw(55.15) + saw(54.85), "lowpass", 170)
drone *= 0.8 + 0.2 * np.sin(2 * np.pi * 0.07 * t)
drone_env = ramp(0, 1, 0.0, 3.0) * (1 - 0.25 * window(7.0, 15.0, 1.0, 1.0)) * (1 + 0.45 * ramp(0, 1, 24.8, 31.0))
drone_env *= np.clip((31.6 - t) / 0.9, 0, 1)
score += 0.16 * drone * drone_env

# 2. pad — slow detuned saw chords, low-passed
CHORDS = [
    (0.0, 7.2, [110.0, 130.81, 164.81]),  # A minor — quiet, watchful
    (7.0, 15.2, [110.0, 130.81, 174.61]),  # F/A — something is wrong
    (15.0, 25.0, [110.0, 130.81, 164.81, 196.0]),  # Am7 — the routine
    (24.8, 31.6, [82.41, 103.83, 123.47, 164.81]),  # E — tension that never resolves
]
pad = np.zeros(N)
for t0, t1, notes in CHORDS:
    w = window(t0, t1, 0.9, 0.9)
    layer = np.zeros(N)
    for f in notes:
        for d in (-0.35, 0.0, 0.4):
            layer += saw(f * (1 + d / 100))
    pad += layer * w / len(notes)
pad = filt(pad, "lowpass", 900) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.11 * t))
pad_env = ramp(0, 1, 0.3, 4.0) * (1 + 0.5 * ramp(0, 1, 26.0, 31.0)) * np.clip((31.7 - t) / 1.0, 0, 1)
score += 0.05 * pad * pad_env

# 3. heartbeat — the intruder (S2) and the rising count (S4)
for k in range(9):
    at = 7.35 + k * 0.92
    if at > 14.9:
        break
    place(score, thump(), at, 0.30)
    place(score, thump(0.4, 80, 40), at + 0.24, 0.18)
n4 = 0
while True:
    at = 24.8 + n4 * 0.44
    if at > 30.9:
        break
    place(score, thump(0.35, 88, 44), at, 0.16 + 0.12 * n4 / 13)
    n4 += 1

# 4. riser into the transformation
rs = np.zeros(N)
m = (t >= 29.2) & (t < 31.05)
u = np.clip((t - 29.2) / 1.85, 0, 1)
rs += np.sin(2 * np.pi * np.cumsum(180 + 620 * u**2) / SR) * u**2
nz = filt(rng.standard_normal(N), "bandpass", [900, 5000]) * u**3
rs = (rs * 0.5 + nz * 0.8) * m
score += 0.10 * rs

# 5. the instrument — a clean, cold chord for the technical world
tech = np.zeros(N)
for f, a in ((110.0, 0.5), (164.81, 0.35), (220.0, 0.3), (246.94, 0.22), (329.63, 0.14)):
    tech += a * (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.003 * t + 1.1))
shimmer = 0.05 * np.sin(2 * np.pi * 1760 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 3.1 * t))
shimmer += 0.03 * np.sin(2 * np.pi * 2637 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 2.3 * t + 1))
tech_env = ramp(0, 1, 31.4, 33.2) * (1 + 0.3 * ramp(0, 1, 35.9, 38.0)) * np.clip((40.0 - t) / 0.35, 0, 1)
score += 0.07 * filt(tech, "lowpass", 2400) * tech_env + shimmer * tech_env * 0.5

# ------------------------------------------------------------------ sfx ----
sfx = np.zeros(N)

# ambience: night wind outside, room tone inside, instrument hum at the end
wind = filt(rng.standard_normal(N), "lowpass", 520) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.13 * t))
outside = window(0.0, 9.8, 1.2, 0.05) + window(12.8, 31.3, 0.05, 0.6)
sfx += 0.05 * wind * outside
room = filt(rng.standard_normal(N), "lowpass", 300) * window(9.8, 12.8, 0.05, 0.05)
sfx += 0.035 * room

click = load_sfx("click.mp3")
click_soft = load_sfx("click-soft.mp3")
whoosh_s = load_sfx("whoosh-short.mp3")
whoosh_c = load_sfx("whoosh-cinematic.mp3")
glitch = load_sfx("glitch-1.mp3")
impact = load_sfx("impact-bass-1.mp3")

# footsteps: side door (sneaking) and inside room 10
for at in np.arange(7.1, 8.6, 0.33):
    place(sfx, noise_burst(0.12, 120, 900, 0.03), at, 0.35)
for at in (9.9, 10.22, 10.52, 10.78):
    place(sfx, noise_burst(0.12, 140, 1000, 0.03), at, 0.28)
# fire door: latch + creak + close
place(sfx, noise_burst(0.08, 1500, 5000, 0.015), 8.93, 0.5)
cr_n = int(0.42 * SR)
ct = np.arange(cr_n) / SR
creak = sg.sosfilt(sg.butter(2, [500, 2400], btype="bandpass", fs=SR, output="sos"), ((ct * (230 + 90 * np.sin(ct * 19))) % 1.0) * 2 - 1)
creak *= np.sin(np.pi * ct / 0.42) ** 2
place(sfx, creak, 9.0, 0.22)
place(sfx, thump(0.4, 120, 60), 9.62, 0.25)

# the torch clicks on (room 10) and again for the split
place(sfx, click, 11.06, 0.9)
place(sfx, click_soft, 18.2, 0.35)
# the guard's spotlight: switch + a faint electrical hum while it is on
place(sfx, click, 15.52, 0.85)
hum = (np.sin(2 * np.pi * 100 * t) + 0.4 * np.sin(2 * np.pi * 200 * t) + 0.15 * np.sin(2 * np.pi * 300 * t))
sfx += 0.012 * hum * window(15.55, 31.2, 0.08, 0.6) * (1 - window(18.2, 22.4, 0.05, 0.05) * 0.6)

# the light swings — a short servo tick on every move (the retune)
ROUTE = [16.75, 22.45, 23.0, 23.55] + [24.8 + 0.44 * n for n in range(14)]
for at in ROUTE:
    place(sfx, noise_burst(0.05, 2500, 7000, 0.008), at, 0.22)
    place(sfx, tone(210, 0.08, 0.02), at + 0.01, 0.12)

# split screen
place(sfx, whoosh_s, 18.12, 0.55)

# S4 torch flicks (one per event) and the two honest catches
S4_ROOMS = [15, 3, 14, 6, 10, 1, 8, 12, 4, 16, 9, 2, 7, 13]
for n in range(1, 14):
    at = 24.8 + 0.44 * n + 0.05
    place(sfx, click_soft, at, 0.22 + 0.1 * (n / 13))
for n in (6, 11):
    at = 24.8 + 0.44 * n + 0.08
    place(sfx, mix(tone(1318.5, 0.35, 0.09), 0.5 * tone(1975.5, 0.3, 0.07)), at, 0.16)

# the transformation
place(sfx, whoosh_c, 29.9, 0.55)
place(sfx, glitch[: int(1.2 * SR)] * np.linspace(1, 0, int(1.2 * SR)), 31.25, 0.18)

# the receiver steps (S5): a quiet data tick per step
for k in range(17):
    at = 32.6 + 0.45 * k
    place(sfx, tone(1480, 0.06, 0.018), at, 0.07)
    place(sfx, noise_burst(0.03, 4000, 9000, 0.006), at, 0.06)

# the statement lands
place(sfx, impact, 35.9, 0.5)
place(sfx, mix(tone(880, 1.8, 0.9, attack=0.02), 0.4 * tone(1318.5, 1.6, 0.8, attack=0.02)), 37.62, 0.05)

# ---------------------------------------------------------------- write ----
def norm_to(x, peak_db):
    p = np.max(np.abs(x)) + 1e-9
    return x * (10 ** (peak_db / 20) / p)


def stereo(x, width=0.0):
    # tiny decorrelation for width on the bed
    d = int(0.011 * SR)
    r = np.concatenate([np.zeros(d), x[:-d]]) if width else x
    return np.stack([x, (1 - width) * x + width * r], axis=1)


os.makedirs(OUT, exist_ok=True)
score = norm_to(score, -9.0)
sfx = norm_to(sfx, -6.0)
wavfile.write(os.path.join(OUT, "score.wav"), SR, (stereo(score, 0.35) * 32767).astype(np.int16))
wavfile.write(os.path.join(OUT, "sfx.wav"), SR, (stereo(sfx) * 32767).astype(np.int16))
print("score rms dB", 20 * np.log10(np.sqrt(np.mean(score**2)) + 1e-9))
print("sfx rms dB", 20 * np.log10(np.sqrt(np.mean(sfx**2)) + 1e-9))
