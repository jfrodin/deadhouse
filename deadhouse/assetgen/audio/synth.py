"""DSP toolkit for offline sound and music synthesis (numpy + scipy).

Everything is float64 mono or stereo arrays at SR. Generators take an explicit
numpy Generator so output is reproducible.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import wave

import numpy as np
from scipy import signal

SR = 44100


def t_axis(dur: float) -> np.ndarray:
    return np.arange(int(dur * SR)) / SR


def silence(dur: float) -> np.ndarray:
    return np.zeros(int(dur * SR))


# ----------------------------------------------------------------------------- oscillators
def sine(freq, dur, phase=0.0):
    t = t_axis(dur)
    if np.ndim(freq) == 0:
        return np.sin(2 * np.pi * freq * t + phase)
    ph = 2 * np.pi * np.cumsum(freq) / SR
    return np.sin(ph + phase)


def saw(freq, dur, harmonics=40):
    t = t_axis(dur)
    out = np.zeros_like(t)
    for k in range(1, harmonics + 1):
        if freq * k > SR / 2.2:
            break
        out += ((-1) ** (k + 1)) * np.sin(2 * np.pi * freq * k * t) / k
    return out * 0.6


def square_odd(freq, dur, harmonics=15, rolloff=1.0):
    t = t_axis(dur)
    out = np.zeros_like(t)
    for k in range(1, harmonics * 2, 2):
        if freq * k > SR / 2.2:
            break
        out += np.sin(2 * np.pi * freq * k * t) / (k ** rolloff)
    return out * 0.7


def noise(dur, rng, color="white"):
    n = int(dur * SR)
    w = rng.standard_normal(n)
    if color == "white":
        return w * 0.3
    if color == "pink":
        # Voss-McCartney-ish via filtering (Paul Kellet's economy filter)
        b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
        a = [1, -2.494956002, 2.017265875, -0.522189400]
        return signal.lfilter(b, a, w) * 0.9
    if color == "brown":
        x = np.cumsum(w)
        x = signal.lfilter([1, -1], [1, -0.995], x)
        return x / (np.max(np.abs(x)) + 1e-9) * 0.5
    raise ValueError(color)


# ----------------------------------------------------------------------------- envelopes
def adsr(dur, a=0.01, d=0.1, s=0.7, r=0.2, total=None):
    n = int((total if total is not None else dur + r) * SR)
    env = np.zeros(n)
    na, nd = int(a * SR), int(d * SR)
    ns = max(0, int(dur * SR) - na - nd)
    nr = int(r * SR)
    i = 0
    seg = np.linspace(0, 1, max(1, na), endpoint=False)
    env[i:i + len(seg)] = seg[: max(0, n - i)]
    i += na
    seg = np.linspace(1, s, max(1, nd), endpoint=False)
    env[i:i + len(seg)] = seg[: max(0, n - i)]
    i += nd
    env[i:i + ns] = s
    i += ns
    seg = np.linspace(s, 0, max(1, nr))
    end = min(n, i + len(seg))
    env[i:end] = seg[: end - i]
    return env


def exp_decay(dur, tau, attack=0.002):
    t = t_axis(dur)
    env = np.exp(-t / tau)
    na = int(attack * SR)
    if na > 0:
        env[:na] *= np.linspace(0, 1, na)
    return env


# ----------------------------------------------------------------------------- filters
def lowpass(x, fc, order=2):
    fc = min(fc, SR / 2.1)
    sos = signal.butter(order, fc, "low", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def highpass(x, fc, order=2):
    sos = signal.butter(order, fc, "high", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def bandpass(x, lo, hi, order=2):
    hi = min(hi, SR / 2.1)
    sos = signal.butter(order, [lo, hi], "band", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def resonator(x, freq, q=20.0):
    b, a = signal.iirpeak(freq, q, fs=SR)
    return signal.lfilter(b, a, x)


def sweep_bandpass(x, f0, f1, q=2.0, steps=24):
    """Band-pass with a moving centre frequency (piecewise, crossfaded)."""
    n = len(x)
    out = np.zeros(n)
    seg = n // steps + 1
    for i in range(steps):
        a, b = i * seg, min(n, (i + 1) * seg + 256)
        if a >= n:
            break
        f = f0 * (f1 / f0) ** (i / max(1, steps - 1))
        bw = f / q
        y = bandpass(x[max(0, a - 512):b], max(30, f - bw / 2), f + bw / 2)
        y = y[(a - max(0, a - 512)):]
        L = min(len(y), n - a)
        w = np.ones(L)
        ov = min(256, L)
        if i > 0:
            w[:ov] = np.linspace(0, 1, ov)
        if b < n:
            w[-ov:] = np.linspace(1, 0, ov)
        out[a:a + L] += y[:L] * w
    return out


# ----------------------------------------------------------------------------- instruments
def karplus(freq, dur, rng, damping=0.996, bright=0.5, pluck_pos=0.2):
    """Karplus-Strong plucked string."""
    n = int(dur * SR)
    p = max(2, int(round(SR / freq)))
    buf = rng.uniform(-1, 1, p)
    buf = lowpass(buf, 400 + bright * 6000, 1)
    k = max(1, int(p * pluck_pos))
    buf = buf - np.roll(buf, k) * 0.5  # pluck-position comb
    blocks = [buf]
    prev_last = 0.0
    total = p
    while total < n:
        prev = blocks[-1]
        shifted = np.concatenate([[prev_last], prev[:-1]])
        prev_last = prev[-1]
        blocks.append(damping * 0.5 * (prev + shifted))
        total += p
    return np.concatenate(blocks)[:n]


def fm_tone(freq, dur, ratio, index, index_decay, amp_tau, rng=None, attack=0.003):
    t = t_axis(dur)
    idx = index * np.exp(-t / index_decay)
    mod = np.sin(2 * np.pi * freq * ratio * t) * idx
    car = np.sin(2 * np.pi * freq * t + mod)
    env = exp_decay(dur, amp_tau, attack)
    return car * env


def piano_note(freq, dur, rng, vel=0.8):
    """Additive piano-ish tone with inharmonic partials and a hammer thump."""
    t = t_axis(dur)
    out = np.zeros_like(t)
    B = 0.0004
    for k in range(1, 12):
        fk = freq * k * np.sqrt(1 + B * k * k)
        if fk > SR / 2.3:
            break
        amp = (1.0 / k ** 1.2) * (0.6 + 0.4 * vel)
        tau = 1.8 / (1 + 0.45 * k) * (220 / max(110, freq)) ** 0.3
        out += amp * np.sin(2 * np.pi * fk * t + rng.uniform(0, 6.28)) * np.exp(-t / tau)
    # two strings slightly detuned for warmth
    out2 = np.sin(2 * np.pi * freq * 1.0012 * t) * np.exp(-t / 1.2) * 0.4
    hammer = lowpass(rng.standard_normal(len(t)), 2500) * np.exp(-t / 0.008) * 0.15
    env = np.minimum(1, t / 0.002)
    return (out + out2 + hammer) * env * vel


def vibraphone(freq, dur, rng, vel=0.8, motor=5.2, depth=0.35):
    t = t_axis(dur)
    a = fm_tone(freq, dur, 4.0, 1.2 * vel, 0.08, 1.6, attack=0.002)
    b = np.sin(2 * np.pi * freq * t) * exp_decay(dur, 2.4, 0.002)
    c = np.sin(2 * np.pi * freq * 3.98 * t) * exp_decay(dur, 0.25, 0.002) * 0.25
    trem = 1 - depth * (0.5 + 0.5 * np.sin(2 * np.pi * motor * t))
    return (a * 0.5 + b * 0.8 + c) * trem * vel


def clarinet(freq, dur, rng, vel=0.7):
    t = t_axis(dur)
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.0 * t) * np.minimum(1, t / 0.4)
    ph = 2 * np.pi * np.cumsum(freq * vib) / SR
    out = np.zeros_like(t)
    for k, amp in ((1, 1.0), (3, 0.45), (5, 0.25), (7, 0.12), (9, 0.06), (2, 0.05), (4, 0.03)):
        out += amp * np.sin(k * ph)
    breath = bandpass(rng.standard_normal(len(t)), 1500, 4000) * 0.015
    env = adsr(dur, 0.06, 0.1, 0.85, 0.12, total=dur)
    return lowpass(out + breath, 3200) * env * vel


def bass_note(freq, dur, rng, vel=0.9):
    s = karplus(freq, dur, rng, damping=0.9985, bright=0.25, pluck_pos=0.18)
    sub = np.sin(2 * np.pi * freq * t_axis(dur)) * exp_decay(dur, 0.6, 0.004) * 0.5
    thump = lowpass(rng.standard_normal(int(dur * SR)), 300) * exp_decay(dur, 0.02) * 0.25
    out = lowpass(s, 1600) + sub + thump
    return out * vel


def ride(dur, rng, vel=0.6):
    t = t_axis(dur)
    out = np.zeros_like(t)
    for f in (3150, 4280, 5370, 6840, 8100, 9330):
        out += np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) * rng.uniform(0.3, 1.0)
    out = out / 6
    n = highpass(rng.standard_normal(len(t)), 6000) * 0.3
    ping = np.sin(2 * np.pi * 620 * t) * exp_decay(dur, 0.15) * 0.15
    return (out * exp_decay(dur, 0.9, 0.001) + n * exp_decay(dur, 0.35, 0.001) + ping) * vel


def brush_swish(dur, rng, vel=0.5):
    n = rng.standard_normal(int(dur * SR))
    n = bandpass(n, 2500, 9000)
    t = t_axis(dur)
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5
    return n * env * vel * 0.25


def brush_slap(dur, rng, vel=0.6):
    t = t_axis(dur)
    n = bandpass(rng.standard_normal(len(t)), 1200, 7000) * exp_decay(dur, 0.06, 0.001)
    body = np.sin(2 * np.pi * 190 * t) * exp_decay(dur, 0.05) * 0.4
    return (n * 0.5 + body) * vel


def kick_soft(dur, rng, vel=0.5):
    t = t_axis(dur)
    f = 55 + 40 * np.exp(-t / 0.03)
    return sine(f, dur) * exp_decay(dur, 0.18, 0.002) * vel


# ----------------------------------------------------------------------------- space
def reverb_ir(dur, rng, decay=1.2, tone=5000, predelay=0.012, stereo=True):
    n = int(dur * SR)
    t = np.arange(n) / SR
    chans = []
    for _ in range(2 if stereo else 1):
        x = rng.standard_normal(n) * np.exp(-t * 6.9 / decay)
        x = lowpass(x, tone)
        pd = int(predelay * SR)
        x = np.concatenate([np.zeros(pd), x])[:n]
        # sparse early reflections
        for k in range(6):
            d = int(rng.uniform(0.005, 0.045) * SR)
            if d < n:
                x[d] += rng.uniform(0.2, 0.5) * (1 if rng.random() < 0.5 else -1)
        chans.append(x / np.sqrt(np.sum(x * x) + 1e-9))
    return np.stack(chans, axis=1) if stereo else chans[0]


def convolve_stereo(x: np.ndarray, ir: np.ndarray) -> np.ndarray:
    """x mono or stereo; ir stereo (n, 2). Returns stereo of len(x)+len(ir)-1."""
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    out = np.stack([signal.fftconvolve(x[:, c], ir[:, c]) for c in range(2)], axis=1)
    return out


def add_reverb(x, ir, wet=0.25, dry=1.0):
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    wetsig = convolve_stereo(x, ir)
    out = np.zeros_like(wetsig)
    out[: len(x)] += x * dry
    out += wetsig * wet
    return out


def pan(x: np.ndarray, p: float) -> np.ndarray:
    """p in [-1, 1]. Equal-power."""
    a = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1)


def place(dst: np.ndarray, src: np.ndarray, start: float, gain=1.0):
    i = int(start * SR)
    if i < 0:
        src = src[-i:]
        i = 0
    if i >= len(dst):
        return
    n = min(len(src), len(dst) - i)
    dst[i:i + n] += src[:n] * gain


def loop_crossfade(x: np.ndarray, fade: float = 1.5) -> np.ndarray:
    """Make a seamless loop: overlap the tail onto the head."""
    nf = int(fade * SR)
    head, body, tail = x[:nf], x[nf:-nf] if len(x) > 2 * nf else x, x[-nf:]
    w = np.linspace(0, 1, nf)
    if x.ndim == 2:
        w = w[:, None]
    mixed = tail * (1 - w) + head * w
    return np.concatenate([mixed, x[nf:-nf]])


def normalize(x, peak=0.89):
    m = np.max(np.abs(x)) + 1e-9
    return x / m * peak


def soft_clip(x, drive=1.0):
    return np.tanh(x * drive) / np.tanh(drive)


# ----------------------------------------------------------------------------- output
def write_wav(path: str, x: np.ndarray):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    data = np.clip(x, -1, 1)
    pcm = (data * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def write_audio(path_noext: str, x: np.ndarray, prefer_ogg: bool = True) -> str:
    """Write .ogg when ffmpeg is available (much smaller), else .wav. Returns the file path."""
    wav = path_noext + ".wav"
    write_wav(wav, x)
    ff = shutil.which("ffmpeg")
    if prefer_ogg and ff:
        ogg = path_noext + ".ogg"
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", wav, "-c:a", "libvorbis", "-q:a", "5",
                        "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:a", "+bitexact", ogg], check=True)
        os.remove(wav)
        return ogg
    return wav
