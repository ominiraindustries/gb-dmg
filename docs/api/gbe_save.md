# `gbe_save` — gbe_save.c

**Qué hace:** SRAM save with two alternating slots (signature, version, sequence, length, Fletcher-16; signature written last): a torn store keeps the previous save

**Lo que pone el juego:** MBC with RAM+battery (`-Wm-yt0x1B -Wm-ya1`)

**Origen y cifras:** gbe_lab: power cycle, flipped bit, torn newest slot (`GB(rom, ram=g.power_off())`)

**Ficheros:** `harness/common/src/gbe_save.c` — en game.json: `"common_src": ["gbe_save.c"]`

**Juegos que lo usan:** `games/dungeon`, `games/faro`, `games/gbe_lab`, `games/happyvalley`, `games/mazmorra`

## Nombres

| Nombre | Comentario |
|---|---|
| `save_slot` | Save in cartridge SRAM (needs an MBC with RAM + battery: -Wm-yt0x1B -Wm-ya1): two alternating slots with signature, version, sequence, length and checksum; a torn write keeps the previous save.... |
| `save_seq` | (ver `save_slot`) |
| `save_load` | 1 = newest valid save copied |
| `save_store` |  |
| `save_erase` |  |
| `save_begin` | piece by piece (no WRAM copy of the save): begin, put..., end / open, get... (same order) |
| `save_put` |  |
| `save_end` |  |
| `save_open` |  |
| `save_get` |  |

## Cabecera (`gbe.h`)

```c
// Save in cartridge SRAM (needs an MBC with RAM + battery: -Wm-yt0x1B -Wm-ya1): two alternating
// slots with signature, version, sequence, length and checksum; a torn write keeps the previous
// save. len <= 4000.
extern uint8_t save_slot, save_seq;
uint8_t save_load(void *dst, uint16_t len, uint8_t version) GBE_FAR;   // 1 = newest valid save copied
void save_store(const void *src, uint16_t len, uint8_t version) GBE_FAR;
void save_erase(void) GBE_FAR;
// piece by piece (no WRAM copy of the save): begin, put..., end / open, get... (same order)
void save_begin(uint16_t len, uint8_t version) GBE_FAR;
void save_put(const void *src, uint16_t n) GBE_FAR;
void save_end(void) GBE_FAR;
uint8_t save_open(uint16_t len, uint8_t version) GBE_FAR;
void save_get(void *dst, uint16_t n) GBE_FAR;
```

## Notas de implementación

`gbe_save.c`:

> gbe: save in cartridge SRAM with two alternating slots ($A000 and $B000, bank 0), each validated
> by a signature, version, sequence number, length and Fletcher-16 checksum. A store goes to the
> slot NOT holding the newest valid save, signature written last: a power cut in the middle of a
> store leaves the previous save intact (CLAUDE.md: SRAM powers up with garbage).
> Needs an MBC with RAM + battery in game.json, e.g. ["-Wm-yt0x1B", "-Wm-ya1"]. SRAM is enabled
> only inside these functions (ENABLE_RAM / DISABLE_RAM). len <= 4000.
> Two ways: save_store / save_load copy one contiguous buffer; save_begin + save_put... + save_end and
> save_open + save_get... write/read the game's globals piece by piece with no WRAM copy of the save
> (games/faro: a 400-byte save buffer left the stack 132 bytes).
> 
> Slot layout: 'G' 'B' version seq len_lo len_hi data[len] sum1 sum2
