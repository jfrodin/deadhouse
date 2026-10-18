"""Sprite-sheet animation playback and runtime-drawn attachments (weapons, lantern, umbrella)."""
from __future__ import annotations

import math

import pygame

from .. import config as C


class Sheet:
    def __init__(self, image: pygame.Surface, meta: dict):
        self.image = image
        self.meta = meta
        self.fw, self.fh = meta["frame"]
        self.ax, self.ay = meta["anchor"]
        self.cols = meta["cols"]
        self.frames: list[pygame.Surface] = []
        n = len(meta["frames"])
        for k in range(n):
            r = pygame.Rect((k % self.cols) * self.fw, (k // self.cols) * self.fh, self.fw, self.fh)
            self.frames.append(image.subsurface(r))
        self.flipped: dict[int, pygame.Surface] = {}
        self.white: dict[tuple, pygame.Surface] = {}

    def frame_index(self, anim: str, view: str, t: float) -> tuple[int, bool]:
        """Return (frame index, mirrored)."""
        a = self.meta["anims"].get(anim) or self.meta["anims"]["idle"]
        flip = view == "W"
        v = "E" if flip else view
        idx = a["dirs"].get(v) or a["dirs"]["S"]
        n = len(idx)
        f = int(t * a["fps"])
        if a["loop"]:
            f %= n
        else:
            f = min(n - 1, f)
        return idx[f], flip

    def get(self, k: int, flip: bool) -> pygame.Surface:
        if not flip:
            return self.frames[k]
        s = self.flipped.get(k)
        if s is None:
            s = pygame.transform.flip(self.frames[k], True, False)
            self.flipped[k] = s
        return s

    def get_white(self, k: int, flip: bool) -> pygame.Surface:
        key = (k, flip)
        s = self.white.get(key)
        if s is None:
            s = self.get(k, flip).copy()
            s.fill((255, 245, 235, 0), special_flags=pygame.BLEND_RGB_MAX)
            self.white[key] = s
        return s

    def data(self, k: int, flip: bool) -> dict:
        d = self.meta["frames"][k]
        if not flip:
            return d
        hr = [self.fw - 1 - d["hr"][0], d["hr"][1]]
        hl = [self.fw - 1 - d["hl"][0], d["hl"][1]]
        head = [self.fw - 1 - d["head"][0], d["head"][1]]
        ang = 180 - d["ang"]
        return {"hr": hr, "hl": hl, "ang": ang, "behind": d["behind"], "head": head}


def _line_px(s, x0, y0, x1, y1, color):
    """Bresenham line, pixel exact."""
    x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    w, h = s.get_size()
    while True:
        if 0 <= x0 < w and 0 <= y0 < h:
            s.set_at((x0, y0), color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


WEAPON_STYLE = {
    "razor": [(0, 2, (58, 40, 30, 255)), (2, 6, (210, 215, 225, 255))],
    "tire_iron": [(0, 11, (78, 82, 90, 255)), (11, 12, (110, 115, 125, 255))],
    "knife": [(0, 2, (40, 30, 24, 255)), (2, 7, (200, 205, 215, 255))],
    "revolver": [(0, 2, (50, 40, 34, 255)), (2, 6, (60, 64, 72, 255))],
}


def draw_weapon(surf, kind: str, hx: float, hy: float, angle_deg: float):
    """Draw a weapon as pixel lines from the hand along `angle` (screen degrees, 0 = right, 90 = down)."""
    style = WEAPON_STYLE.get(kind)
    if not style:
        return
    a = math.radians(angle_deg)
    ca, sa = math.cos(a), math.sin(a)
    for d0, d1, col in style:
        _line_px(surf, hx + ca * d0, hy + sa * d0, hx + ca * d1, hy + sa * d1, col)
    if kind == "tire_iron":
        # lug wrench crossbar at the end
        ex, ey = hx + ca * 11, hy + sa * 11
        _line_px(surf, ex - sa * 2, ey + ca * 2, ex + sa * 2, ey - ca * 2, (110, 115, 125, 255))
    if kind == "revolver":
        surf.fill((50, 40, 34, 255), pygame.Rect(int(hx), int(hy), 2, 2))


def lantern_sprite() -> tuple[pygame.Surface, pygame.Surface]:
    alb = pygame.Surface((5, 6), pygame.SRCALPHA)
    emi = pygame.Surface((5, 6), pygame.SRCALPHA)
    alb.fill((40, 38, 36, 255), (0, 1, 5, 5))
    alb.fill((60, 58, 54, 255), (1, 0, 3, 1))
    alb.fill((200, 170, 110, 255), (1, 2, 3, 2))
    emi.fill((255, 220, 150, 255), (1, 2, 3, 2))
    return alb, emi


def umbrella_sprite(color=(30, 30, 36, 255)) -> pygame.Surface:
    s = pygame.Surface((20, 9), pygame.SRCALPHA)
    pygame.draw.ellipse(s, color, (0, 0, 20, 8))
    dark = tuple(max(0, c - 12) for c in color[:3]) + (255,)
    for x in (4, 10, 16):
        pygame.draw.line(s, dark, (10, 1), (x, 7))
    pygame.draw.ellipse(s, (14, 12, 18, 255), (0, 0, 20, 8), 1)
    s.fill((60, 60, 66, 255), (9, 8, 1, 1))
    return s
