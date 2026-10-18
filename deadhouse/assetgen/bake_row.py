"""Bakes Lantern Row: background, foreground (the elevated rail) and props.

The area is 1440x300. Facades stand along the north edge (base y=148), the road
runs east-west, and the Elevated Line passes overhead along the south edge.
"""
from __future__ import annotations

import numpy as np
import pygame

from . import env
from . import palette as P
from .env import Layers, SpriteSet
from .font_data import GLYPHS
from .gfx import (BAYER4, blit_text, brick_wall, dither_rect, hexc, hline, line, mix, noise_tint, outline, poly, px,
                  rect, shade, surf, text_width, vgrad_dither, vline, with_alpha)

W, H = 1440, 300
BASE = 148
LAYOUT = {
    "mirror_y": BASE,
    "north_sidewalk": (BASE, 176),
    "road": (183, 244),
    "rails": (199, 207),
    "south_sidewalk": (251, 300),
}
GROUND_FLOOR = 40
STORY = 34

TILE_BLACK = hexc("1b2622")
TILE_EDGE = hexc("2c3b35")


# ----------------------------------------------------------------------------- helpers
def glyph_mask(text: str, scale: int, gap: int = 1) -> pygame.Surface:
    w = text_width(GLYPHS, text, gap) * scale
    m = surf(w + 2, 8 * scale + 2)
    tmp = surf(text_width(GLYPHS, text, gap), 8)
    blit_text(tmp, GLYPHS, text, 0, 0, (255, 255, 255, 255), gap=gap)
    m.blit(pygame.transform.scale(tmp, (tmp.get_width() * scale, 8 * scale)), (1, 1))
    return m


def tube_outline(mask: pygame.Surface) -> np.ndarray:
    a = pygame.surfarray.array_alpha(mask) > 0
    edge = np.zeros_like(a)
    edge[1:-1, 1:-1] = a[1:-1, 1:-1] & ~(a[:-2, 1:-1] & a[2:, 1:-1] & a[1:-1, :-2] & a[1:-1, 2:])
    return edge


def big_neon(sprites: SpriteSet, name: str, text: str, color, frame_color=None, scale=2, pad=4, board=None):
    m = glyph_mask(text, scale, gap=2)
    edge = tube_outline(m)
    mw, mh = m.get_size()
    w, h = mw + pad * 2, mh + pad * 2
    alb, emi = surf(w, h), surf(w, h)
    if board is not None:
        rect(alb, 0, 0, w, h, board)
        rect(alb, 1, 1, w - 2, h - 2, shade(board, 0.75))
    xs, ys = np.nonzero(edge)
    for x, y in zip(xs, ys):
        px(alb, x + pad, y + pad, shade(color, 0.35))
        px(emi, x + pad, y + pad, color)
    if frame_color is not None:
        for x in range(1, w - 1):
            if x % 2 == 0:
                px(emi, x, 1, frame_color)
                px(emi, x, h - 2, frame_color)
        for y in range(1, h - 1):
            if y % 2 == 0:
                px(emi, 1, y, frame_color)
                px(emi, w - 2, y, frame_color)
    return sprites.add(name, alb, emi), w, h


def bulb_letters_vertical(sprites, name, text, lit_mask: list[bool], color=P.BULB, board=P.STONE_DARK, w=17):
    """Cinema blade sign made of bulbs. lit_mask says which letters still work."""
    h = len(text) * 13 + 8
    alb, emi = surf(w, h), surf(w, h)
    rect(alb, 0, 0, w, h, shade(board, 0.8))
    rect(alb, 1, 1, w - 2, h - 2, board)
    vline(alb, 2, 2, h - 3, shade(board, 1.2))
    letters = []
    for i, ch in enumerate(text):
        g = GLYPHS[ch]
        ox = (w - len(g[0])) // 2
        oy = 4 + i * 13
        le_alb, le_emi = surf(w, 13), surf(w, 13)
        for j, row in enumerate(g):
            for k, c in enumerate(row):
                if c == "#":
                    px(alb, ox + k, oy + j, P.BULB_DIM)
                    if lit_mask[i]:
                        px(emi, ox + k, oy + j, color)
        letters.append((ox, oy))
    return sprites.add(name, alb, emi), w, h


