# Cartridge: header, MBCs, saves

## Header ($0100-$014F) - fields that matter

| Addr | Field | Notes |
|---|---|---|
| $0100-$0103 | Entry point | boot ROM jumps here; usually `nop` + `jp $0150` |
| $0104-$0133 | Nintendo logo (48 bytes) | must match exactly or the DMG boot ROM locks up (checked after the scroll) |
| $0134-$0143 | Title | uppercase ASCII, pad with $00. On later carts $013F-$0142 = manufacturer code, $0143 = CGB flag |
| $0143 | CGB flag | $80 = CGB enhanced + DMG compatible, $C0 = CGB only. DMG game: leave $00 |
| $0144-$0145 | New licensee code | used only if $014B = $33 |
| $0146 | SGB flag | $03 = SGB functions; else $00 |
| $0147 | Cartridge type | see below |
| $0148 | ROM size | 32 KiB << value |
| $0149 | RAM size | see below |
| $014A | Destination | $00 Japan (and possibly overseas), $01 overseas only |
| $014B | Old licensee | $33 = use new licensee code |
| $014C | Mask ROM version | usually $00 |
| $014D | Header checksum | **verified by boot ROM** - lockup if wrong |
| $014E-$014F | Global checksum | big-endian sum of all ROM bytes except these two; not verified by the console |

Header checksum algorithm (boot ROM):

```c
uint8_t x = 0;
for (uint16_t a = 0x0134; a <= 0x014C; a++) x = x - rom[a] - 1;
// rom[0x014D] must equal x
```

Tooling: GBDK `makebin -Z` writes the logo, header fields and **both checksums** (verified on
`games/hello/build/hello.gb`: $014D and $014E-F match the algorithms). RGBDS uses `rgbfix -v`.
Relevant makebin options (pass through lcc as `-Wm-y...`): `-yt <type>` cart type, `-yo <n>` ROM
banks (`A` = auto), `-ya <n>` RAM banks, `-yn <name>` title, `-yj` non-Japanese, `-yc`/`-yC` CGB
compatible/only, `-ys` SGB, `-yN` omit logo (do not use for real hardware).

Source: reference/pandocs/src/The_Cartridge_Header.md

## Cartridge type ($0147) - relevant values

| Code | Type |
|---|---|
| $00 | ROM ONLY (32 KiB) |
| $01 / $02 / $03 | MBC1 / MBC1+RAM / MBC1+RAM+BATTERY |
| $08 / $09 | ROM+RAM / ROM+RAM+BATTERY (no licensed cart used it; behaviour unknown - avoid) |
| $19 / $1A / $1B | MBC5 / MBC5+RAM / MBC5+RAM+BATTERY |
| $1C / $1D / $1E | MBC5+RUMBLE / +RAM / +RAM+BATTERY |
| others | MBC2 $05-$06, MMM01 $0B-$0D, MBC3 $0F-$13 (RTC), MBC6 $20, MBC7 $22, Camera $FC, TAMA5 $FD, HuC3 $FE, HuC1 $FF - out of scope |

ROM size ($0148): $00 32 KiB (2 banks), $01 64 KiB (4), $02 128 KiB (8), $03 256 KiB (16),
$04 512 KiB (32), $05 1 MiB (64), $06 2 MiB (128), $07 4 MiB (256), $08 8 MiB (512).

RAM size ($0149): $00 none, $01 unused (do not use), $02 8 KiB (1 bank), $03 32 KiB (4 banks),
$04 128 KiB (16 banks), $05 64 KiB (8 banks). Must be $00 if the type has no "RAM".

Source: reference/pandocs/src/The_Cartridge_Header.md

## No MBC

32 KiB ROM mapped at $0000-$7FFF. Optional up to 8 KiB RAM at $A000-$BFFF via discrete logic
(types $08/$09 - unused commercially). Default for small GBDK games.

Source: reference/pandocs/src/nombc.md

## MBC1 (max 2 MiB ROM / 32 KiB RAM; default wiring 512 KiB ROM + 32 KiB RAM)

