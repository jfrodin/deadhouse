# Technical architecture

## Stack (provisional, as approved)
* **Python 3.12**, **pygame-ce 2.5.8** (window, input, CPU-side pixel compositing, audio mixer).
* **moderngl 5.13** (OpenGL 3.3 core): lighting, reflections, bloom, fog and grading on the GPU.
* **numpy**: runtime and build. **scipy**: build time only, for audio filters and convolution.
* **pytest** for tests and **PyInstaller** for the Windows build. **ffmpeg** at build time to encode
  `.ogg`; it falls back to `.wav` if missing.

**Engine verdict after Prototype 1.** The stack holds up. Lantern Row renders at about 300 fps uncapped
at 1920×1080 on an RTX 2070 SUPER (3 ms CPU draw + GPU, 0.3 ms simulation), after one optimisation pass.
Pixel-format matching gave the largest gain (18 ms → 3 ms). No reason to change engines was found. See
"Risks" below.

## Layers
```
engine/   platform: window + fixed-timestep loop (60 Hz), input (keyboard/pad, buffered presses),
          GPU renderer, audio mixer, bitmap font
sim/      pure game logic: World, Area, Player, Enemy AI, NPCs, perception, combat, dialogue runtime,
          GameState. No drawing and no sound: the World emits *events* (sfx, vfx, shake, bark, whisper,
          dialogue requests) which the presentation consumes.
render/   presentation: SceneRenderer (layers, props, rain), sprite sheets + attachments, VFX, UI
states/   TitleState, PlayState (drives the World, presents it, handles dialogue/inventory/death/transitions)
content/  data and per-area scripting (areas/*.py: AREA dict + setup/tick/on_interact/hooks),
          dialogue/*.dlg, items, combat tuning, leads/hints
assetgen/ build-time generators (art + audio). Not used at runtime except for the font glyph table.
```

## Frame
1. **Simulation step** (fixed 1/60 s). Input is turned into actions, then `World.update`: entities,
   noises → hearing, vignettes, exits, triggers, area `tick`. Hit-stop freezes the world for a few frames.
2. **CPU compositing** into three 482×272 canvases (480×270 plus a 1 px margin for sub-pixel camera
   scrolling):
   * **albedo:** baked background, facade props, y-sorted entities and props, VFX, foreground (the El),
     rain;
   * **emissive:** neon, windows, bulbs, the lantern, tracers, sparks, the film on the cinema screen;
   * **material:** R = wetness, G = distance to the reflection mirror line. Sprites clear wetness under
     themselves.
3. **GPU** (`engine/renderer.py`, `engine/shaders.py`):
   * **Light pass:** up to 48 lights (point or cone, optional clip rects to stop light bleeding between
     floors), specular hotspots on wet ground, and **wet-street reflections**. Reflections are found by
     mirroring each wet pixel across the facade base line and sampling the lit scene there.
   * Bright extract, then separable Gaussian blur at half and quarter resolution for bloom and fog glow.
   * **Final:** sub-pixel camera shift, bloom, drifting fbm fog lit by the blurred light, ACES tonemap,
     saturation, vignette, hurt vignette, flash, grain, fade.
   * Quads (portraits) and the 960×540 UI layer on top.
4. **Uploads are zero-copy:** canvases are pygame's native BGRA, and the textures swizzle in the sampler.

## Perception = rendering
`Area.light_at()` runs the same falloff formula as the shader, over the same static lights plus dynamic
ones (the lantern, matches, muzzle flashes). Enemies see Ines according to what the player sees on
screen.

## Content model
* **Areas:** the bake (`assetgen/bake_*.py`) draws layers and emits `meta.json` (colliders, lights,
  props, anchors). The content module (`content/areas/<id>.py`) adds gameplay: NPCs, enemies, pickups,
  interactables, exits, audio configuration and scripted hooks. Anchors are named points shared by both.
* **Dialogue:** `.dlg` files in a small language (see `sim/dialogue.py`) with conditions (`flag`, `!flag`,
  `has:item`, `remnant:x`, `stance:warm>=2`, `&`, `|`), effects (`set`, `give`, `take`, `remember`,
  `remnant`, `call hook`), stance-tagged choices and expressions for portraits. `Script.validate()` checks
  every jump target. A test enforces it.
* **Combat tuning:** `content/combat.py` (frame data for every swing, enemy stats, lantern and revolver).
* **Save data:** `GameState.to_json` / `from_json` is implemented and tested. No save/load UI in P1.

## Testing (see `tests/`)
* **Simulation:** movement, collision (including a regression test for a tunnelling bug found during
  development), combo damage, dodge invulnerability, being killed, takedowns, revolver, noise alerts,
  light-driven visibility, bottle-breaks-bulb, lantern flash, reinforcements, gating by Lessons,
  pickups/equip, quest flows through real dialogue, stance memory, save/load.
* **Routes:** flood-fill reachability of every door, window, ladder and pickup that matters.
* **Bots:** scripted players prove each tenement approach is *possible*: the outside window takedown on
  Hobb, the darkness route, and a head-on fight with dodging.
* **Assets:** every referenced sound, sprite and portrait exists, and **art generation is
  byte-identical** to the committed manifest.
* **End-to-end in the real renderer:** `tools/capture.py tools/flows.json` drives the actual game (GPU,
  hidden window) through every transition, death, respawn, the Maud grant, the boarded door and the
  inventory.

## Risks and notes
* **Fullscreen toggling (F11)** uses SDL's toggle with an OpenGL context. It raised no errors in testing,
  but it hasn't been tried on a real monitor in this environment. `--fullscreen` at launch is the safer
  path.
* **Gamepad support** is mapped to XInput button indices but untested (no pad available).
* Python performance is not a concern at this scale. The renderer would need batching if entity counts
  grew 10×.
