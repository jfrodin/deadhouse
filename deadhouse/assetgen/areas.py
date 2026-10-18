"""Writes baked area layer sets (bg/fg albedo, emissive, material + meta.json)."""
from __future__ import annotations

import json
import os

import pygame


def write_area(out_dir: str, area_id: str, baked: dict) -> list[str]:
    adir = os.path.join(out_dir, "areas", area_id)
    os.makedirs(adir, exist_ok=True)
    files = []
    meta = {"size": list(baked["size"]), "layers": {}}
    for layer in ("bg", "fg"):
        L = baked.get(layer)
        if L is None:
            continue
        for kind, s in (("alb", L.alb), ("emi", L.emi), ("mat", L.mat)):
            p = os.path.join(adir, f"{layer}_{kind}.png")
            pygame.image.save(s, p)
            files.append(p)
        meta["layers"][layer] = L.meta
    files += baked["sprites"].save(os.path.join(out_dir, "sprites"))
    for k, v in baked.get("extra_meta", {}).items():
        meta[k] = v
    p = os.path.join(adir, "meta.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    files.append(p)
    return files
