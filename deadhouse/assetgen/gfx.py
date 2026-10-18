"""Small pixel-art drawing toolkit used by every art generator.

All drawing is deterministic: generators receive an explicit numpy Generator.
"""
from __future__ import annotations

import numpy as np
import pygame

Color = tuple  # (r, g, b) or (r, g, b, a)

BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], dtype=np.float32) / 16.0 + 1 / 32


def hexc(h: str, a: int = 255) -> Color:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def mix(c1: Color, c2: Color, t: float) -> Color:
    n = max(len(c1), len(c2))
    a = list(c1) + [255] * (n - len(c1))
    b = list(c2) + [255] * (n - len(c2))
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(n))


def shade(c: Color, f: float) -> Color:
    """f < 1 darkens, f > 1 lightens (multiplicative, clamped). Alpha kept."""
    out = [max(0, min(255, int(round(v * f)))) for v in c[:3]]
    return tuple(out) + tuple(c[3:])


def with_alpha(c: Color, a: int) -> Color:
    return (c[0], c[1], c[2], a)


def surf(w: int, h: int) -> pygame.Surface:
    return pygame.Surface((max(1, w), max(1, h)), pygame.SRCALPHA)


def rect(s: pygame.Surface, x, y, w, h, c: Color) -> None:
    if w > 0 and h > 0:
        s.fill(c, pygame.Rect(int(x), int(y), int(w), int(h)))


def hline(s, x0, x1, y, c):
    rect(s, min(x0, x1), y, abs(x1 - x0) + 1, 1, c)


def vline(s, x, y0, y1, c):
    rect(s, x, min(y0, y1), 1, abs(y1 - y0) + 1, c)


def px(s, x, y, c):
    if 0 <= x < s.get_width() and 0 <= y < s.get_height():
        s.set_at((int(x), int(y)), c)


def line(s, x0, y0, x1, y1, c, width: int = 1):
    pygame.draw.line(s, c, (x0, y0), (x1, y1), width)


def poly(s, pts, c):
    pygame.draw.polygon(s, c, [(round(x), round(y)) for x, y in pts])


def ellipse(s, x, y, w, h, c):
    pygame.draw.ellipse(s, c, pygame.Rect(int(x), int(y), int(w), int(h)))


def circle(s, cx, cy, r, c):
    pygame.draw.circle(s, c, (int(cx), int(cy)), int(r))


def dither_rect(s, x, y, w, h, c1: Color, c2: Color, t: float) -> None:
    """Ordered-dither between c1 and c2; t = fraction of c2."""
    x, y, w, h = int(x), int(y), int(w), int(h)
    for j in range(h):
        for i in range(w):
            if BAYER4[(y + j) % 4, (x + i) % 4] < t:
                s.set_at((x + i, y + j), c2)
            else:
                s.set_at((x + i, y + j), c1)


def vgrad_dither(s, x, y, w, h, top: Color, bottom: Color, steps: int = 4) -> None:
    """Vertical gradient quantized into `steps` bands and dithered between them."""
    x, y, w, h = int(x), int(y), int(w), int(h)
    for j in range(h):
        t = j / max(1, h - 1)
        band = t * (steps - 1)
        lo = int(band)
        frac = band - lo
        c_lo = mix(top, bottom, lo / max(1, steps - 1))
        c_hi = mix(top, bottom, min(steps - 1, lo + 1) / max(1, steps - 1))
        for i in range(w):
            s.set_at((x + i, y + j), c_hi if BAYER4[(y + j) % 4, (x + i) % 4] < frac else c_lo)


def noise_tint(s: pygame.Surface, area: pygame.Rect, rng: np.random.Generator, amount: float = 0.08, scale: int = 1) -> None:
    """Multiply the RGB of opaque pixels in `area` by a random factor in [1-amount, 1+amount]."""
    area = area.clip(s.get_rect())
    if area.w <= 0 or area.h <= 0:
        return
    rgb = pygame.surfarray.pixels3d(s)
    sub = rgb[area.x:area.x + area.w, area.y:area.y + area.h].astype(np.float32)
    nw, nh = (area.w + scale - 1) // scale, (area.h + scale - 1) // scale
    n = rng.uniform(1 - amount, 1 + amount, size=(nw, nh)).astype(np.float32)
    if scale > 1:
        n = np.repeat(np.repeat(n, scale, 0), scale, 1)
    n = n[:area.w, :area.h, None]
    rgb[area.x:area.x + area.w, area.y:area.y + area.h] = np.clip(sub * n, 0, 255).astype(np.uint8)
    del rgb


def outline(s: pygame.Surface, color: Color, diagonal: bool = False) -> pygame.Surface:
    """Return a copy of s (1px larger on every side) with a 1px outline around opaque pixels."""
    w, h = s.get_size()
    out = surf(w + 2, h + 2)
    a = pygame.surfarray.array_alpha(s) > 0
    m = np.zeros((w + 2, h + 2), bool)
    offs = [(0, 1), (2, 1), (1, 0), (1, 2)]
    if diagonal:
        offs += [(0, 0), (2, 0), (0, 2), (2, 2)]
    for ox, oy in offs:
        m[ox:ox + w, oy:oy + h] |= a
    inner = np.zeros_like(m)
    inner[1:1 + w, 1:1 + h] = a
    m &= ~inner
    rgb = pygame.surfarray.pixels3d(out)
    al = pygame.surfarray.pixels_alpha(out)
    rgb[m] = color[:3]
    al[m] = color[3] if len(color) > 3 else 255
    del rgb, al
    out.blit(s, (1, 1))
    return out


def brick_wall(s, x, y, w, h, base: Color, mortar: Color, rng, bw: int = 8, bh: int = 4, var: float = 0.12) -> None:
    rect(s, x, y, w, h, mortar)
    row = 0
    for yy in range(y, y + h, bh):
        off = (bw // 2) if row % 2 else 0
        for xx in range(x - off, x + w, bw):
            f = 1.0 + rng.uniform(-var, var)
            c = shade(base, f)
            bx0, bx1 = max(xx, x), min(xx + bw - 1, x + w)
            by1 = min(yy + bh - 1, y + h)
            if bx1 > bx0 and by1 > yy:
                rect(s, bx0, yy, bx1 - bx0, by1 - yy, c)
                # top highlight on each brick
                hline(s, bx0, bx1 - 1, yy, shade(c, 1.12))
        row += 1


def blit_text(s, font_glyphs, text: str, x: int, y: int, color: Color, vertical: bool = False, gap: int = 1) -> tuple[int, int]:
    """Draw text with the raw glyph tables (used for in-world signage at 1x)."""
    cx, cy = x, y
    for ch in text:
        g = font_glyphs.get(ch) or font_glyphs.get(ch.upper()) or font_glyphs["?"]
        for j, row in enumerate(g):
            for i, cc in enumerate(row):
                if cc == "#":
                    px(s, cx + i, cy + j, color)
        if vertical:
            cy += 8 + gap + 1
        else:
            cx += len(g[0]) + gap
    return cx, cy


def text_width(font_glyphs, text: str, gap: int = 1) -> int:
    return sum(len((font_glyphs.get(c) or font_glyphs["?"])[0]) + gap for c in text) - gap
