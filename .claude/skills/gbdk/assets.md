# Assets: png2asset, tiles, maps, metasprites, palettes, text

Sources: `docs/pages/06_toolchain.md` (png2asset section), `20_toolchain_settings.md`
(png2asset settings), `gb/metasprites.h`, examples `cross-platform/metasprites`, `large_map`,
`text_basic`, `gb/sgb_border/Readme.md`. Behaviour marked *(tested)* was checked by running
`tools/gbdk/bin/png2asset.exe` 4.5.0 on test PNGs.

## Tile format refresher
8x8 px, 2 bits/pixel, 16 bytes per tile: for each row, byte 0 = low bit plane, byte 1 = high bit
plane, bit 7 = leftmost pixel. Color index = (high << 1) | low. On screen the index goes through
`BGP_REG` (BG/window) or `OBP0_REG`/`OBP1_REG` (sprites; index 0 transparent).
Example row `0x3C,0x7E` -> pixels `0 2 3 3 3 3 2 0`.

## png2asset key flags
| Flag | Use |
|---|---|
| `-o file.c` | output (also writes `file.h`); `-c` is the deprecated alias |
| *(default)* | metasprite mode: tiles + `metasprite_t` frames |
| `-map` | background/window mode: tileset + tile map |
| `-spr8x8` / `-spr8x16` | hardware sprite size. **Default is 8x16** -> pass `-spr8x8` if you use `SPRITES_8x8` |
| `-sw W -sh H` | frame size: the PNG is cut into frames of WxH (sprite sheet), default = whole PNG |
| `-px X -py Y` | pivot inside the frame (default: center); x/y given to `move_metasprite_*` is the pivot |
| `-pw W -ph H` | collision box written to the header (`*_PIVOT_W/H`) |
| `-noflip` | don't dedup tiles by mirroring. **Use for DMG maps** (DMG BG tiles can't be flipped) |
| `-keep_palette_order` | use the indexed PNG's palette order as color indices (see palettes below) |
| `-keep_duplicate_tiles` | no dedup (needed when tile index must equal position, e.g. fonts) |
| `-tiles_only` / `-maps_only` / `-metasprites_only` | export only that part |
| `-tile_origin N` | map entries start at tile N (tiles will be loaded at N) |
| `-source_tileset file.png` | reuse a shared tileset (common tiles) |
| `-b N` | emit `#pragma bank N`; `-b 255` = autobank |
| `-sp 0xNN` | default OAM prop byte for all sprites |
| `-bpp 1` / `-pack_mode 1bpp` | 1bpp tiles (load with `set_*_1bpp_data`) |
| `-use_metafile` | also read args from `<inputfile>.meta`, e.g. `player.png.meta` |
| `-use_map_attributes` | CGB attributes: **not** for DMG |

Typical commands (run from the game dir; output into `src/` so the harness compiles it):
```
tools/gbdk/bin/png2asset res/player.png -spr8x8 -sw 16 -sh 16 -o src/gen/player.c
tools/gbdk/bin/png2asset res/level1.png -map -noflip -keep_palette_order -o src/gen/level1.c
tools/gbdk/bin/png2asset res/font.png -map -noflip -keep_duplicate_tiles -keep_palette_order -tiles_only -o src/gen/font.c
```
Then `#include "gen/player.h"`. Our harness has no png2asset step: generated `.c/.h` must live
under `src/` (commit them, regenerate when the PNG changes).

## Output format *(tested)*
Metasprite mode, `player.png` -> `player.h`:
```
#define player_TILE_W 8          // hw sprite width/height
#define player_TILE_H 8
#define player_WIDTH 16          // frame size (px)
#define player_HEIGHT 16
#define player_TILE_COUNT 4
#define player_PIVOT_X 8 ...     // pivot and collision box
extern const metasprite_t* const player_metasprites[N];   // one entry per frame
BANKREF_EXTERN(player)
extern const palette_color_t player_palettes[4];          // CGB colors: ignore on DMG
extern const uint8_t player_tiles[64];                     // 16 bytes per tile
```
Map mode adds `extern const unsigned char level1_map[W*H];`, `#define level1_WIDTH/HEIGHT` (in
**pixels**: divide by 8 for tiles), `level1_TILE_COUNT`, `level1_tiles[]`, and
`#define level1_map_attributes level1_map` when no attributes. `BANKREF(name)` is always emitted
(harmless in bank 0). Duplicate tiles are removed (also flipped matches unless `-noflip`).

