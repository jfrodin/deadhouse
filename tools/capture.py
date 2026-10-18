"""Drive the real game (GPU renderer, hidden window) with scripted input and save screenshots.

    python tools/capture.py <script.json> <out_dir>

Script: a list of steps, executed in order:
    {"area": "row", "spawn": "560,190"}          (re)start in an area (first step)
    {"state": {"give": {"lantern": 1}, "remnants": ["maud"], "flags": ["x"]}}
    {"wait": 60}                                   advance frames with no input
    {"hold": ["right", "sprint"], "frames": 40}    hold actions for N frames
    {"tap": "attack", "settle": 8}                 press once, then advance
    {"walk_to": [x, y]}                            walk the player there (simple steering)
    {"place": [x, y], "face": [0, -1]}             teleport the player (for staging shots)
    {"dialogue": "viv_start", "picks": [0, 1]}     run a dialogue, choosing options; screenshots inside via "shot_at"
    {"shot": "name.png"}                           save a screenshot
    {"eval": "python expression with w=world, p=player, s=state"}   staging helper
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pygame  # noqa: E402

from deadhouse import config as C  # noqa: E402
from deadhouse.engine.app import App  # noqa: E402
from deadhouse.sim.dialogue import Menu  # noqa: E402


def main(script_path, out_dir):
    with open(script_path, encoding="utf-8") as f:
        steps = json.load(f)
    os.makedirs(out_dir, exist_ok=True)
    app = App(hidden=True, scale=4)
    app.audio = None
    from deadhouse.states.play import PlayState
    from deadhouse.states.title import TitleState

    def frame(held=None):
        app.input.scripted = {a: True for a in (held or [])}
        app.step(C.DT, pygame.event.get())
        app.draw(C.DT)
        pygame.display.flip()

    def shot(name):
        frame()
        pygame.image.save(app.renderer.read_screen(), os.path.join(out_dir, name))
        print("  saved", name)

    for st in steps:
        if "area" in st:
            if st["area"] == "title":
                app.replace(TitleState(app))
            else:
                app.replace(PlayState(app, area_id=st["area"], spawn=st.get("spawn")))
            ps = app.top
            if hasattr(ps, "fade"):
                ps.fade = 0.0
                ps.fade_dir = 0
            continue
        ps = app.top
        w = getattr(ps, "world", None)
        if "state" in st:
            s = ps.state
            for k, n in st["state"].get("give", {}).items():
                s.give(k, n)
            for r in st["state"].get("remnants", []):
                if r not in s.remnants:
                    s.remnants.append(r)
            for fl in st["state"].get("flags", []):
                s.set(fl)
            if "equip" in st["state"]:
                s.equipped = st["state"]["equip"]
        if "place" in st:
            w.player.x, w.player.y = st["place"]
            if "face" in st:
                w.player.fx, w.player.fy = st["face"]
            ps.cam = [w.player.x - C.VIEW_W / 2, w.player.y - C.VIEW_H / 2 - 16]
            ps._clamp_cam()
        if "eval" in st:
            exec(st["eval"], {"w": w, "p": w.player, "s": ps.state, "ps": ps})
        if "wait" in st:
            for _ in range(st["wait"]):
                frame()
        if "hold" in st:
            for _ in range(st.get("frames", 30)):
                frame(st["hold"])
        if "tap" in st:
            frame([st["tap"]])
            for _ in range(st.get("settle", 8)):
                frame()
        if "walk_to" in st:
            tx, ty = st["walk_to"]
            for _ in range(st.get("max", 900)):
                dx, dy = tx - w.player.x, ty - w.player.y
                if abs(dx) < 3 and abs(dy) < 3:
                    break
                held = []
                if dx > 3:
                    held.append("right")
                elif dx < -3:
                    held.append("left")
                if dy > 3:
                    held.append("down")
                elif dy < -3:
                    held.append("up")
                held += st.get("with", [])
                frame(held)
        if "dialogue" in st:
            w.start_dialogue(st["dialogue"], w.by_tag(st.get("who")) if st.get("who") else None)
            frame()
            picks = list(st.get("picks", []))
            shots = {int(k): v for k, v in st.get("shot_at", {}).items()}
            n = 0
            guard = 0
            while ps.dialogue is not None and guard < 400:
                guard += 1
                for _ in range(st.get("read_frames", 20)):
                    frame()
                if n in shots:
                    shot(shots[n])
                n += 1
                if ps.dialogue is None:
                    break
                if ps.dialogue.mode == "menu":
                    k = picks.pop(0) if picks else 0
                    for _ in range(k):
                        frame(["down"])
                        frame()
                    frame(["confirm"])
                else:
                    frame(["confirm"])
                    frame()
                    if ps.dialogue is not None and ps.dialogue.mode == "say" and ps.dialogue.reveal < len(ps.dialogue.current.text):
                        frame(["confirm"])
                frame()
        if "shot" in st:
            shot(st["shot"])
        if os.environ.get("CAPTURE_DEBUG") and getattr(app.top, "world", None) is not None:
            ww = app.top.world
            print("   ", list(st.keys())[0], ww.area.id, round(ww.player.x), round(ww.player.y), ww.player.state)
    pygame.quit()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
