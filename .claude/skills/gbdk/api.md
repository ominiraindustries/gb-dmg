# GBDK-2020 4.5.0 API cheatsheet (Game Boy DMG)

Signatures copied from `tools/gbdk/include/gb/gb.h`, `gb/hardware.h`, `gb/metasprites.h`,
`gb/isr.h`, `rand.h`, `gbdk/*.h`. `OLDCALL` / `PRESERVES_REGS(...)` are omitted unless
relevant (they only matter if you call these from asm). `#include <gb/gb.h>` pulls in
`gb/hardware.h`, `types.h`, `stdint.h`. `#include <gbdk/platform.h>` = gb.h + cgb.h + sgb.h.

## Startup state (measured in 4.5.0, crt0 defaults)
| Item | Value at `main()` |
|---|---|
| LCDC | `0xC0`: LCD **on**, BG **off**, sprites **off**, window off, win map 0x9C00, BG map 0x9800, BG tiles 0x8800 mode, 8x8 sprites |
| BGP / OBP0 / OBP1 | `0xE4` / `0xE4` / `0x1B` (OBP1 is inverted!) |
| IE | `VBL_IFLAG` only; default VBL ISR does OAM DMA + `sys_time++` |
| RAM | statics zeroed per C standard (4.0.5+); other WRAM not cleared |
| Shadow OAM | `shadow_OAM` at 0xC000 (0xA0 bytes), `_DATA` starts 0xC0A0, stack top 0xE000 |
So you must `SHOW_BKG` / `SHOW_SPRITES` yourself. Source: measured with PyBoy;
`docs/pages/03_using_gbdk.md` "Graphics Tile Maps and Data on Startup", `06_toolchain.md`.

## VRAM access safety (read this first)
Source: `03_using_gbdk.md` "Ensuring Safe Access to Graphics Memory", gb.h notes.
| Operation | Display ON | Notes |
|---|---|---|
| `move_sprite`, `set_sprite_tile/prop`, `hide_sprite`, `move_metasprite_*` | safe anytime | write shadow OAM in WRAM; DMA'd in next VBlank |
| `set_bkg_data`, `set_bkg_tiles`, `set_bkg_submap`, `fill_bkg_rect`, `set_bkg_tile_xy`, `set_vram_byte`, win/sprite equivalents | safe (GBDK waits for mode 0/1) | slow for bulk; do big loads with `DISPLAY_OFF` or spread over frames |
| `init_bkg`, `init_win`, `vmemset` | safe | "avoids writes during modes 2 & 3" |
| `get_bkg_tiles`, `get_bkg_tile_xy`, `get_vram_byte`, `get_*_data` | works but stalls | **avoid**: keep a copy of the map in WRAM instead |
| raw pointer write to 0x8000-0x9FFF | **unsafe** unless in VBlank or LCD off | use `set_vram_byte` |
| `SCX_REG`, `SCY_REG`, `WX_REG`, `WY_REG`, `BGP_REG`, `OBPx_REG` | anytime | change applies from the current scanline; write right after `vsync()` to avoid tearing |
| LCD off (`LCDC` bit 7) | only in VBlank | always use `DISPLAY_OFF` / `display_off()` (waits for VBL) |

