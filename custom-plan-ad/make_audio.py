"""Generate an ORIGINAL royalty-free soundtrack (120 BPM sporty beat + synced SFX) -> audio.mp3

Everything is synthesised from scratch with numpy (no samples, no third-party music).
Timings match src/config.ts (30 fps; 1 beat = 15 frames).
Usage: python3 make_audio.py          -> audio.mp3        (custom-plan ad)
       python3 make_audio.py guide    -> audio-guide.mp3  (free-guide ad)
"""
import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 44100
import json
import sys

MODE = sys.argv[1] if len(sys.argv) > 1 else 'plan'
TL_FILE = {'plan': 'src/timeline.json', 'guide': 'src/guide/timeline.json'}[MODE]
TL = json.loads((Path(__file__).parent / TL_FILE).read_text())
DUR = TL['total'] / TL['fps']
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

SC, BT = TL['scenes'], TL['beats']


def at(scene, frame=0):  # seconds of a frame inside a scene
    return f2s(SC[scene]['from'] + frame)


def beat_bed(sparse_until, drop=(None, None)):
    for b in range(int(DUR / BEAT)):
        t = b * BEAT
        bar = b // 4
        build = drop[0] is not None and drop[0] - 0.01 <= t < drop[1]
        hook = t < sparse_until
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


if MODE == 'guide':
    beat_bed(at('reveal'))
    add(impact(), 0.0, 0.9)
    add(riser(1.2, 200, 3000), 0.0, 0.3)
    for i in range(6):  # noise chips pop in
        add(blip(500 + i * 60, 700 + i * 80, 0.08), at('hook', max(0, -6 + i * 3)), 0.5)
    add(tear(), at('hook', BT['strikeAt']), 0.9)
    add(whoosh(0.4), at('reveal') - 0.15, 0.7)
    add(thud(), at('reveal', BT['bookLand']), 1.0)
    add(ding(), at('reveal', BT['bookLand'] + 2), 0.8)
    for i in range(4):
        add(whoosh(0.25), at('inside', BT['pageFirst'] + i * BT['pageGap']), 0.45)
        add(blip(700 + i * 90, 1100 + i * 120), at('inside', BT['pageFirst'] + i * BT['pageGap'] + 4), 0.8)
    add(impact(), at('cta'), 0.7)
    for k in range(len('you@email.com')):  # typing ticks
        add(tap(), at('cta', BT['typeStart']) + k * 1.6 / 30, 0.25)
    add(ding(), at('cta', BT['typeStart'] + 18), 0.8)
else:
    build_a, build_b = at('building'), at('twoPlans')
    beats = int(DUR / BEAT)
    for b in range(beats):
        t = b * BEAT
        bar = b // 4
        build = build_a - 0.01 <= t < build_b  # building scene -> drop drums, riser
        hook = t < at('questions')  # hook : sparse, heavy
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

    # hook: impact on frame 0, tension, paper tear
    add(impact(), 0.0, 0.9)
    add(riser(1.0, 200, 3000), 0.0, 0.35)
    add(tear(), at('hook', BT['tearAt'] - 2), 1.0)
    add(impact(), at('hook', BT['tearAt']), 0.6)
    add(whoosh(0.4), at('questions') - 0.15, 0.7)

    # questions: answer taps
    for i in range(5):
        add(tap(), at('questions', BT['qStart'] + i * BT['perQ'] + BT['tapAt']), 0.9)
        add(whoosh(0.18), at('questions', BT['qStart'] + i * BT['perQ']), 0.25)

    # building: riser into the green burst
    add(riser(f2s(BT['burstAt']), 300, 9000), at('building'), 0.8)
    add(impact(), at('building', BT['burstAt']), 1.0)

    # two plans: whoosh per column + ticks
    add(whoosh(0.3), at('twoPlans', BT['twoPlansA']), 0.5)
    add(whoosh(0.3), at('twoPlans', BT['twoPlansB']), 0.5)
    add(impact(), at('twoPlans', 24), 0.35)

    # plan cards pop + habit checks
    add(whoosh(0.35), at('plan'), 0.5)
    for i in range(5):
        add(blip(700 + i * 90, 1100 + i * 120), at('plan', BT['planFirst'] + i * BT['planGap']), 0.9)
    for k in range(3):
        add(blip(1500, 2000, 0.07), at('plan', BT['planFirst'] + 4 * BT['planGap'] + 8 + k * 6), 0.6)

    # pdf drop, price ding, CTA impact
    add(whoosh(0.35), at('pdf'), 0.6)
    add(thud(), at('pdf', BT['pdfDrop']), 1.0)
    add(ding(), at('price', BT['priceDing']), 0.9)
    add(blip(900, 1300), at('price', BT['priceDing'] + 4), 0.6)
    add(impact(), at('cta'), 0.8)

# master: normalise, soft-clip, fade out last 0.6 s
mix = np.tanh(mix / np.max(np.abs(mix)) * 2.2) * 0.89
fade = np.ones(N)
fade[-int(0.6 * SR) :] = np.linspace(1, 0, int(0.6 * SR))
mix *= fade[:, None]

root = Path(__file__).parent
OUT = root / ('audio.mp3' if MODE == 'plan' else 'audio-guide.mp3')
wav = root / 'audio.wav'
with wave.open(str(wav), 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype('<i2').tobytes())
subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(wav), '-b:a', '192k', str(OUT)], check=True)
wav.unlink()
print('wrote', OUT)
