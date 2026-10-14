# harness/common - shared assets and the gbe engine library

Everything here was measured and tested in a real game before being extracted. A game opts in
from its `game.json`; nothing is linked unless listed.

## Assets (`*.tiles`)
| File | Contents | game.json |
|---|---|---|
| `font.tiles` | 5x7 font: DIGIT0..9, LETTER_A..Z, DASH EXCLAM DOT COLON QUESTION | `"common_res": ["font"]` |

## Code (`src/`)
List the files in `"common_src"`; their headers are on the include path.

| Files | What | Needs from the game | Origin / numbers |
|---|---|---|---|
| `bcd.s` `bcd.h` | `bcd_add3`: packed BCD add with `daa`, saturating at 999999 | - | tetris: ~100 T vs ~2000 T in C |
| `gbe_frame.c` | input edges, `frame_lines`/`max_frame_lines`, `vram_late` guard, `skip_measure` | - | tetris, platformer |
| `gbe_oam.c` | `oam16`/`oam8`: direct shadow OAM writes | - | platformer: ~3x cheaper |
| `gbe_video.c` | VBlank shadows (SCX, SCY, palettes) + `shake_x/y`, fades, top-HUD window cut (LYC ISR), `bgp_below` (BG palette under the cut) | `video_init(line, bgp, obp0, obp1)` | platformer, shmup |
| `gbe_screen.c` | transitions: fade out -> `screen_build(which)` with LCD off -> fade in | `screen_build()` | platformer |
| `gbe_actors.c` `gbe_actors.s` | actor arrays (struct of arrays), `act_spawn`, asm `act_move` | `GBE_ACT_MAX` | platformer: 240 T vs 1500 T |
| `gbe_map.c` `gbe_map.s` | 8-row metatile map in WRAM, asm `mt_at`/`solid_at`, camera follow, column streaming, queued cell redraws | `GBE_MAP_MAX_COLS`, `mt_tiles[][4]`, `mt_attr[]` | platformer |
| `gbe_vmap.c` `gbe_vmap.s` | vertical metatile map (shmups): 10-wide rows, WRAM ring of 16 rows, 1 tile row/frame streamed (<= 8 px/f), `vmap_set` + queue, scroll stop, `VMAP_ROW_Y(r)` | `mt_tiles[][4]`, `GBE_VMAP_W` | shmup: row build ~1000 T asm, copy 24 T/tile |
| `gbe_aim.c` `gbe_aim.s` | 32 directions, speed tables `aim_vx/aim_vy[spd*32+dir]`, `aim_dir(dx, dy)` (error <= 1, tested vs atan2), asm `fire` / C `fire_fan` into a pool range | `fire_first/n/t/tile/prop` | shmup: fire 2000 -> ~960 T |
| `gbe_sfx.c` + `gbe_sfx_asm.s` | register SFX with per-channel priority (`sfx` in asm; `sfx_c` documents it) | `sfx_table[]` | shmup: ~1000 -> ~300 T |
| `gbe_vram.s` | `vram_col16` (16 tiles down a BG column), `vram_mt4_list` (queued 2x2 metatiles; used by gbe_map and gbe_vmap) | - | platformer: 32 T/tile; metatile 600 -> 100 T |
| `gbe_pool.c` `gbe_pool.s` | many-object pools (bullets, shots, enemies) in 8-bit OAM coords: `pool_alloc`, asm `pool_move` (free on exit), asm `hit_first` (box vs range, one compare per axis) | `GBE_POOL_MAX` | shmup: move ~250 T, hit ~100 T per object |
| `gbe_spr.c` (+ asm `spr_group` in `gbe_pool.s`) | OAM groups with fixed ranges (lower range = priority); each group starts half a group further on odd frames, so a sprite dropped on a >10 line is drawn the next frame | `spr_rot` cycling through 2 x a common multiple of the slot counts (< 64) | shmup: ~300 T per drawn object |
| `gbe_bank.c` | read banked const data from any code (bank 0, restores the bank): `bank_set_bkg_data`, `bank_set_sprite_data`, `bank_memcpy`, `bank_read8` | game.json `"banked_res"` + MBC flags | gbe_lab: 3 banked tilesets loaded and checked byte by byte |
| `gbe_save.c` | SRAM save with two alternating slots (signature, version, sequence, length, Fletcher-16; signature written last): a torn store keeps the previous save | MBC with RAM+battery (`-Wm-yt0x1B -Wm-ya1`) | gbe_lab: power cycle, flipped bit, torn newest slot (`GB(rom, ram=g.power_off())`) |
| `gbe_view.c` `gbe_view.s` | first-person grid view (crawlers): pieces of `res/view.pcs` (harness/fpview.py) composed far to near, exact culling precomputed by fpview, classify + paint in asm | `view_map` (16x16), `view_class`, `view_cell()`, `view_bank`; generated `view.c` | dungeon: ~35k T per view (C: 100k), selftest asm == C at random cells |
| `gbe_bgbuf.c` | double buffer on the two BG maps: copy a 20-wide canvas into the hidden map N rows per VBlank, flip LCDC bit 3 | - | dungeon: 4 rows = 2.6k T per VBlank, flip after 3 |
| `gbe_vq.c` `gbe_vq.s` | VRAM write queue (byte stream) with a tile budget per VBlank | `vq_budget` (0 while another big copy runs) | dungeon: ~20 T per tile (an array-of-entries version: ~150) |
| `gbe_text.c` | shared-font text (`txt_tiles`, `txt_u16`) and a 4-line message log typed through gbe_vq | `txt_font`, `txt_blank`, "font" in common_res | dungeon |
| `gbe_menu.c` | vertical menu: cursor tile, repeat 16/6 f, wrap, disabled options, A / B | - | dungeon (M1b) |
| `gbe_rng.c` | xorshift16 `rng_next` / `rng_range`; `gb.rng_next(state)` predicts it in tests | seed `rng_state` | dungeon |
| `gbe_selftest.c` | asm-vs-C equivalence of all the above, run in the ROM | call `gbe_selftest()` when `gbe_eq_request` | test: `gb.selftest()` |