## Display / LCD control (macros on `LCDC_REG`)
| Macro / function | Effect |
|---|---|
| `DISPLAY_ON` | `LCDC_REG \|= LCDCF_ON` |
| `DISPLAY_OFF` | calls `display_off()`: waits for VBlank, then turns LCD off |
| `SHOW_BKG` / `HIDE_BKG` | BG layer (bit 0). Window needs BG on too |
| `SHOW_WIN` / `HIDE_WIN` | window layer (bit 5) |
| `SHOW_SPRITES` / `HIDE_SPRITES` | sprite layer (bit 1) |
| `SPRITES_8x8` / `SPRITES_8x16` | sprite size (bit 2) |
| `LCDCF_*`, `LCDCF_B_*` | raw bits: `LCDCF_BG8000`, `LCDCF_BG9C00`, `LCDCF_WIN9C00`, `LCDCF_OBJ16`, ... |
| `STAT_REG`, `STATF_LYC`, `STATF_MODE00/01/10`, `STATF_LYCF`, `STATF_BUSY` | STAT bits |
| `LY_REG`, `LYC_REG` | current scanline / compare |
| `BGP_REG`, `OBP0_REG`, `OBP1_REG` | DMG palettes |
| `DMG_PALETTE(C0,C1,C2,C3)` | build palette byte; colors `DMG_WHITE 0`, `DMG_LITE_GRAY 1`, `DMG_DARK_GRAY 2`, `DMG_BLACK 3` |
| `SCREENWIDTH` 160, `SCREENHEIGHT` 144 | also `DEVICE_SCREEN_WIDTH` 20, `DEVICE_SCREEN_HEIGHT` 18 (tiles) |
Fade: step `BGP_REG`/`OBP0_REG` through palettes once every N frames (e.g. `0xE4 -> 0x90 -> 0x40 -> 0x00`).

## Background
```
void set_bkg_data(uint8_t first_tile, uint8_t nb_tiles, const uint8_t *data);   // 16 bytes/tile, 2bpp
void set_bkg_1bpp_data(uint8_t first_tile, uint8_t nb_tiles, const uint8_t *data); // 8 bytes/tile
void set_1bpp_colors(uint8_t fgcolor, uint8_t bgcolor);                          // for *_1bpp_data
void set_bkg_tiles(uint8_t x, uint8_t y, uint8_t w, uint8_t h, const uint8_t *tiles); // x,y 0-31, wraps
void set_bkg_based_tiles(uint8_t x, uint8_t y, uint8_t w, uint8_t h, const uint8_t *tiles, uint8_t base_tile);
void set_bkg_submap(uint8_t x, uint8_t y, uint8_t w, uint8_t h, const uint8_t *map, uint8_t map_w); // maps > 32 wide
void set_bkg_based_submap(uint8_t x, uint8_t y, uint8_t w, uint8_t h, const uint8_t *map, uint8_t map_w, uint8_t base_tile);
uint8_t *set_bkg_tile_xy(uint8_t x, uint8_t y, uint8_t t);  // returns VRAM address
void fill_bkg_rect(uint8_t x, uint8_t y, uint8_t w, uint8_t h, uint8_t tile);
void init_bkg(uint8_t c);                                   // whole 32x32 map = c
uint8_t *get_bkg_xy_addr(uint8_t x, uint8_t y);             // address for set_vram_byte
void set_vram_byte(uint8_t *addr, uint8_t v);
inline void move_bkg(uint8_t x, uint8_t y);                 // SCX=x, SCY=y
inline void scroll_bkg(int8_t x, int8_t y);                 // SCX+=x, SCY+=y
```
- `set_bkg_submap`: x/y are *source-map* coords; hardware position is `x & 31, y & 31`, so source
  and hardware coordinates stay aligned -> ideal for streaming columns/rows when scrolling.
  See `examples/cross-platform/large_map`.
- BG tiles 128-255 are the same VRAM as sprite tiles 128-255 (0x8800-0x8FFF).
- Aliases: `set_tile_map` = `set_bkg_tiles`, `set_tile_xy` = `set_bkg_tile_xy`, `fill_rect` = `fill_bkg_rect`.

## Window
Same shape as BG: `set_win_data`, `set_win_1bpp_data`, `set_win_tiles`, `set_win_based_tiles`,
`set_win_submap`, `set_win_based_submap`, `set_win_tile_xy`, `fill_win_rect`, `init_win`, `get_win_xy_addr`.
```
inline void move_win(uint8_t x, uint8_t y);   // WX=x, WY=y. Screen-left edge is x=7 (MINWNDPOSX)
inline void scroll_win(int8_t x, int8_t y);
```
Window shares BG tile data, uses its own map (0x9C00 by default), always draws over BG, cannot be
transparent, and extends to the bottom-right corner. HUD at bottom: `move_win(7, 144 - 16)`.

