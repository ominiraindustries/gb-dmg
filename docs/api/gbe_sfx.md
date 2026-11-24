# `gbe_sfx` — gbe_sfx.c

**Qué hace:** register SFX with per-channel priority (`sfx` in asm; `sfx_c` documents it)

**Lo que pone el juego:** `sfx_table[]`

**Origen y cifras:** shmup: ~1000 -> ~300 T

**Ficheros:** `harness/common/src/gbe_sfx.c` — en game.json: `"common_src": ["gbe_sfx.c"]`

**Juegos que lo usan:** `games/dungeon`, `games/faro`, `games/happyvalley`, `games/mazmorra`, `games/platformer`, `games/shmup`, `games/world_lab`

## Nombres

| Nombre | Comentario |
|---|---|
| `sfx_t` | Sound effects by registers with per-channel priority. The game defines the table: const sfx_t sfx_table[] = { [SFX_JUMP] = { 1, 1, 12, { NR10, NR11, NR12, NR13, NR14 } }, ... }; |
| `sfx_table` |  |
| `sound_init` |  |
| `sfx` |  |
| `sound_update` | once per frame |

## Cabecera (`gbe.h`)

```c
// Sound effects by registers with per-channel priority. The game defines the table:
//   const sfx_t sfx_table[] = { [SFX_JUMP] = { 1, 1, 12, { NR10, NR11, NR12, NR13, NR14 } }, ... };
typedef struct {
    uint8_t ch;         // 1, 2 or 4
    uint8_t prio;       // higher or equal replaces the playing effect on that channel
    uint8_t frames;     // how long the channel stays reserved
    uint8_t r[5];       // NR10-NR14 for ch1; NRx1-NRx4 in r[1..4] for ch2 / ch4
} sfx_t;
extern const sfx_t sfx_table[];
void sound_init(void);
void sfx(uint8_t id);
void sound_update(void);      // once per frame
```

## Notas de implementación

`gbe_sfx.c`:

> gbe: sound effects by registers with per-channel priority (table provided by the game)
