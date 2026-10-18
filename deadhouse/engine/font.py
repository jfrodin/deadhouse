"""Runtime renderer for the hand-designed pixel font in assetgen.font_data."""
from __future__ import annotations

import pygame

from ..assetgen.font_data import ALIASES, CELL_H, GLYPHS


def normalize(text: str) -> str:
    for k, v in ALIASES.items():
        text = text.replace(k, v)
    return text


class BitmapFont:
    def __init__(self, scale: int = 1, spacing: int = 1, line_gap: int = 3):
        self.scale = scale
        self.spacing = spacing
        self.line_h = (CELL_H + line_gap) * scale
        self._masks: dict[str, pygame.Surface] = {}
        self._cache: dict[tuple, pygame.Surface] = {}
        for ch, rows in GLYPHS.items():
            w = len(rows[0])
            s = pygame.Surface((w, CELL_H), pygame.SRCALPHA)
            for y, row in enumerate(rows):
                for x, c in enumerate(row):
                    if c == "#":
                        s.set_at((x, y + 1), (255, 255, 255, 255))
            if scale != 1:
                s = pygame.transform.scale(s, (w * scale, CELL_H * scale))
            self._masks[ch] = s

    def glyph_width(self, ch: str) -> int:
        m = self._masks.get(ch) or self._masks["?"]
        return m.get_width()

    def width(self, text: str) -> int:
        text = normalize(text)
        if not text:
            return 0
        return sum(self.glyph_width(c) + self.spacing * self.scale for c in text) - self.spacing * self.scale

    def _tinted(self, ch: str, color) -> pygame.Surface:
        key = (ch, tuple(color))
        s = self._cache.get(key)
        if s is None:
            m = self._masks.get(ch) or self._masks["?"]
            s = m.copy()
            s.fill((*color[:3], 255), special_flags=pygame.BLEND_RGBA_MULT)
            if len(self._cache) > 4000:
                self._cache.clear()
            self._cache[key] = s
        return s

    def draw(self, surf: pygame.Surface, text: str, pos, color=(230, 225, 215), shadow=None, alpha: int = 255) -> int:
        """Draw a single line; returns the x after the text."""
        text = normalize(text)
        x, y = pos
        for ch in text:
            g = self._tinted(ch, color)
            if shadow is not None:
                sg = self._tinted(ch, shadow)
                if alpha < 255:
                    sg.set_alpha(alpha)
                surf.blit(sg, (x + self.scale, y + self.scale))
            if alpha < 255:
                g.set_alpha(alpha)
            surf.blit(g, (x, y))
            if alpha < 255:
                g.set_alpha(255)
                if shadow is not None:
                    sg.set_alpha(255)
            x += g.get_width() + self.spacing * self.scale
        return x

    def wrap(self, text: str, max_w: int) -> list[str]:
        lines: list[str] = []
        for para in normalize(text).split("\n"):
            words = para.split(" ")
            cur = ""
            for w in words:
                trial = w if not cur else cur + " " + w
                if self.width(trial) <= max_w or not cur:
                    cur = trial
                else:
                    lines.append(cur)
                    cur = w
            lines.append(cur)
        return lines
