"""Reusable environment-art building blocks (facades, windows, signs, ground).

Every function draws into a `Layers` bundle: albedo + emissive + material,
and may register runtime metadata (lights, animated props, colliders, anchors).
"""
from __future__ import annotations

import math
import os

import numpy as np
import pygame

from . import palette as P
from .font_data import GLYPHS
from .gfx import (BAYER4, blit_text, brick_wall, dither_rect, hline, line, mix, noise_tint, outline, poly, px, rect,
                  shade, surf, text_width, vgrad_dither, vline, with_alpha)


class Layers:
    """Albedo/emissive/material canvases plus runtime metadata for one baked layer set."""

    def __init__(self, w: int, h: int, opaque: bool = True):
        self.w, self.h = w, h
        self.alb = surf(w, h)
        if opaque:
            self.alb.fill((0, 0, 0, 255))
        self.emi = surf(w, h)
        self.emi.fill((0, 0, 0, 255 if opaque else 0))
        self.mat = surf(w, h)
        self.mat.fill((0, 0, 0, 255 if opaque else 0))
        self.meta: dict = {"lights": [], "props": [], "colliders": [], "anchors": {}, "sprites": {}}

    # material helpers ---------------------------------------------------------
    def wet(self, x, y, w, h, wetness: float, mirror_y: int | None = None, mask: pygame.Surface | None = None) -> None:
        r = pygame.Rect(int(x), int(y), int(w), int(h)).clip(self.mat.get_rect())
        if r.w <= 0 or r.h <= 0:
            return
        arr = pygame.surfarray.pixels3d(self.mat)
        al = pygame.surfarray.pixels_alpha(self.mat)
        sub = arr[r.x:r.x + r.w, r.y:r.y + r.h]
        if mask is not None:
            m = pygame.surfarray.array_alpha(mask)[: r.w, : r.h] > 0
        else:
            m = np.ones((r.w, r.h), bool)
        sub[..., 0][m] = int(max(0, min(1, wetness)) * 255)
        if mirror_y is None:
            sub[..., 1][m] = 0
        else:
            ys = np.arange(r.y, r.y + r.h)[None, :].repeat(r.w, 0)
            d = np.clip(ys - mirror_y, 0, 255).astype(np.uint8)
            sub[..., 1][m] = d[m]
        al[r.x:r.x + r.w, r.y:r.y + r.h][m] = 255
        del arr, al

    def light(self, x, y, radius, color, intensity=1.0, name=None, flicker=None, **kw) -> dict:
        d = {"x": x, "y": y, "radius": radius, "color": list(color), "intensity": intensity}
        if name:
            d["name"] = name
        if flicker:
            d["flicker"] = flicker
        d.update(kw)
        self.meta["lights"].append(d)
        return d

    def collider(self, x, y, w, h, tag: str | None = None) -> None:
        c = [int(x), int(y), int(w), int(h)]
        if tag:
            c.append(tag)
        self.meta["colliders"].append(c)

    def anchor(self, name: str, x, y) -> None:
        self.meta["anchors"][name] = [int(x), int(y)]


class SpriteSet:
    """Collects small runtime sprites (albedo+emissive pairs) produced while baking."""

    def __init__(self, area_id: str):
        self.area_id = area_id
        self.items: dict[str, tuple[pygame.Surface, pygame.Surface | None]] = {}

    def add(self, name: str, alb: pygame.Surface, emi: pygame.Surface | None = None) -> str:
        key = f"{self.area_id}/{name}"
        self.items[key] = (alb, emi)
        return key

    def save(self, out_dir: str) -> list[str]:
        files = []
        for key, (alb, emi) in self.items.items():
            base = os.path.join(out_dir, key.replace("/", os.sep))
            os.makedirs(os.path.dirname(base), exist_ok=True)
            pygame.image.save(alb, base + "_alb.png")
            files.append(base + "_alb.png")
            if emi is not None:
                pygame.image.save(emi, base + "_emi.png")
                files.append(base + "_emi.png")
        return files


# ---------------------------------------------------------------------------- grime
def grime_bottom(L: Layers, x, y_top, w, h, strength=0.55):
    """Dark dithered gradient (soot / splash-back) rising from the ground."""
    for j in range(h):
        t = (j / max(1, h - 1)) ** 1.6 * strength
        yy = y_top + j
        for i in range(w):
            if BAYER4[yy % 4, (x + i) % 4] < t:
                c = L.alb.get_at((x + i, yy))
                L.alb.set_at((x + i, yy), shade(c, 0.72))


