"""Window, GL context and the fixed-timestep main loop."""
from __future__ import annotations

import os
import time

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import moderngl  # noqa: E402
import pygame  # noqa: E402

from .. import config as C  # noqa: E402
from .input import Input  # noqa: E402
from .renderer import Renderer  # noqa: E402


class App:
    """Owns the platform layer. Game logic lives in `states` pushed onto the stack."""

    def __init__(self, hidden: bool = False, scale: int = C.DEFAULT_WINDOW_SCALE, fullscreen: bool = False):
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        pygame.joystick.init()
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
        pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER, 1)
        self.hidden = hidden
        self.fullscreen = fullscreen
        self.windowed_size = (C.VIEW_W * scale, C.VIEW_H * scale)
        self._make_window()
        pygame.display.set_caption("Deadhouse — Prototype 1")
        self.ctx = moderngl.create_context()
        self.renderer = Renderer(self.ctx, self.window_size)
        self.input = Input()
        self.running = True
        self.states: list = []
        self.frame = 0
        self.time = 0.0
        self.fps = 0.0
        self._fps_acc = 0.0
        self._fps_n = 0

    def _make_window(self):
        flags = pygame.OPENGL | pygame.DOUBLEBUF
        if self.hidden:
            flags |= pygame.HIDDEN
        if self.fullscreen:
            flags |= pygame.FULLSCREEN
            info = pygame.display.Info()
            size = (info.current_w, info.current_h)
        else:
            flags |= pygame.RESIZABLE
            size = self.windowed_size
        pygame.display.set_mode(size, flags, vsync=0 if self.hidden else 1)
        self.window_size = pygame.display.get_window_size()

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        # keeping the GL context alive across mode switches: pygame-ce preserves it for OPENGL windows
        pygame.display.toggle_fullscreen()
        self.window_size = pygame.display.get_window_size()
        self.renderer.resize(self.window_size)

    def push(self, state):
        self.states.append(state)
        state.enter()

    def pop(self):
        s = self.states.pop()
        s.exit()
        return s

    def replace(self, state):
        while self.states:
            self.pop()
        self.push(state)

    @property
    def top(self):
        return self.states[-1] if self.states else None

    def step(self, dt: float, events=None):
        """Advance one fixed step. Exposed so tests and capture tools can drive frames."""
        self.input.begin_frame()
        for ev in events if events is not None else pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
            elif ev.type == pygame.VIDEORESIZE or ev.type == pygame.WINDOWSIZECHANGED:
                self.window_size = pygame.display.get_window_size()
                self.renderer.resize(self.window_size)
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_F11:
                self.toggle_fullscreen()
            self.input.handle(ev)
        self.input.update(dt)
        if self.top:
            self.top.update(dt)
        self.time += dt
        self.frame += 1

    def draw(self, dt: float):
        if self.top:
            self.top.draw(dt)

    def run(self):
        clock = pygame.time.Clock()
        acc = 0.0
        last = time.perf_counter()
        pending: list = []
        while self.running and self.states:
            now = time.perf_counter()
            frame_dt = min(0.1, now - last)
            last = now
            acc += frame_dt
            steps = 0
            pending.extend(pygame.event.get())
            while acc >= C.DT and steps < 4:
                self.step(C.DT, pending)
                pending = []
                acc -= C.DT
                steps += 1
            if steps == 4:
                acc = 0.0
            self.draw(frame_dt)
            pygame.display.flip()
            self._fps_acc += frame_dt
            self._fps_n += 1
            if self._fps_acc >= 0.5:
                self.fps = self._fps_n / self._fps_acc
                self._fps_acc = 0.0
                self._fps_n = 0
            clock.tick(240)
        pygame.quit()
