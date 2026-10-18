import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402
import pytest  # noqa: E402

pygame.init()

from deadhouse import config as C  # noqa: E402
from deadhouse.engine.input import Input  # noqa: E402
from deadhouse.render.assets import Assets  # noqa: E402
from deadhouse.sim.dialogue import Script  # noqa: E402
from deadhouse.sim.world import World  # noqa: E402
from deadhouse.states.play import PlayState  # noqa: E402

AREAS = ["row", "tenement", "alley", "roof", "marquee"]


class Driver:
    """Steps a World with scripted input, the same way the game loop does."""

    def __init__(self, area="row", spawn=None, state=None):
        self.inp = Input()
        self.assets = Assets()
        self.state = state or PlayState.new_game_state()
        self.script = Script.load_dir(os.path.join(C.CONTENT_DIR, "dialogue"))
        self.world = World(self.assets, self.state, self.inp, self.script)
        self.world.hooks = lambda: {}
        self.world.load_area(area, spawn, keep_player=False)
        self.inp.scripted = {}

    @property
    def p(self):
        return self.world.player

    def step(self, n=1, **held):
        for _ in range(n):
            self.inp.begin_frame()
            self.inp.scripted = dict(held)
            self.inp.update(C.DT)
            self.world.update(C.DT)
            self.world.events.clear()

    def tap(self, action, settle=6):
        self.step(1, **{action: True})
        self.step(settle)

    def walk_to(self, x, y, max_frames=900, tol=3.0):
        for _ in range(max_frames):
            dx, dy = x - self.p.x, y - self.p.y
            if abs(dx) < tol and abs(dy) < tol:
                return True
            held = {}
            if dx > tol:
                held["right"] = True
            elif dx < -tol:
                held["left"] = True
            if dy > tol:
                held["down"] = True
            elif dy < -tol:
                held["up"] = True
            self.step(1, **held)
        return False


@pytest.fixture
def driver():
    return Driver
