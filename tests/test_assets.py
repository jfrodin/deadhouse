"""Asset tests: everything the code references exists, and generation is deterministic."""
import hashlib
import json
import os
import re
import tempfile

import numpy as np
import pygame
import pytest

from conftest import AREAS, Driver
from deadhouse import config as C

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "deadhouse")


def all_source():
    for dp, _, fns in os.walk(SRC):
        for fn in fns:
            if fn.endswith(".py"):
                with open(os.path.join(dp, fn), encoding="utf-8") as f:
                    yield fn, f.read()


def test_every_referenced_sound_exists():
    names = set()
    for fn, text in all_source():
        names |= set(re.findall(r'\.sfx\("([a-z_0-9]+)"', text))
        names |= set(re.findall(r'self\.sfx\("([a-z_0-9]+)"', text))
        names |= set(re.findall(r'pv\.sfx\("([a-z_0-9]+)"', text))
    names |= {"step_wet", "step_wood", "step_concrete"}
    sfx_dir = os.path.join(C.ASSET_DIR, "audio", "sfx")
    have = {os.path.splitext(f)[0] for f in os.listdir(sfx_dir)}
    missing = [n for n in sorted(names) if n not in have and f"{n}_1" not in have]
    assert not missing, f"missing sounds: {missing}"


def test_area_audio_beds_exist():
    for a in AREAS:
        d = Driver(a)
        cfg = d.world.area.defn.get("audio", {})
        for amb in cfg.get("ambience", []):
            assert any(os.path.exists(os.path.join(C.ASSET_DIR, "audio", "amb", amb + ext)) for ext in (".ogg", ".wav")), amb
        if cfg.get("music"):
            name = cfg["music"] + cfg.get("music_variant", "_out")
            assert any(os.path.exists(os.path.join(C.ASSET_DIR, "audio", "music", name + ext)) for ext in (".ogg", ".wav")), name


def test_audio_engine_runs_on_dummy_driver():
    pygame.mixer.quit()
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.mixer.init(44100, -16, 2, 512)
    from deadhouse.engine.audio import AudioEngine
    eng = AudioEngine(enabled=True)
    assert eng.enabled
    d = Driver("row")
    eng.set_area(d.world.area.defn["audio"])
    for _ in range(30):
        eng.update(1 / 60, d.world, (100, 0))
    eng.play("gunshot", 1.0, 120, 200, (0, 0))
    eng.play("step_wet", 0.5)
    assert eng.loops, "ambience loops should be playing"


def test_every_sprite_and_portrait_reference_exists():
    from deadhouse.assetgen.char_specs import CHARACTERS
    for name in CHARACTERS:
        assert os.path.exists(os.path.join(C.ASSET_DIR, "chars", name + ".png")), name
    for ex in ("neutral", "amused", "cold", "warm"):
        assert os.path.exists(os.path.join(C.ASSET_DIR, "portraits", f"vivienne_{ex}.png"))
    used = set()
    for fn, text in all_source():
        used |= set(re.findall(r'(?:Enemy|NPC|Pedestrian)\([^)]*?"((?:ped_|brawler|knifeman|hobb|ines|vivienne|augie|bruno|haskell)[a-z_]*)"', text))
    for u in used:
        assert u in CHARACTERS, u


def _sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def test_art_generation_is_deterministic():
    """Re-run a few generators into a temp dir and compare with the committed manifest."""
    from deadhouse.assetgen import registry
    man_path = os.path.join(C.ASSET_DIR, "manifest.json")
    with open(man_path, encoding="utf-8") as f:
        manifest = json.load(f)
    with tempfile.TemporaryDirectory() as tmp:
        files = registry.ART["row"](tmp) + registry.ART["icons"](tmp) + registry.ART["tenement"](tmp)
        assert files
        for p in files:
            rel = os.path.relpath(p, tmp).replace(os.sep, "/")
            assert rel in manifest, rel
            assert _sha(p) == manifest[rel], f"{rel} differs from the committed build"


def test_synthesis_is_deterministic():
    from deadhouse.assetgen.audio import sfx
    a = sfx.punch(np.random.default_rng(5))
    b = sfx.punch(np.random.default_rng(5))
    assert np.array_equal(a, b)
