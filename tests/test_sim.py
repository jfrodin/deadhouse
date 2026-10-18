"""Game-logic tests: movement, combat, stealth, light, items, gating, quest flow, saves."""
import math

import pygame
import pytest

from conftest import AREAS, Driver
from deadhouse.content.combat import ENEMIES
from deadhouse.sim import perception, physics
from deadhouse.sim.dialogue import Menu, Runner, Say
from deadhouse.sim.enemy import Enemy
from deadhouse.sim.state import GameState


# ----------------------------------------------------------------------------- basics
def test_every_area_loads_and_runs():
    for a in AREAS:
        d = Driver(a)
        assert d.p is not None
        d.step(240)  # four seconds of simulation with no input
        assert not d.p.dead or a == "tenement"


def test_spawns_are_not_inside_walls():
    for a in AREAS:
        d = Driver(a)
        for name, (x, y) in d.world.area.spawns.items():
            if name.endswith(("_mouth", "_exit", "_door", "door_in")) or name in d.world.area.anchors:
                continue
            assert not physics.blocked(x, y, d.world.area.colliders), f"{a}:{name} spawn inside a collider"


def test_walls_stop_movement():
    r = [pygame.Rect(100, 0, 10, 200)]
    x, y, hit = physics.move(90.0, 50.0, 30.0, 0.0, r)
    assert hit and x < 100 - physics.FOOT_W / 2 + 0.01


def test_player_walks_and_sprints():
    d = Driver("row")
    x0 = d.p.x
    d.step(60, right=True)
    walked = d.p.x - x0
    x1 = d.p.x
    d.step(60, right=True, sprint=True)
    sprinted = d.p.x - x1
    assert walked > 40 and sprinted > walked * 1.3


# ----------------------------------------------------------------------------- combat
def _lone_enemy(d, etype="brawler", dx=14, dy=0, alert=True, facing=(-1, 0)):
    for e in d.world.enemies():
        e.removed = True
    d.world.entities = [e for e in d.world.entities if not e.removed]
    e = d.world.spawn(Enemy(d.p.x + dx, d.p.y + dy, etype, facing=facing))
    if alert:
        e.become_alert(d.world, d.p.x, d.p.y, shout=False)
    return e


def test_razor_combo_damages_and_kills_a_brawler():
    d = Driver("row")
    e = _lone_enemy(d, alert=False, facing=(1, 0))  # facing away: first hit lands as a surprise
    d.p.face(1, 0)
    hp0 = e.hp
    for _ in range(40):
        d.tap("attack", settle=10)
        if e.dead:
            break
    assert e.hp < hp0
    assert e.dead, f"brawler survived with {e.hp:.0f} hp"


def test_dodge_gives_invulnerability():
    d = Driver("row")
    e = _lone_enemy(d)
    d.step(1, dodge=True, left=True)
    assert d.p.state == "dodge" and d.p.iframes > 0
    from deadhouse.sim.combat import Hit
    hp = d.p.hp
    assert not d.p.on_hit(d.world, Hit(20, 0, 0, 0.2))
    assert d.p.hp == hp


def test_enemies_hurt_ines_and_she_can_go_down():
    d = Driver("row")
    _lone_enemy(d, dx=12)
    for _ in range(60 * 30):
        d.step(1)
        if d.p.dead:
            break
    assert d.p.dead, "an unanswered brawler should eventually put Ines down"


def test_takedown_from_behind_in_the_dark():
    d = Driver("row")
    e = _lone_enemy(d, dx=12, alert=False, facing=(1, 0))  # looking away from Ines
    d.p.face(1, 0)
    assert d.world.takedown_candidate(d.p) is e
    d.tap("attack", settle=70)
    assert e.dead


def test_revolver_shot_hits_and_uses_a_round():
    d = Driver("row")
    e = _lone_enemy(d, dx=80, alert=False, facing=(1, 0))
    d.p.face(1, 0)
    r0 = d.state.count("rounds")
    hp0 = e.hp
    d.tap("shoot", settle=30)
    assert d.state.count("rounds") == r0 - 1
    assert e.hp < hp0


