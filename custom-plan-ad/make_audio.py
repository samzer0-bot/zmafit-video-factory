"""Generate an ORIGINAL royalty-free soundtrack (120 BPM sporty beat + synced SFX) -> audio.mp3

Everything is synthesised from scratch with numpy (no samples, no third-party music).
Timings match src/config.ts (30 fps; 1 beat = 15 frames).
Usage: python3 make_audio.py
"""
import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 44100
DUR = 25.0
BPM = 120
BEAT = 60 / BPM
N = int(SR * DUR)
rng = np.random.default_rng(7)
mix = np.zeros((N, 2))


def f2s(frame):  # video frame -> seconds
    return frame / 30


def add(sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= N:
        return
    sig = sig[: N - i] * gain
    mix[i : i + len(sig), 0] += sig * (1 - pan) ** 0.5 if pan > 0 else sig
    mix[i : i + len(sig), 1] += sig * (1 + pan) ** 0.5 if pan < 0 else sig


def env(n, decay):
    return np.exp(-np.arange(n) / (SR * decay))


def lowpass(x, cutoff):
    """one-pole low-pass; cutoff can be scalar or per-sample array"""
    cutoff = np.broadcast_to(np.asarray(cutoff, dtype=float), x.shape)
    a = 1 - np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for k in range(len(x)):
        acc += a[k] * (x[k] - acc)
        y[k] = acc
    return y


def highpass(x, cutoff):
    return x - lowpass(x, cutoff)


# ---------- instruments ----------
def kick():
    n = int(0.4 * SR)
    t = np.arange(n) / SR
    freq = 45 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(freq) / SR
    click = rng.standard_normal(n) * env(n, 0.003) * 0.3
    return np.tanh((np.sin(ph) * env(n, 0.16) + click) * 1.8)


def clap():
    n = int(0.25 * SR)
    x = highpass(rng.standard_normal(n), 900)
    e = env(n, 0.07)
    for d in (0.0, 0.012, 0.024):  # triple-hit clap
        e[int(d * SR) :] += env(n - int(d * SR), 0.01) * 0.6
    return x * e * 0.5


HAT = highpass(rng.standard_normal(int(0.06 * SR)), 7000) * env(int(0.06 * SR), 0.012)


def bass(freq, length):
    n = int(length * SR)
    t = np.arange(n) / SR
    saw = sum(np.sin(2 * np.pi * freq * h * t) / h for h in range(1, 7))
    return np.tanh(lowpass(saw, 500) * 2.2) * env(n, 0.12) * 0.5


def stab(freqs, length=0.18):
    n = int(length * SR)
    t = np.arange(n) / SR
    s = sum(np.sign(np.sin(2 * np.pi * f * t)) * 0.5 + np.sin(2 * np.pi * f * 2.003 * t) * 0.3 for f in freqs)
    return lowpass(s, 2200) * env(n, 0.06) * 0.12


def riser(length, f0=300, f1=6000):
    n = int(length * SR)
    ramp = np.linspace(0, 1, n)
    noise = lowpass(rng.standard_normal(n), f0 + (f1 - f0) * ramp**2)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * np.cumsum(200 + 900 * ramp**2) / SR) * 0.25
    return (noise * 0.8 + tone) * ramp**1.5 * 0.6


def impact():
    n = int(1.2 * SR)
    t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(30 + 90 * np.exp(-t * 9)) / SR) * env(n, 0.35)
    crash = highpass(rng.standard_normal(n), 3000) * env(n, 0.25) * 0.35
    return np.tanh((boom + crash) * 1.6) * 0.9


def whoosh(length=0.35):
    n = int(length * SR)
    ramp = np.sin(np.linspace(0, np.pi, n))
    return lowpass(rng.standard_normal(n), 400 + 5000 * ramp) * ramp * 0.5


def tear():
    n = int(0.45 * SR)
    grit = (rng.random(n) < 0.08).astype(float) * rng.standard_normal(n)
    x = highpass(lowpass(rng.standard_normal(n) * 0.6 + grit * 3, 6000), 1200)
    am = 0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 38 * np.arange(n) / SR + rng.random() * 3))
    return x * am * env(n, 0.18) * 0.9


