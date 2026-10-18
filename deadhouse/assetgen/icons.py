"""Item icons (pickups in the world and the inventory screen), hand-placed pixel shapes."""
from __future__ import annotations

import os

import pygame

from . import palette as P
from .env import SpriteSet
from .gfx import hexc, hline, line, outline, px, rect, shade, surf, vline


def _icon(draw) -> pygame.Surface:
    s = surf(14, 14)
    draw(s)
    return outline(s, P.INK)


def razor(s):
    rect(s, 2, 8, 6, 2, hexc("5a3a28"))
    hline(s, 2, 7, 8, hexc("7a5238"))
    line(s, 7, 8, 12, 3, hexc("d0d4dc"))
    line(s, 8, 8, 12, 4, hexc("9aa0aa"))


def tire_iron(s):
    line(s, 2, 11, 11, 2, hexc("6a6e76"))
    line(s, 3, 11, 12, 2, hexc("8a8e96"))
    line(s, 9, 1, 12, 4, hexc("8a8e96"))


def revolver(s):
    rect(s, 2, 4, 9, 3, hexc("3c4048"))
    hline(s, 2, 10, 4, hexc("5c626c"))
    rect(s, 5, 6, 4, 3, hexc("4a4e56"))
    rect(s, 3, 7, 3, 5, hexc("5a3a28"))
    px(s, 10, 3, hexc("5c626c"))


def rounds(s):
    for i in range(3):
        rect(s, 3 + i * 3, 4, 2, 7, P.BRASS)
        rect(s, 3 + i * 3, 3, 2, 1, hexc("8a6a3a"))
        vline(s, 3 + i * 3, 4, 10, shade(P.BRASS, 1.3))


def bottle(s):
    rect(s, 5, 5, 4, 7, hexc("3a6a48"))
    rect(s, 6, 2, 2, 3, hexc("3a6a48"))
    vline(s, 5, 6, 10, hexc("6aa07a"))
    rect(s, 6, 7, 2, 2, P.POSTER_PAPER)


def dressing(s):
    rect(s, 2, 4, 10, 7, P.CREAM)
    for x in range(3, 12, 2):
        vline(s, x, 4, 10, shade(P.CREAM, 0.85))
    rect(s, 6, 5, 2, 5, hexc("b02a2a"))
    rect(s, 5, 6, 4, 2, hexc("b02a2a"))


def matches(s):
    rect(s, 3, 3, 8, 9, hexc("6a1e2a"))
    rect(s, 3, 3, 8, 2, P.DECO_GOLD)
    px(s, 6, 7, P.DECO_GOLD)
    px(s, 7, 8, P.DECO_GOLD)


def lantern(s):
    rect(s, 4, 4, 7, 8, hexc("3a3836"))
    rect(s, 5, 2, 5, 2, hexc("5a5854"))
    rect(s, 6, 6, 3, 3, P.BULB)
    hline(s, 4, 10, 11, hexc("5a5854"))


def camera(s):
    rect(s, 2, 4, 10, 8, hexc("5a3a24"))
    rect(s, 2, 4, 10, 2, hexc("7a5234"))
    pygame.draw.circle(s, hexc("2a2a30"), (7, 8), 3)
    px(s, 6, 7, hexc("8a9aaa"))
    rect(s, 9, 2, 3, 2, hexc("9aa0aa"))


def photo(s):
    rect(s, 2, 2, 10, 10, P.CREAM)
    rect(s, 3, 3, 8, 7, hexc("3a3a40"))
    rect(s, 5, 5, 2, 5, hexc("1a1a1e"))
    rect(s, 8, 4, 2, 6, hexc("1a1a1e"))
    px(s, 8, 4, hexc("b02a2a"))


def ledger(s):
    rect(s, 2, 2, 10, 10, P.POSTER_PAPER)
    for y in range(4, 11, 2):
        hline(s, 3, 10, y, hexc("6a5a4a"))
    hline(s, 3, 9, 8, hexc("b02a2a"))


def reel(s):
    pygame.draw.circle(s, hexc("8a8e96"), (7, 7), 5)
    pygame.draw.circle(s, hexc("4a4e56"), (7, 7), 4)
    for (x, y) in ((7, 5), (5, 8), (9, 8)):
        px(s, x, y, hexc("1a1a1e"))
    px(s, 7, 7, hexc("aab0ba"))


def debug(s):
    rect(s, 2, 2, 10, 10, hexc("2a6a8a"))
    hline(s, 4, 9, 6, P.CREAM)
    vline(s, 6, 4, 9, P.CREAM)


ICONS = {"razor": razor, "tire_iron": tire_iron, "revolver": revolver, "rounds": rounds, "bottle": bottle,
         "dressing": dressing, "matches": matches, "lantern": lantern, "camera": camera, "photo": photo,
         "ledger": ledger, "reel": reel, "debug": debug}


def build(out_dir: str) -> list[str]:
    S = SpriteSet("icons")
    for name, fn in ICONS.items():
        S.add(name, _icon(fn))
    return S.save(os.path.join(out_dir, "sprites"))
