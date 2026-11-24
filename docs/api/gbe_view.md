# `gbe_view` — gbe_view.c / .s

**Qué hace:** first-person grid view (crawlers): pieces of `res/view.pcs` (harness/fpview.py) composed far to near, exact culling precomputed by fpview, classify + paint in asm

**Lo que pone el juego:** `view_map` (16x16), `view_class`, `view_cell()`, `view_bank`; generated `view.c`

**Origen y cifras:** dungeon: ~35k T per view (C: 100k), selftest asm == C at random cells

**Ficheros:** `harness/common/src/gbe_view.c`, `harness/common/src/gbe_view.s` — en game.json: `"common_src": ["gbe_view.c", "gbe_view.s"]`

**Juegos que lo usan:** `games/dungeon`

## Nombres

| Nombre | Comentario |
|---|---|
| `VIEW_W` | First-person grid view (crawlers): pieces from res/view.pcs (harness/fpview.py) composed far to near into view_buf (20x12 tile indices). The game defines view_cell() and links view.c. |
| `VIEW_H` |  |
| `view_buf` | view_bank = BANK(view) if banked, else 0 |
| `view_bank` | (ver `view_buf`) |
| `view_map` | 16x16 cell types + type -> VIEW_* (asm reads them) |
| `view_class` | (ver `view_map`) |
| `view_dx` | facing 0 N, 1 E, 2 S, 3 W |
| `view_dy` | (ver `view_dx`) |
| `view_cell` | provided by the game (off the map = VIEW_WALL) |
| `view_compose` | asm core (gbe_view.s) |
| `view_compose_c` | C reference |
| `view_compose_bg` | background piece only (map margins) |
| `view_mark_seen` | after view_compose: 16x16 bit map of seen cells |
| `view_blit` | asm |
| `view_blit_c` | C reference |

## Cabecera (`gbe.h`)

```c
// First-person grid view (crawlers): pieces from res/view.pcs (harness/fpview.py) composed far to
// near into view_buf (20x12 tile indices). The game defines view_cell() and links view.c.
#define VIEW_W 20
#define VIEW_H 12
enum { VIEW_FREE, VIEW_WALL, VIEW_DOOR, VIEW_LOCKED, VIEW_DOWN, VIEW_UP };
extern uint8_t view_buf[], view_bank;           // view_bank = BANK(view) if banked, else 0
extern const uint8_t *view_map, *view_class;    // 16x16 cell types + type -> VIEW_* (asm reads them)
extern const int8_t view_dx[4], view_dy[4];     // facing 0 N, 1 E, 2 S, 3 W
uint8_t view_cell(uint8_t x, uint8_t y);        // provided by the game (off the map = VIEW_WALL)
void view_compose(uint8_t x, uint8_t y, uint8_t f);      // asm core (gbe_view.s)
void view_compose_c(uint8_t x, uint8_t y, uint8_t f);    // C reference
void view_compose_bg(void);                     // background piece only (map margins)
void view_mark_seen(uint8_t *seen);             // after view_compose: 16x16 bit map of seen cells
void view_blit(const uint8_t *piece);           // asm
void view_blit_c(const uint8_t *piece);         // C reference
```

## Notas de implementación

`gbe_view.c`:

> gbe: first-person grid view (dungeon crawlers). The view (20x12 tiles) is a mosaic of tile
> indices: pieces of res/view.pcs (harness/fpview.py: format, geometry, reference compositor)
> copied far to near into view_buf. Nothing is generated per pixel.
> 
> The game provides:
>   view_map = its 16x16 map of cell types (y * 16 + x) and view_class = a table cell type ->
>   VIEW_FREE / VIEW_WALL / VIEW_DOOR / VIEW_LOCKED / VIEW_DOWN / VIEW_UP (off the map: VIEW_WALL),
>   uint8_t view_cell(uint8_t x, uint8_t y) with the same answer (used by the C reference)
>   view_bank = BANK(view) if "view" is in banked_res (0 = not banked)
> and links the generated view.c (view_pcs, view_piece) from res/view.pcs.
> Same painting rules as fpview.pieces_for(); tests compare the ROM's view_buf with fpview.compose().

`gbe_view.s`:

> gbe (view) - piece blitter for the first-person view. C reference: view_blit_c (gbe_view.c),
> checked by gbe_selftest.c (GBE_SELFTEST_VIEW) on every piece of the game's view.pcs.
