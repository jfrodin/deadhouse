"""Registry of asset generators used by tools/build_assets.py."""
from __future__ import annotations

from typing import Callable

from .areas import write_area


def _row(out):
    from . import bake_row
    return write_area(out, "row", bake_row.bake())


def _tenement(out):
    from . import bake_tenement
    return write_area(out, "tenement", bake_tenement.bake())


def _alley(out):
    from . import bake_alley
    return write_area(out, "alley", bake_alley.bake_alley()) + write_area(out, "roof", bake_alley.bake_roof())


def _marquee(out):
    from . import bake_marquee
    return write_area(out, "marquee", bake_marquee.bake())


def _icons(out):
    from . import icons
    return icons.build(out)


def _portraits(out):
    from . import portraits
    return portraits.build(out)


def _chars(out):
    from . import chars
    return chars.build_all(out)


ART: dict[str, Callable[[str], list[str]]] = {
    "row": _row,
    "tenement": _tenement,
    "alley": _alley,
    "marquee": _marquee,
    "chars": _chars,
    "icons": _icons,
    "portraits": _portraits,
}
def _sfx(out):
    from .audio import sfx
    return sfx.build(out)


def _music(out):
    from .audio import music
    return music.build(out)


AUDIO: dict[str, Callable[[str], list[str]]] = {
    "sfx": _sfx,
    "music": _music,
}


def select(targets: list[str]):
    jobs = []
    for t in targets:
        if t == "all":
            jobs += list(ART.items()) + list(AUDIO.items())
        elif t == "art":
            jobs += list(ART.items())
        elif t == "audio":
            jobs += list(AUDIO.items())
        elif t in ART:
            jobs.append((t, ART[t]))
        elif t in AUDIO:
            jobs.append((t, AUDIO[t]))
        else:
            raise SystemExit(f"unknown target {t!r}; known: {sorted(ART) + sorted(AUDIO)}")
    seen, out = set(), []
    for name, fn in jobs:
        if name not in seen:
            seen.add(name)
            out.append((name, fn))
    return out