Header: `gbe.h` (documents every function and the rules). The game provides `src/gbe_config.h`:
```c
#define GBE_ACT_MAX      14     // actor slots
#define GBE_MAP_MAX_COLS 255    // only if gbe_map is used
#define GBE_POOL_MAX     32     // only if gbe_pool is used (+ 8 scratch records for the selftest)
#define GBE_VMAP_W       10     // only if gbe_vmap is used
#define GBE_SELFTEST_MAP 1      // which selftest sections to build: _MAP, _ACTORS, _POOL,
#define GBE_SELFTEST_VMAP 58    //   _VMAP <metatile count>
```
`games/gbe_lab` is the library test bench: a synthetic worst case (shmup peak, 26 objects) with a
frame-budget test and the selftest. Measure library changes there before touching a game.

## Main loop with gbe (see games/platformer/src/main.c)
```c
while (1) {
    vsync();
    frame_begin();                 // input + frame start
    map_draw_vram(); /* ... */     // VBlank: copies only, prepared last frame
    frame_vram_check();
    if (gbe_eq_request) { gbe_eq_request = 0; gbe_selftest(); skip_measure = 1; }
    if (!transition_update()) { /* game logic */ }
    /* sprites */
    sound_update();
    frame_end();
}
```

## Conventions baked into the asm
- Map: 8 metatile rows, world y biased by 32 (`GBE_Y_BIAS`), `mt_attr` bit 7 = solid, metatile 0 empty.
- Actors live within camera-32 .. camera+200 if you use 8-bit camera-relative math (games/platformer).

- Pool: array of 16-byte records (`pool_obj_t`, offsets fixed in `gbe_pool.s`). Measured on the
  shmup peak: C 53.7k T update / 52k draw; asm over struct-of-arrays 32.7k / 19.5k; asm over records
  26.4k / 13.5k. On the SM83 a record walked with one pointer beats one address per field.
- Keep loop counters in registers, not WRAM (`spr_group`: ~470 T/object saved by that alone).
- Collisions of many-vs-many: each shot every 2nd frame, half of the shots each frame (all on one
  frame was a 12k T peak); player vs bullets every frame. 5 px/f shots vs 14 px boxes cannot tunnel.
- What a frame costs with pools (games/shmup peak): OAM groups ~13k T, per-enemy C logic 600-900 T
  each, collisions ~10k, movement ~7k. `gb.worst_frames()` shows the mix of the worst frame.
- VBlank order with GBDK: `vsync()` returns after GBDK's ISR (~1100 T of the 4560 T of VBlank).
  Do the VRAM copies FIRST, read the joypad (`frame_begin`) after them; decide copy budgets before
  the copies start (dungeon: the text budget was decided after the view copy ended and ran late).
- Next step if a game needs more: a draw-friendly record layout (`t y x tile prop` first) so
  `spr_group` copies 4 consecutive bytes instead of jumping inside the record.

## Adding to the library
Only extract code that a game already uses and tests. Keep a C reference for every asm routine and
add it to `gbe_selftest.c`. Update this table.