## Sprites (shadow OAM)
```
void set_sprite_data(uint8_t first_tile, uint8_t nb_tiles, const uint8_t *data); // 0x8000 table
void set_sprite_1bpp_data(uint8_t first_tile, uint8_t nb_tiles, const uint8_t *data);
inline void set_sprite_tile(uint8_t nb, uint8_t tile);      // nb 0-39
inline uint8_t get_sprite_tile(uint8_t nb);
inline void set_sprite_prop(uint8_t nb, uint8_t prop);      // S_FLIPX, S_FLIPY, S_PRIORITY, S_PALETTE
inline uint8_t get_sprite_prop(uint8_t nb);
inline void move_sprite(uint8_t nb, uint8_t x, uint8_t y);  // hardware coords: screen x+8, y+16
inline void scroll_sprite(uint8_t nb, int8_t x, int8_t y);
inline void hide_sprite(uint8_t nb);                         // sets y = 0
void hide_sprites_range(uint8_t from, uint8_t to);           // from <= n < to (to <= 40); needs <gb/metasprites.h>
extern volatile struct OAM_item_t shadow_OAM[];              // {y, x, tile, prop}; direct access OK
```
- Prop flags (gb.h): `S_PRIORITY 0x80` (behind BG colors 1-3), `S_FLIPY 0x40`, `S_FLIPX 0x20`,
  `S_PALETTE 0x10` (use OBP1). Equivalent hardware.h names: `OAMF_PRI`, `OAMF_YFLIP`, `OAMF_XFLIP`, `OAMF_PAL1`.
- Hide with y=0 (or y >= 160). x=0 hides too but the sprite still counts toward the 10/line limit.
- 8x16 mode: tile index LSB ignored (top = tile & 0xFE, bottom = tile | 1).
- `MAX_HARDWARE_SPRITES` = 40, `DEVICE_SPRITE_PX_OFFSET_X` = 8, `DEVICE_SPRITE_PX_OFFSET_Y` = 16.
- `DISABLE_OAM_DMA` / `ENABLE_OAM_DMA`: stop/resume the VBlank OAM copy (e.g. while rebuilding
  OAM over several frames). `SET_SHADOW_OAM_ADDRESS(void *)` (256-byte aligned buffer) for double buffering.

## Metasprites (`#include <gb/metasprites.h>` - NOT pulled in by gb.h)
```
typedef struct metasprite_t { int8_t dy, dx; uint8_t dtile; uint8_t props; } metasprite_t;
#define METASPR_ITEM(dy,dx,dt,a) {(dy),(dx),(dt),(a)}   // dy/dx relative to PREVIOUS item
#define METASPR_TERM {metasprite_end}                  // metasprite_end = -128
uint8_t move_metasprite_ex(const metasprite_t *metasprite, uint8_t base_tile, uint8_t base_prop,
                           uint8_t base_sprite, uint8_t x, uint8_t y);  // returns #hw sprites used
uint8_t move_metasprite_flipx (same params);   // mirrored horizontally
uint8_t move_metasprite_flipy (same params);
uint8_t move_metasprite_flipxy(same params);
void hide_metasprite(const metasprite_t *metasprite, uint8_t base_sprite);
```
- x/y are hardware coords of the pivot (add 8/16 to screen coords).
- They overwrite the prop byte of every sprite used; pass palette/priority via `base_prop`.
- Obsolete (still compile): `move_metasprite` (no base_prop), `move_metasprite_vflip/hflip/hvflip`.
- Frames use different sprite counts: track a "hiwater" and `hide_sprites_range(hiwater, 40)`.
Full pattern in `assets.md`.

