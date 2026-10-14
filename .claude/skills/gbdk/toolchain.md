# Toolchain: lcc flags, output files, romusage, debugging

Sources: `docs/pages/06_toolchain.md`, `20_toolchain_settings.md`, `02_links_and_tools.md`
(debugging tools), `08_faq.md`, `gbdk/emu_debug.h`, `gb/crash_handler.h`. Commands verified with
GBDK 4.5.0 on Windows (`lcc -v` shows the exact sub-commands).

## Pipeline
`lcc` drives: `sdcc` (C -> asm -> .o via `sdasgb`) -> optional `bankpack` (`-autobank`) -> `sdldgb`
(link -> .ihx) -> `ihxcheck` (overlap warnings) -> `makebin` (.ihx -> .gb + header).
Pass-through prefixes: `-Wp` preproc, `-Wf` compiler, `-Wa` assembler, `-Wb` bankpack,
`-Wl` linker, `-Wi` ihxcheck, `-Wm` makebin. lcc always adds `--fsigned-char` and
`-D__PORT_sm83 -D__TARGET_gb`, links `crt0.o`, `sm83.lib`, `gb.lib`, and sets
`-g _shadow_OAM=0xC000 -g .STACK=0xE000 -b _DATA=0xC0A0 -b _CODE=0x0200 -b _HRAM=0xFF80`.

## Our harness
`python harness/gb.py build <game>` runs, from `games/<game>/`:
`lcc -Wl-m -Wl-j -Wm-yn<TITLE> <game.json lcc_flags...> -o build/<game>.gb src/**/*.c src/**/*.s`
then `romusage build/<game>.map -g`. Everything is rebuilt in one call (no incremental objects).

