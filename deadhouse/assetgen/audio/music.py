"""Original score: "Two A.M. at the Velour" (the Mercer Quartet, house band).

A 32-bar AABA ballad in D minor, 84 bpm, swung. Rendered three ways from the
same performance: inside the club, bleeding through the wall onto the street,
and through a cheap apartment radio.
"""
from __future__ import annotations

import os

import numpy as np

from . import synth as S

BPM = 84
BEAT = 60.0 / BPM
BAR = BEAT * 4
SWING = 2 / 3  # position of the off-beat eighth


def mfreq(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


CHORDS = {
    #          bass root, piano voicing (rootless), chord tones for walking bass (pitch classes)
    "Dm9": (38, [53, 57, 60, 64], [2, 5, 9, 0]),
    "Gm9": (43, [53, 57, 58, 62], [7, 10, 2, 5]),
    "Bbmaj7": (34, [57, 60, 62, 65], [10, 2, 5, 9]),
    "A7b9": (45, [55, 58, 61, 65], [9, 1, 4, 7]),
    "A7alt": (45, [55, 60, 61, 65], [9, 1, 5, 7]),
    "Fmaj7": (41, [57, 60, 64, 67], [5, 9, 0, 4]),
    "Em7b5": (40, [50, 55, 58, 64], [4, 7, 10, 2]),
}
A_PROG = ["Dm9", "Dm9", "Gm9", "Gm9", "Bbmaj7", "A7b9", "Dm9", "A7alt"]
B_PROG = ["Fmaj7", "Fmaj7", "Em7b5", "A7b9", "Dm9", "Bbmaj7", "Em7b5", "A7b9"]
FORM = A_PROG + A_PROG + B_PROG + A_PROG

# (beat offset within bar, length in beats, midi) per bar
A_MEL = [
    [(1.0, 0.6, 69), (1.67, 0.33, 72), (2.0, 2.0, 76)],
    [(0.0, 1.0, 74), (1.0, 0.6, 72), (1.67, 0.33, 69), (2.0, 1.8, 65)],
    [(0.67, 0.33, 70), (1.0, 0.6, 74), (1.67, 0.33, 77), (2.0, 1.6, 81)],
    [(0.0, 1.0, 79), (1.0, 0.6, 77), (1.67, 0.33, 74), (2.0, 2.0, 70)],
    [(0.0, 1.5, 69), (1.67, 0.33, 72), (2.0, 0.6, 74), (2.67, 0.33, 77), (3.0, 1.0, 76)],
    [(0.0, 1.0, 70), (1.0, 0.6, 73), (1.67, 0.33, 76), (2.0, 2.0, 79)],
    [(0.0, 1.5, 77), (1.67, 0.33, 76), (2.0, 2.0, 74)],
    [(1.0, 0.6, 73), (1.67, 0.33, 76), (2.0, 0.6, 77), (2.67, 0.33, 76), (3.0, 1.0, 73)],
]
A2_LAST = [
    [(0.0, 1.5, 77), (1.67, 0.33, 76), (2.0, 1.0, 74), (3.0, 0.6, 72), (3.67, 0.33, 69)],
    [(0.0, 3.0, 74), (3.0, 0.6, 72), (3.67, 0.33, 69)],
]
B_MEL = [  # clarinet
    [(0.0, 2.0, 64), (2.0, 0.6, 67), (2.67, 0.33, 69), (3.0, 1.0, 72)],
    [(0.0, 1.5, 71), (1.67, 0.33, 69), (2.0, 2.0, 67)],
    [(0.0, 1.0, 70), (1.0, 0.6, 67), (1.67, 0.33, 64), (2.0, 2.0, 62)],
    [(0.0, 1.0, 61), (1.0, 0.6, 64), (1.67, 0.33, 67), (2.0, 1.8, 70)],
    [(0.0, 2.5, 69), (2.67, 0.33, 65), (3.0, 1.0, 69)],
    [(0.0, 2.0, 74), (2.0, 0.6, 72), (2.67, 0.33, 69), (3.0, 1.0, 65)],
    [(0.0, 1.0, 67), (1.0, 0.6, 70), (1.67, 0.33, 74), (2.0, 1.0, 74), (3.0, 1.0, 70)],
    [(0.0, 2.0, 69), (2.0, 0.6, 67), (2.67, 0.33, 64), (3.0, 1.0, 61)],
]


def swing_pos(beat_pos: float) -> float:
    """Map straight eighth grid (x.5) to swung (x.67)."""
    whole = int(beat_pos)
    frac = beat_pos - whole
    if abs(frac - 0.5) < 1e-6:
        return whole + SWING
    return beat_pos


def walking_bass(rng):
    notes = []
    n = len(FORM)
    for bi, ch in enumerate(FORM):
        root, _, tones = CHORDS[ch]
        nxt_root = CHORDS[FORM[(bi + 1) % n]][0]
        # beat 1 root, 2-3 chord tones nearby, 4 chromatic approach to the next root
        prev = root
        line = [root]
        for b in (1, 2):
            pcs = tones[1:]
            cands = []
            for pc in pcs:
                for octv in range(2, 5):
                    m = 12 * octv + pc
                    if 28 <= m <= 52:
                        cands.append(m)
            cands.sort(key=lambda m: abs(m - prev) + rng.uniform(0, 2))
            pick = cands[0] if cands[0] != prev else cands[1]
            line.append(pick)
            prev = pick
        approach = nxt_root + (1 if rng.random() < 0.5 else -1)
        if approach > 52:
            approach -= 12
        line.append(approach)
        for b, m in enumerate(line):
            notes.append((bi * 4 + b, 0.95, m, 0.85 if b == 0 else 0.72))
    return notes


def render_performance(seed=84):
    rng = np.random.default_rng(seed)
    loop_len = len(FORM) * BAR
    tail = 4.0
    dur = loop_len + tail
    tracks = {k: np.zeros(int(dur * S.SR)) for k in ("bass", "piano", "vibes", "clar", "ride", "brush", "slap", "kick")}

    def hum():
        return rng.normal(0, 0.008)

    # bass
    for beat, length, m, vel in walking_bass(rng):
        t0 = beat * BEAT + hum()
        note = S.bass_note(mfreq(m), length * BEAT + 0.4, rng, vel)
        note *= np.minimum(1, np.linspace(6, 0, len(note)))  # release
        S.place(tracks["bass"], note, max(0, t0))
    # piano comping
    for bi, ch in enumerate(FORM):
        _, voicing, _ = CHORDS[ch]
        pattern = [(0.0, 0.35, 0.55), (1.0 + SWING, 1.8, 0.62)] if bi % 4 != 3 else [(1.0, 0.8, 0.5), (3.0, 0.9, 0.55)]
        if bi in (15, 31):
            pattern = [(0.0, 3.5, 0.6)]
        for pos, length, vel in pattern:
            t0 = bi * BAR + pos * BEAT + hum()
            for k, m in enumerate(voicing):
                n = S.piano_note(mfreq(m), length * BEAT + 0.8, rng, vel * (0.85 + 0.1 * rng.random()))
                n *= np.minimum(1, np.linspace(8, 0, len(n)))
                S.place(tracks["piano"], n, max(0, t0 + k * 0.006))
    # vibes melody (A sections), clarinet in the bridge
    sections = [("A", 0), ("A2", 8), ("B", 16), ("A", 24)]
    for name, start_bar in sections:
        if name == "B":
            mel = B_MEL
            for i, bar in enumerate(mel):
                for pos, length, m in bar:
                    t0 = (start_bar + i) * BAR + pos * BEAT + hum()
                    n = S.clarinet(mfreq(m), length * BEAT * 0.98, rng, 0.7)
                    S.place(tracks["clar"], n, max(0, t0))
            # vibes answer softly in the bridge
            for i in (1, 3, 5, 7):
                _, voicing, _ = CHORDS[B_PROG[i]]
                t0 = (start_bar + i) * BAR + 2.0 * BEAT
                for k, m in enumerate(voicing[1:]):
                    S.place(tracks["vibes"], S.vibraphone(mfreq(m + 12), 2.5, rng, 0.25), t0 + k * 0.09)
            continue
        mel = A_MEL[:6] + (A2_LAST if name == "A2" else A_MEL[6:])
        for i, bar in enumerate(mel):
            for pos, length, m in bar:
                t0 = (start_bar + i) * BAR + pos * BEAT + hum()
                vel = 0.75 + 0.15 * rng.random()
                S.place(tracks["vibes"], S.vibraphone(mfreq(m), max(1.2, length * BEAT + 1.0), rng, vel), max(0, t0))
    # drums: brushes + ride + feathered kick
    total_beats = len(FORM) * 4
    for b in range(total_beats):
        t0 = b * BEAT
        S.place(tracks["brush"], S.brush_swish(BEAT, rng, 0.5 + 0.2 * (b % 2)), t0)
        if b % 2 == 1:
            S.place(tracks["slap"], S.brush_slap(0.25, rng, 0.45), t0 + hum())
        S.place(tracks["kick"], S.kick_soft(0.4, rng, 0.35), t0)
        S.place(tracks["ride"], S.ride(1.2, rng, 0.5 if b % 2 == 0 else 0.42), t0 + hum())
        if b % 2 == 1:
            S.place(tracks["ride"], S.ride(1.0, rng, 0.3), t0 + SWING * BEAT + hum())
    # drum fill into the bridge and back
    for fb in (15, 31):
        for k in range(6):
            S.place(tracks["slap"], S.brush_slap(0.2, rng, 0.25 + k * 0.06), fb * BAR + (2 + k / 3) * BEAT)
    return tracks, loop_len, rng


def mixdown(tracks, rng):
    gains = {"bass": (0.62, 0.0), "piano": (0.30, -0.35), "vibes": (0.34, 0.35), "clar": (0.36, 0.15),
             "ride": (0.075, 0.45), "brush": (0.19, -0.25), "slap": (0.2, -0.15), "kick": (0.30, 0.0)}
    n = len(next(iter(tracks.values())))
    mix = np.zeros((n, 2))
    for k, x in tracks.items():
        g, p = gains[k]
        mix += S.pan(x * g, p)
    return mix


def wrap_loop(x: np.ndarray, loop_len: float) -> np.ndarray:
    n = int(loop_len * S.SR)
    out = x[:n].copy()
    tail = x[n:]
    out[: len(tail)] += tail
    return out


def build(out_dir: str) -> list[str]:
    tracks, loop_len, rng = render_performance()
    dry = mixdown(tracks, rng)
    club = S.reverb_ir(2.2, rng, decay=1.3, tone=6000)
    inside = S.add_reverb(dry, club, wet=0.22)
    inside = wrap_loop(inside, loop_len)
    inside = S.normalize(S.soft_clip(inside * 1.1, 1.2), 0.85)

    # through the wall: almost all highs gone, bass carries, a long wet street tail
    wall = S.lowpass(dry, 420, 4) + S.lowpass(dry, 1400, 2) * 0.06
    mono = wall.mean(axis=1)
    street = S.reverb_ir(3.0, rng, decay=2.2, tone=1800)
    outside = S.add_reverb(mono, street, wet=0.35, dry=0.85)
    outside = wrap_loop(outside, loop_len)
    outside = S.normalize(outside, 0.8)

    # apartment radio: telephone band, saturated, crackle
    radio = S.bandpass(inside.mean(axis=1), 380, 3000, 3)
    radio = np.tanh(radio * 3.0) * 0.5
    crackle = np.zeros(len(radio))
    idx = rng.integers(0, len(radio), size=int(len(radio) / S.SR * 40))
    crackle[idx] = rng.uniform(-0.6, 0.6, size=len(idx))
    crackle = S.highpass(crackle, 2000) + S.lowpass(rng.standard_normal(len(radio)), 6000) * 0.012
    radio = S.normalize(radio + crackle * 0.5, 0.75)

    d = os.path.join(out_dir, "audio", "music")
    return [S.write_audio(os.path.join(d, "velour_in"), inside),
            S.write_audio(os.path.join(d, "velour_out"), outside),
            S.write_audio(os.path.join(d, "velour_radio"), radio)]
