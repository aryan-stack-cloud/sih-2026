"""Picture-locked score + SFX stems for v6 (40.0 s).

Deterministic: fixed RNG seed, no network. Every cue time below mirrors a
schedule in index.html (BEAM / FLASHES / BURSTS / scan dwell / FREEZE), so the
sound lands on the frame. Re-run after retiming the picture:

    python audio-src/build_audio.py

Writes assets/score/score.wav (music bed, carved under the voice in index.html)
and assets/sfx/sfx.wav (effects, never carved). 48 kHz stereo, 24-bit.
"""

import os
import subprocess

import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000
DUR = 40.0
N = int(SR * DUR)
FREEZE = 37.15
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.normpath(os.path.join(HERE, "..", "assets"))
BUNDLED = os.path.expanduser(r"~/.claude/skills/media-use/audio/assets/sfx")
rng = np.random.default_rng(20260924)


# ---------------------------------------------------------------- primitives
def tv(n):
    return np.arange(n) / SR


def st(x, pan=0.0):
    """mono -> stereo, constant-power pan in [-1, 1]"""
    a = (pan + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1)


def add(buf, x, t0, gain=1.0, pan=0.0):
    if x.ndim == 1:
        x = st(x, pan)
    i = int(round(t0 * SR))
    j = min(N, i + len(x))
    if j <= 0 or i >= N:
        return
    s = max(0, -i)
    buf[max(i, 0):j] += gain * x[s:j - i]


def filt(x, kind, f, order=2):
    if kind == "band":
        b, a = signal.butter(order, [f[0] / (SR / 2), f[1] / (SR / 2)], "band")
    else:
        b, a = signal.butter(order, min(0.999, f / (SR / 2)), kind)
    return signal.lfilter(b, a, x, axis=0)


def tv_lowpass(x, fc_of_t, block=256):
    """time-varying 2-pole low-pass: coefficients per block, state carried"""
    y = np.zeros_like(x)
    zi = np.zeros(2)
    for i in range(0, len(x), block):
        fc = fc_of_t(i / SR)
        b, a = signal.butter(2, min(0.99, max(20.0, fc) / (SR / 2)), "low")
        y[i:i + block], zi = signal.lfilter(b, a, x[i:i + block], zi=zi)
    return y


def curve(t, pts):
    xs, ys = zip(*pts)
    return np.interp(t, xs, ys)


def saw(f, n, ph=0.0):
    return signal.sawtooth(2 * np.pi * f * tv(n) + ph)


def sine_sweep(f0, f1, n, k=6.0):
    """exponential pitch glide f0 -> f1"""
    t = tv(n)
    f = f1 + (f0 - f1) * np.exp(-k * t / (n / SR))
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def noise(n):
    return rng.standard_normal(n)


def brown(n):
    x = np.cumsum(rng.standard_normal(n))
    x = filt(x, "high", 18.0)
    return x / (np.max(np.abs(x)) + 1e-9)


def reverb_ir(seconds, damp=6500.0, predelay=0.018):
    n = int(seconds * SR)
    t = tv(n)
    out = []
    for _ in range(2):
        ir = rng.standard_normal(n) * np.exp(-t * 6.9 / seconds)
        ir = filt(ir, "low", damp)
        ir = np.concatenate([np.zeros(int(predelay * SR)), ir])
        out.append(ir / np.sqrt(np.sum(ir ** 2)))
    return out


def reverb(x, ir, wet):
    if x.ndim == 1:
        x = st(x)
    L = signal.fftconvolve(x[:, 0], ir[0])[: len(x)]
    R = signal.fftconvolve(x[:, 1], ir[1])[: len(x)]
    return x * (1 - wet) + np.stack([L, R], 1) * wet


def kick(f0, f1, dur, click=0.25):
    n = int(dur * SR)
    body = sine_sweep(f0, f1, n, 5.0) * np.exp(-tv(n) / (dur * 0.35))
    c = filt(noise(n), "high", 1800) * np.exp(-tv(n) / 0.004) * click
    return body + c


