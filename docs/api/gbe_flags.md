# `gbe_flags` — gbe_flags.c

**Qué hace:** story flags (bitset, 1024 by default) and 16 byte variables, ids from `res/scripts/flags.txt` / `vars.txt`

**Lo que pone el juego:** `GBE_FLAG_BYTES`

**Origen y cifras:** world_lab

**Ficheros:** `harness/common/src/gbe_flags.c` — en game.json: `"common_src": ["gbe_flags.c"]`

**Juegos que lo usan:** `games/faro`, `games/world_lab`

## Nombres

| Nombre | Comentario |
|---|---|
| `GBE_FLAG_BYTES` | 1024 flags |
| `flagsGBE_FLAG_BYTES` |  |
| `vars` |  |
| `flag_get` |  |
| `flag_set` |  |
| `flag_clr` |  |

## Cabecera (`gbe.h`)

```c
// Story flags (bitset) and 16 byte variables; ids F_* / V_* from res/scripts (script_ids.h).
#ifndef GBE_FLAG_BYTES
#define GBE_FLAG_BYTES 128               // 1024 flags
#endif
extern uint8_t flags[GBE_FLAG_BYTES], vars[16];
uint8_t flag_get(uint16_t f);
void flag_set(uint16_t f);
void flag_clr(uint16_t f);
```

## Notas de implementación

`gbe_flags.c`:

> gbe: story flags (bitset) and small variables, saved with the game. Ids come from
> res/scripts/flags.txt / vars.txt (harness/script.py -> script_ids.h: F_*, V_*).
