# `gbe_aim` — gbe_aim.c

**Qué hace:** 32 directions, speed tables `aim_vx/aim_vy[spd*32+dir]`, `aim_dir(dx, dy)` (error <= 1, tested vs atan2), asm `fire` / C `fire_fan` into a pool range

**Lo que pone el juego:** `fire_first/n/t/tile/prop`

**Origen y cifras:** shmup: fire 2000 -> ~960 T

**Ficheros:** `harness/common/src/gbe_aim.c` — en game.json: `"common_src": ["gbe_aim.c"]`

**Juegos que lo usan:** `games/shmup`

## Nombres

| Nombre | Comentario |
|---|---|
| `aim_vx` | Directions: 32 (11.25 deg), dir 0 = down, clockwise on screen: 8 = left, 16 = up, 24 = right. aim_vx/aim_vy[spd * 32 + dir]: 8.8 velocity. Speeds: 0 = 1.0, 1 = 1.25, 2 = 1.5, 3 = 2.0 px/f. |
| `aim_vy` | (ver `aim_vx`) |
| `dir_vx` | speed 0 = the first 32 entries |
| `dir_vy` |  |
| `aim_dir` | direction of (dx, dy) (target - origin); error <= 1 |
| `fire_first` | Bullets go to the pool range fire_first..+fire_n with type fire_t, tile fire_tile, prop fire_prop. x, y = OAM position of the new bullet. Return the slot (0xFF if the range is full). |
| `fire_n` | (ver `fire_first`) |
| `fire_t` | (ver `fire_first`) |
| `fire_tile` | (ver `fire_first`) |
| `fire_prop` | (ver `fire_first`) |
| `fire` | asm (gbe_aim.s) |
| `fire_c` | C reference |
| `fire_fan` | n bullets at dir + step * (k - (n - 1) / 2), k = 0..n-1; returns how many went out |

## Cabecera (`gbe.h`)

```c
// Directions: 32 (11.25 deg), dir 0 = down, clockwise on screen: 8 = left, 16 = up, 24 = right.
// aim_vx/aim_vy[spd * 32 + dir]: 8.8 velocity. Speeds: 0 = 1.0, 1 = 1.25, 2 = 1.5, 3 = 2.0 px/f.
extern const int16_t aim_vx[128], aim_vy[128];
#define dir_vx aim_vx                   // speed 0 = the first 32 entries
#define dir_vy aim_vy
uint8_t aim_dir(int8_t dx, int8_t dy);  // direction of (dx, dy) (target - origin); error <= 1
// Bullets go to the pool range fire_first..+fire_n with type fire_t, tile fire_tile, prop fire_prop.
// x, y = OAM position of the new bullet. Return the slot (0xFF if the range is full).
extern uint8_t fire_first, fire_n, fire_t, fire_tile, fire_prop;
uint8_t fire(uint8_t x, uint8_t y, uint8_t dir, uint8_t spd);     // asm (gbe_aim.s)
uint8_t fire_c(uint8_t x, uint8_t y, uint8_t dir, uint8_t spd);   // C reference
// n bullets at dir + step * (k - (n - 1) / 2), k = 0..n-1; returns how many went out
uint8_t fire_fan(uint8_t x, uint8_t y, uint8_t dir, uint8_t n, uint8_t step, uint8_t spd);
```

## Notas de implementación

`gbe_aim.c`:

> gbe: aiming and bullet patterns (32 directions). Tables generated with Python (math.sin/cos/
> atan2); dir 0 = down, clockwise on screen (8 = left, 16 = up, 24 = right):
>   vx = -sin(dir * 11.25 deg), vy = cos(dir * 11.25 deg), 8.8 fixed point.
> aim_vx/aim_vy[spd * 32 + dir]: speeds 0 = 1.0, 1 = 1.25 (v + v>>2), 2 = 1.5 (v + v>>1), 3 = 2.0.
> fire() is asm (gbe_aim.s, ~2000 T in C per bullet); fire_c is the selftest reference.
