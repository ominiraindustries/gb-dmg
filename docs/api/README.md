# API de gbe (generada)

Generado por `python -I harness/scripts/apidoc.py` desde `harness/common/src/gbe.h` (+ `bcd.h`), las
cabeceras de cada `.c`/`.s` y la tabla de `harness/common/README.md`. **No se edita**: se corrige la
fuente y se regenera (`--check` en las pruebas). Qué usar para cada necesidad: `docs/guias/que-usar.md`.

> gbe - Game Boy engine: reusable pieces measured and tested in games/tetris and games/platformer.
> Use from a game with  "common_src": ["gbe_frame.c", ...]  in game.json (see harness/common/README.md)
> and a games/<game>/src/gbe_config.h with the sizes below.
> Rules the library is built on (CLAUDE.md "Rendimiento y VRAM"):
> - Loop: vsync() -> frame_begin() -> VRAM work (copies only) -> frame_vram_check() -> logic ->
> sprites -> frame_end(). Tiles are prepared outside VBlank; VBlank only copies.
> - vram_late must stay 0 in tests; max_frame_lines < 120 of 154.
> GBE_BANKED (gbe_config.h, MBC games): the non-hot modules (tbox, menu, save, the C part of gact) go
> to switchable banks and their functions are BANKED (games/faro: bank 0 overflowed with the engine).
> |d| < n for an 8-bit difference d = a - b (n <= 128). The obvious "(d + n) < 2n" is
> asymmetric (d = -n counts as near, +n does not): this bug hit games/platformer enemies.