def test_gunshot_is_loud_and_alerts():
    d = Driver("row")
    e = _lone_enemy(d, dx=-150, alert=False, facing=(-1, 0))
    d.p.face(1, 0)
    d.tap("shoot", settle=12)
    assert e.awareness == "alert"


# ----------------------------------------------------------------------------- light and stealth
def test_visibility_depends_on_light():
    d = Driver("tenement")
    w = d.world
    p = d.p
    p.x, p.y = 150, 610  # under the hall bulb
    lit = perception.visibility(w, p)
    bulb = w.area.prop("bulb_f0")
    w.break_light(bulb)
    dark = perception.visibility(w, p)
    assert lit > dark * 2, (lit, dark)
    p.lantern_on = True
    assert perception.visibility(w, p) > dark + 0.4


def test_bottle_breaks_the_bulb_it_is_thrown_at():
    d = Driver("tenement", "from_row")
    w = d.world
    bulb = w.area.prop("bulb_f0")
    d.p.x, d.p.y = 160, 652
    d.p.face(-0.1, -1)
    n = d.state.count("bottle")
    d.tap("throw", settle=60)
    assert d.state.count("bottle") == n - 1
    assert bulb.state.get("broken") and not bulb.light.enabled


def test_breaking_a_bulb_draws_the_brawlers_to_investigate():
    d = Driver("tenement", "from_row")
    w = d.world
    bulb = w.area.prop("bulb_f0")
    w.noise(150, 600, 120, "glass", team="player")
    w.break_light(bulb)
    d.step(5)
    states = [e.awareness for e in w.enemies() if e.group == "ground"]
    assert states and all(s in ("suspicious", "alert") for s in states)


def test_lantern_flash_blinds_an_enemy_facing_ines():
    d = Driver("row")
    d.state.give("lantern")
    e = _lone_enemy(d, dx=40, alert=True, facing=(-1, 0))
    d.p.face(1, 0)
    d.tap("lantern", settle=1)
    assert d.p.lantern_on
    d.tap("flash", settle=1)
    assert e.blind_t > 0


def test_gunshot_in_the_tenement_brings_reinforcements():
    d = Driver("tenement", "from_row")
    w = d.world
    n0 = len(w.enemies())
    w.noise(240, 650, 330, "gunshot", loud=True, team="player")
    d.step(60 * 5)
    assert len(w.enemies()) == n0 + 2


# ----------------------------------------------------------------------------- gating and items
def test_lessons_gate_traversal():
    st = GameState()
    assert not st.check("remnant:silas")
    st.remnants.append("silas")
    assert st.check("remnant:silas") and not st.check("remnant:maud")


def test_marquee_door_needs_maud_and_breaks_with_her():
    d = Driver("row")
    w = d.world
    door = w.area.prop("marquee_side")
    it = next(i for i in w.interactables if i["id"] == "marquee_side")
    d.p.x, d.p.y = it["x"], it["y"] + 4
    d.p.face(0, -1)
    d.tap("interact", settle=10)
    assert not door.state.get("broken")
    d.world.events.clear()
    d.state.remnants.append("maud")
    d.tap("interact", settle=60)
    assert door.state.get("broken")
    d.tap("interact", settle=5)
    assert w.transition and w.transition[0] == "marquee"


def test_pickups_and_equipping_the_tire_iron():
    d = Driver("alley")
    w = d.world
    ti = next(e for e in w.entities if getattr(e, "item", None) == "tire_iron")
    d.p.x, d.p.y = ti.x - 8, ti.y
    d.p.face(1, 0)
    d.tap("interact", settle=20)
    assert d.state.has("tire_iron")
    d.state.equipped = "tire_iron"
    assert d.p.weapon["name"] == "Tire iron"


# ----------------------------------------------------------------------------- dialogue + quest
def run_dialogue(state, script, node, picks=()):
    r = Runner(script, state, {"camera_returned": lambda *a: None, "grant_maud": lambda *a: state.remnants.append("maud")})
    r.start(node)
    picks = list(picks)
    seen = []
    guard = 0
    while not r.ended and guard < 200:
        guard += 1
        if isinstance(r.current, Menu):
            choice = picks.pop(0) if picks else 0
            seen.append(r.visible_choices[choice].text)
            r.advance(choice)
        else:
            seen.append(r.current.text)
            r.advance()
    return seen


