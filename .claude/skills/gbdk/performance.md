# Fast and small C with SDCC on the Game Boy (sm83)

Sources: `docs/pages/04_coding_guidelines.md`, `03_using_gbdk.md` (Mixing C and ASM),
`06_toolchain.md`, `20_toolchain_settings.md`, plus measurements made with the GBDK 4.5.0
compiler (`lcc -S -Wf--max-allocs-per-node50000`, instruction counts per function).
Rule zero: **measure**. Several "classic" tips do not hold for current SDCC (table below).

## Budget
70224 cycles/frame (T-states) = 17556 M-cycles at 59.7 Hz. A typical `ld a,(nn)` is 16 T,
`add a,b` 4 T, `call`+`ret` 24+16 T. Most of a frame is available to game logic because OAM is
DMA'd by the VBlank ISR; VRAM writes with the LCD on wait for HBlank/VBlank.

## Measured: what SDCC 4.5 actually generates
| C code | Result (instructions) | Lesson |
|---|---|---|
| `uint8_t a; a / 8` and even `a / 8u` | 10, **16-bit** shift loop | integer promotion: write `a >> 3` (4 instr: `swap; rlca; and`) |
| `a % 8`, `a % 8u`, `a & 7` | 2 each | modulo by power of 2 is fine |
| `int8_t a; a / 8` | 18 | signed division by 2^n is expensive; use `>>` only if you accept floor semantics |
| `a * b` (both vars) | `call __muluchar` | runtime multiply: avoid in hot loops |
| `a / b` (vars) | `call __divuchar` | avoid; use tables, reciprocal multiply, or BCD for score display |
| `a * 3`, `(uint16_t)a * 40` | 4 / 13, inline shifts+adds | multiply by constant is cheap |
| `int i; if (i < 100) i++;` vs `uint8_t` | 23 vs 6 | 16-bit signed is ~4x code |
| `player.x += player.dx; ...` (global struct, fixed field) | 13 | best: address is a link-time constant |
| same via `ent_t *e` parameter | 21 | pointer deref costs |
| same via `ents[i].x` (array of structs, index) | 34 | index math repeated for every field |
| loop `objs[i].x += objs[i].dx` (AoS, 4-byte struct) | 21 | compiler strength-reduces `i*4` |
| loop `obj_x[i] += obj_dx[i]` (struct of arrays) | 19 (23 without max-allocs) | SoA slightly better here |
| pointer walk `p->x += p->dx; p++` with `for(i=N;i;i--)` | 27, counter spilled to stack | "advancing pointer + down-counter" was *worse* here |
| `for (i=0;i<8;i++)` vs `do { arr[--i] } while(i)` | 11 vs 11 | count direction rarely matters now |
| local `uint8_t t[8]` vs `static uint8_t t[8]` | 21 vs 16 | locals on the stack cost (`ldhl sp`) |
| `-Wf--max-allocs-per-node50000` | e.g. 23 -> 19 | free speed: enable it (slower compiles) |

## Guidelines (docs + measurements)
Types
- `uint8_t` everywhere possible; unsigned over signed (shorter compares, no sign handling).
  Use `stdint.h` types and `stdbool.h` `bool`. No `float` (unsupported).
- Use `u` suffix on constants combined with unsigned values (`127u`) to avoid
  "overflow in implicit constant conversion" warnings and accidental int math.
- Fractional movement: 8.8 fixed point with the `fixed` union (`.w` add speed, `.h` = pixel) or
  `uint16_t pos` with `pos >> 4` (4 subpixel bits; `examples/cross-platform/simple_physics`).
- chars are signed by default with lcc (`--fsigned-char`); `char` != `uint8_t`.

Data placement
- `const` for every table/graphic: goes to ROM. A non-const initialized array costs ROM for the
  initializer **plus** RAM **plus** copy time at boot (and slows compiling).
- Globals and `static` locals beat stack locals, except 1-2 scalar locals in simple code (registers).
  Never put big arrays on the stack. Trade-off: loses re-entrancy (fine except for ISR-shared code).
- Hot single-byte state can live in HRAM: `SFR my_var;` (treated as `volatile uint8_t`, `ldh` access).
- Keep game maps/collision data in WRAM/ROM; never read back from VRAM (`get_bkg_tile_xy` stalls).

Arithmetic
- No `*`, `/`, `%` by variables in per-frame code. Powers of two: shifts/masks written explicitly
  for `uint8_t`. Otherwise lookup tables (`const uint8_t row_offset[]`) or precomputed values.
- Scores: BCD (`gb/bcd.h`: `bcd_add`, `bcd2text`) avoids division when printing.
- Random range: `(uint8_t)(((rand() & 0xFFu) * n) >> 8)` instead of `rand() % n`.

Structures and loops
- Fixed globals (`player.x`) are cheapest. For entity pools, struct-of-arrays and AoS are close;
  index once into a local pointer only if the compiler doesn't already (check the asm).
- Read `joypad()` once per frame into a variable.
- Cache expensive expressions in a local `uint8_t` before a loop; keep loop bodies small.
- `switch` on dense small values compiles to a jump table; long `if/else` chains do not.