## Tile data, misc VRAM helpers
```
void set_data(uint8_t *vram_addr, const uint8_t *data, uint16_t len);   // raw copy to VRAM
void set_tile_data(uint8_t first_tile, uint8_t nb_tiles, const uint8_t *data, uint8_t base); // base 0x80/0x90
void set_tiles(uint8_t x, uint8_t y, uint8_t w, uint8_t h, uint8_t *vram_addr, const uint8_t *tiles);
void vmemcpy(uint8_t *dest, uint8_t *sour, uint16_t len);
void vmemset(void *s, uint8_t c, size_t n);
void set_native_tile_data(uint16_t first_tile, uint8_t nb_tiles, const uint8_t *data); // >=256 -> sprite table
```
Compression (decompress into VRAM): `gb_decompress(const uint8_t *sour, uint8_t *dest)`,
`gb_decompress_bkg_data(uint8_t first_tile, const uint8_t *sour)`, `gb_decompress_sprite_data(...)`
(`gb/gbdecompress.h`); `rle_init(void *data)` + `rle_decompress(void *dest, uint8_t len)`
(`gbdk/rledecompress.h`); `zx0_decompress(void *sour, void *dest)` (`gbdk/zx0decompress.h`).

## Input
```
uint8_t joypad(void);          // OR of J_RIGHT 0x01, J_LEFT 0x02, J_UP 0x04, J_DOWN 0x08,
                               //       J_A 0x10, J_B 0x20, J_SELECT 0x40, J_START 0x80
uint8_t waitpad(uint8_t mask); // busy loop, no HALT: avoid in game code
void waitpadup(void);          // busy loop
uint8_t joypad_init(uint8_t npads, joypads_t *joypads); void joypad_ex(joypads_t *joypads); // SGB multitap
```
Read once per frame; derive edges yourself (see SKILL.md skeleton: `pressed = keys & ~prev`).

## Interrupts
```
typedef void (*int_handler)(void) NONBANKED;
void add_VBL(int_handler h); void remove_VBL(int_handler h);   // up to 4 handlers (3 if remove_VBL used)
void add_LCD(int_handler h); void remove_LCD(int_handler h);   // up to 3
void add_TIM(int_handler h); void remove_TIM(int_handler h);   // up to 4; or add_low_priority_TIM
void add_SIO(int_handler h); void add_JOY(int_handler h);      // + remove_*
void set_interrupts(uint8_t flags);   // VBL_IFLAG|LCD_IFLAG|TIM_IFLAG|SIO_IFLAG|JOY_IFLAG; call OUTSIDE critical
inline void enable_interrupts(void); inline void disable_interrupts(void);
void nowait_int_handler(void);        // add LAST in a chain to skip the "return in mode 0/1" wait
inline uint8_t cancel_pending_interrupts(void);
#define CRITICAL __critical            // CRITICAL { ... } = di ... restore
```
- Handlers added with `add_*` are plain `void f(void)` functions: **no** `CRITICAL`/`INTERRUPT`.
- Install inside `CRITICAL { add_LCD(f); }`, then `set_interrupts(IE_REG | LCD_IFLAG)`.
- Default chain end waits until STAT mode 0/1 before `reti` (avoids VRAM glitches); for per-scanline
  effects add `nowait_int_handler` last (see `examples/gb/lcd_isr_wobble`).
- LYC=0 is unreliable; do start-of-frame work in a VBL handler.
- Raw vectors without the dispatcher (`gb/isr.h`, not for VBlank):
  `ISR_VECTOR(VECTOR_STAT|VECTOR_TIMER|VECTOR_SERIAL|VECTOR_JOYPAD, func)` with
  `void func(void) CRITICAL INTERRUPT { ... }`; don't mix with `add_*` for the same interrupt;
  `VECTOR_STAT` cannot be used together with `stdio.h`. `ISR_NESTED_VECTOR` enables nesting.
- Shared multi-byte variables: read/write them from main code inside `CRITICAL { }`; mark them
  `volatile` if main code polls them.