| Módulo | Qué hace | Nombres | Juegos que lo usan |
|---|---|---|---|
| [`bcd`](bcd.md) | `bcd_add3`: packed BCD add with `daa`, saturating at 999999 | 1 | platformer, shmup, tetris |
| [`gbe_frame`](gbe_frame.md) | input edges, `frame_lines`/`max_frame_lines`, `vram_late` guard, `skip_measure` | 12 | dungeon, faro, gbe_lab, happyvalley, mazmorra, platformer, shmup, world_lab |
| [`gbe_oam`](gbe_oam.md) | `oam16`/`oam8`: direct shadow OAM writes | 2 | dungeon, faro, gbe_lab, happyvalley, mazmorra, platformer, shmup, world_lab |
| [`gbe_video`](gbe_video.md) | VBlank shadows (SCX, SCY, palettes) + `shake_x/y`, fades, top-HUD window cut (LYC ISR), `bgp_below` (BG palette under the cut) | 12 | dungeon, faro, gbe_lab, happyvalley, mazmorra, platformer, shmup, world_lab |
| [`gbe_util`](gbe_util.md) | r * 32 in 16 bits: SDCC sometimes compiles (uint16_t)r << 5 of an u8 local in 8 bits (BG map rows | 1 | happyvalley |
| [`gbe_raster`](gbe_raster.md) | Up to RASTER_MAX SCX changes per frame at chosen lines (parallax, curving tracks). Fill raster_line[] | 7 | - |
| [`gbe_screen`](gbe_screen.md) | transitions: fade out -> `screen_build(which)` with LCD off -> fade in | 6 | dungeon, faro, happyvalley, mazmorra, platformer, shmup |
| [`gbe_actors`](gbe_actors.md) | actor arrays (struct of arrays), `act_spawn`, asm `act_move` | 13 | platformer |
| [`gbe_map`](gbe_map.md) | 8-row metatile map in WRAM, asm `mt_at`/`solid_at`, camera follow, column streaming, queued cell redraws | 24 | platformer |
| [`gbe_vmap`](gbe_vmap.md) | vertical metatile map (shmups): 10-wide rows, WRAM ring of 16 rows, 1 tile row/frame streamed (<= 8 px/f), `vmap_set` + queue, scroll stop, `VMAP_ROW_Y(r)` | 18 | shmup |
| [`gbe_aim`](gbe_aim.md) | 32 directions, speed tables `aim_vx/aim_vy[spd*32+dir]`, `aim_dir(dx, dy)` (error <= 1, tested vs atan2), asm `fire` / C `fire_fan` into a pool range | 13 | shmup |
| [`gbe_pool`](gbe_pool.md) | many-object pools (bullets, shots, enemies) in 8-bit OAM coords: `pool_alloc`, asm `pool_move` (free on exit), asm `hit_first` (box vs range, one compare per axis) | 16 | gbe_lab, shmup |
| [`gbe_spr`](gbe_spr.md) | OAM groups with fixed ranges (lower range = priority); each group starts half a group further on odd frames, so a sprite dropped on a >10 line is drawn the next frame | 3 | gbe_lab, shmup |
| [`gbe_sfx`](gbe_sfx.md) | register SFX with per-channel priority (`sfx` in asm; `sfx_c` documents it) | 5 | dungeon, faro, happyvalley, mazmorra, platformer, shmup, world_lab |
| [`gbe_vram`](gbe_vram.md) | `vram_col16` (16 tiles down a BG column), `vram_mt4_list` (queued 2x2 metatiles; used by gbe_map and gbe_vmap) | 3 | dungeon, faro, mazmorra, platformer, shmup, world_lab |
| [`gbe_view`](gbe_view.md) | first-person grid view (crawlers): pieces of `res/view.pcs` (harness/fpview.py) composed far to near, exact culling precomputed by fpview, classify + paint in asm | 15 | dungeon |
| [`gbe_bgbuf`](gbe_bgbuf.md) | double buffer on the two BG maps: copy a 20-wide canvas into the hidden map N rows per VBlank, flip LCDC bit 3 | 8 | dungeon |
| [`gbe_vq`](gbe_vq.md) | VRAM write queue (byte stream) with a tile budget per VBlank | 14 | dungeon, faro, happyvalley, mazmorra, world_lab |
| [`gbe_vwf`](gbe_vwf.md) | Proportional text drawn into a strip of tiles (reference + test decoder: harness/vwf.py). Register | 5 | happyvalley, mazmorra, world_lab |
| [`gbe_text`](gbe_text.md) | shared-font text (`txt_tiles`, `txt_u16`) and a 4-line message log typed through gbe_vq | 15 | dungeon, faro, happyvalley, mazmorra, world_lab |
| [`gbe_menu`](gbe_menu.md) | vertical menu: cursor tile, repeat 16/6 f, wrap, disabled options, A / B | 7 | dungeon, faro, happyvalley, world_lab |
| [`gbe_rng`](gbe_rng.md) | xorshift16 `rng_next` / `rng_range`; `gb.rng_next(state)` predicts it in tests | 3 | dungeon, faro, happyvalley, mazmorra, world_lab |
| [`gbe_bank`](gbe_bank.md) | read banked const data from any code (bank 0, restores the bank): `bank_set_bkg_data`, `bank_set_sprite_data`, `bank_memcpy`, `bank_read8` | 4 | dungeon, faro, gbe_lab, happyvalley, mazmorra, world_lab |
| [`gbe_save`](gbe_save.md) | SRAM save with two alternating slots (signature, version, sequence, length, Fletcher-16; signature written last): a torn store keeps the previous save | 10 | dungeon, faro, gbe_lab, happyvalley, mazmorra |
| [`gbe_world`](gbe_world.md) | 4-way scrolling world of 16x16 metatiles (top-down RPGs): maps of sectors (16x16 cells) from `res/maps/*.map` (`harness/world.py`, banked), 3x3 sector cache in WRAM (half a sector loaded per frame), BG ring with a 13x12-cell drawn region, edge queue of lines drawn 3 metatiles per VBlank, asm `wmt_at`/`wprep_cell` | 36 | faro, mazmorra, world_lab |
| [`gbe_gact`](gbe_gact.md) | grid actors on gbe_world: 24-byte records, walking at N frames per cell (8.8), both cells taken, generic behaviours (STILL LOOK WANDER CHASE FLEE HOME FOLLOW), one thinker per frame, 16x16 drawing with the PRIO cell bit cached per cell; asm move/draw/`gact_at` | 30 | faro, mazmorra, world_lab |
| [`gbe_flags`](gbe_flags.md) | story flags (bitset, 1024 by default) and 16 byte variables, ids from `res/scripts/flags.txt` / `vars.txt` | 6 | faro, world_lab |
| [`gbe_tbox`](gbe_tbox.md) | dialogue box in the window: typewriter (1-2 chars/f, A finishes the page), pages with a blinking arrow, speaker tab, yes/no, 2x2 choice; all through gbe_vq | 21 | faro, world_lab |
| [`gbe_script`](gbe_script.md) | event script VM for `harness/script.py` bytecode (`res/scripts/*.evs`): flags, vars, say/ask/choice, wait, call/ret, game ops by table; runs from any bank, copies text and operands to WRAM first so game ops may be BANKED | 15 | faro, world_lab |
| [`gbe_tiles`](gbe_tiles.md) | tile DATA queue: runs of tiles from any bank, staged to WRAM in the logic, copied in VBlank with an unrolled asm copy (`tile_copy16`, ~330 T/tile), `tiles_budget` per VBlank (2) | 7 | faro, happyvalley, mazmorra, world_lab |
| [`gbe_list`](gbe_list.md) | scrolling list: n items, k visible rows, cursor, repeat, more-arrows; rows rendered by a game callback (same bank) | 16 | faro, happyvalley, world_lab |
| [`gbe_selftest`](gbe_selftest.md) | asm-vs-C equivalence of all the above, run in the ROM | 6 | dungeon, faro, gbe_lab, mazmorra, platformer, shmup, world_lab |

## Uso por juego

| Juego | Módulos |
|---|---|
| `games/breakout` | - (sin gbe) |
| `games/dungeon` | gbe_bank, gbe_bgbuf, gbe_frame, gbe_log, gbe_menu, gbe_oam, gbe_rng, gbe_save, gbe_screen, gbe_selftest, gbe_sfx, gbe_sfx_asm, gbe_text, gbe_video, gbe_view, gbe_vq, gbe_vram |
| `games/faro` | gbe_bank, gbe_flags, gbe_frame, gbe_gact, gbe_list, gbe_menu, gbe_oam, gbe_rng, gbe_save, gbe_screen, gbe_script, gbe_selftest, gbe_sfx, gbe_sfx_asm, gbe_tbox, gbe_text, gbe_tiles, gbe_video, gbe_vq, gbe_vram, gbe_world |
| `games/gbe_lab` | gbe_bank, gbe_frame, gbe_oam, gbe_pool, gbe_save, gbe_selftest, gbe_spr, gbe_video |
| `games/happyvalley` | gbe_bank, gbe_frame, gbe_list, gbe_menu, gbe_oam, gbe_rng, gbe_save, gbe_screen, gbe_sfx, gbe_sfx_asm, gbe_text, gbe_tiles, gbe_util, gbe_video, gbe_vq, gbe_vwf, gbe_vwf_blit |
| `games/hello` | - (sin gbe) |
| `games/mazmorra` | gbe_bank, gbe_frame, gbe_gact, gbe_oam, gbe_rng, gbe_save, gbe_screen, gbe_selftest, gbe_sfx, gbe_sfx_asm, gbe_text, gbe_tiles, gbe_video, gbe_vq, gbe_vram, gbe_vwf, gbe_vwf_blit, gbe_world |
| `games/platformer` | bcd, gbe_actors, gbe_frame, gbe_map, gbe_oam, gbe_screen, gbe_selftest, gbe_sfx, gbe_sfx_asm, gbe_video, gbe_vram |
| `games/shmup` | bcd, gbe_aim, gbe_frame, gbe_oam, gbe_pool, gbe_screen, gbe_selftest, gbe_sfx, gbe_sfx_asm, gbe_spr, gbe_video, gbe_vmap, gbe_vram |
| `games/tetris` | bcd |
| `games/world_lab` | gbe_bank, gbe_flags, gbe_frame, gbe_gact, gbe_list, gbe_menu, gbe_oam, gbe_rng, gbe_script, gbe_selftest, gbe_sfx, gbe_sfx_asm, gbe_tbox, gbe_text, gbe_tiles, gbe_video, gbe_vq, gbe_vram, gbe_vwf, gbe_vwf_blit, gbe_world |