Functions
- Few parameters: with `__sdcccall(1)` (default since GBDK 4.1) the first two go in registers;
  more go on the stack. Callee pops stack args (seen in generated code).
- `inline` / `static inline` functions work (used heavily in gb.h); macros also fine.
- No recursion. Avoid function pointers in hot paths (indirect call + no register args knowledge).
- `BANKED` calls go through a trampoline and always pass args on the stack: keep per-frame hot code
  in bank 0 or the same bank (see `banking.md`).
- Don't use `printf`/`sprintf` in game code; `waitpad()` burns CPU (no HALT): use `joypad()`+`vsync()`.

ISRs
- Keep them very short; share data via globals; access multi-byte shared vars from main code inside
  `CRITICAL { }` (`__critical`); `volatile` if polled.

## Calling convention `__sdcccall(1)` (verified by compiling)
| Signature | Args | Return |
|---|---|---|
| `uint8_t f(uint8_t a, uint8_t b)` | a=A, b=E | A |
| `uint16_t f(uint16_t a, uint16_t b)` | a=DE, b=BC | BC |
| `f(uint8_t a, uint16_t b)` | a=A, b=DE | |
| `f(uint16_t a, uint8_t b)` | a=DE, b=A | |
| 3rd+ args | stack, popped by callee | |
| `uint32_t f(uint32_t)` | DEBC (DE high) | DEBC |
C symbol `foo` is `_foo` in asm. `OLDCALL` = `__sdcccall(0)` (all args on stack, 8-bit return in E,
16-bit in DE) - used by many gb.h functions; check the prototype before calling from asm.
Function pointers to OLDCALL functions need `OLDCALL` in the typedef (`09_migrating_new_versions.md`).

## Keywords
| Keyword | Meaning |
|---|---|
| `CRITICAL` / `__critical { ... }` | block with interrupts disabled (restores previous state) |
| `void f(void) CRITICAL INTERRUPT` | raw ISR for `ISR_VECTOR` only, never for `add_*` handlers |
| `NAKED` / `__naked` | no prologue/epilogue/ret; body must be asm and end with `ret` |
| `PRESERVES_REGS(b, c)` | promise to the compiler that the function keeps those regs |
| `NONBANKED` / `__nonbanked` | force function into bank 0 (`_HOME`) even in a banked file |
| `BANKED` / `__banked` | far-call calling convention (does not choose the bank itself) |
| `SFR` / `__sfr` | HRAM variable; `AT(addr)` / `__at` fixed address |
| `volatile` | value changes outside normal flow (ISR, hardware); stops optimizer removing reads |

## Inline and separate asm (sdasgb syntax, not RGBDS)
```c
#include <gb/gb.h>
#include <stdint.h>

// Whole function in asm: a in A, b in E, result in A (sdcccall(1))
uint8_t add_sat(uint8_t a, uint8_t b) NAKED {
    a; b;               // silence "unreferenced argument" warnings
    __asm
        add a, e
        ret nc
        ld a, #0xFF
        ret
    __endasm;
}

uint8_t result;

void main(void) {
    __asm__("nop");     // one-liner
    result = add_sat(200, 100);   // 255
    while (1) vsync();
}
```
- Immediates need `#` (`ld a, #0xFF`); globals are `_name`; labels inside inline asm must be
  reusable local labels (`1$:`), never named labels (`04_coding_guidelines.md`).
- `.s` files: `.globl _func`, `.area _CODE` (or `_CODE_<bank>`), then `_func:` ... `ret`.
  Our harness compiles every `src/**/*.s` automatically.
- Prefer writing the whole function in asm instead of mixing C and asm in one function.

## Inspecting generated code
| Goal | Command (run from the game dir, same flags as game.json) |
|---|---|
| asm with C source lines as comments | `lcc -S -o build/main.asm src/main.c` |
| listing with **T-cycle counts** per instruction | `lcc -c -o build/main.o src/main.c` -> `build/main.lst` + `build/main.asm` (`[16]` = cycles) |
| more compiler comments | add `-Wf--fverbose-asm` or `-Wf--i-code-in-asm` |
| see exact tool commands | `lcc -v ...` |
| function sizes | `build/<game>.map` (with `-Wl-m`), or `romusage build/<game>.map -a` |
Note: in a one-shot `lcc -o x.gb a.c b.c` build, `.lst`/`.asm` files go to a temp dir and are deleted;
compile the file separately with `-c`/`-S` to keep them.

## Measuring at runtime
- Emulicious/BGB: `EMU_PROFILE_BEGIN("label")` ... `EMU_PROFILE_END("label")` from
  `gbdk/emu_debug.h` print elapsed clocks (divide by 2 in normal speed, see header). `toolchain.md`.
- Cheap in-game meter: read `LY_REG` right before `vsync()`; store it in a global (e.g. `cpu_ly`).
  LY 144-153 = VBlank. If logic finishes at line L in the same frame, used about `(L+10)/154` of the
  frame (counted from VBlank start at 144). If it regularly passes 144 again you drop to 30 fps.
  The PyBoy tests can read the global by name and assert a budget.
