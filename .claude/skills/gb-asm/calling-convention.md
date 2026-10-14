# SDCC __sdcccall(1) calling convention on SM83 (GBDK-2020 4.5.0 / SDCC 4.5.1)

`__sdcccall(1)` is the default since SDCC 4.2 / GBDK 4.1.0. Sources: SDCC manual 4.3.5
(`tools/gbdk/sdccman.pdf`), GBDK docs `04_coding_guidelines.md`, and, where they disagree,
**the code this compiler actually generates** (`lcc -S`). Legend:
**[run]** = verified by running a ROM in PyBoy, **[gen]** = verified in compiler output only.

## Arguments (functions without varargs, not BANKED)

Only the first two arguments can be in registers; everything else goes on the stack.

| 1st arg | 2nd arg | registers | status |
|---------|---------|-----------|--------|
| 8-bit | - | A | [run] |
| 16-bit or pointer | - | DE | [run] |
| 32-bit | - | DEBC (BC = low word, DE = high word) | [gen] |
| 8-bit | 8-bit | A, E | [run] |
| 8-bit | 16-bit / pointer | A, **DE** | [run] (the SDCC manual says BC; the compiler uses DE) |
| 16-bit / pointer | 8-bit | DE, A | [run] (`sum_bytes(p, n)`) |
| 16-bit / pointer | 16-bit / pointer | DE, BC | [gen] |
| 32-bit | anything | DEBC, 2nd on the **stack** | [gen] (manual suggests A for an 8-bit 2nd; compiler uses the stack) |
| struct/union (any size) | | it and all following args on the stack | manual |

`bool`, `char`, `int8_t`, `uint8_t` are 8-bit; `int`, `uint16_t`, pointers are 16-bit.

### Stack arguments

- Pushed right to left by the caller, then `call`. On entry: `SP+0` = return address,
  `SP+2` = first stack argument, and so on.
- **8-bit stack arguments take 1 byte** (the caller does `push af` / `inc sp`, or packs two
  bytes in one `push`). Example `f(a, b, c, d)` with 4 x u8: c at SP+2, d at SP+3. [gen]
- Read them with `ldhl sp, #2` then `ld r, (hl)` / `ld a, (hl+)`.
- **The callee removes the stack arguments** before returning (SM83 sdcccall(1) rule; it
  applies whatever the return type). SDCC's own epilogue, which you should copy:
  ```
  pop  hl          ; return address
  inc  sp          ; 1 byte of args   (or: add sp, #n   or: pop af for 2 bytes)
  jp   (hl)
  ```
  [run] (`sum3` below; a wrong count corrupts the stack and the test ROM dies).
- **Varargs** functions: all arguments on the stack, the caller cleans up.

## Return values

| Type | Register |
|------|----------|
| 8-bit (`uint8_t`, `bool`, `int8_t`) | A [run] |
| 16-bit, pointer | BC [run] |
| 32-bit | DEBC (DE high word) [gen] |
| struct/union, larger | memory via hidden pointer argument (manual) |

## Registers: who saves what

- **Nothing is callee-saved.** An asm function may destroy A, F, B, C, D, E, H, L. The C
  caller assumes every register is clobbered and saves what it needs itself (seen in
  compiler output: `push de` / `call` / `pop de`) [gen].
- SP must come back balanced (minus the stack args the callee pops).
- `__preserves_regs(b, c, ...)` on the **prototype** promises that the function leaves
  those registers unchanged, so the caller can keep values in them across the call
  (compiler output confirms it stops saving them) [gen]. Registers are named
  individually as 8-bit halves (`__preserves_regs(b, c, d, e, h, l)` compiles and was used
  in the verified example). It is a promise the compiler cannot check:
  if the asm breaks it, the caller computes garbage. Only use it when the function is
  short and obviously clean (e.g. `add_u8` below touches only A and F).
- Interrupts can fire during your function; GBDK's handlers save their own registers, so
  nothing special is needed unless you play with SP (popslide: `di` ... `ei`).