def pluck(f, dur, bright=0.5):
    """Karplus-Strong"""
    n = int(dur * SR)
    p = int(SR / f)
    buf = rng.uniform(-1, 1, p)
    out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = 0.5 * (buf[i % p] + buf[(i + 1) % p]) * (0.992 + 0.006 * bright)
    return filt(out, "low", 900 + 2500 * bright)


def load_bundled(name):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", os.path.join(BUNDLED, name), "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
        capture_output=True,
        check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(np.float64)


def fade(x, fin, fout):
    n = len(x)
    e = np.ones(n)
    a = int(fin * SR)
    b = int(fout * SR)
    if a > 0:
        e[:a] = np.linspace(0, 1, a)
    if b > 0:
        e[n - b:] *= np.linspace(1, 0, b)
    return x * (e[:, None] if x.ndim == 2 else e)


# ------------------------------------------------------- picture schedules
BEAM_SLEWS = [(11.85, 0.32), (13.05, 0.32), (14.25, 0.32), (17.95, 0.3), (18.95, 0.46), (19.95, 0.3), (20.8, 0.2)]
WHIPS = [(22.15, 0.28), (23.95, 0.26), (25.42, 0.24), (26.34, 0.12), (26.52, 0.12), (26.68, 0.1), (26.84, 0.1)]
MONTAGE_FLASH = [21.3, 23.32, 24.98]
RAPID_FLASH = [26.18, 26.4, 26.58, 26.74]
LATE = [22.43, 24.21, 25.66]
BURSTS = [(29.55, 30.35, 0.55), (31.05, 31.45, 0.5), (32.75, 33.15, 0.55), (33.75, 34.12, 0.55), (34.8, 35.15, 0.5), (36.05, 36.7, 1.6)]
SCAN_T0, SCAN_DWELL = 30.45, 0.54
CALLOUTS = [32.0, 32.5, 33.0, 33.6, 34.6]

T = tv(N)
IR_BIG = reverb_ir(3.4, 5200)
IR_MID = reverb_ir(1.6, 7000)
IR_ROOM = reverb_ir(0.6, 8000, 0.006)

# ================================================================== SCORE
score = np.zeros((N, 2))

# 1. Sub drone — D1 + A1, a floor under the whole story; swells into the miss
drone = 0.55 * np.sin(2 * np.pi * 36.71 * T) + 0.38 * np.sin(2 * np.pi * 55.0 * T + 0.4) + 0.12 * np.sin(2 * np.pi * 73.42 * T + 1.1)
drone *= curve(T, [(0, 0), (2.2, 0.5), (10, 0.55), (16.8, 0.62), (21, 0.7), (26.9, 0.95), (27.3, 0.45), (30.2, 0.5), (36.9, 0.75), (37.15, 0.95), (39.2, 0.6), (40, 0)])
score += st(drone) * 0.34

# 2. Dark pad — D minor (D2 A2 F3), + C3 when the search starts, filtered, reverberant
def pad_voice(f, det=0.0055):
    return (saw(f * (1 - det), N, 0.0) + saw(f, N, 1.3) + saw(f * (1 + det), N, 2.1)) / 3.0

pad = pad_voice(73.42) * 0.5 + pad_voice(110.0) * 0.42 + pad_voice(174.61) * 0.3
pad += pad_voice(130.81) * 0.26 * curve(T, [(0, 0), (10.4, 0), (11.4, 1), (27.0, 1), (27.4, 0)])
pad = tv_lowpass(pad, lambda t: 420 + 160 * np.sin(2 * np.pi * t / 9.0) + (900 if 21.0 <= t < 27.0 else 0) * ((t - 21.0) / 6.0 if 21.0 <= t < 27.0 else 0))
pad *= curve(T, [(0, 0), (0.6, 0), (4.5, 0.8), (16.8, 0.85), (17.4, 0.35), (20.8, 0.35), (21.2, 0.8), (26.9, 1.0), (27.05, 0.0), (40, 0)])
score += reverb(st(pad, -0.1) * 0.5 + st(pad * 0.9, 0.12) * 0.5, IR_BIG, 0.45) * 0.2

