---
name: gb-hardware
description: Game Boy DMG hardware reference (condensed from Pan Docs). Load whenever code or design depends on DMG hardware behaviour - PPU/LCD timing and modes, VRAM/OAM access windows, sprites/OAM/DMA, scrolling, window, palettes, raster/STAT effects, interrupts, HALT, timer/DIV, joypad, audio registers and sound effects, cartridge header, MBC1/MBC5 banking, battery saves, or hardware quirks and bugs.
---

# Game Boy DMG hardware - quick reference

> Full references: docs/ref (Pan Docs copy and GBDK docs; `python -I harness/scripts/kb.py query "..." --kind ref`).
> This skill is the condensed version; cite the docs/ref section when a rule depends on a detail.

Target: original DMG (monochrome). Numbers below come from Pan Docs (`reference/pandocs/src/`).
CGB-only features, SGB, Camera, Printer, IR, Four Player Adapter and MBC2/3/6/7/HuC/MMM01/M161
are out of scope (see `othermbc.md`, `MBC3.md` etc. in Pan Docs if ever needed).

## Key numbers

| Item | Value |
|---|---|
| Master clock | 4.194304 MHz (2^22). 1 dot = 1 T-cycle. Real DMGs run ~50-70 ppm slow |
| CPU M-cycle | 4 dots -> 1.048576 MHz. Instruction timings are in M-cycles |
| Scanline | 456 dots (114 M-cycles); 154 lines per frame (0-143 visible, 144-153 VBlank) |
| Frame | 70224 dots = 17556 M-cycles; 59.73 Hz (~16.74 ms, not 60 Hz) |
| Mode 2 (OAM scan) | 80 dots |
| Mode 3 (drawing) | 172-289 dots (variable, see ppu.md) |
| Mode 0 (HBlank) | 376 - mode 3 = 87-204 dots |
| Mode 1 (VBlank) | 4560 dots = 10 lines = 1140 M-cycles (~1.09 ms) |
| Screen | 160x144 px = 20x18 tiles |
| BG/Window maps | two 32x32 maps (256x256 px): $9800-$9BFF, $9C00-$9FFF |
| Tile data | $8000-$97FF: 384 tiles x 16 bytes, 3 blocks of 128 |
| Objects | 40 in OAM ($FE00-$FE9F, 4 bytes each); max 10 per scanline; 8x8 or 8x16 |
| Palettes | BGP (BG+Window, 4 shades), OBP0/OBP1 (3 shades, index 0 = transparent) |
| OAM DMA | 160 M-cycles (640 dots); CPU can only access HRAM meanwhile |
| WRAM / HRAM | 8 KiB $C000-$DFFF / 127 bytes $FF80-$FFFE |
| ROM | 32 KiB without MBC; banked 16 KiB at $4000-$7FFF with MBC |
| DIV | increments at 16384 Hz |
| Interrupt dispatch | 5 M-cycles; vectors $40 VBL, $48 STAT, $50 Timer, $58 Serial, $60 Joypad |

## Memory map (summary)

| Range | Use |
|---|---|
| $0000-$3FFF | ROM bank 0 (header at $0100-$014F, rst/IRQ vectors $0000-$0060) |
| $4000-$7FFF | ROM bank 1..N (switchable via MBC); writes to $0000-$7FFF go to the MBC |
| $8000-$9FFF | VRAM (tiles $8000-$97FF, maps $9800-$9FFF) |
| $A000-$BFFF | Cartridge RAM (if any; must be enabled through MBC) |
| $C000-$DFFF | WRAM |
| $E000-$FDFF | Echo of $C000-$DDFF (prohibited) |
| $FE00-$FE9F | OAM |
| $FEA0-$FEFF | Not usable (reading it during OAM block triggers OAM corruption on DMG) |
| $FF00-$FF7F | I/O registers |
| $FF80-$FFFE | HRAM |
| $FFFF | IE |

## Golden rules

