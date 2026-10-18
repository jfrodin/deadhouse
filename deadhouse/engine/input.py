"""Action-based input: keyboard + gamepad, with press buffering."""
from __future__ import annotations

import pygame

ACTIONS = ("up", "down", "left", "right", "attack", "heavy", "dodge", "interact", "throw", "shoot", "lantern",
           "flash", "sprint", "inventory", "pause", "confirm", "cancel", "help", "remnant", "heal")

KEYMAP = {
    "up": (pygame.K_w, pygame.K_UP),
    "down": (pygame.K_s, pygame.K_DOWN),
    "left": (pygame.K_a, pygame.K_LEFT),
    "right": (pygame.K_d, pygame.K_RIGHT),
    "attack": (pygame.K_j,),
    "heavy": (pygame.K_k,),
    "dodge": (pygame.K_SPACE,),
    "interact": (pygame.K_e,),
    "throw": (pygame.K_q,),
    "shoot": (pygame.K_l,),
    "lantern": (pygame.K_f,),
    "flash": (pygame.K_c,),
    "sprint": (pygame.K_LSHIFT, pygame.K_RSHIFT),
    "inventory": (pygame.K_TAB, pygame.K_i),
    "pause": (pygame.K_ESCAPE,),
    "confirm": (pygame.K_RETURN, pygame.K_e, pygame.K_j),
    "cancel": (pygame.K_ESCAPE, pygame.K_BACKSPACE),
    "help": (pygame.K_F1,),
    "remnant": (pygame.K_r,),
    "heal": (pygame.K_h,),
}

# Xbox-style layout (SDL joystick / XInput button indices)
PADMAP = {
    "attack": (2,),      # X
    "heavy": (3,),       # Y
    "dodge": (1,),       # B
    "interact": (0,),    # A
    "confirm": (0,),
    "cancel": (1,),
    "throw": (4,),       # LB
    "shoot": (5,),       # RB
    "inventory": (6,),   # Back/View
    "pause": (7,),       # Start/Menu
    "flash": (8,),       # left stick click
    "lantern": (9,),     # right stick click
}

BUFFER_TIME = 0.15


class Input:
    def __init__(self):
        self.held: dict[str, bool] = {a: False for a in ACTIONS}
        self.pressed: dict[str, bool] = {a: False for a in ACTIONS}
        self.released: dict[str, bool] = {a: False for a in ACTIONS}
        self._buffer: dict[str, float] = {}
        self.axis = [0.0, 0.0]
        self.pads: dict[int, pygame.joystick.JoystickType] = {}
        self.scripted: dict[str, bool] | None = None  # for automated tests / capture
        self.text_events: list[str] = []
        self._key_to_actions: dict[int, list[str]] = {}
        for a, keys in KEYMAP.items():
            for k in keys:
                self._key_to_actions.setdefault(k, []).append(a)
        self._pad_to_actions: dict[int, list[str]] = {}
        for a, btns in PADMAP.items():
            for b in btns:
                self._pad_to_actions.setdefault(b, []).append(a)
        self._pad_held: dict[str, bool] = {}
        self._key_held: dict[str, bool] = {}
        self.last_device = "keyboard"

    def begin_frame(self):
        for a in ACTIONS:
            self.pressed[a] = False
            self.released[a] = False

    def _set(self, action: str, down: bool, source: dict):
        before = self.held[action]
        source[action] = down
        now = self._key_held.get(action, False) or self._pad_held.get(action, False)
        self.held[action] = now
        if now and not before:
            self.pressed[action] = True
            self._buffer[action] = BUFFER_TIME
        elif before and not now:
            self.released[action] = True

    def handle(self, ev: pygame.event.Event):
        if ev.type == pygame.KEYDOWN:
            self.last_device = "keyboard"
            for a in self._key_to_actions.get(ev.key, ()):
                self._set(a, True, self._key_held)
        elif ev.type == pygame.KEYUP:
            for a in self._key_to_actions.get(ev.key, ()):
                self._set(a, False, self._key_held)
        elif ev.type == pygame.CONTROLLERBUTTONDOWN or ev.type == pygame.JOYBUTTONDOWN:
            self.last_device = "pad"
            for a in self._pad_to_actions.get(ev.button, ()):
                self._set(a, True, self._pad_held)
        elif ev.type == pygame.CONTROLLERBUTTONUP or ev.type == pygame.JOYBUTTONUP:
            for a in self._pad_to_actions.get(ev.button, ()):
                self._set(a, False, self._pad_held)
        elif ev.type == pygame.JOYHATMOTION:
            self.last_device = "pad"
            hx, hy = ev.value
            self._set("remnant", hy > 0, self._pad_held)
            self._set("heal", hy < 0, self._pad_held)
            # d-pad left/right also navigate menus
            self._set("left", hx < 0, self._pad_held)
            self._set("right", hx > 0, self._pad_held)
        elif ev.type == pygame.JOYDEVICEADDED:
            try:
                j = pygame.joystick.Joystick(ev.device_index)
                self.pads[j.get_instance_id()] = j
            except pygame.error:
                pass
        elif ev.type == pygame.JOYDEVICEREMOVED:
            self.pads.pop(ev.instance_id, None)

    def update(self, dt: float):
        for a in list(self._buffer):
            self._buffer[a] -= dt
            if self._buffer[a] <= 0:
                del self._buffer[a]
        if self.scripted is not None:
            for a in ACTIONS:
                want = self.scripted.get(a, False)
                if want != self.held[a]:
                    self._set(a, want, self._key_held)
        x = (1.0 if self.held["right"] else 0.0) - (1.0 if self.held["left"] else 0.0)
        y = (1.0 if self.held["down"] else 0.0) - (1.0 if self.held["up"] else 0.0)
        for j in self.pads.values():
            try:
                ax, ay = j.get_axis(0), j.get_axis(1)
            except pygame.error:
                continue
            if abs(ax) > 0.25 or abs(ay) > 0.25:
                x, y = ax, ay
                self.last_device = "pad"
            # triggers -> lantern flash / sprint
            try:
                if j.get_numaxes() > 5:
                    self._set("sprint", j.get_axis(4) > 0.3, self._pad_held)
                    self._set("flash", j.get_axis(5) > 0.3 or self._pad_held.get("flash", False), self._pad_held)
            except pygame.error:
                pass
        mag = (x * x + y * y) ** 0.5
        if mag > 1.0:
            x, y = x / mag, y / mag
        self.axis = [x, y]

    def consume(self, action: str) -> bool:
        """True if the action was pressed within the buffer window; consumes it."""
        if action in self._buffer:
            del self._buffer[action]
            return True
        return False

    def peek(self, action: str) -> bool:
        return action in self._buffer

    def clear_buffer(self):
        self._buffer.clear()
