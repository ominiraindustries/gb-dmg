# `gbe_list` — gbe_list.c

**Qué hace:** scrolling list: n items, k visible rows, cursor, repeat, more-arrows; rows rendered by a game callback (same bank)

**Lo que pone el juego:** `list_row` callback, tiles

**Origen y cifras:** world_lab: scroll + wrap + choose

**Ficheros:** `harness/common/src/gbe_list.c` — en game.json: `"common_src": ["gbe_list.c"]`

**Juegos que lo usan:** `games/faro`, `games/happyvalley`, `games/world_lab`

## Nombres

| Nombre | Comentario |
|---|---|
| `list_n` | Scrolling list: n items, k visible rows; the game renders a row with list_row(item, buf) (list_w tiles; buf[0] is the cursor column). Set list_cursor/blank/arrow tiles and list_up_at/down_at. Call... |
| `list_sel` | (ver `list_n`) |
| `list_top` | (ver `list_n`) |
| `list_k` | (ver `list_n`) |
| `list_w` | (ver `list_n`) |
| `list_up_at` |  |
| `list_down_at` |  |
| `list_cursor` |  |
| `list_blank` |  |
| `list_arrow_up` |  |
| `list_arrow_down` |  |
| `list_border` |  |
| `list_open` |  |
| `void` |  |
| `list_redraw` | after the items changed (n may shrink) |
| `list_update` |  |

## Cabecera (`gbe.h`)

```c
// Scrolling list: n items, k visible rows; the game renders a row with list_row(item, buf) (list_w
// tiles; buf[0] is the cursor column). Set list_cursor/blank/arrow tiles and list_up_at/down_at.
// Call it from the bank that holds the row callback. list_update(): MENU_NONE / index / MENU_BACK.
extern uint8_t list_n, list_sel, list_top, list_k, list_w;
extern uint8_t *list_up_at, *list_down_at;
extern uint8_t list_cursor, list_blank, list_arrow_up, list_arrow_down, list_border;
void list_open(uint8_t n, uint8_t sel, uint8_t k, uint8_t *dst0, uint8_t stride, uint8_t w,
               void (*row)(uint8_t item, uint8_t *buf));
void list_redraw(void);                 // after the items changed (n may shrink)
uint8_t list_update(void);
```

## Notas de implementación

`gbe_list.c`:

> gbe: scrolling list (inventories, shops, the bestiary) - n items, k visible rows, cursor tile,
> hold-to-repeat (16 f, then every 6 f), 'more above / below' arrows, A = choose, B = back.
> The game renders rows: list_row(item, buf) fills list_w tiles (called for the visible rows when
> the list scrolls; items >= n get blanks). Rows and arrows go through gbe_vq.
> The callback is a plain near pointer: call list_open / list_update from the same ROM bank as
> the callback (or from bank 0 with the callback in bank 0) - gbe_list never switches banks.
