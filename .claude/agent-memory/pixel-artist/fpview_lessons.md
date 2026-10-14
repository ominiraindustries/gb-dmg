---
name: fpview-lessons
description: Lessons from TORRE HUNDIDA (games/dungeon, 2026-10-14) first-person view pieces and big monster sprites - what worked for budget and readability
metadata:
  type: feedback
---
First art pass for the first-person crawler (not yet user-reviewed when written):
- Generate pieces with a scratch script: pixel painters in SCREEN coordinates per piece, slice
  into tiles, dedupe globally, write walls.tiles + view.pcs (index legend, needs >92 chars: use
  Latin-1/Greek letters; never '@', '.', ';' or space as legend chars). Painting in screen
  coords makes textures align across pieces, so dedup does the budget work.
- Partly covered side-wall tiles must contain the BG pixels behind them (ceiling/floor row
  pattern) - only safe where no earlier piece can be under that tile (check the paint order).
- BG must be strictly periodic in 16 px (2 tiles/row) or the count explodes (25 vs 10).
- Courses on side walls: draw only lines that stay inside one tile row (k2/k4/k6, lip only if
  same row); every line that straddles rows doubles tiles.
- Doors and stairs share the arch tiles if the tympanum is dark; ring/outline must look only
  sideways below the arch so every jamb tile is identical.
- Inner-edge rule: F*L/F*R fronts get a black line on their center-side edge, F*C none, sides a
  black line on their far edge -> one 1-px joint per cell boundary, no doubles.
- Big monsters: hand-mirrored ASCII left holes and thin lines; layered shapes (ellipses,
  capsules, polygons) each painting its own black outline then fill, plus an auto light-gray
  halo, gave clean silhouettes that read over black darkness and light walls. Same design
  renders d1 and d2.
- Item icons: chunky with a manual '-' halo; a ring+round body reads as a padlock - keep
  amulets V-chained so they don't clash with the lock.
Continuity pass (2026-10-14, user: "vista cercana y lejana desconexas"):
- Root cause was scale: sides had 4 perspective courses, fronts 8 small bricks. 8 courses on the
  sides costs ~114 tiles vs ~58 for 4 (measured), so ALL faces use 4 courses (ashlar) with lines
  shared at the corners. Ceiling joints / floor ribs on the depth planes (y 16/24, 80/72/64) tie
  BG to walls cheaply (horizontal lines are free in a 2-tile row). Keep BG 2-periodic: main.c
  fill_margins copies columns 0/1 into the slide margins.
- Tile savers: joints at pixel 7 of a tile so the F*L1 edge column dedupes; vertical corners in
  the mortar colour (no black seam between coplanar S0/S1/S2); S2L2/S2R2 = F3L2/F3R2 tiles (-10).
- Bayer gradients across a narrow side piece read as a dotted column, not a ramp: use flat tones
  per depth (1, 50% checker, 2, 3).
- `gb.py preview` view part needs bases for '@ base auto' (fpview.preview bug, reported);
  workaround: monkeypatch fpview.parse with screens.vram_bases.
**Why:** saves iterations next time a view-piece game or large sprites come up.
**How to apply:** any games/*/res/view.pcs work and any sprite larger than 16x16.
