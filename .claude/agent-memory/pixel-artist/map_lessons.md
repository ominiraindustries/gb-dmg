---
name: map-lessons
description: Lessons from building world maps (.map, harness/world.py) for games/faro M1b - autotiling generator, lints, object-cell conflicts
metadata:
  type: project
---
World maps for FARO (2026-10-14) were made with a scratch generator: sketch chars -> metatile names,
paths/water autotiled per 8x8 quadrant (each quadrant from its 2 orthogonal neighbours + diagonal ->
F/I/H/V/O, then look up the PATH_*/WATER_* metatile with that 4-quadrant shape), stamps for houses,
lighthouse, boats. The .map files are the source of truth afterwards.

**Why / how to apply:**
- 2-wide paths always autotile cleanly; 1-wide stubs into 2-wide bands and 1-cell islands next to a
  band give shapes with no metatile (e.g. IIFF) -> use 2-wide stubs and 2x2 islands.
- Trees are 2x2 blocks: keep forests row-pair aligned or the resolver leaves orphans.
- BOAT tiles have a white background: beach them on sand (fits "Varadero" anyway), not on water.
- One object per cell: a sign cannot share a cell with a patch (lens), so interactions go on a
  neighbour (table) or a trigger in front.
- The "<= 4 species per 3x3 sectors" lint constrains spawn tables by geometry: tell the designer.
- Exterior as ONE island map (GDD 6.1 grid, sea sectors deduped) instead of separate area maps.
Related: [[faro-style]]
