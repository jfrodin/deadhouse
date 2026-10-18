"""Synthesized sound effects and ambience beds. Every sound is generated here from noise and oscillators."""
from __future__ import annotations

import os

import numpy as np

from . import synth as S
from .synth import SR


def _env_clip(x, fade_out=0.02):
    n = int(fade_out * SR)
    if n and len(x) > n:
        x[-n:] *= np.linspace(1, 0, n)
    return x


# ----------------------------------------------------------------------------- body / combat
def footstep_wet(rng, i):
    d = 0.22
    t = S.t_axis(d)
    thump = S.sine(70 + 15 * i, d) * S.exp_decay(d, 0.025) * 0.5
    heel = S.bandpass(rng.standard_normal(len(t)), 300, 1800) * S.exp_decay(d, 0.018) * 0.5
    splash = S.bandpass(rng.standard_normal(len(t)), 2500, 9000) * S.exp_decay(d, 0.05, 0.008) * 0.35
    return _env_clip(thump + heel + splash)


def footstep_wood(rng, i):
    d = 0.3
    t = S.t_axis(d)
    thump = S.sine(95 + 10 * i, d) * S.exp_decay(d, 0.04) * 0.6
    knock = S.resonator(rng.standard_normal(len(t)) * S.exp_decay(d, 0.01), 210 + 30 * i, 8) * 0.5
    creak = 0.0
    if i % 3 == 2:
        f = 380 + 60 * np.sin(np.linspace(0, 3, len(t)))
        creak = S.sine(f, d) * S.adsr(0.12, 0.04, 0.05, 0.4, 0.1, total=d) * 0.06
    return _env_clip(thump + knock + creak)


def footstep_concrete(rng, i):
    d = 0.2
    t = S.t_axis(d)
    thump = S.sine(80, d) * S.exp_decay(d, 0.02) * 0.4
    grit = S.bandpass(rng.standard_normal(len(t)), 1500, 6000) * S.exp_decay(d, 0.02) * 0.3
    return _env_clip(thump + grit)


def whoosh(rng, dur=0.2, f0=500, f1=2600, gain=0.7):
    n = rng.standard_normal(int(dur * SR))
    x = S.sweep_bandpass(n, f0, f1, q=1.6, steps=12)
    t = S.t_axis(dur)
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    return x * env * gain


def punch(rng, heavy=False):
    d = 0.35 if heavy else 0.22
    t = S.t_axis(d)
    f = (60 if heavy else 95) + 120 * np.exp(-t / 0.02)
    body = S.sine(f, d) * S.exp_decay(d, 0.07 if heavy else 0.045) * 0.9
    crack = S.bandpass(rng.standard_normal(len(t)), 800, 5000) * S.exp_decay(d, 0.012) * (0.7 if heavy else 0.5)
    slap = S.highpass(rng.standard_normal(len(t)), 3000) * S.exp_decay(d, 0.006) * 0.3
    crunch = 0
    if heavy:
        crunch = S.bandpass(rng.standard_normal(len(t)), 300, 1500) * S.exp_decay(d, 0.04, 0.005) * 0.5
    return _env_clip(S.soft_clip(body + crack + slap + crunch, 1.5))


def cut(rng):
    d = 0.3
    t = S.t_axis(d)
    slice_ = S.sweep_bandpass(rng.standard_normal(len(t)), 6000, 2500, q=3, steps=8) * S.exp_decay(d, 0.04, 0.002)
    wet = S.lowpass(rng.standard_normal(len(t)), 900) * S.exp_decay(d, 0.06, 0.01) * 0.6
    thud = S.sine(110, d) * S.exp_decay(d, 0.03) * 0.4
    return _env_clip(slice_ * 0.8 + wet + thud)


def bullet_hit(rng):
    d = 0.3
    t = S.t_axis(d)
    thud = S.sine(70 + 60 * np.exp(-t / 0.01), d) * S.exp_decay(d, 0.06) * 0.9
    crack = S.bandpass(rng.standard_normal(len(t)), 1000, 6000) * S.exp_decay(d, 0.01)
    return _env_clip(S.soft_clip(thud + crack * 0.6, 1.4))


