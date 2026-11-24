# `gbe_tiles` — gbe_tiles.c

**Qué hace:** tile DATA queue: runs of tiles from any bank, staged to WRAM in the logic, copied in VBlank with an unrolled asm copy (`tile_copy16`, ~330 T/tile), `tiles_budget` per VBlank (2)

**Lo que pone el juego:** -

**Origen y cifras:** world_lab: 4 tiles with GBDK memcpy overran VBlank (vram_late caught it)

**Ficheros:** `harness/common/src/gbe_tiles.c` — en game.json: `"common_src": ["gbe_tiles.c"]`

**Juegos que lo usan:** `games/faro`, `games/happyvalley`, `games/mazmorra`, `games/world_lab`

## Nombres

| Nombre | Comentario |
|---|---|
| `tiles_budget` | tiles_budget <= 4 (TQ_STAGE: larger is clamped) |
| `tiles_lost` | (ver `tiles_budget`) |
| `tq_staged` | tiles staged for the next tiles_draw_vram() |
| `tiles_push` |  |
| `tiles_pending` |  |
| `tiles_prepare` |  |
| `tiles_draw_vram` |  |

## Cabecera (`gbe.h`)

```c
// Tile DATA queue: tiles_push(VRAM address, bank, src, n tiles); tiles_prepare() in the logic
// (copies <= tiles_budget tiles to WRAM with the bank switched), tiles_draw_vram() in VBlank.
extern uint8_t tiles_budget, tiles_lost;   // tiles_budget <= 4 (TQ_STAGE: larger is clamped)
extern uint8_t tq_staged;                  // tiles staged for the next tiles_draw_vram()
uint8_t tiles_push(uint8_t *dst, uint8_t bank, const uint8_t *src, uint8_t n);
uint8_t tiles_pending(void);
void tiles_prepare(void);
void tiles_draw_vram(void);
```

## Notas de implementación

`gbe_tiles.c`:

> gbe: tile DATA queue (16 bytes per tile) - animated BG tiles (water, flowers), sprite frames
> swapped in (bike), a creature's tiles loaded when it appears. The game pushes runs of tiles from
> any bank; tiles_prepare() (logic) copies up to tiles_budget tiles to a WRAM staging buffer with
> the bank switched, tiles_draw_vram() (VBlank) only copies WRAM -> VRAM (tile_copy16 in
> gbe_tiles.s, ~330 T per tile). Runs longer than the budget continue next frame.
