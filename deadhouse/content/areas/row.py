"""Lantern Row — one block of nightclubs, hotels by the hour and a dead cinema."""
import random

import pygame

from ...sim.npc import NPC, Pedestrian, Vignette

AREA = {
    "id": "row",
    "name": "Lantern Row",
    "bake": "row",
    "post": {
        "ambient": (0.105, 0.11, 0.175),
        "fog": 0.22,
        "fog_color": (0.35, 0.3, 0.45),
        "bloom": 1.0,
        "exposure": 1.1,
        "reflect": 1.0,
        "saturation": 1.0,
    },
    "rain": 1.0,
    "reflections": True,
    "floor": "wet",
    "ground_y": 148,  # rain splashes only below this line
    "shelter": [(0, 252, 1440, 48)],  # under the El
    "spawns": {"start": (168, 214), "from_tenement": (105, 160), "from_alley_a": (250, 156),
               "from_alley_b": (1128, 156), "from_marquee": (1080, 160)},
    "spawn_facing": {"from_tenement": (0, 1), "from_marquee": (0, 1)},
    "respawn": "start",
    "title_card": ["LANTERN ROW", "Night Two  ·  1:40 a.m.", "Corvane"],
    "exits": [
        {"rect": (236, 88, 28, 10), "to": "alley", "spawn": "from_row_a"},
    ],
    "audio": {"ambience": ["rain_street", "city_far"], "music": "velour", "music_variant": "_out",
              "music_source": (565, 140), "music_radius": 560},
}

ENEMY_BARKS = {}


