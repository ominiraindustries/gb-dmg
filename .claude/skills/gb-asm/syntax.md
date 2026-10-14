# sdasgb syntax as used by GBDK-2020

GBDK assembles `.s` files with `sdasgb` (ASxxxx family, Z80-style mnemonics). It is **not**
RGBDS: no `SECTION`, no `$FF` hex, no `[hl]`, no `ldi`. Everything below was assembled
with the installed sdasgb (listing checked) unless marked otherwise.

## Statement format

```
label:  mnemonic operand, operand     ; comment
```
- Comments start with `;` (GBDK sources often use `;;` for block comments).
- Mnemonics, registers and directives are case-insensitive (`LD A,#5` works; GBDK's
  examples mix cases). Symbols are case-sensitive.
- One directive or instruction per line.

## Numbers and expressions

| Write | Meaning |
|-------|---------|
| `#5`, `#0x1F`, `#0b0101`, `#'A` | immediate operand (the `#` is required) |
| `0x1F`, `0X1F`, `0h1F`, `$$1F` | hex. `$10` is **not** hex (error) |
| `0b0101`, `$%0101` | binary |
| `10` | decimal (default radix). `cp #10` compares with 10, not 16 |
| `0o17`, `0q17` | octal |
| `<expr`, `>expr` | low byte / high byte (`ld a, #<_buf`, `ld h, #>_table`) |
| `+ - * / % << >> & \| ^ ~` | arithmetic; precedence `* / %` > `+ -` > `<< >>` > `^` > `&` > `\|`; use parentheses |
| `.` | current location counter |

- Without `#`, an operand is an address: `ld a, 5` is an error ("Invalid Addressing Mode"),
  `ld a, (5)` reads memory.
- Memory operands use parentheses: `ld a, (hl)`, `ld a, (_var)`, `ld (_var), a`.
  `ld a, (#_var)` (what SDCC emits) is the same instruction.
- A hex number starting with a letter needs the prefix (`0xFF`), otherwise it is a symbol.

## Instruction spellings specific to SM83 in sdasgb

