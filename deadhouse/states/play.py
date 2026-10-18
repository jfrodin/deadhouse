"""The main gameplay state: drives the World and presents it (scene, UI, audio)."""
from __future__ import annotations

import math
import os
import random

import pygame

from .. import config as C
from ..content.combat import WEAPONS
from ..content.items import ITEMS, REMNANTS
from ..engine.renderer import Light, PostParams, Quad
from ..render.assets import Assets
from ..render.scene import SceneRenderer
from ..render.sprites import Sheet, draw_weapon, lantern_sprite, umbrella_sprite
from ..render.ui import UI
from ..render.vfx import VFX
from ..sim.dialogue import Menu, Runner, Say, Script
from ..sim.enemy import Enemy
from ..sim.entities import Actor
from ..sim.npc import NPC, Pedestrian
from ..sim.player import Player
from ..sim.state import GameState
from ..sim.world import Bottle, Pickup, World

PORTRAITS = {"vivienne": ("neutral", "amused", "cold", "warm")}


class DialogueView:
    def __init__(self, runner: Runner, who, portraits):
        self.runner = runner
        self.who = who
        self.sel = 0
        self.reveal = 0.0
        self.last_line = None
        self.portraits = portraits
        self.expr = {}
        self._sync()

    @property
    def current(self):
        return self.runner.current

    @property
    def mode(self):
        c = self.runner.current
        if isinstance(c, Say):
            return "say"
        if isinstance(c, Menu):
            return "menu"
        return "end"

    @property
    def choices(self):
        return self.runner.visible_choices

    @property
    def portrait(self):
        c = self.runner.current
        sp = None
        if isinstance(c, Say) and c.speaker in self.portraits:
            sp = c.speaker
        elif self.last_line is not None and self.last_line.speaker in self.portraits:
            sp = self.last_line.speaker
        elif self.who is not None and getattr(self.who, "portrait", None):
            sp = self.who.portrait
        if sp is None:
            return None
        return sp, self.expr.get(sp, "neutral")

    def _sync(self):
        c = self.runner.current
        if isinstance(c, Say):
            self.reveal = 0.0
            if c.expr and c.speaker in self.portraits:
                self.expr[c.speaker] = c.expr
            self.last_line = c
        self.sel = 0

    def update(self, dt, inp, sfx):
        c = self.runner.current
        if isinstance(c, Say):
            before = int(self.reveal)
            self.reveal = min(len(c.text), self.reveal + dt * 55)
            if int(self.reveal) // 6 != before // 6 and int(self.reveal) < len(c.text):
                sfx("type", 0.25)
            if inp.consume("confirm") or inp.consume("attack"):
                if self.reveal < len(c.text):
                    self.reveal = len(c.text)
                else:
                    self.runner.advance()
                    self._sync()
                    sfx("ui_next", 0.4)
        elif isinstance(c, Menu):
            n = len(self.runner.visible_choices)
            if inp.pressed["up"]:
                self.sel = (self.sel - 1) % n
                sfx("ui_move", 0.35)
            if inp.pressed["down"]:
                self.sel = (self.sel + 1) % n
                sfx("ui_move", 0.35)
            if inp.consume("confirm") or inp.consume("attack"):
                sfx("ui_select", 0.5)
                self.runner.advance(self.sel)
                self._sync()


