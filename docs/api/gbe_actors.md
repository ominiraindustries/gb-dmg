# `gbe_actors` — gbe_actors.c / .s

**Qué hace:** actor arrays (struct of arrays), `act_spawn`, asm `act_move`

**Lo que pone el juego:** `GBE_ACT_MAX`

**Origen y cifras:** platformer: 240 T vs 1500 T

**Ficheros:** `harness/common/src/gbe_actors.c`, `harness/common/src/gbe_actors.s` — en game.json: `"common_src": ["gbe_actors.c", "gbe_actors.s"]`

**Juegos que lo usan:** `games/platformer`

## Nombres

| Nombre | Comentario |
|---|---|
| `act_type` | Struct of arrays; slot ranges are the game's business. Positions 8.8 fixed point: x = act_x (u16 px) : act_xs (sub), y = act_y (u8 px) : act_ys (sub). |
| `act_xs` | (ver `act_type`) |
| `act_y` | (ver `act_type`) |
| `act_ys` | (ver `act_type`) |
| `act_state` | (ver `act_type`) |
| `act_timer` | (ver `act_type`) |
| `act_flip` | (ver `act_type`) |
| `act_x` |  |
| `act_vx` |  |
| `act_vy` |  |
| `act_spawn` | zeroes the rest |
| `act_move` | asm: position += velocity (~240 T; C reference act_move_c) |
| `act_move_c` |  |

## Cabecera (`gbe.h`)

```c
// Struct of arrays; slot ranges are the game's business. Positions 8.8 fixed point:
// x = act_x (u16 px) : act_xs (sub), y = act_y (u8 px) : act_ys (sub).
extern uint8_t act_type[], act_xs[], act_y[], act_ys[], act_state[], act_timer[], act_flip[];
extern uint16_t act_x[];
extern int16_t act_vx[], act_vy[];
void act_spawn(uint8_t i, uint8_t type, uint16_t x, uint8_t y);   // zeroes the rest
void act_move(uint8_t i);      // asm: position += velocity (~240 T; C reference act_move_c)
void act_move_c(uint8_t i);
```

## Notas de implementación

`gbe_actors.c`:

> gbe: actor arrays (struct of arrays). Sizes from gbe_config.h (GBE_ACT_MAX).

`gbe_actors.s`:

> gbe (actors) - shared engine asm (harness/common/src). Measured and equivalence-tested in
> games/platformer. Call VRAM writers only in VBlank or with the LCD off.