1. **VRAM** ($8000-$9FFF) is CPU-accessible only in modes 0, 1 and 2 (not in mode 3).
   **OAM** ($FE00-$FE9F) only in modes 0 and 1. Blocked writes are silently ignored; blocked reads give
   garbage (usually $FF). With the LCD off both are always accessible.
2. After a STAT wait loop, accessibility is only guaranteed for a short time; no interrupt may run
   between the check and the access.
3. **Turn the LCD off (LCDC.7 = 0) only during VBlank.** Doing it outside VBlank may damage the
   LCD (Nintendo rejected games doing it). After re-enabling, the first frame stays blank.
4. **OAM DMA must be run from HRAM** with interrupts disabled (or inside the VBlank ISR), waiting
   the full 160 M-cycles. Run it in VBlank. GBDK already does this every VBlank from `shadow_OAM`.
5. Hide unused objects with **Y = 0 or Y >= 160**, not with X: off-screen X still counts toward the
   10-per-line limit.
6. OBP0/OBP1 are **uninitialized** at boot; always set them. WRAM/HRAM/cart RAM power up random.
7. Never `inc`/`dec` a 16-bit register or use `[hli]`/`[hld]` with a pointer in $FE00-$FEFF while
   the PPU is in mode 2 (OAM corruption bug, DMG only).
8. Do not write to STAT expecting no side effects: on DMG it can fire a spurious STAT interrupt.
9. Enable cart RAM ($0A to $0000-$1FFF) only around save accesses, then disable it ($00).
10. `ei` takes effect after the next instruction; `halt` with IME=0 and a pending interrupt
    triggers the HALT bug.
11. Prefer HALT-until-VBlank over polling LY (saves battery).
12. Writing DIV resets it and can clock the timer and the APU frame sequencer early.
13. Audio: write NR52 bit 7 = 1 before any other sound register (APU off = registers cleared and
    read-only). Do not toggle DACs/NR51/NR50 mid-sound if you want to avoid pops.

## Topic files (this directory)

| Topic | File |
|---|---|
| LCDC, STAT, modes and timing, mode 3 length, tile addressing, maps, SCX/SCY, window, OAM format, sprite priority, palettes, OAM DMA, raster effects | `ppu.md` |
| Full memory map and DMG register table (address, name, purpose, R/W) | `memory-map.md` |
| IE/IF/IME, priorities, vectors, ISR timing, HALT and HALT bug, STOP, timer/DIV and obscure timer behaviour | `interrupts-timer.md` |
| P1/JOYP, reading procedure, edge detection, bounce | `joypad.md` |
| APU channels, all NRxx registers, wave RAM, formulas, note table, SFX recipes, music driver + SFX | `audio.md` |
| Cartridge header, checksums, ROM/RAM size codes, no-MBC, MBC1, MBC5, SRAM saves | `cartridge.md` |
| Hardware bugs and gotchas: OAM bug, STAT bug, LCD-off rule, power-up state, emulator vs hardware | `quirks.md` |

## Full detail

For anything not covered, grep the source: `reference/pandocs/src/<File>.md`, e.g.
`Rendering.md`, `pixel_fifo.md`, `LCDC.md`, `STAT.md`, `OAM.md`, `OAM_DMA_Transfer.md`, `Window.md`,
`Scrolling.md`, `Tile_Data.md`, `Tile_Maps.md`, `Palettes.md`, `Interrupts.md`,
`Interrupt_Sources.md`, `halt.md`, `Timer_and_Divider_Registers.md`, `Timer_Obscure_Behaviour.md`,
`Joypad_Input.md`, `Audio.md`, `Audio_Registers.md`, `Audio_details.md`, `The_Cartridge_Header.md`,
`MBC1.md`, `MBC5.md`, `Power_Up_Sequence.md`, `OAM_Corruption_Bug.md`,
`Reducing_Power_Consumption.md`, `CPU_Instruction_Set.md`, `Hardware_Reg_List.md`.
When a number here conflicts with Pan Docs, Pan Docs wins - fix this skill.
