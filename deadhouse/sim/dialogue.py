"""A small branching-dialogue language and its runner.

Script syntax (.dlg files in content/dialogue):

    === node_id
    Vivienne (amused): A line of dialogue. Name may carry an (expression).
    > Narration, in Ines's head.
    ? {flag & !other} -> some_node        conditional jump
    ~ set flag | unset flag | give item [n] | take item [n]
    ~ remember who what | remnant name | call hook_name | stance cold
    * {cond} [warm] Choice text -> target   choices (consecutive lines form a menu)
    -> target | -> END

The [stance] tag on a choice (cold / warm / wry / blunt) is recorded in GameState.stance:
how Ines has been speaking shapes how people answer her.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

LINE_RE = re.compile(r"^([A-Za-z][A-Za-z .'\-]*?)\s*(?:\(([a-z_]+)\))?\s*:\s*(.+)$")
CHOICE_RE = re.compile(r"^\*\s*(?:\{([^}]*)\})?\s*(?:\[(cold|warm|wry|blunt)\])?\s*(.+?)\s*->\s*([A-Za-z0-9_]+)\s*$")
JUMP_RE = re.compile(r"^\?\s*\{([^}]*)\}\s*->\s*([A-Za-z0-9_]+)\s*$")


@dataclass
class Say:
    speaker: str      # id (lower-case) or "" for narration
    name: str
    text: str
    expr: str | None = None


@dataclass
class Choice:
    text: str
    target: str
    cond: str | None = None
    stance: str | None = None


@dataclass
class Menu:
    options: list[Choice] = field(default_factory=list)


@dataclass
class Effect:
    cmd: str
    args: list[str]


@dataclass
class Jump:
    target: str
    cond: str | None = None


class Script:
    def __init__(self):
        self.nodes: dict[str, list] = {}

    @classmethod
    def load_dir(cls, path: str) -> "Script":
        s = cls()
        for fn in sorted(os.listdir(path)):
            if fn.endswith(".dlg"):
                with open(os.path.join(path, fn), encoding="utf-8") as f:
                    s.parse(f.read(), fn)
        return s

    def parse(self, text: str, source: str = "<str>"):
        node = None
        for lineno, raw in enumerate(text.splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("==="):
                node = line[3:].strip()
                if node in self.nodes:
                    raise ValueError(f"{source}:{lineno}: duplicate node {node}")
                self.nodes[node] = []
                continue
            if node is None:
                raise ValueError(f"{source}:{lineno}: statement outside a node")
            body = self.nodes[node]
            if line.startswith("*"):
                m = CHOICE_RE.match(line)
                if not m:
                    raise ValueError(f"{source}:{lineno}: bad choice: {line}")
                ch = Choice(m.group(3), m.group(4), m.group(1), m.group(2))
                if body and isinstance(body[-1], Menu):
                    body[-1].options.append(ch)
                else:
                    body.append(Menu([ch]))
            elif line.startswith("->"):
                body.append(Jump(line[2:].strip()))
            elif line.startswith("?"):
                m = JUMP_RE.match(line)
                if not m:
                    raise ValueError(f"{source}:{lineno}: bad conditional jump: {line}")
                body.append(Jump(m.group(2), m.group(1)))
            elif line.startswith("~"):
                parts = line[1:].split()
                body.append(Effect(parts[0], parts[1:]))
            elif line.startswith(">"):
                body.append(Say("", "", line[1:].strip()))
            else:
                m = LINE_RE.match(line)
                if not m:
                    raise ValueError(f"{source}:{lineno}: cannot parse: {line}")
                name = m.group(1).strip()
                body.append(Say(name.lower().split()[0], name, m.group(3).strip(), m.group(2)))

    def validate(self) -> list[str]:
        """Return a list of problems (unknown jump targets)."""
        errs = []
        for nid, body in self.nodes.items():
            for st in body:
                targets = []
                if isinstance(st, Jump):
                    targets = [st.target]
                elif isinstance(st, Menu):
                    targets = [c.target for c in st.options]
                for t in targets:
                    if t != "END" and t not in self.nodes:
                        errs.append(f"{nid}: unknown target {t}")
        return errs


class Runner:
    """Steps through a node, applying effects, stopping at lines and menus."""

    def __init__(self, script: Script, state, hooks=None):
        self.script = script
        self.state = state
        self.hooks = hooks or {}
        self.node = None
        self.pc = 0
        self.current = None  # Say | Menu(filtered) | None (= ended)
        self.visible_choices: list[Choice] = []
        self.ended = True

    def start(self, node: str):
        self.node = node
        self.pc = 0
        self.ended = False
        self._run()

    def _goto(self, target: str):
        if target == "END":
            self.ended = True
            self.current = None
            return
        if target not in self.script.nodes:
            raise KeyError(f"dialogue node {target!r} not found")
        self.node = target
        self.pc = 0

    def _run(self):
        """Advance until something must be shown or the dialogue ends."""
        guard = 0
        while not self.ended:
            guard += 1
            if guard > 500:
                raise RuntimeError("dialogue loop")
            body = self.script.nodes[self.node]
            if self.pc >= len(body):
                self.ended = True
                self.current = None
                return
            st = body[self.pc]
            self.pc += 1
            if isinstance(st, Say):
                self.current = st
                return
            if isinstance(st, Menu):
                opts = [c for c in st.options if self.state.check(c.cond)]
                if not opts:
                    continue
                self.visible_choices = opts
                self.current = st
                return
            if isinstance(st, Jump):
                if st.cond is None or self.state.check(st.cond):
                    self._goto(st.target)
                continue
            if isinstance(st, Effect):
                self._effect(st)

    def _effect(self, e: Effect):
        s = self.state
        a = e.args
        if e.cmd == "set":
            s.set(a[0])
        elif e.cmd == "unset":
            s.unset(a[0])
        elif e.cmd == "give":
            s.give(a[0], int(a[1]) if len(a) > 1 else 1)
            if "on_give" in self.hooks:
                self.hooks["on_give"](a[0], int(a[1]) if len(a) > 1 else 1)
        elif e.cmd == "take":
            s.take(a[0], int(a[1]) if len(a) > 1 else 1)
        elif e.cmd == "remember":
            s.remember(a[0], a[1])
        elif e.cmd == "remnant":
            if a[0] not in s.remnants:
                s.remnants.append(a[0])
        elif e.cmd == "stance":
            s.stance[a[0]] = s.stance.get(a[0], 0) + 1
        elif e.cmd == "call":
            fn = self.hooks.get(a[0])
            if fn is None:
                raise KeyError(f"dialogue hook {a[0]!r} not registered")
            fn(*a[1:])
        else:
            raise ValueError(f"unknown dialogue effect {e.cmd}")

    def advance(self, choice: int | None = None):
        if self.ended:
            return
        if isinstance(self.current, Menu):
            if choice is None:
                return
            ch = self.visible_choices[choice]
            if ch.stance:
                self.state.stance[ch.stance] = self.state.stance.get(ch.stance, 0) + 1
            self.chosen_text = ch.text
            self._goto(ch.target)
        self._run()