def gunshot(rng, pitch=1.0, tail=1.8):
    d = 0.5 + tail
    t = S.t_axis(d)
    blast = rng.standard_normal(len(t)) * S.exp_decay(d, 0.03 * pitch, 0.0005)
    blast = S.lowpass(blast, 7000) * 1.2
    boom = S.sine((50 + 80 * np.exp(-t / 0.015)) * pitch, d) * S.exp_decay(d, 0.12) * 1.2
    crack = S.highpass(rng.standard_normal(len(t)), 3000) * S.exp_decay(d, 0.004) * 0.8
    dry = S.soft_clip(blast + boom + crack, 2.5)
    # city echo: slap-backs off the facades + long lowpassed tail
    ir = S.reverb_ir(tail, rng, decay=tail, tone=2200, predelay=0.03)
    wet = S.convolve_stereo(dry, ir)[: len(dry)]
    out = np.stack([dry, dry], axis=1) * 0.9 + wet * 0.55
    for delay, g in ((0.11, 0.3), (0.23, 0.18), (0.41, 0.1)):
        k = int(delay * SR)
        out[k:] += np.stack([dry[:-k] * g * 0.7, dry[:-k] * g], axis=1)
    return S.normalize(out, 0.95)


def gun_empty(rng):
    d = 0.12
    t = S.t_axis(d)
    click = S.resonator(rng.standard_normal(len(t)) * S.exp_decay(d, 0.003), 3200, 15) * 0.7
    return click


def reload(rng):
    out = np.zeros(int(1.1 * SR))
    for i, tt in enumerate((0.0, 0.25, 0.45, 0.62, 0.8, 1.0)):
        c = S.resonator(rng.standard_normal(int(0.06 * SR)) * S.exp_decay(0.06, 0.004), 2400 + 400 * (i % 2), 12)
        S.place(out, c * 0.5, tt)
    return out


def ricochet(rng):
    d = 0.5
    t = S.t_axis(d)
    f = 3800 * np.exp(-t / 0.25) + 900
    whine = S.sine(f, d) * S.exp_decay(d, 0.18, 0.002) * 0.25
    ping = S.resonator(rng.standard_normal(len(t)) * S.exp_decay(d, 0.003), 4200, 25) * 0.5
    return whine + ping


def glass_break(rng, scale=1.0):
    d = 1.0
    t = S.t_axis(d)
    burst = S.highpass(rng.standard_normal(len(t)), 2500) * S.exp_decay(d, 0.04 * scale, 0.001)
    out = burst * 0.6
    for _ in range(int(28 * scale)):
        f = rng.uniform(2500, 9000)
        st = rng.uniform(0, 0.35)
        dd = 0.25
        tink = S.sine(f, dd) * S.exp_decay(dd, rng.uniform(0.02, 0.06), 0.0005) * rng.uniform(0.05, 0.2)
        S.place(out, tink, st)
    thunk = S.sine(180, d) * S.exp_decay(d, 0.03) * 0.3
    return _env_clip(out + thunk)


def bulb_pop(rng):
    d = 0.9
    t = S.t_axis(d)
    pop = S.bandpass(rng.standard_normal(len(t)), 500, 4000) * S.exp_decay(d, 0.01, 0.0005)
    fizz = S.highpass(rng.standard_normal(len(t)), 4000) * S.exp_decay(d, 0.15, 0.02) * 0.2
    fizz *= (np.sin(2 * np.pi * 120 * t) > 0.6)
    return _env_clip(pop * 0.9 + fizz + glass_break(rng, 0.4)[: len(t)] * 0.6)


def match_strike(rng):
    d = 1.0
    t = S.t_axis(d)
    scratch = S.bandpass(rng.standard_normal(len(t)), 1500, 7000) * S.adsr(0.12, 0.01, 0.05, 0.7, 0.05, total=d) * 0.7
    flare = S.lowpass(rng.standard_normal(len(t)), 2500) * S.adsr(0.5, 0.12, 0.3, 0.2, 0.3, total=d) * 0.45
    return _env_clip(scratch + flare)