| sdasgb | Notes |
|--------|-------|
| `ld a, (hl+)` / `ld (hl+), a` / `ld a, (hl-)` / `ld (hl-), a` | `ldi`/`ldd` are rejected |
| `ldh a, (0x44)`, `ldh (0xFF44), a`, `ldh (.LY), a`, `ldh (_hram_var), a` | 8-bit offset, full 0xFFxx address, or an HRAM symbol all work. `in`/`out` are rejected |
| `ldh a, (c)` / `ldh (c), a` | address 0xFF00+C |
| `ldhl sp, #2` | `ld hl, sp+e8` (opcode F8). `ld hl, sp` is rejected |
| `add sp, #-4` | signed 8-bit |
| `ld (_var), sp` | store SP (20 T) |
| `jp (hl)` | jump to HL (4 T) |
| `stop` | assembles to 2 bytes `10 00` (the manual's 1-byte claim is outdated) |
| `xor a` = `xor a, a`, `sub b` = `sub a, b` | the `a,` is optional for ALU ops |
| `swap a`, `bit 7, (hl)`, `set 3, b`, `res 0, a` | CB ops |

Full list of forms with bytes/cycles: `opcodes.md`.

## Labels and symbols

- `name:` local to the file; `name::` global (exported). `.globl name` also exports a
  definition or declares an external reference (undefined symbols are treated as external
  anyway, but write `.globl` for externals as documentation).
- **C mapping**: the C identifier `foo` is `_foo` in asm, for both functions and variables.
  A C `static` variable/function is emitted with a single colon and is not visible to other
  files or to the test harness.
- Labels may contain `A-Z a-z 0-9 . $ _`, must not start with a digit. GBDK's own library
  uses a leading dot for internal symbols (`.copy_vram`, `.LY`), which C code cannot name.
- **Reusable local labels**: `1$:` ... `65535$:`. Their scope is between two normal labels,
  so every function can have its own `1$`. Assignments (`X = 5`) do not end the scope.
  Inside inline asm in a C function always use `n$` labels (GBDK docs: named labels break the
  compiler's own local-label scoping without warning).

## Constants

```
SPEED   = 3              ; local constant (not a label, no storage)
MAXX    == 152           ; '==' makes it global
        .equ   LIMIT, 8  ; also allowed (.equ / .gblequ / .lclequ)
```
`.include "global.s"` (found automatically by lcc) gives GBDK's hardware equates:
`.LY = 0x44` (offset, for `ldh`), `rLY = 0xFF44`, `.LCDC`, `.STAT`, `.BGP`, `.P1`, ...
(see `tools/gbdk/lib/gb/global.s`). Verified: `ldh a, (.LY)` and `ldh a, (rLY)` both give `F0 44`.

## Areas (sections)

Put code and data in GBDK's areas; the linker concatenates same-named areas from all files.

| Area | Use |
|------|-----|
| `.area _CODE` | code and constant data in ROM bank 0 (non-banked). SDCC puts C `const` arrays here too |
| `.area _CODE_n` | code/data in switchable ROM bank n (needs an MBC; see calling-convention.md for banked calls) |
| `.area _DATA` | uninitialized RAM variables (`.ds n`) in WRAM 0xC000-0xDFFF |
| `.area _HRAM` | variables in HRAM 0xFF80-0xFFFE, reachable with `ldh`. GBDK already uses the first bytes (in the test ROM the first free byte was 0xFF93); let the linker place it, never hard-code |
| `.area _INITIALIZED` + `.area _INITIALIZER` | how SDCC does initialized RAM (`.ds` in the first, the initial bytes as `__xinit__name` in the second, same order). In hand-written asm prefer `_DATA` and initialize in code |
| `.area _HOME`, `_BASE`, `_LIT`, `_GSINIT`, `_GSFINAL`, `_HEADER` | GBDK/SDCC internals; do not use for your code |
| `.area NAME (ABS)` + `.org addr` | absolute placement; nothing checks for overlap with other code |
| custom `.area _MYAREA` + lcc flag `-Wl-b_MYAREA=0x7F00` | place a whole area at an address (verified; used for 256-aligned tables) |

Do not rely on RAM being zero at boot: initialize asm variables explicitly.

## Data directives

```
        .db     1, 2, 0x03, 0b101, 'A    ; bytes (.byte, .fcb are synonyms)
        .dw     _label, 0x1234           ; little-endian words (.word, .fdb)
        .ds     16                       ; reserve 16 bytes (.blkb, .rmb, .rs)
        .ascii  "HI"                     ; no terminator
        .asciz  "HI"                     ; NUL-terminated (.strz)
        .tile   " *****  "               ; one 8-pixel row of a 2bpp tile -> 2 bytes (0x7C 0x7C)
```
Repetition and conditionals:
```
        i = 0
        .rept   256                      ; generates 256 bytes: low byte of i*i
        .db     <(i*i)
        i = i + 1
        .endm

        .if     DEBUG                    ; .if/.else/.endif, .ifdef, .ifndef
        .endif
```
Macros: `.macro name, arg1, arg2` ... `.endm` (asmlnk_manual.txt chapter 2).

**Alignment**: `.bndry 256` only aligns relative to the start of this file's piece of the
area; after linking, the alignment is NOT preserved (asmlnk manual 1.4.21). For a 256-aligned
table use its own area placed with `-Wl-b_AREA=0xXX00` (add to `lcc_flags` in game.json) and
assert `gb.addr("table") & 0xFF == 0` in a test.

## Declaring the asm function to C

```c
// header shared by C files
uint8_t  add_u8(uint8_t a, uint8_t b) __preserves_regs(b, c, d, e, h, l); // optional promise
uint16_t sum_bytes(const uint8_t *p, uint8_t n);
extern uint8_t asm_calls;          // a variable defined in asm as _asm_calls:: .ds 1
extern const uint8_t sq_lo[256];   // ROM table defined in asm
```
GBDK macros: `PRESERVES_REGS(b, c)` = `__preserves_regs(b, c)`, `NAKED` = `__naked`,
`OLDCALL` = `__sdcccall(0)`, `BANKED` = `__banked`.

## Inline asm in C

```c
void f(void) {
    __asm__("nop");          // one line
    __asm
        ld   a, #1
        ld   (_g8), a        ; C globals by _name
    __endasm;
}

// Whole function in asm, no prologue/epilogue: you must write the ret.
// Arguments arrive exactly as for a .s function (sdcccall(1)).
uint8_t naked_inc(uint8_t a) __naked {
    (void)a;                 // silences "unreferenced function argument"
    __asm
        inc  a
        ret
    __endasm;
}
```
Verified at runtime (`naked_inc(41) == 42`). In a non-naked function you cannot know
which registers hold which C locals; only touch globals and preserve what you change, or
better, write the whole function in a `.s` file or as `__naked`.

## Seeing what SDCC generates (the best reference)

```
tools/gbdk/bin/lcc.exe -S -o out.s src/file.c       # asm of a C file
tools/gbdk/bin/lcc.exe -Wa-l -c -o out.o src/x.s    # listing out.lst with bytes and [cycles]
```
The listing (`.lst`) shows bytes and T-cycles per instruction; for conditional
instructions it shows only the taken count (e.g. `jr nz` `[12]`, not taken is 8).
`-Wa-l` on a `.c` file also gives a listing of the compiled C.
