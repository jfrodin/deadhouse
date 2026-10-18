"""Persistent game state: flags, inventory, Remnants, what characters remember."""
from __future__ import annotations

import json


class GameState:
    def __init__(self):
        self.flags: set[str] = set()
        self.inventory: dict[str, int] = {}
        self.equipped = "razor"
        self.remnants: list[str] = []
        self.stance: dict[str, int] = {"cold": 0, "warm": 0, "wry": 0, "blunt": 0}
        self.memory: dict[str, list[str]] = {}   # character -> things they remember about Ines
        self.night = 2
        self.log: list[str] = []

    # ---------------------------------------------------------------- inventory
    def give(self, item: str, n: int = 1):
        self.inventory[item] = self.inventory.get(item, 0) + n

    def take(self, item: str, n: int = 1) -> bool:
        if self.inventory.get(item, 0) < n:
            return False
        self.inventory[item] -= n
        if self.inventory[item] <= 0:
            del self.inventory[item]
        return True

    def has(self, item: str) -> bool:
        return self.inventory.get(item, 0) > 0

    def count(self, item: str) -> int:
        return self.inventory.get(item, 0)

    # ---------------------------------------------------------------- flags
    def set(self, flag: str):
        self.flags.add(flag)

    def unset(self, flag: str):
        self.flags.discard(flag)

    def remember(self, who: str, what: str):
        self.memory.setdefault(who, [])
        if what not in self.memory[who]:
            self.memory[who].append(what)
        self.flags.add(f"{who}.{what}")

    def check(self, cond: str | None) -> bool:
        """Conditions: 'flag', '!flag', 'has:item', 'remnant:silas', 'stance:cold>=2', joined by '&' or '|'."""
        if not cond:
            return True
        if "|" in cond:
            return any(self.check(c) for c in cond.split("|"))
        if "&" in cond:
            return all(self.check(c) for c in cond.split("&"))
        c = cond.strip()
        neg = c.startswith("!")
        if neg:
            c = c[1:].strip()
        if c.startswith("has:"):
            v = self.has(c[4:])
        elif c.startswith("remnant:"):
            v = c[8:] in self.remnants
        elif c.startswith("stance:"):
            key, _, num = c[7:].partition(">=")
            v = self.stance.get(key, 0) >= int(num or 1)
        elif c.startswith("count:"):
            key, _, num = c[6:].partition(">=")
            v = self.count(key) >= int(num or 1)
        else:
            v = c in self.flags
        return v != neg

    # ---------------------------------------------------------------- save/load
    def to_json(self) -> str:
        return json.dumps({
            "flags": sorted(self.flags), "inventory": self.inventory, "equipped": self.equipped,
            "remnants": self.remnants, "stance": self.stance, "memory": self.memory, "night": self.night,
        }, indent=1)

    @classmethod
    def from_json(cls, s: str) -> "GameState":
        d = json.loads(s)
        g = cls()
        g.flags = set(d["flags"])
        g.inventory = dict(d["inventory"])
        g.equipped = d["equipped"]
        g.remnants = list(d["remnants"])
        g.stance = dict(d["stance"])
        g.memory = {k: list(v) for k, v in d["memory"].items()}
        g.night = d.get("night", 2)
        return g
