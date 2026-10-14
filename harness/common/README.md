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
| `gbe_video.c` | VBlank shadows (SCX, palettes), fades, top-HUD window cut (LYC ISR) | `video_init(line, bgp, obp0, obp1)` | platformer |
| `gbe_screen.c` | transitions: fade out -> `screen_build(which)` with LCD off -> fade in | `screen_build()` | platformer |
| `gbe_actors.c` `gbe_actors.s` | actor arrays (struct of arrays), `act_spawn`, asm `act_move` | `GBE_ACT_MAX` | platformer: 240 T vs 1500 T |
| `gbe_map.c` `gbe_map.s` | 8-row metatile map in WRAM, asm `mt_at`/`solid_at`, camera follow, column streaming, queued cell redraws | `GBE_MAP_MAX_COLS`, `mt_tiles[][4]`, `mt_attr[]` | platformer |
| `gbe_sfx.c` | register SFX with per-channel priority | `sfx_table[]` | platformer |
| `gbe_vram.s` | `vram_col16`: 16 tiles down a BG column | - | platformer: 32 T/tile |
| `gbe_pool.c` `gbe_pool.s` | many-object pools (bullets, shots, enemies) in 8-bit OAM coords: `pool_alloc`, asm `pool_move` (free on exit), asm `hit_first` (box vs range) | `GBE_POOL_MAX` | gbe_lab: ~130 T/object move |
| `gbe_spr.c` (+ core in `gbe_pool.s`) | OAM groups with fixed ranges (lower range = priority) and per-frame rotation (`spr_rot`) for >10/line flicker; size 1 or 2 sprites per object | - | gbe_lab: ~4.1k T for 12 objects |
| `gbe_selftest.c` | asm-vs-C equivalence of all the above, run in the ROM | call `gbe_selftest()` when `gbe_eq_request` | test: `gb.selftest()` |

Header: `gbe.h` (documents every function and the rules). The game provides `src/gbe_config.h`:
```c
#define GBE_ACT_MAX      14     // actor slots
#define GBE_MAP_MAX_COLS 255    // only if gbe_map is used
#define GBE_POOL_MAX     32     // only if gbe_pool is used
#define GBE_SELFTEST_MAP 1      // which selftest sections to build: _MAP, _ACTORS, _POOL
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
- Keep loop counters in registers, not WRAM (`spr_group_core`: ~470 T/object saved by that alone).
- Collisions of many-vs-many on alternate frames (shots vs enemies `frame & 1`); player vs bullets
  every frame. Fast shots (4 px/f) vs 8+ px enemy boxes cannot tunnel at 2-frame steps.

## Adding to the library
Only extract code that a game already uses and tests. Keep a C reference for every asm routine and
add it to `gbe_selftest.c`. Update this table.
