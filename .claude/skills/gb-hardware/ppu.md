# PPU / LCD (DMG)

Units: 1 dot = 1 T-cycle at 4.194304 MHz; 1 M-cycle = 4 dots.

## LCDC ($FF40) - LCD control (R/W, never locked by the PPU; may be changed mid-scanline)

| Bit | Name | 0 | 1 |
|---|---|---|---|
| 7 | LCD & PPU enable | off | on |
| 6 | Window tile map | $9800-$9BFF | $9C00-$9FFF |
| 5 | Window enable | off | on |
| 4 | BG & Window tile data | $8800-$97FF ("$8800 method", signed) | $8000-$8FFF ("$8000 method", unsigned) |
| 3 | BG tile map | $9800-$9BFF | $9C00-$9FFF |
| 2 | OBJ size | 8x8 | 8x16 |
| 1 | OBJ enable | off | on |
| 0 | BG & Window enable (DMG) | BG+Window blank (white); window bit ignored; objects still drawn | on |

- LCDC.7 1->0 **only during VBlank** (hardware damage risk otherwise). LCD off: VRAM/OAM fully
  accessible, screen shows a white "whiter than color 0", STAT mode reads 0. On re-enable the PPU
  starts drawing immediately but the first frame is blank.
- LCDC.5 is overridden by LCDC.0 = 0 on DMG.
- LCDC.2 changed mid-frame: 8x8 -> 8x16 within 8 lines of an object's bottom shows its second tile
  for the rest of those lines; changing during mode 2/3 can leak artifacts.
- LCDC.1 can be toggled mid-frame (e.g. hide objects over a status bar). Mid-scanline toggling on
  DMG: behaviour uninvestigated per Pan Docs.
- Objects always use $8000 addressing regardless of LCDC.4.

Source: reference/pandocs/src/LCDC.md

## STAT ($FF41), LY ($FF44), LYC ($FF45)

| STAT bit | Meaning | R/W |
|---|---|---|
| 6 | LYC=LY interrupt select | R/W |
| 5 | Mode 2 interrupt select | R/W |
| 4 | Mode 1 interrupt select | R/W |
| 3 | Mode 0 interrupt select | R/W |
| 2 | LYC == LY flag (constantly updated) | R |
| 1-0 | PPU mode (0 when LCD off) | R |

- LY: 0-153 (144-153 = VBlank). Read-only. LYC: compared constantly; match sets STAT.2 and, if
  enabled, requests STAT interrupt.
- STAT interrupt = rising edge of the OR of all enabled sources ("STAT line"). If a second source
  goes high while the line is already high, no new interrupt ("STAT blocking"). E.g. mode 0 + mode 1
  enabled: no interrupt for mode 1.
- DMG bug: writing STAT (even $00) during mode 2, 0, 1 or LY=LYC can fire a spurious STAT interrupt
  (acts as if $FF were written for one M-cycle). See quirks.md.

Source: reference/pandocs/src/STAT.md, reference/pandocs/src/Interrupt_Sources.md

## Modes and timing

| Mode | Phase | Duration (dots) | CPU can access |
|---|---|---|---|
| 2 | OAM scan (select objects for line) | 80 | VRAM |
| 3 | Drawing pixels | 172-289 | nothing (VRAM, OAM blocked) |
| 0 | HBlank | 376 - mode 3 (87-204) | VRAM, OAM |
| 1 | VBlank (LY 144-153) | 4560 (10 lines) | VRAM, OAM |

Per line: 2 -> 3 -> 0 (456 dots). Per frame: 144 visible lines then 10 VBlank lines = 70224 dots.
VBlank interrupt fires at start of LY=144.

### Mode 3 length (what extends it; mode 0 shrinks by the same amount)