## DMG palettes and color index mapping (important) *(tested)*
png2asset does **not** map RGB grays to fixed DMG shades. Without `-keep_palette_order` it sorts
the colors **actually present** from lightest to darkest and numbers them from 0 (the docs text
says "darkest to lightest" but real output, and the sgb_border readme, are lightest first):
- 4 grays used -> white 0, light 1, dark 2, black 3: matches default `BGP_REG = 0xE4`.
- Only white+black used (typical font) -> black becomes **index 1** -> shows as *light gray*.
- Sprite PNG with alpha -> index 0 = transparent, remaining colors light->dark from 1.
  A sprite with white/gray/black gets 1/2/3 -> white shows as light gray under `OBP0 = 0xE4`.
- Sprite PNG **without** alpha -> its lightest color becomes index 0 = transparent.
Reliable recipe: draw with an **indexed PNG** whose palette is `[white, light gray, dark gray, black]`
(for sprites: `[transparent/magenta, ...3 shades]`) and pass `-keep_palette_order`; indices are then
exactly the palette slots. Then choose shades with registers, e.g. sprites using full range
`OBP0_REG = DMG_PALETTE(DMG_WHITE, DMG_WHITE, DMG_DARK_GRAY, DMG_BLACK);` (slot 0 is transparent).
Use `OBP1_REG` + `S_PALETTE` prop for a second sprite palette (flash on hit: swap palette bit).

## Loading and drawing
```c
#include <gb/gb.h>
#include <gb/metasprites.h>     // metasprite_t, move_metasprite_*, hide_sprites_range
#include <stdint.h>

// Stand-in for png2asset output (gen/hero.h): 2 tiles, 2 frames of 8x16 made of 8x8 sprites
const uint8_t hero_tiles[32] = {
    0x3C,0x3C,0x42,0x7E,0x81,0xFF,0x81,0xFF,0x81,0xFF,0x81,0xFF,0x42,0x7E,0x3C,0x3C,
    0x18,0x18,0x24,0x3C,0x42,0x7E,0x81,0xFF,0x81,0xFF,0x42,0x7E,0x24,0x3C,0x18,0x18,
};
const metasprite_t hero_frame0[] = {
    METASPR_ITEM(-8, -4, 0, 0),   // first item: offset from pivot
    METASPR_ITEM( 8,  0, 1, 0),   // next items: offset from previous item
    METASPR_TERM
};
const metasprite_t hero_frame1[] = {
    METASPR_ITEM(-8, -4, 1, 0),
    METASPR_ITEM( 8,  0, 0, 0),
    METASPR_TERM
};
const metasprite_t * const hero_metasprites[2] = { hero_frame0, hero_frame1 };

#define HERO_TILE_BASE 0     // where hero tiles live in sprite VRAM
#define HERO_SPR_BASE  0     // first hardware sprite used

uint8_t hero_x = 80, hero_y = 72;   // screen coords of the pivot
uint8_t hero_frame, hero_facing_left;

void draw_hero(void) {
    uint8_t used;
    const metasprite_t *ms = hero_metasprites[hero_frame];
    if (hero_facing_left)
        used = move_metasprite_flipx(ms, HERO_TILE_BASE, 0, HERO_SPR_BASE, hero_x + 8, hero_y + 16);
    else
        used = move_metasprite_ex(ms, HERO_TILE_BASE, 0, HERO_SPR_BASE, hero_x + 8, hero_y + 16);
    hide_sprites_range(HERO_SPR_BASE + used, MAX_HARDWARE_SPRITES);  // frames differ in size
}

void main(void) {
    DISPLAY_OFF;
    set_sprite_data(HERO_TILE_BASE, 2, hero_tiles);
    SPRITES_8x8;                       // must match png2asset -spr8x8 / -spr8x16
    SHOW_SPRITES;
    DISPLAY_ON;
    while (1) {
        uint8_t keys = joypad();
        if (keys & J_LEFT)  { hero_x--; hero_facing_left = 1; }
        if (keys & J_RIGHT) { hero_x++; hero_facing_left = 0; }
        if ((sys_time & 7) == 0) hero_frame ^= 1;   // animate every 8 frames
        draw_hero();
        vsync();
    }
}
```
- With several actors, give each a range of hardware sprites (or allocate sequentially each frame
  and hide the rest once at the end). Only call `move_metasprite_*` when something changed.
- 10 sprites per scanline max: a 16 px wide metasprite = 2 per line, so 5 side-by-side actors fill a
  line. For many objects, rotate the OAM start index every frame (flicker instead of vanishing).

