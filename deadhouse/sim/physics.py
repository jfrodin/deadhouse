"""Feet-box movement against axis-aligned colliders (no pygame display dependency)."""
from __future__ import annotations

import pygame

FOOT_W = 10
FOOT_H = 5


def foot_rect(x: float, y: float, w: int = FOOT_W, h: int = FOOT_H) -> pygame.Rect:
    return pygame.Rect(int(round(x - w / 2)), int(round(y - h)), w, h)


def move(x: float, y: float, dx: float, dy: float, colliders: list[pygame.Rect], w: int = FOOT_W, h: int = FOOT_H,
         extra: list[pygame.Rect] = ()) -> tuple[float, float, bool]:
    """Move feet position by (dx, dy), sliding along colliders. Returns new x, y and whether we hit something.

    Large moves are split into sub-steps so nothing tunnels through thin walls.
    """
    n = int(max(abs(dx), abs(dy)) // 4) + 1
    if n > 1:
        hit_any = False
        for _ in range(n):
            x, y, h_ = move(x, y, dx / n, dy / n, colliders, w, h, extra)
            hit_any = hit_any or h_
        return x, y, hit_any
    hit = False
    solids = list(colliders) + list(extra)
    # x axis
    nx = x + dx
    r = foot_rect(nx, y, w, h)
    for c in solids:
        if r.colliderect(c):
            hit = True
            if dx > 0:
                nx = c.left - w / 2 - 0.001
            elif dx < 0:
                nx = c.right + w / 2 + 0.001
            r = foot_rect(nx, y, w, h)
    # y axis
    ny = y + dy
    r = foot_rect(nx, ny, w, h)
    for c in solids:
        if r.colliderect(c):
            hit = True
            if dy > 0:
                ny = c.top - 0.001
            elif dy < 0:
                ny = c.bottom + h + 0.001
            r = foot_rect(nx, ny, w, h)
    return nx, ny, hit


def blocked(x: float, y: float, colliders: list[pygame.Rect], w: int = FOOT_W, h: int = FOOT_H) -> bool:
    r = foot_rect(x, y, w, h)
    return any(r.colliderect(c) for c in colliders)
