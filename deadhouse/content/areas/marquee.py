"""Inside the Marquee, closed since 1931. Mr. Haskell still runs the projector."""
from ...engine.renderer import Light
from ...sim import flicker
from ...sim.npc import NPC
from ...sim.world import Pickup

AREA = {
    "id": "marquee",
    "name": "The Marquee",
    "bake": "marquee",
    "post": {"ambient": (0.035, 0.035, 0.05), "fog": 0.35, "fog_color": (0.35, 0.36, 0.45), "bloom": 1.1,
             "exposure": 1.25, "reflect": 0.0, "saturation": 0.85},
    "rain": 0.0,
    "reflections": False,
    "floor": "concrete",
    "ground_y": 0,
    "spawns": {"from_row": (48, 252)},
    "spawn_facing": {"from_row": (1, 0)},
    "respawn": "from_row",
    "title_card": ["THE MARQUEE", "Closed for renovation, 1931"],
    "exits": [{"rect": (30, 238, 8, 30), "to": "row", "spawn": "from_marquee"}],
    "audio": {"ambience": ["interior_cinema"]},
}


def setup(world):
    st = world.state
    world.spawn(NPC(240, 124, "haskell", "Mr. Haskell", "haskell_start", facing=(0, -1), idle_anim="idle", tag="haskell",
                    barks=["Shh. This is the good part.", "Every night. Somebody has to."], bark_radius=90))
    if not st.check("marquee.rounds"):
        world.spawn(Pickup(300, 194, "rounds", 3, label=".38 rounds", flag="marquee.rounds"))
    if not st.check("marquee.entered"):
        st.set("marquee.entered")
        world.whisper("maud", "Smells like my father's church. Dust and somebody's last cigarette.")


def lights(world):
    """The projector beam and the light coming off the screen."""
    t = world.t
    lvl = flicker.level("projector", t, 3.3)
    return [
        Light(240, 268, 260, (0.8, 0.85, 1.0), 0.9 * lvl, 0.6, (0.0, -1.0), 0.985, 0.955, (0, 104, 480, 300)),
        Light(240, 132, 150, (0.75, 0.8, 0.95), 0.55 * lvl, 0.3, None, 0.9, 0.7, (0, 104, 480, 300)),
    ]


def draw_over(world, sc):
    """Film on the screen and the visible beam with dust motes."""
    import math
    import random
    import pygame
    t = world.t
    for p in world.area.props:
        if p.kind == "film":
            frames = p.data["frames"]
            k = int(t / 3.2) % len(frames)
            _, emi = sc.assets.sprite(frames[k])
            lvl = flicker.level("projector", t, 3.3)
            e = sc.levels.get(emi, lvl * 0.7)
            if e is not None:
                cx, cy = sc.cv.to_canvas(p.x, p.y)
                sc.cv.emi.blit(e, (cx, cy), special_flags=pygame.BLEND_RGB_ADD)
    # beam: faint additive wedge from the booth to the screen
    e = sc.cv.emi
    bx, by = sc.cv.to_canvas(240, 268)
    sx0, sy = sc.cv.to_canvas(110, 92)
    sx1, _ = sc.cv.to_canvas(370, 92)
    lvl = flicker.level("projector", t, 3.3)
    beam = pygame.Surface(e.get_size(), pygame.SRCALPHA)
    c = int(9 * lvl)
    pygame.draw.polygon(beam, (c, c, int(c * 1.3)), [(bx - 2, by), (bx + 2, by), (sx1, sy), (sx0, sy)])
    c2 = int(7 * lvl)
    pygame.draw.polygon(beam, (c2, c2, int(c2 * 1.3)), [(bx - 1, by), (bx + 1, by), (bx + 40, sy + 60), (bx - 40, sy + 60)])
    e.blit(beam, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    rnd = random.Random(int(t * 10))
    for i in range(26):
        f = rnd.random()
        x = bx + (rnd.uniform(sx0, sx1) - bx) * f + math.sin(t * 0.7 + i) * 2
        y = by + (sy - by) * f
        if 0 <= x < e.get_width() and 0 <= y < e.get_height():
            b = int(120 * lvl)
            e.fill((b, b, b), (int(x), int(y), 1, 1))
