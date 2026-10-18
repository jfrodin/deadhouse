"""Regenerate every game asset from source.

    python tools/build_assets.py            # everything
    python tools/build_assets.py art        # images only
    python tools/build_assets.py audio      # sound + music only
    python tools/build_assets.py row chars  # specific generators

Output goes to assets/generated/. A manifest with SHA-256 hashes is written so
tests can verify that generation is deterministic.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

from deadhouse.assetgen import registry  # noqa: E402

OUT = os.path.join(ROOT, "assets", "generated")


def sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def main(argv: list[str]) -> int:
    pygame.init()
    targets = argv or ["all"]
    jobs = registry.select(targets)
    manifest_path = os.path.join(OUT, "manifest.json")
    manifest = {}
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
    os.makedirs(OUT, exist_ok=True)
    for name, fn in jobs:
        t0 = time.time()
        files = fn(OUT)
        for p in files:
            rel = os.path.relpath(p, OUT).replace(os.sep, "/")
            manifest[rel] = sha(p)
        print(f"  {name:<18} {len(files):>4} files  {time.time() - t0:6.1f}s")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(manifest.items())), f, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