# 3. Night ambience — distant rumble + wind; falls away with the world (S6)
amb = brown(N) * 0.8
amb = filt(amb, "low", 260)
wind = filt(noise(N), "band", (260, 1400), 2) * (0.5 + 0.5 * np.sin(2 * np.pi * T / 7.3) ** 2)
hum = 0.06 * (np.sin(2 * np.pi * 50 * T) + 0.4 * np.sin(2 * np.pi * 100 * T))
ambience = (amb * 0.5 + wind * 0.05 + hum) * curve(T, [(0, 0), (1.4, 1), (6.6, 1), (6.7, 0.35), (8.9, 0.35), (9.0, 1), (27.4, 1), (29.2, 0), (40, 0)])
score += st(ambience) * 0.55

# 4. Heartbeat — starts on the room-10 flash, accelerates through the montage
beats = []
t = 16.95
while t < 26.95:
    bpm = 64 if t < 21.0 else 76 + (150 - 76) * ((t - 21.0) / 6.0) ** 1.4
    beats.append((t, bpm))
    t += 60.0 / bpm
hb = np.zeros((N, 2))
for (bt, bpm) in beats:
    lub = kick(62, 44, 0.32, 0.12)
    add(hb, lub, bt, 1.0)
    if bpm < 104:
        add(hb, kick(56, 42, 0.26, 0.08), bt + 0.27, 0.62)
score += reverb(hb, IR_MID, 0.18) * 0.6

# 5. The sting — room 10 flashes while the guard watches room four
n = int(3.2 * SR)
cl = (saw(146.83, n) + saw(155.56, n, 0.7) + saw(220.0, n, 1.9) + 0.6 * saw(311.13, n, 2.4)) / 3.6
cl = filt(cl, "low", 1900) * (1 - np.exp(-tv(n) / 0.03)) * np.exp(-tv(n) / 1.1)
ring = (np.sin(2 * np.pi * 1760 * tv(n)) + 0.6 * np.sin(2 * np.pi * 2489 * tv(n))) * np.exp(-tv(n) / 1.0) * 0.25
add(score, reverb(st(cl + ring), IR_BIG, 0.5), 16.85, 0.34)

# 6. The hollow after the miss — a thin tremolo tone
n = int(3.4 * SR)
hollow = np.sin(2 * np.pi * 440 * tv(n)) * (0.6 + 0.4 * np.sin(2 * np.pi * 5.2 * tv(n)))
hollow = fade(hollow * 0.08, 0.9, 1.0)
add(score, reverb(st(hollow), IR_BIG, 0.6), 17.5, 1.0)

# 7. Montage hits on each flash
for ft in MONTAGE_FLASH:
    add(score, reverb(st(kick(70, 38, 0.9, 0.3)), IR_BIG, 0.35), ft, 0.55)
for ft in RAPID_FLASH:
    add(score, st(kick(80, 45, 0.35, 0.3)), ft, 0.32)

# 8. The pull back — soft sub as the rooms start to move; the spectrum resolves on a cold chord
add(score, reverb(st(kick(48, 30, 2.2, 0.0)), IR_BIG, 0.4), 28.4, 0.55)
n = int((FREEZE - 30.1) * SR)
chord_f = [293.66, 440.0, 659.25, 880.0]
chord = np.zeros(n)
for i, f in enumerate(chord_f):
    chord += (np.sin(2 * np.pi * f * tv(n) + i) + np.sin(2 * np.pi * f * 1.003 * tv(n) + 2 * i)) * (0.5 / (i + 1.4))
