# `bcd` — bcd.s

**Qué hace:** `bcd_add3`: packed BCD add with `daa`, saturating at 999999

**Lo que pone el juego:** -

**Origen y cifras:** tetris: ~100 T vs ~2000 T in C

**Ficheros:** `harness/common/src/bcd.s` — en game.json: `"common_src": ["bcd.s"]`

**Juegos que lo usan:** `games/platformer`, `games/shmup`, `games/tetris`

## Nombres

| Nombre | Comentario |
|---|---|
| `bcd_add3` | dst += src, 3 bytes of packed BCD, little-endian (byte 0 = lowest 2 digits), saturates at 999999 |

## Cabecera (`bcd.h`)

```c
// Shared packed BCD helpers (harness/common/src/bcd.s). Use from a game with
// "common_src": ["bcd.s"] in game.json and #include "bcd.h".
#include <stdint.h>

// dst += src, 3 bytes of packed BCD, little-endian (byte 0 = lowest 2 digits), saturates at 999999
void bcd_add3(uint8_t *dst, const uint8_t *src);
```

## Notas de implementación

`bcd.s`:

> Shared (harness/common/src). Packed BCD score arithmetic (2 digits per byte, little-endian: byte 0 = lowest digits).
> 
> void bcd_add3(uint8_t *dst, const uint8_t *src)
>   dst in DE, src in BC (__sdcccall(1)). dst += src, saturating at 999999. Clobbers AF HL DE.
>   16-bit inc and ld do not touch flags, so the carry survives between bytes for adc/daa.
> 
> Cost: ~100 T, vs ~2000 T for the C digit-per-byte loop it replaces.
