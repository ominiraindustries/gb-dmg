# ROM banking, MBCs and SRAM saves

Sources: `docs/pages/05_banking_mbcs.md`, `04_coding_guidelines.md` (banked calling convention),
`20_toolchain_settings.md` (bankpack/makebin), `gb/gb.h` (macros), examples
`cross-platform/banks*`, `cross-platform/sram_banks`. All flag sets below were built and run
in PyBoy with GBDK 4.5.0.

## Memory map refresher
| Range | What | Notes |
|---|---|---|
| 0000-3FFF | ROM bank 0 (fixed) | crt0, GBDK lib, all unbanked code/const data. **Must stay <= 16 KB** with an MBC |
| 4000-7FFF | ROM bank N (switchable) | code/const data in `_CODE_N` |
| A000-BFFF | cart SRAM bank (8 KB each) | needs `ENABLE_RAM`; persists only with a battery cart type |
| C000-DFFF | WRAM | shadow OAM C000-C09F, `_DATA` from C0A0, stack grows down from E000 |
| FF80-FFFE | HRAM | OAM DMA routine at FF80, `SFR` vars |
No MBC = 32 KB, banks 0+1 used as one flat ROM; nothing below is needed.

## Which MBC
Docs recommend **MBC5** (`0x19` / `0x1A` / `0x1B` = +SRAM+BATT): `SWITCH_ROM` works up to bank 255.
MBC1 (`0x01` / `0x02` / `0x03`) works for small games but banks 0x20/0x40/0x60 are unusable,
`SWITCH_ROM`/banked calls reach bank 31 max, 32 KB SRAM only with ROM <= 512 KB.
| `-Wm-yt` | Cart | | `-Wm-yt` | Cart |
|---|---|---|---|---|
| 0x00 | ROM only | | 0x13 | MBC3+SRAM+BATT |
| 0x01 | MBC1 | | 0x10 | MBC3+RTC+SRAM+BATT |
| 0x02 | MBC1+SRAM | | 0x19 | MBC5 |
| 0x03 | MBC1+SRAM+BATT | | 0x1A | MBC5+SRAM |
| 0x08/0x09 | ROM+SRAM(+BATT), 32 KB | | 0x1B | MBC5+SRAM+BATT |

## lcc flags (go in `games/<game>/game.json` `"lcc_flags"`)
| Flag | Meaning |
|---|---|
| `-Wm-yt<N>` | cart type byte 0x147 (also forwarded to bankpack as `-yt`) |
| `-Wm-yo<N>` | number of 16 KB ROM banks: 2,4,8,...,512; `-Wm-yoA` = auto-size |
| `-Wm-ya<N>` | number of 8 KB SRAM banks: 0,1,4,16. **Omit it and the header says no RAM** -> emulators won't map SRAM |
| `-autobank` | run bankpack: assigns banks to files with `#pragma bank 255` |
| `-Wb-<opt>` | bankpack options, e.g. `-Wb-v` (print assignments), `-Wb-max=3` (error if more banks needed) |
| `-Wf-bo<N>` / `-Wf-ba<N>` | put a file in ROM bank N / SRAM bank N (alternative to pragmas) |
`-Wl-yt...` also works (lcc forwards it), but use `-Wm-` consistently.
**`-autobank` without `-Wm-yt` fails** with the cryptic `?ASlink-Error-<cannot open> : "...lcc*.lk"`.

### Recipe: 64 KB MBC1 game with battery save
```json
{
  "title": "MYGAME",
  "lcc_flags": ["-autobank", "-Wm-yt0x03", "-Wm-yo4", "-Wm-ya1"]
}
```
4 banks x 16 KB = 64 KB, 1 x 8 KB SRAM, header 0x147=0x03, 0x148=0x01, 0x149=0x02 (verified).
MBC5 equivalent: `["-autobank", "-Wm-yt0x1B", "-Wm-yo4", "-Wm-ya1"]`.
Add `-Wf--max-allocs-per-node50000` too (see `toolchain.md`). Our harness rebuilds every
source in one lcc call, so bankpack re-evaluates all autobanked files every build (the docs'
`-Wb-ext=.rel` advice is only needed for incremental Makefile builds).

## Putting code/data in banks
- `#pragma bank 255` at the top of a file = "autobank this file" (bankpack picks the bank).
  `#pragma bank 2` = fixed bank 2. One bank per source file; split large assets into several files.
- `BANKREF(name)` in that file creates the symbol `___bank_name`; other files use
  `BANKREF_EXTERN(name)` and `BANK(name)` (a `uint8_t` constant resolved at link time).
