# SM83 optimization idioms (cycle counts in T-states from opcodes.json)

Rule zero: measure before and after (`measure_cycles()` in equivalence-testing.md, or the
`[cycles]` column of `lcc -Wa-l` listings). Figures marked "measured" were obtained by running
the code in PyBoy and match the hand count from opcodes.json exactly.

## Budgets

| Period | T-states | Source |
|--------|----------|--------|
| Frame (154 lines) | 70224 | 154 x 456 |
| Scanline | 456 | Pandocs Rendering.md |
| VBlank (mode 1, lines 144-153) | 4560 | 10 lines |
| Mode 2 (OAM scan) | 80 | VRAM accessible, OAM not |
| Mode 3 (drawing) | 172-289 | VRAM and OAM inaccessible |
| Mode 0 (HBlank) | 376 - mode 3 = 87-204 | VRAM and OAM accessible |
| Mode 0 + next line's mode 2 | 165-288 contiguous | VRAM accessible (Pandocs Accessing_VRAM_and_OAM.md) |
| OAM DMA (160 bytes) | 640 | done by GBDK's VBlank ISR from shadow OAM |
| GBDK VBlank IRQ until `vsync()` returns | ~1136 measured (template game) | leaves ~3400 T of VBlank |

VRAM is writable in modes 0, 1 **and 2** (only mode 3 blocks it); OAM only in modes 0 and 1.
Writes in the wrong mode are silently ignored. With the display off (`DISPLAY_OFF`) both are
always accessible.

## VRAM copy rates (measured, 64 bytes WRAM to WRAM, page-aligned destination)

| Method | T/byte | Bytes in ~3400 T after `vsync()` | Bytes in a full VBlank (4560) |
|--------|--------|---------|---------|
| simple loop `ld a,(hl+)` / `ld (de),a` / `inc de` / `dec c` / `jr nz` | 40.7 (40 per byte) | ~83 | ~112 |
| GBDK `memcpy` | 30.9 | ~110 | ~147 |
| 8x unrolled `ld a,(hl+)` / `ld (de),a` / `inc e` (dest must not cross a 256-byte page) | 22.7 (20 + 2 loop) | ~150 | ~200 |
| popslide, 4 pops per loop | 21.9 | ~155 | ~208 |
| popslide fully unrolled | 19.8 (18 + fixed 116 T) | ~180 | ~245 |

Take these as upper bounds: your main loop also runs between `vsync()` and the copy.
A 16-byte tile = 2 bytes x 8 rows; about 9 tiles per VBlank with an unrolled copy.

Simple loop (40 T/byte = 8+8+8+4+12):
```
1$:     ld      a, (hl+)        ; 8
        ld      (de), a         ; 8
        inc     de              ; 8
        dec     c               ; 4
        jr      nz, 1$          ; 12 taken / 8 last
```
Popslide (pop is 12 T for 2 bytes; 36 T per 2 bytes with the stores):
```
        di                      ; an interrupt would push onto your data!
        ld      (save_sp), sp   ; 20
        ld      sp, #_src       ; 12   (or ld sp, hl: 8)
        ld      hl, #dest       ; 12
        .rept   32
        pop     de              ; 12
        ld      a, e            ; 4
        ld      (hl+), a        ; 8
        ld      a, d            ; 4
        ld      (hl+), a        ; 8
        .endm
        ld      a, (save_sp)    ; restore SP: there is no ld hl,(nn) on SM83
        ld      l, a
        ld      a, (save_sp+1)
        ld      h, a
        ld      sp, hl          ; 16+4+16+4+8 = 48 T
        ei
```
(`ld (hl), e` / `inc l` / `ld (hl), d` / `inc l` is also 36 T per 2 bytes but limited to one
256-byte page.) Keep interrupts off for as short as possible: a long `di` delays the VBlank
ISR and the music driver.

## Small idioms

| Instead of | Use | Saves | Caveat |
|-----------|-----|-------|--------|
| `ld a, #0` (2 B, 8 T) | `xor a` (1 B, 4 T) | 4 T, 1 B | sets Z=1, clears C |
| `cp #0` (2 B, 8 T) | `or a` or `and a` (1 B, 4 T) | 4 T, 1 B | tests A==0, clears C |
| `ld (0xFF40), a` / `ld a,(0xFFxx)` (3 B, 16 T) | `ldh (0x40), a` (2 B, 12 T) | 4 T, 1 B | any 0xFF00-0xFFFF address, incl. HRAM |
| several I/O regs in a row | `ld c, #0x41` + `ldh a, (c)` (1 B, 8 T each) | 4 T per access | C must hold the low byte |
| `ld a, (hl)` + `inc hl` (16 T) | `ld a, (hl+)` (8 T) | 8 T | only with A |
| `inc hl` (8 T) | `inc l` (4 T) | 4 T | only if HL does not cross a 256 page (aligned buffers) |
| `jp label` (3 B, 16 T; cond 16/12) | `jr label` (2 B, 12 T; cond 12/8) | 1 B, 4 T | range -128..+127 |
| `call f` + `ret` (24+16 T) | `jp f` (16 T) tail call | 24 T | f's ret returns to your caller |
| `jr z, 1$` ... `1$: ret` | `ret z` (20/8 T) | | |
| `sla a` (2 B, 8 T) | `add a, a` (1 B, 4 T) | 4 T, 1 B | same result, Z and C (H differs) |
| 4 x `srl a` (32 T) | `swap a` + `and #0x0F` (16 T) | 16 T | for x >> 4 (and `and #0xF0` for << 4) |
| 16-bit `<< 1` with `sla l` / `rl h` (16 T) | `add hl, hl` (8 T) | 8 T | Z unchanged |
| 16-bit `>> 1` | `srl h` / `rr l` (16 T) | | no faster way |
| `push bc` / `pop bc` around code (28 T) | a free register, or HRAM temp with `ldh` (12 T each way) | | |
| branch to turn carry into a mask | `sbc a, a` after a compare (4 T) | | A = 0x00 if no carry, 0xFF if carry |
| `cpl` + `inc a` | negate A (8 T) | | |
| `ld (hl), a` with a constant | `ld (hl), #n` (12 T, no register needed) | | |

