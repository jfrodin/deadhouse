"""Rooftops of No. 14 and the Hotel Calla. The city opens up; the lantern waits in the pigeon loft."""
import math

from ...sim.world import Pickup

AREA = {
    "id": "roof",
    "name": "The roofs over Lantern Row",
    "bake": "roof",
    "post": {"ambient": (0.09, 0.1, 0.17), "fog": 0.18, "fog_color": (0.3, 0.3, 0.5), "bloom": 1.1,
             "exposure": 1.15, "reflect": 0.9},
    "rain": 1.0,
    "reflections": True,
    "floor": "wet",
    "ground_y": 110,
    "spawns": {"from_ladder": (44, 280), "from_window": (44, 280)},
    "spawn_facing": {"from_ladder": (0, -1)},
    "respawn": "from_ladder",
    "title_card": ["THE ROOFS", "Above Lantern Row"],
    "exits": [],
    "audio": {"ambience": ["roof"], "music": "velour", "music_variant": "_out", "music_source": (560, 200),
              "music_radius": 520, "music_gain": 0.5},
}


def setup(world):
    st = world.state
    a = world.area
    if not st.has("lantern"):
        world.spawn(Pickup(148, 208, "lantern", 1, flag="roof.lantern"))
    world.interactables += [
        {"id": "escape", "x": a.anchors["escape_top"][0], "y": a.anchors["escape_top"][1] + 6, "verb": "Climb down",
         "label": "Fire escape", "radius": 20},
    ]
    if not st.check("roof.entered"):
        st.set("roof.entered")
        world.whisper("silas", "Best view in Corvane, and it's free. The pigeon man keeps his loft on Fourteen. Kept.")


def on_interact(world, it):
    if it["id"] == "escape":
        world.start_dialogue("roof_escape")


def go_alley(world):
    p = world.player
    world.sfx("climb", p.x, p.y)
    p.start_busy("climb", 0.8, lambda: world.request_transition("alley", "from_ladder"))


def go_window(world):
    p = world.player
    world.sfx("climb", p.x, p.y)
    p.start_busy("climb", 0.8, lambda: world.request_transition("tenement", "from_window"))


def on_pickup(world, item):
    if item == "lantern":
        world.toast("Bull's-eye lantern. F to light it, C to flash. Light makes you a target.", 4)
        world.whisper("silas", "A railwayman's lantern. In my line of work we called that a confession. Use it like one.")


def tick(world, dt):
    pass


HOOKS = {"go_alley": go_alley, "go_window": go_window}