chord *= (1 - np.exp(-tv(n) / 0.5))
add(score, reverb(st(chord * 0.11), IR_BIG, 0.55), 30.1, 1.0)
# shimmer while the rooms fly
n = int(2.2 * SR)
sh = filt(noise(n), "band", (5000, 11000), 2) * np.sin(np.pi * tv(n) / 2.2) ** 2 * 0.05
sh *= 0.5 + 0.5 * (np.sin(2 * np.pi * 13 * tv(n)) > 0)
add(score, reverb(st(sh), IR_MID, 0.5), 28.3, 1.0)

# 9. The receiver's rhythm — a muted pluck on every scan step
k = 0
while True:
    st_t = SCAN_T0 + k * SCAN_DWELL
    if st_t > 36.95:
        break
    f = 73.42 if k % 2 == 0 else 110.0
    add(score, st(pluck(f, 0.5, 0.35) * 0.5), st_t, 0.55)
    k += 1

# 10. Tension into the final burst, then the freeze
n = int(1.1 * SR)
swell = filt(noise(n), "band", (300, 3000), 2) * (tv(n) / (n / SR)) ** 2.5 * 0.12
swell += saw(146.83, n) * 0.05 * (tv(n) / (n / SR)) ** 2
add(score, reverb(st(swell), IR_MID, 0.3), 35.9, 1.0)
# freeze: everything above stops dead at FREEZE except the drone; a thin high ring holds the frozen frame
cut = int(FREEZE * SR)
drone_only = st(drone) * 0.34
score[cut:] = drone_only[cut:]
n = N - cut
ring2 = (np.sin(2 * np.pi * 1318.5 * tv(n)) + 0.3 * np.sin(2 * np.pi * 1975.5 * tv(n))) * np.exp(-tv(n) / 2.2) * 0.05
score[cut:] += reverb(st(ring2), IR_BIG, 0.6)
score = fade(score, 0.0, 0.9)

# ================================================================== SFX
sfx = np.zeros((N, 2))


def padto(x, n):
    return np.concatenate([x, np.zeros(n - len(x))]) if len(x) < n else x[:n]


def footstep(g=1.0):
    n = int(0.16 * SR)
    x = filt(noise(n), "band", (150, 2400), 2) * np.exp(-tv(n) / 0.03)
    x += padto(kick(95, 60, 0.12, 0.0), n) * 0.6
    return x * g


def latch():
    n = int(0.25 * SR)
    ping = np.sin(2 * np.pi * 2200 * tv(n)) * np.exp(-tv(n) / 0.02) * 0.5
    x = filt(noise(n), "high", 1500) * np.exp(-tv(n) / 0.006)
    thunk = padto(kick(140, 80, 0.2, 0.0), n) * 0.7
    return ping + x + thunk


def torch_click(g=1.0):
    n = int(0.08 * SR)
    a = filt(noise(n), "band", (2000, 7000), 2) * np.exp(-tv(n) / 0.0025)
    b = np.zeros(n)
    k = int(0.018 * SR)
    b[k:] = a[: n - k] * 0.7
    tick = np.sin(2 * np.pi * 3100 * tv(n)) * np.exp(-tv(n) / 0.004) * 0.4
    return (a + b + tick) * g


def servo(dur, f0=140, f1=190, g=1.0):
    n = int(dur * SR)
    u = tv(n) / dur
    f = f0 + (f1 - f0) * np.sin(np.pi * u)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = signal.sawtooth(ph) * 0.5 + filt(noise(n), "band", (400, 2500), 2) * 0.3
    x = filt(x, "band", (120, 2600), 2)
    return x * np.sin(np.pi * u) ** 0.6 * g


def whip(dur, g=1.0):
    n = int(max(0.2, dur + 0.12) * SR)
    u = np.clip(tv(n) / dur, 0, 1)
    x = noise(n)
    x = tv_lowpass(x, lambda t: 500 + 4500 * np.sin(np.pi * min(1.0, t / dur)))
    return x * np.sin(np.pi * u) ** 1.2 * g


