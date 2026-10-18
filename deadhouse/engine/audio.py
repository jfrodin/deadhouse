"""Runtime audio: positional one-shots, crossfaded ambience beds, distance-driven music.

Mixing model: the listener is the camera centre. One-shots are panned and
attenuated by distance. Each area declares its ambience loops, an optional
music source (e.g. the Velour's band behind a wall) and whether combat tension
can rise.
"""
from __future__ import annotations

import math
import os
import random

import pygame

from .. import config as C

AUDIO_DIR = os.path.join(C.ASSET_DIR, "audio")


class Loop:
    def __init__(self, sound: pygame.mixer.Sound, channel: pygame.mixer.Channel):
        self.sound = sound
        self.ch = channel
        self.vol = 0.0
        self.target = 0.0
        self.playing = False

    def ensure(self):
        if not self.playing:
            self.ch.play(self.sound, loops=-1)
            self.ch.set_volume(0.0)
            self.playing = True

    def step(self, dt, rate=1.2):
        d = self.target - self.vol
        self.vol += max(-rate * dt, min(rate * dt, d))
        if self.vol <= 0.001 and self.target <= 0.0 and self.playing:
            self.ch.stop()
            self.playing = False
        elif self.playing:
            self.ch.set_volume(self.vol)


class AudioEngine:
    def __init__(self, enabled=True):
        self.enabled = enabled and pygame.mixer.get_init() is not None
        self.sounds: dict[str, list[pygame.mixer.Sound]] = {}
        self.master = 0.9
        self.sfx_vol = 0.85
        self.amb_vol = 0.7
        self.music_vol = 0.75
        self.loops: dict[str, Loop] = {}
        self.cfg: dict = {}
        self.reserved = 10
        self.tension = 0.0
        if self.enabled:
            pygame.mixer.set_num_channels(48)
            pygame.mixer.set_reserved(self.reserved)
            self._next_res = 0

    # ------------------------------------------------------------------ loading
    def _file(self, folder, name):
        for ext in (".ogg", ".wav"):
            p = os.path.join(AUDIO_DIR, folder, name + ext)
            if os.path.exists(p):
                return p
        return None

    def get(self, name: str) -> list[pygame.mixer.Sound]:
        v = self.sounds.get(name)
        if v is None:
            v = []
            p = self._file("sfx", name)
            if p:
                v.append(pygame.mixer.Sound(p))
            k = 1
            while True:
                p = self._file("sfx", f"{name}_{k}")
                if not p:
                    break
                v.append(pygame.mixer.Sound(p))
                k += 1
            self.sounds[name] = v
        return v

    def loop(self, folder: str, name: str) -> Loop | None:
        key = f"{folder}/{name}"
        lp = self.loops.get(key)
        if lp is None:
            p = self._file(folder, name)
            if not p or self._next_res >= self.reserved:
                return None
            lp = Loop(pygame.mixer.Sound(p), pygame.mixer.Channel(self._next_res))
            self._next_res += 1
            self.loops[key] = lp
        return lp

    # ------------------------------------------------------------------ one-shots
    def play(self, name, vol=1.0, x=None, y=None, cam=None):
        if not self.enabled:
            return
        v = self.get(name)
        if not v:
            return
        snd = random.choice(v)
        ch = pygame.mixer.find_channel(True)
        if ch is None:
            return
        g = vol * self.sfx_vol * self.master
        l = r = g
        if x is not None and cam is not None:
            lx = cam[0] + C.VIEW_W / 2
            ly = cam[1] + C.VIEW_H / 2
            dx, dy = x - lx, (y - ly) * 1.3
            d = math.hypot(dx, dy)
            att = 1.0 / (1.0 + (d / 240.0) ** 2)
            p = max(-1.0, min(1.0, dx / 280.0))
            a = (p + 1) * math.pi / 4
            l = g * att * math.cos(a) * 1.41
            r = g * att * math.sin(a) * 1.41
        ch.play(snd)
        ch.set_volume(min(1.0, l), min(1.0, r))

    # ------------------------------------------------------------------ beds
    def set_area(self, cfg: dict):
        if not self.enabled:
            return
        self.cfg = cfg or {}
        wanted = set()
        for name in self.cfg.get("ambience", []):
            lp = self.loop("amb", name)
            if lp:
                lp.ensure()
                lp.target = self.amb_vol * self.master * self.cfg.get("amb_gain", {}).get(name, 1.0)
                wanted.add(f"amb/{name}")
        for key, lp in self.loops.items():
            if key not in wanted and not key.startswith("music/") and key != "amb/tension":
                lp.target = 0.0

    def update(self, dt, world, cam):
        if not self.enabled:
            return
        cfg = self.cfg
        lx = cam[0] + C.VIEW_W / 2
        ly = cam[1] + C.VIEW_H / 2
        music = cfg.get("music")
        for key, lp in self.loops.items():
            if key.startswith("music/") and (music is None or not key.endswith(music + cfg.get("music_variant", "_out"))):
                lp.target = 0.0
        if music:
            variant = cfg.get("music_variant", "_out")
            lp = self.loop("music", music + variant)
            if lp:
                lp.ensure()
                sx, sy = cfg.get("music_source", (lx, ly))
                d = math.hypot(sx - lx, (sy - ly) * 1.2)
                near = max(0.0, 1.0 - d / cfg.get("music_radius", 520.0))
                lp.target = self.music_vol * self.master * (0.08 + 0.92 * near ** 1.4) * cfg.get("music_gain", 1.0)
        # combat tension rises while anyone is hunting Ines
        alert = any(e.awareness == "alert" and not e.dead for e in world.enemies()) if world else False
        self.tension += (dt / 1.5) if alert else -(dt / 4.0)
        self.tension = max(0.0, min(1.0, self.tension))
        lp = self.loop("amb", "tension")
        if lp:
            if self.tension > 0.01:
                lp.ensure()
            lp.target = self.tension * 0.55 * self.music_vol * self.master
        for lp in self.loops.values():
            lp.step(dt)

    def stop_all(self):
        if self.enabled:
            pygame.mixer.stop()