- `const` data in a banked file lives in that bank and is readable **only while that bank is mapped**.
- Function keywords:
  - `BANKED`: far call (trampoline switches to the callee's bank and back). Declare it `BANKED` in
    the header too. Don't combine `static` with `BANKED` (breaks autobank bank fixups).
  - `NONBANKED`: forced into bank 0 even if the file is banked.
  - neither: near call, placed in the file's bank; only callable from the same bank or bank 0
    *while that bank is mapped*.
- Who can do what (docs):
  - bank-0 code: may call any function, may use data in any bank (after switching).
  - banked code: may call bank 0 and `BANKED` functions; may use data only from bank 0 and its
    own bank; **must never `SWITCH_ROM` itself** (it would unmap its own code).

## Verified multi-file example (autobank + SRAM)
```c
// file: level.h
#ifndef LEVEL_H
#define LEVEL_H
#include <gb/gb.h>
#include <stdint.h>
extern const uint8_t level_data[4];
BANKREF_EXTERN(level_data)
uint8_t level_sum(void) BANKED;
BANKREF_EXTERN(level_sum)
#endif
```
```c
// file: level.c
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>
#include "level.h"

BANKREF(level_data)
const uint8_t level_data[4] = {1, 2, 3, 4};

BANKREF(level_sum)
uint8_t level_sum(void) BANKED {
    // Runs with its own bank mapped: may read level_data directly
    return level_data[0] + level_data[1] + level_data[2] + level_data[3];
}
```
```c
// file: save.c
#include <stdint.h>
#pragma dataseg DATA_0
// Everything below is placed in cart SRAM bank 0 (0xA000...). Never give these initializers.
uint8_t save_magic;
uint16_t save_hiscore;
```
```c
// file: main.c
// build: -autobank -Wm-yt0x03 -Wm-yo4 -Wm-ya1
#include <gb/gb.h>
#include <stdint.h>
#include "level.h"

extern uint8_t save_magic;
extern uint16_t save_hiscore;
#define SAVE_MAGIC 0xA5

uint8_t result, copied;
uint16_t hiscore;

// Bank-0 helper that may switch banks (main.c has no #pragma bank -> bank 0)
uint8_t read_level_byte(uint8_t i) NONBANKED {
    uint8_t saved = CURRENT_BANK;
    SWITCH_ROM(BANK(level_data));
    uint8_t v = level_data[i];
    SWITCH_ROM(saved);
    return v;
}

void load_save(void) {
    ENABLE_RAM;
    SWITCH_RAM(0);
    if (save_magic != SAVE_MAGIC) {     // first boot or garbage
        save_magic = SAVE_MAGIC;
        save_hiscore = 0;
    }
    hiscore = save_hiscore;             // work on a WRAM copy
    DISABLE_RAM;                        // protect SRAM from corruption on power-off
}

void store_hiscore(uint16_t v) {
    ENABLE_RAM;
    save_hiscore = v;
    DISABLE_RAM;
}

void main(void) {
    load_save();
    result = level_sum();               // far call: 10
    copied = read_level_byte(3);        // 4
    store_hiscore(1234);
    while (1) vsync();
}
```
Resulting symbols (`.noi`): `_save_magic 0xA000`, `_save_hiscore 0xA001`, `_level_data 0x14013`
(banked addresses are printed as `bank << 16 | addr`).

## Access patterns for banked const data
1. **Banked function next to its data** (best): put `load_level_1(void) BANKED { set_bkg_data(...,
   level1_tiles); set_bkg_tiles(..., level1_map); }` in the asset's file. GBDK library functions
   are in bank 0, so they read the currently mapped bank fine.
2. **NONBANKED wrapper** that saves `CURRENT_BANK`, `SWITCH_ROM(bank)`, works, restores
   (`05_banking_mbcs.md` "Wrapper Function for Accessing Banked Data"):
   `set_banked_bkg_data(first, n, data, BANK(data))`.
3. **Copy to WRAM** once (level map into a WRAM buffer) when data is needed every frame from code
   in other banks.
4. Far pointers (`gbdk/far_ptr.h`: `TO_FAR_PTR`, `FAR_CALL(ptr, type, ...)`) for function tables
   across banks; not from ISRs.

Pointers are 16-bit and bank-unaware: a pointer into 0x4000-0x7FFF is only valid while the right
bank is mapped. Don't pass pointers to banked data into code living in a different bank.

## Cost of banking
- Banked call: caller pushes args on the stack (never registers), puts bank in E and address in HL,
  calls the bank-0 trampoline `__sdcc_bcall_ehl`, which pushes the current bank, switches,
  calls; on return switches back. So: several extra instructions + 2 bank-register writes per call,
  and args always on the stack. Keep per-frame hot paths in bank 0 or inside one bank.
- `SWITCH_ROM(b)` itself is cheap: two stores (`_current_bank = b; rROMB0 = b`).
- Bank 0 is precious: keep the main loop, ISRs, frequently called helpers and bank-switching
  wrappers there; move level data, graphics, music, menus, cutscenes to banks.
- Check fill with `romusage build/<game>.map -g` (the harness prints it). Bank 0 overflow shows up
  as `Write from one bank spans into the next` / `possibly wrote twice at addr 4000` warnings.

## Interrupts and banks
- `int_handler` is `NONBANKED`: ISRs live in bank 0. If an ISR calls banked code or switches banks
  (e.g. a music driver in a bank), save `CURRENT_BANK` first and `SWITCH_ROM` back before returning.
- `SWITCH_ROM_MBC5` (two writes) is not interrupt-safe; plain `SWITCH_ROM` is fine for <= 256 banks.

## SRAM notes
- Pattern: `ENABLE_RAM` -> `SWITCH_RAM(n)` (only if >1 bank) -> read/write -> `DISABLE_RAM`.
- Validate with a magic byte + version (+ checksum) because SRAM starts as garbage.
- Initialized variables in a `DATA_N`/`-Wf-ba` file silently end up in WRAM instead (docs known
  issue): declare SRAM variables without initializers and set them at runtime.
- Alternative without pragmas: a struct at a fixed address,
  `typedef struct { uint8_t magic; uint16_t hiscore; } save_t;` + `#define SAVE ((save_t *)0xA000)`.
- SRAM banks > 1: `-Wm-ya4` (32 KB) and `SWITCH_RAM(0..3)`.
