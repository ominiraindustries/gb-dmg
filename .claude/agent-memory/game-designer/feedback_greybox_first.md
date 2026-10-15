---
name: feedback-greybox-first
description: User's studio rule since 2026-10-15 - M1 is a greybox (harness/common/greybox.tiles + font) to check all logic; art/UI milestones only after the user has played it
metadata:
  type: feedback
---

"Primero el juego con cuadrados para comprobar toda la lógica, el arte al final." M1 of a new game is a
playable greybox using `harness/common/greybox.tiles` (WALL FLOOR DOOR BOX DOT CROSS CHECK GRAY ARROW_U
ARROW_R BLANK SOLID) + the shared font; art and UI come in a later milestone after the user's playtest.
He also chose the proportional font `font_mini` (gbe_vwf) for text.

**Why:** earlier games (faro) broke visually and logically at the same time; logic first is cheaper.
**How to apply:** in every new GDD, plan M1 visuals only with greybox tiles (actors = BOX + digits,
markers = DOOR/CHECK columns), budget VRAM for greybox + font_mini + a vwf text slot, and list the art
assets for M3 separately. Simulation-heavy games: specify formulas so a Python model can mirror the ROM.
Related: [[project-happyvalley]].
