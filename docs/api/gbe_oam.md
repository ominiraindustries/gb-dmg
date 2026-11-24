# `gbe_oam` — gbe_oam.c

**Qué hace:** `oam16`/`oam8`: direct shadow OAM writes

**Lo que pone el juego:** -

**Origen y cifras:** platformer: ~3x cheaper

**Ficheros:** `harness/common/src/gbe_oam.c` — en game.json: `"common_src": ["gbe_oam.c"]`

**Juegos que lo usan:** `games/dungeon`, `games/faro`, `games/gbe_lab`, `games/happyvalley`, `games/mazmorra`, `games/platformer`, `games/shmup`, `games/world_lab`

## Nombres

| Nombre | Comentario |
|---|---|
| `oam16` | Direct shadow OAM writes (~3x cheaper than set_sprite_tile/prop + move_sprite). 16x16 objects in 8x16 sprite mode = 2 sprites: tiles (t, t+2); S_FLIPX swaps the halves. |
| `oam8` |  |

## Cabecera (`gbe.h`)

```c
// Direct shadow OAM writes (~3x cheaper than set_sprite_tile/prop + move_sprite).
// 16x16 objects in 8x16 sprite mode = 2 sprites: tiles (t, t+2); S_FLIPX swaps the halves.
void oam16(uint8_t nb, uint8_t ox, uint8_t y, uint8_t tile, uint8_t prop);
void oam8(uint8_t nb, uint8_t ox, uint8_t y, uint8_t tile, uint8_t prop);
```

## Notas de implementación

`gbe_oam.c`:

> gbe: direct shadow OAM writes