def rf_burst(dur, g=1.0):
    n = int((dur + 0.12) * SR)
    t = tv(n)
    mod = signal.square(2 * np.pi * 57 * t) * 0.5 + 0.5
    car = np.sin(2 * np.pi * (880 + 260 * mod) * t)
    crackle = filt(noise(n), "band", (1800, 6000), 2) * (rng.uniform(0, 1, n) > 0.985)
    env = np.clip(t / 0.02, 0, 1) * np.clip((dur - t) / 0.05 + 1, 0, 1)
    x = filt(car * 0.6 + crackle * 0.9 + filt(noise(n), "band", (700, 2200), 2) * 0.25, "band", (300, 7000), 2)
    return x * env * g


# 2A: footsteps to the side door, latch
for i, ft in enumerate([5.14, 5.5, 5.86, 6.2]):
    add(sfx, footstep(0.35 + 0.05 * i), ft, 1.0, 0.25)
add(sfx, reverb(st(latch()), IR_ROOM, 0.3), 6.05, 0.4, 0.3)
# 2B: the torch clicks on / off inside Room 07
add(sfx, reverb(st(torch_click()), IR_ROOM, 0.35), 8.55, 0.55, -0.05)
add(sfx, reverb(st(torch_click(0.6)), IR_ROOM, 0.35), 9.45, 0.45, -0.05)
# S3: the searchlight strikes — relay clunk + arc crackle, then a low mains hum while it burns
n = int(0.9 * SR)
clunk = padto(kick(90, 50, 0.4, 0.4), n) * 0.9 + filt(noise(n), "band", (300, 2200), 2) * np.exp(-tv(n) / 0.05) * 0.5
arc = filt(noise(n), "high", 900) * np.exp(-tv(n) / 0.18) * (rng.uniform(0, 1, n) > 0.6) * 0.35
add(sfx, reverb(st(clunk + arc), IR_MID, 0.25), 10.55, 0.55)
n = int((28.4 - 10.8) * SR)
buzz = (np.sin(2 * np.pi * 100 * tv(n)) + 0.5 * np.sin(2 * np.pi * 200 * tv(n)) + 0.25 * np.sin(2 * np.pi * 300 * tv(n)))
buzz *= 0.85 + 0.15 * np.sin(2 * np.pi * 0.7 * tv(n))
add(sfx, fade(st(buzz * 0.012, -0.35), 0.3, 1.2), 10.8, 1.0)
for (s, d) in BEAM_SLEWS:
    add(sfx, servo(d + 0.1, g=0.16), s - 0.02, 1.0, -0.3)
# S4: the torch in room 10 — distant, wet
add(sfx, reverb(st(filt(torch_click(), "low", 3500)), IR_MID, 0.6), 16.85, 0.28, 0.35)
add(sfx, reverb(st(latch()), IR_MID, 0.4), 19.52, 0.22, 0.45)
for i, ft in enumerate([19.95, 20.3, 20.65]):
    add(sfx, footstep(0.14), ft, 1.0, 0.55)
# S5: montage — flashes, whips, too-late thuds
for ft in MONTAGE_FLASH:
    add(sfx, reverb(st(torch_click(1.0)), IR_MID, 0.3), ft, 0.4)
    n = int(0.12 * SR)
    add(sfx, st(filt(noise(n), "high", 4500) * np.exp(-tv(n) / 0.03) * 0.25), ft + 0.01, 1.0)
for ft in RAPID_FLASH:
    add(sfx, st(torch_click(0.8)), ft, 0.35)
for (s, d) in WHIPS:
    add(sfx, st(whip(d, 0.2)), s - 0.04, 1.0, -0.2)
for lt in LATE:
    add(sfx, reverb(st(kick(70, 40, 0.3, 0.05)), IR_MID, 0.25), lt, 0.35)
