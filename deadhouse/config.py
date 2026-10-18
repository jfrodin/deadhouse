"""Global constants. Everything else should derive from these."""
import os
import sys

# Internal world resolution (pixel art canvas). Scales exactly 4x to 1080p, 8x to 4K.
VIEW_W = 480
VIEW_H = 270
# One pixel of margin on every side lets the GPU pass shift the image by a
# sub-pixel camera offset, which keeps scrolling smooth without blurring the art.
MARGIN = 1
CANVAS_W = VIEW_W + 2 * MARGIN
CANVAS_H = VIEW_H + 2 * MARGIN

# UI is drawn on its own layer at 2x world resolution for crisper text.
UI_W = VIEW_W * 2
UI_H = VIEW_H * 2

FPS = 60
DT = 1.0 / FPS
MAX_LIGHTS = 48

DEFAULT_WINDOW_SCALE = 3  # 1440x810 windowed; F11 toggles fullscreen


def resource_root() -> str:
    """Project root, also when frozen by PyInstaller."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


ROOT = resource_root()
ASSET_DIR = os.path.join(ROOT, "assets", "generated")
CONTENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "content")
