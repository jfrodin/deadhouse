"""Combat tuning data. Times are seconds, distances pixels, damage in HP."""

# A weapon's light combo is a list of swings. Each swing:
#   anim, windup, active, recover, damage, reach, arc (deg), knock, stagger, noise
WEAPONS = {
    "razor": {
        "name": "Straight razor",
        "desc": "Fast and quiet. Opens wounds that keep bleeding. Useless against a man who can reach you first.",
        "icon": "razor",
        "combo": [
            dict(anim="attack1", windup=0.06, active=0.07, recover=0.13, damage=8, reach=17, arc=110, knock=40, stagger=0.18, noise=16),
            dict(anim="attack2", windup=0.06, active=0.07, recover=0.13, damage=8, reach=17, arc=110, knock=40, stagger=0.18, noise=16),
            dict(anim="attack3", windup=0.11, active=0.09, recover=0.28, damage=15, reach=23, arc=45, knock=90, stagger=0.4, noise=20),
        ],
        "heavy": dict(anim="heavy", windup=0.34, active=0.1, recover=0.32, damage=18, reach=19, arc=120, knock=110, stagger=0.6, noise=30),
        "bleed": 2.5,   # damage per second for 3 seconds after a hit
        "draw": "razor",
    },
    "tire_iron": {
        "name": "Tire iron",
        "desc": "Slow, heavy, honest. Breaks guards, bones and boarded windows.",
        "icon": "tire_iron",
        "combo": [
            dict(anim="attack1", windup=0.12, active=0.09, recover=0.22, damage=13, reach=21, arc=120, knock=90, stagger=0.42, noise=34),
            dict(anim="attack2", windup=0.12, active=0.09, recover=0.3, damage=15, reach=21, arc=120, knock=110, stagger=0.5, noise=34),
        ],
        "heavy": dict(anim="heavy", windup=0.5, active=0.12, recover=0.42, damage=32, reach=23, arc=140, knock=170, stagger=1.0, noise=50, guard_break=True),
        "bleed": 0.0,
        "draw": "tire_iron",
    },
}

REVOLVER = dict(damage=46, range=230, cone_deg=34, draw_time=0.16, cooldown=0.42, noise=330, knock=140, stagger=0.7)
BOTTLE = dict(speed=210, max_range=120, noise=120, damage=6, stagger=0.35, break_radius=14)
LANTERN = dict(radius=118, cone_cos_inner=0.93, cone_cos_outer=0.72, intensity=1.15, flash_range=78,
               flash_cos=0.82, blind_time=2.6, flash_cooldown=3.2, visibility_bonus=0.55)
DODGE = dict(time=0.3, iframes=0.22, speed=200, cooldown=0.12)
PLAYER = dict(hp=100, walk=64, sprint=104, accel=900, friction=900, heal_amount=40, heal_time=1.4)
TAKEDOWN = dict(range=19, behind_cos=-0.2, time=0.95, noise=18)

ENEMIES = {
    "brawler": dict(
        name="Bruiser", sprite="brawler", hp=58, walk=46, run=86, sight=170, hearing=1.0, react=0.35,
        attacks=[
            dict(anim="windup", windup=0.42, active=0.1, recover=0.42, damage=13, reach=17, arc=90, knock=90, stagger=0.3, weight=3),
            dict(anim="heavy", windup=0.78, active=0.12, recover=0.6, damage=24, reach=19, arc=110, knock=170, stagger=0.6, weight=1),
        ],
        poise=16, guard=False, preferred_range=13, keep_distance=False),
    "knifeman": dict(
        name="Knife", sprite="knifeman", hp=38, walk=54, run=104, sight=180, hearing=1.2, react=0.25,
        attacks=[
            dict(anim="attack3", windup=0.28, active=0.08, recover=0.2, damage=8, reach=20, arc=50, knock=40, stagger=0.15, weight=2, flurry=3, gap=0.13),
        ],
        poise=8, guard=False, preferred_range=18, keep_distance=False, lights_match=True),
    "gunman": dict(
        name="Hobb", sprite="hobb", hp=72, walk=40, run=70, sight=210, hearing=1.0, react=0.4,
        attacks=[
            dict(anim="attack1", windup=0.36, active=0.1, recover=0.5, damage=12, reach=16, arc=100, knock=110, stagger=0.4, weight=1),
        ],
        gun=dict(aim=0.85, damage=28, range=240, rounds=3, reload=2.2, cooldown=0.65, noise=330),
        poise=22, guard=False, preferred_range=110, keep_distance=True),
}