16-bit loop counters: `dec bc` sets **no flags**, so the loop is
`dec bc` / `ld a, b` / `or a, c` / `jr nz` = 8+4+4+12 = 28 T per iteration. Prefer an 8-bit
counter (`dec c` / `jr nz` = 16 T) or two nested 8-bit counters.

## Lookup tables

Aligned to 256 bytes (index in A):
```
        ld      h, #>_table     ; 8
        ld      l, a            ; 4
        ld      a, (hl)         ; 8    = 20 T
```
Unaligned table:
```
        ld      hl, #_table     ; 12
        add     a, l            ; 4
        ld      l, a            ; 4
        adc     a, h            ; 4
        sub     a, l            ; 4
        ld      h, a            ; 4
        ld      a, (hl)         ; 8    = 40 T
```
Getting 256-byte alignment: `.bndry` does **not** survive linking. Put the table in its own
area and place it with a linker flag, verified:
```
        .area   _ALIGNED        ; in the .s file
_table::
        ...                     ; 256 bytes
```
`game.json`: `"lcc_flags": ["-Wl-b_ALIGNED=0x7F00"]`, and in a test:
`assert gb.addr("table") & 0xFF == 0`. Split tables (`tbl_lo` / `tbl_hi`, 256 bytes each)
make 16-bit lookups cheap: same L, H+1.

## Multiplication

- By a constant: shifts and adds. x*10 with x in HL: `add hl, hl` (x2), `ld d, h` / `ld e, l`,
  `add hl, hl` / `add hl, hl` (x8), `add hl, de` (x8 + x2) = 8+4+4+8+8+8 = 40 T.
- 8x8 -> 16 general: shift-and-add loop, 8 iterations, 24 + 8 x (28..32) + loop overhead.
  Measured: 404 T (incl. 28 T of extra work) vs 468 T for SDCC's `__mulint` from C. Small win;
  a table of squares (`a*b = ((a+b)^2 - (a-b)^2) / 4`) is faster when it is really hot.
- Multiplying by a power of 2 in C is already a shift; the compiler handles it.

## HRAM

0xFF80-0xFFFE: `ldh` access (12 T, 2 B) vs 16 T / 3 B for WRAM via `ld (a16)`. Use it for a
few hot variables (frame counter, temporaries). GBDK already uses the start of HRAM (its OAM
DMA routine): declare variables in `.area _HRAM` and let the linker place them (first free
byte was 0xFF93 in the test ROM). From C, an `extern uint8_t hram_var;` works normally (the C
compiler accesses it with a 16-bit address; only asm benefits from `ldh`).

## Calls and the convention

- A call + ret costs 40 T; for tiny functions that matters. In C, a macro or `static inline`
  may beat an asm function call.
- Arranging arguments so they arrive where the asm needs them avoids shuffling: the first
  pointer comes in DE, a second pointer in BC, an 8-bit after a pointer in A.
- More than two arguments go on the stack: each read is `ldhl sp, #n` (12 T) + `ld r, (hl)`
  (8 T), and the callee must pop them. Prefer passing a pointer to a struct or using globals.
- Returning a 16-bit value costs `ld c, l` / `ld b, h` (8 T) if your result is in HL.

## Unrolling

Unrolling removes `dec` + `jr` (16 T per iteration) at the cost of ROM. Use `.rept n` ...
`.endm`. Partial unroll (x4, x8) gets most of the gain. Check the size in the build output.

## Walking arrays of records (measured in games/shmup, harness/common/src/gbe_pool.s)
- Array of 16-byte records beats struct-of-arrays on the SM83: one pointer walked with
  `ld a,(hl+)` instead of one 16-bit address computation per field (pool_move: C ~1000 T/object,
  asm over separate arrays ~350, asm over records ~200).
- Keep loop counters in registers, not WRAM (`ld a,(n); dec a; ld (n),a` = 36 T per iteration);
  spr_group saved ~470 T per object just by that.
- Avoid `push hl / pop hl` per record: track the offset you are at and add the rest
  (`ld a,l; add a,#13; ld l,a; jr nc,.+3; inc h`).
- Overlap test with one compare per axis: `(uint8)(y - ky) < ry` with `ky = qy - oy - oh + 1`,
  `ry = qh + oh - 1` precomputed once per call and kept in D/E (~100 T per object vs ~300).
- Precompute tables instead of shifting `int16_t` at run time (speeds x 4 levels x 32 directions =
  512 bytes of ROM, `fire` 2000 -> 960 T).
- Rotations / modulo by small counts: subtract `n*8, n*4, n*2, n` (4 steps) instead of a loop of
  single subtractions (up to 15 rounds for n = 2).

## sdasgb details met in games/shmup
- `jr` reaches -128..+127 bytes: long unrolled bodies need `jp` ("jr out of range" at link time).
- `.+3` style relative targets work inside `.rept` blocks where local labels would repeat.
- A helper shared by two .s modules must be global (`name::`); a plain `name:` is module-local and
  the linker reports "Undefined Global".
- Name scratch Python helper scripts carefully: a script called `token.py` next to the runner
  shadowed the stdlib `token` module and broke `import numpy` (PyBoy).
