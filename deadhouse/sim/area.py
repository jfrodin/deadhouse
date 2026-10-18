"""Runtime area: merges baked metadata (meta.json) with the content definition."""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field

import pygame

from . import flicker


@dataclass
class LightSource:
    x: float
    y: float
    radius: float
    color: tuple
    intensity: float = 1.0
    pattern: str | None = None
    seed: float = 0.0
    enabled: bool = True
    name: str | None = None
    clip: tuple | None = None
    direction: tuple | None = None
    cos_inner: float = 0.9
    cos_outer: float = 0.7
    specular: float = 1.0

    def level(self, t: float) -> float:
        if not self.enabled:
            return 0.0
        return flicker.level(self.pattern, t, self.seed)

    def contribution(self, px: float, py: float, t: float) -> float:
        """Scalar light amount at a point (same falloff as the GPU shader)."""
        if not self.enabled:
            return 0.0
        if self.clip is not None:
            x0, y0, x1, y1 = self.clip
            if px < x0 or py < y0 or px > x1 or py > y1:
                return 0.0
        dx, dy = px - self.x, py - self.y
        d2 = dx * dx + dy * dy
        r2 = self.radius * self.radius
        if d2 >= r2:
            return 0.0
        k = 1.0 - d2 / r2
        f = k * k * self.intensity * self.level(t)
        if self.direction is not None:
            d = max(d2 ** 0.5, 0.001)
            c = (dx * self.direction[0] + dy * self.direction[1]) / d
            lo, hi = self.cos_outer, self.cos_inner
            u = min(1.0, max(0.0, (c - lo) / max(1e-4, hi - lo)))
            f *= u * u * (3 - 2 * u)
        lum = 0.3 * self.color[0] + 0.59 * self.color[1] + 0.11 * self.color[2]
        return f * lum


@dataclass
class Prop:
    kind: str
    data: dict
    x: float
    y: float
    id: str | None = None
    state: dict = field(default_factory=dict)
    light: LightSource | None = None


class Area:
    def __init__(self, area_id: str, assets):
        self.id = area_id
        mod = importlib.import_module(f"deadhouse.content.areas.{area_id}")
        self.defn: dict = mod.AREA
        bake_id = self.defn.get("bake", area_id)
        self.bake_id = bake_id
        meta = assets.json(f"areas/{bake_id}/meta.json")
        self.w, self.h = meta["size"]
        self.layers = meta["layers"]
        self.name = self.defn.get("name", area_id)
        self.post = dict(self.defn.get("post", {}))
        self.colliders: list[pygame.Rect] = []
        self.collider_tags: list[str | None] = []
        self.anchors: dict[str, tuple[int, int]] = {}
        self.lights: list[LightSource] = []
        self.props: list[Prop] = []
        seed = 0.0
        for lname, L in self.layers.items():
            for c in L.get("colliders", []):
                self.colliders.append(pygame.Rect(c[0], c[1], c[2], c[3]))
                self.collider_tags.append(c[4] if len(c) > 4 else None)
            for k, v in L.get("anchors", {}).items():
                self.anchors[k] = (v[0], v[1])
            for ld in L.get("lights", []):
                seed += 1.37
                self.lights.append(LightSource(ld["x"], ld["y"], ld["radius"], tuple(ld["color"]), ld.get("intensity", 1.0),
                                               ld.get("flicker"), seed, name=ld.get("name"),
                                               clip=tuple(ld["clip"]) if ld.get("clip") else None))
            for pd in L.get("props", []):
                seed += 2.11
                p = Prop(pd["kind"], pd, pd.get("x", 0), pd.get("y", pd.get("base_y", 0)), pd.get("id"))
                ld = pd.get("light")
                if ld:
                    p.light = LightSource(pd.get("x", 0) + ld.get("dx", 0), pd.get("y", pd.get("base_y", 0)) + ld.get("dy", 0),
                                          ld["radius"], tuple(ld["color"]), ld.get("intensity", 1.0),
                                          pd.get("flicker") or pd.get("pattern"), seed,
                                          clip=tuple(ld["clip"]) if ld.get("clip") else None)
                    self.lights.append(p.light)
                p.state["seed"] = seed
                self.props.append(p)
        # content-defined extra lights / colliders
        for ld in self.defn.get("lights", []):
            seed += 0.91
            self.lights.append(LightSource(ld["x"], ld["y"], ld["radius"], tuple(ld["color"]), ld.get("intensity", 1.0),
                                           ld.get("flicker"), seed, name=ld.get("name"),
                                           clip=tuple(ld["clip"]) if ld.get("clip") else None))
        for c in self.defn.get("colliders", []):
            self.colliders.append(pygame.Rect(c[0], c[1], c[2], c[3]))
            self.collider_tags.append(c[4] if len(c) > 4 else None)
        self.exits = [dict(e) for e in self.defn.get("exits", [])]
        for e in self.exits:
            e["rect"] = pygame.Rect(e["rect"])
        self.spawns = {k: tuple(v) for k, v in self.defn.get("spawns", {}).items()}
        for k, v in self.anchors.items():
            self.spawns.setdefault(k, v)

    def prop(self, pid: str) -> Prop | None:
        for p in self.props:
            if p.id == pid:
                return p
        return None

    def disable_collider(self, tag: str) -> None:
        keep_r, keep_t = [], []
        for r, t in zip(self.colliders, self.collider_tags):
            if t != tag:
                keep_r.append(r)
                keep_t.append(t)
        self.colliders, self.collider_tags = keep_r, keep_t

    def light_at(self, x: float, y: float, t: float, extra=()) -> float:
        amb = self.post.get("ambient", (0.06, 0.07, 0.11))
        total = 0.3 * amb[0] + 0.59 * amb[1] + 0.11 * amb[2]
        for L in self.lights:
            total += L.contribution(x, y, t)
        for L in extra:
            total += L.contribution(x, y, t)
        return total