def setup(world):
    st = world.state
    a = world.area
    # --- the people you can talk to
    world.spawn(NPC(530, 164, "vivienne", "Vivienne Sabler", "viv_start", facing=(1, 0.3), idle_anim="smoke",
                    portrait="vivienne", tag="vivienne",
                    barks=["Rain's bad for business. Good for secrets.", "Bruno, darling, smile. It's free."]))
    world.entities[-1].overlay.append("cigarette")
    world.spawn(NPC(592, 163, "bruno", "Bruno", "bruno_start", facing=(0, 1), tag="bruno",
                    barks=["Members and guests.", "Keep moving.", "Coat check's inside. You're not."]))
    world.spawn(NPC(722, 167, "augie", "Augie Prell", "augie_start", facing=(-0.3, 1), idle_anim="idle", tag="augie",
                    barks=[("!augie.met", "Psst — Deadhouse. A word?"), "Can't sleep. Can't work. Can't win."]))
    world.spawn(NPC(1010, 166, "ped_cap_a", "Sully", "sully_start", facing=(0, 1), idle_anim="idle", tag="sully",
                    barks=["Light? Anybody got a light?", "Marquee's haunted, you know. Pictures still running."]))

    # --- pedestrians
    rnd = random.Random(14)
    kinds = ["ped_fedora_a", "ped_fedora_b", "ped_cloche_a", "ped_cloche_b", "ped_long_a", "ped_bare_a"]
    for i in range(7):
        y = rnd.choice((166, 169, 172))
        world.spawn(Pedestrian(rnd.uniform(40, 1400), y, kinds[i % len(kinds)], y, 20, 1420, umbrella=rnd.random() < 0.55))
    for i in range(4):
        y = rnd.choice((272, 278, 284))
        world.spawn(Pedestrian(rnd.uniform(40, 1400), y, kinds[(i + 3) % len(kinds)], y, 20, 1420, umbrella=rnd.random() < 0.3))

    # --- street vignettes
    w_ = world.spawn(NPC(346, 160, "ped_cloche_a", "Woman", None, facing=(1, 0), idle_anim="talk"))
    m_ = world.spawn(NPC(358, 160, "ped_bare_a", "Man", None, facing=(-1, 0), idle_anim="idle"))
    w_.solid = m_.solid = True

    def couple_after(world_):
        w_.removed = True  # she walks out of his life (and out of frame)
        m_.home_facing = (0, -1)

    world.vignettes.append(Vignette("hotel_couple", pygame.Rect(300, 150, 110, 40), [
        ("w", "You said you'd tell her tonight.", 2.6),
        ("m", "I said I'd try.", 2.2),
        ("w", "You always try. You try like a drowning man tries.", 3.2),
        ("m", "Keep your voice down—", 2.0),
        ("w", "Why? Who's listening? The rain?", 2.8),
        ("w", "Go home, Arthur. She's waiting up. She always waits up.", 3.2),
    ], {"w": w_, "m": m_}, after=couple_after, flag="saw.hotel_couple"))

    d1 = world.spawn(NPC(468, 162, "ped_long_a", "Dancer", None, facing=(1, 0.2), idle_anim="smoke"))
    d2 = world.spawn(NPC(480, 163, "ped_cloche_b", "Dancer", None, facing=(-1, 0.2), idle_anim="idle"))
    d1.overlay.append("cigarette")
    world.vignettes.append(Vignette("dancers", pygame.Rect(440, 150, 80, 40), [
        ("a", "He tipped me in streetcar tokens.", 2.4),
        ("b", "At least they take you somewhere.", 2.4),
        ("a", "Not on my feet they don't.", 2.2),
        ("b", "Break's over. Smile like you mean it.", 2.6),
        ("a", "I never mean it. That's why they pay.", 2.8),
    ], {"a": d1, "b": d2}, flag="saw.dancers"))

    # --- interactables
    t = a.anchors
    world.interactables += [
        {"id": "tenement_door", "x": t["tenement_door"][0], "y": t["tenement_door"][1] - 4, "verb": "Enter",
         "label": "No. 14, the Garnet Arms", "radius": 16},
        {"id": "hotel_door", "x": t["hotel_door"][0], "y": t["hotel_door"][1], "verb": "Knock", "label": "Hotel Calla"},
        {"id": "pawn_door", "x": t["pawn_door"][0], "y": t["pawn_door"][1], "verb": "Try", "label": "Prell & Son Loans"},
        {"id": "diner_door", "x": t["diner_door"][0], "y": t["diner_door"][1], "verb": "Try", "label": "Orsolya's"},
        {"id": "velour_door", "x": t["velour_door"][0], "y": t["velour_door"][1], "verb": "Enter", "label": "The Velour"},
        {"id": "marquee_side", "x": t["marquee_side_door"][0], "y": t["marquee_side_door"][1], "verb": "Examine",
         "label": "Boarded door", "radius": 18},
        {"id": "wagon", "x": t["wagon_side"][0], "y": t["wagon_side"][1], "verb": "Wagon", "label": "", "radius": 24},
        {"id": "phone", "x": 688, "y": 172, "verb": "Use", "label": "Telephone"},
    ]
    door = a.prop("marquee_side")
    if st.check("broke.marquee_side"):
        door.state["broken"] = True
        for it in world.interactables:
            if it["id"] == "marquee_side":
                it["verb"], it["label"] = "Enter", "The Marquee"
    # breakable lamp heads (bottle targets) on the Row
    for p in a.props:
        if p.kind == "lamp":
            p.state["breakable"] = True
            p.state["target"] = (p.x + 5, p.y + 6)

    if not st.check("row.intro"):
        st.set("row.intro")
        world.whisper("silas", "Rain's good for business, Calder. Everyone's looking at their feet.")


