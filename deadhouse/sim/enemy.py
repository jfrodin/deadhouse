"""Enemy AI: patrol/idle -> suspicious -> alert -> attack, with light-based perception.

Behaviour differences are data-driven (content.combat.ENEMIES) plus a few flags:
  keep_distance  gunman holds range and aims with a visible telegraph
  lights_match   knifeman strikes a match when he can't see (and becomes a target)
"""
from __future__ import annotations

import math
import random

from ..content.combat import ENEMIES
from . import combat, perception, physics
from .entities import Actor, norm

ALERT, SUSPICIOUS, CALM = "alert", "suspicious", "calm"


class Enemy(Actor):
    kind = "enemy"

    def __init__(self, x, y, etype: str, facing=(0, 1), name=None, post=None, patrol=None, group=None):
        d = ENEMIES[etype]
        super().__init__(x, y, d["sprite"], d["hp"])
        self.etype = etype
        self.d = d
        self.team = "enemy"
        self.display_name = name or d["name"]
        self.fx, self.fy = facing
        self.awareness = CALM
        self.suspicion = 0.0
        self.last_seen = None
        self.investigate = None
        self.post = post or (x, y)
        self.post_facing = facing
        self.patrol = patrol or []
        self.patrol_i = 0
        self.patrol_wait = 0.0
        self.group = group
        self.attack = None
        self.attack_done = False
        self.flurry_left = 0
        self.cooldown = random.uniform(0.3, 0.8)
        self.poise = d["poise"]
        self.blind_t = 0.0
        self.stun_t = 0.0
        self.think_t = random.uniform(0, 0.1)
        self.rounds = d.get("gun", {}).get("rounds", 0)
        self.aim_t = 0.0
        self.match_lit = 0.0
        self.match_cd = 0.0
        self.down_t = 0.0
        self.in_takedown = False
        self.strafe = random.choice((-1, 1))
        self.bark_cd = 0.0
        self.seen_body = set()

    # ------------------------------------------------------------------ helpers
    def _move(self, world, vx, vy, dt):
        kx, ky = self.apply_knock(dt)
        nx, ny, _ = physics.move(self.x, self.y, vx * dt + kx, vy * dt + ky, world.area.colliders,
                                 extra=world.dynamic_colliders(self))
        moved = math.hypot(nx - self.x, ny - self.y)
        self.x, self.y = nx, ny
        return moved

    def _seek(self, world, tx, ty, speed, dt, stop=4.0):
        dx, dy = tx - self.x, ty - self.y
        nx, ny, d = norm(dx, dy)
        if d <= stop:
            return True
        # steer around other enemies
        for e in world.enemies():
            if e is self or e.dead:
                continue
            ox, oy = self.x - e.x, self.y - e.y
            od = math.hypot(ox, oy)
            if 0 < od < 14:
                nx += ox / od * 0.6
                ny += oy / od * 0.6
        nx, ny, _ = norm(nx, ny)
        self.face(nx, ny)
        moved = self._move(world, nx * speed, ny * speed, dt)
        if moved < speed * dt * 0.25:
            # blocked: try sliding sideways
            self._move(world, -ny * speed * self.strafe, nx * speed * self.strafe, dt)
        return False

    def bark(self, world, key: str):
        if self.bark_cd <= 0:
            world.enemy_bark(self, key)
            self.bark_cd = 3.5

    def become_alert(self, world, x, y, shout=True):
        was = self.awareness
        self.awareness = ALERT
        self.suspicion = 1.0
        self.last_seen = (x, y)
        if was != ALERT and shout:
            self.bark(world, "alert")
            world.alert_group(self, x, y)
            world.sfx("alert_sting", self.x, self.y, 0.55)

    # ------------------------------------------------------------------ perception
    def perceive(self, world, dt):
        p = world.player
        if p is None or p.dead:
            if self.awareness == ALERT:
                self.awareness = SUSPICIOUS
            return
        sight = self.d["sight"] * (0.25 if self.blind_t > 0 else 1.0)
        cone = 0.15 if self.awareness == ALERT else 0.3
        seen, strength = perception.can_see(world, self, p, sight, cone)
        if self.match_lit > 0:
            seen2, s2 = perception.can_see(world, self, p, sight + 40, cone)
            seen, strength = seen or seen2, max(strength, s2)
        if seen:
            if self.awareness == ALERT:
                self.last_seen = (p.x, p.y)
            else:
                rate = strength * (3.2 if self.awareness == SUSPICIOUS else 2.2)
                self.suspicion += rate * 0.1 / max(0.2, self.d["react"])
                self.investigate = (p.x, p.y)
                if self.suspicion >= 1.0:
                    self.become_alert(world, p.x, p.y)
                elif self.suspicion >= 0.35 and self.awareness == CALM:
                    self.awareness = SUSPICIOUS
                    self.bark(world, "suspicious")
        else:
            if self.awareness != ALERT:
                self.suspicion = max(0.0, self.suspicion - 0.1 * 0.25)
        # downed comrades are noticed
        for e in world.enemies():
            if e is not self and e.dead and e.id not in self.seen_body:
                s, _ = perception.can_see(world, self, e, 120, 0.2)
                if s:
                    self.seen_body.add(e.id)
                    if self.awareness != ALERT:
                        self.awareness = SUSPICIOUS
                        self.suspicion = max(self.suspicion, 0.7)
                        self.investigate = (e.x, e.y)
                        self.bark(world, "body")

    def hear(self, world, noise: perception.Noise):
        if self.dead or noise.team == "enemy":
            return
        d = math.hypot(noise.x - self.x, noise.y - self.y)
        r = noise.radius * self.d["hearing"]
        if d > r:
            return
        if noise.loud and d < r * 0.6:
            self.become_alert(world, noise.x, noise.y)
            return
        if self.awareness != ALERT:
            self.awareness = SUSPICIOUS
            self.suspicion = max(self.suspicion, 0.5 if noise.loud else 0.4)
            self.investigate = (noise.x, noise.y)
            self.bark(world, "noise")
        else:
            self.last_seen = (noise.x, noise.y)

    # ------------------------------------------------------------------ update
    def update(self, world, dt):
        super().update(world, dt)
        self.state_t += dt
        self.cooldown = max(0.0, self.cooldown - dt)
        self.bark_cd = max(0.0, self.bark_cd - dt)
        self.match_cd = max(0.0, self.match_cd - dt)
        if self.match_lit > 0:
            self.match_lit -= dt
        if self.bleed_t > 0 and not self.dead:
            self.bleed_t -= dt
            self.hp -= self.bleed_dps * dt
            if self.hp <= 0:
                self._go_down(world, None)
        if self.dead:
            self.down_t += dt
            self._move(world, 0, 0, dt)
            self.set_anim("down")
            return
        if self.in_takedown:
            self._move(world, 0, 0, dt)
            return
        self.think_t -= dt
        if self.think_t <= 0:
            self.think_t = 0.1
            self.perceive(world, dt)
        if self.blind_t > 0:
            self.blind_t -= dt
            self.set_anim("blinded")
            self._move(world, math.sin(self.state_t * 5) * 8, 0, dt)
            if self.blind_t <= 0 and self.awareness != ALERT:
                self.become_alert(world, *(self.last_seen or (self.x, self.y)))
            return
        if self.stun_t > 0:
            self.stun_t -= dt
            self._move(world, 0, 0, dt)
            self.set_anim("stagger" if self.stun_t > 0.25 else "hit")
            return
        if self.attack is not None:
            self._run_attack(world, dt)
            return
        if self.awareness == ALERT:
            self._combat(world, dt)
        elif self.awareness == SUSPICIOUS:
            self._investigate(world, dt)
        else:
            self._calm(world, dt)

    def _calm(self, world, dt):
        if self.patrol:
            tx, ty = self.patrol[self.patrol_i]
            if self.patrol_wait > 0:
                self.patrol_wait -= dt
                self.set_anim("idle")
                self._move(world, 0, 0, dt)
            elif self._seek(world, tx, ty, self.d["walk"] * 0.75, dt):
                self.patrol_i = (self.patrol_i + 1) % len(self.patrol)
                self.patrol_wait = random.uniform(1.5, 3.5)
            else:
                self.set_anim("walk", speed=0.8)
        else:
            if math.hypot(self.post[0] - self.x, self.post[1] - self.y) > 5:
                self._seek(world, self.post[0], self.post[1], self.d["walk"] * 0.8, dt)
                self.set_anim("walk", speed=0.8)
            else:
                self.fx, self.fy = self.post_facing
                self._move(world, 0, 0, dt)
                self.set_anim("smoke" if self.etype == "brawler" and self.group == "ground" else "idle")

    def _investigate(self, world, dt):
        # knifeman strikes a match in the dark
        if self.d.get("lights_match") and self.match_lit <= 0 and self.match_cd <= 0:
            lum = world.area.light_at(self.x, self.y - 12, world.t, world.dynamic_light_sources())
            if lum < 0.3:
                self.match_lit = 6.0
                self.match_cd = 12.0
                world.sfx("match", self.x, self.y)
                self.set_anim("match", restart=True)
        tgt = self.investigate
        if tgt is None:
            self.awareness = CALM
            return
        if self._seek(world, tgt[0], tgt[1], self.d["walk"], dt, stop=8):
            self.set_anim("idle")
            # look around, then give up
            self.fx, self.fy = math.cos(self.state_t * 1.3), math.sin(self.state_t * 1.3)
            self.suspicion -= dt * 0.12
            if self.suspicion <= 0.15:
                self.awareness = CALM
                self.investigate = None
                self.bark(world, "giveup")
        else:
            self.set_anim("walk")

    def _combat(self, world, dt):
        p = world.player
        if p is None or p.dead:
            self.awareness = SUSPICIOUS
            return
        seen = self.last_seen or (p.x, p.y)
        dx, dy = p.x - self.x, p.y - self.y
        d = math.hypot(dx, dy)
        visible = perception.line_of_sight(world.area, self.x, self.y, p.x, p.y)
        if visible and d < self.d["sight"] + 60:
            self.last_seen = (p.x, p.y)
            seen = self.last_seen
        gun = self.d.get("gun")
        if gun:
            self._gunman(world, p, d, visible, dt)
            return
        pref = self.d["preferred_range"]
        if d > pref + 2:
            if self._seek(world, seen[0], seen[1], self.d["run"], dt, stop=pref):
                pass
            self.set_anim("run")
        else:
            self.face(dx, dy)
            # circle a little while waiting for an opening
            sx, sy = -self.fy * self.strafe, self.fx * self.strafe
            self._move(world, sx * 18, sy * 18, dt)
            self.set_anim("walk", speed=0.6)
            if self.cooldown <= 0 and world.attack_tokens_free(self):
                self._begin_attack(world)
        if not visible and math.hypot(seen[0] - self.x, seen[1] - self.y) < 10:
            self.awareness = SUSPICIOUS
            self.investigate = seen
            self.suspicion = 0.8

    def _gunman(self, world, p, d, visible, dt):
        gun = self.d["gun"]
        if d < 22 and self.cooldown <= 0:
            self._begin_attack(world)  # pistol whip
            return
        if self.rounds <= 0:
            self.aim_t = 0
            self.state_t += 0
            if not hasattr(self, "reload_t") or self.reload_t <= 0:
                self.reload_t = gun["reload"]
                world.sfx("reload", self.x, self.y)
                self.bark(world, "reload")
            self.reload_t -= dt
            self.set_anim("idle")
            # back off while reloading
            nx, ny, _ = norm(self.x - p.x, self.y - p.y)
            self._move(world, nx * 22, ny * 22, dt)
            if self.reload_t <= 0:
                self.rounds = gun["rounds"]
            return
        if not visible:
            self.aim_t = 0
            seen = self.last_seen
            if seen:
                self._seek(world, seen[0], seen[1], self.d["walk"], dt, stop=6)
                self.set_anim("walk")
            return
        self.face(p.x - self.x, p.y - self.y)
        if self.cooldown > 0:
            self.set_anim("aim")
            self._move(world, 0, 0, dt)
            return
        self.aim_t += dt
        self.set_anim("aim")
        self._move(world, 0, 0, dt)
        if self.aim_t >= gun["aim"]:
            self.aim_t = 0
            self.rounds -= 1
            self.cooldown = gun["cooldown"]
            world.enemy_fire(self, p, gun)

    def _begin_attack(self, world):
        atks = self.d["attacks"]
        total = sum(a["weight"] for a in atks)
        r = random.uniform(0, total)
        for a in atks:
            r -= a["weight"]
            if r <= 0:
                break
        self.attack = a
        self.attack_done = False
        self.flurry_left = a.get("flurry", 1)
        self.set_state("attack")
        world.take_attack_token(self)
        p = world.player
        self.face(p.x - self.x, p.y - self.y)
        frames = {"windup": 2, "heavy": 6, "attack1": 4, "attack3": 5}[a["anim"]]
        self.set_anim(a["anim"], restart=True,
                      speed=(frames / {"windup": 6, "heavy": 12, "attack1": 18, "attack3": 16}[a["anim"]]) / (a["windup"] + a["active"]))
        if a["windup"] >= 0.6:
            world.telegraph(self, a["windup"])

    def _run_attack(self, world, dt):
        a = self.attack
        t = self.state_t
        p = world.player
        if t < a["windup"] * 0.7 and p is not None:
            self.face(p.x - self.x, p.y - self.y)
        if not self.attack_done and t >= a["windup"]:
            self.attack_done = True
            self.knock_vx += self.fx * 60
            self.knock_vy += self.fy * 60
            combat.swing(world, self, a)
            if a["anim"] == "windup":
                self.set_anim("attack1", restart=True)
        self._move(world, 0, 0, dt)
        if t >= a["windup"] + a["active"] + (a["recover"] if self.flurry_left <= 1 else a.get("gap", 0.1)):
            self.flurry_left -= 1
            if self.flurry_left > 0:
                self.attack_done = False
                self.set_state("attack")
                self.state_t = a["windup"] * 0.5
                self.set_anim(a["anim"], restart=True, speed=2.0)
            else:
                self.attack = None
                self.set_state("idle")
                self.cooldown = random.uniform(0.5, 1.2)
                world.release_attack_token(self)
                self.strafe *= -1

    # ------------------------------------------------------------------ damage
    def on_hit(self, world, hit) -> bool:
        if self.dead:
            return False
        surprised = self.awareness != ALERT
        dmg = hit.damage * (1.6 if surprised and hit.kind == "melee" else 1.0)
        self.hp -= dmg
        combat.damage_feedback(world, self, hit)
        if hit.bleed > 0:
            self.bleed_t = 3.0
            self.bleed_dps = hit.bleed
        self.knock_vx, self.knock_vy = hit.kx, hit.ky
        if self.hp <= 0:
            self._go_down(world, hit)
            return True
        self.poise -= dmg
        if self.attack is not None and (self.poise <= 0 or hit.guard_break or hit.kind == "bullet"):
            self.attack = None
            world.release_attack_token(self)
        if self.poise <= 0 or hit.stagger >= 0.5 or self.attack is None:
            self.stun_t = hit.stagger
            if self.poise <= 0:
                self.stun_t += 0.4
                self.poise = self.d["poise"]
        p = world.player
        if p is not None:
            self.become_alert(world, p.x, p.y)
        return True

    def _go_down(self, world, hit):
        self.dead = True
        self.hp = 0
        self.attack = None
        world.release_attack_token(self)
        self.set_anim("down", restart=True)
        world.sfx("body_fall", self.x, self.y)
        world.enemy_down(self)

    def begin_takedown(self, world, by):
        self.in_takedown = True
        self.set_anim("takedown_victim", restart=True, speed=0.5)
        self.face(self.x - by.x, self.y - by.y)

    def cancel_takedown(self, world):
        self.in_takedown = False
        self.become_alert(world, world.player.x, world.player.y)

    def blind(self, world, t):
        if self.dead:
            return
        self.blind_t = t
        self.attack = None
        world.release_attack_token(self)
        self.aim_t = 0
        self.bark(world, "blinded")