## BANKED functions (MBC games)

From GBDK docs (`04_coding_guidelines.md`, "Banked Calling Convention") and compiler output
[gen, not executed]:
- Caller: pushes **all** args on the stack (right to left), `ld e, #b_func` (bank),
  `ld hl, #_func`, `call ___sdcc_bcall_ehl`; after return the **caller** cleans the stack.
- The trampoline pushes the old bank (2 bytes) and its own return address, so in the
  callee the first argument is at **SP+6** (normal stack offset +4).
- Callee returns with a plain `ret`; return value in A / BC / DEBC as usual.
- A banked asm function lives in `.area _CODE_n` and must also export its bank number as
  `b_` + C name, exactly as SDCC emits for a C function `bk_add` in bank 1:
  ```
          .globl  b_bk_add
          .globl  _bk_add
          .area   _CODE_1
          b_bk_add = 1
  _bk_add::
          ldhl    sp, #6          ; first (8-bit) arg
          ...
          ret
  ```
  Declare it in C with `BANKED`. Test it on an MBC build before relying on it.

## __sdcccall(0) / OLDCALL (old convention, for reference)

All args on the stack (right to left), return 8-bit in E, 16-bit in DE, 32-bit in HLDE,
caller cleans. Only relevant for old libraries or functions marked `OLDCALL`.

## How to find the registers for any prototype

Write a C stub with the exact prototype, compile, and read it:
```
printf '#include <stdint.h>\nuint8_t f(uint16_t a, uint8_t b){return b;}\n' > stub.c
tools/gbdk/bin/lcc.exe -S -o stub.s stub.c     # look at _f:: in stub.s
```

## Worked example (verified)

Built with `lcc -Wl-m -Wl-j -Wm-ynASMTEST -Wl-b_ALIGNED=0x7F00 -o build/asmtest.gb
src/eqtest.c src/fast_c.c src/main.c src/fast.s` (same flags as `harness/gb.py` plus the
area placement) and run under PyBoy: an exhaustive equivalence test against the C versions
passed (3 x 65536 + 319 comparisons, 0 mismatches) and the measured cycles match hand counts
from opcodes.json exactly (`add_u8` 20 T, `mul8x8(200,123)` 404 T).

`src/fast.h`
```c
#include <stdint.h>
// C reference versions (fast_c.c): keep them, they are the spec
uint8_t  add_u8_c(uint8_t a, uint8_t b);
uint16_t mul8x8_c(uint8_t a, uint8_t b);
uint16_t sum_bytes_c(const uint8_t *p, uint8_t n);
uint16_t mix_a16_c(uint8_t a, uint16_t b);
uint8_t  sum3_c(uint8_t a, uint8_t b, uint8_t c);
// asm ports (fast.s)
uint8_t  add_u8(uint8_t a, uint8_t b) __preserves_regs(b, c, d, e, h, l);
uint16_t mul8x8(uint8_t a, uint8_t b);
uint16_t sum_bytes(const uint8_t *p, uint8_t n);
uint16_t mix_a16(uint8_t a, uint16_t b);
uint8_t  sum3(uint8_t a, uint8_t b, uint8_t c);
// data defined in asm / C
extern uint8_t asm_calls;          // _DATA
extern uint8_t hram_counter;       // _HRAM
extern const uint8_t sq_lo[256];   // 256-aligned ROM table
extern uint8_t c_scale;            // C global read by asm (defined in fast_c.c, = 3)
```

