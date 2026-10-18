"""Base entity types. Pure game logic: positions are feet positions in area pixels."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

_next_id = [1]


def new_id() -> int:
    _next_id[0] += 1
    return _next_id[0]


def dir4(fx: float, fy: float) -> str:
    """Facing vector -> sprite view: S, N, E or W."""
    if abs(fx) > abs(fy) * 1.05:
        return "E" if fx > 0 else "W"
    return "S" if fy >= 0 else "N"


def norm(x: float, y: float) -> tuple[float, float, float]:
    d = math.hypot(x, y)
    if d < 1e-6:
        return 0.0, 0.0, 0.0
    return x / d, y / d, d


class Entity:
    kind = "entity"
    solid = True
    foot_w = 10
    foot_h = 5

    def __init__(self, x: float, y: float, sprite: str | None = None):
        self.id = new_id()
        self.x, self.y = float(x), float(y)
        self.vx = self.vy = 0.0
        self.fx, self.fy = 0.0, 1.0  # facing
        self.sprite = sprite
        self.anim = "idle"
        self.anim_t = 0.0
        self.anim_speed = 1.0
        self.removed = False
        self.flash = 0.0       # hit flash timer (render)
        self.tag: str | None = None
        self.interact: dict | None = None  # {"verb": "Talk", "dialogue": node, ...}
        self.overlay: list[str] = []      # extra attachments for rendering (umbrella, cigarette...)
        self.shadow = True

    @property
    def view(self) -> str:
        return dir4(self.fx, self.fy)

    def set_anim(self, name: str, restart: bool = False, speed: float = 1.0):
        if name != self.anim or restart:
            self.anim = name
            self.anim_t = 0.0
        self.anim_speed = speed

    def face(self, dx: float, dy: float):
        nx, ny, d = norm(dx, dy)
        if d > 0:
            self.fx, self.fy = nx, ny

    def dist_to(self, other) -> float:
        return math.hypot(other.x - self.x, other.y - self.y)

    def update(self, world, dt: float):
        self.anim_t += dt * self.anim_speed
        if self.flash > 0:
            self.flash -= dt


class Actor(Entity):
    kind = "actor"

    def __init__(self, x, y, sprite=None, hp=50):
        super().__init__(x, y, sprite)
        self.hp = self.max_hp = hp
        self.state = "idle"
        self.state_t = 0.0
        self.knock_vx = self.knock_vy = 0.0
        self.iframes = 0.0
        self.bleed_t = 0.0
        self.bleed_dps = 0.0
        self.dead = False
        self.team = "neutral"

    def set_state(self, s: str):
        self.state = s
        self.state_t = 0.0

    def apply_knock(self, dt: float):
        if abs(self.knock_vx) + abs(self.knock_vy) > 0.5:
            dx, dy = self.knock_vx * dt, self.knock_vy * dt
            self.knock_vx *= max(0.0, 1 - dt * 9)
            self.knock_vy *= max(0.0, 1 - dt * 9)
            return dx, dy
        self.knock_vx = self.knock_vy = 0.0
        return 0.0, 0.0
