"""Loads generated assets (images, sprite sheets, sounds) by key."""
from __future__ import annotations

import json
import os

import pygame

from .. import config as C


_REF = None


def canvas_format(s: pygame.Surface) -> pygame.Surface:
    """Convert to the 32-bit BGRA+alpha layout the canvases use (blits then skip per-pixel conversion)."""
    global _REF
    if _REF is None:
        _REF = pygame.Surface((1, 1), pygame.SRCALPHA, 32)
    if s.get_masks() == _REF.get_masks() and s.get_bitsize() == 32:
        return s
    return s.convert(_REF)


class Assets:
    def __init__(self, root: str = C.ASSET_DIR):
        self.root = root
        self._img: dict[str, pygame.Surface] = {}
        self._json: dict[str, dict] = {}
        self._sprite: dict[str, tuple[pygame.Surface, pygame.Surface | None]] = {}

    def path(self, rel: str) -> str:
        return os.path.join(self.root, rel.replace("/", os.sep))

    def image(self, rel: str) -> pygame.Surface:
        s = self._img.get(rel)
        if s is None:
            s = canvas_format(pygame.image.load(self.path(rel)))
            self._img[rel] = s
        return s

    def exists(self, rel: str) -> bool:
        return os.path.exists(self.path(rel))

    def json(self, rel: str) -> dict:
        d = self._json.get(rel)
        if d is None:
            with open(self.path(rel), encoding="utf-8") as f:
                d = json.load(f)
            self._json[rel] = d
        return d

    def sprite(self, key: str) -> tuple[pygame.Surface, pygame.Surface | None]:
        """A baked prop sprite: (albedo, emissive or None)."""
        sp = self._sprite.get(key)
        if sp is None:
            alb = self.image(f"sprites/{key}_alb.png")
            emi_rel = f"sprites/{key}_emi.png"
            emi = self.image(emi_rel) if self.exists(emi_rel) else None
            sp = (alb, emi)
            self._sprite[key] = sp
        return sp