def rain_streaks(L: Layers, x, y, w, h, rng, count=6, alpha=0.18):
    for _ in range(count):
        sx = int(rng.integers(x, x + w))
        sy = int(rng.integers(y, y + max(1, h // 2)))
        ln = int(rng.integers(6, max(7, h // 2)))
        for k in range(ln):
            yy = sy + k
            if yy >= y + h or yy >= L.h:
                break
            if yy >= 0 and rng.random() < 1 - k / ln * 0.6:
                c = L.alb.get_at((sx, yy))
                L.alb.set_at((sx, yy), shade(c, 1 - alpha))


# ---------------------------------------------------------------------------- windows
def sash_window(L: Layers, rng, x, y, w=10, h=16, state="dark", frame=P.CREAM, sill=True, curtain=None):
    """A double-hung window. state: dark|warm|dim|shade|red|tv|blind."""
    fr = frame
    rect(L.alb, x - 1, y - 1, w + 2, h + 2, shade(fr, 0.8))
    rect(L.alb, x, y, w, h, P.GLASS)
    # dark glass reflection sheen
    if state == "dark":
        for k in range(min(w, h)):
            if k % 3 == 0:
                px(L.alb, x + w - 1 - k // 2, y + k, P.GLASS_LIGHT)
        vline(L.alb, x + 1, y + 1, y + h // 2, P.GLASS_LIGHT)
    else:
        col = {
            "warm": P.WINDOW_WARM, "dim": P.WINDOW_DIM, "shade": P.WINDOW_WARM,
            "red": with_alpha(shade(P.NEON_RED, 0.45), 255), "tv": P.WINDOW_TV, "blind": P.WINDOW_DIM,
        }[state]
        rect(L.emi, x, y, w, h, col)
        # slight vertical falloff toward the top for depth
        for j in range(h):
            f = 0.75 + 0.25 * (j / max(1, h - 1))
            hline(L.emi, x, x + w - 1, y + j, shade(col, f))
        rect(L.alb, x, y, w, h, shade(P.CREAM, 0.6))
        if state == "shade":
            sh = int(h * rng.uniform(0.3, 0.6))
            rect(L.emi, x, y, w, sh, shade(col, 0.5))
            hline(L.emi, x, x + w - 1, y + sh, shade(col, 1.2))
        if state == "blind":
            for j in range(0, h, 2):
                hline(L.emi, x, x + w - 1, y + j, shade(col, 0.4))
        cur = curtain if curtain is not None else (rng.random() < 0.6)
        if cur:
            cw = max(2, w // 3)
            rect(L.emi, x, y, cw, h, shade(col, 0.45))
            rect(L.emi, x + w - cw, y, cw, h, shade(col, 0.45))
            vline(L.emi, x + cw, y, y + h - 1, shade(col, 0.7))
    # mullions
    hline(L.alb, x, x + w - 1, y + h // 2, shade(fr, 0.75))
    hline(L.emi, x, x + w - 1, y + h // 2, (0, 0, 0, 255))
    if w >= 8:
        vline(L.alb, x + w // 2, y, y + h - 1, shade(fr, 0.7))
        vline(L.emi, x + w // 2, y, y + h - 1, (0, 0, 0, 255))
    # lintel and sill
    hline(L.alb, x - 2, x + w + 1, y - 2, shade(fr, 1.05))
    if sill:
        hline(L.alb, x - 2, x + w + 1, y + h + 1, shade(fr, 1.15))
        hline(L.alb, x - 1, x + w, y + h + 2, shade(fr, 0.55))


def storefront(L: Layers, rng, x, y, w, h, frame=P.WOOD_DARK, glow=None, display=None):
    """Large plate-glass shop window; glow is an emissive color for lit interiors."""
    rect(L.alb, x - 2, y - 2, w + 4, h + 4, shade(frame, 0.9))
    rect(L.alb, x - 2, y + h, w + 4, 3, shade(frame, 0.7))  # kick plate
    rect(L.alb, x, y, w, h, P.GLASS)
    if glow is not None:
        for j in range(h):
            f = 0.55 + 0.45 * (j / max(1, h - 1))
            hline(L.emi, x, x + w - 1, y + j, shade(glow, f))
        rect(L.alb, x, y, w, h, shade(P.CREAM, 0.5))
    else:
        # diagonal sheen
        for s in range(h):
            xx = x + (s * 2) % max(1, w)
            px(L.alb, xx, y + s, P.GLASS_LIGHT)
    if display:
        display(L, x, y, w, h)
    vline(L.alb, x + w // 2, y, y + h - 1, shade(frame, 0.8))
    vline(L.emi, x + w // 2, y, y + h - 1, (0, 0, 0, 255))


def door(L: Layers, x, y, w, h, color=P.WOOD_DARK, glass=True, lit=None, frame=None):
    fr = frame or shade(color, 0.7)
    rect(L.alb, x - 2, y - 2, w + 4, h + 2, fr)
    rect(L.alb, x, y, w, h, color)
    # panels
    rect(L.alb, x + 2, y + h // 2 + 2, w - 4, h // 2 - 5, shade(color, 0.85))
    if glass:
        gx, gy, gw, gh = x + 2, y + 3, w - 4, h // 2 - 4
        rect(L.alb, gx, gy, gw, gh, P.GLASS)
        if lit is not None:
            rect(L.emi, gx, gy, gw, gh, lit)
            rect(L.alb, gx, gy, gw, gh, shade(P.CREAM, 0.5))
    px(L.alb, x + w - 3, y + h // 2 + 1, P.BRASS)
    # transom
    rect(L.alb, x, y - 6, w, 4, P.GLASS)
    if lit is not None:
        rect(L.emi, x, y - 6, w, 4, shade(lit, 0.7))


def cornice(L: Layers, x, y, w, color, depth=3):
    rect(L.alb, x - 2, y, w + 4, depth, shade(color, 1.1))
    hline(L.alb, x - 2, x + w + 1, y, shade(color, 1.3))
    hline(L.alb, x - 2, x + w + 1, y + depth, shade(color, 0.5))
    hline(L.alb, x - 1, x + w, y + depth + 1, shade(color, 0.7))
    for i in range(x, x + w, 4):  # dentils
        px(L.alb, i, y + depth - 1, shade(color, 0.7))


def drainpipe(L: Layers, x, y0, y1):
    vline(L.alb, x, y0, y1, P.IRON)
    vline(L.alb, x + 1, y0, y1, P.IRON_LIGHT)
    for y in range(y0 + 6, y1, 22):
        hline(L.alb, x - 1, x + 2, y, shade(P.IRON, 0.7))
    L.wet(x - 1, y1 - 1, 4, 3, 0.95)


def awning(L: Layers, x, y, w, h, color, stripe=None):
    for j in range(h):
        inset = j // 2
        c = shade(color, 1.0 - 0.25 * (1 - j / max(1, h)))
        hline(L.alb, x - inset, x + w - 1 + inset, y + j, c)
        if stripe is not None:
            for i in range(x - inset, x + w + inset, 6):
                hline(L.alb, i, min(i + 2, x + w - 1 + inset), y + j, shade(stripe, 0.8 + 0.2 * j / h))
    # scalloped edge
    yy = y + h
    for i in range(x - h // 2, x + w + h // 2, 4):
        hline(L.alb, i, i + 2, yy, shade(color, 0.7))
        px(L.alb, i + 1, yy + 1, shade(color, 0.55))


# ---------------------------------------------------------------------------- neon
def neon_letters(alb, emi, text, x, y, color, vertical=False, gap=2, tube_dim=None):
    """Draw text as 1px neon tubes: dim glass in albedo, bright tubes in emissive."""
    tube = tube_dim or shade(color, 0.35)
    blit_text(alb, GLYPHS, text, x, y, tube, vertical=vertical, gap=gap)
    blit_text(emi, GLYPHS, text, x, y, color, vertical=vertical, gap=gap)


def neon_blade(sprites: SpriteSet, name, text, color, outline_color=None, board=P.IRON, width=13):
    """A vertical projecting blade sign. Returns (key, w, h)."""
    n = len(text)
    h = n * 10 + 8
    w = width
    alb, emi = surf(w, h), surf(w, h)
    rect(alb, 0, 0, w, h, shade(board, 0.9))
    rect(alb, 1, 1, w - 2, h - 2, shade(board, 0.6))
    # rivets
    for yy in (2, h - 3):
        px(alb, 2, yy, P.IRON_LIGHT)
        px(alb, w - 3, yy, P.IRON_LIGHT)
    tx = (w - 5) // 2
    neon_letters(alb, emi, text, tx, 3, color, vertical=True, gap=1)
    if outline_color is not None:
        for yy in range(1, h - 1):
            px(emi, 1, yy, outline_color)
            px(emi, w - 2, yy, outline_color)
        hline(emi, 1, w - 2, 1, outline_color)
        hline(emi, 1, w - 2, h - 2, outline_color)
    return sprites.add(name, alb, emi), w, h


def neon_text_sign(sprites: SpriteSet, name, text, color, board=None, pad=3, outline_color=None):
    tw = text_width(GLYPHS, text, 2)
    w, h = tw + pad * 2, 8 + pad * 2
    alb, emi = surf(w, h), surf(w, h)
    if board is not None:
        rect(alb, 0, 0, w, h, board)
        rect(alb, 1, 1, w - 2, h - 2, shade(board, 0.7))
    neon_letters(alb, emi, text, pad, pad, color, gap=2)
    if outline_color is not None:
        hline(emi, 1, w - 2, 1, outline_color)
        hline(emi, 1, w - 2, h - 2, outline_color)
        vline(emi, 1, 1, h - 2, outline_color)
        vline(emi, w - 2, 1, h - 2, outline_color)
    return sprites.add(name, alb, emi), w, h


def add_sign_prop(L: Layers, key, x, y, w, h, flicker="steady", light_color=None, radius=70, intensity=0.9, light_dy=None, layer="facade"):
    prop = {"kind": "sign", "sprite": key, "x": int(x), "y": int(y), "flicker": flicker, "layer": layer}
    if light_color is not None:
        prop["light"] = {"dx": w / 2, "dy": h / 2 if light_dy is None else light_dy, "radius": radius,
                         "color": list(light_color), "intensity": intensity}
    L.meta["props"].append(prop)
    return prop


# ---------------------------------------------------------------------------- ground
def ground_street(L: Layers, rng, x0, x1, layout: dict):
    """Sidewalks, curbs, road with tram rails, puddles. layout gives y-coordinates."""
    ns0, ns1 = layout["north_sidewalk"]
    rd0, rd1 = layout["road"]
    ss0, ss1 = layout["south_sidewalk"]
    mirror = layout["mirror_y"]
    w = x1 - x0
    # north sidewalk slabs
    rect(L.alb, x0, ns0, w, ns1 - ns0, P.CONCRETE)
    noise_tint(L.alb, pygame.Rect(x0, ns0, w, ns1 - ns0), rng, 0.05)
    for x in range(x0, x1, 18):
        vline(L.alb, x, ns0, ns1 - 1, P.CONCRETE_DARK)
    hline(L.alb, x0, x1 - 1, ns0 + (ns1 - ns0) // 2, shade(P.CONCRETE, 0.92))
    # AO at facade base
    hline(L.alb, x0, x1 - 1, ns0, shade(P.CONCRETE, 0.55))
    hline(L.alb, x0, x1 - 1, ns0 + 1, shade(P.CONCRETE, 0.75))
    L.wet(x0, ns0, w, ns1 - ns0, 0.26, mirror)
    # curb north
    rect(L.alb, x0, ns1, w, 2, P.CURB_TOP)
    rect(L.alb, x0, ns1 + 2, w, 2, P.CURB_FACE)
    L.wet(x0, ns1, w, 4, 0.2, mirror)
    # gutter
    rect(L.alb, x0, ns1 + 4, w, 3, P.GUTTER)
    L.wet(x0, ns1 + 4, w, 3, 1.0, mirror)
    # road
    rect(L.alb, x0, ns1 + 7, w, rd1 - (ns1 + 7), P.ASPHALT)
    noise_tint(L.alb, pygame.Rect(x0, ns1 + 7, w, rd1 - (ns1 + 7)), rng, 0.06, scale=1)
    # asphalt patches and cracks
    for _ in range(w // 70):
        px0 = int(rng.integers(x0, x1 - 30))
        py0 = int(rng.integers(rd0 + 4, rd1 - 14))
        pw, ph = int(rng.integers(14, 40)), int(rng.integers(5, 12))
        rect(L.alb, px0, py0, pw, ph, P.ASPHALT_PATCH)
        hline(L.alb, px0, px0 + pw - 1, py0, shade(P.ASPHALT_PATCH, 0.8))
    for _ in range(w // 40):
        cx = int(rng.integers(x0, x1))
        cy = int(rng.integers(rd0 + 2, rd1 - 2))
        for k in range(int(rng.integers(4, 12))):
            cx += int(rng.integers(-1, 2))
            cy += 1 if rng.random() < 0.4 else 0
            px(L.alb, cx + k, cy, P.ASPHALT_DARK)
    road_wet = rng.uniform(0.6, 0.75)
    L.wet(x0, ns1 + 7, w, rd1 - (ns1 + 7), road_wet, mirror)
    # tram rails
    for ry in layout.get("rails", []):
        hline(L.alb, x0, x1 - 1, ry, P.RAIL)
        hline(L.alb, x0, x1 - 1, ry + 1, P.RAIL_DARK)
        L.wet(x0, ry, w, 1, 0.95, mirror)
    # faded lane paint
    lane = (rd0 + rd1) // 2
    for x in range(x0 + 6, x1, 28):
        if rng.random() < 0.8:
            rect(L.alb, x, lane, 12, 1, mix(P.ASPHALT, P.CREAM, 0.35))
    # puddles: irregular blobs with very high wetness
    for _ in range(w // 55):
        cx = int(rng.integers(x0 + 10, x1 - 10))
        cy = int(rng.integers(rd0 + 6, rd1 - 6))
        pw, ph = int(rng.integers(16, 46)), int(rng.integers(4, 9))
        m = surf(pw, ph)
        pygame.draw.ellipse(m, (255, 255, 255, 255), m.get_rect())
        for _ in range(3):
            ox, oy = int(rng.integers(0, pw // 2)), int(rng.integers(-2, 3))
            pygame.draw.ellipse(m, (255, 255, 255, 255), pygame.Rect(ox, oy, pw // 2, ph))
        dark = surf(pw, ph)
        dark.fill(P.ASPHALT_DARK)
        dark.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        L.alb.blit(dark, (cx - pw // 2, cy - ph // 2))
        L.wet(cx - pw // 2, cy - ph // 2, pw, ph, 1.0, mirror, mask=m)
    # south curb + sidewalk
    rect(L.alb, x0, rd1, w, 3, P.GUTTER)
    L.wet(x0, rd1, w, 3, 1.0, mirror)
    rect(L.alb, x0, rd1 + 3, w, 2, P.CURB_FACE)
    rect(L.alb, x0, rd1 + 5, w, 2, P.CURB_TOP)
    rect(L.alb, x0, ss0, w, ss1 - ss0, shade(P.CONCRETE, 0.85))
    noise_tint(L.alb, pygame.Rect(x0, ss0, w, ss1 - ss0), rng, 0.05)
    for x in range(x0 + 9, x1, 18):
        vline(L.alb, x, ss0, ss1 - 1, P.CONCRETE_DARK)
    L.wet(x0, rd1 + 3, w, ss1 - rd1 - 3, 0.38, mirror)


def manhole(L: Layers, x, y):
    pygame.draw.ellipse(L.alb, shade(P.MANHOLE, 0.7), pygame.Rect(x - 1, y - 1, 16, 7))
    pygame.draw.ellipse(L.alb, P.MANHOLE, pygame.Rect(x, y, 14, 5))
    for i in range(2, 12, 3):
        hline(L.alb, x + i, x + i + 1, y + 2, shade(P.MANHOLE, 0.75))
    L.wet(x, y, 14, 5, 0.6)


# ---------------------------------------------------------------------------- skyline
def skyline(L: Layers, rng, x0, x1, y_bottom, max_h=60):
    """Distant city silhouettes with scattered lit windows (top of street views)."""
    x = x0
    far = mix(P.INK, P.GLASS, 0.5)
    while x < x1:
        bw = int(rng.integers(18, 50))
        bh = int(rng.integers(max_h // 3, max_h))
        top = y_bottom - bh
        rect(L.alb, x, top, bw, bh, far)
        if rng.random() < 0.3:  # spire / water tower
            rect(L.alb, x + bw // 2 - 1, top - 8, 3, 8, far)
        for wy in range(top + 3, y_bottom - 2, 4):
            for wx in range(x + 2, x + bw - 2, 3):
                if rng.random() < 0.12:
                    c = P.WINDOW_DIM if rng.random() < 0.7 else P.WINDOW_COOL
                    px(L.emi, wx, wy, shade(c, rng.uniform(0.5, 1.0)))
        x += bw + int(rng.integers(-6, 4))
