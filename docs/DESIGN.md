# Game design

Each section is marked **[P1]** (implemented in Prototype 1), **[P1-partial]**, or **[proposed]**.

## Core loop
Each **Night** (chapter) the city delivers new bodies and leads to the Deadhouse. Ines explores
districts on foot, talks to people, finds equipment, gains Remnants and opens new routes, then confronts
whoever is behind that Night's thread. Between Nights the city changes: headlines, who is alive, who
controls a block. **[proposed; P1 is a single block on Night Two]**

Minute to minute: walk a street that is alive, read light and shadow, talk, take something, choose how to
get into a guarded place, fight or avoid fighting, find a way back out. **[P1]**

## Movement
8-way movement, a noisy sprint, collision that slides along walls, and areas joined by doors, alleys,
ladders and windows. **[P1]**

## Light and stealth **[P1]**
* Enemies see you according to **how lit you are**. Visibility comes from the same light model the GPU
  draws, so what you see is what they see.
* Enemies have a vision cone, line of sight, a suspicion meter (calm → suspicious → alert) and hearing.
  Footsteps when sprinting, breaking glass, fights and gunshots are noises with different radii.
* **Breaking a bulb** with a bottle darkens a room. The noise draws people to investigate.
* **Takedowns** work on anyone who hasn't noticed you, from behind.
* The **lantern** lights a cone but makes you visible. Its **flash** blinds anyone looking at you.
* A gunshot carries into the street. In the tenement it **brings two more of Hobb's men**.

## Combat **[P1]**
* Ines is capable but not superhuman. Her moves are a light combo (the razor has three swings), a heavy
  attack, a dodge with invulnerability frames, a revolver (6 chambers, scarce rounds, aim assist, very
  loud), thrown bottles and the lantern flash.
* **Weapons change the moveset:** the razor is fast, causes bleeding and has short reach. The tire iron is
  slow, staggers, and its heavy attack breaks guards.
* **Feedback:** hit-stop, screen shake, white hit flash, blood that stays on the floor, a slash arc,
  knockback, and positional impact sounds.
* **Enemies telegraph:** a red mark during wind-ups, and a dashed then solid red aim line from a gunman.
  Up to two attack at once (attack tokens).
* **Enemy types in P1:**
  * the *brawler* (punch combo and a slow haymaker),
  * the *knifeman* (fast lunging flurries; strikes a match when he can't see, which also makes him a
    target),
  * the *gunman* Hobb (keeps his distance, aims with a telegraph, reloads, pistol-whips up close).
* **Healing:** field dressings, Ines's nurse's craft, taking 1.4 s to apply. **[P1]**
* **Planned:** Remnant active abilities (Maud's counter-stance and others), more enemy types, bosses.
  **[proposed]**

## Remnants **[P1-partial]**
Each Remnant has a **Lesson** (permanent traversal), an **Active** (combat), a **Passive**, and a **Read**
(a conversation insight).
* P1 includes **Silas Webb** (Lesson: *Climb* fire escapes; passive: quieter sprint) and **Maud Kessel**
  (Lesson: *Break* boarded doors). Maud is granted through a clearly labelled **prototype test kit** in the
  wagon, because her real acquisition scene, a playable memory fight in a Sumps cellar, belongs to the
  vertical slice.
* Remnants speak in Ines's head with contextual whispers, and on request (R).
* **Proposed:** two active slots, pairings that unlock combined abilities, unfinished business that
  strengthens them, and the release/sell choice (Last Call). Active abilities and Reads are not
  implemented.

## Equipment and inventory **[P1]**
Categories are Weapons (equip), Tools (revolver, lantern, matches), Items (rounds, bottles, dressings),
Evidence and Leads. There is no weight and no grid. P1 includes razor, tire iron, revolver, lantern,
bottles, dressings, matches, Augie's camera, the photograph, Hobb's ledger page and the 1931 film can.
**Proposed:** outfits as armour with social access (evening dress gets Ines into the Velour).

## Progression **[proposed]**
No XP. Growth comes from Remnants, equipment, outfits, **Scars** (personality traits earned at choices,
each with a perk), and max health/nerve gained by resolving major stories.

## Dialogue, choice and relationships **[P1]**
* A small scripting language (`.dlg`) with branching, conditions, effects and hooks.
* **Stance tags** on choices (`[cold] [warm] [wry] [blunt]`) record how Ines has been speaking.
  Characters' replies and later lines depend on it.
* **Memories:** characters remember specific things. Augie knows whether you looked at his prints and
  whether you lied about it. Vivienne remembers whether you saw through her, and whether you were
  interested.
* **Consequences in P1:** Vivienne gives the fire-escape tip only if Ines earned it (warm or wry). Sully's
  tip depends on giving him a light. Augie's ending lines differ depending on whether you lied.
* **Proposed:** discrete relationship stances (wary, trusting, intimate, betrayed), character agendas that
  advance Night by Night, and gossip that spreads.

## Living city **[P1]**
On Lantern Row:
* pedestrians, some with umbrellas, who scatter at gunfire;
* two street vignettes (an affair ending in a hotel doorway, two dancers on a smoke break);
* barks;
* a train on the El every 45–80 s, with moving window light;
* steam from the manholes, dancers silhouetted in the Velour's windows, and flickering, dying neon;
* the band bleeding through the walls.

There's also a cat in the alley.

## Adult content policy
* **[P1]** Vivienne's flirtation and invitation, the hotel couple's affair, the Row's economy of rooms by
  the hour, the pin-up in Hobb's room, and Augie's blackmail photograph. The photograph shows a closeted
  alderman with a dockworker, both adults, and is written with sympathy rather than for the joke.
* **[proposed]** Intimate scenes are real events with sensuality and consequence: written frankly and
  shown in illustrated vignettes, but not explicit. Nudity is drawn as figure art. Sexual violence exists
  only as narrative subject matter (survivors, aftermath, investigation) and is never depicted or playable.
  Every character in sexual content is an adult.
* The explicitness limit is a deliberate boundary set by the developer (the AI), not a technical
  limitation. It is documented as such.

## Addiction **[design decision]**
There is no dependence meter. Ines's history with morphine stays in the story as choices at key moments.
**[proposed]**
