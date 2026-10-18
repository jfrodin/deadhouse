"""Bakes No. 14, the Garnet Arms: a four-storey tenement drawn as a cutaway stack.

Going up the stairs = moving north. Each floor is a walkable band with its back
wall visible above it; dark slabs separate the floors; stair flights cut through.
"""
from __future__ import annotations

import numpy as np
import pygame

from . import env
from . import palette as P
from .env import Layers, SpriteSet
from .font_data import GLYPHS
from .gfx import (BAYER4, blit_text, dither_rect, hexc, hline, line, mix, noise_tint, outline, poly, px, rect, shade,
                  surf, vline)

W, H = 480, 700
X0, X1 = 48, 432

FLOORS = {  # name: (walk_y0, walk_y1, wall_y0) -- back wall face spans wall_y0..walk_y0
    "f0": (586, 664, 546),
    "f1": (436, 520, 396),
    "f2": (286, 370, 246),
    "f3": (100, 220, 52),
}
STAIRS = {  # rect x, y, w, h (walkable), direction of the rail side
    "s1": (362, 518, 52, 70),
    "s2": (64, 368, 52, 70),
    "s3": (362, 218, 52, 70),
}

WALLPAPER = [hexc("4f3a3a"), hexc("3e4a3c"), hexc("4a4252"), hexc("5a4632")]
FLOORBOARD = hexc("5a4030")
SLAB = hexc("17131a")


