# `gbe_pool` — gbe_pool.c / .s

**Qué hace:** many-object pools (bullets, shots, enemies) in 8-bit OAM coords: `pool_alloc`, asm `pool_move` (free on exit), asm `hit_first` (box vs range, one compare per axis)

**Lo que pone el juego:** `GBE_POOL_MAX`

**Origen y cifras:** shmup: move ~250 T, hit ~100 T per object

**Ficheros:** `harness/common/src/gbe_pool.c`, `harness/common/src/gbe_pool.s` — en game.json: `"common_src": ["gbe_pool.c", "gbe_pool.s"]`

**Juegos que lo usan:** `games/gbe_lab`, `games/shmup`

## Nombres

| Nombre | Comentario |
|---|---|
| `pool_obj_t` | Object pools in 8-bit OAM space (X = screen x + 8, Y = screen y + 16). GBE_POOL_MAX records of 16 bytes (the asm walks records with ld a,(hl+); field offsets are fixed, see gbe_pool.s). Moving... |
| `pool` |  |
| `pool_alloc` | first free slot of the range, 0xFF if full |
| `pool_clear` |  |
| `pool_move` | asm (gbe_pool.s), n >= 1 |
| `pool_move_c` |  |
| `hit_qx` | Collisions: set the query box and the pool object box, then hit_first(first, n) returns the first live object of the range that overlaps, or 0xFF. 8-bit circular overlap (one compare per axis):... |
| `hit_qy` | (ver `hit_qx`) |
| `hit_qw` | (ver `hit_qx`) |
| `hit_qh` | (ver `hit_qx`) |
| `hit_ox` | (ver `hit_qx`) |
| `hit_oy` | (ver `hit_qx`) |
| `hit_ow` | (ver `hit_qx`) |
| `hit_oh` | (ver `hit_qx`) |
| `hit_first` | asm, n >= 1 |
| `hit_first_c` |  |

## Cabecera (`gbe.h`)

```c
// Object pools in 8-bit OAM space (X = screen x + 8, Y = screen y + 16). GBE_POOL_MAX records of
// 16 bytes (the asm walks records with ld a,(hl+); field offsets are fixed, see gbe_pool.s).
// Moving frees objects that leave the screen (X >= 168 or Y >= 176, any side).
typedef struct {
    uint8_t t;              // +0  type, 0 = free
    uint8_t x, xs;          // +1  OAM x, sub-pixel
    uint8_t y, ys;          // +3  OAM y, sub-pixel
    int16_t vx, vy;         // +5  8.8 px/frame
    uint8_t s, tm, aux;     // +9  game use (state, timer, anything)
    uint8_t tile, prop;     // +12 what gbe_spr draws
    uint8_t aux2, pad;      // +14
} pool_obj_t;
extern pool_obj_t pool[];
uint8_t pool_alloc(uint8_t first, uint8_t n);      // first free slot of the range, 0xFF if full
void pool_clear(uint8_t first, uint8_t n);
void pool_move(uint8_t first, uint8_t n);          // asm (gbe_pool.s), n >= 1
void pool_move_c(uint8_t first, uint8_t n);
// Collisions: set the query box and the pool object box, then hit_first(first, n) returns the
// first live object of the range that overlaps, or 0xFF. 8-bit circular overlap (one compare per
// axis): fine for OAM coordinates; qw + ow and qh + oh must be <= 256.
extern uint8_t hit_qx, hit_qy, hit_qw, hit_qh, hit_ox, hit_oy, hit_ow, hit_oh;
uint8_t hit_first(uint8_t first, uint8_t n);       // asm, n >= 1
uint8_t hit_first_c(uint8_t first, uint8_t n);
```

## Notas de implementación

`gbe_pool.c`:

> gbe: object pools in 8-bit OAM space and collisions. Array of 16-byte records (not struct of
> arrays): on the SM83 the asm walks a record with ld a,(hl+) instead of re-deriving one
> address per field (measured in games/gbe_lab: struct-of-arrays asm cost ~350 T per moved
> object). The asm is in gbe_pool.s; the *_c functions are the selftest references.
> 
> Coordinates are OAM coordinates: X = screen x + 8, Y = screen y + 16. Visible area: X 0..167,
> Y 0..159. An object whose X >= 168 or Y >= 176 after moving is freed (left/top exits wrap to
> >= 168 / >= 176 too, so one compare per axis covers every side).

`gbe_pool.s`:

> gbe (pool) - shared engine asm: object pools in 8-bit OAM space, collisions, OAM groups.
> Records of 16 bytes (pool_obj_t in gbe.h), walked with pointers. Field offsets:
>   +0 t  +1 x  +2 xs  +3 y  +4 ys  +5/+6 vx (lo/hi)  +7/+8 vy  +9 s  +10 tm  +11 aux
>   +12 tile  +13 prop  +14 aux2  +15 pad
> C references: gbe_pool.c / gbe_spr.c (*_c), checked by gbe_selftest.c (GBE_SELFTEST_POOL).
> History (games/gbe_lab, shmup peak with 26 objects): C ~1000 T per moved object; asm over
> separate arrays ~350 T (one address per field); these record walkers are the current version.
