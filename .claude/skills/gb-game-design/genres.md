# Genre notes for the DMG (technical implications for the GDD)

| Genre | GB references | Technical needs | Risks |
|---|---|---|---|
| Fixed-screen arcade (breakout, pac-like, single-screen platformer) | Alleyway, Mario Bros-likes | No scrolling, BG redraw only of changed tiles, simple | Few: good first projects |
| Falling-block puzzle | Tetris, Dr. Mario | Board in WRAM, row copies in VBlank, line clear animation | VRAM budget on big clears (solved in games/tetris) |
| Side-scrolling platformer | Super Mario Land, Kirby | Scrolling with column streaming (1 column of 18 tiles per 8 px), metatile maps, collision maps in ROM, camera, banking for levels | VRAM streaming in VBlank, sprite per line, slopes are hard |
| Top-down action/adventure | Zelda: Link's Awakening | Screen-by-screen or scrolling rooms, metatiles, many maps => MBC5 banking, text boxes, inventory UI, save | Scope; save data design |
| Vertical shmup | Solar Striker | Vertical scroll (row streaming), many bullets => sprite pools, flicker manager, fast collision (grid/AABB). Reference: games/shmup (GRIFO) on gbe_vmap/gbe_pool/gbe_spr/gbe_aim, boss drawn in the BG | 10 sprites/line, CPU: the peak is many medium costs at once (see budgets.md) |
| First-person grid crawler | Eye of the Beholder, Dungeon Hack (PC) | View = mosaic of pre-drawn pieces in the BG (`harness/fpview.py` + gbe_view), two BG maps flipped with LCDC.3, HUD in the window, grid levels, automap, message log, menus, SRAM save, banks. Reference: games/dungeon (TORRE HUNDIDA) | VRAM (the view takes ~160 BG tiles), cost of composing a step, near/far art continuity, bank 0 filling up |
| RPG / turn-based | Pokémon, Final Fantasy Legend | Menus, text engine, big data tables in banks, SRAM saves, battle screens | Content volume, text rendering speed |
| Racing (pseudo-3D) | F1 Race | Raster effects (LYC interrupt per line changing SCX), road tables | Mid-frame timing, emulator vs hardware differences |
| Card/board game | Solitaire, chess | Cursor UI, AI search (CPU heavy, spread over frames) | AI must not block frames: compute incrementally |

## First-person grid crawler (measured in games/dungeon)
- View 160x96 = 20x12 tiles, 3 cells deep, every plane edge on 8 px. Pieces live in `res/view.pcs`;
  `fpview.py` is the reference compositor (occlusion masks, canonical-scene PNGs) and the tests
  compare the ROM's view with it after 200 random moves. Design the geometry there first.
- Cost: composing a step in C was 100k T; with tables, asm classify/paint and occlusion culling
  ~35k T (budgets.md). The step frame only composes; seen cells, AI and HUD wait for later frames.
  The 240 tiles go to the hidden BG map 4 rows per VBlank (3 VBlanks), then LCDC.3 flips.
- Feel: an instant step with a 2-3 px bob, turns as a short SCX slide over margins filled with the
  BG pattern. Real-time combat needs a telegraph (wind-up >= 12 frames) so stepping away works.
- Monsters/items: occupancy maps (one byte per cell) for O(1) "who is there"; AI on alternate halves.
- VRAM 256 BG tiles: view 162 + UI 24 + fonts 68 = 254, so the title art shares the view's slot
  (`vram_order` list). Plan the fonts' 68 tiles from the GDD on.
- ROM: bank 0 filled at M1b; menus/screens/save code moved to bank 1 (gbdk `banking.md`).
- Art: the same scale on every face (4 stone courses near and far), BG 16 px periodic, flat tones
  per depth (gb-pixel-art). The user saw the near/far mismatch at once.

## Scope ladder (suggested order of projects)
1. Fixed-screen arcade (done: breakout)
2. Grid puzzle (done: tetris)
3. Single-screen action with enemies and animation (sprite animation, simple AI)
4. Horizontal scrolling platformer, one level (streaming, metatiles, camera) (done: platformer)
5. Multi-level game with save (MBC5, banking, SRAM) (banking + save done: dungeon, one floor)
6. Adventure/RPG (text engine, menus, data in banks) (text log + menus: dungeon)
