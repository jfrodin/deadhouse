"""Build the Windows executable with PyInstaller and zip it.

    python tools/build_exe.py

Output: dist/Deadhouse/Deadhouse.exe and dist/Deadhouse-Prototype1-win64.zip
Assets must be generated first (tools/build_assets.py).
"""
from __future__ import annotations

import io
import os
import shutil
import struct
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


def make_icon(path: str):
    """Generate the app icon (a neon 'D' on black) and wrap the PNGs in an .ico container."""
    import pygame
    pygame.init()
    from deadhouse.assetgen.font_data import GLYPHS
    pngs = []
    for size in (16, 32, 48, 256):
        s = pygame.Surface((32, 32), pygame.SRCALPHA)
        s.fill((14, 10, 16, 255))
        g = GLYPHS["D"]
        for j, row in enumerate(g):
            for i, c in enumerate(row):
                if c == "#":
                    s.fill((255, 63, 174, 255), (9 + i * 3, 4 + j * 3, 3, 3))
        pygame.draw.rect(s, (196, 40, 52, 255), (6, 28, 20, 2))
        big = pygame.transform.scale(s, (size, size))
        buf = io.BytesIO()
        pygame.image.save(big, buf, "png")
        pngs.append((size, buf.getvalue()))
    with open(path, "wb") as f:
        f.write(struct.pack("<HHH", 0, 1, len(pngs)))
        offset = 6 + 16 * len(pngs)
        for size, data in pngs:
            f.write(struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset))
            offset += len(data)
        for _, data in pngs:
            f.write(data)


def main():
    build = os.path.join(ROOT, "build")
    os.makedirs(build, exist_ok=True)
    icon = os.path.join(build, "deadhouse.ico")
    make_icon(icon)
    sep = ";" if os.name == "nt" else ":"
    args = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
        "--name", "Deadhouse", "--icon", icon,
        "--distpath", os.path.join(ROOT, "dist"), "--workpath", os.path.join(build, "pyi"),
        "--specpath", build,
        "--add-data", f"{os.path.join(ROOT, 'assets', 'generated')}{sep}assets/generated",
        "--add-data", f"{os.path.join(ROOT, 'deadhouse', 'content', 'dialogue')}{sep}deadhouse/content/dialogue",
        "--collect-submodules", "glcontext", "--collect-submodules", "deadhouse.content",
        "--collect-submodules", "deadhouse.states",
        "--hidden-import", "glcontext.wgl",
        "--exclude-module", "scipy", "--exclude-module", "tkinter", "--exclude-module", "pytest",
        "--exclude-module", "deadhouse.assetgen.audio",
        os.path.join(ROOT, "Deadhouse.py"),
    ]
    print(" ".join(args))
    subprocess.run(args, check=True, cwd=ROOT)
    out = os.path.join(ROOT, "dist", "Deadhouse")
    # ship the readme for players
    for fn in ("PLAYING.txt",):
        src = os.path.join(ROOT, "docs", fn)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(out, fn))
    z = os.path.join(ROOT, "dist", "Deadhouse-Prototype1-win64.zip")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for dp, _, fns in os.walk(out):
            for fn in fns:
                p = os.path.join(dp, fn)
                zf.write(p, os.path.relpath(p, os.path.dirname(out)))
    print("built", out)
    print("zipped", z, f"{os.path.getsize(z) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
