# `gbe_spr` — gbe_spr.c

**Qué hace:** OAM groups with fixed ranges (lower range = priority); each group starts half a group further on odd frames, so a sprite dropped on a >10 line is drawn the next frame

**Lo que pone el juego:** `spr_rot` cycling through 2 x a common multiple of the slot counts (< 64)

**Origen y cifras:** shmup: ~300 T per drawn object

**Ficheros:** `harness/common/src/gbe_spr.c` — en game.json: `"common_src": ["gbe_spr.c"]`

**Juegos que lo usan:** `games/gbe_lab`, `games/shmup`

## Nombres

| Nombre | Comentario |
|---|---|
| `spr_rot` | OAM manager: one call per priority group (lower OAM slots = higher priority on the DMG). spr_rot: advance once per frame, cycling through 2 x a common multiple of the groups' slot counts (< 64;... |
| `spr_group` | size 1: one sprite per object; size 2: 16x16 (tile, tile + 2). pool_n >= 1. |
| `spr_group_c` |  |

## Cabecera (`gbe.h`)

```c
// OAM manager: one call per priority group (lower OAM slots = higher priority on the DMG).
// spr_rot: advance once per frame, cycling through 2 x a common multiple of the groups' slot
// counts (< 64; e.g. 48 for groups of 12, 6, 8, 2 slots): consecutive frames start each group
// half a group apart, so a sprite dropped on a crowded line is drawn the next frame.
extern uint8_t spr_rot;
// size 1: one sprite per object; size 2: 16x16 (tile, tile + 2). pool_n >= 1.
void spr_group(uint8_t oam_first, uint8_t oam_n, uint8_t pool_first, uint8_t pool_n, uint8_t size);
void spr_group_c(uint8_t oam_first, uint8_t oam_n, uint8_t pool_first, uint8_t pool_n, uint8_t size);
```

## Notas de implementación

`gbe_spr.c`:

> gbe: OAM manager for many objects - priority groups with fixed OAM ranges.
> Lower OAM indices win on the DMG when a line has more than 10 sprites, so groups written to
> smaller OAM indices have priority. Inside a group the first OAM slot rotates every frame
> (spr_rot): objects on a crowded line take turns being dropped (flicker) instead of always
> losing the same ones. Size the group's OAM range >= live objects x size.
> spr_group is asm (gbe_pool.s); spr_group_c is the selftest reference.
> Requires shadow_OAM page-aligned (GBDK places it at 0xC000).
