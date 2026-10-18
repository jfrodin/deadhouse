"""Composes the three low-res layers (albedo / emissive / material) for a frame."""
from __future__ import annotations

import math
import random

import pygame

from .. import config as C
from ..engine.renderer import Light
from ..sim import flicker

BLACK = (0, 0, 0, 255)


class Canvas:
    def __init__(self):
        size = (C.CANVAS_W, C.CANVAS_H)
        self.alb = pygame.Surface(size, pygame.SRCALPHA)
        self.emi = pygame.Surface(size, pygame.SRCALPHA)
        self.mat = pygame.Surface(size, pygame.SRCALPHA)
        self.ox = 0  # world -> canvas offset (canvas = world - origin)
        self.oy = 0

    def begin(self, origin_x: int, origin_y: int):
        self.ox, self.oy = origin_x, origin_y
        self.alb.fill((0, 0, 0, 255))
        self.emi.fill(BLACK)
        self.mat.fill(BLACK)

    def to_canvas(self, x, y):
        return int(round(x)) - self.ox, int(round(y)) - self.oy


class LevelCache:
    """Pre-dimmed copies of emissive sprites (pygame additive blits ignore surface alpha)."""

    STEPS = 8

    def __init__(self):
        self._c: dict[tuple[int, int], pygame.Surface] = {}

    def get(self, surf: pygame.Surface, level: float) -> pygame.Surface | None:
        q = max(0, min(self.STEPS, int(round(level * self.STEPS))))
        if q == 0:
            return None
        if q == self.STEPS:
            return surf
        key = (id(surf), q)
        s = self._c.get(key)
        if s is None:
            s = surf.copy()
            f = int(255 * q / self.STEPS)
            s.fill((f, f, f, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self._c[key] = s
        return s


class Rain:
    def __init__(self, count=260, seed=7):
        self.rng = random.Random(seed)
        self.drops = [self._new(True) for _ in range(count)]
        self.splashes: list[list[float]] = []
        self.last_cam = None
        self.intensity = 1.0

    def _new(self, anywhere=False):
        r = self.rng
        return [r.uniform(-20, C.CANVAS_W + 20), r.uniform(-C.CANVAS_H, C.CANVAS_H) if anywhere else r.uniform(-40, -4),
                r.uniform(240, 330), r.uniform(2, 5), r.random()]

    def update(self, dt, cam, ground_test):
        if self.last_cam is not None:
            dx, dy = cam[0] - self.last_cam[0], cam[1] - self.last_cam[1]
        else:
            dx = dy = 0
        self.last_cam = cam
        r = self.rng
        for d in self.drops:
            d[0] -= dx
            d[1] -= dy
            d[1] += d[2] * dt
            d[0] -= d[2] * dt * 0.18
            if d[1] > C.CANVAS_H + 10 or d[0] < -30 or d[0] > C.CANVAS_W + 30:
                d[:] = self._new()
                d[0] = r.uniform(-20, C.CANVAS_W + 40)
        # splashes on visible ground
        n = int(dt * 90 * self.intensity) + (1 if r.random() < (dt * 90 * self.intensity) % 1 else 0)
        for _ in range(n):
            sx, sy = r.uniform(0, C.CANVAS_W), r.uniform(0, C.CANVAS_H)
            if ground_test(sx + cam[0], sy + cam[1]):
                self.splashes.append([sx + cam[0], sy + cam[1], 0.0])
        for s in self.splashes:
            s[2] += dt
        self.splashes = [s for s in self.splashes if s[2] < 0.22]

    def draw(self, cv: Canvas, cam_origin):
        a = cv.alb
        for d in self.drops:
            x, y, _, ln, shade_ = d
            col = (150 + int(60 * shade_), 160 + int(60 * shade_), 185 + int(50 * shade_), 255)
            x0, y0 = int(x), int(y)
            pygame.draw.line(a, col, (x0, y0), (x0 + 1, y0 - int(ln)))
        for sx, sy, age in self.splashes:
            x, y = int(sx) - cv.ox, int(sy) - cv.oy
            if age < 0.08:
                a.set_at((x, y), (190, 200, 220, 255)) if 0 <= x < C.CANVAS_W and 0 <= y < C.CANVAS_H else None
                if 0 <= x < C.CANVAS_W and 0 <= y - 1 < C.CANVAS_H:
                    a.set_at((x, y - 1), (170, 180, 205, 255))
            else:
                for ox in (-2, 2):
                    if 0 <= x + ox < C.CANVAS_W and 0 <= y < C.CANVAS_H:
                        a.set_at((x + ox, y), (130, 140, 165, 255))


class SceneRenderer:
    def __init__(self, assets):
        self.assets = assets
        self.cv = Canvas()
        self.levels = LevelCache()
        self.rain = Rain()
        self._mask_cache: dict[int, pygame.Surface] = {}
        self._refl_cache: dict[int, pygame.Surface] = {}

    # ------------------------------------------------------------------ helpers
    def mask_of(self, s: pygame.Surface) -> pygame.Surface:
        """Solid black silhouette with s's alpha (used to clear wetness under sprites)."""
        k = id(s)
        m = self._mask_cache.get(k)
        if m is None:
            m = s.copy()
            m.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGB_MULT)
            self._mask_cache[k] = m
        return m

    def reflection_of(self, s: pygame.Surface) -> pygame.Surface:
        k = id(s)
        r = self._refl_cache.get(k)
        if r is None:
            r = pygame.transform.flip(s, False, True)
            r.fill((150, 160, 185, 255), special_flags=pygame.BLEND_RGBA_MULT)
            r.set_alpha(80)
            self._refl_cache[k] = r
        return r

    def blit_sprite(self, alb, emi, x, y, level=1.0, clear_wet=True, reflect_wet=False):
        """Blit at world position (top-left)."""
        cx, cy = self.cv.to_canvas(x, y)
        w, h = alb.get_size()
        if cx > C.CANVAS_W or cy > C.CANVAS_H or cx + w < 0 or cy + h < 0:
            return
        if reflect_wet:
            self.cv.alb.blit(self.reflection_of(alb), (cx, cy + h))
        self.cv.alb.blit(alb, (cx, cy))
        if clear_wet:
            self.cv.mat.blit(self.mask_of(alb), (cx, cy))
        if emi is not None:
            e = self.levels.get(emi, level)
            if e is not None:
                self.cv.emi.blit(e, (cx, cy), special_flags=pygame.BLEND_RGB_ADD)

    # ------------------------------------------------------------------ frame
    def draw_area_layer(self, area, layer: str):
        cv = self.cv
        src = pygame.Rect(cv.ox, cv.oy, C.CANVAS_W, C.CANVAS_H)
        for kind, target in (("alb", cv.alb), ("emi", cv.emi), ("mat", cv.mat)):
            rel = f"areas/{area.bake_id}/{layer}_{kind}.png"
            if layer != "bg" and not self.assets.exists(rel):
                return
            img = self.assets.image(rel)
            if layer == "bg":
                target.blit(img, (0, 0), src)
            elif kind == "emi":
                target.blit(img, (0, 0), src, special_flags=pygame.BLEND_RGB_ADD)
            else:
                target.blit(img, (0, 0), src)

    def facade_props(self, area, t):
        for p in area.props:
            k = p.kind
            if k == "sign" and p.data.get("layer", "facade") == "facade":
                alb, emi = self.assets.sprite(p.data["sprite"])
                lvl = flicker.level(p.data.get("flicker"), t, p.state["seed"])
                self.blit_sprite(alb, emi, p.x, p.y, lvl, clear_wet=False)
            elif k == "chase":
                alb, emi = self.assets.sprite(p.data["sprite"])
                self.blit_sprite(alb, None, p.x, p.y, clear_wet=False)
                step = int(t * 7)
                cx, cy = self.cv.to_canvas(p.x, p.y + p.data["bulbs_y"])
                col = p.data["color"]
                for i, bx in enumerate(p.data["bulbs_x"]):
                    if (i + step) % 4 != 0:
                        x = cx + bx
                        if 0 <= x < C.CANVAS_W and 0 <= cy < C.CANVAS_H:
                            self.cv.emi.set_at((x, cy), col)
            elif k == "dancers":
                self._dancers(p, t)
            elif k == "boarded_door":
                self._boarded_door(p, t)
            elif k == "bulb":
                self._bulb(p, t)
            elif k == "cat":
                self._cat(p, t)
            elif k == "searchlight":
                self._searchlight(p, t)
            elif k == "flicker_light":
                lvl = flicker.level(p.data.get("pattern"), t, p.state["seed"])
                cx, cy = self.cv.to_canvas(p.x, p.y)
                if lvl > 0.1 and 0 <= cx < C.CANVAS_W and 0 <= cy < C.CANVAS_H:
                    c = int(255 * lvl)
                    pygame.draw.rect(self.cv.emi, (c, int(c * 0.8), int(c * 0.5)), (cx - 2, cy, 5, 2))

    def _cat(self, p, t):
        cx, cy = self.cv.to_canvas(p.x, p.y)
        a, e = self.cv.alb, self.cv.emi
        if p.state.get("gone"):
            return
        col = (20, 18, 22, 255)
        pygame.draw.ellipse(a, col, (cx - 4, cy - 3, 9, 5))      # body
        a.fill(col, (cx + 3, cy - 6, 4, 4))                       # head
        a.fill(col, (cx + 3, cy - 7, 1, 1))                       # ears
        a.fill(col, (cx + 6, cy - 7, 1, 1))
        sw = int(round(math.sin(t * 2.3) * 2))
        pygame.draw.line(a, col, (cx - 4, cy), (cx - 7, cy - 2 + sw))  # tail
        blink = (t % 4.0) > 0.12
        if blink:
            e.fill((150, 210, 90), (cx + 4, cy - 5, 1, 1))
            e.fill((150, 210, 90), (cx + 6, cy - 5, 1, 1))

    def _searchlight(self, p, t):
        e = self.cv.emi
        cx, cy = self.cv.to_canvas(p.x, p.y)
        ang = -math.pi / 2 + math.sin(t * 0.25) * 0.6
        L = 160
        spread = 0.06
        pts = [(cx, cy), (cx + math.cos(ang - spread) * L, cy + math.sin(ang - spread) * L),
               (cx + math.cos(ang + spread) * L, cy + math.sin(ang + spread) * L)]
        beam = pygame.Surface(e.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(beam, (16, 18, 26), pts)
        e.blit(beam, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def _bulb(self, p, t):
        cx, cy = self.cv.to_canvas(p.x, p.y)
        a, e = self.cv.alb, self.cv.emi
        pygame.draw.line(a, (30, 26, 30, 255), (cx, cy - 14), (cx, cy - 1))
        if p.state.get("broken"):
            a.fill((60, 60, 64, 255), (cx - 1, cy - 1, 3, 2))
            a.fill((140, 150, 150, 255), (cx, cy + 1, 1, 1))
            return
        a.fill((200, 190, 160, 255), (cx - 1, cy, 3, 3))
        e.fill((255, 220, 160), (cx - 1, cy, 3, 3))
        e.fill((255, 255, 230), (cx, cy + 1, 1, 1))

    def _dancers(self, p, t):
        cx, cy = self.cv.to_canvas(p.x, p.y)
        w, h = p.data["w"], p.data["h"]
        ph = p.data.get("phase", 0)
        e = self.cv.emi
        clip = e.get_clip()
        e.set_clip(pygame.Rect(cx, cy, w, h))
        for i, off in enumerate((0.0, 1.9)):
            sway = math.sin(t * 1.7 + ph * 6 + off) * 3.0
            dx = cx + w // 2 + int(sway) + (i * 2 - 1) * 2
            bob = int(abs(math.sin(t * 3.4 + off)) * 1.5)
            col = (34, 18, 14, 255)
            pygame.draw.ellipse(e, col, (dx - 2, cy + 5 - bob, 4, 4))
            pygame.draw.rect(e, col, (dx - 2, cy + 9 - bob, 5, h - 9))
        e.set_clip(clip)

    def _boarded_door(self, p, t):
        cx, cy = self.cv.to_canvas(p.x, p.y)
        w, h = p.data["w"], p.data["h"]
        a, e = self.cv.alb, self.cv.emi
        lvl = flicker.level("projector", t, p.state["seed"])
        broken = p.state.get("broken", False)
        light = (int(95 * lvl), int(105 * lvl), int(140 * lvl))
        if broken:
            pygame.draw.rect(e, (int(60 * lvl), int(66 * lvl), int(90 * lvl)), (cx, cy, w, h))
            # splintered stubs at the frame
            for yy in range(cy + 4, cy + h - 2, 9):
                pygame.draw.rect(a, (90, 66, 46, 255), (cx, yy, 3, 3))
                pygame.draw.rect(a, (90, 66, 46, 255), (cx + w - 3, yy + 1, 3, 3))
            return
        # dark doorway, cold light leaking through short broken slits between the planks
        pygame.draw.rect(e, (int(14 * lvl), int(16 * lvl), int(24 * lvl)), (cx, cy, w, h))
        slits = ((2, 8, 5), (11, 17, 11), (4, 9, 17), (13, 18, 23), (1, 6, 29))
        for x0, x1, yy in slits:
            if yy < h:
                pygame.draw.line(e, light, (cx + x0, cy + yy), (cx + x1, cy + yy))
        boards = ((-2, 2, 5, 0), (-1, 8, 5, 1), (-2, 14, 6, -1), (-1, 20, 5, 1), (-2, 26, 5, 0))
        for x0, yy, th, tilt in boards:
            if yy >= h:
                continue
            col = (118, 88, 62, 255)
            pygame.draw.polygon(a, col, [(cx + x0, cy + yy + tilt), (cx + w + 1, cy + yy - tilt),
                                         (cx + w + 1, cy + yy + th - tilt), (cx + x0, cy + yy + th + tilt)])
            pygame.draw.line(a, (150, 116, 84, 255), (cx + x0, cy + yy + tilt), (cx + w + 1, cy + yy - tilt))
            for nx in (cx + 1, cx + w - 2):
                if 0 <= nx < C.CANVAS_W and 0 <= cy + yy + 2 < C.CANVAS_H:
                    a.set_at((nx, cy + yy + 2), (170, 175, 180, 255))

    def sorted_props(self, area, t):
        """Props that participate in y-sorting: (sort_y, draw_fn)."""
        out = []
        for p in area.props:
            k = p.kind
            if k == "lamp":
                alb, emi = self.assets.sprite(p.data["sprite"])
                lvl = flicker.level(p.data.get("flicker"), t, p.state["seed"])
                if p.state.get("broken"):
                    lvl = 0.0
                out.append((p.data["base_y"], lambda a=alb, e=emi, x=p.x, y=p.y, l=lvl: self.blit_sprite(a, e, x, y, l)))
            elif k == "static":
                alb, emi = self.assets.sprite(p.data["sprite"])
                y = p.data["base_y"] - alb.get_height()
                out.append((p.data["base_y"], lambda a=alb, e=emi, x=p.x, y=y: self.blit_sprite(a, e, x, y)))
            elif k == "rope":
                out.append((p.y, lambda p=p: self._rope(p)))
        return out

    def _rope(self, p):
        post_key = None
        for lname in ("bg",):
            pass
        alb, _ = self.assets.sprite("row/ropepost")
        x, y, w = p.x, p.y, p.data["w"]
        self.blit_sprite(alb, None, x, y - 12)
        self.blit_sprite(alb, None, x + w, y - 12)
        cx, cy = self.cv.to_canvas(x + 2, y - 9)
        pts = [(cx + i, cy + int(math.sin(i / w * math.pi) * 3)) for i in range(0, w + 1)]
        pygame.draw.lines(self.cv.alb, (120, 24, 44, 255), False, pts)

    def collect_lights(self, area, t, extra: list[Light]) -> list[Light]:
        lights: list[Light] = []
        vx0, vy0 = self.cv.ox - 120, self.cv.oy - 120
        vx1, vy1 = self.cv.ox + C.CANVAS_W + 120, self.cv.oy + C.CANVAS_H + 120
        for L in area.lights:
            lvl = L.level(t)
            if lvl <= 0.01:
                continue
            if L.x + L.radius < vx0 or L.x - L.radius > vx1 or L.y + L.radius < vy0 or L.y - L.radius > vy1:
                continue
            lights.append(Light(L.x, L.y, L.radius, L.color, L.intensity * lvl, L.specular, L.direction,
                                L.cos_inner, L.cos_outer, L.clip))
        lights.extend(extra)
        # most important lights first (renderer has a fixed cap)
        lights.sort(key=lambda l: -l.intensity * l.radius)
        return lights[: C.MAX_LIGHTS]