Example: LYC split so the bottom rows (a status bar) don't scroll:
```c
#include <gb/gb.h>
#include <stdint.h>

uint8_t scroll_x;

void lcd_isr(void) {          // runs at LY == LYC
    SCX_REG = 0;              // rows below line 128 don't scroll
}
void vbl_isr(void) {          // start of frame
    SCX_REG = scroll_x;
}

void main(void) {
    CRITICAL {
        STAT_REG = STATF_LYC;
        LYC_REG = 128;
        add_LCD(lcd_isr);
        add_VBL(vbl_isr);
    }
    set_interrupts(IE_REG | LCD_IFLAG);
    SHOW_BKG;
    while (1) {
        scroll_x++;
        vsync();
    }
}
```

## Timing
```
void vsync(void);              // HALT until VBlank ISRs done. Returns IMMEDIATELY if LCD is off.
                               // Never returns if VBL interrupt disabled. Replaces wait_vbl_done().
extern volatile uint16_t sys_time;   // +1 per frame (wraps ~18 min)
void delay(uint16_t d);        // busy-wait d ms, works with interrupts off
#define VBL_DONE _vbl_done     // flag set by VBL ISR
```
Timer: `TIMA_REG`, `TMA_REG`, `TAC_REG` with `TACF_START | TACF_4KHZ/16KHZ/65KHZ/262KHZ`; `DIV_REG`.

## Sound registers (`gb/hardware.h`)
Regs `NR10_REG`..`NR52_REG` (aliases `rAUD1SWEEP`, `rAUD1LEN`, `rAUD1ENV`, `rAUD1LOW`, `rAUD1HIGH`,
... `rAUDVOL`=NR50, `rAUDTERM`=NR51, `rAUDENA`=NR52), wave RAM `AUD3WAVE[16]`.
Helper macros: `AUDENA_ON/OFF`, `AUDVOL_VOL_LEFT(x)`, `AUDVOL_VOL_RIGHT(x)` (0-7),
`AUDTERM_{1..4}_{LEFT,RIGHT}`, `AUDLEN_DUTY_12_5/25/50/75`, `AUDLEN_LENGTH(x)`, `AUDENV_VOL(x)`
(0-15), `AUDENV_UP/DOWN`, `AUDENV_LENGTH(x)` (0-7), `AUDHIGH_RESTART`, `AUDHIGH_LENGTH_ON/OFF`,
`AUD1SWEEP_UP/DOWN`, `AUD1SWEEP_TIME(x)`, `AUD1SWEEP_LENGTH(x)`, `AUD4POLY_WIDTH_15BIT/7BIT`.
Period for a tone of f Hz on ch1/ch2: `p = 2048 - 131072 / f` (11 bits: low 8 to NRx3, high 3 in NRx4).
```c
#include <gb/gb.h>
#include <stdint.h>

void sound_init(void) {
    NR52_REG = AUDENA_ON;                                    // must be first
    NR50_REG = AUDVOL_VOL_LEFT(7) | AUDVOL_VOL_RIGHT(7);
    NR51_REG = 0xFF;                                         // all channels both sides
}

// Short blip on channel 1 with downward pitch sweep. period: 0..2047
void sfx_blip(uint16_t period) {
    NR10_REG = AUD1SWEEP_TIME(2) | AUD1SWEEP_DOWN | AUD1SWEEP_LENGTH(3);
    NR11_REG = AUDLEN_DUTY_50 | AUDLEN_LENGTH(0);
    NR12_REG = AUDENV_VOL(15u) | AUDENV_DOWN | AUDENV_LENGTH(2);  // 15u: avoids warning 158
    NR13_REG = (uint8_t)period;
    NR14_REG = AUDHIGH_RESTART | (uint8_t)(period >> 8);
}

// Noise burst (explosion/hit) on channel 4
void sfx_noise(void) {
    NR41_REG = 0;
    NR42_REG = AUDENV_VOL(12u) | AUDENV_DOWN | AUDENV_LENGTH(3);
    NR43_REG = 0x55 | AUD4POLY_WIDTH_15BIT;
    NR44_REG = AUDHIGH_RESTART;
}

void main(void) {
    sound_init();
    sfx_blip(1750);
    sfx_noise();
    while (1) vsync();
}
```
Music: use hUGEDriver (tracker) or similar; see `02_links_and_tools.md` "Music And Sound Effects".
`examples/gb/sound` is an interactive register playground for finding SFX values.