| Write range | Register | Details |
|---|---|---|
| $0000-$1FFF | RAM enable | low nibble $A enables, anything else disables |
| $2000-$3FFF | ROM bank (5 bits) | selects bank for $4000-$7FFF. Value 0 behaves as 1. Bits above ROM size are masked |
| $4000-$5FFF | RAM bank (2 bits) / ROM bank bits 5-6 | RAM bank 0-3 (32 KiB RAM carts) or upper ROM bits (1 MiB+ carts) |
| $6000-$7FFF | Banking mode (1 bit) | 0 = simple (default): $0000-$3FFF and $A000-$BFFF locked to bank 0. 1 = advanced: 2-bit register also applies to those areas |

Pitfalls:
- The 00->01 translation looks only at the 5-bit register: banks $20, $40, $60 are unreachable at
  $4000 on large carts (you get $21, $41, $61). Lay out code/data so those banks are not needed
  in the switchable window, or use MBC5.
- 32 KiB RAM banking requires mode 1 (in mode 0 RAM is locked to bank 0). 32 KiB RAM only with ROM
  <= 512 KiB.
- All registers are $00 at power-up (ROM bank treated as 1). Bank registers are write-only: keep a
  shadow copy of the current bank (GBDK: `_current_bank`, maintained by `SWITCH_ROM`).
- Interrupt handlers live in bank 0; an ISR that switches banks must restore the previous bank.
- MBC1M multicarts (1 MiB compilations) wire bits differently - irrelevant for new games.

Source: reference/pandocs/src/MBC1.md

## MBC5 (max 8 MiB ROM / 128 KiB RAM) - preferred for anything > 32 KiB

| Write range | Register | Details |
|---|---|---|
| $0000-$1FFF | RAM enable | write $0A enable, $00 disable (hardware checks low nibble = $A; rely on $0A/$00) |
| $2000-$2FFF | ROM bank bits 0-7 | 0 really selects bank 0 at $4000 (unlike MBC1) |
| $3000-$3FFF | ROM bank bit 8 | for > 256 banks (4 MiB+) |
| $4000-$5FFF | RAM bank | $00-$0F; on rumble carts bit 3 drives the motor instead |

- No banking modes, no unreachable banks. Only MBC guaranteed for CGB double speed (irrelevant
  on DMG).
- GBDK: `SWITCH_ROM_MBC5(b)` writes $3000 = 0 and $2000 = b; `SWITCH_ROM(b)` writes only $2000
  region (`rROMB0`); `SWITCH_ROM_MBC5_8M` for > 256 banks (do not mix with the others).

Source: reference/pandocs/src/MBC5.md

## Unmapped RAM banks

Selecting a RAM bank beyond the chip size wraps around:
`((addr - $A000) + bank * $2000) % ram_size`.

Source: reference/pandocs/src/MBCs.md

## Battery SRAM saves - discipline

1. RAM content on first power-up is **random garbage**. Store a signature (several known bytes,
   avoid all-$00/all-$FF) plus a version and a checksum at a fixed SRAM location; validate before
   trusting any save. Initialize defaults if invalid.
2. Enable RAM ($0A to $0000-$1FFF; GBDK `ENABLE_RAM`), do the accesses, then **disable it
   immediately** ($00; GBDK `DISABLE_RAM`). Disabled RAM protects contents against corruption
   during power-off or cartridge removal. While disabled, reads are open bus (often $FF, not
   guaranteed) and writes are ignored.
3. Write saves atomically-ish: write data, then update checksum/valid flag last (or keep two
   slots and alternate) so a power cut mid-save leaves one valid copy.
4. Header must declare RAM: type with +RAM+BATTERY ($03 MBC1, $1B MBC5) and $0149 >= $02;
   otherwise emulators may not map or persist SRAM. GBDK: e.g. `-Wm-yt0x1B -Wm-ya1` (MBC5 + RAM
   + battery, 1 RAM bank = 8 KiB) - verify flag spelling against the GBDK manual.
5. In GBDK, SRAM variables can be placed in the SRAM area (see GBDK docs on `-Wf-ba0` / SRAM
   banks - verify in the GBDK manual); never access them while RAM is disabled.
6. SRAM is as fast as WRAM; can be used as extra work RAM, but keep save data separate.

Source: reference/pandocs/src/MBC1.md, reference/pandocs/src/Power_Up_Sequence.md
