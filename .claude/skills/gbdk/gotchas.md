# GBDK / SDCC pitfalls that break things silently

Sources: `docs/pages/08_faq.md`, `09_migrating_new_versions.md`, `03_using_gbdk.md` (known
issues), `04_coding_guidelines.md`, header notes in `gb/gb.h`, `gb/isr.h`, `gb/metasprites.h`,
and tests run with GBDK 4.5.0 (marked *tested*).

## Startup and frame loop
- **LCD is already on and BG/sprites are off** at `main()` (LCDC=0xC0) *tested*. Forgetting
  `SHOW_BKG`/`SHOW_SPRITES` gives a blank screen with no error.
- Default `OBP1_REG = 0x1B` (inverted shades) *tested*: sprites with `S_PALETTE` look wrong until you set it.
- `vsync()` **returns immediately when the LCD is off**: a frame-counting loop with the display off
  runs at full CPU speed (timers/animations go 100x faster). It **never returns if the VBL
  interrupt is disabled** (e.g. `set_interrupts(LCD_IFLAG)` dropped `VBL_IFLAG`): use
  `set_interrupts(IE_REG | LCD_IFLAG)` or include `VBL_IFLAG`.
- Turn the LCD off only with `DISPLAY_OFF`/`display_off()` (waits for VBlank). Writing LCDC bit 7
  directly outside VBlank is forbidden on real DMG hardware.
- `waitpad()`/`waitpadup()` spin without HALT; `delay()` blocks everything. Use counters + `vsync()`.
- `sys_time` is 16-bit and wraps every ~18 min; fine for `sys_time & 7` style animation timing.
- Logic longer than one frame silently halves the frame rate (next `vsync()` waits a whole frame).

## Memory and variables
- Globals/statics are zeroed at boot (since 4.0.5); **locals and the rest of WRAM are garbage**.
- Non-`const` initialized arrays live in RAM, cost ROM for the initializer and boot copy time, and
  make compiles slow. Every table must be `const`.
- `const uint8_t *p` = pointer to const data (normal for ROM tables); `uint8_t * const p` = constant pointer.
- `uint8_t a[8] = {5};` sets only `a[0]` = 5 (rest 0): standard C, docs list it as a known surprise.
- `static` globals/functions don't appear in the `.noi`: our tests can't read them *tested*.
- Variables in an SRAM data segment (`#pragma dataseg DATA_N` / `-Wf-ba`) **with an initializer
  silently move to WRAM**. Initialize SRAM at runtime.
- `char` is **signed** (lcc passes `--fsigned-char`); `int` is 16-bit; there is no `float`.
- Integer promotion: 8-bit operands become `int` in expressions. `uint8_t / 8` compiles to a 16-bit
  shift loop *tested* (write `>> 3`); `if (a + b > 255)` is evaluated in 16 bits (works, but costs);
  wraparound only happens when stored back into a `uint8_t` (cast: `(uint8_t)(x - y)`).
- Constants mixed with unsigned types: add `u` (`127u`) or get "overflow in implicit constant conversion".
  This also hits header macros: `NR12_REG = AUDENV_VOL(15) | ...` warns (15<<4 is a signed int);
  write `AUDENV_VOL(15u)` *tested*.
- `f()` declares "any arguments": always write `f(void)` (warning 283).
- Variables written in an ISR and polled in main code need `volatile` (otherwise the loop can be
  optimized away, "warning 110 ... EVELYN the modified DOG"). Multi-byte ones: access in `CRITICAL {}`.
- Varargs (`printf`, `sprintf`, `EMU_printf`): cast 8-bit args explicitly (`(uint8_t)x` for `%hu`/`%hx`),
  otherwise output is wrong. `EMU_printf` `%c` must *not* be cast.

- **Frame timers in `uint8_t` wrap at 256 frames (4.3 s)**: any screen or phase longer than that
  (a 10 s countdown, a 300 f results screen) needs `uint16_t` (games/shmup CONTINUAR: digits lasted
  136 f after the wrap and Start was ignored 46 f of every 256). `t % 60` blink phases on a wrapping
  u8 also drift (46/30 instead of 30/30).
- **One shot per frame for spawns that cost**: several emitters firing in the same frame (fans,
  turrets) stack into a peak; a per-frame token (`fire_busy`) with "retry next frame" is invisible.

## Graphics
- **With gbe_video, SCX/SCY/BGP/OBP0/OBP1 are written from shadows every VBlank**: a direct
  `SCY_REG = x` lasts one frame. The build stops on it (`gb.py check_sources`); set the shadow.
- Never read VRAM for game state (`get_bkg_tile_xy`, `get_vram_byte`): it stalls until VRAM is
  accessible. Keep maps in WRAM.
- Raw pointer writes to VRAM with the LCD on corrupt randomly; GBDK `set_*` functions are safe
  but slow, so bulk loads go inside `DISPLAY_OFF ... DISPLAY_ON` or are spread across frames.
- BG tiles 128-255 **are** sprite tiles 128-255 (0x8800-0x8FFF): loading sprites at 128+ overwrites
  BG tiles and vice versa.
- Map coordinates wrap at 32: `set_bkg_tiles` with x+w > 32 wraps to the left edge. Use
  `set_bkg_submap` for source maps wider than 32 tiles.
- `#include <stdio.h>` (printf) loads a font over many BG tiles; `ISR_VECTOR(VECTOR_STAT, ...)`
  can't coexist with stdio.
- Sprite coordinates are offset: `move_sprite(n, screen_x + 8, screen_y + 16)`. Hide with y=0;
  x=0 hides but still counts toward the 10-sprites-per-line limit.
