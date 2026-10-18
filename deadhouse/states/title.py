"""Title screen: Lantern Row plays live behind the logo while the camera drifts down the street."""
from __future__ import annotations

import math

import pygame

from .. import config as C


class TitleState:
    OPTIONS = ("Begin Night Two", "Controls", "Quit")

    def __init__(self, app):
        self.app = app
        from .play import PlayState
        self.preview = PlayState(app, area_id="row", spawn="160,214")
        self.preview.attract = True
        self.preview.world.player.locked = True
        self.preview.ui.title_card = None
        self.preview.ui.whisper = None
        self.preview.fade = 1.0
        self.preview.fade_dir = -1
        self.sel = 0
        self.t = 0.0
        self.help = False
        self.leaving = None

    def enter(self):
        pass

    def exit(self):
        pass

    def update(self, dt):
        self.t += dt
        inp = self.app.input
        pv = self.preview
        p = pv.world.player
        # drift the camera along the Row
        x = 380 + math.sin(self.t * 0.045) * 360
        p.x, p.y = x, 230
        p.vx = p.vy = 0
        pv.world.update(dt)
        pv.world.events.clear()
        pv._update_camera(dt)
        pv.vfx.update(dt)
        gy = pv.world.area.defn.get("ground_y", 0)
        pv.scene.rain.update(dt, (int(pv.cam[0]) - C.MARGIN, int(pv.cam[1]) - C.MARGIN), lambda xx, yy: gy < yy < pv.world.area.h)
        if pv.audio:
            pv.audio.update(dt, pv.world, pv.cam)
        if pv.fade_dir:
            pv.fade = max(0.0, min(1.0, pv.fade + pv.fade_dir * dt / 1.2))
            if pv.fade_dir < 0 and pv.fade <= 0:
                pv.fade_dir = 0
        if self.leaving is not None:
            self.leaving -= dt
            pv.fade = min(1.0, pv.fade + dt / 0.8)
            if self.leaving <= 0:
                from .play import PlayState
                self.app.replace(PlayState(self.app))
            return
        if self.help:
            if inp.consume("confirm") or inp.consume("cancel") or inp.consume("pause"):
                self.help = False
            return
        if inp.pressed["up"]:
            self.sel = (self.sel - 1) % len(self.OPTIONS)
            pv.sfx("ui_move", 0.35)
        if inp.pressed["down"]:
            self.sel = (self.sel + 1) % len(self.OPTIONS)
            pv.sfx("ui_move", 0.35)
        if inp.consume("confirm") or inp.consume("attack"):
            pv.sfx("ui_select", 0.6)
            choice = self.OPTIONS[self.sel]
            if choice.startswith("Begin"):
                self.leaving = 0.9
            elif choice == "Controls":
                self.help = True
            else:
                self.app.running = False

    def draw(self, dt):
        pv = self.preview
        ui = pv.ui
        # render the street (player hidden) with our own UI on top
        pv.world.player.sprite = None
        pv.world.player.shadow = False
        ui.begin()
        if self.help:
            ui.draw_help()
        else:
            self._draw_title(ui)
        pv._draw_frame(dt, ui_ready=True)

    def _draw_title(self, ui):
        cx = C.UI_W // 2
        a = int(255 * min(1.0, self.t / 2.0))
        band = pygame.Surface((C.UI_W, 300), pygame.SRCALPHA)
        for yy in range(300):
            k = 1 - abs(yy - 150) / 150
            pygame.draw.line(band, (6, 4, 8, int(150 * k * a / 255)), (0, yy), (C.UI_W, yy))
        ui.surf.blit(band, (0, 90))
        # logo: big pixel letters with a red underline, like a sign that has been on too long
        title = "DEADHOUSE"
        f = ui.huge
        w = f.width(title)
        x = cx - w // 2
        y = 120
        flick = 1.0 if (int(self.t * 13) % 37) != 0 else 0.4
        col = (int(236 * flick), int(226 * flick), int(214 * flick))
        f.draw(ui.surf, title, (x + 3, y + 3), (20, 6, 10), None, a)
        f.draw(ui.surf, title, (x, y), col, None, a)
        pygame.draw.rect(ui.surf, (196, 40, 52, a), (x, y + 50, w, 3))
        ui.text("CORVANE  ·  NIGHT TWO", cx, y + 64, (170, 160, 150), alpha=a, center=True)
        for i, opt in enumerate(self.OPTIONS):
            sel = i == self.sel
            c = (236, 226, 214) if sel else (130, 122, 116)
            ui.text(("> " if sel else "") + opt + (" <" if sel else ""), cx, 300 + i * 20, c, alpha=a, center=True)
        ui.text("Prototype 1  ·  all art, music, sound and writing generated in code", cx, C.UI_H - 30, (110, 104, 100),
                alpha=a, center=True)
        ui.text("Enter / E: select    Arrows: move    F11: fullscreen", cx, C.UI_H - 16, (90, 86, 84), alpha=a, center=True)
