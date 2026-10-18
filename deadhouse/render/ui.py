"""UI layer (960x540): HUD, prompts, barks, dialogue box, inventory, overlays."""
from __future__ import annotations

import math

import pygame

from .. import config as C
from ..content.items import ITEMS, REMNANTS
from ..content.combat import WEAPONS
from ..engine.font import BitmapFont

INK = (12, 10, 16)
PAPER = (232, 226, 214)
DIM = (150, 144, 136)
RED = (196, 40, 52)
GOLD = (214, 176, 108)

NAME_COLORS = {
    "ines": (220, 120, 80), "vivienne": (236, 96, 170), "augie": (220, 184, 110), "bruno": (170, 170, 180),
    "silas": (150, 190, 255), "maud": (255, 170, 120), "haskell": (200, 200, 230), "hobb": (220, 150, 120),
    "clerk": (190, 190, 170),
}


def panel(surf, rect, alpha=200, border=(60, 54, 60)):
    s = pygame.Surface(rect.size, pygame.SRCALPHA)
    s.fill((10, 8, 14, alpha))
    surf.blit(s, rect.topleft)
    pygame.draw.rect(surf, border, rect, 1)


class Toast:
    def __init__(self, text, dur):
        self.text, self.t, self.dur = text, dur, dur


class Bark:
    def __init__(self, who, text, dur, color):
        self.who, self.text, self.t, self.dur, self.color = who, text, dur, dur, color


