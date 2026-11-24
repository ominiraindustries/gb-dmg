---
name: gb-game-design
description: Game design for Game Boy DMG games - turning an idea into a scoped design document (GDD) with core loop, mechanics with concrete numbers, controls, screen flow, UI/HUD layout on the 20x18 tile grid, asset and sprite/tile budgets, milestones and a test plan. Load when planning a new game, designing or revising mechanics, game feel, difficulty, menus/HUD/UI, or checking whether a design fits DMG limits.
---

# Designing games for the DMG

> Design first (CLAUDE.md): read `docs/guias/diseno-juegos.md` and cite the rules applied; a level is not done until
> it passes its checklist. `python -I harness/scripts/kb.py query "..." --kind game,study,tecnica` finds what earlier
> GDDs, studies and technique cards already settled.

The design is done when a programmer can implement it without guessing and a tester can
check it. Every mechanic has numbers, every screen has a mockup, every asset has a budget.

## Process (in order, each step reviewed by the user before the next)

1. **Pitch** (5 lines): genre, fantasy ("you are..."), core loop in one sentence, what makes it
   different, target session length (DMG: 2-10 min sessions, playable on a bus).
2. **Core loop and mechanics**: the 30-second loop, then each mechanic with exact parameters
   in frames and pixels (see `feel.md`). Unknown values get a starting number + "tune in playtest".
3. **Controls**: D-pad, A, B, Start, Select only. A = main action (jump/confirm), B = secondary
   (attack/back), Start = pause/menu, Select = rarely used (map, swap). No simultaneous 3-button chords.
4. **Screens and flow**: list every screen (title, menus, gameplay, pause, game over, win...) as a
   state machine; each gets a `.screen` mockup (`ui.md`, rendered by `python harness/gb.py preview`).
5. **Content and budgets**: asset list with tile counts, sprite counts per scanline in the worst
   case, ROM size estimate, SRAM needs (`budgets.md`).
6. **Milestones**: M1 = vertical slice (one level/round fully playable with placeholder art),
   then content, then polish (juice, sound, transitions), then hardware test. Small scope first.
7. **Test plan**: for each mechanic, what an automated test or bot checks (positions, counters,
   frame budget, VRAM safety), and what needs a human playtest (feel, difficulty, fun).

Write it to `games/<game>/design/gdd.md` using `gdd-template.md`. Keep open questions in a
"Decisiones pendientes" list for the user instead of inventing answers to taste questions.

## DMG design constraints (cheat sheet)

| Limit | Design consequence |
|---|---|
| 160x144 px = 20x18 tiles | Little room: HUD 1-2 rows max; characters 16x16 typical; ~10 tiles of view ahead when scrolling |
| 4 shades, sprites 3 + transparent | Readability by contrast and silhouette, not color; 2 sprite palettes (OBP0/OBP1) for variants |
| 40 sprites, 10 per scanline | A 16x16 actor = 2 sprites wide (8x16 mode); max ~5 actors on one horizontal band; more = flicker |
| Blurry, slow LCD (ghosting) | Avoid fast small objects, 1-px details, thin moving lines, rapid flashing; projectiles >= 4x4 |
| ~70k T-cycles per frame, VBlank ~3600 T | Few hundred objects is impossible; tile updates per frame are limited (~40-60 tiles) |
| BG tiles 256 (128 shared w/ sprites) | Tilesets per level/area; metatiles 16x16 (4 tiles) for maps |
| ROM 32 KB w/o MBC; MBC5 up to MBs | Bigger games need banking from the start (decide in the GDD) |
| SRAM saves need battery cart | Decide early: high scores / progress save => MBC5 + RAM + battery |
| 4 sound channels (2 pulse, wave, noise) | Music uses 3-4 channels; SFX steal a channel briefly (usually ch1 or ch4) |
| Buttons: D-pad + A B Start Select | No analog; design around digital 8-way movement |

## Topic files

| Need | File |
|---|---|
| GDD skeleton to fill | `gdd-template.md` |
| Game feel numbers: movement, jumps, DAS, lock delay, coyote time, buffers, hit-stop, shake | `feel.md` |
| Screens, HUD, menus, text, fonts, transitions, `.screen` mockups | `ui.md` |
| Tile/sprite/ROM/CPU budgets and how to estimate them | `budgets.md` |
| Genre notes on GB: what each genre needs technically (scrolling, banking, multiplexing) | `genres.md` |

## Rules of thumb
- One new idea per game; everything else borrowed from proven GB games.
- Design for the worst case: the busiest moment must still fit sprites-per-line and frame budget.
- Prefer state you can test: every rule that matters exposes a global the tests can read.
- Difficulty ramps by parameters in tables (speeds, spawn rates), not by special-case code.
- Names: avoid trademarks for anything that might be released (e.g. "BLOCKS", not "Tetris").
