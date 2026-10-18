"""Deadhouse master palette.

Albedo colors are deliberately mid-valued and slightly desaturated: the GPU
lighting pass supplies most of the mood (deep blue ambient, sodium and neon
key lights). Emissive colors are what glows by itself.
"""
from .gfx import hexc

# --- outlines / darks
INK = hexc("14121a")
INK_WARM = hexc("1e1416")
SHADOW = hexc("0b0a10", 150)

# --- street materials
ASPHALT = hexc("3b3e46")
ASPHALT_DARK = hexc("2c2e35")
ASPHALT_PATCH = hexc("34363d")
RAIL = hexc("8d939c")
RAIL_DARK = hexc("4f545b")
CONCRETE = hexc("6d6b68")
CONCRETE_DARK = hexc("55534f")
CONCRETE_LIGHT = hexc("82807a")
CURB_TOP = hexc("8c8982")
CURB_FACE = hexc("47464a")
GUTTER = hexc("2a2b30")
MANHOLE = hexc("3e3b37")

# --- building materials
BRICK_RED = hexc("7c3e33")
BRICK_DARK = hexc("5b2e29")
BRICK_BROWN = hexc("6a4a3a")
MORTAR = hexc("4a3b37")
PLASTER = hexc("8e8577")
PLASTER_DARK = hexc("6e665b")
CREAM = hexc("b3a68e")
STONE = hexc("a0978a")
STONE_DARK = hexc("736b60")
DECO_GOLD = hexc("b08a4e")
WOOD_DARK = hexc("4a3226")
WOOD = hexc("6b4a35")
WOOD_PLANK = hexc("7a5a40")
IRON = hexc("3b3f46")
IRON_LIGHT = hexc("5c626b")
GLASS = hexc("1b2330")
GLASS_LIGHT = hexc("2b3648")
CURTAIN_RED = hexc("6a2430")
CURTAIN_GOLD = hexc("8a6a3a")
AWNING_GREEN = hexc("2f4a3c")
AWNING_RED = hexc("5e1f2c")
AWNING_STRIPE = hexc("a39a82")
VELVET = hexc("6b1626")
BRASS = hexc("a88a52")
POSTER_PAPER = hexc("9a8a6a")
TRASH = hexc("3a3a36")

# --- emissive
NEON_MAGENTA = hexc("ff3fae")
NEON_PINK = hexc("ff7ac8")
NEON_CYAN = hexc("3fe6ff")
NEON_RED = hexc("ff3b3b")
NEON_GREEN = hexc("6dff9a")
NEON_AMBER = hexc("ffb347")
BULB = hexc("ffd38a")
BULB_DIM = hexc("6a4a28")
SODIUM = hexc("ffb35a")
WINDOW_WARM = hexc("a8743c")
WINDOW_DIM = hexc("5a3c22")
WINDOW_COOL = hexc("4a6a88")
WINDOW_TV = hexc("6a8ab0")
PROJECTOR = hexc("cfd8ff")

# Light colors (floats, used by the runtime renderer)
L_SODIUM = (1.0, 0.62, 0.30)
L_BULB = (1.0, 0.78, 0.50)
L_MAGENTA = (1.0, 0.25, 0.68)
L_CYAN = (0.25, 0.85, 1.0)
L_RED = (1.0, 0.22, 0.22)
L_GREEN = (0.4, 1.0, 0.55)
L_WINDOW = (1.0, 0.72, 0.42)
L_MOON = (0.45, 0.55, 0.85)
L_FLUOR = (0.75, 0.9, 1.0)