# ----------------------------------------------------------------------------- buildings
def tenement(L: Layers, S: SpriteSet, rng, x0, x1):
    w = x1 - x0
    brick_wall(L.alb, x0, 0, w, BASE, P.BRICK_RED, P.MORTAR, rng, bw=7, bh=3)
    noise_tint(L.alb, pygame.Rect(x0, 0, w, BASE), rng, 0.05, scale=2)
    # stone ground-floor band
    gy = BASE - GROUND_FLOOR
    rect(L.alb, x0, gy, w, GROUND_FLOOR, P.STONE_DARK)
    for yy in range(gy + 4, BASE, 6):
        hline(L.alb, x0, x1 - 1, yy, shade(P.STONE_DARK, 0.8))
    cornice(L, x0, gy - 4, w, P.STONE_DARK)
    # windows: 4 visible rows above
    states = ["dark", "warm", "dim", "dark", "shade", "tv", "warm", "dark", "dim", "dark", "blind"]
    for r in range(4):
        wy = gy - 26 - r * STORY
        for i, wx in enumerate(range(x0 + 12, x1 - 12, 27)):
            st = states[int(rng.integers(0, len(states)))]
            env.sash_window(L, rng, wx, wy, 11, 17, st, frame=P.STONE)
            if rng.random() < 0.5:
                env.rain_streaks(L, wx, wy + 19, 11, 20, rng, count=3)
    # ghost sign painted on the brick
    gs = "GARNET ARMS"
    tw = text_width(GLYPHS, gs, 2)
    blit_text(L.alb, GLYPHS, gs, x0 + (w - tw) // 2, gy - 3 * STORY + 4, mix(P.BRICK_RED, P.CREAM, 0.32), gap=2)
    # laundry storefront (lit, open late)
    env.storefront(L, rng, x0 + 10, gy + 8, 62, 24, frame=P.IRON, glow=mix(P.WINDOW_COOL, P.CREAM, 0.35))
    for i in range(4):  # machines silhouettes
        mx = x0 + 13 + i * 15
        rect(L.emi, mx, gy + 20, 11, 12, shade(P.WINDOW_COOL, 0.35))
        pygame.draw.circle(L.emi, shade(P.WINDOW_COOL, 0.8), (mx + 5, gy + 26), 3)
    env.neon_letters(L.alb, L.emi, "WASH", x0 + 25, gy - 1, P.NEON_CYAN)
    L.light(x0 + 41, BASE + 10, 70, P.L_FLUOR, 0.55)
    # entrance with stoop
    dx = x0 + 96
    env.door(L, dx, gy + 12, 18, 28, P.WOOD_DARK, lit=P.WINDOW_DIM)
    rect(L.alb, dx - 6, BASE - 2, 30, 3, P.STONE)
    rect(L.alb, dx - 4, BASE + 1, 26, 3, shade(P.STONE, 0.85))
    rect(L.alb, dx - 2, BASE + 4, 22, 3, shade(P.STONE, 0.7))
    L.wet(dx - 6, BASE - 2, 30, 9, 0.3, BASE)
    L.collider(dx - 6, BASE, 4, 7)
    L.collider(dx + 20, BASE, 4, 7)
    blit_text(L.alb, GLYPHS, "14", dx + 5, gy + 2, P.BRASS)
    L.anchor("tenement_door", dx + 9, BASE + 8)
    # broken transom bulb over the door
    L.meta["props"].append({"kind": "flicker_light", "x": dx + 9, "y": gy + 4, "pattern": "dying",
                            "light": {"radius": 40, "color": list(P.L_BULB), "intensity": 0.6}})
    # rooms-to-let card in a window
    rect(L.alb, x0 + 128, gy + 14, 12, 7, P.POSTER_PAPER)
    hline(L.alb, x0 + 129, x0 + 138, gy + 16, P.INK)
    hline(L.alb, x0 + 129, x0 + 136, gy + 18, P.INK)
    env.storefront(L, rng, x0 + 124, gy + 8, 22, 24, frame=P.WOOD_DARK)
    rect(L.alb, x0 + 128, gy + 14, 12, 7, P.POSTER_PAPER)
    env.storefront(L, rng, x0 + 158, gy + 8, 62, 24, frame=P.WOOD_DARK, glow=None)
    env.grime_bottom(L, x0, BASE - 18, w, 18)
    env.drainpipe(L, x1 - 4, 0, BASE - 1)


def cornice(L, x, y, w, c):
    env.cornice(L, x, y, w, c)


def hotel(L: Layers, S: SpriteSet, rng, x0, x1):
    w = x1 - x0
    rect(L.alb, x0, 0, w, BASE, P.CREAM)
    noise_tint(L.alb, pygame.Rect(x0, 0, w, BASE), rng, 0.04, scale=2)
    # rusticated quoins
    for yy in range(0, BASE, 8):
        rect(L.alb, x0, yy, 5, 6, shade(P.CREAM, 0.9))
        rect(L.alb, x1 - 5, yy, 5, 6, shade(P.CREAM, 0.9))
    gy = BASE - GROUND_FLOOR
    cornice(L, x0, gy - 4, w, P.CREAM)
    for r in range(4):
        wy = gy - 26 - r * STORY
        for i, wx in enumerate(range(x0 + 14, x1 - 12, 21)):
            roll = rng.random()
            st = "red" if roll < 0.12 else ("shade" if roll < 0.35 else ("dark" if roll < 0.7 else "dim"))
            env.sash_window(L, rng, wx, wy, 9, 17, st, frame=P.PLASTER_DARK)
    # lobby window with a clerk
    env.storefront(L, rng, x0 + 12, gy + 6, 44, 26, frame=P.WOOD_DARK, glow=P.WINDOW_WARM)
    cx = x0 + 34
    rect(L.emi, x0 + 12, gy + 22, 44, 10, shade(P.WINDOW_WARM, 0.45))  # desk
    pygame.draw.ellipse(L.emi, shade(P.WINDOW_WARM, 0.25), pygame.Rect(cx - 3, gy + 11, 7, 7))
    rect(L.emi, cx - 4, gy + 17, 9, 6, shade(P.WINDOW_WARM, 0.25))
    L.light(x0 + 34, BASE + 8, 60, P.L_WINDOW, 0.5)
    # door + canopy
    dx = x0 + 66
    env.door(L, dx, gy + 10, 20, 30, P.WOOD_DARK, lit=P.WINDOW_WARM)
    L.anchor("hotel_door", dx + 10, BASE + 6)
    env.awning(L, dx - 8, gy - 2, 36, 8, P.AWNING_RED)
    blit_text(L.alb, GLYPHS, "CALLA", dx - 3, gy - 12, P.BRASS, gap=1)
    # right window with a small red ROOMS neon
    env.storefront(L, rng, x0 + 100, gy + 6, 48, 26, frame=P.WOOD_DARK, glow=P.WINDOW_DIM)
    key, sw, sh = env.neon_text_sign(S, "rooms", "ROOMS", P.NEON_RED)
    env.add_sign_prop(L, key, x0 + 106, gy + 12, sw, sh, "buzz", P.L_RED, radius=45, intensity=0.6, light_dy=40)
    # vertical HOTEL blade
    key, bw, bh = env.neon_blade(S, "hotel_blade", "HOTEL", P.NEON_RED, outline_color=shade(P.NEON_RED, 0.6))
    env.add_sign_prop(L, key, x1 - 18, 18, bw, bh, "steady", P.L_RED, radius=90, intensity=0.9, light_dy=bh + 50)
    env.grime_bottom(L, x0, BASE - 14, w, 14, 0.4)


def velour(L: Layers, S: SpriteSet, rng, x0, x1):
    w = x1 - x0
    top = BASE - GROUND_FLOOR - 2 * STORY - 16
    # glazed black tile facade
    rect(L.alb, x0, top, w, BASE - top, TILE_BLACK)
    for yy in range(top, BASE, 5):
        hline(L.alb, x0, x1 - 1, yy, TILE_EDGE)
    for xx in range(x0, x1, 9):
        vline(L.alb, xx, top, BASE - 1, TILE_EDGE)
    noise_tint(L.alb, pygame.Rect(x0, top, w, BASE - top), rng, 0.06)
    # gold deco pilasters and stepped parapet
    for xx in (x0 + 2, x0 + 60, x1 - 64, x1 - 6):
        rect(L.alb, xx, top, 4, BASE - top - GROUND_FLOOR, P.DECO_GOLD)
        vline(L.alb, xx, top, BASE - GROUND_FLOOR - 1, shade(P.DECO_GOLD, 1.3))
        vline(L.alb, xx + 3, top, BASE - GROUND_FLOOR - 1, shade(P.DECO_GOLD, 0.6))
    for k, (dw, dh) in enumerate(((w, 4), (w - 60, 8), (w - 130, 12))):
        rect(L.alb, x0 + (w - dw) // 2, top - dh, dw, dh, TILE_BLACK if k else P.DECO_GOLD)
        hline(L.alb, x0 + (w - dw) // 2, x0 + (w + dw) // 2 - 1, top - dh, P.DECO_GOLD)
    # tall upper windows (dancers move in two of them at runtime)
    gy = BASE - GROUND_FLOOR
    win_xs = [x0 + 18, x0 + 38, x0 + 80, x0 + 104, x0 + 128, x0 + 152, x0 + 176, x1 - 54, x1 - 34]
    for r in range(2):
        wy = gy - 30 - r * STORY
        for i, wx in enumerate(win_xs):
            st = "warm" if (i + r) % 3 != 0 else "shade"
            env.sash_window(L, rng, wx, wy, 11, 22, st, frame=P.DECO_GOLD, curtain=True)
            if r == 0 and i in (3, 5):
                L.meta["props"].append({"kind": "dancers", "x": wx, "y": wy, "w": 11, "h": 22, "phase": i * 0.37})
    # ground floor: entrance
    rect(L.alb, x0, gy, w, GROUND_FLOOR, shade(TILE_BLACK, 0.85))
    hline(L.alb, x0, x1 - 1, gy, P.DECO_GOLD)
    dc = x0 + w // 2
    rect(L.alb, dc - 22, gy + 6, 44, GROUND_FLOOR - 6, P.INK_WARM)
    for side in (-1, 1):
        dx = dc - 20 if side < 0 else dc + 1
        rect(L.alb, dx, gy + 8, 19, GROUND_FLOOR - 8, P.VELVET)
        rect(L.alb, dx + 1, gy + 9, 17, GROUND_FLOOR - 10, shade(P.VELVET, 1.15))
        pygame.draw.circle(L.alb, P.BRASS, (dx + 9, gy + 18), 5)
        pygame.draw.circle(L.emi, P.WINDOW_WARM, (dx + 9, gy + 18), 4)
        pygame.draw.circle(L.alb, shade(P.CREAM, 0.6), (dx + 9, gy + 18), 4)
        vline(L.alb, dx + (17 if side < 0 else 1), gy + 24, gy + 32, P.BRASS)
    L.anchor("velour_door", dc, BASE + 6)
    L.light(dc, BASE + 4, 60, P.L_BULB, 0.35)
    # poster cases
    for pxx in (dc - 76, dc + 50):
        rect(L.alb, pxx - 1, gy + 5, 28, 32, P.DECO_GOLD)
        rect(L.alb, pxx + 1, gy + 7, 24, 28, P.POSTER_PAPER)
        rect(L.emi, pxx + 1, gy + 7, 24, 28, shade(P.WINDOW_WARM, 0.35))
        # poster art: a singer silhouette against a crescent
        pygame.draw.circle(L.alb, shade(P.NEON_MAGENTA, 0.55), (pxx + 13, gy + 16), 7)
        pygame.draw.circle(L.alb, P.POSTER_PAPER, (pxx + 16, gy + 14), 6)
        pygame.draw.ellipse(L.alb, P.INK, pygame.Rect(pxx + 9, gy + 15, 6, 6))
        poly(L.alb, [(pxx + 8, gy + 34), (pxx + 12, gy + 20), (pxx + 14, gy + 20), (pxx + 19, gy + 34)], P.INK)
        hline(L.alb, pxx + 4, pxx + 22, gy + 30, P.CURTAIN_RED)
    # canopy with chasing bulbs (runtime prop) and VELOUR neon above
    cw = 100
    cx0 = dc - cw // 2
    alb, emi = surf(cw, 14), surf(cw, 14)
    rect(alb, 0, 0, cw, 10, P.INK_WARM)
    rect(alb, 0, 0, cw, 2, P.DECO_GOLD)
    rect(alb, 0, 8, cw, 2, P.DECO_GOLD)
    for i in range(2, cw - 2, 4):
        px(alb, i, 5, P.BULB_DIM)
    key = S.add("velour_canopy", alb, emi)
    L.meta["props"].append({"kind": "chase", "sprite": key, "x": cx0, "y": gy - 12, "bulbs_y": 5,
                            "bulbs_x": list(range(2, cw - 2, 4)), "color": list(P.BULB),
                            "light": {"dx": cw / 2, "dy": 40, "radius": 80, "color": list(P.L_BULB), "intensity": 0.5}})
    key, sw, sh = big_neon(S, "velour_sign", "VELOUR", P.NEON_MAGENTA, frame_color=P.NEON_CYAN, scale=2, pad=4,
                           board=shade(TILE_BLACK, 0.7))
    env.add_sign_prop(L, key, dc - sw // 2, top - 6 - sh + 26, sw, sh, "steady", P.L_MAGENTA, radius=120,
                      intensity=0.5, light_dy=sh + 70)
    # velvet rope posts become runtime props
    L.meta["props"].append({"kind": "rope", "x": dc - 38, "y": BASE + 14, "w": 22})
    L.meta["props"].append({"kind": "rope", "x": dc + 16, "y": BASE + 14, "w": 22})
    env.grime_bottom(L, x0, BASE - 10, w, 10, 0.35)


def pawn(L: Layers, S: SpriteSet, rng, x0, x1):
    w = x1 - x0
    brick_wall(L.alb, x0, 0, w, BASE, P.BRICK_BROWN, P.MORTAR, rng, bw=8, bh=3)
    noise_tint(L.alb, pygame.Rect(x0, 0, w, BASE), rng, 0.05, scale=2)
    gy = BASE - GROUND_FLOOR
    cornice(L, x0, gy - 4, w, P.STONE_DARK)
    for r in range(4):
        wy = gy - 26 - r * STORY
        for wx in range(x0 + 12, x1 - 10, 26):
            env.sash_window(L, rng, wx, wy, 10, 17, ["dark", "dim", "dark", "warm"][int(rng.integers(0, 4))], frame=P.STONE)

    def display(L_, x, y, ww, hh):
        # a trumpet, a clock and a row of watches behind bars
        line(L_.emi, x + 4, y + 18, x + 16, y + 14, shade(P.BRASS, 0.9))
        pygame.draw.circle(L_.emi, shade(P.BRASS, 0.9), (x + 18, y + 13), 3)
        pygame.draw.circle(L_.emi, shade(P.CREAM, 0.6), (x + 32, y + 10), 5)
        line(L_.emi, x + 32, y + 10, x + 32, y + 7, P.INK)
        for i in range(5):
            px(L_.emi, x + 26 + i * 4, y + 20, shade(P.BRASS, 1.2))
        for bx in range(x + 2, x + ww, 5):
            vline(L_.alb, bx, y, y + hh - 1, P.IRON)
            vline(L_.emi, bx, y, y + hh - 1, (0, 0, 0, 255))

    env.storefront(L, rng, x0 + 8, gy + 8, 50, 26, frame=P.WOOD_DARK, glow=P.WINDOW_DIM, display=display)
    env.door(L, x0 + 68, gy + 12, 16, 28, P.WOOD_DARK, lit=P.WINDOW_DIM)
    L.anchor("pawn_door", x0 + 76, BASE + 6)
    key, sw, sh = env.neon_text_sign(S, "loans", "LOANS", P.NEON_GREEN)
    env.add_sign_prop(L, key, x0 + 14, gy - 2, sw, sh, "buzz", P.L_GREEN, radius=60, intensity=0.6, light_dy=50)
    # three balls
    for i, (bx, by) in enumerate(((x1 - 14, gy - 26), (x1 - 19, gy - 18), (x1 - 9, gy - 18))):
        pygame.draw.circle(L.alb, shade(P.BRASS, 0.7), (bx, by), 3)
        pygame.draw.circle(L.emi, shade(P.NEON_AMBER, 0.55), (bx, by), 2)
    hline(L.alb, x1 - 20, x1 - 4, gy - 31, P.IRON)
    env.grime_bottom(L, x0, BASE - 16, w, 16)


def marquee(L: Layers, S: SpriteSet, rng, x0, x1):
    w = x1 - x0
    top = BASE - GROUND_FLOOR - 70
    rect(L.alb, x0, top, w, BASE - top, P.STONE)
    noise_tint(L.alb, pygame.Rect(x0, top, w, BASE - top), rng, 0.05, scale=2)
    # stepped deco crown
    for k, (dw, dh) in enumerate(((w, 5), (w - 80, 10), (w - 190, 18))):
        rect(L.alb, x0 + (w - dw) // 2, top - dh, dw, dh, shade(P.STONE, 0.95 - 0.05 * k))
        hline(L.alb, x0 + (w - dw) // 2, x0 + (w + dw) // 2 - 1, top - dh, shade(P.STONE, 1.2))
    # fluted pilasters
    for xx in range(x0 + 6, x1 - 4, 34):
        rect(L.alb, xx, top, 6, BASE - top - GROUND_FLOOR, shade(P.STONE, 1.05))
        for f in range(0, 6, 2):
            vline(L.alb, xx + f, top + 2, BASE - GROUND_FLOOR - 2, shade(P.STONE, 0.82))
    # tall deco window grid (dark, dusty)
    for wx in range(x0 + 16, x1 - 20, 34):
        rect(L.alb, wx, top + 12, 20, 44, P.STONE_DARK)
        rect(L.alb, wx + 2, top + 14, 16, 40, P.GLASS)
        for gy_ in range(top + 14, top + 54, 6):
            hline(L.alb, wx + 2, wx + 17, gy_, P.STONE_DARK)
        vline(L.alb, wx + 9, top + 14, top + 53, P.STONE_DARK)
        dither_rect(L.alb, wx + 2, top + 14, 16, 40, P.GLASS, shade(P.GLASS, 1.4), 0.15)
    gy = BASE - GROUND_FLOOR
    rect(L.alb, x0, gy, w, GROUND_FLOOR, P.STONE_DARK)
    hline(L.alb, x0, x1 - 1, gy, shade(P.STONE, 1.2))
    # boarded entrance
    ec = x0 + w // 2 - 4
    rect(L.alb, ec - 50, gy + 6, 100, GROUND_FLOOR - 6, P.INK)
    for i, bx in enumerate(range(ec - 48, ec + 48, 24)):
        rect(L.alb, bx, gy + 8, 22, GROUND_FLOOR - 8, P.WOOD_DARK)
        for k in range(3):
            yy = gy + 12 + k * 9 + int(rng.integers(-1, 2))
            rect(L.alb, bx - 1, yy, 24, 4, P.WOOD_PLANK)
            hline(L.alb, bx - 1, bx + 22, yy, shade(P.WOOD_PLANK, 1.2))
            px(L.alb, bx + 1, yy + 1, P.IRON_LIGHT)
            px(L.alb, bx + 20, yy + 1, P.IRON_LIGHT)
    # marquee board with missing letters
    mb_x, mb_w = ec - 70, 140
    rect(L.alb, mb_x, gy - 22, mb_w, 22, shade(P.STONE, 0.6))
    rect(L.alb, mb_x + 3, gy - 19, mb_w - 6, 16, P.CREAM)
    msg = "CL S D  F R  RENOV TI N"
    tw = text_width(GLYPHS, msg, 1)
    blit_text(L.alb, GLYPHS, msg, mb_x + (mb_w - tw) // 2, gy - 15, P.INK, gap=1)
    bulbs = list(range(mb_x + 2, mb_x + mb_w - 2, 5))
    for bx in bulbs:
        px(L.alb, bx, gy - 21, P.BULB_DIM)
        px(L.alb, bx, gy - 2, P.BULB_DIM)
    # a handful of bulbs still burn
    for bx in bulbs[::7]:
        px(L.emi, bx, gy - 21, shade(P.BULB, 0.8))
    # torn posters in the side cases
    for pxx in (ec - 92, ec + 66):
        rect(L.alb, pxx, gy + 6, 24, 30, P.STONE)
        rect(L.alb, pxx + 2, gy + 8, 20, 26, P.POSTER_PAPER)
        poly(L.alb, [(pxx + 2, gy + 20), (pxx + 12, gy + 34), (pxx + 2, gy + 34)], P.INK)
        poly(L.alb, [(pxx + 6, gy + 10), (pxx + 18, gy + 10), (pxx + 12, gy + 22)], shade(P.CURTAIN_RED, 0.8))
        hline(L.alb, pxx + 4, pxx + 18, gy + 26, P.INK)
    # dead vertical MARQUEE sign; a few letters still flicker
    key, bw, bh = bulb_letters_vertical(S, "marquee_blade", "MARQUEE", [False, False, False, False, True, True, False])
    env.add_sign_prop(L, key, ec - bw // 2 - 1, top - 34, bw, bh, "dying", P.L_BULB, radius=60, intensity=0.5,
                      light_dy=bh // 2)
    # the boarded SIDE door with projector light leaking between the planks
    sx = x1 - 40
    rect(L.alb, sx - 2, gy + 4, 24, GROUND_FLOOR - 4, shade(P.STONE, 0.7))
    rect(L.alb, sx, gy + 6, 20, GROUND_FLOOR - 6, P.INK)
    L.anchor("marquee_side_door", sx + 10, BASE + 6)
    L.meta["props"].append({"kind": "boarded_door", "x": sx, "y": gy + 6, "w": 20, "h": GROUND_FLOOR - 6,
                            "id": "marquee_side", "pattern": "projector",
                            "light": {"dx": 10, "dy": GROUND_FLOOR + 2, "radius": 46, "color": [0.7, 0.78, 1.0],
                                      "intensity": 0.55}})
    blit_text(L.alb, GLYPHS, "STAFF", sx + 1, gy - 6, shade(P.STONE, 0.6), gap=0)
    env.grime_bottom(L, x0, BASE - 14, w, 14, 0.45)


def diner(L: Layers, S: SpriteSet, rng, x0, x1):
    w = x1 - x0
    top = BASE - GROUND_FLOOR - STORY - 10
    base_col = hexc("5e6a62")
    rect(L.alb, x0, top, w, BASE - top, base_col)
    noise_tint(L.alb, pygame.Rect(x0, top, w, BASE - top), rng, 0.05, scale=2)
    rect(L.alb, x0, top, w, 4, shade(base_col, 1.25))
    for wx in range(x0 + 14, x1 - 14, 24):
        env.sash_window(L, rng, wx, top + 12, 11, 15, "dim" if rng.random() < 0.5 else "dark", frame=P.CREAM)
    gy = BASE - GROUND_FLOOR
    rect(L.alb, x0, gy - 3, w, 3, P.CREAM)
    # huge lit window with counter, stools and a cook
    wx0, ww = x0 + 10, 104
    env.storefront(L, rng, wx0, gy + 4, ww, 26, frame=P.IRON_LIGHT, glow=mix(P.WINDOW_WARM, P.CREAM, 0.45))
    rect(L.emi, wx0, gy + 20, ww, 10, shade(P.WINDOW_WARM, 0.5))  # counter
    hline(L.emi, wx0, wx0 + ww - 1, gy + 20, shade(P.CREAM, 0.8))
    for sx in range(wx0 + 6, wx0 + ww - 4, 12):
        rect(L.emi, sx, gy + 27, 4, 3, shade(P.NEON_RED, 0.4))
    cook = wx0 + 70
    pygame.draw.ellipse(L.emi, shade(P.WINDOW_WARM, 0.25), pygame.Rect(cook - 3, gy + 8, 7, 7))
    rect(L.emi, cook - 4, gy + 14, 9, 7, shade(P.CREAM, 0.6))
    # a lone customer at the counter
    pygame.draw.ellipse(L.emi, shade(P.WINDOW_WARM, 0.2), pygame.Rect(wx0 + 24, gy + 13, 6, 6))
    rect(L.emi, wx0 + 23, gy + 18, 8, 6, shade(P.WINDOW_WARM, 0.2))
    L.light(wx0 + ww // 2, BASE + 14, 95, (1.0, 0.85, 0.65), 0.75)
    env.door(L, x0 + 124, gy + 10, 18, 30, P.IRON, lit=mix(P.WINDOW_WARM, P.CREAM, 0.45))
    L.anchor("diner_door", x0 + 133, BASE + 6)
    key, sw, sh = env.neon_text_sign(S, "allnight", "ALL NIGHT", P.NEON_CYAN)
    env.add_sign_prop(L, key, wx0 + 18, gy - 15, sw, sh, "steady", P.L_CYAN, radius=70, intensity=0.6, light_dy=50)
    blit_text(L.alb, GLYPHS, "ORSOLYA'S", x0 + 96, top + 31, P.CURTAIN_RED, gap=1)
    env.grime_bottom(L, x0, BASE - 10, w, 10, 0.3)


def garage(L: Layers, S: SpriteSet, rng, x0, x1):
    w = x1 - x0
    brick_wall(L.alb, x0, 0, w, BASE, P.BRICK_DARK, P.MORTAR, rng, bw=8, bh=3)
    noise_tint(L.alb, pygame.Rect(x0, 0, w, BASE), rng, 0.06, scale=2)
    gy = BASE - GROUND_FLOOR
    for r in range(4):
        wy = gy - 26 - r * STORY
        for wx in range(x0 + 14, x1 - 10, 30):
            env.sash_window(L, rng, wx, wy, 12, 16, "dark" if rng.random() < 0.8 else "dim", frame=P.STONE_DARK)
    rx = x0 + 20
    rect(L.alb, rx - 3, gy + 2, 86, GROUND_FLOOR - 2, P.STONE_DARK)
    for yy in range(gy + 4, BASE, 3):
        hline(L.alb, rx, rx + 79, yy, P.IRON_LIGHT if yy % 6 else P.IRON)
    key, sw, sh = env.neon_text_sign(S, "parking", "PARKING", P.NEON_AMBER, board=P.IRON)
    env.add_sign_prop(L, key, rx + 12, gy - 16, sw, sh, "dying", (1.0, 0.65, 0.25), radius=55, intensity=0.5, light_dy=45)
    env.grime_bottom(L, x0, BASE - 20, w, 20, 0.6)


def alley_gap(L: Layers, rng, x0, x1, name: str):
    w = x1 - x0
    # receding wet cobbles fading into darkness
    for y in range(60, BASE):
        t = (y - 60) / (BASE - 60)
        c = mix(P.INK, shade(P.ASPHALT, 0.8), t ** 1.5)
        hline(L.alb, x0, x1 - 1, y, c)
    for y in range(64, BASE, 4):
        for x in range(x0 + (y // 4) % 2 * 3, x1, 6):
            px(L.alb, x, y, shade(L.alb.get_at((x, y)), 0.7))
    rect(L.alb, x0, 0, w, 60, P.INK)
    vline(L.alb, x0, 0, BASE, shade(P.INK, 1.6))
    vline(L.alb, x1 - 1, 0, BASE, shade(P.INK, 1.6))
    L.wet(x0, 60, w, BASE - 60, 0.7, None)
    # distant dim bulb deep in the alley
    pygame.draw.circle(L.emi, shade(P.BULB, 0.6), (x0 + w // 2 + 4, 70), 1)
    L.light(x0 + w // 2 + 4, 84, 40, P.L_BULB, 0.35)
    L.anchor(f"{name}_mouth", x0 + w // 2, BASE + 4)
    L.anchor(f"{name}_exit", x0 + w // 2, 96)


# ----------------------------------------------------------------------------- foreground
def elevated_line(F: Layers, rng):
    deck_y0, deck_y1 = 236, 252
    steel = hexc("2f343b")
    steel_l = hexc("4a5159")
    rect(F.alb, 0, deck_y0, W, deck_y1 - deck_y0, steel)
    hline(F.alb, 0, W - 1, deck_y0, steel_l)
    hline(F.alb, 0, W - 1, deck_y0 + 1, shade(steel_l, 0.85))
    hline(F.alb, 0, W - 1, deck_y1 - 1, shade(steel, 0.6))
    # lattice girder
    for x in range(0, W, 12):
        line(F.alb, x, deck_y0 + 3, x + 6, deck_y1 - 3, steel_l)
        line(F.alb, x + 6, deck_y1 - 3, x + 12, deck_y0 + 3, steel_l)
    for x in range(0, W, 6):
        px(F.alb, x, deck_y0 + 2, hexc("6a727c"))
        px(F.alb, x + 3, deck_y1 - 2, hexc("6a727c"))
    # ties on top of the deck
    for x in range(0, W, 5):
        rect(F.alb, x, deck_y0 - 3, 3, 3, P.WOOD_DARK)
    hline(F.alb, 0, W - 1, deck_y0 - 4, P.RAIL_DARK)
    # pillars
    for x in range(100, W, 240):
        rect(F.alb, x - 4, deck_y1, 9, H - deck_y1, steel)
        vline(F.alb, x - 4, deck_y1, H - 1, steel_l)
        vline(F.alb, x + 4, deck_y1, H - 1, shade(steel, 0.6))
        for y in range(deck_y1 + 4, H, 8):
            px(F.alb, x - 2, y, hexc("6a727c"))
            px(F.alb, x + 2, y, hexc("6a727c"))
        rect(F.alb, x - 6, H - 5, 13, 5, shade(steel, 0.8))
        # knee braces
        line(F.alb, x - 4, deck_y1 + 8, x - 14, deck_y1, steel)
        line(F.alb, x + 4, deck_y1 + 8, x + 14, deck_y1, steel)
    F.wet(0, deck_y0 - 4, W, H - deck_y0 + 4, 0.0)


def el_bulbs(L: Layers, F: Layers):
    """Caged work-lights hanging under the El at every pillar."""
    for i, x in enumerate(range(100, W, 240)):
        for side in (-1, 1):
            bx = x + side * 22
            vline(F.alb, bx, 252, 255, hexc("2f343b"))
            rect(F.alb, bx - 1, 256, 3, 4, P.IRON)
            rect(F.emi, bx - 1, 257, 3, 2, P.BULB)
            px(F.emi, bx, 257, shade(P.BULB, 1.3))
            pattern = "buzz" if (i + (side > 0)) % 3 == 0 else None
            L.light(bx, 268, 78, P.L_BULB, 0.95, flicker=pattern)


def pillar_colliders(L: Layers):
    for x in range(100, W, 240):
        L.collider(x - 6, H - 8, 13, 8)


# ----------------------------------------------------------------------------- props (runtime sprites)
def lamp_sprite(S: SpriteSet) -> str:
    w, h = 11, 54
    alb, emi = surf(w, h), surf(w, h)
    iron = hexc("23262c")
    hl = hexc("4b525c")
    rect(alb, 3, h - 5, 5, 5, iron)  # base
    rect(alb, 2, h - 2, 7, 2, iron)
    rect(alb, 4, 10, 3, h - 14, iron)
    vline(alb, 4, 10, h - 6, hl)
    for y in (18, 30):
        rect(alb, 3, y, 5, 2, iron)
    # lantern head
    poly(alb, [(1, 3), (9, 3), (8, 10), (2, 10)], iron)
    rect(alb, 3, 4, 5, 5, P.BULB_DIM)
    rect(emi, 3, 4, 5, 5, P.SODIUM)
    rect(emi, 4, 5, 3, 3, shade(P.SODIUM, 1.4))
    poly(alb, [(0, 3), (5, 0), (10, 3)], iron)
    return S.add("lamp", alb, emi)


def wagon_sprite(S: SpriteSet) -> str:
    """The city morgue's panel wagon, seen from the side, facing east."""
    w, h = 76, 34
    alb, emi = surf(w, h), surf(w, h)
    body = hexc("26292e")
    body_l = hexc("3c4148")
    chrome = hexc("9aa2ac")
    # body
    poly(alb, [(4, 12), (50, 12), (58, 4), (66, 4), (72, 14), (74, 24), (2, 24)], body)
    rect(alb, 2, 12, 50, 13, body)
    hline(alb, 4, 50, 12, body_l)
    line(alb, 51, 12, 58, 4, body_l)
    hline(alb, 58, 66, 4, body_l)
    # windshield + side window
    poly(alb, [(53, 13), (59, 6), (65, 6), (68, 13)], P.GLASS)
    px(alb, 60, 7, P.GLASS_LIGHT)
    px(alb, 61, 8, P.GLASS_LIGHT)
    # lettering
    blit_text(alb, GLYPHS, "CITY MORGUE", 6, 14, shade(P.CREAM, 0.75), gap=1)
    # trim, bumper, lamps
    hline(alb, 2, 74, 22, chrome)
    rect(alb, 70, 18, 4, 3, P.BULB_DIM)
    rect(alb, 0, 16, 2, 3, shade(P.NEON_RED, 0.4))
    rect(emi, 0, 16, 2, 3, shade(P.NEON_RED, 0.5))
    # wheels
    for wx in (14, 60):
        pygame.draw.circle(alb, P.INK, (wx, 25), 7)
        pygame.draw.circle(alb, hexc("2a2b2e"), (wx, 25), 5)
        pygame.draw.circle(alb, chrome, (wx, 25), 2)
        poly(alb, [(wx - 9, 20), (wx + 9, 20), (wx + 7, 15), (wx - 7, 15)], body)
    out = outline(alb, P.INK)
    emi2 = surf(w + 2, h + 2)
    emi2.blit(emi, (1, 1))
    return S.add("wagon", out, emi2)


def props_misc(S: SpriteSet) -> dict:
    keys = {}
    # trash can
    alb = surf(10, 13)
    rect(alb, 1, 2, 8, 11, hexc("4a4d52"))
    for x in (2, 4, 6):
        vline(alb, x, 3, 12, hexc("5c6067"))
    rect(alb, 0, 1, 10, 2, hexc("5c6067"))
    rect(alb, 3, 0, 4, 1, hexc("5c6067"))
    keys["trashcan"] = S.add("trashcan", outline(alb, P.INK))
    # hydrant
    alb = surf(8, 11)
    rect(alb, 2, 2, 4, 8, hexc("7a2a26"))
    rect(alb, 1, 4, 6, 2, hexc("7a2a26"))
    rect(alb, 2, 1, 4, 1, hexc("9a3a30"))
    rect(alb, 1, 10, 6, 1, hexc("5a1f1c"))
    vline(alb, 3, 2, 9, hexc("a04a3a"))
    keys["hydrant"] = S.add("hydrant", outline(alb, P.INK))
    # phone booth
    alb, emi = surf(16, 40), surf(16, 40)
    rect(alb, 0, 2, 16, 38, hexc("2d3a34"))
    rect(alb, 2, 6, 12, 28, P.GLASS)
    for j in range(28):
        hline(emi, 2, 13, 6 + j, shade(P.WINDOW_COOL, 0.25 + 0.2 * j / 27))
    rect(alb, 0, 0, 16, 3, hexc("3c4c44"))
    blit_text(alb, GLYPHS, "TEL", 3, -1 + 1, shade(P.CREAM, 0.8), gap=0)
    rect(emi, 6, 14, 4, 6, shade(P.INK, 1.0))
    vline(alb, 8, 6, 33, hexc("2d3a34"))
    keys["phonebooth"] = S.add("phonebooth", outline(alb, P.INK), _pad(emi))
    # rope post
    alb = surf(4, 12)
    rect(alb, 1, 2, 2, 9, P.BRASS)
    rect(alb, 0, 0, 4, 2, shade(P.BRASS, 1.2))
    rect(alb, 0, 10, 4, 2, shade(P.BRASS, 0.7))
    keys["ropepost"] = S.add("ropepost", alb)
    # newspaper box
    alb = surf(9, 12)
    rect(alb, 0, 0, 9, 12, hexc("3d4f6a"))
    rect(alb, 1, 2, 7, 4, P.POSTER_PAPER)
    hline(alb, 2, 6, 3, P.INK)
    hline(alb, 2, 5, 5, P.INK)
    keys["newsbox"] = S.add("newsbox", outline(alb, P.INK))
    return keys


def train_car(S: SpriteSet) -> str:
    w, h = 96, 30
    alb, emi = surf(w, h), surf(w, h)
    body = hexc("3a2e2a")
    body_l = hexc("564640")
    roof = hexc("2a2422")
    rect(alb, 0, 4, w, h - 8, body)
    rect(alb, 2, 0, w - 4, 5, roof)
    hline(alb, 2, w - 3, 4, body_l)
    rect(alb, 0, h - 6, w, 3, hexc("22201e"))
    for wx in range(6, w - 8, 12):
        rect(alb, wx, 9, 8, 9, P.GLASS)
        rect(emi, wx, 9, 8, 9, shade(P.WINDOW_WARM, 0.9))
        rect(alb, wx, 9, 8, 9, shade(P.CREAM, 0.6))
    # passengers: heads and hats as dark shapes against the window light
    rng = np.random.default_rng(7)
    for wx in range(6, w - 8, 12):
        if rng.random() < 0.65:
            hx = wx + int(rng.integers(1, 5))
            rect(emi, hx, 13, 3, 5, (40, 26, 18, 255))
            rect(emi, hx - 1, 18, 5, 0, (40, 26, 18, 255))
            if rng.random() < 0.4:
                rect(emi, hx - 1, 12, 5, 1, (30, 20, 14, 255))
    rect(alb, w // 2 - 3, 7, 6, 14, shade(body, 0.8))  # door
    blit_text(alb, GLYPHS, "CORVANE", 4, 20, shade(P.CREAM, 0.45), gap=1)
    for bx in (10, w - 18):
        rect(alb, bx, h - 4, 8, 4, hexc("1a1816"))
    return S.add("train_car", outline(alb, P.INK), _pad(emi))


def _pad(s: pygame.Surface) -> pygame.Surface:
    out = surf(s.get_width() + 2, s.get_height() + 2)
    out.blit(s, (1, 1))
    return out


# ----------------------------------------------------------------------------- bake entry
def bake(seed: int = 1931):
    rng = np.random.default_rng(seed)
    S = SpriteSet("row")
    L = Layers(W, H)
    # sky + distant skyline (only visible above low buildings)
    vgrad_dither(L.alb, 0, 0, W, 70, hexc("0d0f18"), hexc("1a1d2a"), steps=5)
    env.skyline(L, rng, 0, W, 66, max_h=56)
    tenement(L, S, rng, 0, 232)
    alley_gap(L, rng, 232, 268, "alley_a")
    hotel(L, S, rng, 268, 430)
    velour(L, S, rng, 430, 700)
    pawn(L, S, rng, 700, 800)
    marquee(L, S, rng, 800, 1110)
    alley_gap(L, rng, 1110, 1146, "alley_b")
    diner(L, S, rng, 1146, 1300)
    garage(L, S, rng, 1300, W)
    # ground
    env.ground_street(L, rng, 0, W, LAYOUT)
    for x in (238, 760, 1210):
        env.manhole(L, x, 214)
        L.meta["props"].append({"kind": "steam", "x": x + 7, "y": 216})
    # shelter from the El: drier, darker sidewalk
    for y in range(251, H):
        for x in range(W):
            if BAYER4[y % 4, x % 4] < 0.45:
                L.alb.set_at((x, y), shade(L.alb.get_at((x, y)), 0.7))
    L.wet(0, 254, W, H - 254, 0.14, BASE)

    # colliders: facades (with alley openings), bottom edge and pillar feet
    for x0, x1 in ((0, 232), (268, 1110), (1146, W)):
        L.collider(x0, 0, x1 - x0, BASE + 1)
    for x0, x1 in ((232, 268), (1110, 1146)):
        L.collider(x0, 0, x1 - x0, 92)
        L.collider(x0 - 2, 92, 4, 57)
        L.collider(x1 - 2, 92, 4, 57)
    L.collider(-20, 0, 20, H)
    L.collider(W, 0, 20, H)
    L.collider(0, H - 2, W, 4)
    pillar_colliders(L)

    # runtime props
    lamp = lamp_sprite(S)
    for i, x in enumerate((70, 330, 640, 870, 1185, 1395)):
        flicker = "dying" if x == 870 else ("buzz" if i == 4 else "steady")
        L.meta["props"].append({"kind": "lamp", "sprite": lamp, "x": x - 5, "y": 174 - 54, "base_y": 174,
                                "flicker": flicker,
                                "light": {"dx": 5, "dy": 50, "radius": 88, "color": list(P.L_SODIUM), "intensity": 1.05}})
        L.collider(x - 2, 170, 5, 4)
    misc = props_misc(S)
    placements = [("trashcan", 220, 162), ("trashcan", 272, 166), ("trashcan", 1150, 164), ("hydrant", 818, 170),
                  ("phonebooth", 680, 168), ("newsbox", 1290, 168), ("trashcan", 1104, 162)]
    for kind, x, base_y in placements:
        L.meta["props"].append({"kind": "static", "sprite": misc[kind], "x": x, "base_y": base_y})
        w = {"trashcan": 10, "hydrant": 8, "phonebooth": 16, "newsbox": 9}[kind]
        L.collider(x, base_y - 4, w + 2, 5)
    L.meta["props"].append({"kind": "static", "sprite": wagon_sprite(S), "x": 120, "base_y": 196, "id": "wagon"})
    L.collider(124, 186, 70, 10, "wagon")
    L.anchor("wagon_side", 160, 204)
    L.meta["ropepost"] = misc["ropepost"]
    train_car(S)

    F = Layers(W, H, opaque=False)
    elevated_line(F, rng)
    el_bulbs(L, F)
    return {"bg": L, "fg": F, "sprites": S, "size": (W, H)}
