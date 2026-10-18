"""The simulation: one area at a time, its entities, combat services and events.

The World never touches the screen or speakers. It emits `events` (sfx, vfx,
barks, shake, ...) that the presentation layer consumes each frame.
"""
from __future__ import annotations

import importlib
import math
import random

import pygame

from ..content.combat import BOTTLE, LANTERN, REVOLVER, TAKEDOWN
from ..content.items import ITEMS, REMNANTS
from . import perception
from .area import Area, LightSource
from .combat import Hit
from .enemy import ALERT, Enemy
from .entities import Actor, Entity, norm
from .npc import NPC, Pedestrian, Vignette
from .perception import Noise
from .player import Player


class Pickup(Entity):
    kind = "pickup"
    solid = False

    def __init__(self, x, y, item, count=1, label=None, flag=None, icon=None):
        super().__init__(x, y, None)
        self.item = item
        self.count = count
        self.flag = flag
        self.icon = icon or ITEMS.get(item, {}).get("icon", item)
        name = label or ITEMS.get(item, {}).get("name", item)
        self.interact = {"verb": "Take", "label": name}
        self.shadow = False


class Bottle(Entity):
    kind = "bottle"
    solid = False

    def __init__(self, x, y, tx, ty, thrower):
        super().__init__(x, y, None)
        self.sx, self.sy = x, y
        self.tx, self.ty = tx, ty
        d = math.hypot(tx - x, ty - y)
        self.dur = max(0.18, d / BOTTLE["speed"])
        self.t = 0.0
        self.z = 0.0
        self.thrower = thrower
        self.shadow = True