def metal_click(rng, f=2600, d=0.15, g=0.6):
    t = S.t_axis(d)
    return S.resonator(rng.standard_normal(len(t)) * S.exp_decay(d, 0.003), f, 14) * g


def lantern(rng, on=True):
    d = 0.6
    out = np.zeros(int(d * SR))
    S.place(out, metal_click(rng, 2200, 0.15, 0.6), 0.0)
    S.place(out, metal_click(rng, 3100, 0.12, 0.4), 0.06)
    if on:
        hiss = S.bandpass(rng.standard_normal(int(0.5 * SR)), 1200, 5000) * S.adsr(0.3, 0.05, 0.1, 0.3, 0.15, total=0.5) * 0.12
        S.place(out, hiss, 0.05)
    return out


def flash_burst(rng):
    d = 0.9
    t = S.t_axis(d)
    fwump = S.lowpass(rng.standard_normal(len(t)), 1500) * S.exp_decay(d, 0.06, 0.003) * 0.9
    ring = S.sine(2600, d) * S.exp_decay(d, 0.3, 0.005) * 0.08 + S.sine(3900, d) * S.exp_decay(d, 0.2) * 0.05
    return fwump + ring + metal_click(rng, 1800, d, 0.3)


def body_fall(rng):
    d = 0.6
    t = S.t_axis(d)
    thud = S.sine(55 + 40 * np.exp(-t / 0.02), d) * S.exp_decay(d, 0.09) * 1.0
    cloth = S.bandpass(rng.standard_normal(len(t)), 400, 3000) * S.exp_decay(d, 0.08, 0.01) * 0.4
    second = np.zeros(len(t))
    S.place(second, S.sine(70, 0.2) * S.exp_decay(0.2, 0.04) * 0.5, 0.14)
    return _env_clip(S.soft_clip(thud + cloth + second, 1.3))


def takedown(rng):
    d = 1.0
    t = S.t_axis(d)
    struggle = S.bandpass(rng.standard_normal(len(t)), 300, 2500) * (0.4 + 0.6 * np.abs(np.sin(2 * np.pi * 5.5 * t)))
    struggle *= S.adsr(0.6, 0.05, 0.2, 0.7, 0.3, total=d) * 0.35
    choke = S.sine(140 + 20 * np.sin(t * 30), d) * S.adsr(0.4, 0.1, 0.1, 0.4, 0.2, total=d) * 0.05
    return struggle + choke


def wood_strain(rng):
    d = 0.6
    t = S.t_axis(d)
    f = 220 + 140 * t / d
    creak = np.sin(2 * np.pi * np.cumsum(f) / SR) * (np.sin(2 * np.pi * 37 * t) > 0) * S.adsr(0.5, 0.1, 0.1, 0.7, 0.1, total=d)
    return S.bandpass(creak, 150, 2000) * 0.35


def wood_break(rng):
    d = 1.4
    t = S.t_axis(d)
    crack = S.bandpass(rng.standard_normal(len(t)), 600, 5000) * S.exp_decay(d, 0.03, 0.0008) * 1.2
    boom = S.sine(80 + 60 * np.exp(-t / 0.02), d) * S.exp_decay(d, 0.12) * 0.8
    out = crack + boom
    for _ in range(14):
        st = rng.uniform(0.08, 0.9)
        dd = 0.15
        k = S.resonator(rng.standard_normal(int(dd * SR)) * S.exp_decay(dd, 0.008), rng.uniform(300, 1200), 6)
        S.place(out, k * rng.uniform(0.15, 0.4), st)
    return _env_clip(S.soft_clip(out, 1.5))


def door(rng):
    d = 1.0
    t = S.t_axis(d)
    f = 300 + 200 * np.sin(np.linspace(0, 2.5, len(t)))
    creak = np.sin(2 * np.pi * np.cumsum(f) / SR) * (np.sin(2 * np.pi * 43 * t) > 0.2) * S.adsr(0.5, 0.15, 0.2, 0.5, 0.2, total=d)
    creak = S.bandpass(creak, 200, 2500) * 0.25
    latch = np.zeros(len(t))
    S.place(latch, metal_click(rng, 1900, 0.15, 0.5), 0.0)
    S.place(latch, S.sine(90, 0.2) * S.exp_decay(0.2, 0.04) * 0.5, 0.72)
    return creak + latch


