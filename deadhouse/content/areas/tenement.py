"""No. 14, the Garnet Arms — Hobb's building. The prototype's combat space.

Four approaches are supported by the layout and the AI:
  head-on        fight up the stairs (the gunman holds the top floor)
  darkness       break the ceiling bulbs with bottles; unaware men can be taken from behind
  outside        climb the alley fire escape and come in through Hobb's window
  lantern        blind Hobb (or anyone) with the bull's-eye lantern and close the distance
Firing the revolver brings two more of Hobb's men in from the street.
"""
import pygame

from ...sim.enemy import Enemy
from ...sim.npc import NPC
from ...sim.world import Pickup

AREA = {
    "id": "tenement",
    "name": "No. 14, the Garnet Arms",
    "bake": "tenement",
    "post": {"ambient": (0.045, 0.045, 0.065), "fog": 0.04, "fog_color": (0.25, 0.22, 0.25), "bloom": 1.0,
             "exposure": 1.2, "reflect": 0.7, "saturation": 0.95},
    "rain": 0.0,
    "reflections": False,
    "floor": "wood",
    "ground_y": 0,
    "spawns": {"from_row": (240, 650), "from_window": (64, 152)},
    "spawn_facing": {"from_row": (0, -1), "from_window": (1, 0)},
    "respawn": "from_row",
    "title_card": ["No. 14", "The Garnet Arms  ·  Hobb's building"],
    "exits": [{"rect": (222, 668, 36, 12), "to": "row", "spawn": "from_tenement"}],
    "audio": {"ambience": ["interior_tenement"], "music": "velour", "music_variant": "_radio",
              "music_source": (305, 440), "music_radius": 230, "music_gain": 0.55},
}

ENEMY_BARKS = {
    "alert": ["Hey! Who let you in?", "There she is!", "Deadhouse — you lost?", "Get her!"],
    "suspicious": ["Who's on the stairs?", "Mrs. Kowal? That you?", "Somebody there?"],
    "noise": ["What was that?", "Bulb's gone again—", "...Rats."],
    "giveup": ["Nothing.", "This building hates me.", "Rats. Big ones."],
    "body": ["Danny? Danny!", "Somebody dropped Pike!"],
    "blinded": ["My eyes—!", "Can't see! Can't SEE!"],
    "reload": ["Hold still, sweetheart.", "Loading— don't move."],
}


def setup(world):
    st = world.state
    a = world.area
    for p in a.props:
        if p.kind == "bulb":
            p.state["breakable"] = True
            p.state["target"] = (p.x, p.y + 2)
            if st.check(f"broke.{p.id}"):
                p.state["broken"] = True
                p.light.enabled = False
    if not st.check("tenement.cleared"):
        world.spawn(Enemy(60, 628, "brawler", facing=(1, 0), name="Danny Dunne", group="ground"))
        world.spawn(Enemy(132, 628, "brawler", facing=(-1, 0.2), name="Mick Dunne", group="ground"))
        world.spawn(Enemy(250, 320, "knifeman", facing=(0, 1), name="Pike", group="landing",
                          patrol=[(190, 322), (316, 322)]))
        if not st.check("tenement.hobb_down"):
            hobb = world.spawn(Enemy(292, 168, "gunman", facing=(0, 1), name="Hobb", group="top"))
            hobb.tag = "hobb"
    if not st.check("tenement.bottles"):
        world.spawn(Pickup(206, 652, "bottle", 2, flag="tenement.bottles"))
    if not st.has("camera") and not st.check("quest.camera_done"):
        world.spawn(Pickup(296, 152, "camera", 1, flag="tenement.camera"))
    if not st.check("tenement.ledger"):
        world.spawn(Pickup(274, 152, "ledger", 1, flag="tenement.ledger"))
    world.interactables += [
        {"id": "window", "x": 60, "y": 150, "verb": "Climb out", "label": "Fire escape", "radius": 16},
        {"id": "door_2b", "x": 305, "y": 440, "verb": "Knock", "label": "2B", "radius": 16},
        {"id": "door_1a", "x": 159, "y": 590, "verb": "Knock", "label": "1A", "radius": 16},
    ]
    a.defn["_reinf"] = None
    if not st.check("tenement.entered"):
        st.set("tenement.entered")
        if st.check("tip.tenement"):
            world.whisper("silas", "Two Dunnes and a bottle downstairs, like Sully said. Nobody's looking at the bulb, Calder.")
        else:
            world.whisper("silas", "Rye and cheap cigars. Two of them in the hall, at least. Lights make friends of nobody.")


def on_noise(world, n):
    st = world.state
    if n.source == "gunshot" and n.team == "player" and not st.check("tenement.reinf"):
        st.set("tenement.reinf")
        world.area.defn["_reinf"] = 3.5


def tick(world, dt):
    a = world.area
    t = a.defn.get("_reinf")
    if t is not None:
        t -= dt
        if t <= 0:
            a.defn["_reinf"] = None
            for x in (232, 248):
                e = world.spawn(Enemy(x, 662, "brawler", facing=(0, -1), name="Hobb's man", group="reinf"))
                e.sprite = "brawler_b"
                e.become_alert(world, world.player.x, world.player.y, shout=False)
            world.sfx("door", 240, 660)
            world.toast("The street door bangs open. Your gunshot carried.", 3)
        else:
            a.defn["_reinf"] = t
    p = world.player
    st = world.state
    if p is not None and not st.check("w.hobb_room") and p.y < 230:
        st.set("w.hobb_room")
        h = world.by_tag("hobb")
        if h is not None and not h.dead and h.awareness != "alert":
            world.whisper("silas", "That's Hobb. Back to the window, eyes on the door. Men like him always watch the wrong way.")


def on_enemy_down(world, e):
    st = world.state
    if e.tag == "hobb":
        st.set("tenement.hobb_down")
    if all(x.dead for x in world.enemies()):
        st.set("tenement.cleared")
        world.whisper("silas", "Quiet now. Breathe, Calder. Your hands always shake after. Mine did too.")


def on_pickup(world, item):
    if item == "camera":
        world.start_dialogue("prints")
    elif item == "ledger":
        world.start_dialogue("ledger")


def on_interact(world, it):
    p = world.player
    if it["id"] == "window":
        world.sfx("climb", p.x, p.y)
        p.start_busy("climb", 0.5, lambda: world.request_transition("roof", "from_window"))
    elif it["id"] == "door_2b":
        world.start_dialogue("door_2b")
    elif it["id"] == "door_1a":
        world.start_dialogue("door_1a")
