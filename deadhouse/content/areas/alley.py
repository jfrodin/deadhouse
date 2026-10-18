"""The alley beside No. 14: laundry overhead, a kitchen door, and the fire escape (Silas's Lesson)."""
from ...sim.npc import NPC
from ...sim.world import Pickup

AREA = {
    "id": "alley",
    "name": "Garnet Alley",
    "bake": "alley",
    "post": {"ambient": (0.09, 0.095, 0.15), "fog": 0.3, "fog_color": (0.3, 0.28, 0.42), "bloom": 1.0,
             "exposure": 1.15, "reflect": 0.9},
    "rain": 1.0,
    "reflections": True,
    "floor": "wet",
    "ground_y": 96,
    "spawns": {"from_row_a": (160, 468), "from_row_b": (160, 468), "from_ladder": (78, 346), "from_window": (78, 346)},
    "spawn_facing": {"from_row_a": (0, -1), "from_ladder": (1, 0)},
    "shelter": [(56, 200, 46, 22), (56, 300, 40, 22)],
    "respawn": "from_row_a",
    "exits": [{"rect": (100, 474, 120, 8), "to": "row", "spawn": "from_alley_a"}],
    "audio": {"ambience": ["alley", "city_far"], "amb_gain": {"city_far": 0.6}, "music": "velour",
              "music_variant": "_out", "music_source": (160, 560), "music_radius": 420, "music_gain": 0.6},
}


def setup(world):
    st = world.state
    a = world.area
    world.spawn(NPC(244, 272, "ped_long_a", "Rosa", "rosa_start", facing=(-1, 0), idle_anim="smoke", tag="rosa",
                    barks=["Five minutes. I get five minutes.", "Don't look at me like that, I'm on my break."]))
    world.entities[-1].overlay.append("cigarette")
    if not st.check("alley.tire_iron"):
        world.spawn(Pickup(86, 376, "tire_iron", 1, flag="alley.tire_iron"))
    if not st.check("alley.bottle"):
        world.spawn(Pickup(200, 180, "bottle", 1, flag="alley.bottle"))
    world.interactables += [
        {"id": "ladder", "x": a.anchors["ladder"][0], "y": a.anchors["ladder"][1], "verb": "Climb",
         "label": "Fire escape", "radius": 18, "requires": "remnant:silas"},
        {"id": "gate", "x": a.anchors["gate"][0], "y": a.anchors["gate"][1], "verb": "Examine", "label": "Iron gate"},
    ]
    if not st.check("alley.entered"):
        st.set("alley.entered")
        world.whisper("silas", "There. Rust on the ladder, not on the rungs. Somebody uses it. Up we go, Calder.")


def on_interact(world, it):
    p = world.player
    if it["id"] == "ladder":
        world.sfx("climb", p.x, p.y)
        p.face(-1, 0)
        p.start_busy("climb", 0.9, lambda: world.request_transition("roof", "from_ladder"), speed=1.0)
    elif it["id"] == "gate":
        world.start_dialogue("alley_gate")


def on_pickup(world, item):
    if item == "tire_iron":
        world.toast("Tire iron. Tab to equip — slower, heavier, honest.", 3.5)
        world.whisper("maud", "Now that's a conversation-ender.")
