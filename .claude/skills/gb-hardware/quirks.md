# Hardware quirks and gotchas (DMG)

## OAM corruption bug (DMG/MGB/SGB only; not CGB/GBA)

Trigger: while the PPU is in **mode 2**, either
- any CPU read/write of $FE00-$FEFF (including the unusable $FEA0-$FEFF), or
- a 16-bit increment/decrement of a register whose value is in $FE00-$FEFF: `inc rr`/`dec rr`
  (BC, DE, HL, SP), `ld a,[hli]`/`[hld]`, `ld [hli],a`/`[hld],a` (these hit twice), `push`/`call`/
  `rst`/interrupt dispatch and `pop`/`ret` when SP is in that range, executing code from OAM.

Effect: rows of OAM (20 rows x 8 bytes) get overwritten with mixes of neighbouring rows (objects 0
and 1 are not affected). The written value/address do not matter.

Practical rules:
- Never touch OAM directly from C; write `shadow_OAM` in WRAM and let DMA copy it (GBDK default).
  Any C pointer loop over OAM compiles to `ld [hl+],a` / `inc hl` style code - exactly the trigger.
- The trigger is the register value *before* the inc/dec being in $FE00-$FEFF: avoid pointers that
  sit in that range while being incremented/decremented outside VBlank (e.g. a loop that overruns
  past $FDFF into $FE00 and keeps going).
- Never put the stack near $FE00.

Source: reference/pandocs/src/OAM_Corruption_Bug.md

## Spurious STAT interrupt on write (DMG only)

Writing STAT (even $00) during mode 2, 0, 1 or while LY=LYC may request a STAT interrupt (acts as
if $FF was written for one M-cycle). Configure STAT sources once with IE.1 off or IF cleared
afterwards: `STAT = x; IF &= ~2;` before enabling. Not present on CGB (two commercial games depend
on it and fail there).

Source: reference/pandocs/src/STAT.md

## LCD off only in VBlank

LCDC.7 1->0 outside VBlank may damage the LCD (Nintendo-rejected). GBDK `DISPLAY_OFF` /
`display_off()` waits for VBlank first - **never** write `LCDC_REG &= ~LCDCF_ON` directly unless
already in VBlank. After LCDC.7 = 1 the first frame is blank (white). Do not STOP with the LCD on.

Source: reference/pandocs/src/LCDC.md, reference/pandocs/src/Reducing_Power_Consumption.md

## Power-up state (after DMG boot ROM)

| Item | DMG value | Rely on it? |
|---|---|---|
| A | $01 (DMG), $FF (MGB/Pocket), $11 (CGB/AGB in any mode) | yes, for model detection only |
| SP / PC | $FFFE / $0100 | set SP yourself (GBDK crt0 does) |
| LCDC | $91 (LCD on, BG on, BG tiles $8000, map $9800) | no |
| STAT / LY | $85 / $00 | no |
| BGP | $FC | no - set it |
| OBP0 / OBP1 | **uninitialized** (often $00 or $FF) | no - always set before showing objects |
| IE / IF | $00 / $E1 (VBlank already flagged) | clear IF before `ei` |
| DIV | $AB (DMG) | no |
| NR52 / NR50 / NR51 | $F1 / $77 / $F3 (APU on) | no; turn APU off ($00) if unused to save ~16% power |
| WRAM, HRAM | random (pattern varies by unit and temperature) | never - zero-init |
| Cart SRAM | random on first use | validate with signature/checksum |
| VRAM | contains the Nintendo logo tiles and map | clear what you use |

Flashcarts/multicarts run their own menu before your ROM, so even "boot" register values may be
different; initialize everything explicitly. Some emulators fill RAM with $00/$FF, hiding
uninitialized-variable bugs that appear on hardware.

Source: reference/pandocs/src/Power_Up_Sequence.md

## PPU timing variance

- Mode 3 is 172-289 dots; each object on a line, SCX%8 and the window lengthen it and shorten
  HBlank (down to 87 dots). Code that "fits in HBlank" in an emulator with few sprites can miss on
  a busy line. Budget the worst case.
- VRAM is blocked in mode 3 and OAM in modes 2-3: writes are **silently dropped** (missing tiles,
  not crashes). Classic symptom: random missing/garbled tiles when updating maps outside VBlank.
- DMA during mode 2/3 makes objects disappear or show wrong tiles for those lines.
- Changing OBJ size (LCDC.2) mid-frame leaks tile halves.
- Changing SCY mid-tile-fetch can desync bitplanes on pre-CGB-D models (precise-timing only).

Source: reference/pandocs/src/Rendering.md, reference/pandocs/src/OAM_DMA_Transfer.md, reference/pandocs/src/LCDC.md, reference/pandocs/src/Scrolling.md

## Sprites

