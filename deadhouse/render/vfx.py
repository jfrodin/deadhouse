"""Particles and transient effects, drawn into the albedo/emissive canvases."""
from __future__ import annotations

import math
import random

import pygame

from .. import config as C


class Particle:
    __slots__ = ("x", "y", "z", "vx", "vy", "vz", "life", "max_life", "kind", "color", "size")

    def __init__(self, x, y, z, vx, vy, vz, life, kind, color, size=1):
        self.x, self.y, self.z = x, y, z
        self.vx, self.vy, self.vz = vx, vy, vz
        self.life = self.max_life = life
        self.kind = kind
        self.color = color
        self.size = size


class VFX:
    def __init__(self):
        self.p: list[Particle] = []
        self.stains: list[tuple] = []     # (x, y, color, size) blood on the ground (persist)
        self.tracers: list[list] = []     # [x1, y1, x2, y2, life]
        self.rng = random.Random(3)

    def clear(self):
        self.p.clear()
        self.stains.clear()
        self.tracers.clear()

    def spawn(self, ev: dict):
        k = ev["kind"]
        x, y = ev["x"], ev["y"]
        r = self.rng
        if k == "blood":
            dx, dy = ev.get("dx", 0), ev.get("dy", 0)
            n = ev.get("amount", 5)
            for _ in range(n):
                sp = r.uniform(20, 70)
                a = math.atan2(dy, dx) + r.uniform(-0.8, 0.8) if (dx or dy) else r.uniform(0, 6.28)
                col = r.choice(((110, 14, 20, 255), (80, 8, 14, 255), (140, 24, 28, 255)))
                self.p.append(Particle(x, y + 16, 16, math.cos(a) * sp, math.sin(a) * sp * 0.6, r.uniform(10, 50),
                                       r.uniform(0.4, 0.8), "blood", col, r.choice((1, 1, 2))))
        elif k == "splash":
            for _ in range(3):
                a = r.uniform(0, 6.28)
                self.p.append(Particle(x + r.uniform(-3, 3), y, 0, math.cos(a) * 18, math.sin(a) * 6, r.uniform(25, 45),
                                       0.25, "drop", (170, 180, 200, 255)))
        elif k == "sparks":
            for _ in range(10):
                a = r.uniform(0, 6.28)
                sp = r.uniform(30, 110)
                self.p.append(Particle(x, y, 0, math.cos(a) * sp, math.sin(a) * sp, r.uniform(-20, 40),
                                       r.uniform(0.15, 0.4), "spark", (255, 210, 140, 255)))
        elif k == "glass":
            for _ in range(12):
                a = r.uniform(0, 6.28)
                sp = r.uniform(20, 80)
                self.p.append(Particle(x, y, 6, math.cos(a) * sp, math.sin(a) * sp * 0.6, r.uniform(10, 60),
                                       r.uniform(0.5, 1.2), "glass", r.choice(((140, 170, 150, 255), (190, 210, 200, 255), (90, 120, 100, 255)))))
        elif k == "tracer":
            self.tracers.append([x, y, ev["x2"], ev["y2"], 0.06])
        elif k == "steam":
            self.p.append(Particle(x + r.uniform(-4, 4), y, 0, r.uniform(-4, 4), 0, r.uniform(10, 18), r.uniform(1.6, 2.6),
                                   "steam", (150, 150, 160, 255), r.choice((2, 3, 4))))
        elif k == "dust":
            for _ in range(ev.get("amount", 8)):
                a = r.uniform(0, 6.28)
                self.p.append(Particle(x + r.uniform(-6, 6), y, r.uniform(0, 20), math.cos(a) * 20, math.sin(a) * 10,
                                       r.uniform(-5, 10), r.uniform(0.5, 1.0), "dust", (120, 100, 80, 255), 1))
        elif k == "splinters":
            for _ in range(16):
                a = r.uniform(-1.2, 1.2) + (math.pi / 2)
                sp = r.uniform(30, 90)
                self.p.append(Particle(x + r.uniform(-8, 8), y, r.uniform(4, 30), math.cos(a) * sp * r.choice((-1, 1)),
                                       math.sin(a) * sp * 0.6, r.uniform(10, 60), r.uniform(0.6, 1.4), "glass",
                                       r.choice(((106, 78, 54, 255), (130, 98, 70, 255), (80, 60, 40, 255))), r.choice((1, 2))))

    def update(self, dt):
        alive = []
        for q in self.p:
            q.life -= dt
            if q.life <= 0:
                if q.kind == "blood" and len(self.stains) < 300:
                    self.stains.append((q.x, q.y, q.color, q.size))
                continue
            q.x += q.vx * dt
            q.y += q.vy * dt
            if q.kind == "steam":
                q.z += q.vz * dt
                q.vx *= 0.98
                q.size = min(6, q.size + dt * 1.5)
            else:
                q.z += q.vz * dt
                q.vz -= 160 * dt
                if q.z <= 0:
                    q.z = 0
                    q.vz *= -0.3
                    q.vx *= 0.5
                    q.vy *= 0.5
                    if q.kind == "blood":
                        q.life = min(q.life, 0.01)
            alive.append(q)
        self.p = alive
        for t in self.tracers:
            t[4] -= dt
        self.tracers = [t for t in self.tracers if t[4] > 0]

    def draw_stains(self, cv):
        a = cv.alb
        for x, y, col, size in self.stains:
            cx, cy = int(x) - cv.ox, int(y) - cv.oy
            if 0 <= cx < C.CANVAS_W and 0 <= cy < C.CANVAS_H:
                a.fill((col[0] // 2 + 20, col[1] // 2, col[2] // 2, 255), (cx, cy, size + 1, size))

    def draw(self, cv):
        a, e = cv.alb, cv.emi
        for q in self.p:
            cx, cy = int(q.x) - cv.ox, int(q.y - q.z) - cv.oy
            if not (-8 <= cx < C.CANVAS_W + 8 and -8 <= cy < C.CANVAS_H + 8):
                continue
            if q.kind == "spark":
                f = q.life / q.max_life
                c = (int(255 * f + 80), int(190 * f + 40), int(110 * f), 255)
                c = tuple(min(255, v) for v in c[:3]) + (255,)
                e.fill(c, (cx, cy, 1, 1))
            elif q.kind == "steam":
                f = q.life / q.max_life
                s = int(q.size)
                col = (110, 112, 125, int(70 * f))
                surf = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)
                pygame.draw.circle(surf, col, (s, s), s)
                a.blit(surf, (cx - s, cy - s))
            elif q.kind == "dust":
                a.fill(q.color, (cx, cy, 1, 1))
            else:
                a.fill(q.color, (cx, cy, q.size, q.size))
        for x1, y1, x2, y2, life in self.tracers:
            f = life / 0.06
            pygame.draw.line(e, (int(255 * f), int(220 * f), int(150 * f)), (x1 - cv.ox, y1 - cv.oy), (x2 - cv.ox, y2 - cv.oy))
