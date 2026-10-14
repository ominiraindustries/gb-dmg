# Budgets: estimate before building

## Tiles (VRAM 384 tiles)
GBDK default (LCDC bit 4 = 0): BG/window use tiles 0-255 at $8800 addressing, i.e. BG 0-127 private
($9000) + 128-255 shared with sprites ($8800); sprites 0-127 private ($8000).
- Font: 36 tiles (digits + letters). HUD icons: 2-6.
- Level tileset: count unique 8x8 tiles in the mockups; metatiles (16x16 = 4 tiles) for maps.
- Sprites: 16x16 actor = 4 tiles per frame (8x16 mode: 2 sprites x 2 tiles); walk cycle 2-4 frames;
  use horizontal flip (`S_FLIPX`) instead of storing left-facing frames.
- If over budget: stream tiles per level/area (load with LCD off between levels), share tiles.

## Sprites (40 total, 10 per scanline)
Count the worst horizontal band: hero (2) + enemies (2 each) + bullets (1 each) + particles.
If > 10: reduce, stagger vertically, or flicker (rotate OAM order every frame; readable but ugly).

## CPU (per frame 70224 T; leave >= 20% headroom)
Measured in this repo:
| Work | Cost |
|---|---|
| Breakout full frame logic (1 ball, 54 bricks) | ~9-10 scanlines |
| Tetris idle frame | ~23 scanlines; hard drop + lock + spawn ~93 scanlines |
| `fits()` collision check (cached shape) | ~1000 T |
| Copy 10 tiles to VRAM (asm) / (C loop) / (`set_bkg_tiles`) | ~228 T / ~760 T / ~5200 T |
| Shmup peak (games/shmup towers zone: 12 bullets, 6 enemies, 4 shots, 2-4 turrets) | ~118 lines after optimizing (started at 131) |
| OAM groups for ~29 pooled objects (5 calls) | ~11-13k T (~25-29 lines): budget it, the GDD guessed 2500 T |
| Per-enemy logic in C (route, animation, firing) | ~600-900 T per enemy per frame even when simple |
| Shots x enemies collisions (4 shots/frame vs 6 enemies + 4 turrets, asm hit_first) | ~10k T |
| Move 27 pooled objects (asm) | ~7k T |
| First-person view (games/dungeon, 20x12 tiles, 3 cells deep): compose with culling (asm) | ~35k T per step (C version 100k) |
| Double-buffer copy, 4 rows of 20 tiles per VBlank (asm, 20 T/tile) | ~2.6k T; with GBDK's ISR that fills VBlank: nothing else that frame |
| Message log: start a message (scroll 4 lines + queue) | ~14k T (with memmove/strncpy from GBDK: 23k) |
Rule of thumb from games/shmup: estimate C per object at ~800 T and asm per drawn sprite at ~300 T;
GDD estimates of 40-120 T per object were 3-5x too low.
VBlank work after `vsync()`: ~3600 T total -> plan <= 4 rows of 10 tiles or 1 row of 20 + HUD per frame.

## ROM
Code: a small game is 4-10 KB of C. Tiles: 16 bytes each. Maps: 1 byte per tile (or per metatile).
Music (hUGEDriver): driver ~2 KB + songs 1-4 KB each. > 32 KB total => MBC5 + banking (see gbdk skill).

## RAM
WRAM 8 KB: boards/maps in RAM (e.g. 10x18 = 180 bytes), actor tables (struct of arrays), buffers.
HRAM 127 bytes: hottest variables only (asm).
