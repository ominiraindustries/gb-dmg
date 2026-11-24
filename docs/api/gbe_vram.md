# `gbe_vram` — gbe_vram.s

**Qué hace:** `vram_col16` (16 tiles down a BG column), `vram_mt4_list` (queued 2x2 metatiles; used by gbe_map and gbe_vmap)

**Lo que pone el juego:** -

**Origen y cifras:** platformer: 32 T/tile; metatile 600 -> 100 T

**Ficheros:** `harness/common/src/gbe_vram.s` — en game.json: `"common_src": ["gbe_vram.s"]`

**Juegos que lo usan:** `games/dungeon`, `games/faro`, `games/mazmorra`, `games/platformer`, `games/shmup`, `games/world_lab`

## Nombres

| Nombre | Comentario |
|---|---|
| `vram_col16` | 16 tiles down a BG map column (stride 32) |
| `vram_mt4_list` | n metatiles (n >= 1) |
| `vram_row20` | 20 consecutive BG map bytes, 24 T/tile |

## Cabecera (`gbe.h`)

```c
void vram_col16(uint8_t *dst, const uint8_t *src);  // 16 tiles down a BG map column (stride 32)
void vram_mt4_list(uint8_t **dst, const uint8_t *tiles, uint8_t n);   // n metatiles (n >= 1)
void vram_row20(uint8_t *dst, const uint8_t *src);  // 20 consecutive BG map bytes, 24 T/tile
```

## Notas de implementación

`gbe_vram.s`:

> gbe (vram) - shared engine asm (harness/common/src). Measured and equivalence-tested in
> games/platformer. Call VRAM writers only in VBlank or with the LCD off.
