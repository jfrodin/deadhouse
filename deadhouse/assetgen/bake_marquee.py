"""Bakes the inside of the Marquee: a dead cinema where the projector still runs."""
from __future__ import annotations

import math

import numpy as np
import pygame

from . import env
from . import palette as P
from .env import Layers, SpriteSet
from .font_data import GLYPHS
from .gfx import (BAYER4, blit_text, dither_rect, hexc, hline, line, mix, noise_tint, outline, poly, px, rect, shade,
                  surf, vgrad_dither, vline)

W, H = 480, 300
SCREEN = pygame.Rect(110, 18, 260, 74)


def film_frames(S: SpriteSet, rng) -> list[str]:
    """A few frames of an old film about Saint Agathe's, shown on the screen at runtime (emissive)."""
    keys = []
    w, h = SCREEN.w, SCREEN.h

    def grain(e, amt=0.12):
        arr = pygame.surfarray.pixels3d(e)
        n = rng.uniform(1 - amt, 1 + amt, size=arr.shape[:2])[..., None]
        arr[:] = np.clip(arr * n, 0, 255).astype(np.uint8)
        del arr

    base = (200, 205, 215, 255)
    dark = (40, 42, 48, 255)
    # 0: title card
    e = surf(w, h)
    e.fill(dark)
    rect(e, 20, 10, w - 40, h - 20, (70, 72, 80, 255))
    rect(e, 22, 12, w - 44, h - 24, dark)
    t = "SAINT AGATHE'S"
    blit_text(e, GLYPHS, t, (w - len(t) * 6) // 2, 24, base, gap=1)
    t = "A MODERN HOSPITAL  1931"
    blit_text(e, GLYPHS, t, (w - len(t) * 6) // 2, 40, (150, 152, 160, 255), gap=1)
    grain(e)
    keys.append(S.add("film_0", surf(1, 1), e))
    # 1: a long corridor (perspective)
    e = surf(w, h)
    e.fill((110, 112, 120, 255))
    poly(e, [(0, 0), (w, 0), (w // 2 + 20, h // 2 - 6), (w // 2 - 20, h // 2 - 6)], (150, 152, 160, 255))
    poly(e, [(0, h), (w, h), (w // 2 + 20, h // 2 + 6), (w // 2 - 20, h // 2 + 6)], (80, 82, 90, 255))
    rect(e, w // 2 - 20, h // 2 - 6, 40, 12, (230, 232, 240, 255))
    for k in range(1, 6):
        x = int(w // 2 - 20 - (w // 2 - 20) * (1 - k / 6) ** 1.5)
        line(e, x, 0, x, h, (60, 62, 70, 255))
        line(e, w - x, 0, w - x, h, (60, 62, 70, 255))
    grain(e)
    keys.append(S.add("film_1", surf(1, 1), e))
    # 2: a nurse in a doorway, back turned
    e = surf(w, h)
    e.fill((90, 92, 100, 255))
    rect(e, w // 2 - 30, 4, 60, h - 4, (190, 192, 200, 255))
    pygame.draw.ellipse(e, (30, 30, 36, 255), (w // 2 - 6, 14, 12, 14))
    poly(e, [(w // 2 - 10, 28), (w // 2 + 10, 28), (w // 2 + 16, h), (w // 2 - 16, h)], (225, 226, 232, 255))
    rect(e, w // 2 - 9, 10, 18, 5, (240, 240, 245, 255))  # cap
    grain(e)
    keys.append(S.add("film_2", surf(1, 1), e))
    # 3: rows of beds, a figure sitting up
    e = surf(w, h)
    e.fill((70, 72, 80, 255))
    for k in range(6):
        x = 14 + k * 42
        rect(e, x, 40, 34, 18, (200, 202, 210, 255))
        rect(e, x, 36, 8, 8, (220, 222, 230, 255))
    pygame.draw.ellipse(e, (30, 30, 36, 255), (14 + 3 * 42 + 4, 22, 9, 10))
    rect(e, 14 + 3 * 42 + 4, 31, 9, 12, (230, 230, 236, 255))
    grain(e)
    keys.append(S.add("film_3", surf(1, 1), e))
    # 4: intertitle
    e = surf(w, h)
    e.fill(dark)
    for i, line_ in enumerate(("WHERE NO ONE", "IS EVER FORGOTTEN")):
        blit_text(e, GLYPHS, line_, (w - len(line_) * 6) // 2, 24 + i * 14, base, gap=1)
    grain(e)
    keys.append(S.add("film_4", surf(1, 1), e))
    # 5: a door with a number, closing
    e = surf(w, h)
    e.fill((100, 102, 110, 255))
    rect(e, w // 2 - 24, 6, 48, h - 6, (40, 40, 46, 255))
    rect(e, w // 2 - 24, 6, 20, h - 6, (170, 172, 180, 255))
    blit_text(e, GLYPHS, "7", w // 2 + 4, 24, base, gap=1)
    grain(e)
    keys.append(S.add("film_5", surf(1, 1), e))
    return keys


def bake(seed=31):
    rng = np.random.default_rng(seed)
    S = SpriteSet("marquee")
    L = Layers(W, H)
    rect(L.alb, 0, 0, W, H, hexc("120e12"))
    # proscenium + stage
    rect(L.alb, 70, 0, 340, 112, hexc("2a1e1a"))
    for xx in range(72, 410, 12):
        vline(L.alb, xx, 0, 111, P.DECO_GOLD if xx % 24 == 0 else hexc("3a2a22"))
    rect(L.alb, SCREEN.x - 4, SCREEN.y - 4, SCREEN.w + 8, SCREEN.h + 8, hexc("0e0c0e"))
    rect(L.alb, SCREEN.x, SCREEN.y, SCREEN.w, SCREEN.h, hexc("2c2c30"))
    L.anchor("screen", SCREEN.centerx, SCREEN.bottom)
    # velvet curtains, half drawn
    for side in (0, 1):
        x0 = SCREEN.x - 34 if side == 0 else SCREEN.right + 4
        for k in range(30):
            c = shade(P.VELVET, 0.8 + 0.4 * math.sin(k * 0.9) ** 2)
            vline(L.alb, x0 + k, 0, 104, c)
        rect(L.alb, x0, 0, 30, 6, P.DECO_GOLD)
    rect(L.alb, 70, 104, 340, 10, hexc("3a2820"))  # stage lip
    hline(L.alb, 70, 409, 104, shade(P.DECO_GOLD, 0.8))
    # auditorium floor: worn carpet with a pattern
    carpet = hexc("3a1c22")
    rect(L.alb, 0, 114, W, H - 114, carpet)
    for y in range(116, H, 6):
        for x in range((y // 6) % 2 * 6, W, 12):
            px(L.alb, x, y, shade(carpet, 1.3))
            px(L.alb, x + 1, y + 1, shade(carpet, 1.15))
    noise_tint(L.alb, pygame.Rect(0, 114, W, H - 114), rng, 0.08, scale=2)
    # seats: rows with a centre aisle and side aisles
    seat = hexc("5a1e26")
    seat_back = hexc("3a1418")
    for r, y in enumerate(range(134, 272, 17)):
        for x0, x1 in ((64, 222), (258, 418)):
            for x in range(x0, x1, 8):
                if rng.random() < 0.06:
                    rect(L.alb, x, y + 2, 7, 6, hexc("2a1e1a"))  # a broken seat
                    continue
                rect(L.alb, x, y, 7, 4, seat_back)
                rect(L.alb, x, y + 4, 7, 6, seat)
                hline(L.alb, x, x + 6, y + 4, shade(seat, 1.3))
            L.collider(x0, y + 2, x1 - x0, 8, "low")
    # walls
    rect(L.alb, 0, 114, 30, H - 114, hexc("1e1418"))
    rect(L.alb, W - 30, 114, 30, H - 114, hexc("1e1418"))
    for y in range(120, H, 30):
        rect(L.alb, 8, y, 14, 18, hexc("2e2024"))  # sconces (dead)
        rect(L.alb, W - 22, y, 14, 18, hexc("2e2024"))
    # side door (west) with an EXIT sign
    rect(L.alb, 20, 236, 12, 32, hexc("0a080a"))
    L.anchor("door", 44, 252)
    key, sw, sh = env.neon_text_sign(S, "exit", "EXIT", P.NEON_RED)
    env.add_sign_prop(L, key, 8, 222, sw, sh, "steady", P.L_RED, radius=50, intensity=0.5, light_dy=20)
    # projection booth (south wall)
    rect(L.alb, 190, H - 26, 100, 26, hexc("1a1416"))
    rect(L.alb, 230, H - 30, 20, 6, hexc("0a080a"))
    rect(L.emi, 236, H - 29, 8, 4, shade(P.PROJECTOR, 0.9))
    L.anchor("booth", 240, H - 34)
    # a box of .38 rounds left on a seat
    L.anchor("rounds", 300, 196)
    # colliders
    L.collider(0, 0, W, 116)
    L.collider(0, 0, 30, H)
    L.collider(W - 30, 0, 30, H)
    L.collider(0, H - 4, W, 4)
    L.collider(190, H - 26, 100, 26)
    # film frames for the screen
    L.meta["props"].append({"kind": "film", "x": SCREEN.x, "y": SCREEN.y, "frames": film_frames(S, rng)})
    return {"bg": L, "sprites": S, "size": (W, H)}
