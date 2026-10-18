# Prototype 1 report — an honest assessment

**Build:** `dist/Deadhouse-Prototype1-win64.zip` (40 MB) · **Screenshots:** `deliverables/screenshots/` ·
**Audio:** `deliverables/audio/` · **Tests:** `deliverables/test_results.txt` (34 automated tests pass;
the scripted end-to-end run through the real renderer passes)

## What was built
* One block of Lantern Row on Night Two, plus No. 14 (four floors), the alley, the roofs and the Marquee.
* A light-driven stealth and combat core with three enemy types and four ways into Hobb's building.
* Seven talkable characters, two street vignettes, pedestrians, and a train on the El.
* A branching dialogue system that remembers stance and specific acts.
* One portrait with four expressions.
* An original jazz piece rendered three ways (club, wall, radio), seven ambience beds, a combat tension
  layer and about 40 synthesised sound effects.
* A reproducible build of every asset from code.

About 12,000 lines of Python, including the generators and tests.

## What works
1. **The city at night.** I believe this is the strongest result. GPU lighting, wet reflections of neon,
   rain, fog, flickering and dying signs, dancers in windows, steam and the train crossing overhead give
   Lantern Row a coherent, recognisable look that doesn't read as programmer art. District colour,
   with Lantern Row's magenta and cyan, is already distinct.
2. **Light as gameplay.** Enemies see by the same light the GPU draws. Breaking a bulb really changes a
   room, and the lantern is a genuine trade-off. Bots confirm that the darkness route, the outside
   (window) route and a head-on fight are all achievable.
3. **Reactive conversation.** Stance tags and memories change what people say and give, without meters:
   Augie notices if you lied, and Vivienne gives the fire-escape tip only if you earned it. The writing
   has the tone I proposed: subtext, humour, warmth beside rot.
4. **Engineering.** The stack is fast (about 300 fps uncapped on the Row), testable and reproducible. The
   art build is byte-identical between runs. Bugs found during development are now regression tests.
5. **The Marquee.** A small optional discovery that I think shows the kind of curiosity reward the game
   should be full of.

## What does not work yet (or that I can't judge)
1. **Character sprites are the weakest visual element.** They're readable and consistent, but generic.
   Faces are only 7 px wide, NPCs differ mostly by hats and colour, and motion is simple. They don't yet
   match the quality of the environments. **My recommendation for P1.5:** move to taller sprites (around
   48 px), hand-key a few poses per animation instead of purely procedural cycles, and give each named
   character a unique silhouette.
2. **The portrait is a proof of style, not finished art.** The ink-and-light approach reads well at
   dialogue size and expressions are distinguishable. But anatomy is stylised and elongated, the fur is
   crude, and it isn't yet "seductive" at the level the brief deserves. I need your reaction to the
   direction before investing in more portraits.
3. **Combat feel is unverified.** Hit-stop, shake, flash, arcs, telegraphs and knockback are all there and
   the numbers are tuned, but I can't feel input latency or weight. This is the most important thing for
   you to judge.
4. **Audio is unheard.** I checked it with levels and spectrograms: the walking bass, piano voicings and
   vibraphone melody are present, and nothing clips. Whether it *sounds* like a band in a club needs your
   ears. Start with `deliverables/audio/street_mix.ogg` and `music_velour_in.ogg`.
5. **Remnants are only Lessons.** Climb and Break gate traversal, but there are no active abilities or
   Reads yet, so the system's real promise (tactical combinations) isn't demonstrated. Maud comes from a
   labelled test kit rather than her intended memory-fight.
6. **The living city is thin.** Pedestrians loop, nobody goes indoors, barks repeat. It feels alive for a
   few minutes, not an hour.
7. **Adult themes are only present in conversation and set dressing.** By design, P1 contains no intimate
   scenes. The tone is established, but the adult side of the game isn't demonstrated beyond flirtation, an
   affair vignette and a blackmail photograph.
8. **Untested:** gamepad, and the F11 toggle on a real monitor.

## Engine decision
**Keep pygame-ce + moderngl.** The prototype showed no performance, rendering or maintainability problems
that would justify switching. The one serious slowdown was a pixel-format mismatch, fixed in an hour. The
code-only workflow suits how I work: every asset and layout is text I can generate, review and test. The
cost is no visual editor, which matters less to me than to a human team. I'd reconsider if we needed large
numbers of animated characters on screen, or complex physics.

## What I would like from you
1. Play `Deadhouse.exe` for 30–45 minutes. Take No. 14 at least two different ways.
2. Tell me:
   * Does the city feel convincing and worth exploring?
   * Does combat feel good, and does stealth feel fair?
   * Is the portrait direction right?
   * Do the sprites bother you as much as they bother me?
   * Does the music work?
3. Then I'll do the P1.5 revision pass and propose the vertical slice plan.