- 8x16 sprite mode ignores bit 0 of the tile index.
- Window: x position is `WX - 7`, it covers everything to the right and below, has no transparency,
  and only shows if BG is on too (`SHOW_BKG` + `SHOW_WIN`).
- LYC interrupt on line 0 is unreliable; do top-of-frame work in a VBL handler.
- `gb/gb.h` does **not** include `gb/metasprites.h`: `metasprite_t`, `move_metasprite_*` and
  `hide_sprites_range` need `#include <gb/metasprites.h>` *tested*.
- `move_metasprite_*` overwrites the prop byte of every sprite it uses (pass flags via `base_prop`)
  and returns the count used: hide leftover sprites from bigger frames (`hide_sprites_range`).
- Renamed flip functions are counter-intuitive: old `move_metasprite_hflip` == new `move_metasprite_flipy`,
  old `vflip` == new `flipx`. Use the new `flipx/flipy/flipxy` names only.

## png2asset
- Default sprite size is **8x16** (`-spr8x16`): pass `-spr8x8` or call `SPRITES_8x16`.
- Colors are re-indexed light->dark from the colors actually used: a white+black image makes black
  index 1 (light gray on screen); a sprite PNG without alpha loses its lightest color to transparency
  *tested*. Use indexed PNGs + `-keep_palette_order` (`assets.md`).
- Dedup + flip matching is on by default: use `-noflip` for DMG maps, `-keep_duplicate_tiles` when
  tile index must equal glyph position (fonts).
- `*_WIDTH`/`*_HEIGHT` in generated headers are pixels, not tiles.

## Interrupts
- Handlers for `add_VBL/add_LCD/add_TIM/...` are plain functions: **no** `CRITICAL`/`INTERRUPT`
  attributes. Those are only for `ISR_VECTOR` raw handlers (which must not be mixed with `add_*` for
  the same interrupt; no raw VBlank vector).
- Install handlers inside `CRITICAL { }` but call `set_interrupts()` **outside** it (it re-enables
  interrupts itself).
- Chain limits: VBL 4 (3 if you use `remove_VBL`), LCD 3, TIM/SIO/JOY 4.
- Handlers run in bank 0 (`int_handler` is `NONBANKED`); far pointer macros (`FAR_CALL`) must not be
  used in ISRs; restore `CURRENT_BANK` if an ISR switches banks.
- Per-scanline LCD handlers must finish within one line; add `nowait_int_handler` last so the chain
  doesn't wait for mode 0/1 before returning.

## Banking / cartridge
- Bank 0 must stay <= 16 KB once you use an MBC; overflow corrupts bank 1 (ihxcheck warns
  "possibly wrote twice at addr 4000", but cannot detect overflow into an empty bank: run romusage).
- `-autobank` without `-Wm-yt...` fails with an unreadable linker error *tested*.
- No `-Wm-ya<N>` -> header says "no RAM" -> SRAM isn't mapped in emulators *tested*.
- Never `SWITCH_ROM` inside a `BANKED` function or any code not in bank 0.
- `static BANKED` functions break autobank fixups.
- Pointers are bank-unaware; data in 0x4000-0x7FFF is only valid while its bank is mapped.
- MBC1: banked calls/`SWITCH_ROM` only up to bank 31; banks 0x20/0x40/0x60 unusable. Prefer MBC5.
- Always `DISABLE_RAM` after SRAM writes; validate saves with a magic/checksum.

## Toolchain / environment
- Old APIs still compile but are obsolete: `wait_vbl_done` (use `vsync`), `move_metasprite`,
  `cgb_compatibility`, `bgb_emu.h` (use `gbdk/emu_debug.h`). Online tutorials often use pre-4.x
  names (`gbz80` port, `-Wl-yp` header pokes, `set_bkg_1bit_data`): translate them.
- Windows: SDCC can fail when run from folders with spaces on non-C drives (`08_faq.md`).
- Slow compile = big non-const array or `#include "x.c"`; never include .c files.
- Functions written in asm before GBDK 4.1 assume the old calling convention: declare them `OLDCALL`.
- `warning 158: overflow in implicit constant conversion` on an inline call such as
  `move_sprite(0, x, PADDLE_Y + 16)` with a constant > 127 is spurious (SDCC inlining); silence it
  with an explicit cast `(uint8_t)(PADDLE_Y + 16)`.
- `warning 84: 'auto' variable 'f' may be used before initialization` after declaring a function
  prototype inside a block (`case X: { void f(void); f(); }`): SDCC treats it as a variable. Put
  prototypes at file scope.
- `set_bkg_tiles` / `set_bkg_tile_xy` cost ~130 M-cycles per tile and wait for STAT mode outside
  VBlank: fine for a few tiles, ruinous for whole rows every frame (games/tetris measured 4 rows +
  HUD going to 120 scanlines). In VBlank write the map directly (`0x9800 + y*32 + x`).
- **SDCC 4.5.1 codegen bug (seen in harness/common/src/gbe_map.c map_load):**
  `level_px_w = (uint16_t)cols << 4;` computed the value in HL but stored `0` as the high byte
  (`xor a` / `ld (_level_px_w + 1), a`), with or without `--max-allocs-per-node`. Not reproducible
  in small files: it depends on the surrounding function. `(uint16_t)cols * 16` compiled correctly.
  Lesson: a test must read every important 16-bit value back (here the whole map read as solid);
  when a value is "half right", read the asm (`lcc -S`) before suspecting the logic.