def blip(f0=880, f1=1320, length=0.12):
    n = int(length * SR)
    ramp = np.linspace(0, 1, n)
    return np.sin(2 * np.pi * np.cumsum(f0 + (f1 - f0) * ramp) / SR) * env(n, 0.04) * 0.35


def tap():
    n = int(0.05 * SR)
    return highpass(rng.standard_normal(n), 2500) * env(n, 0.006) * 0.6 + blip(1400, 1800, 0.05) * 0.5


def ding():
    n = int(1.0 * SR)
    t = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * f * t) * a for f, a in ((1318.5, 0.5), (1975.5, 0.35), (2637, 0.2))) * env(n, 0.3) * 0.5


def thud():
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(60 + 120 * np.exp(-t * 30)) / SR) * env(n, 0.08) * 0.8


# ---------- arrangement ----------
ROOTS = [55.0, 43.65, 65.41, 49.0]  # A1 F1 C2 G1  (Am - F - C - G)
CHORDS = [(220, 261.6, 329.6), (174.6, 220, 261.6), (261.6, 329.6, 392), (196, 246.9, 293.7)]

beats = int(DUR / BEAT)
for b in range(beats):
    t = b * BEAT
    bar = b // 4
    build = 14 <= b < 18  # 7–9 s : building scene -> drop drums, riser
    hook = b < 6  # 0–3 s : sparse, heavy
    if not build:
        add(kick(), t, 0.95)
    if not hook and not build and b % 2 == 1:
        add(clap(), t, 0.8)
    if not build:
        for h in (0.5,) if hook else (0, 0.25, 0.5, 0.75):
            add(HAT, t + h * BEAT, 0.22 if h % 0.5 else 0.32, pan=0.3)
    if not hook and not build:
        root = ROOTS[bar % 4]
        for e in (0, 0.5):
            add(bass(root, BEAT / 2), t + e * BEAT, 0.9)
        add(stab(CHORDS[bar % 4]), t + 0.5 * BEAT, 1.0, pan=-0.2)

# hook: impact on frame 0, tension, paper tear at frame 46
add(impact(), 0.0, 0.9)
add(riser(1.5, 200, 3000), f2s(0), 0.35)
add(tear(), f2s(30), 1.0)
add(impact(), f2s(32), 0.6)
add(whoosh(0.4), f2s(86), 0.7)

# questions: answer taps (START 8 + i*22 + 10)
for i in range(5):
    add(tap(), f2s(90 + 8 + i * 22 + 10), 0.9)
    add(whoosh(0.18), f2s(90 + 8 + i * 22), 0.25)

# building: riser into the green burst (frame 210+40)
add(riser(f2s(40), 300, 9000), f2s(210), 0.8)
add(impact(), f2s(250), 1.0)

# plan cards pop (270 + 12 + i*34) + habit checks
for i in range(5):
    add(blip(700 + i * 90, 1100 + i * 120), f2s(270 + 12 + i * 34), 0.9)
for k in range(3):
    add(blip(1500, 2000, 0.07), f2s(270 + 12 + 4 * 34 + 8 + k * 6), 0.6)

# pdf drop, price ding, CTA impact
add(whoosh(0.35), f2s(480), 0.6)
add(thud(), f2s(480 + 18), 1.0)
add(ding(), f2s(570 + 16), 0.9)
add(blip(900, 1300), f2s(570 + 20), 0.6)
add(impact(), f2s(660), 0.8)

# master: normalise, soft-clip, fade out last 0.6 s
mix = np.tanh(mix / np.max(np.abs(mix)) * 2.2) * 0.89
fade = np.ones(N)
fade[-int(0.6 * SR) :] = np.linspace(1, 0, int(0.6 * SR))
mix *= fade[:, None]

root = Path(__file__).parent
wav = root / 'audio.wav'
with wave.open(str(wav), 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype('<i2').tobytes())
subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(wav), '-b:a', '192k', str(root / 'audio.mp3')], check=True)
wav.unlink()
print('wrote', root / 'audio.mp3')
