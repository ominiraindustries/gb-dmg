---
name: gbdk
description: GBDK-2020 4.5.0 reference for writing or reviewing Game Boy (DMG) C code - gb.h/hardware.h API (sprites, backgrounds, window, metasprites, input, interrupts/ISRs, timing, sound registers), SDCC performance rules, ROM banking/MBC and SRAM saves, png2asset asset conversion, lcc/makebin/romusage flags and emulator debugging. Load it whenever touching games/*/src, game.json lcc_flags, or any GBDK question.
---

# GBDK-2020 for fast, polished DMG games

Verified against `tools/gbdk` 4.5.0 headers, `reference/gbdk-src/docs/pages/*.md` and test builds.
Trust these files over memory: many web tutorials use pre-4.x APIs (`wait_vbl_done`, `gbz80`).

## Golden rules
1. Frame loop = input -> update -> draw to shadow OAM -> `vsync()`. One `joypad()` read per frame.
2. LCD starts **on** with BG and sprites **off**: always `SHOW_BKG` / `SHOW_SPRITES` (`DISPLAY_ON`).
3. Bulk VRAM loads (tiles, full maps) between `DISPLAY_OFF` and `DISPLAY_ON`. Small updates (a few
   tiles of HUD) right after `vsync()` with the GBDK `set_*` functions. Never raw-write VRAM with LCD on.
4. Never read VRAM for game logic; keep maps/collision in WRAM or ROM.
5. Sprites: `move_sprite` etc. write shadow OAM (safe anytime). Coordinates are screen + (8,16).
   Max 40 sprites, 10 per scanline. Hide with `hide_sprite` / `hide_sprites_range` (the latter needs `#include <gb/metasprites.h>`).
6. `uint8_t` by default, unsigned, globals over stack locals, `const` for all tables (ROM).
7. No `*`, `/`, `%` by variables per frame; for `uint8_t` write shifts/masks explicitly
   (`x >> 3`, not `x / 8`: the latter is a 16-bit loop). Constant multiplies are fine.
8. No `printf`/`stdio.h`, `waitpad`, `delay`, `float`, recursion in game code.
9. ISR handlers via `add_VBL/add_LCD` are plain `void f(void)`; install in `CRITICAL {}`, enable
   with `set_interrupts(IE_REG | ...)` outside it. Shared vars `volatile`, multi-byte in `CRITICAL`.
10. Measure (asm listing, `EMU_PROFILE_*`, LY at end of frame) before optimizing or going to asm.
11. MBC games: bank 0 <= 16 KB, `-autobank` needs `-Wm-yt`, SRAM needs `-Wm-ya1`, never
    `SWITCH_ROM` from banked code.
12. png2asset: default is 8x16 sprites; use indexed PNG + `-keep_palette_order` for exact shades.

## Minimal game skeleton (compiles with GBDK 4.5.0)
```c
#include <gb/gb.h>
#include <stdint.h>

const uint8_t tiles[] = {   // tile 0: blank, tile 1: ball (2bpp, 16 bytes each)
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    0x3C,0x3C,0x7E,0x42,0xFF,0x81,0xFF,0x81,0xFF,0x81,0xFF,0x81,0x7E,0x42,0x3C,0x3C,
};

// Non-static globals: readable from tests by name via the .noi file
uint8_t keys, prev_keys, pressed;      // pressed = went down this frame
uint8_t ball_x, ball_y, paused;

void init(void) {
    DISPLAY_OFF;
    BGP_REG = OBP0_REG = DMG_PALETTE(DMG_WHITE, DMG_LITE_GRAY, DMG_DARK_GRAY, DMG_BLACK);
    set_bkg_data(0, 1, tiles);
    init_bkg(0);                         // whole 32x32 BG map = tile 0
    set_sprite_data(0, 2, tiles);
    set_sprite_tile(0, 1);
    ball_x = 76; ball_y = 68;
    SHOW_BKG; SHOW_SPRITES;
    DISPLAY_ON;
}

void update(void) {
    if (pressed & J_START) paused ^= 1;
    if (paused) return;
    if ((keys & J_LEFT)  && ball_x > 0)   ball_x--;
    if ((keys & J_RIGHT) && ball_x < 152) ball_x++;
    if ((keys & J_UP)    && ball_y > 0)   ball_y--;
    if ((keys & J_DOWN)  && ball_y < 136) ball_y++;
}

void draw(void) {
    move_sprite(0, ball_x + 8, ball_y + 16);   // shadow OAM, copied by DMA in VBlank
}

void main(void) {
    init();
    while (1) {
        // Top of loop runs right after VBlank started: do small VRAM writes here
        prev_keys = keys;
        keys = joypad();
        pressed = keys & ~prev_keys;
        update();
        draw();
        vsync();                        // HALT until next VBlank (low power, 59.7 Hz)
    }
}
```

## Most-used API (exact names; full signatures in `api.md`)
- `DISPLAY_ON` / `DISPLAY_OFF`, `SHOW_BKG`, `SHOW_WIN`, `SHOW_SPRITES`, `HIDE_*`, `SPRITES_8x8` / `SPRITES_8x16`
- `BGP_REG`, `OBP0_REG`, `OBP1_REG` = `DMG_PALETTE(c0,c1,c2,c3)` with `DMG_WHITE..DMG_BLACK`
- `set_bkg_data(first, n, data)`, `set_bkg_tiles(x, y, w, h, map)`, `set_bkg_submap(x, y, w, h, map, map_w)`
- `set_bkg_tile_xy(x, y, t)`, `fill_bkg_rect(x, y, w, h, t)`, `init_bkg(t)`, `move_bkg(x, y)`, `scroll_bkg(dx, dy)`
- `set_win_tiles(...)`, `move_win(x + 7, y)`
- `set_sprite_data(first, n, data)`, `set_sprite_tile(nb, t)`, `set_sprite_prop(nb, S_FLIPX|S_FLIPY|S_PRIORITY|S_PALETTE)`
- `move_sprite(nb, x, y)`, `hide_sprite(nb)`, `hide_sprites_range(from, to)` (needs `<gb/metasprites.h>`)
- `move_metasprite_ex(ms, base_tile, base_prop, base_sprite, x, y)` and `_flipx/_flipy/_flipxy` (return #sprites;
  `#include <gb/metasprites.h>`)
- `joypad()` with `J_UP J_DOWN J_LEFT J_RIGHT J_A J_B J_START J_SELECT`
- `vsync()`, `sys_time`, `LY_REG`, `SCX_REG`, `SCY_REG`, `STAT_REG`, `LYC_REG`
- `CRITICAL { add_VBL(f); add_LCD(f); }`, `set_interrupts(IE_REG | LCD_IFLAG)`, `nowait_int_handler`
- `NR10_REG..NR52_REG` + `AUDENV_VOL(x)`, `AUDHIGH_RESTART` etc. for SFX
- `initrand(seed)`, `rand()`, `randw()` (`#include <rand.h>`)
- Banking: `#pragma bank 255`, `BANKREF(x)`, `BANKREF_EXTERN(x)`, `BANK(x)`, `BANKED`, `NONBANKED`,
  `SWITCH_ROM(b)`, `CURRENT_BANK`; SRAM: `ENABLE_RAM`, `SWITCH_RAM(b)`, `DISABLE_RAM`
- Debug: `EMU_printf("%hu", (uint8_t)v)`, `EMU_PROFILE_BEGIN/END` (`#include <gbdk/emu_debug.h>`)

## Topic files (read the one you need)
| Topic | File |
|---|---|
| Full API by area, VRAM safety table, startup register values, ISR examples, sound SFX code | `api.md` |
| SDCC codegen facts (measured), types, loops, structs, calling convention, inline asm, measuring | `performance.md` |
| MBC1/MBC5, `#pragma bank`, autobank, BANKED calls, banked data access, SRAM saves, game.json flags | `banking.md` |
| png2asset flags/output, palette index mapping, metasprite drawing, maps, fonts/text | `assets.md` |
| lcc/makebin/sdcc flags, output files (.map .noi .sym .cdb .lst), romusage, EMU debug, warnings | `toolchain.md` |
| Which official example shows which technique | `examples.md` |
| Silent failures and pitfalls checklist (use when reviewing code) | `gotchas.md` |

## Harness reminders (this repo)
- Build `python harness/gb.py build <game>`; extra flags in `games/<game>/game.json` `"lcc_flags"`.
  The harness already passes `-Wl-m -Wl-j -Wm-yS -Wf--max-allocs-per-node50000 -Wm-yn<title>`
  and `-I build/gen -I src` (generated files can include game headers).
- The build **fails on purpose** on `warning 112` (implicit declaration: names the missing header,
  e.g. `gb/metasprites.h`, `string.h`, `rand.h`) and `warning 84` (prototype inside a block).
  Fix the include/prototype; do not work around the check (`harness/gb.py check_warnings`).
- Art: `games/<game>/res/*.tiles` (ASCII 8x8 tiles, see `harness/asciitiles.py`) become
  `build/gen/<stem>.c/.h` with `<stem>_tiles[]`, `<STEM>_COUNT` and `<STEM>_<LABEL>` defines.
- Tests read non-`static` globals by name from the `.noi`. Put a `frame_lines`/`max_frame_lines`
  global (LY after the frame's work, see games/breakout) to test the frame budget.
