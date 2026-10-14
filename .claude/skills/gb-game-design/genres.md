# Genre notes for the DMG (technical implications for the GDD)

| Genre | GB references | Technical needs | Risks |
|---|---|---|---|
| Fixed-screen arcade (breakout, pac-like, single-screen platformer) | Alleyway, Mario Bros-likes | No scrolling, BG redraw only of changed tiles, simple | Few: good first projects |
| Falling-block puzzle | Tetris, Dr. Mario | Board in WRAM, row copies in VBlank, line clear animation | VRAM budget on big clears (solved in games/tetris) |
| Side-scrolling platformer | Super Mario Land, Kirby | Scrolling with column streaming (1 column of 18 tiles per 8 px), metatile maps, collision maps in ROM, camera, banking for levels | VRAM streaming in VBlank, sprite per line, slopes are hard |
| Top-down action/adventure | Zelda: Link's Awakening | Screen-by-screen or scrolling rooms, metatiles, many maps => MBC5 banking, text boxes, inventory UI, save | Scope; save data design |
| Vertical shmup | Solar Striker | Vertical scroll (row streaming), many bullets => sprite pools, flicker manager, fast collision (grid/AABB) | 10 sprites/line, CPU for collisions |
| RPG / turn-based | Pokémon, Final Fantasy Legend | Menus, text engine, big data tables in banks, SRAM saves, battle screens | Content volume, text rendering speed |
| Racing (pseudo-3D) | F1 Race | Raster effects (LYC interrupt per line changing SCX), road tables | Mid-frame timing, emulator vs hardware differences |
| Card/board game | Solitaire, chess | Cursor UI, AI search (CPU heavy, spread over frames) | AI must not block frames: compute incrementally |

## Scope ladder (suggested order of projects)
1. Fixed-screen arcade (done: breakout)
2. Grid puzzle (done: tetris)
3. Single-screen action with enemies and animation (sprite animation, simple AI)
4. Horizontal scrolling platformer, one level (streaming, metatiles, camera)
5. Multi-level game with save (MBC5, banking, SRAM)
6. Adventure/RPG (text engine, menus, data in banks)