class World:
    def __init__(self, assets, state, input_, script):
        self.assets = assets
        self.state = state
        self.input = input_
        self.script = script
        self.area: Area | None = None
        self.entities: list[Entity] = []
        self.player: Player | None = None
        self.events: list[dict] = []
        self.t = 0.0
        self.freeze = 0.0
        self.noises: list[Noise] = []
        self.tokens: set[int] = set()
        self.temp_lights: list[list] = []  # [LightSource, ttl]
        self.vignettes: list[Vignette] = []
        self.triggers: list[dict] = []
        self.interactables: list[dict] = []
        self.in_dialogue = False
        self.transition: tuple | None = None
        self.area_mod = None
        self.checkpoint = None

    # ------------------------------------------------------------------ setup
    def load_area(self, area_id: str, spawn: str | tuple | None = None, keep_player=True):
        self.area = Area(area_id, self.assets)
        self.area_mod = importlib.import_module(f"deadhouse.content.areas.{area_id}")
        old = self.player
        self.entities = []
        self.vignettes = []
        self.triggers = []
        self.interactables = []
        self.tokens = set()
        self.temp_lights = []
        self.noises = []
        if isinstance(spawn, tuple):
            sx, sy = spawn
        else:
            sx, sy = self.area.spawns.get(spawn or "start", next(iter(self.area.spawns.values()), (100, 100)))
        if old is not None and keep_player:
            p = old
            p.x, p.y = float(sx), float(sy)
            p.vx = p.vy = 0
            p.set_state("free")
        else:
            p = Player(sx, sy)
            p.world_state = self.state
        self.player = p
        self.entities.append(p)
        face = self.area.defn.get("spawn_facing", {}).get(spawn if isinstance(spawn, str) else "", None)
        if face:
            p.fx, p.fy = face
        setup = getattr(self.area_mod, "setup", None)
        if setup:
            setup(self)
        self.state.set(f"visited.{area_id}")
        self.checkpoint = (area_id, (p.x, p.y))
        self.events.append({"type": "area_enter", "area": area_id})

    def death_key(self, e) -> str | None:
        name = getattr(e, "display_name", None)
        return f"dead.{self.area.id}.{name}" if name and isinstance(e, Enemy) else None

    def spawn(self, e: Entity) -> Entity:
        """Add an entity. Named enemies Ines has already put down stay down when she comes back."""
        key = self.death_key(e)
        if key and self.state.check(key):
            e.removed = True
            return e
        self.entities.append(e)
        return e

    # ------------------------------------------------------------------ queries
    def actors(self):
        return [e for e in self.entities if isinstance(e, Actor) and not e.removed]

    def enemies(self):
        return [e for e in self.entities if isinstance(e, Enemy) and not e.removed]

    def by_tag(self, tag):
        for e in self.entities:
            if e.tag == tag:
                return e
        return None

    def dynamic_colliders(self, me):
        out = []
        for e in self.entities:
            if e is me or not e.solid or e.removed:
                continue
            if isinstance(e, NPC):
                out.append(pygame.Rect(int(e.x - 4), int(e.y - 4), 8, 4))
        return out

    def dynamic_light_sources(self) -> list[LightSource]:
        out = [L for L, _ in self.temp_lights]
        p = self.player
        if p is not None and p.lantern_on:
            out.extend(self.lantern_lights(p))
        for e in self.enemies():
            if e.match_lit > 0 and not e.dead:
                out.append(LightSource(e.x + e.fx * 4, e.y - 14, 60, (1.0, 0.7, 0.35), 0.85, "buzz", e.id))
        return out

    def lantern_lights(self, p) -> list[LightSource]:
        cone = LightSource(p.x + p.fx * 2, p.y - 10 + p.fy * 2, LANTERN["radius"], (1.0, 0.86, 0.6), LANTERN["intensity"],
                           None, 0, direction=(p.fx, p.fy), cos_inner=LANTERN["cone_cos_inner"],
                           cos_outer=LANTERN["cone_cos_outer"], specular=1.4)
        glow = LightSource(p.x, p.y - 12, 34, (1.0, 0.8, 0.5), 0.6)
        return [cone, glow]

    def nearest_enemy(self, p, max_d, min_cos):
        best, bd = None, max_d
        for e in self.enemies():
            if e.dead:
                continue
            nx, ny, d = norm(e.x - p.x, e.y - p.y)
            if d < bd and (nx * p.fx + ny * p.fy) >= min_cos:
                best, bd = e, d
        return best

    # ------------------------------------------------------------------ events
    def sfx(self, name, x=None, y=None, vol=1.0):
        self.events.append({"type": "sfx", "name": name, "x": x, "y": y, "vol": vol})

    def vfx(self, kind, x, y, **kw):
        d = {"type": "vfx", "kind": kind, "x": x, "y": y}
        d.update(kw)
        self.events.append(d)

    def shake(self, amt):
        self.events.append({"type": "shake", "amount": amt})

    def hitstop(self, t):
        self.freeze = max(self.freeze, t)

    def hurt_pulse(self, amt):
        self.events.append({"type": "hurt", "amount": amt})

    def toast(self, text, dur=2.5):
        self.events.append({"type": "toast", "text": text, "dur": dur})

    def bark(self, who, text, duration=3.2, color=None):
        self.events.append({"type": "bark", "who": who, "text": text, "dur": duration, "color": color})

    def whisper(self, remnant, text, cond=None):
        """A Remnant speaking in Ines's head."""
        if remnant in self.state.remnants:
            self.events.append({"type": "whisper", "remnant": remnant, "text": text})

    def ask_remnant(self):
        from ..content.leads import hint
        r, text = hint(self.area.id, self.state)
        if r and text:
            self.events.append({"type": "whisper", "remnant": r, "text": text})

    def noise(self, x, y, radius, source, loud=False, team="neutral"):
        self.noises.append(Noise(x, y, radius, source, loud, team))

    def telegraph(self, ent, t):
        self.events.append({"type": "telegraph", "ent": ent, "t": t})

    def footstep(self, ent, loud=False):
        surf = self.area.defn.get("floor", "wet")
        self.sfx(f"step_{surf}", ent.x, ent.y, 0.5 if not loud else 0.75)
        if loud:
            r = 46
            if "silas" in self.state.remnants:
                r *= 0.6
            self.noise(ent.x, ent.y, r, "footsteps", team=ent.team)
        if surf == "wet" and random.random() < 0.6:
            self.vfx("splash", ent.x, ent.y)

    # ------------------------------------------------------------------ combat services
    def attack_tokens_free(self, e) -> bool:
        return e.id in self.tokens or len(self.tokens) < 2

    def take_attack_token(self, e):
        self.tokens.add(e.id)

    def release_attack_token(self, e):
        self.tokens.discard(e.id)

    def alert_group(self, e, x, y):
        for o in self.enemies():
            if o is e or o.dead:
                continue
            if (o.group and o.group == e.group) or math.hypot(o.x - e.x, o.y - e.y) < 90:
                if perception.line_of_sight(self.area, e.x, e.y, o.x, o.y) or o.group == e.group:
                    o.become_alert(self, x, y, shout=False)

    def enemy_bark(self, e, key):
        lines = getattr(self.area_mod, "ENEMY_BARKS", {}).get(key) or DEFAULT_BARKS.get(key)
        if lines:
            self.bark(e, random.choice(lines), 2.2, (230, 170, 150))

    def takedown_candidate(self, p):
        for e in self.enemies():
            if e.dead or e.awareness == ALERT or e.in_takedown:
                continue
            d = math.hypot(e.x - p.x, e.y - p.y)
            if d > TAKEDOWN["range"]:
                continue
            nx, ny, _ = norm(p.x - e.x, p.y - e.y)
            behind = nx * e.fx + ny * e.fy  # <0: player is behind the enemy
            if behind < TAKEDOWN["behind_cos"]:
                return e
        return None

    def complete_takedown(self, p, e):
        e.in_takedown = False
        e.hp = 0
        e._go_down(self, None)
        self.sfx("takedown", e.x, e.y)
        self.shake(1.2)
        self.noise(e.x, e.y, TAKEDOWN["noise"], "fight", team="player")
        self.state.set("did_takedown")

    def revolver_target(self, p):
        best, score = None, 1e9
        cos_lim = math.cos(math.radians(REVOLVER["cone_deg"]))
        for e in self.enemies():
            if e.dead:
                continue
            nx, ny, d = norm(e.x - p.x, e.y - p.y)
            if d > REVOLVER["range"]:
                continue
            c = nx * p.fx + ny * p.fy
            if c < cos_lim:
                continue
            if not perception.line_of_sight(self.area, p.x, p.y, e.x, e.y):
                continue
            s = d * (2 - c)
            if s < score:
                best, score = e, s
        return best

    def fire_revolver(self, p):
        if not self.state.take("rounds"):
            self.sfx("gun_empty", p.x, p.y)
            return
        tgt = self.revolver_target(p)
        mx, my = p.x + p.fx * 10, p.y - 15 + p.fy * 6
        self.sfx("gunshot", p.x, p.y)
        self.shake(4.0)
        self.events.append({"type": "flash", "amount": 0.22})
        self.temp_lights.append([LightSource(mx, my, 110, (1.0, 0.85, 0.55), 1.8), 0.07])
        self.noise(p.x, p.y, REVOLVER["noise"], "gunshot", loud=True, team="player")
        self.state.set("fired_gun")
        if tgt is not None:
            ex, ey = tgt.x, tgt.y - 14
            nx, ny, _ = norm(tgt.x - p.x, tgt.y - p.y)
            tgt.on_hit(self, Hit(REVOLVER["damage"], nx * REVOLVER["knock"], ny * REVOLVER["knock"], REVOLVER["stagger"], "bullet"))
            self.hitstop(0.07)
        else:
            ex, ey = p.x + p.fx * REVOLVER["range"], p.y - 14 + p.fy * REVOLVER["range"]
            # stop at the first wall
            steps = int(REVOLVER["range"] / 6)
            for i in range(1, steps):
                tx, ty = p.x + p.fx * i * 6, p.y + p.fy * i * 6
                if any(r.collidepoint(tx, ty) for r in self.area.colliders):
                    ex, ey = tx, ty - 14
                    self.vfx("sparks", tx, ty - 10)
                    self.sfx("ricochet", tx, ty)
                    break
            self.shoot_out_light(p.x, p.y, ex, ey + 14)
        self.vfx("tracer", mx, my, x2=ex, y2=ey)
        for ped in self.entities:
            if isinstance(ped, Pedestrian):
                ped.scare(p.x)

    def enemy_fire(self, e, p, gun):
        mx, my = e.x + e.fx * 10, e.y - 15 + e.fy * 6
        self.sfx("gunshot_enemy", e.x, e.y)
        self.temp_lights.append([LightSource(mx, my, 100, (1.0, 0.85, 0.55), 1.6), 0.07])
        self.noise(e.x, e.y, gun["noise"], "gunshot", loud=True, team="enemy")
        self.shake(2.0)
        # dodging through the shot or breaking line of sight avoids it
        los = perception.line_of_sight(self.area, e.x, e.y, p.x, p.y)
        nx, ny, d = norm(p.x - e.x, p.y - e.y)
        ex, ey = p.x, p.y - 14
        if los and d <= gun["range"]:
            hit = p.on_hit(self, Hit(gun["damage"], nx * 120, ny * 120, 0.5, "bullet"))
            if not hit:
                ex, ey = p.x + nx * 40 + random.uniform(-8, 8), p.y - 14 + ny * 40
        else:
            ex, ey = e.x + nx * min(d, 200), e.y - 14 + ny * min(d, 200)
        self.vfx("tracer", mx, my, x2=ex, y2=ey)
        for ped in self.entities:
            if isinstance(ped, Pedestrian):
                ped.scare(e.x)

    def near_miss(self, p):
        self.events.append({"type": "near_miss"})

    def lantern_flash(self, p):
        self.sfx("flash", p.x, p.y)
        self.temp_lights.append([LightSource(p.x + p.fx * 20, p.y - 10 + p.fy * 20, 120, (1.0, 0.95, 0.85), 2.4,
                                             direction=(p.fx, p.fy), cos_inner=0.9, cos_outer=0.65), 0.12])
        self.events.append({"type": "flash", "amount": 0.08})
        n = 0
        for e in self.enemies():
            if e.dead:
                continue
            nx, ny, d = norm(e.x - p.x, e.y - p.y)
            if d > LANTERN["flash_range"] or nx * p.fx + ny * p.fy < LANTERN["flash_cos"]:
                continue
            # must be looking roughly toward the light
            if -(nx * e.fx + ny * e.fy) < -0.2:
                continue
            if not perception.line_of_sight(self.area, p.x, p.y, e.x, e.y):
                continue
            e.blind(self, LANTERN["blind_time"])
            n += 1
        if n:
            self.state.set("blinded_someone")
        self.noise(p.x, p.y, 30, "flash", team="player")

    def throw_bottle(self, p):
        if not self.state.take("bottle"):
            return
        # aim: breakable light in front > enemy in front > straight ahead
        tx, ty = p.x + p.fx * BOTTLE["max_range"], p.y + p.fy * BOTTLE["max_range"]
        best = None
        bd = BOTTLE["max_range"] + 20
        for prop in self.area.props:
            if prop.state.get("breakable") and not prop.state.get("broken"):
                lx, ly = prop.state["target"]
                nx, ny, d = norm(lx - p.x, ly - p.y)
                if d < bd and nx * p.fx + ny * p.fy > 0.75:
                    best, bd = (lx, ly), d
        if best is None:
            e = self.nearest_enemy(p, BOTTLE["max_range"], 0.8)
            if e is not None:
                best = (e.x, e.y)
        if best is not None:
            tx, ty = best
        self.spawn(Bottle(p.x + p.fx * 4, p.y + p.fy * 2, tx, ty, p))
        self.sfx("throw", p.x, p.y)

    def _bottle_land(self, b: Bottle):
        b.removed = True
        self.sfx("glass", b.tx, b.ty)
        self.vfx("glass", b.tx, b.ty)
        self.noise(b.tx, b.ty, BOTTLE["noise"], "glass", team="player")
        for prop in self.area.props:
            if prop.state.get("breakable") and not prop.state.get("broken"):
                lx, ly = prop.state["target"]
                if math.hypot(lx - b.tx, ly - b.ty) <= BOTTLE["break_radius"]:
                    self.break_light(prop)
        for e in self.enemies():
            if not e.dead and math.hypot(e.x - b.tx, e.y - b.ty) < 10:
                nx, ny, _ = norm(e.x - b.sx, e.y - b.sy)
                e.on_hit(self, Hit(BOTTLE["damage"], nx * 60, ny * 60, BOTTLE["stagger"], "bottle"))

    def break_light(self, prop):
        prop.state["broken"] = True
        if prop.light is not None:
            prop.light.enabled = False
        x, y = prop.state["target"]
        self.sfx("bulb_pop", x, y)
        self.vfx("sparks", x, y - 2)
        self.state.set(f"broke.{prop.id or 'light'}")
        self.events.append({"type": "light_broken", "id": prop.id})

    def shoot_out_light(self, x0, y0, x1, y1):
        for prop in self.area.props:
            if prop.state.get("breakable") and not prop.state.get("broken"):
                lx, ly = prop.state["target"]
                # distance from point to segment
                dx, dy = x1 - x0, y1 - y0
                L2 = dx * dx + dy * dy
                if L2 <= 0:
                    continue
                t = max(0, min(1, ((lx - x0) * dx + (ly - y0) * dy) / L2))
                if math.hypot(x0 + dx * t - lx, y0 + dy * t - ly) < 8:
                    self.break_light(prop)
                    return

    def enemy_down(self, e):
        key = self.death_key(e)
        if key and not getattr(e, "respawns", False):
            self.state.set(key)
        self.events.append({"type": "enemy_down", "ent": e})
        hook = getattr(self.area_mod, "on_enemy_down", None)
        if hook:
            hook(self, e)

    def player_down(self):
        self.events.append({"type": "player_down"})

    def finish_heal(self, p):
        if self.state.take("dressing"):
            from ..content.combat import PLAYER
            p.hp = min(p.max_hp, p.hp + PLAYER["heal_amount"])
            self.toast("You tie it off. Steady hands.")

    # ------------------------------------------------------------------ interaction
    def interact_candidates(self, p):
        cands = []
        px, py = p.x + p.fx * 6, p.y + p.fy * 4
        for e in self.entities:
            if e is p or e.removed or e.interact is None:
                continue
            if isinstance(e, Actor) and e.dead:
                continue
            d = math.hypot(e.x - px, e.y - py)
            if d < 22:
                cands.append((d, e))
        for it in self.interactables:
            if it.get("hidden") and not self.state.check(it.get("show_if")):
                continue
            if it.get("done"):
                continue
            d = math.hypot(it["x"] - px, it["y"] - py)
            if d < it.get("radius", 18):
                cands.append((d - 2, it))
        cands.sort(key=lambda c: c[0])
        return [c[1] for c in cands]

    def interact_prompt(self, p):
        if p.state != "free" or self.in_dialogue:
            return None
        c = self.interact_candidates(p)
        if not c:
            return None
        t = c[0]
        if isinstance(t, dict):
            verb = t.get("verb", "Use")
            if t.get("requires") and not self.state.check(t["requires"]):
                verb = t.get("locked_verb", verb)
            return verb, t.get("label", "")
        label = getattr(t, "display_name", "") or t.interact.get("label", "")
        return t.interact.get("verb", "Use"), label

    def try_interact(self, p):
        c = self.interact_candidates(p)
        if not c:
            return
        t = c[0]
        if isinstance(t, Pickup):
            self.state.give(t.item, t.count)
            if t.flag:
                self.state.set(t.flag)
            name = ITEMS.get(t.item, {}).get("name", t.item)
            self.toast(f"{name}" + (f" ×{t.count}" if t.count > 1 else ""))
            self.sfx("pickup", t.x, t.y)
            self.events.append({"type": "pickup", "item": t.item})
            t.removed = True
            p.start_busy("interact", 0.25)
            hook = getattr(self.area_mod, "on_pickup", None)
            if hook:
                hook(self, t.item)
            return
        if isinstance(t, dict):
            hook = getattr(self.area_mod, "on_interact", None)
            if hook:
                hook(self, t)
            return
        d = t.interact.get("dialogue")
        if d:
            self.start_dialogue(d, t)

    def start_dialogue(self, node, who=None):
        self.events.append({"type": "dialogue", "node": node, "who": who})

    def request_transition(self, area_id, spawn, style="fade"):
        self.transition = (area_id, spawn, style)

    # ------------------------------------------------------------------ main update
    def update(self, dt):
        if self.freeze > 0:
            self.freeze -= dt
            return
        self.t += dt
        for L in self.temp_lights:
            L[1] -= dt
        self.temp_lights = [L for L in self.temp_lights if L[1] > 0]
        for e in list(self.entities):
            if e.removed:
                continue
            if isinstance(e, Bottle):
                e.t += dt
                k = min(1.0, e.t / e.dur)
                e.x = e.sx + (e.tx - e.sx) * k
                e.y = e.sy + (e.ty - e.sy) * k
                e.z = math.sin(k * math.pi) * 18 + 10 * (1 - k)
                if k >= 1.0:
                    self._bottle_land(e)
                continue
            e.update(self, dt)
        for n in self.noises:
            for e in self.enemies():
                e.hear(self, n)
            hook = getattr(self.area_mod, "on_noise", None)
            if hook:
                hook(self, n)
        self.noises = []
        for v in self.vignettes:
            v.update(self, dt)
        p = self.player
        if p is not None and not p.dead and self.transition is None:
            for ex in self.area.exits:
                if ex["rect"].collidepoint(p.x, p.y) and self.state.check(ex.get("requires")):
                    self.request_transition(ex["to"], ex["spawn"])
                    break
            for tr in self.triggers:
                if not tr.get("done") and tr["rect"].collidepoint(p.x, p.y) and self.state.check(tr.get("cond")):
                    if tr.get("once", True):
                        tr["done"] = True
                    tr["fn"](self)
        tick = getattr(self.area_mod, "tick", None)
        if tick:
            tick(self, dt)
        self.entities = [e for e in self.entities if not e.removed]


DEFAULT_BARKS = {
    "alert": ["There!", "Hey — you!", "Got you.", "Over here!"],
    "suspicious": ["Who's there?", "Huh?", "Somebody there?"],
    "noise": ["What was that?", "You hear that?", "...Rats again?"],
    "giveup": ["Nothing.", "Rats. Just rats.", "Getting jumpy."],
    "body": ["Christ — Lenny?", "Somebody did him!"],
    "blinded": ["My eyes—!", "Can't see!"],
    "reload": ["Hold still, damn you.", "Loading—"],
}