def pickup(rng):
    d = 0.5
    out = np.zeros(int(d * SR))
    cloth = S.bandpass(rng.standard_normal(int(0.15 * SR)), 800, 4000) * S.exp_decay(0.15, 0.04) * 0.3
    S.place(out, cloth, 0)
    S.place(out, S.vibraphone(880, 0.45, rng, 0.25), 0.04)
    return out


def ui_tick(rng, f=1800, g=0.25):
    return metal_click(rng, f, 0.06, g)


def ui_pluck(rng):
    return S.karplus(392, 0.5, rng, 0.993, 0.4) * S.exp_decay(0.5, 0.2) * 0.4


def paper(rng, d=0.25):
    t = S.t_axis(d)
    return S.bandpass(rng.standard_normal(len(t)), 1500, 8000) * np.sin(np.pi * t / d) ** 2 * 0.25


def typewriter(rng):
    d = 0.05
    t = S.t_axis(d)
    return S.resonator(rng.standard_normal(len(t)) * S.exp_decay(d, 0.002), rng.uniform(1300, 1700), 10) * 0.25


def whisper(rng):
    d = 2.0
    t = S.t_axis(d)
    air = S.sweep_bandpass(rng.standard_normal(len(t)), 600, 3000, q=2.5, steps=16) * S.adsr(1.4, 0.6, 0.4, 0.5, 0.5, total=d)
    tone = (S.sine(220 * 2 ** (3 / 12), d) + S.sine(220 * 1.5, d) * 0.6) * S.adsr(1.2, 0.8, 0.3, 0.4, 0.6, total=d) * 0.04
    tone = tone[::-1]  # reversed swell
    return air * 0.3 + tone


def alert_sting(rng):
    d = 1.6
    t = S.t_axis(d)
    out = np.zeros(len(t))
    for f in (73.4, 77.8, 146.8, 155.6):  # D and Eb a minor second apart
        out += S.saw(f, d, 25) * 0.25
    out = S.lowpass(out, 900) * S.adsr(1.0, 0.04, 0.4, 0.5, 0.5, total=d)
    hit = S.sine(55, d) * S.exp_decay(d, 0.25) * 0.5
    return S.soft_clip(out + hit, 1.4) * 0.8


def player_down(rng):
    d = 3.0
    t = S.t_axis(d)
    drone = (S.saw(55, d, 20) * 0.2 + S.saw(55 * 1.007, d, 20) * 0.2)
    drone = S.lowpass(drone, 400) * S.adsr(2.5, 0.3, 0.5, 0.6, 0.5, total=d)
    beats = np.zeros(len(t))
    for st in (0.2, 0.45, 1.3, 1.6, 2.6):
        S.place(beats, S.sine(50, 0.2) * S.exp_decay(0.2, 0.05) * 0.8, st)
    return drone + beats


def dressing(rng):
    d = 1.3
    t = S.t_axis(d)
    tear = S.bandpass(rng.standard_normal(len(t)), 1200, 6000) * (np.abs(np.sin(2 * np.pi * 11 * t)) ** 4)
    tear *= S.adsr(0.5, 0.02, 0.1, 0.8, 0.1, total=d) * 0.35
    return tear


def climb(rng):
    out = np.zeros(int(1.2 * SR))
    for st in (0.0, 0.3, 0.6, 0.9):
        S.place(out, metal_click(rng, rng.uniform(900, 1500), 0.25, 0.4), st)
        S.place(out, S.sine(120, 0.15) * S.exp_decay(0.15, 0.03) * 0.3, st)
    return out


def near_miss(rng):
    return whoosh(rng, 0.25, 3000, 900, 0.5)


def throw(rng):
    return whoosh(rng, 0.22, 900, 2400, 0.5)


