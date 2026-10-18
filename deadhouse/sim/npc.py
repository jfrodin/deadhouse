"""Non-hostile people: talkers, pedestrians and scripted street vignettes."""
from __future__ import annotations

import math
import random

from . import physics
from .entities import Actor, norm


class NPC(Actor):
    """A character you can talk to. Faces the player when close."""
    kind = "npc"

    def __init__(self, x, y, sprite, name, dialogue=None, facing=(0, 1), idle_anim="idle", barks=None,
                 bark_radius=60, verb="Talk", portrait=None, tag=None):
        super().__init__(x, y, sprite, 50)
        self.display_name = name
        self.fx, self.fy = facing
        self.home_facing = facing
        self.idle_anim = idle_anim
        self.dialogue = dialogue
        self.barks = list(barks or [])
        self.bark_i = 0
        self.bark_radius = bark_radius
        self.bark_cd = random.uniform(2, 5)
        self.verb = verb
        self.portrait = portrait
        self.tag = tag
        self.talking = False
        if dialogue:
            self.interact = {"verb": verb, "dialogue": dialogue}

    def update(self, world, dt):
        super().update(world, dt)
        p = world.player
        if p is not None:
            d = self.dist_to(p)
            if d < 40 or self.talking:
                self.face(p.x - self.x, p.y - self.y)
                self.set_anim("talk" if self.talking else self.idle_anim)
            else:
                self.fx, self.fy = self.home_facing
                self.set_anim(self.idle_anim)
            self.bark_cd -= dt
            if self.barks and d < self.bark_radius and self.bark_cd <= 0 and not self.talking and not world.in_dialogue:
                line = self.barks[self.bark_i % len(self.barks)]
                self.bark_i += 1
                cond = None
                if isinstance(line, tuple):
                    cond, line = line
                if cond is None or world.state.check(cond):
                    world.bark(self, line)
                self.bark_cd = random.uniform(7, 12)


class Pedestrian(Actor):
    """Walks the sidewalk lanes. Scatters at gunfire."""
    kind = "pedestrian"

    def __init__(self, x, y, sprite, lane_y, x_min, x_max, umbrella=False, speed=None):
        super().__init__(x, y, sprite, 30)
        self.lane_y = lane_y
        self.x_min, self.x_max = x_min, x_max
        self.dir = random.choice((-1, 1))
        self.speed = speed or random.uniform(26, 38)
        self.pause = 0.0
        self.panic = 0.0
        self.umbrella = umbrella
        if umbrella:
            self.overlay.append("umbrella")
        self.solid = False

    def update(self, world, dt):
        super().update(world, dt)
        p = world.player
        if self.panic > 0:
            self.panic -= dt
            sp = 95
        else:
            sp = self.speed
        if self.pause > 0 and self.panic <= 0:
            self.pause -= dt
            self.set_anim("idle")
            return
        if random.random() < dt * 0.04 and self.panic <= 0:
            self.pause = random.uniform(1.0, 3.0)
            self.fx, self.fy = 0, -1  # look at a shop window
            return
        vx = self.dir * sp
        vy = (self.lane_y - self.y) * 2.0
        # sidestep the player
        if p is not None:
            dx, dy = self.x - p.x, self.y - p.y
            if abs(dx) < 16 and abs(dy) < 10 and dx * self.dir < 0:
                vy += (1 if dy >= 0 else -1) * 40
        self.face(vx, vy * 0.2)
        nx, ny, _ = physics.move(self.x, self.y, vx * dt, vy * dt, world.area.colliders)
        if abs(nx - self.x) < abs(vx * dt) * 0.3:
            self.dir *= -1
        self.x, self.y = nx, ny
        if self.x < self.x_min:
            self.dir = 1
        elif self.x > self.x_max:
            self.dir = -1
        self.set_anim("walk", speed=sp / 34)

    def scare(self, from_x):
        self.panic = random.uniform(3.0, 5.0)
        self.dir = 1 if self.x > from_x else -1
        self.pause = 0


class Vignette:
    """A tiny scripted street scene: a sequence of barks between actors, once."""

    def __init__(self, vid: str, trigger_rect, lines, actors, once=True, flag=None, after=None):
        self.id = vid
        self.rect = trigger_rect
        self.lines = lines        # list of (actor_key, text, delay_after)
        self.actors = actors      # actor_key -> entity
        self.once = once
        self.flag = flag
        self.after = after        # callback(world) when finished
        self.running = False
        self.done = False
        self.i = 0
        self.t = 0.0

    def update(self, world, dt):
        if self.done:
            return
        p = world.player
        if not self.running:
            if p is not None and self.rect.collidepoint(p.x, p.y) and not world.in_dialogue:
                self.running = True
                self.t = 0.0
            return
        self.t -= dt
        if self.t <= 0:
            if self.i >= len(self.lines):
                self.done = True
                if self.flag:
                    world.state.set(self.flag)
                if self.after:
                    self.after(world)
                return
            key, text, delay = self.lines[self.i]
            actor = self.actors.get(key)
            if actor is not None and not actor.removed:
                world.bark(actor, text, duration=max(2.2, delay))
            self.i += 1
            self.t = delay
