"""Bot playthroughs of the tenement's intended approaches. These prove each route is *possible*,
not that it is fun — that part needs a human."""
import math

from conftest import Driver
from deadhouse.sim.entities import norm


def stalk(d, target_filter, seconds=25.0):
    """Very simple stealth bot: circle behind an unaware target, then press attack for the takedown."""
    w = d.world
    for _ in range(int(seconds * 60)):
        p = d.p
        if p.dead:
            return False
        targets = [e for e in w.enemies() if target_filter(e) and not e.dead]
        if not targets:
            return True
        cand = w.takedown_candidate(p)
        if cand is not None and target_filter(cand) and p.state == "free":
            d.step(1, attack=True)
            d.step(70)
            continue
        e = min(targets, key=lambda t: math.hypot(t.x - p.x, t.y - p.y))
        # aim for a point behind the enemy
        bx, by = e.x - e.fx * 12, e.y - e.fy * 12
        dx, dy = bx - p.x, by - p.y
        held = {}
        if abs(dx) > 2:
            held["right" if dx > 0 else "left"] = True
        if abs(dy) > 2:
            held["down" if dy > 0 else "up"] = True
        d.step(1, **held)
        if p.state == "free" and abs(dx) <= 2 and abs(dy) <= 2:
            p.face(e.x - p.x, e.y - p.y)
    return False


def test_outside_approach_take_hobb_from_behind():
    """Come in through the fire-escape window and take Hobb before he turns around."""
    d = Driver("tenement", "from_window")
    w = d.world
    hobb = w.by_tag("hobb")
    # creep along between the table and Hobb's back
    assert d.walk_to(250, 156)
    assert hobb.awareness != "alert", "Hobb noticed Ines on the way in"
    ok = stalk(d, lambda e: e is hobb, seconds=8)
    assert ok and hobb.dead, f"takedown failed (awareness={hobb.awareness}, hp={hobb.hp})"
    assert not d.p.dead


def test_darkness_approach_in_the_hall():
    """Break the hall bulb, let the Dunnes come to the glass, and take them in the dark."""
    d = Driver("tenement", "from_row")
    w = d.world
    bulb = w.area.prop("bulb_f0")
    # throw from the dark doorway, never stepping into the bulb's light
    d.p.x, d.p.y = 238, 655
    d.p.face(150 - 238, 598 - 655)
    d.tap("throw", settle=50)
    assert bulb.state.get("broken")
    d.step(90)
    ground = [e for e in w.enemies() if e.group == "ground"]
    assert all(e.awareness in ("suspicious", "calm") for e in ground), [e.awareness for e in ground]
    ok = stalk(d, lambda e: e.group == "ground", seconds=30)
    downs = sum(e.dead for e in ground)
    assert downs >= 1, "the bot could not take even one brother in the dark"
    assert not d.p.dead


def test_head_on_fight_is_winnable_with_dodging():
    """A crude brawling bot (attack, dodge when a windup is coming) beats the two brothers."""
    d = Driver("tenement", "from_row")
    w = d.world
    ground = [e for e in w.enemies() if e.group == "ground"]
    for e in ground:
        e.become_alert(w, d.p.x, d.p.y, shout=False)
    for _ in range(60 * 60):
        p = d.p
        if p.dead or all(e.dead for e in ground):
            break
        live = [e for e in ground if not e.dead]
        e = min(live, key=lambda t: math.hypot(t.x - p.x, t.y - p.y))
        dist = math.hypot(e.x - p.x, e.y - p.y)
        threat = any(x.attack is not None and x.state_t < x.attack["windup"] and math.hypot(x.x - p.x, x.y - p.y) < 30 for x in live)
        if threat and p.state == "free" and p.dodge_cd <= 0:
            nx, ny, _ = norm(p.x - e.x, p.y - e.y)
            held = {"dodge": True}
            held["right" if nx > 0 else "left"] = True
            d.step(1, **held)
            d.step(4)
            continue
        if dist > 16:
            held = {}
            if abs(e.x - p.x) > 3:
                held["right" if e.x > p.x else "left"] = True
            if abs(e.y - p.y) > 3:
                held["down" if e.y > p.y else "up"] = True
            d.step(1, **held)
        else:
            p.face(e.x - p.x, e.y - p.y)
            d.step(1, attack=True)
            d.step(3)
    assert all(e.dead for e in ground), f"brothers left standing: {[round(e.hp) for e in ground if not e.dead]}"
    assert not d.p.dead, "the bot died — combat may be overtuned against the player"
