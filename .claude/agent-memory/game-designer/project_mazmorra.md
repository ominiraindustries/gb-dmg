---
name: project-mazmorra
description: games/mazmorra = Zelda-like one-dungeon game MADRIGUERA (GDD v0.1 2026-10-15): Tilo vs Rey Topo, 9 flip-screen rooms on a gbe_world map, bombs, M1 = 3 rooms + babosa
metadata:
  type: project
---

games/mazmorra: user asked (2026-10-15) for a Zelda-like with ONE dungeon, 6-9 rooms, flip-screen
(Link's Awakening slide), sword, 2-3 enemy types, keys/locked doors, one path item, boss, hearts,
signs/dialogue, save, 20-30 min. Studio constraint after faro: M1 = 3 rooms + 1 enemy + sword + hearts
HUD + transitions + title; worst frame < 100 lines.

My GDD v0.1 choices (verify in games/mazmorra/design/gdd.md): title MADRIGUERA, hero Tilo, boss Rey
Topo, NPC Don Terron, village Robledo, Campana del Alba. Enemies babosa (M1), topillo, escupidor.
Bombs recommended over hook. Whole dungeon = one res/maps/mazmorra.map of 2x2 sectors (rooms 10x8 on a
3x4 grid, cache holds the whole map), camera locked per room, slide 4 px/f with world_edge_budget 4;
enemies on gbe_gact with gact_px=0xFF. HUD top in the window (hud_cut line 16), dialogue box window
rows 2-6 under it (cut 56), pause = cut 144. Compact shared font font_mini planned (comparison image
first). Engine items E1-E7 in GDD 9.4.

**Why:** smallest polished slice after faro's failure; reuse world/gact/tbox/script/save.
**How to apply:** keep M1 tiny; pending decisions were item, room format, grid enemies. Related:
[[project-faro]], [[user-taste]], [[feedback-commercial-scope]].
