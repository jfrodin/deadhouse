# Known issues and limitations (Prototype 1)

## Unverified by the developer (needs a human)
* **Combat feel.** Timings, weight and fairness have been tuned by numbers and bots, not by hands on a
  controller.
* **Audio.** Mixed and checked with level statistics and spectrograms only. Balance, timbre and whether
  the band sounds like a band all need ears.
* **Animation in motion.** Frames were inspected as contact sheets; the playback itself hasn't been
  watched.
* **Gamepad.** Mapped to XInput indices, but no controller was available to test with.
* **F11 fullscreen toggle.** Throws no errors, but hasn't been seen on a real monitor. Launching with
  `--fullscreen` is the safer option.

## Known limitations
* **Character sprites** are serviceable but generic. Faces are only 7 px wide, walk cycles are simple,
  and NPCs are distinguished mostly by hats and colours.
* **Portraits:** only Vivienne has one. The style (flat vector, hard light) reads well at dialogue size,
  but anatomy is stylised and long, and the fur wrap is crude. It is a proof of style, not final art.
* **NPCs block the sidewalk.** Talkers and the vignette couple are solid; you walk around them.
* **Pedestrians loop** along the sidewalks and never enter buildings.
* **The tenement stairwell** is a cutaway stack. It's readable, but less striking than the street.
* **Enemies can lose track of Ines too easily** around corners, and their pathing is steering only (no
  pathfinding). This is fine for these rooms, but won't scale.
* **Dialogue text skips and advances on the same key.** Mashing E can skip lines you meant to read.
* **The test kit is visible in the wagon dialogue.** That's intentional for evaluation; it will be removed.
* **Respawn resets enemies** in the area you died in. Items you picked up stay picked up.
* **Bracketed notes** in some dialogue mark where a thread continues beyond Prototype 1.

## Fixed during development (kept as regression tests)
* Fast movement could tunnel through thin walls (sub-stepped movement now).
* A newly created player started in a state the controller didn't handle, so Ines couldn't move.
* The posts at the alley mouths snagged Ines on the sidewalk.
* Pixel-format mismatch made every blit convert pixels (55 → 300 fps after the fix).
