# `gbe_rng` — gbe_rng.c

**Qué hace:** xorshift16 `rng_next` / `rng_range`; `gb.rng_next(state)` predicts it in tests

**Lo que pone el juego:** seed `rng_state`

**Origen y cifras:** dungeon

**Ficheros:** `harness/common/src/gbe_rng.c` — en game.json: `"common_src": ["gbe_rng.c"]`

**Juegos que lo usan:** `games/dungeon`, `games/faro`, `games/happyvalley`, `games/mazmorra`, `games/world_lab`

## Nombres

| Nombre | Comentario |
|---|---|
| `rng_state` | 16-bit xorshift; tests predict it (gbtest.rng_next). Seed rng_state from DIV + frames on a key press. |
| `rng_next` |  |
| `rng_range` | 0 .. n-1 |

## Cabecera (`gbe.h`)

```c
// 16-bit xorshift; tests predict it (gbtest.rng_next). Seed rng_state from DIV + frames on a key press.
extern uint16_t rng_state;
uint8_t rng_next(void);
uint8_t rng_range(uint8_t n);          // 0 .. n-1
```

## Notas de implementación

`gbe_rng.c`:

> gbe: 16-bit xorshift (7, 9, 8), one global state. rng_next() returns the low 8 bits.
> harness/gbtest.py rng_next() is the same algorithm: tests predict combat rolls from rng_state.