class UI:
    def __init__(self):
        self.surf = pygame.Surface((C.UI_W, C.UI_H), pygame.SRCALPHA)
        self.font = BitmapFont(1)
        self.big = BitmapFont(2, spacing=1)
        self.huge = BitmapFont(4, spacing=1)
        self.toasts: list[Toast] = []
        self.barks: list[Bark] = []
        self.whisper = None  # (remnant, text, t)
        self.title_card = None  # (lines, t)
        self.t = 0.0

    # ------------------------------------------------------------------ helpers
    def text(self, txt, x, y, color=PAPER, font=None, shadow=True, alpha=255, center=False):
        """Draw a line of text. Lines are rendered once and cached (glyph-by-glyph blits are slow)."""
        f = font or self.font
        color = tuple(color[:3])
        key = (txt, color, id(f), shadow)
        cache = self.__dict__.setdefault("_tcache", {})
        img = cache.get(key)
        if img is None:
            w = f.width(txt) + 2 * f.scale
            img = pygame.Surface((max(1, w), f.line_h + 2 * f.scale), pygame.SRCALPHA)
            f.draw(img, txt, (0, 0), color, (8, 6, 10) if shadow else None)
            if len(cache) > 1500:
                cache.clear()
            cache[key] = img
        if center:
            x = x - (img.get_width() - 2 * f.scale) // 2
        if alpha < 255:
            img.set_alpha(max(0, alpha))
            self.surf.blit(img, (x, y))
            img.set_alpha(255)
        else:
            self.surf.blit(img, (x, y))
        return x + img.get_width()

    def world_to_ui(self, x, y, cam):
        return (x - cam[0]) * 2, (y - cam[1]) * 2

    def update(self, dt):
        self.t += dt
        for t in self.toasts:
            t.t -= dt
        self.toasts = [t for t in self.toasts if t.t > 0]
        for b in self.barks:
            b.t -= dt
        self.barks = [b for b in self.barks if b.t > 0]
        if self.whisper:
            r, txt, t = self.whisper
            t -= dt
            self.whisper = (r, txt, t) if t > 0 else None
        if self.title_card:
            lines, t = self.title_card
            t -= dt
            self.title_card = (lines, t) if t > 0 else None

    def toast(self, text, dur=2.5):
        if self.toasts and self.toasts[-1].text == text:
            self.toasts[-1].t = dur
            return
        self.toasts.append(Toast(text, dur))
        self.toasts = self.toasts[-4:]

    def bark(self, who, text, dur=3.2, color=None):
        self.barks = [b for b in self.barks if b.who is not who]
        self.barks.append(Bark(who, text, dur, color))

    # ------------------------------------------------------------------ frame
    def begin(self):
        self.surf.fill((0, 0, 0, 0))

    def draw_world_overlays(self, world, cam):
        """Barks above heads and the interaction prompt."""
        for b in self.barks:
            if b.who is None or getattr(b.who, "removed", False):
                continue
            ux, uy = self.world_to_ui(b.who.x, b.who.y - 44, cam)
            lines = self.font.wrap(b.text, 190)
            alpha = int(255 * min(1.0, b.t / 0.4, (b.dur - b.t) / 0.15 + 0.2))
            h = len(lines) * 13 + 6
            w = max(self.font.width(l) for l in lines) + 12
            r = pygame.Rect(int(ux - w / 2), int(uy - h), w, h)
            r.clamp_ip(self.surf.get_rect().inflate(-8, -8))
            s = pygame.Surface(r.size, pygame.SRCALPHA)
            s.fill((8, 6, 12, int(150 * alpha / 255)))
            self.surf.blit(s, r.topleft)
            col = b.color or NAME_COLORS.get(getattr(b.who, "sprite", ""), PAPER)
            for i, ln in enumerate(lines):
                self.text(ln, r.x + 6, r.y + 4 + i * 13, col if i == 0 and False else PAPER, alpha=alpha)
            pygame.draw.line(self.surf, (*col, alpha), (r.x, r.bottom - 1), (r.right - 1, r.bottom - 1))
        p = world.player
        if p is not None:
            pr = world.interact_prompt(p)
            if pr:
                verb, label = pr
                ux, uy = self.world_to_ui(p.x, p.y - 48, cam)
                key = "E" if True else "A"
                txt = f"{verb}" + (f" — {label}" if label else "")
                w = self.font.width(txt) + 30
                r = pygame.Rect(int(ux - w / 2), int(uy - 18), w, 18)
                panel(self.surf, r, 170, (90, 80, 70))
                pygame.draw.rect(self.surf, GOLD, (r.x + 4, r.y + 3, 13, 12), 1)
                self.text(key, r.x + 8, r.y + 3, GOLD, shadow=False)
                self.text(txt, r.x + 22, r.y + 3)

    def draw_hud(self, world, show_fps=None, in_dialogue=False):
        p = world.player
        st = world.state
        if p is None:
            return
        # health: a thin red line with a pulse
        x, y = 18, 16
        w = 150
        frac = max(0.0, p.hp / p.max_hp)
        pygame.draw.rect(self.surf, (20, 14, 18, 200), (x - 2, y - 2, w + 4, 8))
        low = frac < 0.35
        col = RED if not low or int(self.t * 4) % 2 == 0 else (240, 70, 80)
        pygame.draw.rect(self.surf, col, (x, y, int(w * frac), 4))
        for k in range(1, 5):
            pygame.draw.line(self.surf, (20, 14, 18), (x + w * k // 5, y), (x + w * k // 5, y + 3))
        self.text("INES", x, y + 8, (210, 120, 90))
        # weapon + tools
        wname = WEAPONS[st.equipped]["name"]
        self.text(wname, x + 40, y + 8, DIM)
        yy = y + 24
        if st.has("revolver"):
            n = st.count("rounds")
            self.text(".38", x, yy, DIM)
            for i in range(6):
                c = GOLD if i < n else (60, 54, 50)
                pygame.draw.rect(self.surf, c, (x + 24 + i * 6, yy + 2, 3, 7))
            if n > 6:
                self.text(f"+{n - 6}", x + 62, yy, GOLD)
            yy += 14
        items = []
        if st.count("bottle"):
            items.append(f"Bottles {st.count('bottle')}")
        if st.count("dressing"):
            items.append(f"Dressings {st.count('dressing')}")
        if items:
            self.text("   ".join(items), x, yy, DIM)
            yy += 14
        if st.has("lantern"):
            on = p.lantern_on
            self.text("Lantern " + ("lit" if on else "dark"), x, yy, (240, 210, 140) if on else DIM)
            if on and p.flash_cd > 0:
                pygame.draw.rect(self.surf, (90, 80, 60), (x + 90, yy + 4, 30, 3))
                pygame.draw.rect(self.surf, (240, 210, 140), (x + 90, yy + 4, int(30 * (1 - p.flash_cd / 3.2)), 3))
            yy += 14
        # remnants (hidden while a portrait occupies the corner)
        rx, ry = 18, C.UI_H - 28
        for i, r in enumerate([] if in_dialogue else st.remnants):
            rd = REMNANTS[r]
            col = rd["color"]
            self.text(rd["name"].split()[0].upper(), rx, ry, col)
            self.text(rd["lesson"], rx, ry + 12, DIM)
            rx += 92
        if show_fps is not None:
            self.text(f"{show_fps:5.1f} fps", C.UI_W - 70, 8, DIM)

    def draw_messages(self):
        # toasts bottom centre
        for i, t in enumerate(reversed(self.toasts)):
            a = int(255 * min(1.0, t.t / 0.5))
            y = C.UI_H - 70 - i * 16
            self.text(t.text, C.UI_W // 2, y, PAPER, alpha=a, center=True)
        if self.whisper:
            r, txt, t = self.whisper
            rd = REMNANTS[r]
            a = int(255 * min(1.0, t / 0.6, 1.0))
            col = rd["color"]
            name = rd["name"].split()[0].upper()
            lines = self.font.wrap(txt, 420)
            y = 54
            self.text(name, C.UI_W // 2, y - 14, col, alpha=a, center=True)
            for i, ln in enumerate(lines):
                self.text(ln, C.UI_W // 2, y + i * 13, (200, 210, 230), alpha=a, center=True)
        if self.title_card:
            lines, t = self.title_card
            a = int(255 * min(1.0, t / 1.0, (5.0 - t) / 0.8 + 0.0 if t < 5 else 1.0))
            a = max(0, min(255, a))
            x, y = 18, C.UI_H - 112
            self.text(lines[0], x, y, PAPER, self.big, alpha=a)
            pygame.draw.line(self.surf, (*RED, a), (x, y + 25), (x + 120, y + 25))
            for i, ln in enumerate(lines[1:]):
                self.text(ln, x, y + 30 + i * 13, DIM, alpha=a)

    # ------------------------------------------------------------------ dialogue
    def draw_dialogue(self, dlg):
        """dlg: DialogueView (see states.play)."""
        box = pygame.Rect(150, C.UI_H - 150, C.UI_W - 300, 136)
        if dlg.portrait:
            box = pygame.Rect(330, C.UI_H - 150, C.UI_W - 350, 136)
        panel(self.surf, box, 215, (80, 70, 74))
        cur = dlg.current
        x = box.x + 16
        y = box.y + 12
        if dlg.mode == "say":
            if cur.speaker:
                col = NAME_COLORS.get(cur.speaker, GOLD)
                self.text(cur.name.upper(), x, y, col)
                y += 18
            else:
                y += 4
            txt = cur.text[: int(dlg.reveal)]
            col = PAPER if cur.speaker else (190, 196, 214)
            for i, ln in enumerate(self.font.wrap(txt, box.w - 32)):
                self.text(ln, x, y + i * 14, col)
            if dlg.reveal >= len(cur.text) and int(self.t * 2) % 2 == 0:
                self.text("v", box.right - 18, box.bottom - 18, GOLD)
        elif dlg.mode == "menu":
            if dlg.last_line is not None:
                ln = dlg.last_line
                head = (ln.name.upper() + ": ") if ln.speaker else ""
                short = self.font.wrap(head + ln.text, box.w - 32)
                for i, s in enumerate(short[-2:]):
                    self.text(s, x, y + i * 13, DIM)
                y += 30
            for i, ch in enumerate(dlg.choices):
                sel = i == dlg.sel
                col = PAPER if sel else DIM
                prefix = "> " if sel else "  "
                tag = f"[{ch.stance}] " if ch.stance else ""
                lines = self.font.wrap(prefix + ch.text, box.w - 70)
                for j, ln in enumerate(lines):
                    self.text(ln, x, y, col)
                    if j == 0 and tag:
                        self.text(tag.strip(), box.right - 16 - self.font.width(tag.strip()), y,
                                  {"cold": (140, 170, 220), "warm": (230, 160, 110), "wry": (190, 200, 130),
                                   "blunt": (220, 120, 110)}[ch.stance])
                    y += 13
                y += 3

    # ------------------------------------------------------------------ inventory
    def icon(self, assets, key):
        cache = getattr(self, "_icons", None)
        if cache is None:
            cache = self._icons = {}
        if key not in cache:
            rel = f"sprites/icons/{key}_alb.png"
            img = None
            if assets is not None and assets.exists(rel):
                img = pygame.transform.scale_by(assets.image(rel), 1)
            cache[key] = img
        return cache[key]

    def draw_inventory(self, inv, world):
        st = world.state
        self.surf.fill((6, 5, 9, 215))
        self.text("INVENTORY", 40, 30, PAPER, self.big)
        self.text(f"Night {st.night} · Lantern Row", 40, 56, DIM)
        cols = inv.columns
        x0 = 40
        colw = min(220, (C.UI_W - 60) // max(1, len(cols)))
        for ci, (title, rows) in enumerate(cols):
            x = x0 + ci * colw
            self.text(title.upper(), x, 90, GOLD if ci == inv.col else DIM)
            for ri, (key, label) in enumerate(rows):
                sel = ci == inv.col and ri == inv.row
                col = PAPER if sel else (170, 164, 156)
                y = 110 + ri * 16
                if sel:
                    pygame.draw.rect(self.surf, (60, 40, 46), (x - 4, y - 2, colw - 8, 15))
                ic = ITEMS.get(key, {}).get("icon") or (WEAPONS[key]["icon"] if key in WEAPONS else None)
                img = self.icon(world.assets, ic) if ic else None
                if img is not None:
                    self.surf.blit(img, (x, y - 2))
                room = colw - 14 - (18 if img is not None else 0)
                if self.font.width(label) > room:
                    while label and self.font.width(label + "...") > room:
                        label = label[:-1]
                    label += "..."
                self.text(label, x + (18 if img is not None else 0), y, col)
        key = inv.selected_key()
        desc = ""
        if key:
            if key.startswith("lead:"):
                title, text, done = inv.leads[int(key[5:])]
                desc = title + "\n\n" + text + ("\n\n(Resolved.)" if done else "")
            elif key in REMNANTS:
                r = REMNANTS[key]
                desc = (f"{r['name']}, {r['epithet']}.\nLesson — {r['lesson']}: {r['lesson_desc']}\n"
                        f"Passive — {r['passive']}: {r['passive_desc']}\nRead — {r['read']}: {r['read_desc']}")
            elif key in WEAPONS:
                desc = WEAPONS[key]["desc"] + ("\n\n(Equipped)" if st.equipped == key else "\n\nE: equip")
            else:
                desc = ITEMS.get(key, {}).get("desc", "")
        panel(self.surf, pygame.Rect(40, 360, C.UI_W - 80, 140), 160)
        for i, ln in enumerate(self.font.wrap(desc, C.UI_W - 110)):
            self.text(ln, 56, 374 + i * 14, PAPER)
        self.text("Tab / Esc: close    Arrows: select    E: use / equip", 40, C.UI_H - 24, DIM)

    # ------------------------------------------------------------------ overlays
    def draw_help(self):
        self.surf.fill((6, 5, 9, 225))
        self.text("CONTROLS", 60, 40, PAPER, self.big)
        rows = [
            ("Move", "WASD / arrows · left stick"), ("Sprint (noisy)", "Shift · left trigger"),
            ("Attack / takedown from behind", "J · X"), ("Heavy attack", "K · Y"), ("Dodge", "Space · B"),
            ("Interact / talk / climb", "E · A"), ("Throw bottle (aims at lights)", "Q · LB"),
            ("Fire revolver (loud)", "L · RB"), ("Lantern on/off", "F · right stick"),
            ("Lantern flash (blinds)", "C · left stick"), ("Field dressing", "H · d-pad down"),
            ("Ask your Remnant for a hint", "R · d-pad up"),
            ("Inventory, evidence and leads", "Tab · View"), ("Pause / this help", "Esc · F1 · Menu"), ("Fullscreen", "F11"),
        ]
        for i, (a, b) in enumerate(rows):
            self.text(a, 60, 90 + i * 18, PAPER)
            self.text(b, 380, 90 + i * 18, DIM)
        self.text("Light is everything: the darker you stand, the less they see. Lanterns, matches and gunfire",
                  60, 370, (190, 196, 214))
        self.text("make you visible. Breaking a bulb changes a room.", 60, 384, (190, 196, 214))
        self.text("Esc / Enter: resume      Q: quit to desktop", 60, C.UI_H - 40, GOLD)

    def draw_death(self, t):
        a = int(min(1.0, t / 1.2) * 255)
        self.text("Ines goes down.", C.UI_W // 2, 220, (220, 200, 190), self.big, alpha=a, center=True)
        if t > 1.5:
            self.text("Press E to get back up.", C.UI_W // 2, 260, DIM, alpha=a, center=True)
