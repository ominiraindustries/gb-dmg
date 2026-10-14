# UI, HUD and screens on the DMG

## The grid
Screen = 20 columns x 18 rows of 8x8 tiles. Design every screen on this grid with a `.screen`
mockup in `games/<game>/design/screens/<name>.screen` and render it with
`python harness/gb.py preview <game>` (format documented at the top of `harness/preview.py`).
Look at the PNG (Read tool) before calling a screen done.

## HUD
- 1 row (top or bottom) is usually enough; 2 rows max. Score, lives, level/time.
- Static HUD over a scrolling level: use the **window layer** (WX/WY) for the HUD, BG for the level,
  or a LYC interrupt to change SCX at the HUD line. Fixed-screen games can draw HUD in the BG.
- Right-align numbers, blank leading zeros (or keep zeros for an arcade look - pick one).
- HUD values are rendered to a tile buffer when they change (outside VBlank) and copied in VBlank.
- Icons (hearts, lives) beat digits for small counts (<= 5).

## Text
- Shared fonts: `harness/common/font.tiles` (digits, A-Z, `- ! . : ? /`, bold 7x7, 42 tiles) and
  `font_lower.tiles` (a-z, 26 tiles, same baseline). Missing glyphs go there (shared), never per game.
  No accents or n-tilde: write "Pocion", and rephrase words that need the n-tilde.
- **Sentence case** (user preference since games/dungeon): "Nueva partida", "Pulsa Start",
  "Coges una llave". Capitals only at the start of a line/label, acronyms (PV), button names, and
  title logos. Budget both fonts (68 BG tiles) in the GDD from the start.
- Descenders g j p q y drop 1 px into row 7: in lines stacked every 8 px they can touch the line
  below (accepted in the dungeon log); a title right over a dark area needs a blank row.
- 18 characters per line inside a 1-tile border; dialogue boxes 3-4 lines at the bottom (rows 13-17).
- Text appears letter by letter (1 char / 1-2 frames), A speeds up / advances, blinking arrow when
  waiting. Never more than ~20 tiles written per frame.
- Short words; DMG blur makes dense text hard to read.

## Menus
- Cursor sprite (arrow) beside options, wrap-around, D-pad with auto-repeat, A confirm, B back.
- Highlight by cursor, not by color (we have none).
- Title screen: logo (big tiles), "Pulsa Start" blinking at ~1 Hz (30 frames on/off), options below.

## Screen flow
Every game needs: title, gameplay, pause, game over (and/or win), optional options/high scores.
Transitions: fade out (BGP steps) -> redraw with LCD off (allowed: one blank frame) -> fade in.
Mark LCD-off redraw frames with `skip_measure` so frame-budget tests ignore them.

## Readability checklist (review every mockup)
- [ ] Player and enemies readable at a glance (dark outline, distinct silhouettes)?
- [ ] Background lighter / lower contrast than actors?
- [ ] Interactive vs decorative tiles distinguishable?
- [ ] Nothing important in light gray on white?
- [ ] HUD does not overlap the action; numbers aligned?
- [ ] Fits 10 sprites per scanline in the busiest row?
