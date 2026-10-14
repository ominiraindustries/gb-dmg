# Memory map and DMG registers

## Address space

| Start | End | Size | Description | Notes |
|---|---|---|---|---|
| $0000 | $00FF | | rst vectors ($00,$08,...,$38), IRQ vectors ($40,$48,$50,$58,$60) | Free for other use if unused |
| $0100 | $014F | | Cartridge header (entry point at $0100) | see cartridge.md |
| $0000 | $3FFF | 16 KiB | ROM bank 0 | fixed (MBC1 mode 1 on 1 MiB+ carts can remap) |
| $4000 | $7FFF | 16 KiB | ROM bank 1..N | switchable via MBC; writes to $0000-$7FFF = MBC registers |
| $8000 | $97FF | 6 KiB | VRAM tile data (384 tiles) | blocked in mode 3 |
| $9800 | $9BFF | 1 KiB | VRAM tile map 0 (32x32) | |
| $9C00 | $9FFF | 1 KiB | VRAM tile map 1 (32x32) | |
| $A000 | $BFFF | 8 KiB | Cartridge RAM (banked if MBC) | needs RAM enable; open bus (often $FF) when disabled |
| $C000 | $CFFF | 4 KiB | WRAM | |
| $D000 | $DFFF | 4 KiB | WRAM | (bank-switchable only on CGB) |
| $E000 | $FDFF | | Echo of $C000-$DDFF | Nintendo prohibits use; some flashcarts conflict |
| $FE00 | $FE9F | 160 B | OAM (40 x 4 bytes) | blocked in modes 2/3 |
| $FEA0 | $FEFF | | Not usable | DMG: reads during OAM block trigger OAM corruption, else $00 |
| $FF00 | $FF7F | | I/O registers | |
| $FF80 | $FFFE | 127 B | HRAM | only memory usable during OAM DMA |
| $FFFF | | | IE register | |

VRAM map entry address = `$9800 + map*$400 + y*32 + x`.

Source: reference/pandocs/src/Memory_Map.md

## DMG hardware registers

R/W column: R = read-only, W = write-only, R/W, Mixed = some bits read-only. Power-up value is
the DMG (not DMG0) value after the boot ROM; see quirks.md.

| Addr | Name | Purpose | R/W | Boot |
|---|---|---|---|---|
| $FF00 | P1/JOYP | Joypad (bits 5/4 select, 3-0 input, active low) | Mixed | $CF |
| $FF01 | SB | Serial data | R/W | $00 |
| $FF02 | SC | Serial control (bit 7 start, bit 0 clock: 1 = internal) | R/W | $7E |
| $FF04 | DIV | Divider, 16384 Hz; any write resets to 0 | R/W | $AB |
| $FF05 | TIMA | Timer counter | R/W | $00 |
| $FF06 | TMA | Timer modulo (reload value) | R/W | $00 |
| $FF07 | TAC | Timer control (bit 2 enable, 1-0 clock) | R/W | $F8 |
| $FF0F | IF | Interrupt flags (bits 4-0) | R/W | $E1 |
| $FF10 | NR10 | CH1 sweep | R/W | $80 |
| $FF11 | NR11 | CH1 duty / length | Mixed | $BF |
| $FF12 | NR12 | CH1 volume & envelope | R/W | $F3 |
| $FF13 | NR13 | CH1 period low | W | $FF |
| $FF14 | NR14 | CH1 period high & control (trigger, length enable) | Mixed | $BF |
| $FF16 | NR21 | CH2 duty / length | Mixed | $3F |
| $FF17 | NR22 | CH2 volume & envelope | R/W | $00 |
| $FF18 | NR23 | CH2 period low | W | $FF |
| $FF19 | NR24 | CH2 period high & control | Mixed | $BF |
| $FF1A | NR30 | CH3 DAC enable (bit 7) | R/W | $7F |
| $FF1B | NR31 | CH3 length | W | $FF |
| $FF1C | NR32 | CH3 output level (bits 6-5) | R/W | $9F |
| $FF1D | NR33 | CH3 period low | W | $FF |
| $FF1E | NR34 | CH3 period high & control | Mixed | $BF |
| $FF20 | NR41 | CH4 length | W | $FF |
| $FF21 | NR42 | CH4 volume & envelope | R/W | $00 |
| $FF22 | NR43 | CH4 frequency & randomness | R/W | $00 |
| $FF23 | NR44 | CH4 control (trigger, length enable) | Mixed | $BF |
| $FF24 | NR50 | Master volume & VIN panning | R/W | $77 |
| $FF25 | NR51 | Panning (bits 7-4 left CH4-1, 3-0 right CH4-1) | R/W | $F3 |
| $FF26 | NR52 | APU on/off (bit 7), channel status (3-0, read-only) | Mixed | $F1 |
| $FF30-$FF3F | Wave RAM | 32 4-bit samples for CH3 | R/W | not specified |
| $FF40 | LCDC | LCD control | R/W | $91 |
| $FF41 | STAT | LCD status / STAT interrupt sources | Mixed | $85 |
| $FF42 | SCY | BG viewport Y | R/W | $00 |
| $FF43 | SCX | BG viewport X | R/W | $00 |
| $FF44 | LY | Current line 0-153 | R | $00 |
| $FF45 | LYC | LY compare | R/W | $00 |
| $FF46 | DMA | OAM DMA source high byte & start | R/W | $FF |
| $FF47 | BGP | BG palette | R/W | $FC |
| $FF48 | OBP0 | OBJ palette 0 | R/W | uninitialized |
| $FF49 | OBP1 | OBJ palette 1 | R/W | uninitialized |
| $FF4A | WY | Window Y | R/W | $00 |
| $FF4B | WX | Window X + 7 | R/W | $00 |
| $FF50 | BANK | Boot ROM unmap (written by boot ROM; do not touch) | W | - |
| $FFFF | IE | Interrupt enable (bits 4-0) | R/W | $00 |

Unlisted addresses in $FF00-$FF7F are unused on DMG ($FF4C-$FF77 range are CGB registers:
KEY0/KEY1, VBK, HDMA1-5, RP, BCPS/BCPD/OCPS/OCPD, OPRI, SVBK, PCM12/34 - ignore for DMG).

Source: reference/pandocs/src/Hardware_Reg_List.md, reference/pandocs/src/Power_Up_Sequence.md

## Interrupt bit layout (IE $FFFF and IF $FF0F)

| Bit | Source | Vector | Priority |
|---|---|---|---|
| 0 | VBlank | $0040 | highest |
| 1 | LCD STAT | $0048 | |
| 2 | Timer | $0050 | |
| 3 | Serial | $0058 | |
| 4 | Joypad | $0060 | lowest |

Source: reference/pandocs/src/Interrupts.md

## GBDK name mapping (hardware.h)

GBDK exposes registers as `<NAME>_REG` (e.g. `LCDC_REG`, `STAT_REG`, `LYC_REG`, `BGP_REG`,
`OBP0_REG`, `NR52_REG`) and `r<NAME>` aliases (`rLCDC`, `rSTAT`, `rAUDENA` for NR52). MBC
registers: `rRAMG` (RAM enable), `rROMB0`/`rROMB1` (ROM bank), `rRAMB` (RAM bank).
Check `tools/gbdk/include/gb/hardware.h` for exact spellings.
