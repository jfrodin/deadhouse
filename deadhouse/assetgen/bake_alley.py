"""Bakes the alley beside No. 14 (north-south) and the rooftops above it."""
from __future__ import annotations

import math

import numpy as np
import pygame

from . import env
from . import palette as P
from .env import Layers, SpriteSet
from .font_data import GLYPHS
from .gfx import (BAYER4, blit_text, brick_wall, dither_rect, hexc, hline, line, mix, noise_tint, outline, poly, px,
                  rect, shade, surf, vgrad_dither, vline)

# ============================================================================ alley
AW, AH = 320, 480
AX0, AX1 = 56, 264  # walkable floor between the side walls


def cobbles(L: Layers, rng, x, y, w, h):
    """Irregular rounded setts with dark joints (reads as ground, not as a wall)."""
    base = hexc("3a3c42")
    joint = hexc("1c1d22")
    rect(L.alb, x, y, w, h, joint)
    yy = y
    while yy < y + h:
        rh = int(rng.integers(4, 7))
        xx = x - int(rng.integers(0, 6))
        while xx < x + w:
            sw = int(rng.integers(5, 9))
            c = shade(base, rng.uniform(0.8, 1.2))
            r = pygame.Rect(xx + 1, yy + 1, sw - 1, rh - 1).clip(pygame.Rect(x, y, w, h))
            if r.w > 1 and r.h > 1:
                pygame.draw.ellipse(L.alb, c, r)
                if r.w > 3:
                    hline(L.alb, r.x + 1, r.right - 2, r.y, shade(c, 1.25))  # wet top edge catches light
            xx += sw
        yy += rh
    noise_tint(L.alb, pygame.Rect(x, y, w, h), rng, 0.05)
    # grime and moss toward the walls
    for k in range(10):
        for xx in range(x, x + w):
            edge = min(xx - x, x + w - 1 - xx)
            if edge < 10 and rng.random() < 0.25 * (1 - edge / 10):
                yy = int(rng.integers(y, y + h))
                px(L.alb, xx, yy, hexc("2a3328"))


def side_wall(L: Layers, rng, x0, x1, y0, y1, facing):
    """A side wall of the alley, cheated toward the camera so it reads as height."""
    brick_wall(L.alb, x0, y0, x1 - x0, y1 - y0, shade(P.BRICK_DARK, 0.75), shade(P.MORTAR, 0.7), rng, bw=7, bh=3)
    noise_tint(L.alb, pygame.Rect(x0, y0, x1 - x0, y1 - y0), rng, 0.08, scale=2)
    # darken toward the top (further up the wall, less light)
    for xx in range(x0, x1):
        k = (xx - x0) / max(1, x1 - x0 - 1)
        f = 0.45 + 0.55 * (k if facing > 0 else 1 - k)
        for yy in range(y0, y1):
            if BAYER4[yy % 4, xx % 4] < 1 - f:
                L.alb.set_at((xx, yy), shade(L.alb.get_at((xx, yy)), 0.6))
    # a few windows seen at a steep angle
    for wy in range(y0 + 30, y1 - 30, 70):
        if rng.random() < 0.7:
            wx = x0 + 6 if facing > 0 else x1 - 14
            rect(L.alb, wx, wy, 8, 18, P.GLASS)
            if rng.random() < 0.5:
                rect(L.emi, wx + 1, wy + 1, 6, 16, shade(P.WINDOW_WARM, 0.35))
    edge = x1 - 1 if facing > 0 else x0
    vline(L.alb, edge, y0, y1 - 1, hexc("4a4048"))


