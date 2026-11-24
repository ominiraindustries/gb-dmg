# `gbe_bgbuf` — gbe_bgbuf.c

**Qué hace:** double buffer on the two BG maps: copy a 20-wide canvas into the hidden map N rows per VBlank, flip LCDC bit 3

**Lo que pone el juego:** -

**Origen y cifras:** dungeon: 4 rows = 2.6k T per VBlank, flip after 3

**Ficheros:** `harness/common/src/gbe_bgbuf.c` — en game.json: `"common_src": ["gbe_bgbuf.c"]`

**Juegos que lo usan:** `games/dungeon`

## Nombres

| Nombre | Comentario |
|---|---|
| `bg_front` | Double buffer on the two BG maps (LCDC bit 3): copy a 20-wide WRAM canvas into the hidden map bgbuf_rows_per rows per VBlank, then flip. bg_front = visible map (0 $9800, 1 $9C00). |
| `bgbuf_rows_left` | (ver `bg_front`) |
| `bgbuf_rows_per` | (ver `bg_front`) |
| `view_flips` | (ver `bg_front`) |
| `bgbuf_flip_xor` | (ver `bg_front`) |
| `bgbuf_start` |  |
| `bgbuf_draw_vram` | VBlank |
| `bgbuf_fill_both` | LCD off |

## Cabecera (`gbe.h`)

```c
// Double buffer on the two BG maps (LCDC bit 3): copy a 20-wide WRAM canvas into the hidden map
// bgbuf_rows_per rows per VBlank, then flip. bg_front = visible map (0 $9800, 1 $9C00).
extern uint8_t bg_front, bgbuf_rows_left, bgbuf_rows_per, view_flips, bgbuf_flip_xor;
void bgbuf_start(const uint8_t *src, uint8_t rows, uint8_t dst_row);
void bgbuf_draw_vram(void);                     // VBlank
void bgbuf_fill_both(const uint8_t *src, uint8_t rows, uint8_t dst_row);   // LCD off
```

## Notas de implementación

`gbe_bgbuf.c`:

> gbe: double buffer with the two BG maps ($9800 / $9C00, LCDC bit 3). A WRAM canvas (20 tiles
> wide) is copied into the hidden map a few rows per VBlank; when the last row is copied, still
> in VBlank, LCDC bit 3 flips and the whole new picture appears at once (no tearing, no LCD off).
> The window may use rows 0-5 of $9C00 (HUD at the bottom): keep the canvas rows elsewhere.
> Measured in games/dungeon (12 rows x 20 tiles): see harness/common/README.md.
