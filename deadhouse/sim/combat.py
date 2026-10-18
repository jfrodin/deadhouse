"""Shared combat resolution: melee sweeps, hits, damage feedback events."""
from __future__ import annotations

import math
from dataclasses import dataclass

from .entities import Actor, norm


@dataclass
class Hit:
    damage: float
    kx: float
    ky: float
    stagger: float
    kind: str = "melee"      # melee | bullet | bottle | takedown
    bleed: float = 0.0
    source: object = None
    guard_break: bool = False
    heavy: bool = False


def melee_targets(world, attacker: Actor, reach: float, arc_deg: float):
    cos_half = math.cos(math.radians(arc_deg / 2))
    out = []
    for e in world.actors():
        if e is attacker or e.dead or e.team == attacker.team or e.team == "neutral":
            continue
        dx, dy = e.x - attacker.x, (e.y - attacker.y) * 1.15
        nx, ny, d = norm(dx, dy)
        if d > reach + 6:
            continue
        if d > 6 and nx * attacker.fx + ny * attacker.fy < cos_half:
            continue
        out.append(e)
    return out


def swing(world, attacker: Actor, sw: dict, bleed: float = 0.0, damage_mul: float = 1.0) -> int:
    """Resolve one melee swing's active frame. Returns the number of targets hit."""
    n = 0
    for t in melee_targets(world, attacker, sw["reach"], sw["arc"]):
        nx, ny, _ = norm(t.x - attacker.x, t.y - attacker.y)
        if nx == 0 and ny == 0:
            nx, ny = attacker.fx, attacker.fy
        hit = Hit(sw["damage"] * damage_mul, nx * sw["knock"], ny * sw["knock"], sw["stagger"], "melee", bleed, attacker,
                  sw.get("guard_break", False), sw.get("anim") == "heavy")
        if t.on_hit(world, hit):
            n += 1
    if n:
        world.hitstop(0.055 if not sw.get("anim") == "heavy" else 0.09)
        world.shake(1.6 if sw.get("anim") != "heavy" else 3.2)
    else:
        world.sfx("swing_heavy" if sw.get("anim") == "heavy" else "swing", attacker.x, attacker.y, 0.7)
    world.noise(attacker.x, attacker.y, sw.get("noise", 25), "fight", team=attacker.team)
    return n


def damage_feedback(world, target: Actor, hit: Hit):
    target.flash = 0.12
    kind = hit.kind
    if kind == "bullet":
        world.sfx("hit_bullet", target.x, target.y)
    elif hit.heavy:
        world.sfx("hit_heavy", target.x, target.y)
    elif hit.bleed > 0:
        world.sfx("hit_cut", target.x, target.y)
    else:
        world.sfx("hit", target.x, target.y)
    world.vfx("blood", target.x, target.y - 16, dx=hit.kx, dy=hit.ky, amount=4 if hit.damage < 15 else 9)
