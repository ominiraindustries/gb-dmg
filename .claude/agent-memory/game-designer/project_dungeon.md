---
name: project-dungeon
description: games/dungeon = first-person grid dungeon crawler TORRE HUNDIDA, GDD v1.0 approved 2026-10-14; vehicle for ROM banking, double-buffered BG view, text/menus, SRAM save, grid levels
metadata:
  type: project
---

games/dungeon: first-person grid crawler the user asked for "tipo Eye of the Beholder o Dungeon Hack"
(GDD v1.0 approved 2026-10-14). Theme TORRE HUNDIDA: wizard's apprentice descends a tower swallowed
upside down; monsters diablillo/armadura viva/ojo flotante; staff and amulet. One hero, slow real-time
combat with wind-up, view on top + window HUD, automap, save anytime.

Key design choices made in the GDD (verify against games/dungeon/design/gdd.md before reusing):
- View 160x96 (20x12 tiles) drawn as a mosaic of pre-drawn pieces (tile-index spans), planes at
  z=2,3,4 with all edges on 8 px: P1 cols 4-15 rows 2-9, P2 6-13/3-8, P3 7-12/4-7.
- Double buffer with LCDC.3 (two BG maps), 4 rows/VBlank x 3 VBlanks (~2200 T each), flip at end;
  HUD in the window at WY=96 ($9C00 rows 0-5), view at map rows 8-19 (SCY base 64).
- Engine list E1-E16 (banking base already existed: banked_res + gbe_bank; gbe_save and gbtest
  power_off/ram existed too, E1/E8/E13 are extensions; gbe_view, gbe_bgbuf, gbe_vq, gbe_text, gbe_menu, gbe_save,
  gbe_rng, levels "grid" order, fpview.py reference composer).

**Why:** like shmup, the game exists to grow the harness; banking was the blocking pending task.
**How to apply:** when revising, keep engine work (M1a) before game logic (M1b) and re-measure the
estimated costs (compose 24-30k T, VBlank 78%) once M1a exists. Related: [[project-shmup]], [[user-taste]].
