# `gbe_vmap` — gbe_vmap.c / .s

**Qué hace:** vertical metatile map (shmups): 10-wide rows, WRAM ring of 16 rows, 1 tile row/frame streamed (<= 8 px/f), `vmap_set` + queue, scroll stop, `VMAP_ROW_Y(r)`

**Lo que pone el juego:** `mt_tiles[][4]`, `GBE_VMAP_W`

**Origen y cifras:** shmup: row build ~1000 T asm, copy 24 T/tile

**Ficheros:** `harness/common/src/gbe_vmap.c`, `harness/common/src/gbe_vmap.s` — en game.json: `"common_src": ["gbe_vmap.c", "gbe_vmap.s"]`

**Juegos que lo usan:** `games/shmup`

## Nombres

| Nombre | Comentario |
|---|---|
| `GBE_VMAP_W` | Vertical metatile map (shmups): GBE_VMAP_W (10) metatiles per row = the screen width, row 0 = bottom, world y grows up, scroll_y = world px at the bottom screen line (SCY = 112 - scroll_y). WRAM... |
| `VMAP_ROW_Y` | OAM Y (8-bit) of the top edge of metatile row r: valid while the row is near the screen |
| `vmap_ring` |  |
| `row_buf` |  |
| `row_pending` |  |
| `scroll_sub` |  |
| `vmap_rows` |  |
| `vmap_mrows` |  |
| `vmap_stop` |  |
| `rows_written` |  |
| `scroll_y` |  |
| `vmap_load` | LCD off |
| `vmap_scroll` | per frame: scroll + SCY shadow + <= 1 tile row prepared |
| `vmap_get` | ring cell (0 if not in the ring) |
| `vmap_set` | ring cell + queued redraw if drawn |
| `vmap_draw_vram` | VBlank: row + up to 8 queued metatiles |
| `gbe_vrow_tiles` | asm: row_buf = one half of a metatile row |
| `gbe_vrow_tiles_c` | C reference |

## Cabecera (`gbe.h`)

```c
// Vertical metatile map (shmups): GBE_VMAP_W (10) metatiles per row = the screen width, row 0 =
// bottom, world y grows up, scroll_y = world px at the bottom screen line (SCY = 112 - scroll_y).
// WRAM ring of 16 metatile rows, BG ring of 32 tile rows streamed 1 per frame (speed <= 8 px/f).
// Same game tables as gbe_map: mt_tiles[][4]. Map rows past the end read as metatile 0.
#ifndef GBE_VMAP_W
#define GBE_VMAP_W 10
#endif
// OAM Y (8-bit) of the top edge of metatile row r: valid while the row is near the screen
#define VMAP_ROW_Y(r) ((uint8_t)((uint8_t)scroll_y + 144 - ((uint8_t)(r) << 4)))
extern uint8_t vmap_ring[], row_buf[], row_pending, scroll_sub;
extern uint16_t vmap_rows, vmap_mrows, vmap_stop, rows_written, scroll_y;
void vmap_load(const uint8_t *src, uint16_t rows, uint16_t scroll, uint16_t stop);   // LCD off
void vmap_scroll(uint16_t speed);       // per frame: scroll + SCY shadow + <= 1 tile row prepared
uint8_t vmap_get(uint8_t col, uint16_t row);           // ring cell (0 if not in the ring)
void vmap_set(uint8_t col, uint16_t row, uint8_t mt);  // ring cell + queued redraw if drawn
void vmap_draw_vram(void);              // VBlank: row + up to 8 queued metatiles
void gbe_vrow_tiles(const uint8_t *m, uint8_t top);    // asm: row_buf = one half of a metatile row
void gbe_vrow_tiles_c(const uint8_t *m, uint8_t top);  // C reference
```

## Notas de implementación

`gbe_vmap.c`:

> gbe: vertical metatile map (shmups) - rows of 10 metatiles (20 tiles, the screen width, no
> horizontal scroll), a WRAM ring of the rows near the screen, tile-row streaming into the
> 32-row BG ring, cell changes with queued redraws, scroll stop.
> 
> World y grows UP from the bottom of map row 0; scroll_y = world px at the bottom screen line.
> Tile row tr (world px 8tr..8tr+7) lives in BG map row 31 - (tr & 31), so with
> SCY = 112 - scroll_y screen line L shows world px scroll_y + 143 - L.
> Tables from the game: mt_tiles[][4] (TL TR BL BR), as in gbe_map.

`gbe_vmap.s`:

> gbe (vmap) - vertical map asm: tile row preparation and the 20-tile VRAM row copy.
> C reference: gbe_vrow_tiles_c in gbe_vmap.c, checked by gbe_selftest.c (GBE_SELFTEST_VMAP).
