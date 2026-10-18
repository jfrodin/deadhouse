"""Deterministic light flicker patterns. Shared by sim (perception) and rendering."""
from __future__ import annotations

import math


def _hash(n: float) -> float:
    return (math.sin(n * 12.9898 + 78.233) * 43758.5453) % 1.0


def level(pattern: str | None, t: float, seed: float = 0.0) -> float:
    """Brightness multiplier in [0, 1] for a light/sign at time t."""
    if not pattern or pattern == "steady":
        return 0.97 + 0.03 * math.sin(t * 7.0 + seed * 3.1)
    if pattern == "buzz":
        # mostly on; occasional rapid stutter
        slot = math.floor(t * 9.0 + seed * 17)
        r = _hash(slot + seed)
        if r < 0.05:
            return 0.15
        if r < 0.09:
            return 0.6
        return 0.95 + 0.05 * math.sin(t * 60.0)
    if pattern == "dying":
        # long irregular dark spells broken by sputters
        slot = math.floor(t * 3.0 + seed * 5)
        r = _hash(slot * 1.7 + seed)
        if r < 0.35:
            return 0.0
        fast = _hash(math.floor(t * 24.0) + seed * 3)
        if r < 0.55:
            return 1.0 if fast > 0.5 else 0.08
        return 0.85 + 0.15 * fast
    if pattern == "off":
        return 0.0
    if pattern == "projector":
        # cold cinema light: rapid frame flicker plus slow scene changes
        frame = _hash(math.floor(t * 24.0) + seed)
        scene = 0.55 + 0.45 * _hash(math.floor(t * 0.5) + seed * 9)
        return scene * (0.75 + 0.25 * frame)
    if pattern == "tv":
        return 0.5 + 0.5 * _hash(math.floor(t * 6.0) + seed)
    return 1.0