class InventoryView:
    def __init__(self, world):
        self.world = world
        self.col = 0
        self.row = 0
        self.rebuild()

    def rebuild(self):
        st = self.world.state
        weapons = [(w, WEAPONS[w]["name"] + ("  *" if st.equipped == w else "")) for w in ("razor", "tire_iron") if st.has(w)]
        tools, items, keys = [], [], []
        for k, n in st.inventory.items():
            it = ITEMS.get(k, {})
            kind = it.get("kind")
            label = it.get("name", k) + (f"  x{n}" if n > 1 else "")
            if kind in ("gun", "tool", "debug"):
                tools.append((k, label))
            elif kind in ("consumable", "throwable", "ammo"):
                items.append((k, label))
            elif kind == "key":
                keys.append((k, label))
        rem = [(r, REMNANTS[r]["name"]) for r in st.remnants]
        from ..content.leads import active
        self.leads = active(st)
        leads = [(f"lead:{i}", ("[done] " if done else "") + title) for i, (title, text, done) in enumerate(self.leads)]
        self.columns = [("Weapons", weapons), ("Tools", tools), ("Items", items), ("Evidence", keys)]
        if rem:
            self.columns.append(("Remnants", rem))
        if leads:
            self.columns.append(("Leads", leads))
        self.columns = [c for c in self.columns if c[1]] or [("Empty", [])]
        self.col = min(self.col, len(self.columns) - 1)
        self.row = min(self.row, max(0, len(self.columns[self.col][1]) - 1))

    def selected_key(self):
        rows = self.columns[self.col][1]
        if not rows:
            return None
        return rows[self.row][0]

    def update(self, inp, sfx):
        if inp.pressed["left"]:
            self.col = (self.col - 1) % len(self.columns)
            self.row = 0
            sfx("ui_move", 0.3)
        if inp.pressed["right"]:
            self.col = (self.col + 1) % len(self.columns)
            self.row = 0
            sfx("ui_move", 0.3)
        rows = self.columns[self.col][1]
        if rows:
            if inp.pressed["up"]:
                self.row = (self.row - 1) % len(rows)
                sfx("ui_move", 0.3)
            if inp.pressed["down"]:
                self.row = (self.row + 1) % len(rows)
                sfx("ui_move", 0.3)
        if inp.consume("interact") or inp.consume("confirm"):
            k = self.selected_key()
            st = self.world.state
            if k in WEAPONS:
                st.equipped = k
                sfx("equip", 0.6)
                self.rebuild()
            elif k == "dressing" and self.world.player.hp < self.world.player.max_hp:
                self.world.player.set_state("heal")
                return "close"
            elif k == "testkit":
                hook = self.world.hooks().get("testkit")
                if hook:
                    hook()
                    self.rebuild()
        return None


