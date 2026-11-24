---
name: gb-asm
description: SM83 (Game Boy CPU) assembly for GBDK-2020 projects. Use when writing, reading, optimizing or porting Game Boy asm, mixing .s files or inline asm with GBDK C (sdasgb syntax, SDCC __sdcccall(1) calling convention, __naked, __preserves_regs), counting cycles or VBlank budgets, or deciding whether a C hot path should be ported to asm.
---

# SM83 assembly with GBDK-2020 (4.5.0, SDCC 4.5.1)

> Knowledge base first: `python -I harness/scripts/kb.py query "..." --kind api,ref,tecnica` (gbe asm pieces, Pan Docs,
> technique cards); then the detail files below. Asm only after profiling, always with its C reference and selftest.

Toolchain facts in this skill were checked against the installed tools (`tools/gbdk`) by
building and running test ROMs under PyBoy; cycle counts come from `reference/opcodes.json`.
If a doc and the compiler disagree, **the compiler output wins** (`lcc -S file.c` shows it).

## When to port to asm

Only when **all** of these hold:
1. A measurement shows the function matters (cycles per frame, or it makes the frame miss
   VBlank). Measure with `measure_cycles()` (see equivalence-testing.md) or the cycle column
   of an `lcc -Wa-l` listing. Do not port on intuition.
2. The C version has already been fixed at the algorithm/data level (tables, `uint8_t`,
   globals instead of pointers to structs, no `*`/`/`/`%` by non-powers of 2). Those changes
   are usually worth more than asm.
3. The function is small and self-contained (a loop, a copy, a collision check, a multiply).
   Whole game logic in asm is not maintainable.

Measured examples: a byte-sum loop `sum_bytes(p, 100)` C 7648 T vs asm 4472 T (SDCC
handles 16-bit accumulators/pointer loops poorly); `mul8x8` C 468 T vs asm 404 T (SDCC's
`__mulint` is already decent: small win); a 64-byte copy with GBDK `memcpy` 1980 T vs an
unrolled asm copy 1268-1452 T. Expect big wins in tight loops, little elsewhere.

## Porting procedure (always all steps)

1. **Keep the C version** and rename it `foo_c` (same prototype). It is the specification.
2. Write `foo` in `src/<name>.s` (any `.s` in `src/` is built by `python harness/gb.py build`).
   Get the argument registers from calling-convention.md; when unsure, write a C stub with
   the same prototype, run `lcc -S` and read where it reads its arguments.
3. Declare the prototype in a header shared by C and tests. Add `__preserves_regs(...)` only
   if you are sure (it is a promise; breaking it corrupts the caller silently).
4. **Equivalence test** (equivalence-testing.md): an `eq_run()` in the ROM runs `foo_c` and
   `foo` over exhaustive (8-bit x 8-bit = 65536 cases) or seeded-random inputs plus edge
   cases (0, 1, 0x7F, 0x80, 0xFF, n = 0, max length), counts mismatches into globals;
   pytest triggers it, asserts `eq_mismatch == 0`, and checks a checksum against a Python
   oracle (catches C and asm being wrong the same way).
5. **Measure** both with `measure_cycles()`; keep the asm only if the gain matters. Record
   the numbers in a comment above the asm function.
6. Run the whole game test suite (`python harness/gb.py test <game>`): calling-convention
   bugs often show up as corruption elsewhere (stack imbalance, clobbered registers).

## SM83 is not a Z80 (things that bite)

- No IX/IY, no shadow registers, no `ex`, no `djnz`, no `ldir`/block ops, no `in`/`out`,
  no 16-bit `ld hl,(nn)` / `ld (nn),hl`, no `sbc hl`/`adc hl`, no sign (S) or parity (P/V)
  flags, so no `jp p/m/pe/po`. Only Z N H C (F bits 7..4).
- Added: `ld a,(hl+)` / `ld (hl+),a` / `(hl-)` (8 T), `ldh` for 0xFF00-0xFFFF (12 T, 2
  bytes, also reaches HRAM), `ldh a,(c)`, `ld (a16),sp`, `ldhl sp,#e8`, `add sp,#e8`, `swap r`.
- `inc rr`/`dec rr` (16-bit) set **no flags**: `dec bc; jr nz` tests a stale Z flag. Test
  with `ld a,b; or a,c`. `inc r`/`dec r` (8-bit) set Z but **not C**.
