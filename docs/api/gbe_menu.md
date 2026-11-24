# `gbe_menu` — gbe_menu.c

**Qué hace:** vertical menu: cursor tile, repeat 16/6 f, wrap, disabled options, A / B

**Lo que pone el juego:** -

**Origen y cifras:** dungeon (M1b)

**Ficheros:** `harness/common/src/gbe_menu.c` — en game.json: `"common_src": ["gbe_menu.c"]`

**Juegos que lo usan:** `games/dungeon`, `games/faro`, `games/happyvalley`, `games/world_lab`

## Nombres

| Nombre | Comentario |
|---|---|
| `MENU_NONE` | Vertical menu: cursor tile through gbe_vq, repeat 16/6 f, wrap, disabled options skipped. |
| `MENU_BACK` |  |
| `menu_n` |  |
| `menu_sel` |  |
| `menu_disabled` |  |
| `menu_open` |  |
| `menu_update` | MENU_NONE / index chosen with A / MENU_BACK (B) |

## Cabecera (`gbe.h`)

```c
// Vertical menu: cursor tile through gbe_vq, repeat 16/6 f, wrap, disabled options skipped.
#define MENU_NONE 0xFF
#define MENU_BACK 0xFE
extern uint8_t menu_n, menu_sel, menu_disabled;
void menu_open(uint8_t n, uint8_t sel, uint8_t disabled, uint8_t *cursor0, uint8_t stride,
               uint8_t cursor_tile, uint8_t blank_tile) GBE_FAR;
uint8_t menu_update(void) GBE_FAR;                      // MENU_NONE / index chosen with A / MENU_BACK (B)
```

## Notas de implementación

`gbe_menu.c`:

> gbe: vertical menu with a cursor tile, hold-to-repeat (16 f, then every 6 f), wrap-around,
> disabled options skipped, A = choose, B = back. The game draws the box and the texts (text
> helpers, or a .screen map); the menu only moves the cursor through the VRAM queue.
