---
name: faro-style
description: FARO (games/faro) art direction from the user (2026-10-14) - clean Link's Awakening look, own identity, male hero Leo; what worked technically
metadata:
  type: feedback
---
User on FARO: "no me hagas algo muy generico, hazme algo con estilo propio, mas clean, tipo Zelda".
Protagonist is a BOY, Leo (keeper's grandson), not Mar.

**Why:** first pass (dotted paths, hatched/engraved battle art, textured trees, plank walls) read as
generic RPG-maker noise.
**How to apply (any top-down/RPG art for this user):**
- Flat fills, few deliberate shades, crisp black outlines, ONE light source; no hatching, no random
  speckles; calm light ground (grass = 1-2 tufts per 16x16, paths flat light grey with soft scalloped edges).
- Give the place identity motifs: FARO uses umbrella-pine signature tree, whitewashed houses with
  porthole windows, arched doors and scalloped eaves, fog as a single white curl per 16x16, the lighthouse.
- Chunky foliage that reads as leaves (not rock): lobed canopy painter = small discs, upper lobes in
  front, 2 tones ('-' lit upper-left / '+'), black rim under each front lobe, black silhouette.
  Smooth gradients + glints on round blobs always read as ROCKS.
- Battle pictures: layered shapes (bpaint) with flat 3-tone quantize work well and look clean.
- Field sprites 16x16 chibi with a light knitted beanie made the hero readable over every ground.
Tech notes: 4 Spanish glyphs went to harness/common/font_es.tiles (appending to font.tiles pushed
games/dungeon to 258 BG tiles). Generators lived in the session scratchpad; the .tiles are the source.