def test_dialogue_scripts_are_valid(driver):
    d = driver("row")
    errs = d.script.validate()
    assert errs == [], errs
    assert len(d.script.nodes) > 60


def test_camera_quest_flow():
    d = Driver("row")
    st, sc = d.state, d.script
    run_dialogue(st, sc, "augie_start", [1])
    assert st.check("quest.camera") and st.check("augie.met")
    st.give("camera")
    st.set("looked_at_prints")
    lines = run_dialogue(st, sc, "augie_start", [1])  # lie about the prints
    assert st.has("photo") and not st.has("camera")
    assert st.check("augie.ines_lied")
    assert any("Lionel Gaunt" in l for l in lines)


def test_vivienne_remembers_how_ines_spoke():
    d = Driver("row")
    st, sc = d.state, d.script
    run_dialogue(st, sc, "viv_start", [3, 0, 0])  # warm, ask about Hobb, maybe I will
    assert st.check("tip.fire_escape") and st.check("viv.interested")
    assert st.stance["warm"] >= 2
    st2 = GameState()
    run_dialogue(st2, sc, "viv_start", [2, 1, 2])  # cold all the way (the Augie option is hidden: never met him)
    assert not st2.check("tip.fire_escape")


def test_save_load_roundtrip():
    st = Driver("row").state
    st.set("quest.camera")
    st.remember("augie", "met")
    st.give("rounds", 3)
    st2 = GameState.from_json(st.to_json())
    assert st2.flags == st.flags and st2.inventory == st.inventory and st2.memory == st.memory


# ----------------------------------------------------------------------------- reachability
def reachable(area, start, goals, step=3):
    """Flood-fill the walkable feet positions of an area."""
    cols = area.colliders
    sx, sy = int(start[0] // step), int(start[1] // step)
    seen = {(sx, sy)}
    stack = [(sx, sy)]
    found = set()
    while stack:
        cx, cy = stack.pop()
        x, y = cx * step, cy * step
        for i, g in enumerate(goals):
            if math.hypot(x - g[0], y - g[1]) < 12:
                found.add(i)
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if (nx, ny) in seen:
                continue
            px, py = nx * step, ny * step
            if px < 0 or py < 0 or px > area.w or py > area.h:
                continue
            seen.add((nx, ny))
            if not physics.blocked(px, py, cols, w=8, h=4):
                stack.append((nx, ny))
    return found


def test_tenement_routes_are_walkable():
    d = Driver("tenement", "from_row")
    a = d.world.area
    goals = [(296, 158), (60, 150), (305, 440)]  # Hobb's table, the window, door 2B
    found = reachable(a, a.spawns["from_row"], goals)
    assert found == {0, 1, 2}, f"unreachable goals: {set(range(len(goals))) - found}"


def test_row_reaches_doors_and_alley():
    d = Driver("row")
    a = d.world.area
    goals = [a.anchors["tenement_door"], (250, 96), a.anchors["marquee_side_door"], a.anchors["velour_door"]]
    found = reachable(a, a.spawns["start"], goals)
    assert found == {0, 1, 2, 3}, f"unreachable: {set(range(len(goals))) - found}"


def test_alley_ladder_reachable():
    d = Driver("alley")
    a = d.world.area
    found = reachable(a, a.spawns["from_row_a"], [a.anchors["ladder"], (86, 376)])
    assert found == {0, 1}


def test_downed_enemies_stay_down_after_leaving_and_returning():
    d = Driver("tenement", "from_row")
    w = d.world
    danny = next(e for e in w.enemies() if e.display_name == "Danny Dunne")
    danny._go_down(w, None)
    w.load_area("row", "from_tenement")
    w.load_area("tenement", "from_row")
    names = [e.display_name for e in w.enemies()]
    assert "Danny Dunne" not in names and "Mick Dunne" in names