- 10 per line, selected by OAM order using only Y: objects hidden with X=0 or X>=168 still use
  slots. Hide with Y=0 or Y>=160.
- DMG priority by X then OAM index (CGB uses OAM index only - a DMG game on CGB keeps DMG priority
  because the boot ROM sets OPRI in compatibility mode).
- 8x16 mode ignores tile index bit 0.
- OBJ X=0 object costs 11 dots of mode 3 even though invisible.

Source: reference/pandocs/src/OAM.md, reference/pandocs/src/Rendering.md, reference/pandocs/src/Power_Up_Sequence.md

## Window

- WY is latched as a "Y condition" (WY == LY at some line start) until VBlank.
- Window line counter only advances on lines where the window rendered.
- WX=0 shifts by SCX%8; WX=166 on DMG fills the line offset by one row; WX changes after window
  start insert a color-0 pixel. Hide partial-screen windows with WX > 166, not LCDC.5.

Source: reference/pandocs/src/Window.md, reference/pandocs/src/pixel_fifo.md

## CPU / interrupts

- HALT bug: `halt` with IME=0 and (IE & IF) != 0 executes the next byte twice.
- `ei` is delayed one instruction; `reti` is immediate.
- During OAM DMA the CPU may only access HRAM (DMG): the wait loop must be in HRAM and no
  interrupt may fire.
- STOP is unreliable/complex; resets DIV; LCD must be off.
- Echo RAM ($E000-$FDFF) mirrors WRAM but is prohibited; some flashcarts map SRAM there.

Source: reference/pandocs/src/halt.md, reference/pandocs/src/Interrupts.md, reference/pandocs/src/OAM_DMA_Transfer.md, reference/pandocs/src/Memory_Map.md

## Timer

- Writing DIV or TAC can generate an extra TIMA tick; writing DIV also advances the APU frame
  sequencer early (envelopes/lengths/sweeps glitch). Don't write DIV during gameplay.
- DMG only: disabling the timer while the selected bit is 1 ticks TIMA.
- TIMA reads $00 for one M-cycle after overflow before TMA reload.

Source: reference/pandocs/src/Timer_Obscure_Behaviour.md

## Audio

- NR52 bits 0-3 are read-only status; many emulators wrongly let writes toggle channels.
- APU off (NR52.7=0) clears all sound registers and makes them read-only.
- CH3 wave RAM unusable while CH3 plays (DMG); retriggering CH3 mid-read corrupts wave RAM
  (Duck Tales hits this). Stop with NR30=$00 first.
- First CH3 sample after trigger is index 1; the previous buffered sample plays first.
- Envelope at volume 0 keeps the channel "on"; DAC on/off, NR51 and NR50 changes pop.
- Switching CH4 to 7-bit LFSR mid-note can lock it silent until retriggered.
- Writing NRx2 mid-note ("zombie mode") behaves differently per model, wildly on DMG.
- On GBA, CH3's DAC output is inverted (spike when disabling it): disconnect CH3 in NR51 before
  rewriting wave RAM if GBA compatibility matters.
- Speaker is mono; stereo panning only audible on headphones.

Source: reference/pandocs/src/Audio_Registers.md, reference/pandocs/src/Audio_details.md

## Cartridge

- Wrong header checksum or logo = boot ROM lockup on real DMG (emulators without a boot ROM may
  run it anyway). makebin computes both checksums.
- MBC1: bank 0 written to $2000 selects bank 1; banks $20/$40/$60 unreachable at $4000.
- SRAM must be enabled before access and should be disabled after; reads while disabled are open
  bus.
- RAM size code $01 is bogus (used by some old homebrew tools) - use $00 or $02+.

Source: reference/pandocs/src/The_Cartridge_Header.md, reference/pandocs/src/MBC1.md

## Emulator vs. real DMG (what tests here will not catch)

Pan Docs explicitly notes emulators commonly differ on: NR52 write behaviour, Echo RAM (old VBA),
and uninitialized RAM contents. Many emulators also skip the boot ROM logo/checksum checks
(general knowledge, not Pan Docs). The DMG-only bugs above (OAM corruption,
STAT write IRQ, wave RAM locking/corruption, timer TAC tick, window WX=166) are absent on CGB/GBA,
so testing a DMG game on a GBC/GBA or a CGB-mode emulator hides them. Mode 3 length and
mid-frame register timing are only modelled by accurate emulators. Treat the PyBoy-based tests as
logic tests; verify timing, raster effects and audio on an accuracy-focused emulator and hardware.

Also: the frame rate is 59.73 Hz (not 60); real units run 50-70 ppm slow. Use frame counts, and
convert to seconds with 59.73 if real time matters.

Source: reference/pandocs/src/Audio_Registers.md, reference/pandocs/src/Memory_Map.md, reference/pandocs/src/Power_Up_Sequence.md, reference/pandocs/src/Specifications.md