- Rotates on A (`rla`, `rlca`, `rra`, `rrca`) always clear Z; the CB versions set Z.
- Interrupts: `ei` takes effect after the next instruction. `reti` = `ei` + `ret`.
- Opcodes D3 DB DD E3 E4 EB EC ED F4 FC FD lock the CPU.

## sdasgb syntax in one breath (details: syntax.md)

`#` for immediates (`ld a, #5`; `ld a, 5` is an error), `(x)` for memory, hex `0x1F`,
binary `0b0101`, `<sym`/`>sym` low/high byte, `name::` global label, `1$:` local label
(scope ends at the next normal label), `.area _CODE` / `_DATA` / `_HRAM`, `.db .dw .ds`.
C symbol `foo` is `_foo` in asm. The asmlnk manual's ASGB appendix is outdated: GBDK's
sdasgb rejects `ldi`/`ldd`/`in`/`out`; use `ld a,(hl+)`, `ldh`.

## __sdcccall(1) in one table (details: calling-convention.md)

| Arguments (first, second)  | Registers |
|----------------------------|-----------|
| `u8`                       | A |
| `u16` or pointer           | DE |
| `u8, u8`                   | A, E |
| `u8, u16/ptr`              | A, DE (the SDCC manual says BC: wrong, verified) |
| `u16/ptr, u8`              | DE, A |
| `u16/ptr, u16/ptr`         | DE, BC |
| `u32, ...`                 | DEBC (DE = high word), 2nd arg on the stack |
| 3rd and later args, structs | stack, pushed right to left; first stack arg at SP+2 on entry; 8-bit args take 1 byte |

Return: 8-bit (`uint8_t`, `bool`, `int8_t`) in A; 16-bit and pointers in BC; 32-bit in
DEBC; structs through a hidden pointer.

- The **callee** removes stack args (`pop hl` / `add sp,#n` or `inc sp` / `jp (hl)`),
  except vararg functions (caller cleans).
- **No register is callee-saved**: asm may clobber AF BC DE HL unless the prototype says
  `__preserves_regs(...)`. SP must be balanced.
- `BANKED` functions: all args on stack, first at SP+6, caller cleans, return as above.

## Cycle facts to remember (T-states)

Frame 70224 T, scanline 456 T, VBlank 4560 T (10 lines). GBDK's VBlank ISR + `vsync()`
return measured at about 1136 T in the template game (includes the 640 T OAM DMA), leaving
about 3400 T of VBlank after `vsync()`. Copying to VRAM costs 18-40 T/byte depending on the
loop (optimization.md). `call`+`ret` = 40 T; `push`+`pop` = 28 T.

## For X read Y

| Need | Read |
|------|------|
| Exact bytes/cycles/flags of an instruction | `opcodes.md` (generated; regenerate with `python harness/scripts/gen_opcodes.py --check`) |
| Directives, areas, labels, constants, data, inline asm, C symbol mapping | `syntax.md` |
| Register/stack rules, __preserves_regs, banked, worked verified example | `calling-convention.md` |
| Idioms with cycle counts, VBlank/scanline budgets, VRAM copy rates | `optimization.md` |
| C vs asm equivalence test + cycle measurement code for our harness | `equivalence-testing.md` |
| Instruction semantics in depth (flags, timing per M-cycle) | `reference/gbctr.pdf` pages 20-139 (ch. 6; 8-bit ALU p.46, 16-bit p.78, CB ops p.83, control flow p.117, HALT/DI/EI p.131) |
| Opcode encoding, Z80 differences | `reference/pandocs/src/CPU_Instruction_Set.md`, `CPU_Comparison_with_Z80.md` |
| PPU modes / when VRAM is accessible | `reference/pandocs/src/Rendering.md`, `Accessing_VRAM_and_OAM.md` |
| Assembler/linker directives in full | `tools/gbdk/asmlnk_manual.txt` (sections 1.3-1.4; ignore ASGB mnemonics `ldi/ldd/in/out`) |
| Hardware register names usable from asm | `tools/gbdk/lib/gb/global.s` (`.include "global.s"`) |
| SDCC calling convention text | `tools/gbdk/sdccman.pdf` section 4.3.5 (but see the corrections above) |
| GBDK on asm/C mixing, areas, banked trampoline | `reference/gbdk-src/docs/pages/03_using_gbdk.md`, `04_coding_guidelines.md` ("When C isn't fast enough", "Calling convention") |
