"""Entry point: builds the App and the top-level game states."""
from __future__ import annotations

import argparse

import pygame

from . import config as C
from .engine.app import App


def parse(argv=None):
    ap = argparse.ArgumentParser(prog="deadhouse")
    ap.add_argument("--area", default=None, help="start directly in an area (dev)")
    ap.add_argument("--spawn", default=None, help="spawn point name or x,y (dev)")
    ap.add_argument("--shot", default=None, help="render N frames hidden, save a screenshot, exit")
    ap.add_argument("--frames", type=int, default=90)
    ap.add_argument("--script", default=None, help="capture script (tools/capture.py format)")
    ap.add_argument("--scale", type=int, default=C.DEFAULT_WINDOW_SCALE)
    ap.add_argument("--fullscreen", action="store_true")
    ap.add_argument("--skip-title", action="store_true")
    ap.add_argument("--title", action="store_true", help="force the title screen (also in --shot mode)")
    ap.add_argument("--fps", action="store_true", help="show the frame rate")
    return ap.parse_args(argv)


def run(argv=None):
    args = parse(argv)
    hidden = args.shot is not None
    app = App(hidden=hidden, scale=4 if hidden else args.scale, fullscreen=args.fullscreen and not hidden)
    from .engine.audio import AudioEngine
    app.audio = AudioEngine(enabled=not hidden)
    from .states.play import PlayState
    from .states.title import TitleState

    if args.title or not (args.area or hidden or args.skip_title):
        app.push(TitleState(app))
    else:
        app.push(PlayState(app, area_id=args.area or "row", spawn=args.spawn))
        app.top.show_fps = args.fps

    if hidden:
        for _ in range(args.frames):
            app.step(C.DT, pygame.event.get())
            app.draw(C.DT)
            pygame.display.flip()
        pygame.image.save(app.renderer.read_screen(), args.shot)
        pygame.quit()
        return 0
    app.run()
    return 0
