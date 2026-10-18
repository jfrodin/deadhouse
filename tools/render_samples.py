"""Render listenable audio samples from the generated assets (for review without running the game).

    python tools/render_samples.py <out_dir>

Produces: street_mix.ogg (40 s on Lantern Row), tenement_mix.ogg (30 s: a fight in No. 14),
sfx_reel.ogg (every sound effect in sequence), and copies of the three music renders.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from deadhouse.assetgen.audio import synth as S  # noqa: E402

A = os.path.join(ROOT, "assets", "generated", "audio")
SR = 44100


def load(rel: str) -> np.ndarray:
    path = os.path.join(A, rel)
    if not os.path.exists(path):
        path = os.path.splitext(path)[0] + ".wav"
    tmp = os.path.join(tempfile.gettempdir(), "dh_sample.wav")
    if path.endswith(".ogg"):
        subprocess.run([shutil.which("ffmpeg"), "-y", "-loglevel", "error", "-i", path, "-ar", str(SR), tmp], check=True)
        path = tmp
    with wave.open(path) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").reshape(-1, w.getnchannels()) / 32768.0
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    return x.astype(np.float64)


def loop_to(x, n):
    reps = n // len(x) + 1
    return np.tile(x, (reps, 1))[:n]


def put(dst, src, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= len(dst):
        return
    m = min(len(src), len(dst) - i)
    l = np.cos((pan + 1) * np.pi / 4) * 1.41
    r = np.sin((pan + 1) * np.pi / 4) * 1.41
    dst[i:i + m, 0] += src[:m, 0] * gain * l
    dst[i:i + m, 1] += src[:m, 1] * gain * r


def street_mix():
    dur = 40.0
    n = int(dur * SR)
    out = np.zeros((n, 2))
    out += loop_to(load("amb/rain_street.ogg"), n) * 0.7
    out += loop_to(load("amb/city_far.ogg"), n) * 0.55
    band = loop_to(load("music/velour_out.ogg"), n)
    t = np.arange(n) / SR
    # walking toward the Velour's wall and past it
    env = 0.18 + 0.62 * np.exp(-((t - 20) / 8.0) ** 2)
    out += band * env[:, None] * 0.75
    steps = [load(f"sfx/step_wet_{i}.ogg") for i in range(1, 5)]
    k = 0
    for tt in np.arange(1.0, 34.0, 0.46):
        put(out, steps[k % 4], tt, 0.45, -0.1 if k % 2 else 0.1)
        k += 1
    put(out, load("sfx/el_train.ogg"), 26.0, 0.8)
    put(out, load("sfx/whisper.ogg"), 4.0, 0.5)
    put(out, load("sfx/match.ogg"), 13.0, 0.6, -0.3)
    return S.normalize(out, 0.9)


def tenement_mix():
    dur = 30.0
    n = int(dur * SR)
    out = np.zeros((n, 2))
    out += loop_to(load("amb/interior_tenement.ogg"), n) * 0.8
    out += loop_to(load("music/velour_radio.ogg"), n) * 0.22
    tension = loop_to(load("amb/tension.ogg"), n)
    t = np.arange(n) / SR
    out += tension * np.clip((t - 9.0) / 1.5, 0, 1)[:, None] * 0.45
    steps = [load(f"sfx/step_wood_{i}.ogg") for i in range(1, 5)]
    for k, tt in enumerate(np.arange(1.0, 7.5, 0.5)):
        put(out, steps[k % 4], tt, 0.5)
    put(out, load("sfx/throw.ogg"), 7.6, 0.6)
    put(out, load("sfx/glass.ogg"), 8.0, 0.8, -0.3)
    put(out, load("sfx/bulb_pop.ogg"), 8.05, 0.7, -0.3)
    put(out, load("sfx/alert_sting.ogg"), 9.2, 0.7)
    seq = [("swing_1", 11.0), ("hit_1", 11.08), ("swing_2", 11.5), ("hit_cut_1", 11.58), ("swing_3", 12.1),
           ("hit_2", 12.2), ("near_miss", 13.0), ("swing_heavy", 14.0), ("hit_heavy", 14.3), ("body_fall", 14.9),
           ("lantern_on", 17.0), ("flash", 18.2), ("takedown", 19.0), ("body_fall", 19.8), ("gunshot_enemy", 22.0),
           ("near_miss", 22.1), ("gunshot", 23.2), ("hit_bullet", 23.25), ("body_fall", 23.9), ("door", 26.0)]
    for name, tt in seq:
        put(out, load(f"sfx/{name}.ogg"), tt, 0.8)
    return S.normalize(out, 0.9)


def sfx_reel():
    names = sorted(os.path.splitext(f)[0] for f in os.listdir(os.path.join(A, "sfx")))
    parts = []
    for nm in names:
        if nm == "el_train":
            continue
        x = load(f"sfx/{nm}.ogg")
        parts += [x, np.zeros((int(0.35 * SR), 2))]
    return S.normalize(np.concatenate(parts), 0.9), names


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    S.write_audio(os.path.join(out_dir, "street_mix"), street_mix())
    S.write_audio(os.path.join(out_dir, "tenement_mix"), tenement_mix())
    reel, names = sfx_reel()
    S.write_audio(os.path.join(out_dir, "sfx_reel"), reel)
    with open(os.path.join(out_dir, "sfx_reel_order.txt"), "w", encoding="utf-8") as f:
        f.write("Order of sounds in sfx_reel.ogg (0.35 s gaps):\n" + "\n".join(n for n in names if n != "el_train"))
    for nm in ("velour_in", "velour_out", "velour_radio"):
        shutil.copy(os.path.join(A, "music", nm + ".ogg"), os.path.join(out_dir, f"music_{nm}.ogg"))
    shutil.copy(os.path.join(A, "sfx", "el_train.ogg"), os.path.join(out_dir, "el_train.ogg"))
    print("samples written to", out_dir)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "deliverables", "audio"))