def heartbeat(rng):
    out = np.zeros(int(0.9 * SR))
    for st, g in ((0.0, 0.8), (0.18, 0.5)):
        S.place(out, S.sine(48, 0.2) * S.exp_decay(0.2, 0.05) * g, st)
    return out


# ----------------------------------------------------------------------------- ambience beds (loops)
def rain_street(rng, dur=40.0):
    n = int(dur * SR)
    hiss = S.lowpass(S.noise(dur, rng, "pink"), 7000) * 0.35
    hiss = S.highpass(hiss, 250)
    # individual drops: tiny filtered impulses everywhere
    drops = np.zeros(n)
    idx = rng.integers(0, n, size=int(dur * 900))
    drops[idx] = rng.uniform(-1, 1, size=len(idx))
    drops = S.bandpass(drops, 1800, 9000) * 0.5
    # gutter trickle: bandpassed noise wobbling
    t = np.arange(n) / SR
    trickle = S.bandpass(rng.standard_normal(n), 400, 1400) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.3 * t) * np.sin(2 * np.pi * 1.7 * t)) * 0.12
    # heavier drips on metal awnings
    pings = np.zeros(n)
    for _ in range(int(dur * 2.5)):
        st = rng.uniform(0, dur - 0.3)
        f = rng.uniform(1800, 4200)
        p = S.sine(f, 0.12) * S.exp_decay(0.12, 0.02, 0.0005) * rng.uniform(0.03, 0.09)
        S.place(pings, p, st)
    left = hiss + drops * 0.8 + trickle + pings
    right = S.lowpass(S.noise(dur, rng, "pink"), 7000) * 0.35
    right = S.highpass(right, 250) + np.roll(drops, 9000) * 0.8 + np.roll(trickle, 4000) + np.roll(pings, 20000)
    out = np.stack([left, right], axis=1)
    return S.normalize(S.loop_crossfade(out, 2.0), 0.55)


def city_far(rng, dur=60.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    rumble = S.lowpass(S.noise(dur, rng, "brown"), 160) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.05 * t))
    out = np.stack([rumble, np.roll(rumble, 5000)], axis=1) * 0.9
    # distant car horns and one far siren
    for _ in range(4):
        st = rng.uniform(2, dur - 4)
        f = rng.choice((311.0, 349.0, 392.0))
        d = rng.uniform(0.25, 0.7)
        h = (S.saw(f, d, 10) + S.saw(f * 1.26, d, 10)) * S.adsr(d - 0.1, 0.02, 0.05, 0.8, 0.1, total=d)
        h = S.lowpass(h, 1200) * 0.06
        S.place(out[:, 0 if rng.random() < 0.5 else 1], h, st)
    st = rng.uniform(10, dur - 12)
    sd = 9.0
    tt = S.t_axis(sd)
    f = 700 + 250 * np.sin(2 * np.pi * 0.4 * tt)
    siren = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / sd) ** 2 * 0.035
    siren = S.lowpass(siren, 1500)
    S.place(out[:, 0], siren * 0.7, st)
    S.place(out[:, 1], siren, st + 0.02)
    return S.normalize(S.loop_crossfade(out, 3.0), 0.5)


def interior_tenement(rng, dur=40.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    hum = (np.sin(2 * np.pi * 60 * t) * 0.3 + np.sin(2 * np.pi * 120 * t) * 0.15) * 0.05
    tone = S.lowpass(S.noise(dur, rng, "brown"), 120) * 0.25
    out = np.stack([hum + tone, hum + np.roll(tone, 3000)], axis=1)
    # pipes knocking, a drip, a cough far upstairs, rain on the roof (muffled)
    for _ in range(5):
        st = rng.uniform(1, dur - 2)
        for k in range(int(rng.integers(2, 5))):
            S.place(out[:, 1], S.resonator(rng.standard_normal(int(0.1 * SR)) * S.exp_decay(0.1, 0.005), 180, 6) * 0.35, st + k * 0.17)
    for i in range(int(dur / 2.3)):
        S.place(out[:, 0], S.sine(1400 - (i % 3) * 120, 0.08) * S.exp_decay(0.08, 0.012) * 0.08, i * 2.3 + 0.7)
    roof = S.lowpass(S.noise(dur, rng, "pink"), 900) * 0.18
    out[:, 0] += roof
    out[:, 1] += np.roll(roof, 7000)
    return S.normalize(S.loop_crossfade(out, 2.0), 0.45)


def interior_cinema(rng, dur=30.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    # projector: motor whir + shutter flutter at 24 fps
    whir = S.bandpass(rng.standard_normal(n), 200, 900) * 0.15
    flutter = S.bandpass(rng.standard_normal(n), 1500, 5000) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 24 * t))) * 0.05
    motor = np.sin(2 * np.pi * 96 * t) * 0.03
    big_room = S.lowpass(S.noise(dur, rng, "brown"), 90) * 0.35
    out = np.stack([whir + flutter + motor + big_room, whir * 0.8 + flutter * 0.6 + motor + np.roll(big_room, 4000)], axis=1)
    return S.normalize(S.loop_crossfade(out, 2.0), 0.45)