def bake_alley(seed=7):
    rng = np.random.default_rng(seed)
    S = SpriteSet("alley")
    L = Layers(AW, AH)
    # north wall: the back of the next block, a south-facing brick face
    brick_wall(L.alb, 0, 0, AW, 96, P.BRICK_DARK, P.MORTAR, rng, bw=8, bh=3)
    noise_tint(L.alb, pygame.Rect(0, 0, AW, 96), rng, 0.08, scale=2)
    for wx in (80, 140, 200):
        env.sash_window(L, rng, wx, 14, 10, 16, ["dark", "dim", "shade"][int(rng.integers(0, 3))], frame=P.STONE_DARK)
    # chained iron gate (locked: beyond the prototype)
    gx = 140
    rect(L.alb, gx, 56, 40, 40, P.INK)
    for xx in range(gx, gx + 40, 4):
        vline(L.alb, xx, 56, 95, P.IRON_LIGHT)
    hline(L.alb, gx, gx + 39, 60, P.IRON_LIGHT)
    hline(L.alb, gx, gx + 39, 90, P.IRON_LIGHT)
    for k in range(6):
        px(L.alb, gx + 18 + k % 3, 72 + k, shade(P.IRON_LIGHT, 1.4))
    L.anchor("gate", gx + 20, 100)
    # torn posters on the brick
    for pxx, col in ((40, P.POSTER_PAPER), (232, shade(P.POSTER_PAPER, 0.8))):
        rect(L.alb, pxx, 40, 22, 30, col)
        blit_text(L.alb, GLYPHS, "VOTE", pxx + 2, 44, P.CURTAIN_RED, gap=0)
        blit_text(L.alb, GLYPHS, "PRUITT", pxx + 1, 54, P.INK, gap=0)
        poly(L.alb, [(pxx + 12, 70), (pxx + 22, 58), (pxx + 22, 70)], P.BRICK_DARK)
    env.grime_bottom(L, 0, 70, AW, 26, 0.6)
    # side walls: No. 14 on the west, the Hotel Calla on the east
    side_wall(L, rng, 0, AX0, 96, AH, +1)
    side_wall(L, rng, AX1, AW, 96, AH, -1)
    # floor
    cobbles(L, rng, AX0, 96, AX1 - AX0, AH - 96)
    # gutter down the middle, puddles
    cx = (AX0 + AX1) // 2
    rect(L.alb, cx - 2, 96, 4, AH - 96, hexc("23252a"))
    L.wet(AX0, 96, AX1 - AX0, AH - 96, 0.55, 96)
    L.wet(cx - 2, 96, 4, AH - 96, 1.0, 96)
    for _ in range(9):
        px0, py0 = int(rng.integers(AX0 + 10, AX1 - 30)), int(rng.integers(120, AH - 20))
        pw, ph = int(rng.integers(14, 34)), int(rng.integers(4, 8))
        m = surf(pw, ph)
        pygame.draw.ellipse(m, (255, 255, 255, 255), m.get_rect())
        dark = surf(pw, ph)
        dark.fill(hexc("22242a"))
        dark.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        L.alb.blit(dark, (px0, py0))
        L.wet(px0, py0, pw, ph, 1.0, 96, mask=m)
    # hotel kitchen back door on the east wall: light spill + step
    rect(L.alb, AX1 - 3, 250, 4, 30, P.WOOD_DARK)
    rect(L.emi, AX1 - 2, 252, 2, 26, shade(P.WINDOW_WARM, 0.9))
    for k in range(22):
        y = 252 + k
        for i in range(1, 30 - k // 2):
            if BAYER4[y % 4, (AX1 - i) % 4] < 0.4 * (1 - i / 30):
                px(L.emi, AX1 - i, y + 4, shade(P.WINDOW_WARM, 0.25))
    L.light(AX1 - 10, 268, 90, P.L_WINDOW, 0.75)
    L.anchor("kitchen_door", AX1 - 12, 270)
    # caged bulb over the north gate
    L.light(160, 108, 90, P.L_BULB, 0.8)
    rect(L.emi, 158, 98, 3, 2, P.BULB)
    # neon spill from the Row at the south mouth
    L.light(160, AH + 10, 140, (0.9, 0.35, 0.7), 0.7)
    L.light(120, AH - 4, 90, P.L_SODIUM, 0.5)
    # dumpsters, crates, trash
    def dumpster(x, y):
        rect(L.alb, x, y, 34, 18, hexc("2f4234"))
        rect(L.alb, x, y, 34, 4, hexc("3c5442"))
        for xx in range(x + 3, x + 34, 6):
            vline(L.alb, xx, y + 5, y + 17, hexc("26362a"))
        rect(L.alb, x + 2, y + 18, 4, 3, P.INK)
        rect(L.alb, x + 28, y + 18, 4, 3, P.INK)
        L.collider(x, y + 8, 34, 12)
    dumpster(AX1 - 40, 150)
    dumpster(AX0 + 4, 380)
    for (bx, by) in ((AX0 + 50, 130), (AX1 - 24, 330), (AX0 + 10, 230)):
        rect(L.alb, bx, by, 14, 12, P.WOOD)
        line(L.alb, bx, by, bx + 13, by + 11, P.WOOD_DARK)
        line(L.alb, bx + 13, by, bx, by + 11, P.WOOD_DARK)
        hline(L.alb, bx, bx + 13, by, shade(P.WOOD, 1.3))
        L.collider(bx, by + 4, 14, 8)
    # the fire escape ladder base on the west wall (No. 14)
    lx = AX0 + 2
    rect(L.alb, lx, 300, 10, 44, P.INK)
    for y in range(302, 344, 5):
        hline(L.alb, lx, lx + 9, y, P.IRON_LIGHT)
    vline(L.alb, lx, 300, 344, P.IRON_LIGHT)
    vline(L.alb, lx + 9, 300, 344, P.IRON_LIGHT)
    L.anchor("ladder", lx + 12, 340)
    rect(L.emi, lx + 14, 286, 2, 2, P.BULB)  # caged work light on No. 14's wall
    L.light(lx + 20, 300, 96, P.L_BULB, 0.85, flicker="buzz")
    # colliders
    L.collider(0, 0, AW, 98)
    L.collider(0, 0, AX0, AH)
    L.collider(AX1, 0, AW - AX1, AH)

    # foreground: fire-escape platforms and laundry lines overhead
    F = Layers(AW, AH, opaque=False)
    for (py_, pw) in ((200, 46), (300, 40)):
        rect(F.alb, AX0 - 2, py_, pw, 22, P.IRON)
        for xx in range(AX0, AX0 + pw - 2, 3):
            vline(F.alb, xx, py_ + 2, py_ + 19, hexc("1c1e22"))
        hline(F.alb, AX0 - 2, AX0 + pw - 3, py_, P.IRON_LIGHT)
        hline(F.alb, AX0 - 2, AX0 + pw - 3, py_ + 21, P.IRON_LIGHT)
        vline(F.alb, AX0 + pw - 3, py_, py_ + 21, P.IRON_LIGHT)
    for (ly, sag) in ((140, 10), (260, 14), (410, 8)):
        pts = [(AX0, ly), (AX1, ly - 4)]
        prev = None
        for i in range(0, AX1 - AX0 + 1, 2):
            t = i / (AX1 - AX0)
            y = ly - 4 * t + math.sin(t * math.pi) * sag
            pt = (AX0 + i, int(y))
            if prev:
                line(F.alb, prev[0], prev[1], pt[0], pt[1], hexc("8a8478"))
            prev = pt
        for k in range(int(rng.integers(4, 8))):
            t = rng.uniform(0.1, 0.9)
            x = int(AX0 + t * (AX1 - AX0))
            y = int(ly - 4 * t + math.sin(t * math.pi) * sag)
            col = [P.CREAM, hexc("8a3a3a"), hexc("4a5a7a"), hexc("c8c0b0"), hexc("6a2a4a")][int(rng.integers(0, 5))]
            kind = int(rng.integers(0, 3))
            if kind == 0:  # shirt
                rect(F.alb, x - 4, y + 1, 9, 9, col)
                rect(F.alb, x - 6, y + 1, 13, 3, col)
            elif kind == 1:  # slip / stockings
                rect(F.alb, x - 3, y + 1, 6, 12, col)
                hline(F.alb, x - 3, x + 2, y + 1, shade(col, 1.2))
            else:  # sheet
                rect(F.alb, x - 8, y + 1, 16, 10, col)
                for yy in range(y + 2, y + 11, 3):
                    hline(F.alb, x - 8, x + 7, yy, shade(col, 0.9))
            px(F.alb, x - 2, y, P.WOOD)
            px(F.alb, x + 2, y, P.WOOD)
    F.wet(0, 0, AW, AH, 0.0)
    # a cat on the dumpster lid (runtime prop)
    L.meta["props"].append({"kind": "cat", "x": AX1 - 26, "y": 148})
    L.meta["props"].append({"kind": "steam", "x": AX1 - 14, "y": 286})
    return {"bg": L, "fg": F, "sprites": S, "size": (AW, AH)}


# ============================================================================ roof
RW, RH = 560, 320


def bake_roof(seed=9):
    rng = np.random.default_rng(seed)
    S = SpriteSet("roof")
    L = Layers(RW, RH)
    # night sky + the city beyond (north)
    vgrad_dither(L.alb, 0, 0, RW, 110, hexc("0a0c16"), hexc("23233a"), steps=6)
    env.skyline(L, rng, -20, RW + 20, 108, max_h=70)
    # a far bridge with a string of lights
    for x in range(0, RW, 3):
        y = int(60 + 8 * math.sin(x / RW * math.pi))
        px(L.alb, x, y + 6, hexc("1a1c26"))
        if x % 9 == 0:
            px(L.emi, x, y + 5, shade(P.BULB, 0.6))
    # searchlight cone (static glow; animated at runtime)
    L.meta["props"].append({"kind": "searchlight", "x": 430, "y": 108})
    # roof surfaces: tar paper with seams, parapets
    tar = hexc("2a2a2e")
    rect(L.alb, 0, 110, RW, RH - 110, tar)
    for y in range(114, RH, 9):
        hline(L.alb, 0, RW - 1, y, shade(tar, 0.8))
    noise_tint(L.alb, pygame.Rect(0, 110, RW, RH - 110), rng, 0.08, scale=2)
    L.wet(0, 110, RW, RH - 110, 0.5, 110)
    # puddles on the tar
    for _ in range(10):
        px0, py0 = int(rng.integers(10, RW - 40)), int(rng.integers(130, RH - 20))
        pw, ph = int(rng.integers(18, 50)), int(rng.integers(5, 10))
        m = surf(pw, ph)
        pygame.draw.ellipse(m, (255, 255, 255, 255), m.get_rect())
        dark = surf(pw, ph)
        dark.fill(shade(tar, 0.7))
        dark.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        L.alb.blit(dark, (px0, py0))
        L.wet(px0, py0, pw, ph, 1.0, 110, mask=m)
    # parapet along the north edge (low wall facing us)
    rect(L.alb, 0, 104, RW, 10, P.BRICK_DARK)
    hline(L.alb, 0, RW - 1, 104, P.STONE)
    hline(L.alb, 0, RW - 1, 105, P.STONE_DARK)
    # the step between No. 14 and the Hotel Calla's roof
    rect(L.alb, 300, 110, 6, RH - 110, P.BRICK_DARK)
    hline(L.alb, 300, 305, 110, P.STONE)
    # chimney stacks, vents, the water tower
    for (cx, cy) in ((90, 150), (230, 140), (380, 160)):
        rect(L.alb, cx, cy - 22, 16, 26, P.BRICK_RED)
        rect(L.alb, cx - 1, cy - 24, 18, 3, P.STONE_DARK)
        rect(L.alb, cx + 3, cy - 23, 4, 2, P.INK)
        rect(L.alb, cx + 9, cy - 23, 4, 2, P.INK)
        L.collider(cx, cy - 4, 16, 8)
        L.meta["props"].append({"kind": "smoke", "x": cx + 6, "y": cy - 24})
    tx, ty = 470, 170
    for lx in (tx - 18, tx + 14):  # legs
        rect(L.alb, lx, ty - 30, 4, 40, P.IRON)
    rect(L.alb, tx - 26, ty - 84, 52, 54, hexc("4a3628"))
    for xx in range(tx - 26, tx + 26, 5):
        vline(L.alb, xx, ty - 84, ty - 31, hexc("3a2a20"))
    for yy in (ty - 76, ty - 52, ty - 36):
        hline(L.alb, tx - 26, tx + 25, yy, P.IRON_LIGHT)
    poly(L.alb, [(tx - 28, ty - 84), (tx, ty - 104), (tx + 28, ty - 84)], hexc("2e2420"))
    L.collider(tx - 20, ty - 4, 40, 10)
    # skylight over the hotel stairwell: warm light from below
    rect(L.alb, 340, 236, 40, 24, P.IRON)
    rect(L.alb, 342, 238, 36, 20, P.GLASS)
    rect(L.emi, 342, 238, 36, 20, shade(P.WINDOW_WARM, 0.55))
    for xx in range(342, 378, 6):
        vline(L.alb, xx, 238, 257, P.IRON)
        vline(L.emi, xx, 238, 257, (0, 0, 0, 255))
    L.light(360, 248, 70, P.L_WINDOW, 0.6)
    L.collider(338, 240, 44, 20)
    # pigeon loft on No. 14 (the lantern is inside)
    lx0, ly0 = 120, 196
    rect(L.alb, lx0, ly0 - 26, 56, 30, P.WOOD)
    for xx in range(lx0, lx0 + 56, 4):
        vline(L.alb, xx, ly0 - 26, ly0 + 3, shade(P.WOOD, 0.85))
    poly(L.alb, [(lx0 - 4, ly0 - 26), (lx0 + 28, ly0 - 38), (lx0 + 60, ly0 - 26)], P.WOOD_DARK)
    for k in range(3):
        rect(L.alb, lx0 + 6 + k * 16, ly0 - 18, 8, 8, P.INK)
        for yy in range(ly0 - 18, ly0 - 10, 2):
            hline(L.alb, lx0 + 6 + k * 16, lx0 + 13 + k * 16, yy, hexc("6a6a60"))
    L.collider(lx0, ly0 - 6, 56, 10)
    L.anchor("loft", lx0 + 28, ly0 + 10)
    # the back of the VELOUR sign glows over the east parapet
    for k in range(6):
        rect(L.alb, 520 + k * 2, 70, 1, 40, P.IRON)
    rect(L.emi, 516, 66, 40, 4, shade(P.NEON_MAGENTA, 0.6))
    L.light(530, 112, 160, P.L_MAGENTA, 0.75)
    # fire-escape top on the south-west edge (down to the alley / Hobb's window)
    rect(L.alb, 20, RH - 28, 40, 28, P.IRON)
    for xx in range(22, 58, 3):
        vline(L.alb, xx, RH - 26, RH - 2, hexc("1c1e22"))
    hline(L.alb, 20, 59, RH - 28, P.IRON_LIGHT)
    rect(L.alb, 26, RH - 12, 8, 12, P.INK)
    L.anchor("escape_top", 40, RH - 34)
    # colliders: parapet, edges
    L.collider(0, 0, RW, 116)
    L.collider(-10, 0, 10, RH)
    L.collider(RW, 0, 10, RH)
    L.collider(0, RH - 2, 20, 4)
    L.collider(60, RH - 2, RW - 60, 4)
    L.collider(300, 110, 6, 40)
    L.collider(300, 200, 6, RH - 200)
    # moon fill
    L.light(280, 200, 400, (0.4, 0.45, 0.75), 0.35)
    F = Layers(RW, RH, opaque=False)
    # foreground: parapet along the south edge (we look over it), with gaps
    rect(F.alb, 60, RH - 10, RW - 60, 10, P.BRICK_DARK)
    hline(F.alb, 60, RW - 1, RH - 10, P.STONE)
    F.wet(0, RH - 12, RW, 12, 0.0)
    return {"bg": L, "fg": F, "sprites": S, "size": (RW, RH)}