- Compare two C versions with `-S` instruction counts and `.lst` cycle counts before porting to asm
  (CLAUDE.md: asm only with an equivalence test).

## Measured in games/platformer (actors, physics, sprites)
| Pattern | Cost | Better |
|---|---|---|
| `act_x[i] += ...` with variable `i` across 6 parallel arrays (8.8 pos += vel) | ~1500 T | asm `act_move` (~240 T), see games/platformer/src/vram.s |
| Map lookup `level[((x >> 4) << 3) | row]` + attr in C | ~372 T | asm `solid_at` (~190 T); trick: `(x >> 4) << 3 == (x >> 1) & ~7` |
| Loop over 4 fixed slots with `arr[BASE + i]` | ~8900 T | unrolled with constant indices ~5300 T |
| `set_sprite_tile` + `set_sprite_prop` + `move_sprite` per sprite | ~300 T | write `shadow_OAM[n]` fields through a pointer; `memset` ranges to hide |
| Enemy physics every frame (5 enemies) | 5 x 3300 T | half rate (alternate halves, double step); player collision every frame |

## Measured in games/shmup (pools of 16-byte records, per-object logic, sound)
| Pattern | Cost | Better |
|---|---|---|
| Per-object logic in C through `pool_obj_t *o` in one big loop (6 enemies: age, route, anim, steering) | ~1500 T per object | small functions taking the pointer (`enemy_frame(o)`, `enemy_think(o)`): SDCC keeps `o` in a register pair, ~600-900 T; "think" on alternate frames per object (`(i ^ frame) & 1`) |
| Same C even for trivial work (`tm++`, two compares) | ~470 T per object | skip the call for types that only need `o->tm++` |
| `fire()` (alloc + 13 field writes + speed by switch/shifts) | ~2000 T per bullet | asm with precomputed speed tables (`aim_vx/aim_vy[spd*32+dir]`) ~960 T |
| `sfx()` through `const sfx_t *` (and even with `memcpy` to the registers) | ~1000-1300 T | asm, `ldh (c),a` x5: ~300 T (gbe_sfx_asm.s) |
| `add_score` composing 6 HUD digits every call | ~1070 T, 12x in a bomb frame | add only, mark dirty, compose once per frame in `hud_update` |
| VBlank queue of 4-tile metatiles copied in C (`d[0..33] = q[..]`) | ~600 T per metatile (4 ran past VBlank) | asm `vram_mt4_list` ~100 T |
| `aim_at` with `int16_t` differences + halving loop | ~1300 T | halve the coordinates first (8-bit, 1 px error) ~650 T incl. `aim_dir` |
| struct pointer access in general | SDCC keeps the pointer on the stack in big functions: every `o->f` is ~10 instructions (`ldhl sp`, two loads, add offset) | fewer fields per function, locals for repeated fields, or asm for loops over many records |
| 5 OAM groups (`spr_group`) per frame, 29 records | ~11-13k T (~300 T per drawn object) | the record layout (`+1 x .. +12 tile`) forces pointer jumps; a draw-friendly layout (`t y x tile prop` first) would be the next step |
Lesson: the frame peak was 4 medium costs at once (sprites 13k, enemy logic 9-15k, collisions 11k,
movement 7k), not one hot spot. Use `gb.worst_frames(...)` to see inside the worst frame, not
per-call averages. A synthetic "all pools full" cheat under-reported the peak (112 vs 128 lines):
always also run a bot through the real level.

## GBDK library speed (measured in games/dungeon, GBDK 4.5.0)
| Function | Cost | Note |
|---|---|---|
| `memcpy`, `memset` | ~8-12 T per byte | asm: use them |
| `memmove` | ~190 T per byte (60 bytes = 11.3k T) | C. A forward copy to a lower address is safe with memcpy |
| `strncpy` | ~290 T per byte | C. Write a 3-line loop |
| `set_bkg_tiles` | ~520 T per tile, waits for STAT | VBlank / LCD off only; prefer direct writes or gbe_vq |

## Measured in games/dungeon (grid crawler, M1b)
| Pattern | Cost | Better |
|---|---|---|
| "Is there a monster / item at (x, y)?" scanning lists of 12 / 24 | ~1.2k T per lookup, ~9k T per frame in sprites + AI | occupancy maps `mon_map[256]`, `item_map[256]` (index + 1), updated on move / death / pickup |
| Seen-cell marking with `d * dx` multiplies + C walkable calls | ~60k T | reuse the classes the view already computed + offset tables (gbe `view_mark_seen`, ~8k) |
| HUD digits with `/ 10` and `% 10` | ~14k T for one row | subtract-10 loop, tiles written directly (~3.7k) |
| A step frame doing everything (compose + AI + sprites + seen + HUD) | > 1 frame | compose alone on that frame; seen cells next frame; sprites not rebuilt (the old view is still shown); AI on alternate halves with timers -2 |
| `uint8_t` timer compared with 300 | never fires | SDCC warning 94 is now a build error (gb.py) |