`src/fast.s`
```
;; fast.s - asm ports of fast_c.c (SDCC __sdcccall(1), the GBDK 4.x default)
        .module fast
        .globl  _c_scale        ; C global defined in fast_c.c

        .area   _DATA
_asm_calls::                    ; uint8_t asm_calls (visible to C and to tests)
        .ds     1

        .area   _HRAM
_hram_counter::                 ; uint8_t hram_counter (0xFF80-0xFFFE, use ldh)
        .ds     1

        .area   _CODE

;; uint8_t add_u8(uint8_t a, uint8_t b) __preserves_regs(b, c, d, e, h, l)
;; in: A=a, E=b   out: A          20 T including ret
_add_u8::
        add     a, e
        ret

;; uint16_t mul8x8(uint8_t a, uint8_t b)
;; in: A=a, E=b   out: BC = a*b   (shift-and-add, MSB first)   404 T for (200,123)
_mul8x8::
        ld      hl, #0
        ld      d, h            ; DE = b
        ld      b, #8
1$:     add     hl, hl          ; result <<= 1 (never overflows: result < 2^16)
        add     a, a            ; next bit of a -> carry
        jr      nc, 2$
        add     hl, de
2$:     dec     b
        jr      nz, 1$
        ld      c, l
        ld      b, h
        ldh     a, (_hram_counter)   ; HRAM variable through ldh with a symbol
        inc     a
        ldh     (_hram_counter), a
        ret

;; uint16_t sum_bytes(const uint8_t *p, uint8_t n)
;; in: DE=p, A=n   out: BC = sum
_sum_bytes::
        ld      h, d
        ld      l, e
        ld      bc, #0
        or      a, a
        ret     z               ; n == 0
        ld      e, a            ; E = counter
1$:     ld      a, (hl+)
        add     a, c
        ld      c, a
        jr      nc, 2$
        inc     b
2$:     dec     e
        jr      nz, 1$
        ld      hl, #_asm_calls
        inc     (hl)
        ret

;; uint16_t mix_a16(uint8_t a, uint16_t b)
;; in: A=a, DE=b (NOT BC as the SDCC manual says)   out: BC = b + a
_mix_a16::
        add     a, e
        ld      c, a
        ld      a, d
        adc     a, #0
        ld      b, a
        ret

;; uint8_t sum3(uint8_t a, uint8_t b, uint8_t c)
;; in: A=a, E=b, c at SP+2   out: A = a + b + c*c_scale
;; The CALLEE removes the 1 byte of stack args.
_sum3::
        add     a, e
        ld      d, a            ; D = a + b
        ldhl    sp, #2
        ld      e, (hl)         ; E = c
        ld      a, (_c_scale)   ; read a C global
        or      a, a
        jr      z, 2$           ; c_scale == 0 -> A = 0
        ld      b, a            ; B = loop counter
        xor     a, a
1$:     add     a, e
        dec     b
        jr      nz, 1$
2$:     add     a, d
        pop     hl              ; return address
        inc     sp              ; drop 1 byte of stack args
        jp      (hl)

;; 256-aligned table: own area, placed with lcc flag -Wl-b_ALIGNED=0x7F00
        .area   _ALIGNED
_sq_lo::                        ; low byte of i*i, i = 0..255
        i = 0
        .rept   256
        .db     <(i*i)
        i = i + 1
        .endm
```

`src/fast_c.c`
```c
#include "fast.h"
uint8_t c_scale = 3;
uint8_t add_u8_c(uint8_t a, uint8_t b) { return a + b; }
uint16_t mul8x8_c(uint8_t a, uint8_t b) { return (uint16_t)a * b; }
uint16_t sum_bytes_c(const uint8_t *p, uint8_t n) {
    uint16_t s = 0;
    while (n--) s += *p++;
    return s;
}
uint16_t mix_a16_c(uint8_t a, uint16_t b) { return b + a; }
uint8_t sum3_c(uint8_t a, uint8_t b, uint8_t c) { return (uint8_t)(a + b + c * c_scale); }
```

`game.json` needs `"lcc_flags": ["-Wl-b_ALIGNED=0x7F00"]` for the table area (0x7F00-0x7FFF
must be free: check the build's ROM usage). Verified in the ROM: `sq_lo` at 0x7F00,
`hram_counter` at 0xFF93, `asm_calls` in WRAM, all readable with `gb.u8()` by C name.
The equivalence/measurement code that exercised all of this is in equivalence-testing.md.