## Banking / SRAM macros (details in `banking.md`)
`SWITCH_ROM(b)`, `CURRENT_BANK`, `BANK(name)`, `BANKREF(name)`, `BANKREF_EXTERN(name)`,
`BANKED`, `NONBANKED`, `ENABLE_RAM`, `DISABLE_RAM`, `SWITCH_RAM(b)`, `SWITCH_ROM_MBC5(b)`.

## Memory / misc
| API | Notes |
|---|---|
| `SFR name;` | 8-bit unsigned volatile var in HRAM (0xFF80-0xFFFE), `ldh` access (`06_toolchain.md`) |
| `AT(addr)` | `__at`, place a variable at a fixed address |
| `void hiramcpy(uint8_t dst, const void *src, uint8_t n)` | copy to 0xFF00+dst |
| `void reset(void)` | soft reset (jumps to crt0 init) |
| `_cpu` (`DMG_TYPE 0x01`, `MGB_TYPE 0xFF`, `CGB_TYPE 0x11`), `_is_GBA` | hardware detection |
| `memcpy`, `memset`, `memcmp`, `strlen`... (`string.h`) | `memcpy`/`memset` are WRAM-only (not VRAM-safe with LCD on) |
| `abs`, `itoa(int, char*, radix)`, `uitoa` (`stdlib.h`) | radix arg required |
| `fixed` (`types.h`) | union `{.l,.h}` / `.w`: 8.8 fixed point; `.h` = integer pixel |
| `BCD`, `MAKE_BCD(v)`, `uint2bcd`, `bcd_add`, `bcd_sub`, `bcd2text(const BCD*, uint8_t tile_offset, uint8_t *buf)` | `gb/bcd.h`: scores without division |
| `INCBIN(var, "path")`, `INCBIN_EXTERN(var)`, `INCBIN_SIZE(var)` | `gbdk/incbin.h`, path relative to lcc working dir (game dir in our harness) |

## Random (`rand.h`)
```
void initrand(uint16_t seed);   // seed from DIV_REG sampled at a human-timed moment (title screen press)
uint8_t rand(void);             // LCG, RAND_MAX 255
uint16_t randw(void);
void initarand(uint16_t seed); uint8_t arand(void);   // lagged additive variant
extern uint16_t __rand_seed;    // save/restore for replays
```
Range 0..n-1 without division (from `examples/gb/rand/src/rand.c`):
`#define RAND_RANGE_8BIT(randval, range) (uint8_t)(((randval & 0xFFu) * range) >> 8)`.
Powers of two: just mask (`rand() & 15`).

## Text / console (avoid in games)
`#include <stdio.h>` + `printf` loads a font into many BG tiles and is slow (`04_coding_guidelines.md`).
`gbdk/console.h`: `gotoxy`, `posx`, `posy`, `setchar`, `cls`; `gbdk/font.h`: `font_init`, `font_load(font_ibm|font_min|font_spect|font_italic)`, `font_set`.
Use your own font tiles + `set_bkg_tiles` (see `assets.md`). For debug text use `EMU_printf` (`toolchain.md`).

## Obsolete names -> current (`09_migrating_new_versions.md`)
`wait_vbl_done` -> `vsync`; `move_metasprite` -> `move_metasprite_ex`; `move_metasprite_hflip` -> `move_metasprite_flipy` (!);
`move_metasprite_vflip` -> `move_metasprite_flipx` (!); `cgb_compatibility` -> `set_default_palette`;
`_current_bank` -> `CURRENT_BANK`; `__banked` -> `BANKED`; `bgb_emu.h`/`BGB_*` -> `gbdk/emu_debug.h`/`EMU_*`;
`set_bkg_1bit_data` -> `set_bkg_1bpp_data`; `gb/font.h` etc. -> `gbdk/font.h`.
