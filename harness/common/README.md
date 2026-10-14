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
| `gbe_selftest.c` | asm-vs-C equivalence of all the above, run in the ROM | call `gbe_selftest()` when `gbe_eq_request` | test: `gb.selftest()` |

Header: `gbe.h` (documents every function and the rules). The game provides `src/gbe_config.h`:
```c
#define GBE_ACT_MAX      14     // actor slots
#define GBE_MAP_MAX_COLS 255    // only if gbe_map is used
```

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

## Adding to the library
Only extract code that a game already uses and tests. Keep a C reference for every asm routine and
add it to `gbe_selftest.c`. Update this table.
