"""The notebook: what Ines knows and where it points. Shown in the inventory, derived from flags."""

LEADS = [
    # (show_if, done_if, title, text)
    ("quest.camera", "quest.camera_done", "Augie's camera",
     "Hobb took Augie Prell's camera. Hobb keeps the top floor of No. 14, the Garnet Arms, at the west end of the Row."),
    ("quest.camera_done", None, "The photograph",
     "Tomas Reyes leaving the Velour's side door at 2:10 a.m., and Lionel Gaunt, Vivienne Sabler's floor manager, holding it open."),
    ("tip.fire_escape", "tenement.hobb_down", "Nobody watches the fire escape",
     "Vivienne: Hobb's boys watch the stairs. The alley beside No. 14 has a fire escape up to his window."),
    ("tip.tenement", None, "Sully's count",
     "Two Dunne brothers drinking in the hall. Pike on the second landing, scared of the dark. Hobb never comes down."),
    ("clue.dravo", None, "F. Dravo",
     "Hobb's ledger: a cellar under Hu's Laundry, Pell Street, in the Sumps. 'Two donors Thursday.' (Beyond Prototype 1.)"),
    ("clue.donor_rumor", None, "Somebody took the last good hour out of him",
     "Rosa: a boy from the Row, Pim, went to the Sumps for easy money and came back empty. He's with Jo Fairweather now."),
    ("haskell.reel", None, "Saint Agathe's, 1931",
     "Mr. Haskell gave you the part of the film they cut. You worked at Saint Agathe's for six years and never saw the east wing open."),
    ("w.marquee", "broke.marquee_side", "A projector in a dead cinema",
     "Someone runs a film behind the Marquee's boarded staff door. The boards are soft with rain. It needs a shoulder — Maud's Lesson."),
]


def active(state):
    out = []
    for show, done, title, text in LEADS:
        if state.check(show):
            out.append((title, text, bool(done and state.check(done))))
    return out


# Remnant hints for the R key: the first matching line is spoken. (area, condition, remnant, text)
HINTS = [
    ("row", "!quest.camera", "silas", "The photographer by the pawnshop keeps looking at you. People who look like that want something."),
    ("row", "quest.camera & !tenement.entered", "silas", "No. 14 is the shabby one at the west end. Front door, or the alley beside it. I know which I'd pick."),
    ("row", "has:camera", "silas", "Augie's still by the pawnshop. Give him his camera before somebody else takes it off you."),
    ("row", "!remnant:maud", "silas", "That Marquee door wants a shoulder, not a burglar. Check the wagon if you're testing things, Calder."),
    ("row", "", "silas", "Breathe. Look at the light. Every lamp on this street is somebody's choice to be seen."),
    ("tenement", "!broke.bulb_f0", "silas", "That bulb in the hall is the only thing the Dunnes can see by. A bottle fixes that."),
    ("tenement", "!tenement.hobb_down", "silas", "Hobb watches his door, not his window. If you went up the fire escape, you'd come in behind him."),
    ("tenement", "", "silas", "If it goes bad, a gunshot will bring the street in. Dodge through a swing — they telegraph."),
    ("alley", "!has:tire_iron", "silas", "There's iron in this alley that isn't nailed down. By the dumpster."),
    ("alley", "", "silas", "Ladder's on Fourteen's wall. E to climb. My Lesson, your hands."),
    ("roof", "!has:lantern", "silas", "The pigeon man's loft. He kept a railway lantern in there for the night birds."),
    ("roof", "", "silas", "The fire escape goes down to the alley, or one flight to Hobb's window. Your call."),
    ("marquee", "", "maud", "Talk to the old man. He's been waiting twenty-three years for somebody to come through that wall."),
]


def hint(area_id, state):
    for a, cond, remnant, text in HINTS:
        if a == area_id and (not cond or state.check(cond)):
            r = remnant if remnant in state.remnants else (state.remnants[0] if state.remnants else None)
            return r, text
    return None, None