def alley_bed(rng, dur=40.0):
    rain = rain_street(rng, dur)
    t = np.arange(len(rain)) / SR
    drip = np.zeros(len(rain))
    for i in range(int(dur * 1.2)):
        st = rng.uniform(0, len(rain) / SR - 0.2)
        S.place(drip, S.sine(rng.uniform(900, 1600), 0.1) * S.exp_decay(0.1, 0.015) * 0.12, st)
    rain[:, 0] = S.lowpass(rain[:, 0], 5000) + drip
    rain[:, 1] = S.lowpass(rain[:, 1], 5000) + np.roll(drip, 30000)
    return S.normalize(rain, 0.5)


def roof_bed(rng, dur=40.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    wind = S.sweep_bandpass(S.noise(dur, rng, "pink"), 200, 600, q=1.5, steps=30) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * t))
    rain = rain_street(rng, dur) * 0.8
    windst = np.stack([wind, np.roll(wind, 8000)], axis=1) * 0.5
    city = city_far(rng, dur)
    m = min(len(rain), len(windst), len(city))
    out = rain[:m] + windst[:m] + city[:m] * 1.2
    return S.normalize(S.loop_crossfade(out, 2.0), 0.55)


def tension(rng, dur=24.0):
    """Combat bed: low divided strings on D and Eb, slow bowing swells, a pulse like a held breath."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for f, p in ((36.7, -0.3), (38.9, 0.3), (73.4, -0.1), (77.8, 0.2), (110.0, 0.0)):
        vib = 1 + 0.003 * np.sin(2 * np.pi * rng.uniform(4.5, 5.5) * t + rng.uniform(0, 6))
        ph = 2 * np.pi * np.cumsum(f * vib) / SR
        x = sum(np.sin(k * ph) / k for k in range(1, 14))
        bow = 0.6 + 0.4 * np.sin(2 * np.pi * (1 / 6.0) * t + rng.uniform(0, 6)) ** 2
        out += S.pan(S.lowpass(x * bow, 700) * 0.12, p)
    pulse = np.zeros(n)
    beat = 60 / 96
    k = 0.0
    while k < dur:
        S.place(pulse, S.sine(44, 0.3) * S.exp_decay(0.3, 0.08) * 0.6, k)
        k += beat
    out += np.stack([pulse, pulse], axis=1)
    return S.normalize(S.loop_crossfade(out, 2.0), 0.6)


def neon_buzz(rng, dur=4.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    b = sum(np.sin(2 * np.pi * 120 * k * t) / k for k in range(1, 8)) * 0.1
    b += S.highpass(rng.standard_normal(n), 5000) * 0.01
    return np.stack([b, b], axis=1)


def el_train(rng):
    """A train crossing the Elevated Line above the street, left to right (~9 s)."""
    d = 10.0
    n = int(d * SR)
    t = np.arange(n) / SR
    env = np.clip(np.sin(np.pi * t / d), 0, 1) ** 1.3
    rumble = S.lowpass(S.noise(d, rng, "brown"), 220) * 2.0
    rattle = S.bandpass(rng.standard_normal(n), 300, 2400) * 0.5
    clacks = np.zeros(n)
    k = 0.0
    while k < d:
        for off in (0.0, 0.11):
            st = k + off
            if st < d:
                c = S.resonator(rng.standard_normal(int(0.08 * SR)) * S.exp_decay(0.08, 0.006), rng.uniform(140, 260), 4)
                S.place(clacks, c * 0.9, st)
        k += 0.42
    screech = np.zeros(n)
    st = rng.uniform(3.5, 5.5)
    sd = 1.6
    tt = S.t_axis(sd)
    sc = (np.sin(2 * np.pi * 3100 * tt) + np.sin(2 * np.pi * 4170 * tt) * 0.6) * np.sin(np.pi * tt / sd) * 0.08
    S.place(screech, sc, st)
    mono = (rumble + rattle + clacks) * env + screech * env
    p = np.linspace(-0.9, 0.9, n)
    out = np.stack([mono * np.cos((p + 1) * np.pi / 4), mono * np.sin((p + 1) * np.pi / 4)], axis=1)
    return S.normalize(out, 0.85)


# ----------------------------------------------------------------------------- registry
def build(out_dir: str) -> list[str]:
    rng = np.random.default_rng(1931)
    d = os.path.join(out_dir, "audio", "sfx")
    a = os.path.join(out_dir, "audio", "amb")
    files = []

    def w(name, x, folder=d):
        if folder == d:
            x = S.normalize(x, 0.9)
        files.append(S.write_audio(os.path.join(folder, name), x))

    for i in range(4):
        w(f"step_wet_{i + 1}", footstep_wet(rng, i))
        w(f"step_wood_{i + 1}", footstep_wood(rng, i))
        w(f"step_concrete_{i + 1}", footstep_concrete(rng, i))
    for i in range(3):
        w(f"swing_{i + 1}", whoosh(rng, 0.18, 600 + 150 * i, 2800, 0.6))
        w(f"hit_{i + 1}", punch(rng))
        w(f"hit_cut_{i + 1}", cut(rng))
    w("swing_heavy", whoosh(rng, 0.34, 250, 1500, 0.9))
    w("hit_heavy", punch(rng, heavy=True))
    w("hit_bullet", bullet_hit(rng))
    w("gunshot", gunshot(rng, 1.0, 1.8))
    w("gunshot_enemy", gunshot(rng, 0.9, 1.8))
    w("gun_empty", gun_empty(rng))
    w("reload", reload(rng))
    w("ricochet", ricochet(rng))
    w("glass", glass_break(rng))
    w("bulb_pop", bulb_pop(rng))
    w("match", match_strike(rng))
    w("lantern_on", lantern(rng, True))
    w("lantern_off", lantern(rng, False))
    w("flash", flash_burst(rng))
    w("body_fall", body_fall(rng))
    w("takedown", takedown(rng))
    w("wood_strain", wood_strain(rng))
    w("wood_break", wood_break(rng))
    w("door", door(rng))
    w("pickup", pickup(rng))
    w("equip", metal_click(rng, 1500, 0.2, 0.5))
    w("ui_move", ui_tick(rng, 2000, 0.18))
    w("ui_next", ui_tick(rng, 1500, 0.2))
    w("ui_select", ui_pluck(rng))
    w("ui_open", paper(rng, 0.25))
    w("ui_close", paper(rng, 0.18))
    w("type", typewriter(rng))
    w("whisper", whisper(rng))
    w("alert_sting", alert_sting(rng))
    w("player_down", player_down(rng))
    w("dressing", dressing(rng))
    w("climb", climb(rng))
    w("near_miss", near_miss(rng))
    w("throw", throw(rng))
    w("heartbeat", heartbeat(rng))
    w("el_train", el_train(rng))

    w("rain_street", rain_street(rng), a)
    w("city_far", city_far(rng), a)
    w("interior_tenement", interior_tenement(rng), a)
    w("interior_cinema", interior_cinema(rng), a)
    w("alley", alley_bed(rng), a)
    w("roof", roof_bed(rng), a)
    w("neon_buzz", neon_buzz(rng), a)
    w("tension", tension(rng), a)
    return files
