"""Who can see whom: light levels, vision cones, line of sight, and noise."""
from __future__ import annotations

import math
from dataclasses import dataclass

import pygame


@dataclass
class Noise:
    x: float
    y: float
    radius: float
    source: str  # "gunshot", "glass", "footsteps", "fight", "voice"
    loud: bool = False
    team: str = "neutral"


def line_of_sight(area, x0, y0, x1, y1, extra_blockers=()) -> bool:
    """Sample along the segment (eye height ignored) against blocking colliders."""
    dx, dy = x1 - x0, y1 - y0
    d = math.hypot(dx, dy)
    if d < 1:
        return True
    steps = int(d / 5) + 1
    rects = [r for r, t in zip(area.colliders, area.collider_tags) if t not in ("low", "rail")]
    rects += list(extra_blockers)
    # quick reject: only rects that touch the segment's bounding box
    bb = pygame.Rect(min(x0, x1) - 1, min(y0, y1) - 1, abs(dx) + 2, abs(dy) + 2)
    rects = [r for r in rects if r.colliderect(bb)]
    if not rects:
        return True
    for i in range(1, steps):
        t = i / steps
        px, py = x0 + dx * t, y0 + dy * t - 3
        for r in rects:
            if r.collidepoint(px, py):
                return False
    return True


def visibility(world, target) -> float:
    """How visible an actor is in [0, 1] — driven by the light falling on them."""
    lum = world.area.light_at(target.x, target.y - 14, world.t, world.dynamic_light_sources())
    vis = (lum - 0.07) * 3.2
    if getattr(target, "lantern_on", False):
        vis += 0.55
    if getattr(target, "is_sprinting", False):
        vis += 0.12
    if getattr(target, "match_lit", 0) > 0:
        vis += 0.6
    return max(0.06, min(1.0, vis))


def can_see(world, viewer, target, sight: float, cone_cos: float = 0.25) -> tuple[bool, float]:
    """Returns (seen, strength). strength in [0, 1] drives how fast suspicion rises."""
    dx, dy = target.x - viewer.x, target.y - viewer.y
    d = math.hypot(dx, dy)
    if d < 1:
        return True, 1.0
    vis = visibility(world, target)
    rng = 22 + sight * vis
    if d > rng:
        return False, 0.0
    facing = (dx * viewer.fx + dy * viewer.fy) / d
    close = d < 14
    if facing < cone_cos and not close:
        return False, 0.0
    if not line_of_sight(world.area, viewer.x, viewer.y, target.x, target.y):
        return False, 0.0
    strength = vis * (1.0 - d / (rng + 1)) * (1.4 if facing > 0.8 else 1.0)
    return True, max(0.05, min(1.0, strength))
