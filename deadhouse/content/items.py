"""Item and Remnant definitions."""

ITEMS = {
    # weapons are defined in combat.WEAPONS; listed here for inventory text/icons
    "razor": dict(kind="weapon", name="Straight razor", icon="razor"),
    "tire_iron": dict(kind="weapon", name="Tire iron", icon="tire_iron"),
    "revolver": dict(kind="gun", name="Police revolver", icon="revolver",
                     desc="Okafor's? No. Someone's. Six chambers, never enough rounds. Every shot tells the block where you are."),
    "rounds": dict(kind="ammo", name=".38 rounds", icon="rounds", desc="Brass. Heavier than they look."),
    "bottle": dict(kind="throwable", name="Empty bottle", icon="bottle",
                   desc="Throw it at a light, a head, or anywhere you want people to look instead of at you."),
    "dressing": dict(kind="consumable", name="Field dressing", icon="dressing",
                     desc="Gauze, iodine, a steady hand. You were a nurse before you were anything else. (H to use)"),
    "matches": dict(kind="tool", name="Matches", icon="matches", desc="A book from the Velour. Six left."),
    "lantern": dict(kind="tool", name="Bull's-eye lantern", icon="lantern",
                    desc="A hooded railway lantern. Light the dark, blind a man for a breath — and let everyone see you. (F toggle, C flash)"),
    "camera": dict(kind="key", name="Augie's camera", icon="camera",
                   desc="A press camera with a cracked flash reflector. The film counter reads 9."),
    "photo": dict(kind="key", name="Photograph: the Velour, 2:10 AM", icon="photo",
                  desc="Tomas Reyes leaving the Velour by the side door. The man holding the door wears a floor manager's carnation."),
    "ledger": dict(kind="key", name="Page from Hobb's ledger", icon="ledger",
                   desc="F. DRAVO — cellar under Hu's Laundry, Pell St. — 2 donors Thurs. Paid in full."),
    "reel": dict(kind="key", name="Film can: SAINT AGATHE'S — 1931", icon="reel",
                 desc="Haskell said it was never supposed to be shown. He showed it every night anyway."),
    "testkit": dict(kind="debug", name="Prototype test kit", icon="debug", desc="Not part of the game. Grants Maud's Lesson for testing."),
}

REMNANTS = {
    "silas": dict(
        name="Silas Webb", epithet="the burglar",
        lesson="Climb", lesson_desc="Drainpipes, fire escapes, transoms. If it holds a cat, it holds you.",
        active="Light Fingers", active_desc="(Prototype: not yet implemented.)",
        passive="Soft Step", passive_desc="Running makes less noise.",
        read="Marks", read_desc="Notices what people are hiding in their pockets.",
        color=(150, 190, 255),
    ),
    "maud": dict(
        name="Maud Kessel", epithet="the fighter",
        lesson="Break", lesson_desc="Rotten doors, boarded windows, bad brick. Shoulder first.",
        active="Counter", active_desc="(Prototype: not yet implemented.)",
        passive="Iron Jaw", passive_desc="Harder to stagger.",
        read="Bluffs", read_desc="Knows when someone is lying about violence.",
        color=(255, 170, 120),
    ),
}