## Background maps
```c
#include <gb/gb.h>
#include <stdint.h>

// Stand-in for png2asset -map output
const uint8_t bg_tiles[32] = {
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00, // blank
    0xFF,0xFF,0x81,0xFF,0x81,0xFF,0x81,0xFF,0x81,0xFF,0x81,0xFF,0x81,0xFF,0xFF,0xFF, // block
};
#define BG_W 20
#define BG_H 18
uint8_t bg_map[BG_W * BG_H];     // in WRAM so collision can read it (never read VRAM)

void main(void) {
    for (uint16_t i = 0; i < BG_W * BG_H; i++) bg_map[i] = (i < BG_W || i >= BG_W * (BG_H - 1)) ? 1 : 0;
    DISPLAY_OFF;                                   // bulk VRAM writes at full speed
    set_bkg_data(0, 2, bg_tiles);
    set_bkg_tiles(0, 0, BG_W, BG_H, bg_map);
    SHOW_BKG;
    DISPLAY_ON;
    while (1) vsync();
}
```
- Map from png2asset: `set_bkg_data(0, level1_TILE_COUNT, level1_tiles);`
  `set_bkg_tiles(0, 0, level1_WIDTH / 8, level1_HEIGHT / 8, level1_map);` (only if width <= 32 tiles).
- Wider/taller than 32 tiles: `set_bkg_submap(x, y, w, h, map, map_w)` to stream one column/row per
  8 px of scroll at the screen edge (`examples/cross-platform/large_map`).
- Tiles not starting at 0: `set_bkg_based_tiles(..., base)` or convert with `-tile_origin`.
- Tileset + many levels (`cross-platform/platformer_template` Readme): convert the tileset once
  with `-map -noflip -keep_duplicate_tiles -tiles_only`, draw levels in Tiled/LDtk, export each level
  as PNG and convert with `-map -noflip -maps_only -source_tileset res/tileset.png`. Keeping solid
  tiles in one contiguous index range makes collision a single compare on the WRAM/ROM map.
- Tile budget: 256 BG/window tiles, 256 sprite tiles, 128 of them shared (0x8800-0x8FFF = BG tiles
  128-255 = sprite tiles 128-255). Plan VRAM: e.g. sprites 0-127, BG 0-127, shared/font 128-255.

## Text and fonts
- Avoid `stdio.h`/`printf` (font eats BG tiles, slow). Instead load your own font tiles and map
  characters to tile indices:
```c
#include <gb/gb.h>
#include <stdint.h>

// Font tiles laid out in ASCII order starting at ' ' (0x20), loaded at FONT_BASE.
// Convert with: -map -noflip -keep_duplicate_tiles -keep_palette_order -tiles_only
#define FONT_BASE 128u

// Draw a zero-terminated string on the BG map at tile coords (x, y)
void draw_text(uint8_t x, uint8_t y, const char *s) {
    uint8_t *addr = get_bkg_xy_addr(x, y);
    while (*s) {
        set_vram_byte(addr++, (uint8_t)(*s++ - ' ') + FONT_BASE);  // no row wrap handling
    }
}

// 0-255 as 3 digits using subtraction loops instead of / and %
void draw_u8(uint8_t x, uint8_t y, uint8_t v) {
    uint8_t buf[3];
    uint8_t d = 0;
    while (v >= 100u) { v -= 100u; d++; }
    buf[0] = d + ('0' - ' ') + FONT_BASE;
    d = 0;
    while (v >= 10u) { v -= 10u; d++; }
    buf[1] = d + ('0' - ' ') + FONT_BASE;
    buf[2] = v + ('0' - ' ') + FONT_BASE;
    set_bkg_tiles(x, y, 3, 1, buf);
}

void main(void) {
    SHOW_BKG;
    draw_text(1, 1, "HELLO");
    draw_u8(1, 2, 255);
    while (1) vsync();
}
```
  (`get_win_xy_addr` for the window.) Duplicate glyphs (several blank tiles) would be removed by
  default dedup and break the ASCII mapping: hence `-keep_duplicate_tiles`.
- 2-color fonts can be stored as 1bpp (`-bpp 1`, 8 bytes/tile) and loaded with
  `set_1bpp_colors(DMG_BLACK, DMG_WHITE); set_bkg_1bpp_data(FONT_BASE, n, font_tiles);`.
- Scores: `gb/bcd.h` `bcd2text(&score, FONT_BASE + ('0' - ' '), buf)` gives 8 tile indices directly.
- Built-in fonts (`gbdk/font.h`: `font_init(); font_set(font_load(font_min));`) exist but are
  meant for stdio-style text.

## Other asset routes
- `INCBIN(var, "res/file.bin")` + `INCBIN_EXTERN(var)` (`gbdk/incbin.h`): raw binary; path is relative
  to the lcc working directory (in our harness: `games/<game>/`).
- Compression: `gbcompress` tool (`--alg=gb|rle|zx0`, `--cout`) + `gb_decompress_bkg_data`,
  `rle_decompress`, `zx0_decompress` (see `api.md`). Examples: `cross-platform/gbdecompress`, `rle_map`.
- 1bpp packing halves ROM for 2-color graphics.