# riser under the montage — its cut lands on the pull-back (27.0)
riser = load_bundled("riser.mp3")[int(0.8 * SR): int(4.15 * SR)]
add(sfx, fade(riser, 0.4, 0.02), 27.0 - len(riser) / SR, 0.11)
# the crane: cinematic whoosh peaking as the camera rises; the glitch as the rooms turn digital
add(sfx, load_bundled("whoosh-cinematic.mp3"), 27.8 - 2.5, 0.18)
add(sfx, fade(load_bundled("glitch-1.mp3"), 0.05, 0.6), 28.55, 0.12)
# spectrum powers on
n = int(0.5 * SR)
power = sine_sweep(180, 820, n, 3.0) * np.sin(np.pi * tv(n) / 0.5) * 0.25
add(sfx, reverb(st(power), IR_MID, 0.4), 30.1, 0.5)
# receiver steps: soft digital ticks
k = 0
while SCAN_T0 + k * SCAN_DWELL <= 36.95:
    n = int(0.05 * SR)
    tick = (np.sin(2 * np.pi * 1500 * tv(n)) + 0.4 * np.sin(2 * np.pi * 3000 * tv(n))) * np.exp(-tv(n) / 0.008)
    add(sfx, st(tick * 0.1, -0.3), SCAN_T0 + k * SCAN_DWELL, 1.0)
    k += 1
# RF bursts (the transmissions)
for (a, b, g) in BURSTS:
    add(sfx, reverb(st(rf_burst(b - a, 0.16 * g)), IR_MID, 0.25), a, 1.0, 0.2)
# callout ticks
for ct in CALLOUTS:
    n = int(0.04 * SR)
    tk = filt(noise(n), "high", 3000) * np.exp(-tv(n) / 0.003) * 0.2 + np.sin(2 * np.pi * 2400 * tv(n)) * np.exp(-tv(n) / 0.006) * 0.08
    add(sfx, st(tk), ct, 1.0, -0.1)
# MISSED — a deep, short impact on the empty band (serious, not a cartoon stamp):
# only the attack of the bundled impact, under a synthesized sub-hit with a long room tail
impact = load_bundled("impact-bass-1.mp3")[: int(1.0 * SR)]
env = np.ones(len(impact))
env[int(0.18 * SR):] = np.exp(-tv(len(impact) - int(0.18 * SR)) / 0.22)
add(sfx, impact * env[:, None], 37.0, 0.2)
add(sfx, reverb(st(kick(72, 31, 1.4, 0.35)), IR_BIG, 0.4), 37.0, 0.55)
n = int(0.5 * SR)
add(sfx, reverb(st(filt(noise(n), "low", 700) * np.exp(-tv(n) / 0.09) * 0.35), IR_BIG, 0.5), 37.0, 1.0)
sfx = fade(sfx, 0.0, 0.8)


# ============================================================ normalise + write
def normalise(x, peak_db):
    p = np.max(np.abs(x))
    return x * (10 ** (peak_db / 20) / p) if p > 0 else x


def soft_limit(x, ceiling=0.95):
    return np.tanh(x / ceiling) * ceiling


score = soft_limit(normalise(score, -4.0))
sfx = soft_limit(normalise(sfx, -3.0))
os.makedirs(os.path.join(ASSETS, "score"), exist_ok=True)
os.makedirs(os.path.join(ASSETS, "sfx"), exist_ok=True)
sf.write(os.path.join(ASSETS, "score", "score.wav"), score.astype(np.float32), SR, subtype="PCM_24")
sf.write(os.path.join(ASSETS, "sfx", "sfx.wav"), sfx.astype(np.float32), SR, subtype="PCM_24")


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)


print("score  rms %.1f dB  peak %.1f dB" % (rms_db(score), 20 * np.log10(np.max(np.abs(score)))))
print("sfx    rms %.1f dB  peak %.1f dB" % (rms_db(sfx), 20 * np.log10(np.max(np.abs(sfx)))))
