"""Ines Calder: movement, melee combo, dodge, revolver, bottles, lantern, takedowns."""
from __future__ import annotations

import math

from ..content.combat import BOTTLE, DODGE, LANTERN, PLAYER, REVOLVER, TAKEDOWN, WEAPONS
from . import combat, physics
from .entities import Actor, norm


class Player(Actor):
    kind = "player"

    def __init__(self, x, y):
        super().__init__(x, y, "ines", PLAYER["hp"])
        self.team = "player"
        self.state = "free"
        self.combo_i = 0
        self.combo_timer = 0.0
        self.swing = None
        self.swing_done = False
        self.dodge_dir = (0.0, 1.0)
        self.dodge_cd = 0.0
        self.shoot_cd = 0.0
        self.flash_cd = 0.0
        self.lantern_on = False
        self.is_sprinting = False
        self.step_acc = 0.0
        self.locked = False   # dialogue / cutscene
        self.takedown_target = None
        self.pending_shot = False
        self.heal_t = 0.0
        self.anim_override = None
        self.lantern_dir = (0.0, 1.0)

    # ------------------------------------------------------------------ helpers
    @property
    def weapon(self) -> dict:
        return WEAPONS[self.world_state.equipped]

    def can_act(self) -> bool:
        return self.state in ("free",) and not self.locked

    def in_recover(self) -> bool:
        return self.state in ("attack", "heavy") and self.swing_done and self.state_t > self.swing["windup"] + self.swing["active"] + 0.04

    # ------------------------------------------------------------------ update
    def update(self, world, dt):
        super().update(world, dt)
        self.world_state = world.state
        inp = world.input
        self.state_t += dt
        self.iframes = max(0.0, self.iframes - dt)
        self.dodge_cd = max(0.0, self.dodge_cd - dt)
        self.shoot_cd = max(0.0, self.shoot_cd - dt)
        self.flash_cd = max(0.0, self.flash_cd - dt)
        self.combo_timer = max(0.0, self.combo_timer - dt)
        if self.bleed_t > 0:
            self.bleed_t -= dt
        if self.dead:
            self._move(world, 0, 0, dt)
            return
        ax, ay = (0.0, 0.0) if self.locked else tuple(inp.axis)

        if self.state == "free":
            self._free(world, inp, ax, ay, dt)
        elif self.state in ("attack", "heavy"):
            self._attacking(world, inp, ax, ay, dt)
        elif self.state == "dodge":
            t = self.state_t / DODGE["time"]
            sp = DODGE["speed"] * (1 - t) ** 1.4 + 20
            self.vx, self.vy = self.dodge_dir[0] * sp, self.dodge_dir[1] * sp
            self._move(world, self.vx, self.vy, dt)
            if self.state_t >= DODGE["time"]:
                self.set_state("free")
                self.dodge_cd = DODGE["cooldown"]
        elif self.state == "hurt":
            self._move(world, self.vx * 0.2, self.vy * 0.2, dt)
            if self.state_t >= self.hurt_time:
                self.set_state("free")
        elif self.state == "shoot":
            self._move(world, 0, 0, dt)
            if self.pending_shot and self.state_t >= REVOLVER["draw_time"]:
                self.pending_shot = False
                world.fire_revolver(self)
                self.set_anim("shoot", restart=True)
            if self.state_t >= REVOLVER["draw_time"] + 0.24:
                if inp.peek("shoot") and world.state.count("rounds") > 0 and self.shoot_cd <= 0:
                    inp.consume("shoot")
                    self._start_shot(world)
                else:
                    self.set_state("free")
        elif self.state == "throw":
            self._move(world, 0, 0, dt)
            if self.state_t >= 0.16 and not self.swing_done:
                self.swing_done = True
                world.throw_bottle(self)
            if self.state_t >= 0.34:
                self.set_state("free")
        elif self.state == "takedown":
            self._move(world, 0, 0, dt)
            tgt = self.takedown_target
            if tgt is not None and not self.swing_done and self.state_t > 0.55:
                self.swing_done = True
                world.complete_takedown(self, tgt)
            if self.state_t >= TAKEDOWN["time"]:
                self.takedown_target = None
                self.set_state("free")
        elif self.state == "heal":
            self._move(world, 0, 0, dt)
            if self.state_t >= PLAYER["heal_time"]:
                world.finish_heal(self)
                self.set_state("free")
        elif self.state == "busy":  # scripted actions: interact, break, climb
            self._move(world, 0, 0, dt)
            if self.state_t >= self.busy_time:
                cb = self.busy_cb
                self.busy_cb = None
                self.set_state("free")
                if cb:
                    cb()
        self._animate()

    def _free(self, world, inp, ax, ay, dt):
        sprint = inp.held["sprint"] and (ax or ay)
        self.is_sprinting = bool(sprint)
        target = PLAYER["sprint"] if sprint else PLAYER["walk"]
        tvx, tvy = ax * target, ay * target
        rate = PLAYER["accel"] * dt
        self.vx += max(-rate, min(rate, tvx - self.vx))
        self.vy += max(-rate, min(rate, tvy - self.vy))
        if ax or ay:
            self.face(ax, ay)
        self._move(world, self.vx, self.vy, dt)
        speed = math.hypot(self.vx, self.vy)
        if speed > 10:
            self.step_acc += speed * dt
            stride = 15 if sprint else 12
            if self.step_acc >= stride:
                self.step_acc = 0
                world.footstep(self, loud=bool(sprint))
        if self.locked:
            return
        # actions (buffered)
        if inp.consume("dodge") and self.dodge_cd <= 0:
            self._start_dodge(ax, ay)
        elif inp.consume("attack"):
            tgt = world.takedown_candidate(self)
            if tgt is not None:
                self._start_takedown(world, tgt)
            else:
                self._start_swing(world, heavy=False)
        elif inp.consume("heavy"):
            self._start_swing(world, heavy=True)
        elif inp.consume("shoot"):
            if world.state.has("revolver"):
                if world.state.count("rounds") > 0 and self.shoot_cd <= 0:
                    self._start_shot(world)
                elif world.state.count("rounds") <= 0:
                    world.sfx("gun_empty", self.x, self.y)
                    world.toast("No rounds left.")
        elif inp.consume("throw"):
            if world.state.count("bottle") > 0:
                self.set_state("throw")
                self.swing_done = False
                self.set_anim("throw", restart=True)
                self.vx = self.vy = 0
            else:
                world.toast("No bottles. Look in the trash — this city never runs out.")
        elif inp.consume("lantern"):
            if world.state.has("lantern"):
                self.lantern_on = not self.lantern_on
                world.sfx("lantern_on" if self.lantern_on else "lantern_off", self.x, self.y)
        elif inp.consume("flash"):
            if world.state.has("lantern") and self.lantern_on and self.flash_cd <= 0:
                self.flash_cd = LANTERN["flash_cooldown"]
                world.lantern_flash(self)
        elif inp.consume("heal"):
            if world.state.count("dressing") > 0 and self.hp < self.max_hp:
                self.set_state("heal")
                self.vx = self.vy = 0
                world.sfx("dressing", self.x, self.y)
            elif world.state.count("dressing") <= 0:
                world.toast("No dressings left.")
        elif inp.consume("interact"):
            world.try_interact(self)
        elif inp.consume("remnant"):
            world.ask_remnant()

    def _attacking(self, world, inp, ax, ay, dt):
        sw = self.swing
        t = self.state_t
        slow = 0.25 if t < sw["windup"] + sw["active"] else 0.45
        if ax or ay:
            if t < sw["windup"] * 0.6:
                self.face(ax, ay)  # small aim window at the start of a swing
        if not self.swing_done and t >= sw["windup"]:
            self.swing_done = True
            lunge = 70 if self.state == "attack" else 40
            self.vx += self.fx * lunge
            self.vy += self.fy * lunge
            mul = 1.0
            combat.swing(world, self, sw, bleed=self.weapon.get("bleed", 0.0), damage_mul=mul)
        self.vx *= max(0.0, 1 - dt * 10)
        self.vy *= max(0.0, 1 - dt * 10)
        self._move(world, self.vx + ax * PLAYER["walk"] * slow * 0.3, self.vy + ay * PLAYER["walk"] * slow * 0.3, dt)
        end = sw["windup"] + sw["active"] + sw["recover"]
        if self.in_recover():
            if inp.peek("dodge") and self.dodge_cd <= 0:
                inp.consume("dodge")
                self._start_dodge(ax, ay)
                return
            if self.state == "attack" and inp.peek("attack") and t > end * 0.6:
                inp.consume("attack")
                self._start_swing(world, heavy=False)
                return
            if inp.peek("heavy") and t > end * 0.7:
                inp.consume("heavy")
                self._start_swing(world, heavy=True)
                return
        if t >= end:
            self.set_state("free")
            self.combo_timer = 0.32

    def _start_swing(self, world, heavy: bool):
        w = self.weapon
        if heavy:
            self.swing = w["heavy"]
            self.combo_i = 0
            self.set_state("heavy")
        else:
            if self.combo_timer <= 0 and self.state == "free":
                self.combo_i = 0
            combo = w["combo"]
            self.swing = combo[self.combo_i % len(combo)]
            self.combo_i = (self.combo_i + 1) % len(combo)
            self.set_state("attack")
        self.swing_done = False
        # gentle aim assist: turn toward the nearest enemy in front
        tgt = world.nearest_enemy(self, 40, 0.3)
        if tgt is not None:
            self.face(tgt.x - self.x, tgt.y - self.y)
        total = self.swing["windup"] + self.swing["active"] + self.swing["recover"]
        frames = {"attack1": 4, "attack2": 4, "attack3": 5, "heavy": 6}[self.swing["anim"]]
        fps = {"attack1": 18, "attack2": 18, "attack3": 16, "heavy": 12}[self.swing["anim"]]
        self.set_anim(self.swing["anim"], restart=True, speed=(frames / fps) / total)
        self.vx *= 0.3
        self.vy *= 0.3

    def _start_dodge(self, ax, ay):
        if ax or ay:
            nx, ny, _ = norm(ax, ay)
        else:
            nx, ny = -self.fx, -self.fy  # backstep
        self.dodge_dir = (nx, ny)
        if ax or ay:
            self.face(nx, ny)
        self.iframes = DODGE["iframes"]
        self.set_state("dodge")
        self.set_anim("dodge", restart=True)
        self.world_state_dodge = True

    def _start_shot(self, world):
        tgt = world.revolver_target(self)
        if tgt is not None:
            self.face(tgt.x - self.x, tgt.y - self.y)
        self.set_state("shoot")
        self.pending_shot = True
        self.shoot_cd = REVOLVER["cooldown"]
        self.set_anim("aim", restart=True)
        self.vx = self.vy = 0

    def _start_takedown(self, world, tgt):
        self.takedown_target = tgt
        self.face(tgt.x - self.x, tgt.y - self.y)
        self.set_state("takedown")
        self.swing_done = False
        self.set_anim("takedown", restart=True, speed=0.55)
        tgt.begin_takedown(world, self)
        self.vx = self.vy = 0

    def start_busy(self, anim: str, duration: float, cb=None, speed=1.0):
        self.set_state("busy")
        self.busy_time = duration
        self.busy_cb = cb
        self.set_anim(anim, restart=True, speed=speed)
        self.vx = self.vy = 0

    def _move(self, world, vx, vy, dt):
        kx, ky = self.apply_knock(dt)
        self.x, self.y, _ = physics.move(self.x, self.y, vx * dt + kx, vy * dt + ky, world.area.colliders,
                                         extra=world.dynamic_colliders(self))

    def _animate(self):
        s = self.state
        if s == "free":
            sp = math.hypot(self.vx, self.vy)
            if sp > 80:
                self.set_anim("run", speed=sp / 104)
            elif sp > 8:
                self.set_anim("walk", speed=max(0.6, sp / 64))
            else:
                self.set_anim("idle")
        elif s == "hurt":
            self.set_anim("hit")
        elif s == "heal":
            self.set_anim("interact", speed=0.25)
        elif s == "down":
            self.set_anim("down")

    # ------------------------------------------------------------------ damage
    def on_hit(self, world, hit) -> bool:
        if self.dead or self.iframes > 0 or self.state == "dodge":
            if self.state == "dodge" and not self.dead:
                world.near_miss(self)
            return False
        self.hp -= hit.damage
        combat.damage_feedback(world, self, hit)
        world.shake(3.0 if hit.kind == "bullet" else 2.2)
        world.hurt_pulse(min(1.0, hit.damage / 30))
        self.knock_vx, self.knock_vy = hit.kx * 0.9, hit.ky * 0.9
        if self.hp <= 0:
            self.hp = 0
            self.dead = True
            self.set_state("down")
            self.set_anim("down", restart=True)
            world.player_down()
            return True
        if self.state in ("takedown",) and self.takedown_target is not None:
            self.takedown_target.cancel_takedown(world)
            self.takedown_target = None
        self.hurt_time = 0.22 + hit.stagger * 0.5
        self.iframes = 0.35
        self.set_state("hurt")
        self.set_anim("hit", restart=True)
        return True
