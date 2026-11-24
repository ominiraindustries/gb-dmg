# `gbe_util` — gbe_util.s

**Ficheros:** `harness/common/src/gbe_util.s` — en game.json: `"common_src": ["gbe_util.s"]`

**Juegos que lo usan:** `games/happyvalley`

## Nombres

| Nombre | Comentario |
|---|---|
| `gbe_row32` | r * 32 in 16 bits: SDCC sometimes compiles (uint16_t)r << 5 of an u8 local in 8 bits (BG map rows >= 8 wrap onto 0-7). Use it for map row offsets: (uint8_t *)0x9800 + gbe_row32(r) + c. |

## Cabecera (`gbe.h`)

```c
// r * 32 in 16 bits: SDCC sometimes compiles (uint16_t)r << 5 of an u8 local in 8 bits (BG map rows
// >= 8 wrap onto 0-7). Use it for map row offsets: (uint8_t *)0x9800 + gbe_row32(r) + c.
uint16_t gbe_row32(uint8_t r) __preserves_regs(d, e, h, l);
```

## Notas de implementación

`gbe_util.s`:

> gbe: small helpers SDCC gets wrong. SDCC 4.5 sometimes compiles (uint16_t)r << 5 (r an u8 local) in
> 8 bits (swap / rlca / and 0xE0: rows >= 8 of a BG map wrap onto rows 0-7; seen in happyvalley's
> race view and mazmorra, see the gbdk skill gotchas). Use these for map row offsets.
> uint16_t gbe_row32(uint8_t r)   BC = r * 32
