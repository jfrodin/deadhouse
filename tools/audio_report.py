"""Dev tool: spectrogram images + level statistics for generated audio (since a reviewer can't always listen).

    python tools/audio_report.py <file.ogg|wav> <out.png> [start_s] [dur_s]
"""
import os
import subprocess
import shutil
import sys
import tempfile
import wave

import numpy as np
import pygame
from scipy import signal


def load(path):
    if path.endswith(".ogg"):
        tmp = os.path.join(tempfile.gettempdir(), "dh_audio_report.wav")
        subprocess.run([shutil.which("ffmpeg"), "-y", "-loglevel", "error", "-i", path, tmp], check=True)
        path = tmp
    with wave.open(path) as w:
        n = w.getnframes()
        data = np.frombuffer(w.readframes(n), dtype="<i2").reshape(-1, w.getnchannels()) / 32768.0
        return data, w.getframerate()


def main():
    src, out = sys.argv[1], sys.argv[2]
    start = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
    dur = float(sys.argv[4]) if len(sys.argv) > 4 else 20.0
    x, sr = load(src)
    mono = x.mean(axis=1)
    peak = np.max(np.abs(x))
    rms = np.sqrt(np.mean(mono ** 2))
    clip = np.mean(np.abs(x) > 0.99)
    print(f"{os.path.basename(src)}: {len(x) / sr:.1f}s peak {20 * np.log10(peak + 1e-9):.1f} dBFS, "
          f"rms {20 * np.log10(rms + 1e-9):.1f} dBFS, clipped {clip * 100:.3f}%, "
          f"L/R corr {np.corrcoef(x[:, 0], x[:, 1])[0, 1]:.2f}")
    seg = mono[int(start * sr): int((start + dur) * sr)]
    f, t, Z = signal.stft(seg, sr, nperseg=4096, noverlap=3072)
    mag = 20 * np.log10(np.abs(Z) + 1e-7)
    # log-frequency image 40 Hz .. 12 kHz
    H, W = 360, min(1200, Z.shape[1])
    fl = np.geomspace(40, 12000, H)
    img = np.zeros((W, H))
    cols = np.linspace(0, Z.shape[1] - 1, W).astype(int)
    for i, fq in enumerate(fl):
        k = np.searchsorted(f, fq)
        img[:, H - 1 - i] = mag[min(k, len(f) - 1), cols]
    img = np.clip((img + 90) / 80, 0, 1)
    rgb = np.stack([img ** 0.8 * 255, img ** 1.6 * 220, img ** 3 * 160], axis=2).astype(np.uint8)
    pygame.init()
    s = pygame.surfarray.make_surface(rgb)
    # mark octaves (C notes) for reading the melody
    for c in (65.4, 130.8, 261.6, 523.3, 1046.5, 2093, 4186):
        y = H - 1 - int(np.searchsorted(fl, c))
        pygame.draw.line(s, (60, 90, 140), (0, y), (8, y))
    pygame.image.save(s, out)


if __name__ == "__main__":
    main()
