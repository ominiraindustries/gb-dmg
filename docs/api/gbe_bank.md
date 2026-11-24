# `gbe_bank` — gbe_bank.c

**Qué hace:** read banked const data from any code (bank 0, restores the bank): `bank_set_bkg_data`, `bank_set_sprite_data`, `bank_memcpy`, `bank_read8`

**Lo que pone el juego:** game.json `"banked_res"` + MBC flags

**Origen y cifras:** gbe_lab: 3 banked tilesets loaded and checked byte by byte

**Ficheros:** `harness/common/src/gbe_bank.c` — en game.json: `"common_src": ["gbe_bank.c"]`

**Juegos que lo usan:** `games/dungeon`, `games/faro`, `games/gbe_lab`, `games/happyvalley`, `games/mazmorra`, `games/world_lab`

## Nombres

| Nombre | Comentario |
|---|---|
| `bank_set_bkg_data` | Banked assets: game.json "banked_res": ["walls", "level1"] puts the generated files in switchable banks (BANKREF(<stem>)); load them with BANK(<stem>) from any code: bank_set_bkg_data(BANK(walls),... |
| `bank_set_sprite_data` |  |
| `bank_memcpy` |  |
| `bank_read8` |  |

## Cabecera (`gbe.h`)

```c
// Banked assets: game.json "banked_res": ["walls", "level1"] puts the generated files in switchable
// banks (BANKREF(<stem>)); load them with BANK(<stem>) from any code:
//   bank_set_bkg_data(BANK(walls), first, WALLS_COUNT, walls_tiles);
void bank_set_bkg_data(uint8_t bank, uint8_t first, uint8_t n, const uint8_t *data) NONBANKED;
void bank_set_sprite_data(uint8_t bank, uint8_t first, uint8_t n, const uint8_t *data) NONBANKED;
void bank_memcpy(uint8_t bank, void *dst, const void *src, uint16_t n) NONBANKED;
uint8_t bank_read8(uint8_t bank, const uint8_t *p) NONBANKED;
// Index tables of generated data (script_index, world_maps): { &__bank_<sym>, address } - the
// bank is a link-time address constant, so it fits a static initializer; read it with
// (uint8_t)(uint16_t)ref.bank.
typedef struct { const void *bank; const void *ptr; } gbe_ref_t;
```

## Notas de implementación

`gbe_bank.c`:

> gbe: reading data from switchable ROM banks (assets listed in game.json "banked_res").
> These functions live in bank 0 (gbe files have no #pragma bank) and restore the caller's bank,
> so any code may call them. Banked code must never SWITCH_ROM itself (it unmaps its own code).
