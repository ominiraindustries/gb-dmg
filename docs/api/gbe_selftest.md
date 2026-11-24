# `gbe_selftest` — gbe_selftest.c

**Qué hace:** asm-vs-C equivalence of all the above, run in the ROM

**Lo que pone el juego:** call `gbe_selftest()` when `gbe_eq_request`

**Origen y cifras:** test: `gb.selftest()`

**Ficheros:** `harness/common/src/gbe_selftest.c` — en game.json: `"common_src": ["gbe_selftest.c"]`

**Juegos que lo usan:** `games/dungeon`, `games/faro`, `games/gbe_lab`, `games/mazmorra`, `games/platformer`, `games/shmup`, `games/world_lab`

## Nombres

| Nombre | Comentario |
|---|---|
| `gbe_eq_request` | Equivalence of every asm routine with its C reference (gb-asm procedure). Tests call gb.selftest() (sets gbe_eq_request; the game calls gbe_selftest()). Which modules are checked comes from... |
| `gbe_eq_done` | (ver `gbe_eq_request`) |
| `gbe_eq_mismatch` |  |
| `gbe_eq_count` |  |
| `GBE_SELFTEST_ATTR` |  |
| `gbe_selftest` |  |

## Cabecera (`gbe.h`)

```c
// Equivalence of every asm routine with its C reference (gb-asm procedure). Tests call
// gb.selftest() (sets gbe_eq_request; the game calls gbe_selftest()). Which modules are checked
// comes from gbe_config.h: GBE_SELFTEST_MAP (needs a loaded map), GBE_SELFTEST_ACTORS,
// GBE_SELFTEST_POOL (uses the last 8 pool slots as scratch and the last 10 OAM entries),
// GBE_SELFTEST_VMAP <metatile count of mt_tiles>, GBE_SELFTEST_AIM (needs _POOL's scratch),
// GBE_SELFTEST_VIEW (every piece of the game's view.pcs).
extern uint8_t gbe_eq_request, gbe_eq_done;
extern uint16_t gbe_eq_mismatch, gbe_eq_count;
#ifdef GBE_SELFTEST_BANKED
#define GBE_SELFTEST_ATTR BANKED
#else
#define GBE_SELFTEST_ATTR
#endif
void gbe_selftest(void) GBE_SELFTEST_ATTR;
```

## Notas de implementación

`gbe_selftest.c`:

> gbe: equivalence of the engine asm with its C references, run inside the ROM on request.
> Python side: harness/gbtest.py GB.selftest(). Modules are enabled in the game's gbe_config.h.
> GBE_SELFTEST_BANKED in gbe_config.h puts this file (and the C references of gbe_world/gbe_gact
> it holds) in a switchable bank: needs -autobank (games/world_lab: bank 0 was 93 % full).
