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
**Why:** saves iterations next time a view-piece game or large sprites come up.
**How to apply:** any games/*/res/view.pcs work and any sprite larger than 16x16.