## Flag reference (useful subset)
| Flag | Effect |
|---|---|
| `-o file.gb` | output ROM (extension picks format) |
| `-c` / `-S` | compile only to .o / to .asm |
| `-v` | print every sub-command (debug the build itself) |
| `-Dname=val`, `-Idir` | preprocessor define / include dir |
| `-debug` | `--debug` for sdcc, `.cdb` (`-Wl-y`), `.noi` (`-Wl-j`), wide map (`-Wl-w`), `-Wa-l`, `-Wl-u` |
| `-Wl-m` | write `.map` (areas, symbols, sizes; romusage input) |
| `-Wl-j` | write `.noi` (`DEF _sym 0xADDR`; our tests read it) |
| `-Wm-yS` | convert `.noi` to `.sym` for BGB/Emulicious (needs `-Wl-j`) |
| `-Wm-yn"TITLE"` | header title, max 15 chars (harness sets it from game.json `title`) |
| `-Wm-yt0xNN`, `-Wm-yoN`/`-Wm-yoA`, `-Wm-yaN` | MBC type, ROM banks, SRAM banks (`banking.md`) |
| `-Wm-yc` / `-Wm-yC` / `-Wm-ys` | CGB compatible / CGB only / SGB: **don't** use for a DMG game |
| `-Wm-yj` | non-Japanese region flag |
| `-autobank` | bankpack assigns `#pragma bank 255` files (needs `-Wm-yt`) |
| `-Wf--max-allocs-per-node50000` | better register allocation: smaller/faster code, slower compile. Recommended by `04_coding_guidelines.md` (GBDK lib itself is built with it) |
| `-Wf--max-allocs-per-node0` | the opposite: easier source-level stepping in a debugger, slower code |
| `-Wf--opt-code-speed` / `-Wf--opt-code-size` | minor effect compared to max-allocs |
| `-Wf--Werror`, `-Wf--disable-warning N` | warnings as errors / silence warning N |
| `-Wf--fverbose-asm`, `-Wf--i-code-in-asm` | annotate generated asm |
| `-Wa-l` | assembler listing `.lst` with cycle counts. `lcc -c -o dir/x.o x.c` already leaves `x.asm` + `x.lst` next to the .o; in one-shot builds they are temp files and get deleted |
| `-Wl-g_sym=0xADDR`, `-Wl-b_AREA=0xADDR` | move a symbol/area, e.g. shadow OAM / `_DATA` (FAQ) |
| `-K` | skip ihxcheck (don't) |

Suggested `game.json` for a plain 32 KB DMG game:
```json
{ "title": "MYGAME", "lcc_flags": ["-Wf--max-allocs-per-node50000"] }
```

## Output files
| File | Made by | Use |
|---|---|---|
| `.gb` | makebin | the ROM |
| `.map` | `-Wl-m` | area sizes/addresses per bank; `romusage x.map` |
| `.noi` | `-Wl-j` | symbol -> address list (globals only; `static` vars/functions are absent). Banked symbols print as `0xBBAAAA` (bank<<16) |
| `.sym` | `-Wm-yS` | BGB/Emulicious symbols |
| `.cdb` | `-debug` / `-Wl-y` | source-level debug info (Emulicious debugger in VS Code) |
| `.asm` | `-S`, or `-c` (kept next to the .o) | generated asm with C lines as comments |
| `.lst` | `-c` (kept next to the .o) | listing with addresses and `[cycles]` |
| `.ihx` | linker | intermediate, deleted by lcc |

## romusage (`tools/gbdk/bin/romusage`)
| Command | Shows |
|---|---|
| `romusage build/g.map -g` | per-bank usage bars (harness default) |
| `romusage build/g.map -a` | areas in each bank (`-aS` sort by size): find what eats bank 0 |
| `romusage build/g.noi -a -e:STACK:DEFF:100 -e:SHADOW_OAM:C000:A0` | add stack/OAM regions to RAM estimate |
| `romusage build/g.map -q -R` | quiet, non-zero exit on overflow (CI) |
| `romusage build/g.map -sRp -g -B` | colored, summarized banks |
Bank overflow symptoms at build: `WARNING: possibly wrote twice at addr 4000`, `Write from one bank
spans into the next`, `error: ROM is too large for number of banks specified` (`08_faq.md`).
ihxcheck can't detect overflow into an *empty* bank: check romusage.

## Emulator debug output (`#include <gbdk/emu_debug.h>`)
Works in Emulicious (and BGB for most); on hardware/PyBoy these are harmless no-op sequences
(`ld d,d` + jump over the text) but they cost bytes/cycles, so wrap them in `#ifdef DEBUG`.
| Macro / function | Effect |
|---|---|
| `EMU_MESSAGE("text %A% %ROMBANK%")` | print text; `%REG%`, `%ROMBANK%`, `%TOTALCLKS%`, `%LASTCLKS%`, `%CLKS2VBLANK%` expand |
| `EMU_printf(const char *fmt, ...)` | printf-like: `%hx %hu %hd` (cast 8-bit args!), `%c` (don't cast), `%u %d %x %s` |
| `EMU_PROFILE_BEGIN("msg")` / `EMU_PROFILE_END("msg")` | elapsed clocks between the two (divide by 2 in normal-speed mode, per header) |
| `EMU_BREAKPOINT` | `ld b,b` source breakpoint |
```c
#include <gb/gb.h>
#include <stdint.h>
#include <gbdk/emu_debug.h>

uint8_t player_x = 10;

void update(void) {
    for (uint8_t i = 0; i < 100; i++) player_x++;
}

void main(void) {
    EMU_printf("x=%hu frame=%u\n", (uint8_t)player_x, (uint16_t)sys_time);
    EMU_PROFILE_BEGIN("update ");
    update();
    EMU_PROFILE_END("update ");
    while (1) vsync();
}
```
Crash screen: `#include <gb/crash_handler.h>` in one file installs an RST 38 handler that dumps
registers to the screen when execution runs into 0xFF bytes (`examples/gb/crash`).

## Common warnings
| Message | Meaning / fix |
|---|---|
| `warning 283: function declarator with no prototype` | write `f(void)`, not `f()` |
| `warning 110: conditional flow changed by optimizer: so said EVELYN...` | dead branch removed; logic bug or a var that needs `volatile` (ISR-shared) |
| `warning 126: unreachable code` | same family |
| `warning 85: unreferenced function argument` | harmless; reference the arg (`a;`) in NAKED asm functions |
| `WARNING: overflow in implicit constant conversion` | sign mismatch of constants; add `u` suffixes (`04_coding_guidelines.md`) |
| `z80instructionSize() failed to parse line node, assuming 999 bytes` | SDCC peephole quirk: ignore |
| `?ASlink-Warning-Undefined Global _foo` | a .c/.s file isn't compiled/linked, or a `static` mismatch |
| `?ASlink-Error-<cannot open> : "...lcc*.lk"` | `-autobank` used without `-Wm-yt` |
| `old "gbz80" SDCC PORT name` | old Makefile: port is `sm83` since 4.1.0 |
| very slow compile | huge non-`const` initialized array, or `#include`d `.c` files (`08_faq.md`) |
