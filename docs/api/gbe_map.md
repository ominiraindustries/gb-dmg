# `gbe_map` — gbe_map.c / .s

**Qué hace:** 8-row metatile map in WRAM, asm `mt_at`/`solid_at`, camera follow, column streaming, queued cell redraws

**Lo que pone el juego:** `GBE_MAP_MAX_COLS`, `mt_tiles[][4]`, `mt_attr[]`

**Origen y cifras:** platformer

**Ficheros:** `harness/common/src/gbe_map.c`, `harness/common/src/gbe_map.s` — en game.json: `"common_src": ["gbe_map.c", "gbe_map.s"]`

**Juegos que lo usan:** `games/platformer`

## Nombres

| Nombre | Comentario |
|---|---|
| `GBE_Y_BIAS` | Side-scrolling metatile map: GBE_MAP_ROWS (8) rows of 16x16 metatiles, column-major in WRAM, world y with Y_BIAS 32 (map row 0 at y 32), BG ring of 32 tile columns streamed 1 per frame. The game... |
| `GBE_MAP_ROWS` |  |
| `ATTR_SOLID` |  |
| `mt_tiles` |  |
| `mt_attr` |  |
| `level` |  |
| `level_cols` |  |
| `map_wall_mt` |  |
| `col_buf` |  |
| `col_pending` |  |
| `level_px_w` |  |
| `camera_x` |  |
| `camera_max` |  |
| `cols_written` |  |
| `map_load` | LCD off |
| `map_follow` | camera never goes back; streams <= 1 column |
| `map_set` | change a cell (+ queued redraw if on screen) |
| `map_draw_vram` | VBlank: column + up to 8 queued metatiles |
| `mt_at` | asm: metatile at a world pixel (0 above/below, wall past end) |
| `solid_at` | asm: mt_attr[mt_at()] & ATTR_SOLID |
| `mt_at_c` | C references for the equivalence test |
| `solid_at_c` |  |
| `map_column` | fill col_buf with tile column tc (asm inside) |
| `map_column_c` |  |

## Cabecera (`gbe.h`)

```c
// Side-scrolling metatile map: GBE_MAP_ROWS (8) rows of 16x16 metatiles, column-major in WRAM,
// world y with Y_BIAS 32 (map row 0 at y 32), BG ring of 32 tile columns streamed 1 per frame.
// The game defines:  const uint8_t mt_tiles[][4] (TL TR BL BR)  and  const uint8_t mt_attr[]
// (bit 7 = solid). Metatile 0 must be empty.
#define GBE_Y_BIAS   32
#define GBE_MAP_ROWS 8
#ifndef ATTR_SOLID
#define ATTR_SOLID   0x80
#endif
extern const uint8_t mt_tiles[][4];
extern const uint8_t mt_attr[];
extern uint8_t level[], level_cols, map_wall_mt, col_buf[], col_pending;
extern uint16_t level_px_w, camera_x, camera_max, cols_written;
void map_load(const uint8_t *src, uint8_t cols, uint16_t cam, uint8_t wall_mt);   // LCD off
void map_follow(uint16_t target_x, uint8_t lead);   // camera never goes back; streams <= 1 column
void map_set(uint8_t col, uint8_t row, uint8_t mt); // change a cell (+ queued redraw if on screen)
void map_draw_vram(void);                           // VBlank: column + up to 8 queued metatiles
uint8_t mt_at(uint16_t x, uint8_t y);    // asm: metatile at a world pixel (0 above/below, wall past end)
uint8_t solid_at(uint16_t x, uint8_t y); // asm: mt_attr[mt_at()] & ATTR_SOLID
uint8_t mt_at_c(uint16_t x, uint8_t y);  // C references for the equivalence test
uint8_t solid_at_c(uint16_t x, uint8_t y);
void map_column(uint16_t tc);            // fill col_buf with tile column tc (asm inside)
void map_column_c(uint16_t tc);
```

## Notas de implementación

`gbe_map.c`:

> gbe: side-scrolling metatile map in WRAM, camera and column streaming, cell changes.
> Sizes from gbe_config.h (GBE_MAP_MAX_COLS). Tables from the game: mt_tiles, mt_attr.

`gbe_map.s`:

> gbe (map) - shared engine asm (harness/common/src). Measured and equivalence-tested in
> games/platformer. Call VRAM writers only in VBlank or with the LCD off.