def wallpaper(L: Layers, rng, x, y, w, h, base):
    rect(L.alb, x, y, w, h, base)
    # stripes + small diamond motif
    for xx in range(x, x + w, 8):
        vline(L.alb, xx, y, y + h - 1, shade(base, 0.85))
        for yy in range(y + 4, y + h - 10, 9):
            px(L.alb, xx + 4, yy, shade(base, 1.25))
            px(L.alb, xx + 3, yy + 1, shade(base, 1.15))
            px(L.alb, xx + 5, yy + 1, shade(base, 1.15))
            px(L.alb, xx + 4, yy + 2, shade(base, 1.25))
    noise_tint(L.alb, pygame.Rect(x, y, w, h), rng, 0.06, scale=2)
    # water stains / peeling patches
    for _ in range(max(1, w // 90)):
        sx = int(rng.integers(x, x + w - 12))
        sw = int(rng.integers(8, 22))
        for k in range(int(rng.integers(6, h - 8))):
            for i in range(sw - k // 3):
                if rng.random() < 0.55:
                    xx, yy = sx + i + k // 6, y + k
                    if x <= xx < x + w:
                        c = L.alb.get_at((xx, yy))
                        L.alb.set_at((xx, yy), shade(c, 0.86))
    # wainscot
    rect(L.alb, x, y + h - 12, w, 12, P.WOOD_DARK)
    hline(L.alb, x, x + w - 1, y + h - 12, shade(P.WOOD, 1.1))
    for xx in range(x + 4, x + w, 22):
        rect(L.alb, xx, y + h - 9, 16, 6, shade(P.WOOD_DARK, 0.85))
    hline(L.alb, x, x + w - 1, y + h - 1, shade(P.WOOD_DARK, 0.6))


def floorboards(L: Layers, rng, x, y, w, h, base=FLOORBOARD):
    """Long planks running north-south, slightly different tones, with butt joints and nail heads."""
    rect(L.alb, x, y, w, h, base)
    for xx in range(x, x + w, 7):
        tone = shade(base, rng.uniform(0.88, 1.1))
        rect(L.alb, xx, y, 6, h, tone)
        vline(L.alb, xx + 6, y, y + h - 1, shade(base, 0.62))
        jy = y + int(rng.integers(8, max(9, h - 8)))
        hline(L.alb, xx, xx + 5, jy, shade(base, 0.6))
        px(L.alb, xx + 1, jy + 2, shade(base, 1.35))
        px(L.alb, xx + 4, jy - 2, shade(base, 1.35))
        for yy in range(y, y + h, 3):
            if rng.random() < 0.12:
                px(L.alb, xx + int(rng.integers(0, 6)), yy, shade(tone, 0.85))
    noise_tint(L.alb, pygame.Rect(x, y, w, h), rng, 0.07)
    # worn path down the middle
    cx = x + w // 2
    for yy in range(y, y + h):
        for xx in range(cx - 40, cx + 40):
            if x <= xx < x + w and BAYER4[yy % 4, xx % 4] < 0.3 * (1 - abs(xx - cx) / 40):
                L.alb.set_at((xx, yy), shade(L.alb.get_at((xx, yy)), 1.12))
    # AO along the back wall
    for k in range(4):
        hline(L.alb, x, x + w - 1, y + k, shade(L.alb.get_at((x + 1, y + k)), 0.6 + k * 0.1))


def stairs(L: Layers, x, y, w, h, rail_side="left"):
    tread = hexc("6a4a36")
    riser = hexc("3a2820")
    for i, yy in enumerate(range(y, y + h, 6)):
        rect(L.alb, x, yy, w, 4, tread)
        hline(L.alb, x, x + w - 1, yy, shade(tread, 1.2))
        rect(L.alb, x, yy + 4, w, 2, riser)
        # worn centres
        rect(L.alb, x + w // 2 - 8, yy + 1, 16, 2, shade(tread, 1.1))
    # banisters
    for side in (x - 3, x + w):
        rect(L.alb, side, y - 2, 3, h + 4, P.WOOD_DARK)
        vline(L.alb, side + 1, y - 2, y + h + 1, shade(P.WOOD, 1.2))
        for yy in range(y, y + h, 8):
            rect(L.alb, side, yy, 3, 2, shade(P.WOOD, 1.3))


def door_apt(L: Layers, x, y, num: str, lit=None):
    env.door(L, x, y, 18, 32, hexc("3b2a22"), glass=False, frame=hexc("2a1e18"))
    blit_text(L.alb, GLYPHS, num, x + 4, y + 4, P.BRASS, gap=0)
    if lit is not None:
        rect(L.emi, x, y + 32, 18, 1, lit)  # light under the door


def bake(seed: int = 14):
    rng = np.random.default_rng(seed)
    S = SpriteSet("tenement")
    L = Layers(W, H)
    rect(L.alb, 0, 0, W, H, SLAB)
    # side walls (top faces)
    for x in (0, X1):
        rect(L.alb, x, 0, W - X1 if x else X0, H, hexc("1d181e"))
    vline(L.alb, X0 - 1, 0, H - 1, hexc("2c252c"))
    vline(L.alb, X1, 0, H - 1, hexc("2c252c"))

    for k, (name, (wy0, wy1, wall0)) in enumerate(FLOORS.items()):
        wallpaper(L, rng, X0, wall0, X1 - X0, wy0 - wall0, WALLPAPER[k])
        floorboards(L, rng, X0, wy0, X1 - X0, wy1 - wy0)
    # slab edges (ceiling beams seen from above)
    for y in (520, 370, 220):
        rect(L.alb, X0, y, X1 - X0, 4, hexc("2a2028"))
        hline(L.alb, X0, X1 - 1, y, hexc("3a2e36"))
    # front wall + door
    rect(L.alb, 0, 664, W, H - 664, hexc("1d181e"))
    hline(L.alb, X0, X1 - 1, 664, hexc("3a2e36"))
    rect(L.alb, 222, 664, 36, 36, hexc("0e0c10"))
    rect(L.emi, 224, 690, 32, 10, shade(P.SODIUM, 0.25))  # street glow through the door
    L.wet(222, 650, 36, 14, 0.6)  # rain tracked in
    pygame.draw.ellipse(L.alb, shade(FLOORBOARD, 0.7), pygame.Rect(214, 646, 52, 16))
    L.anchor("door_in", 240, 652)

    for nm, (x, y, w, h) in STAIRS.items():
        stairs(L, x, y, w, h)
    # dim wall sconces so the stairs always read, without killing the shadows
    for (sx, sy, clip) in ((420, 556, [X0, 500, X1, 700]), (58, 404, [X0, 350, X1, 546]), (420, 256, [X0, 200, X1, 396])):
        rect(L.alb, sx - 2, sy - 3, 5, 5, P.BRASS)
        rect(L.emi, sx - 1, sy - 2, 3, 3, shade(P.BULB, 0.8))
        L.light(sx, sy + 14, 62, (1.0, 0.72, 0.45), 0.5, clip=clip)

    # --- ground hall dressing
    wy0, wy1, wall0 = FLOORS["f0"]
    for i in range(6):  # mailboxes
        rect(L.alb, 70 + i * 9, wall0 + 8, 8, 10, P.BRASS)
        rect(L.alb, 71 + i * 9, wall0 + 9, 6, 3, shade(P.BRASS, 0.6))
    blit_text(L.alb, GLYPHS, "NO PEDDLERS", 70, wall0 + 22, shade(P.CREAM, 0.6), gap=1)
    door_apt(L, 150, wall0 + 6, "1A")
    door_apt(L, 290, wall0 + 6, "1B", lit=shade(P.WINDOW_WARM, 0.7))
    # radiator
    rect(L.alb, 230, wy0 - 8, 30, 12, P.IRON)
    for xx in range(231, 260, 3):
        vline(L.alb, xx, wy0 - 7, wy0 + 3, P.IRON_LIGHT)
    L.collider(228, wy0 - 2, 34, 6, "low")
    # table where the Dunne brothers drink (west end of the hall)
    tx = 74
    rect(L.alb, tx, 616, 44, 18, P.WOOD)
    rect(L.alb, tx, 616, 44, 2, shade(P.WOOD, 1.3))
    rect(L.alb, tx + 2, 634, 4, 8, P.WOOD_DARK)
    rect(L.alb, tx + 38, 634, 4, 8, P.WOOD_DARK)
    for bx, c in ((tx + 8, hexc("3a5a40")), (tx + 16, hexc("5a3a20")), (tx + 26, hexc("3a5a40"))):
        rect(L.alb, bx, 611, 3, 7, c)
        px(L.alb, bx + 1, 611, shade(c, 1.6))
    rect(L.alb, tx + 32, 619, 6, 4, P.CREAM)  # playing cards
    L.collider(tx - 2, 620, 48, 16, "low")

    # --- floor 1: hallway, radio behind 2B
    wy0, wy1, wall0 = FLOORS["f1"]
    door_apt(L, 140, wall0 + 6, "2A")
    door_apt(L, 296, wall0 + 6, "2B", lit=shade(P.WINDOW_WARM, 0.9))
    rect(L.alb, 200, wall0 + 10, 24, 16, P.POSTER_PAPER)  # framed notice
    blit_text(L.alb, GLYPHS, "RENT", 202, wall0 + 13, P.INK, gap=1)
    L.anchor("radio", 305, wy0 + 2)
    L.light(305, wy0 + 6, 40, P.L_WINDOW, 0.45, clip=[X0, 392, X1, 546])
    # a pram parked in the hall
    rect(L.alb, 380, wy0 + 30, 22, 12, hexc("2a2e3a"))
    rect(L.alb, 380, wy0 + 28, 10, 6, hexc("1e222c"))
    L.collider(378, wy0 + 32, 26, 12)

    # --- floor 2: landing where Pike sits
    wy0, wy1, wall0 = FLOORS["f2"]
    door_apt(L, 180, wall0 + 6, "3A")
    door_apt(L, 290, wall0 + 6, "3B")
    rect(L.alb, 240, wy0 + 20, 16, 10, P.WOOD_DARK)  # crate he sits on
    hline(L.alb, 240, 255, wy0 + 20, shade(P.WOOD, 1.2))
    L.collider(240, wy0 + 24, 16, 6, "low")

    # --- floor 3: Hobb's room
    wy0, wy1, wall0 = FLOORS["f3"]
    # rug
    rug = hexc("5a2028")
    rect(L.alb, 150, 150, 170, 56, rug)
    for xx in range(152, 318, 6):
        px(L.alb, xx, 152, P.CURTAIN_GOLD)
        px(L.alb, xx, 203, P.CURTAIN_GOLD)
    dither_rect(L.alb, 156, 156, 158, 44, rug, shade(rug, 1.2), 0.15)
    # table with lamp, camera, papers
    rect(L.alb, 262, 122, 64, 22, P.WOOD)
    rect(L.alb, 262, 122, 64, 2, shade(P.WOOD, 1.3))
    rect(L.alb, 264, 144, 4, 8, P.WOOD_DARK)
    rect(L.alb, 320, 144, 4, 8, P.WOOD_DARK)
    rect(L.alb, 300, 114, 8, 10, hexc("2a5a3a"))  # green banker's lamp
    rect(L.emi, 300, 120, 8, 2, shade(P.WINDOW_WARM, 1.2))
    rect(L.alb, 268, 126, 14, 9, P.POSTER_PAPER)  # ledger
    L.collider(260, 128, 68, 18, "low")
    L.light(304, 128, 120, (1.0, 0.82, 0.55), 1.0, clip=[X0, 40, X1, 250], name="hobb_lamp")
    # cot, chair, coat rack, safe
    rect(L.alb, 64, 188, 60, 22, hexc("4a4a44"))
    rect(L.alb, 64, 188, 18, 22, P.CREAM)
    L.collider(62, 192, 64, 18)
    rect(L.alb, 380, 110, 26, 30, P.IRON)
    rect(L.alb, 383, 113, 20, 24, shade(P.IRON, 1.2))
    pygame.draw.circle(L.alb, P.BRASS, (393, 124), 3)
    L.collider(378, 120, 30, 22)
    # pin-up calendar on the back wall (the Row's idea of decoration)
    rect(L.alb, 200, wall0 + 6, 20, 28, P.CREAM)
    pygame.draw.ellipse(L.alb, hexc("c89a7a"), pygame.Rect(205, wall0 + 9, 8, 14))
    rect(L.alb, 203, wall0 + 22, 14, 4, P.CURTAIN_RED)
    blit_text(L.alb, GLYPHS, "MAY", 201, wall0 + 27, P.INK, gap=0)
    # the fire-escape window in the west wall
    rect(L.alb, X0 - 6, 126, 8, 36, hexc("3a3036"))
    rect(L.alb, X0 - 4, 128, 4, 32, P.GLASS)
    rect(L.emi, X0 - 4, 128, 4, 32, shade(P.WINDOW_COOL, 0.6))
    L.light(X0 + 8, 146, 80, (0.55, 0.6, 1.0), 0.7, clip=[X0, 40, X1, 250])
    L.wet(X0, 132, 14, 26, 0.5)
    L.anchor("window_in", X0 + 14, 150)
    # door frame where the stairs arrive
    rect(L.alb, 356, 216, 64, 4, P.WOOD_DARK)

    # --- colliders: everything that is not floor or stairs is solid
    L.collider(0, 0, X0, H)
    L.collider(X1, 0, W - X1, H)
    walk = [pygame.Rect(X0, FLOORS[f][0], X1 - X0, FLOORS[f][1] - FLOORS[f][0]) for f in FLOORS]
    walk += [pygame.Rect(*STAIRS[s]) for s in STAIRS]
    walk.append(pygame.Rect(222, 664, 36, 36))
    # carve solids as horizontal strips between walkable bands, then merge identical rows
    open_runs: dict[tuple, int] = {}
    strips = []
    for y in list(range(0, H, 2)) + [H]:
        runs = set()
        if y < H:
            xs = sorted((r.left, r.right) for r in walk if r.top <= y < r.bottom)
            x = X0
            for a, b in xs:
                if a > x:
                    runs.add((x, a - x))
                x = max(x, b)
            if x < X1:
                runs.add((x, X1 - x))
        for key in list(open_runs):
            if key not in runs:
                y0 = open_runs.pop(key)
                strips.append((key[0], y0, key[1], y - y0))
        for key in runs:
            open_runs.setdefault(key, y)
    for x, y, w, h in strips:
        L.collider(x, y, w, h)

    # --- props that matter at runtime: breakable ceiling bulbs
    bulbs = [("bulb_f0", 150, 598, [X0, 540, X1, 700]), ("bulb_f1", 230, 446, [X0, 392, X1, 546]),
             ("bulb_f2", 250, 296, [X0, 242, X1, 396])]
    for bid, bx, by, clip in bulbs:
        L.meta["props"].append({"kind": "bulb", "id": bid, "x": bx, "y": by,
                                "light": {"dx": 0, "dy": 6, "radius": 112, "color": [1.0, 0.8, 0.55], "intensity": 1.0,
                                          "clip": clip}})
    return {"bg": L, "sprites": S, "size": (W, H)}


def merge_colliders(cols):
    return cols