| Cause | Penalty |
|---|---|
| Base | 160 px + 12 dots (two initial tile fetches) = 172 |
| Fine scroll | SCX % 8 dots at start of line |
| Window | 6 dots when switching to the window on that line |
| Each object drawn on the line (even partially) | 6-11 dots: flat 6 + (pixels of the underlying BG/window tile right of the object's leftmost pixel - 2, min 0, only for the first object in that tile). Object at OAM X=0 always costs 11 |

Practical consequence: HBlank can be as short as 87 dots (~21 M-cycles). Code that must hit HBlank
should assume the worst case. Mid-scanline writes to BGP reveal the delay on DMG.

Source: reference/pandocs/src/Rendering.md, reference/pandocs/src/pixel_fifo.md

## VRAM / OAM accessibility

- VRAM ($8000-$9FFF): accessible in modes 0, 1, 2. Wait idiom: loop while `STAT & 2` (mode 2 or 3);
  even if the loop exits at the very end of mode 0/1, mode 2 follows so VRAM stays accessible a few
  more cycles - but an interrupt in between can land you in mode 3.
- OAM ($FE00-$FE9F): accessible in modes 0, 1. Safe idiom: wait until STAT&2 != 0 (leave blank),
  then wait until STAT&2 == 0 (blank just began).
- Alternative sync: enable only STAT mode-0 source + IE.1, `di`, `halt` -> wakes at mode 0 start;
  mode 0 + next mode 2 is a VRAM window of ~165-288 dots (figure stated in
  Accessing_VRAM_and_OAM.md; the Rendering.md table gives 87-204 + 80 = 167-284 - small mismatch
  in the source, plan for the lower bound).
- Blocked writes are ignored; blocked reads return undefined data (typically $FF).
- Large updates: LCD off (only entering from VBlank) or spread across VBlanks. One VBlank =
  1140 M-cycles total, minus ISR overhead and OAM DMA (160 M-cycles + setup).

Source: reference/pandocs/src/Accessing_VRAM_and_OAM.md

## Tile data ($8000-$97FF)

| Block | Range | Objects | BG/Win, LCDC.4=1 | BG/Win, LCDC.4=0 |
|---|---|---|---|---|
| 0 | $8000-$87FF | 0-127 | 0-127 | - |
| 1 | $8800-$8FFF | 128-255 | 128-255 | 128-255 (-128..-1) |
| 2 | $9000-$97FF | - | - | 0-127 |

- Tile = 16 bytes, 2 bytes per row, top row first. Byte 1 = low bit of each pixel's color index,
  byte 2 = high bit; bit 7 = leftmost pixel. (Example: $3C,$7E -> indices 0 2 3 3 3 3 2 0.)
- With LCDC.4=1, BG and objects share all 256 tiles at $8000-$8FFF. With LCDC.4=0 BG uses
  $8800-$97FF and only block 1 is shared; total distinct tiles = 384.
- Tile ID from address: (address / 16) mod 256.

Source: reference/pandocs/src/Tile_Data.md, reference/pandocs/src/Memory_Map.md

## Tile maps and scrolling

- Two 32x32 maps of 1-byte tile IDs: $9800-$9BFF and $9C00-$9FFF. Entry address bits:
  `1001 1 m yyyyy xxxxx` (m = map select): X = addr mod 32, Y = addr/32 mod 32.
- SCY ($FF42), SCX ($FF43): top-left of the 160x144 viewport inside the 256x256 map; wraps
  (`bottom = (SCY+143)%256`, `right = (SCX+159)%256`). Readable/writable even in mode 3.
- Scroll registers are re-read at each tile fetch, except SCX low 3 bits, read once at line start.
  So mid-line SCX writes shift coarse position only; do raster scroll changes in HBlank.
- Streaming scroll: the map wraps, so write the new column/row just outside the view (21 columns
  / 19 rows are visible at once when not tile-aligned).

Source: reference/pandocs/src/Tile_Maps.md, reference/pandocs/src/Scrolling.md

## Window (WY $FF4A, WX $FF4B)

- Screen position of window top-left = (WX - 7, WY). Visible when WX in 0-166 and WY in 0-143.
  WX=7, WY=0 covers the whole screen. Window is opaque, not scrollable, always starts at its map's
  top-left tile, uses the same tile data as BG.
- Internal window line counter increments only on lines where the window was actually rendered;
  hiding it for some lines and showing again resumes at the next unrendered row (not LY-WY).
- "Y condition" latches when WY == LY at the start of a line and stays true until VBlank. So moving
  WY above LY mid-frame does not show the window this frame.
- Quirks: WX=0 -> window shifted left by SCX%8. WX=166 (DMG) -> window spans whole line, offset
  one line vertically. Disabling via LCDC.5 mid-line under specific conditions inserts one color-0
  pixel (DMG). Changing WX after the window started can insert a color-0 pixel.
- Advice from Pan Docs: write WX/WY/LCDC in VBlank; if mid-frame, in HBlank. To hide the window
  for part of the screen (e.g. status bar at top), set WX to a high value (>166) instead of
  toggling LCDC.5.
- Window costs +6 dots of mode 3 on lines where it is visible.

Source: reference/pandocs/src/Window.md, reference/pandocs/src/Tile_Maps.md

## OAM entry ($FE00 + 4*n, n = 0..39)

| Byte | Meaning |
|---|---|
| 0 | Y = screen Y + 16. Y=0 or Y>=160 hides. Y=16 top row; Y=152 8x8 bottom-aligned; Y=144 8x16 bottom-aligned |
| 1 | X = screen X + 8. X=0 or X>=168 hides but **still counts** toward the per-line limit |
| 2 | Tile index ($8000 method). 8x16: bit 0 ignored -> top = NN & $FE, bottom = NN OR $01 |
| 3 | Attributes (below) |

| Attr bit | Meaning (DMG) |
|---|---|
| 7 | Priority: 1 = BG/Window colors 1-3 drawn over this object (BG color 0 never covers) |
| 6 | Y flip |
| 5 | X flip |
| 4 | Palette: 0 = OBP0, 1 = OBP1 |
| 3-0 | CGB only (bank, palette); ignored on DMG |

Write a WRAM shadow copy and DMA it (GBDK: `shadow_OAM`, `move_sprite`, `set_sprite_tile`,
`set_sprite_prop`; transferred automatically each VBlank).

Source: reference/pandocs/src/OAM.md

## Object selection and priority

- **Selection** (mode 2): scans OAM in order $FE00 -> $FE9F, picks the first 10 objects whose Y
  range covers LY (size from LCDC.2). X is not considered. Objects 11+ on that line are not drawn.
- **Drawing priority (DMG)**: smaller X wins; equal X -> lower OAM index wins. (CGB mode uses OAM
  index only - irrelevant here.)
- Object-to-object priority is resolved first (first opaque pixel in priority order); only then is
  the winning object's attr bit 7 checked against BG. So a higher-priority object with bit 7 set,
  over BG colors 1-3, shows BG and also hides any lower-priority object there (even one with
  bit 7 clear). Usable to hide only parts of an object behind the background.
- Flicker technique (common practice, not Pan Docs): rotate OAM order each frame so that >10
  objects on a line flicker instead of permanently vanishing.

Source: reference/pandocs/src/OAM.md

## Palettes (DMG)

| Register | Bits 7-6 | 5-4 | 3-2 | 1-0 |
|---|---|---|---|---|
| BGP $FF47 | color for ID 3 | ID 2 | ID 1 | ID 0 |
| OBP0 $FF48 / OBP1 $FF49 | ID 3 | ID 2 | ID 1 | ignored (ID 0 transparent) |

Shade values: 0 white, 1 light gray, 2 dark gray, 3 black. Typical BGP = $E4 (identity: 3,2,1,0).
Boot leaves BGP = $FC; OBP0/OBP1 uninitialized -> always set them.
Fades/flashes: rewrite BGP/OBPx (cheap, one register write; do it in VBlank or a defined line).

Source: reference/pandocs/src/Palettes.md, reference/pandocs/src/Power_Up_Sequence.md

## OAM DMA ($FF46)

- Write $XX: copies $XX00-$XX9F -> $FE00-$FE9F. XX = $00-$DF. Takes 160 M-cycles (640 dots, ~1.4
  lines).
- On DMG the CPU can only access HRAM ($FF80-$FFFE) during DMA -> the start+wait routine must run
  from HRAM, and interrupts must not fire (they push to stack/fetch from ROM): call it from the
  VBlank ISR or with `di`.
- PPU reads OAM incorrectly during DMA: in mode 2 objects read as off-screen; in mode 3 wrong
  tile/attr. So run DMA in mode 1.
- Canonical HRAM routine (10 bytes):

```
run_dma:            ; copied to HRAM at init
    ld a, HIGH(shadow_oam)
    ldh [$FF46], a  ; start
    ld a, 40        ; 40 x 4 M-cycles = 160
.wait:
    dec a           ; 1 M-cycle
    jr nz, .wait    ; 3 M-cycles
    ret
```

- Mid-frame DMA (>40 objects multiplexing) is possible: wait for mode 0 first; objects vanish on
  ~2 lines; starting in mode 3 causes glitches.
- GBDK installs its own HRAM routine and DMAs `shadow_OAM` every VBlank (`ENABLE_OAM_DMA` /
  `DISABLE_OAM_DMA`, `SET_SHADOW_OAM_ADDRESS` for any 256-byte aligned buffer).

Source: reference/pandocs/src/OAM_DMA_Transfer.md

## Mid-frame (raster) effects

| Effect | Method |
|---|---|
| Status bar without sprites over it | LYC at bar's first line, STAT LYC int, handler clears LCDC.1; VBlank sets it back |
| Status bar at bottom | Window with WY = bar line, WX = 7 |
| Status bar at top | Window from line 0, then at bar end set WX > 166 (not LCDC.5) |
| Parallax bands | LYC interrupt per band, write new SCX in the handler (chain LYC to next band) |
| Wavy / per-line scroll | Mode 0 STAT interrupt or LYC each line, write SCX/SCY from a table |
| Palette split | Write BGP at a given line |

Caveats:
- ISR entry is 5 M-cycles plus push/pop; at worst-case HBlank (87 dots ~ 21 M-cycles) the write
  may land in mode 3 of the next line. Write the critical register first, keep handlers tiny, or
  trigger one line early (LYC = target - 1) and wait for mode 0.
- Interrupt latency varies (the CPU finishes the current instruction; HALT/other ISRs delay it),
  so raster effects jitter if other interrupts (timer, serial) are active or IME is off.
- STAT blocking: LYC and mode interrupts sharing the line can suppress each other.
- Writing STAT on DMG can spuriously trigger the interrupt (configure sources once, early).
- SCX fine bits are latched per line; SCY is re-read per tile fetch.
- In GBDK: `add_LCD(handler)` + `set_interrupts(VBL_IFLAG | LCD_IFLAG)`, `STAT_REG`, `LYC_REG`.
  Keep LCD handlers short (GBDK ISR wrappers add overhead; asm handlers for per-line effects).

Source: reference/pandocs/src/Interrupt_Sources.md, reference/pandocs/src/LCDC.md, reference/pandocs/src/Rendering.md