class PlayState:
    def __init__(self, app, area_id="row", spawn=None, state: GameState | None = None):
        self.app = app
        self.assets = Assets()
        self.scene = SceneRenderer(self.assets)
        self.ui = UI()
        self.vfx = VFX()
        self.state = state or self.new_game_state()
        self.script = Script.load_dir(os.path.join(C.CONTENT_DIR, "dialogue"))
        self.world = World(self.assets, self.state, app.input, self.script)
        self.world.hooks = self._hooks
        self.sheets: dict[str, Sheet] = {}
        self.audio = getattr(app, "audio", None)
        if spawn and "," in str(spawn):
            sp = tuple(float(v) for v in spawn.split(","))
        else:
            sp = spawn
        self.world.load_area(area_id, sp, keep_player=False)
        p = self.world.player
        self.cam = [p.x - C.VIEW_W / 2, p.y - C.VIEW_H / 2]
        self._clamp_cam()
        self.shake = 0.0
        self.flash = 0.0
        self.hurt = 0.0
        self.fade = 1.0
        self.fade_dir = -1
        self.pending = None
        self.dialogue: DialogueView | None = None
        self.inventory: InventoryView | None = None
        self.paused = False
        self.dead_t = None
        self.show_fps = False
        self.lantern_imgs = lantern_sprite()
        self.umbrella = umbrella_sprite()
        self.t = 0.0
        self.portrait_cache = set()
        self.attract = False
        self._on_area_enter()

    @staticmethod
    def new_game_state() -> GameState:
        g = GameState()
        for item, n in (("razor", 1), ("revolver", 1), ("rounds", 3), ("bottle", 2), ("dressing", 2), ("matches", 1)):
            g.give(item, n)
        g.remnants = ["silas"]
        return g

    # ------------------------------------------------------------------ plumbing
    def enter(self):
        pass

    def exit(self):
        pass

    def _hooks(self):
        h = {}
        mod_hooks = getattr(self.world.area_mod, "HOOKS", {})
        for k, fn in mod_hooks.items():
            h[k] = (lambda f: (lambda *a: f(self.world, *a)))(fn)
        return h

    def sheet(self, name) -> Sheet:
        s = self.sheets.get(name)
        if s is None:
            s = Sheet(self.assets.image(f"chars/{name}.png"), self.assets.json(f"chars/{name}.json"))
            self.sheets[name] = s
        return s

    def sfx(self, name, vol=1.0, x=None, y=None):
        if self.audio:
            self.audio.play(name, vol, x, y, self.cam)

    def _clamp_cam(self):
        a = self.world.area
        self.cam[0] = max(0, min(a.w - C.VIEW_W, self.cam[0])) if a.w > C.VIEW_W else (a.w - C.VIEW_W) / 2
        self.cam[1] = max(0, min(a.h - C.VIEW_H, self.cam[1])) if a.h > C.VIEW_H else (a.h - C.VIEW_H) / 2

    def _on_area_enter(self):
        a = self.world.area
        self.vfx.clear()
        card = a.defn.get("title_card")
        if card and not self.state.check(f"card.{a.id}"):
            self.state.set(f"card.{a.id}")
            self.ui.title_card = (card, 5.0)
        if self.audio:
            self.audio.set_area(a.defn.get("audio", {}))
        self.scene.rain.intensity = a.defn.get("rain", 0.0)

    # ------------------------------------------------------------------ update
    def update(self, dt):
        self.t += dt
        inp = self.app.input
        w = self.world
        if inp.pressed["help"]:
            self.paused = not self.paused
        if self.fade_dir != 0:
            self.fade = max(0.0, min(1.0, self.fade + self.fade_dir * dt / 0.35))
            if self.fade_dir > 0 and self.fade >= 1.0 and self.pending:
                self._do_transition()
            elif self.fade_dir < 0 and self.fade <= 0.0:
                self.fade_dir = 0
        if self.paused:
            if inp.consume("pause") or inp.consume("confirm"):
                self.paused = False
            if inp.pressed["throw"]:
                self.app.running = False
            self.ui.update(dt)
            return
        if self.dialogue is not None:
            self.dialogue.update(dt, inp, lambda n, v=1.0: self.sfx(n, v))
            if self.dialogue.mode == "end":
                self._end_dialogue()
        elif self.inventory is not None:
            r = self.inventory.update(inp, lambda n, v=1.0: self.sfx(n, v))
            if inp.consume("inventory") or inp.consume("pause") or r == "close":
                self.inventory = None
                self.sfx("ui_close", 0.4)
            # the world is paused while the inventory is open
            self.ui.update(dt)
            return
        else:
            if inp.consume("pause"):
                self.paused = True
                self.sfx("ui_open", 0.4)
                return
            if inp.consume("inventory") and self.dead_t is None:
                self.inventory = InventoryView(w)
                self.sfx("ui_open", 0.4)
                return
        if inp.pressed["help"] and False:
            pass
        if self.dead_t is not None:
            self.dead_t += dt
            if self.dead_t > 1.5 and (inp.consume("interact") or inp.consume("confirm")):
                self._respawn()
        w.update(dt)
        self._consume_events()
        if w.transition and not self.pending:
            self.pending = w.transition
            w.transition = None
            self.fade_dir = 1
            self.sfx("door", 0.5)
        self.vfx.update(dt)
        self.ui.update(dt)
        self._update_camera(dt)
        gy = w.area.defn.get("ground_y", 0)
        self.scene.rain.update(dt, (int(self.cam[0]) - C.MARGIN, int(self.cam[1]) - C.MARGIN),
                               lambda x, y: y > gy and y < w.area.h and not self._sheltered(x, y))
        # ambient steam from manholes
        for p in w.area.props:
            if p.kind in ("steam", "smoke") and random.random() < dt * (4 if p.kind == "steam" else 2.5):
                self.vfx.spawn({"kind": "steam", "x": p.x, "y": p.y})
        if self.audio:
            self.audio.update(dt, w, self.cam)
        self.shake = max(0.0, self.shake - dt * 14)
        self.flash = max(0.0, self.flash - dt * 4)
        self.hurt = max(0.0, self.hurt - dt * 1.2)

    def _sheltered(self, x, y):
        for r in self.world.area.defn.get("shelter", []):
            if r[0] <= x < r[0] + r[2] and r[1] <= y < r[1] + r[3]:
                return True
        return False

    def _update_camera(self, dt):
        p = self.world.player
        look = 22 if p.state != "free" or math.hypot(p.vx, p.vy) > 5 else 8
        tx = p.x + p.fx * look - C.VIEW_W / 2
        ty = p.y + p.fy * look * 0.7 - C.VIEW_H / 2 - 16
        k = min(1.0, dt * 4.5)
        self.cam[0] += (tx - self.cam[0]) * k
        self.cam[1] += (ty - self.cam[1]) * k
        self._clamp_cam()

    def _consume_events(self):
        w = self.world
        for ev in w.events:
            t = ev["type"]
            if t == "sfx":
                self.sfx(ev["name"], ev.get("vol", 1.0), ev.get("x"), ev.get("y"))
            elif t == "vfx":
                self.vfx.spawn(ev)
            elif t == "shake":
                self.shake = min(6.0, self.shake + ev["amount"])
            elif t == "flash":
                self.flash = max(self.flash, ev["amount"])
            elif t == "hurt":
                self.hurt = min(1.0, self.hurt + ev["amount"])
            elif t == "toast":
                self.ui.toast(ev["text"], ev.get("dur", 2.5))
            elif t == "bark":
                self.ui.bark(ev["who"], ev["text"], ev.get("dur", 3.2), ev.get("color"))
            elif t == "whisper":
                self.ui.whisper = (ev["remnant"], ev["text"], 4.5)
                self.sfx("whisper", 0.5)
            elif t == "dialogue":
                self._start_dialogue(ev["node"], ev.get("who"))
            elif t == "near_miss":
                self.sfx("near_miss", 0.6)
            elif t == "player_down":
                self.dead_t = 0.0
                self.sfx("player_down", 0.9)
            elif t == "area_enter":
                pass
            elif t == "music":
                if self.audio:
                    self.audio.set_music_state(ev.get("state"))
        w.events.clear()

    def _start_dialogue(self, node, who):
        r = Runner(self.script, self.state, self._hooks())
        r.start(node)
        if r.ended:
            return
        self.dialogue = DialogueView(r, who, PORTRAITS)
        w = self.world
        w.in_dialogue = True
        w.player.locked = True
        w.player.vx = w.player.vy = 0
        if isinstance(who, NPC):
            who.talking = True
            w.player.face(who.x - w.player.x, who.y - w.player.y)
        self.app.input.clear_buffer()
        self.sfx("ui_open", 0.3)

    def _end_dialogue(self):
        d = self.dialogue
        self.dialogue = None
        w = self.world
        w.in_dialogue = False
        w.player.locked = False
        if isinstance(d.who, NPC):
            d.who.talking = False
        self.app.input.clear_buffer()
        after = getattr(w.area_mod, "after_dialogue", None)
        if after:
            after(w, d.runner.node)

    def _do_transition(self):
        area_id, spawn, style = self.pending
        self.pending = None
        self.world.load_area(area_id, spawn)
        p = self.world.player
        self.cam = [p.x - C.VIEW_W / 2, p.y - C.VIEW_H / 2]
        self._clamp_cam()
        self.scene.rain.last_cam = None
        self._on_area_enter()
        self.fade_dir = -1

    def _respawn(self):
        self.dead_t = None
        area_id = self.world.checkpoint[0]
        p = self.world.player
        p.hp = p.max_hp
        p.dead = False
        p.set_state("free")
        p.lantern_on = False
        spawn = self.world.area.defn.get("respawn", "start")
        self.pending = (area_id, spawn, "fade")
        self.fade = 1.0
        self._do_transition()

    # ------------------------------------------------------------------ draw
    def draw(self, dt):
        self._draw_frame(dt, ui_ready=False)

    def _draw_frame(self, dt, ui_ready=False):
        w = self.world
        sc = self.scene
        sx = sy = 0.0
        if self.shake > 0:
            sx = random.uniform(-1, 1) * self.shake
            sy = random.uniform(-1, 1) * self.shake
        cam = (self.cam[0] + sx, self.cam[1] + sy)
        ix, iy = int(math.floor(cam[0])), int(math.floor(cam[1]))
        sc.cv.begin(ix - C.MARGIN, iy - C.MARGIN)
        sc.draw_area_layer(w.area, "bg")
        self.vfx.draw_stains(sc.cv)
        sc.facade_props(w.area, w.t)
        items = sc.sorted_props(w.area, w.t)
        for e in w.entities:
            items.append((e.y, (lambda e=e: self._draw_entity(e))))
        items.sort(key=lambda it: it[0])
        for _, fn in items:
            fn()
        self.vfx.draw(sc.cv)
        self._draw_world_fx()
        sc.draw_area_layer(w.area, "fg")
        draw_over = getattr(w.area_mod, "draw_over", None)
        if draw_over:
            draw_over(w, sc)
        if w.area.defn.get("rain", 0) > 0:
            sc.rain.draw(sc.cv, None)
        extra = [Light(L.x, L.y, L.radius, L.color, L.intensity * L.level(w.t), L.specular, L.direction, L.cos_inner,
                       L.cos_outer, L.clip) for L in w.dynamic_light_sources()]
        area_lights = getattr(w.area_mod, "lights", None)
        if area_lights:
            extra += area_lights(w)
        lights = sc.collect_lights(w.area, w.t, extra)
        post = PostParams(**{k: v for k, v in w.area.post.items() if k in PostParams.__dataclass_fields__})
        post.flash = self.flash
        p = w.player
        post.hurt = max(self.hurt, (1 - p.hp / p.max_hp) * 0.5 if p.hp < p.max_hp * 0.35 else 0.0)
        post.fade = self.fade
        if self.dead_t is not None:
            post.saturation = max(0.0, 1.0 - self.dead_t)
            post.fade = min(0.7, self.dead_t * 0.4)
        # UI
        ui = self.ui
        quads = []
        if not ui_ready:
            ui.begin()
        if ui_ready:
            pass
        elif self.paused:
            ui.draw_help()
        elif self.inventory is not None:
            ui.draw_inventory(self.inventory, w)
        else:
            ui.draw_world_overlays(w, cam)
            ui.draw_hud(w, self.app.fps if self.show_fps else None, in_dialogue=self.dialogue is not None)
            ui.draw_messages()
            if self.dialogue is not None:
                pr = self.dialogue.portrait
                if pr is not None:
                    key = self._portrait_key(*pr)
                    if key:
                        quads.append(Quad(key, (20, C.UI_H - 392, 300, 380)))
                ui.draw_dialogue(self.dialogue)
            if self.dead_t is not None:
                ui.draw_death(self.dead_t)
        self.app.renderer.render(sc.cv.alb, sc.cv.emi, sc.cv.mat, lights, cam, post, ui.surf, quads, dt)

    def _portrait_key(self, who, expr):
        key = f"portrait/{who}/{expr}"
        if key not in self.portrait_cache:
            rel = f"portraits/{who}_{expr}.png"
            if not self.assets.exists(rel):
                rel = f"portraits/{who}_neutral.png"
                if not self.assets.exists(rel):
                    return None
            self.app.renderer.register_texture(key, self.assets.image(rel))
            self.portrait_cache.add(key)
        return key

    def _draw_entity(self, e):
        sc = self.scene
        cv = sc.cv
        if isinstance(e, Pickup):
            alb, emi = self.assets.sprite(f"icons/{e.icon}") if self.assets.exists(f"sprites/icons/{e.icon}_alb.png") else (None, None)
            bob = math.sin(self.t * 3 + e.id) * 1.0
            if alb is not None:
                sc.blit_sprite(alb, emi, e.x - alb.get_width() // 2, e.y - alb.get_height() - 2 + bob)
            cx, cy = cv.to_canvas(e.x, e.y - 6 + bob)
            g = int(150 + 100 * math.sin(self.t * 4 + e.id))
            if 0 <= cx < C.CANVAS_W and 0 <= cy < C.CANVAS_H:
                cv.emi.fill((g, g, int(g * 0.8)), (cx, cy - 4, 1, 1))
            return
        if isinstance(e, Bottle):
            cx, cy = cv.to_canvas(e.x, e.y)
            pygame.draw.ellipse(cv.alb, (10, 10, 14, 255), (cx - 2, cy - 1, 4, 2))
            cv.alb.fill((80, 120, 90, 255), (cx - 1, int(cy - e.z) - 2, 2, 3))
            cv.alb.fill((150, 190, 160, 255), (cx - 1, int(cy - e.z) - 2, 1, 1))
            return
        if not e.sprite:
            return
        sh = self.sheet(e.sprite)
        k, flip = sh.frame_index(e.anim, e.view, e.anim_t)
        img = sh.get_white(k, flip) if e.flash > 0 else sh.get(k, flip)
        d = sh.data(k, flip)
        x0, y0 = e.x - sh.ax, e.y - sh.ay
        cx, cy = cv.to_canvas(x0, y0)
        if cx > C.CANVAS_W + 50 or cy > C.CANVAS_H + 50 or cx < -50 or cy < -50:
            return
        # contact shadow
        if e.shadow:
            fx, fy = cv.to_canvas(e.x, e.y)
            s = pygame.Surface((16, 5), pygame.SRCALPHA)
            pygame.draw.ellipse(s, (0, 0, 0, 110), s.get_rect())
            cv.alb.blit(s, (fx - 8, fy - 3))
        # wet street reflection
        if self.world.area.defn.get("reflections") and e.y > self.world.area.defn.get("ground_y", 0) + 4:
            r = sc.reflection_of(img)
            cv.alb.blit(r, (cx, cy + 2 * sh.ay - sh.fh + 1))
        weapon = self._weapon_for(e)
        behind = d["behind"]
        if weapon and behind:
            draw_weapon(cv.alb, weapon, cx + d["hr"][0], cy + d["hr"][1], d["ang"])
        cv.alb.blit(img, (cx, cy))
        cv.mat.blit(sc.mask_of(sh.get(k, flip)), (cx, cy))
        if weapon and not behind:
            draw_weapon(cv.alb, weapon, cx + d["hr"][0], cy + d["hr"][1], d["ang"])
        if isinstance(e, Player) and e.lantern_on:
            la, le = self.lantern_imgs
            hx, hy = d["hl"]
            cv.alb.blit(la, (cx + hx - 2, cy + hy - 1))
            cv.emi.blit(le, (cx + hx - 2, cy + hy - 1), special_flags=pygame.BLEND_RGB_ADD)
        if isinstance(e, Enemy) and e.match_lit > 0 and not e.dead:
            hx, hy = d["hr"]
            fl = 200 + int(55 * math.sin(self.t * 30))
            cv.emi.fill((fl, int(fl * 0.7), 60), (cx + hx, cy + hy - 3, 1, 2))
        if "umbrella" in e.overlay:
            hx, hy = d["head"]
            cv.alb.blit(self.umbrella, (cx + hx - 10, cy + hy - 12))
        if "cigarette" in e.overlay:
            hx, hy = d["head"]
            glow = 160 + int(90 * max(0, math.sin(self.t * 1.3 + e.id)))
            cv.emi.fill((glow, int(glow * 0.45), 30), (cx + hx + (2 if e.view != "W" else -3), cy + hy + 3, 1, 1))
        # player slash arc on active frames
        if isinstance(e, Player) and e.state in ("attack", "heavy") and e.swing is not None:
            sw = e.swing
            t = e.state_t - sw["windup"]
            if 0 <= t < sw["active"] + 0.05:
                self._slash_arc(e, sw, t / (sw["active"] + 0.05))

    def _weapon_for(self, e):
        if isinstance(e, Player):
            if e.state in ("attack", "heavy"):
                return WEAPONS[self.state.equipped]["draw"]
            if e.state == "shoot":
                return "revolver"
            return None
        if isinstance(e, Enemy):
            if e.dead:
                return None
            if e.etype == "knifeman" and e.awareness != "calm":
                return "knife"
            if e.etype == "gunman" and (e.aim_t > 0 or e.anim in ("aim", "shoot")):
                return "revolver"
        return None

    def _slash_arc(self, p, sw, f):
        cv = self.scene.cv
        cx, cy = cv.to_canvas(p.x, p.y - 12)
        r = sw["reach"] * 0.9
        a0 = math.atan2(p.fy * 0.8, p.fx)
        half = math.radians(sw["arc"] / 2)
        n = 14
        b = int(255 * (1 - f))
        col = (b, int(b * 0.92), int(b * 0.85))
        span = half * 2 * min(1.0, f * 1.6 + 0.3)
        start = a0 - half
        for i in range(n):
            a = start + span * i / (n - 1)
            x = cx + math.cos(a) * r
            y = cy + math.sin(a) * r * 0.75
            if 0 <= x < C.CANVAS_W and 0 <= y < C.CANVAS_H:
                cv.emi.fill(col, (int(x), int(y), 1, 1))

    def _draw_world_fx(self):
        """Aim lines and attack telegraphs."""
        cv = self.scene.cv
        w = self.world
        p = w.player
        for e in w.enemies():
            if e.dead:
                continue
            if e.etype == "gunman" and e.aim_t > 0 and p is not None:
                gun = e.d["gun"]
                f = min(1.0, e.aim_t / gun["aim"])
                x0, y0 = cv.to_canvas(e.x + e.fx * 8, e.y - 15)
                x1, y1 = cv.to_canvas(p.x, p.y - 14)
                n = int(math.hypot(x1 - x0, y1 - y0) / 2)
                col = (int(120 + 135 * f), int(20 * f), int(20 * f))
                for i in range(n):
                    if f < 0.75 and (i // 2) % 2:
                        continue
                    x = int(x0 + (x1 - x0) * i / max(1, n))
                    y = int(y0 + (y1 - y0) * i / max(1, n))
                    if 0 <= x < C.CANVAS_W and 0 <= y < C.CANVAS_H:
                        cv.emi.fill(col, (x, y, 1, 1))
            if e.attack is not None and e.state_t < e.attack["windup"]:
                f = e.state_t / e.attack["windup"]
                x, y = cv.to_canvas(e.x, e.y - 40)
                b = int(140 + 115 * f)
                if 0 <= x < C.CANVAS_W and 0 <= y < C.CANVAS_H and (e.attack["windup"] > 0.5 or f > 0.4):
                    cv.emi.fill((b, int(b * 0.25), int(b * 0.2)), (x, y, 1, 3))
                    cv.emi.fill((b, int(b * 0.25), int(b * 0.2)), (x, y + 4, 1, 1))
