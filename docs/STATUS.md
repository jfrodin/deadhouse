# Status — Prototype 1 ("One Block of Lantern Row")

Legend:
* **Tested (auto)**: covered by the pytest suite or the scripted end-to-end run.
* **Verified (visual)**: checked by rendering screenshots of the real game and inspecting them.
* **Unverified**: implemented, but needs a human to judge it: feel, sound, gamepad, real-monitor
  fullscreen.

## Implemented

| Feature | Evidence |
|---|---|
| Window, 60 Hz fixed-step loop, letterboxed scaling (integer where possible), F11 fullscreen | Tested (auto) for scaling; fullscreen **unverified** on a real monitor |
| GPU lighting (48 lights, cones, clip rects), wet reflections, bloom, fog, grain, tonemap | Verified (visual) |
| Rain with splashes and shelter, steam, chimney smoke, sparks, glass, splinters, blood that stays | Verified (visual) |
| Lantern Row: 10 facades, neon/bulb signs with flicker patterns, lamps, the El with periodic trains | Verified (visual) |
| No. 14 tenement (4 floors), alley, rooftops, Marquee interior | Verified (visual); routes tested (auto) |
| Character rig: 16 characters, 24 animation types, 3 views + mirroring | Verified (visual stills); motion **unverified** |
| Vivienne portrait, 4 expressions, in dialogue | Verified (visual) |
| Title screen with the live street behind it | Verified (visual) |
| Movement, sprint, collision (sub-stepped) | Tested (auto) |
| Melee: razor 3-hit combo + heavy, tire iron 2-hit + guard-breaking heavy, aim assist, hit-stop, shake, flash, knockback, bleed | Tested (auto) for damage and kills; feel **unverified** |
| Dodge with invulnerability frames, cancel from recovery | Tested (auto) |
| Revolver: draw delay, aim assist, rounds, noise, ricochet, shooting out lights | Tested (auto) |
| Bottles: arc throw that auto-targets lamps and bulbs, breaks lights, makes noise | Tested (auto) |
| Lantern: cone light, visibility penalty, flash that blinds | Tested (auto) |
| Takedowns from behind on unaware enemies | Tested (auto, including bot playthroughs) |
| Enemy AI: calm/suspicious/alert, vision cone scaled by light, LOS, hearing, investigating, noticing bodies, group alerts, attack tokens; brawler/knifeman (strikes matches in the dark)/gunman (aim telegraph, reload) | Tested (auto) |
| Gunshot reinforcements in the tenement | Tested (auto) |
| Death → desaturate → respawn at the area entrance | Tested (end-to-end) |
| Remnants: Silas (Climb, quieter sprint), Maud (Break) via prototype test kit; whispers; R for hints | Tested (auto) for gating; hint text verified |
| Dialogue language + runtime; stance tags; memories; conditions; hooks; portraits and expressions | Tested (auto): script validation, quest flows |
| Quest: Augie's camera → photograph (outcome depends on whether you looked at the prints and whether you lied) | Tested (auto) |
| Vivienne: tip depends on how Ines speaks to her; flirtation remembered; photograph reaction | Tested (auto) |
| Side characters: Sully, Rosa, Mrs. Kowal, Bruno, Haskell; 2 vignettes; pedestrians who scatter at gunfire | Verified (visual) / end-to-end |
| Inventory: weapons (equip), tools, items, evidence, Remnants, Leads (notebook) | Verified (visual) |
| Audio: positional SFX, crossfaded ambience beds per area, band music by distance (street) / radio (tenement), combat tension layer, the El train | Engine tested on the dummy driver; **how it sounds is unverified** (spectrograms and levels only) |
| All assets generated from code; deterministic art | Tested (auto, byte-identical manifest check) |
| Windows build (PyInstaller, 40 MB zip) | Frozen exe smoke-tested in screenshot mode |

## Not implemented in Prototype 1 (proposed / planned)
* Remnant **active abilities** and **Reads**, two-slot loadout, pairings, unfinished business,
  release/sell.
* Acquiring a Remnant through a playable memory (Maud's cellar fight). She is granted by a test kit.
* Outfits as armour and access, Scars, max-health growth, shops and money.
* The Velour interior, Lionel Gaunt, the Sumps, every other district, the Deadhouse hub, Nights and the
  passage of time.
* Intimate scenes, illustrated vignettes, nudity, and other adult content beyond what is listed in
  DESIGN.md.
* Save/load **UI** (the state serialises; there is no menu), options (volume, rebinding),
  accessibility settings.
* Portraits for anyone but Vivienne. Bosses. Cars.