def on_interact(world, it):
    st = world.state
    p = world.player
    i = it["id"]
    if i == "tenement_door":
        world.request_transition("tenement", "from_row")
    elif i == "hotel_door":
        world.start_dialogue("hotel_door")
    elif i == "pawn_door":
        world.toast("BACK IN 5 MIN, says the sign. The dust says otherwise.", 3)
    elif i == "diner_door":
        world.toast("CLOSED FOR A FUNERAL — BACK AT FOUR. The coffee smell says someone's still in there.", 3.5)
    elif i == "velour_door":
        world.start_dialogue("bruno_start", world.by_tag("bruno"))
    elif i == "phone":
        world.start_dialogue("phone")
    elif i == "wagon":
        world.start_dialogue("wagon")
    elif i == "marquee_side":
        prop = world.area.prop("marquee_side")
        if prop.state.get("broken"):
            world.request_transition("marquee", "from_row")
        elif "maud" in st.remnants:
            def smash():
                prop.state["broken"] = True
                st.set("broke.marquee_side")
                world.sfx("wood_break", it["x"], it["y"])
                world.vfx("splinters", it["x"], it["y"] - 10)
                world.shake(4)
                world.noise(it["x"], it["y"], 110, "fight", team="player")
                it["verb"], it["label"] = "Enter", "The Marquee"
                world.whisper("maud", "There. Doors are just walls that gave up.")
            p.face(0, -1)
            world.sfx("wood_strain", it["x"], it["y"], 0.7)
            p.start_busy("break", 0.45, smash)
        else:
            world.start_dialogue("marquee_door")


def grant_maud(world, *args):
    st = world.state
    if "maud" not in st.remnants:
        st.remnants.append("maud")
        st.set("debug.maud")
        world.toast("Prototype: Maud Kessel's Lesson granted — Break.", 3.5)
        world.whisper("maud", "Who the hell are you? ...Never mind. Point me at something.")


def tick(world, dt):
    train_tick(world, dt)
    p = world.player
    st = world.state
    if p is None:
        return
    # contextual remnant lines
    if not st.check("w.tenement") and abs(p.x - 105) < 30 and p.y < 175:
        st.set("w.tenement")
        world.whisper("silas", "Front doors are for people who want to be seen. There's always a fire escape.")
    if not st.check("w.marquee") and abs(p.x - 1080) < 40 and p.y < 175:
        st.set("w.marquee")
        world.whisper("silas", "Someone's running a picture in a dead house. Not my kind of door, Calder. That one wants a shoulder.")


# ---------------------------------------------------------------- the El
TRAIN_SPEED = 118.0
TRAIN_LEN = 3 * 98


def _train_state(world):
    s = world.area.defn.setdefault("_train", {"t": random.uniform(8, 16), "x": None})
    return s


def train_tick(world, dt):
    s = _train_state(world)
    if s["x"] is None:
        s["t"] -= dt
        if s["t"] <= 0:
            p = world.player
            s["x"] = (p.x if p else 700) - 240 - TRAIN_LEN - 60
            s["end"] = s["x"] + TRAIN_LEN + 480 + 200 + TRAIN_LEN
            world.sfx("el_train", None, None, 1.0)
    else:
        s["x"] += TRAIN_SPEED * dt
        if s["x"] > s["end"]:
            s["x"] = None
            s["t"] = random.uniform(45, 80)


def lights(world):
    """Moving light from the train windows onto the street."""
    from ...engine.renderer import Light
    s = _train_state(world)
    out = []
    if s["x"] is not None:
        for k in range(3):
            cx = s["x"] + k * 98 + 49
            out.append(Light(cx, 238, 70, (1.0, 0.85, 0.6), 0.55))
    return out


def draw_over(world, sc):
    s = _train_state(world)
    if s["x"] is None:
        return
    alb, emi = sc.assets.sprite("row/train_car")
    for k in range(3):
        x = s["x"] + k * 98
        lvl = 0.85 + 0.15 * ((int(world.t * 20) + k) % 3 == 0)
        sc.blit_sprite(alb, emi, x, 233 - alb.get_height(), lvl, clear_wet=True)
        # sparks at the shoe gear now and then
        if random.random() < 0.15:
            cx, cy = sc.cv.to_canvas(x + random.uniform(10, 88), 232)
            if 0 <= cx < sc.cv.alb.get_width() and 0 <= cy < sc.cv.alb.get_height():
                sc.cv.emi.fill((255, 220, 150), (cx, cy, 1, 1))


HOOKS = {"grant_maud": grant_maud}
