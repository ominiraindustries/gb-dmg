// gbe - Game Boy engine: reusable pieces measured and tested in games/tetris and games/platformer.
// Use from a game with  "common_src": ["gbe_frame.c", ...]  in game.json (see harness/common/README.md)
// and a games/<game>/src/gbe_config.h with the sizes below.
//
// Rules the library is built on (CLAUDE.md "Rendimiento y VRAM"):
//  - Loop: vsync() -> frame_begin() -> VRAM work (copies only) -> frame_vram_check() -> logic ->
//    sprites -> frame_end(). Tiles are prepared outside VBlank; VBlank only copies.
//  - vram_late must stay 0 in tests; max_frame_lines < 120 of 154.
#pragma once
#include <gb/gb.h>
#include <gb/metasprites.h>
#include <stdint.h>
#include "gbe_config.h"   // game-provided: GBE_ACT_MAX, GBE_MAP_MAX_COLS, ...

// |d| < n for an 8-bit difference d = a - b (n <= 128). The obvious "(d + n) < 2n" is
// asymmetric (d = -n counts as near, +n does not): this bug hit games/platformer enemies.
#define GBE_WITHIN(d, n) ((uint8_t)((uint8_t)(d) + (n) - 1) < (uint8_t)(2 * (n) - 1))

// ---------------------------------------------------------------- gbe_frame.c
extern uint8_t keys, prev_keys, pressed;                  // joypad: held, previous, new this frame
extern uint8_t frame_lines, max_frame_lines, skip_measure, vram_late;
void frame_begin(void);       // right after vsync(): input + frame start time
void frame_vram_check(void);  // right after the VBlank copies: counts writes that ran past VBlank
void frame_end(void);         // last thing in the loop: scanlines used (255 = missed a frame)

// ---------------------------------------------------------------- gbe_oam.c
// Direct shadow OAM writes (~3x cheaper than set_sprite_tile/prop + move_sprite).
// 16x16 objects in 8x16 sprite mode = 2 sprites: tiles (t, t+2); S_FLIPX swaps the halves.
void oam16(uint8_t nb, uint8_t ox, uint8_t y, uint8_t tile, uint8_t prop);
void oam8(uint8_t nb, uint8_t ox, uint8_t y, uint8_t tile, uint8_t prop);

// ---------------------------------------------------------------- gbe_video.c
// Register shadows written by the library's VBlank handler (same moment as GBDK's OAM DMA):
// SCX, palettes (fades) and, with the HUD cut on, the window/sprites split at line cut_line.
extern uint8_t scx_shadow, bgp_shadow, obp0_shadow, obp1_shadow;
extern uint8_t hud_cut;       // 1: window visible above cut_line, sprites only below it
void video_init(uint8_t cut_line, uint8_t bgp, uint8_t obp0, uint8_t obp1);   // installs ISRs
void set_fade(uint8_t k);     // 0 = normal palettes .. 3 = white (ui.md 1.2 formula)

// ---------------------------------------------------------------- gbe_screen.c
// Transitions: fade out 16 f -> screen_build(next) with the LCD off -> fade in 16 f.
// The game defines:  void screen_build(uint8_t which);
// A build that runs its own fade-in sets trans_own_fadein = 1.
extern uint8_t trans_own_fadein;
void transition(uint8_t next);
void show_screen_now(uint8_t which);   // boot: build + fade in
uint8_t transition_update(void);       // 1 while a transition owns the frame (freeze logic)
void screen_build(uint8_t which);      // provided by the game
void lcd_off_redraw_begin(void);       // DISPLAY_OFF, white, window/sprites off, skip_measure

// ---------------------------------------------------------------- gbe_actors.c / .s
// Struct of arrays; slot ranges are the game's business. Positions 8.8 fixed point:
// x = act_x (u16 px) : act_xs (sub), y = act_y (u8 px) : act_ys (sub).
extern uint8_t act_type[], act_xs[], act_y[], act_ys[], act_state[], act_timer[], act_flip[];
extern uint16_t act_x[];
extern int16_t act_vx[], act_vy[];
void act_spawn(uint8_t i, uint8_t type, uint16_t x, uint8_t y);   // zeroes the rest
void act_move(uint8_t i);      // asm: position += velocity (~240 T; C reference act_move_c)
void act_move_c(uint8_t i);

// ---------------------------------------------------------------- gbe_map.c / .s
// Side-scrolling metatile map: GBE_MAP_ROWS (8) rows of 16x16 metatiles, column-major in WRAM,
// world y with Y_BIAS 32 (map row 0 at y 32), BG ring of 32 tile columns streamed 1 per frame.
// The game defines:  const uint8_t mt_tiles[][4] (TL TR BL BR)  and  const uint8_t mt_attr[]
// (bit 7 = solid). Metatile 0 must be empty.
#define GBE_Y_BIAS   32
#define GBE_MAP_ROWS 8
#ifndef ATTR_SOLID
#define ATTR_SOLID   0x80
#endif
extern const uint8_t mt_tiles[][4];
extern const uint8_t mt_attr[];
extern uint8_t level[], level_cols, map_wall_mt, col_buf[], col_pending;
extern uint16_t level_px_w, camera_x, camera_max, cols_written;
void map_load(const uint8_t *src, uint8_t cols, uint16_t cam, uint8_t wall_mt);   // LCD off
void map_follow(uint16_t target_x, uint8_t lead);   // camera never goes back; streams <= 1 column
void map_set(uint8_t col, uint8_t row, uint8_t mt); // change a cell (+ queued redraw if on screen)
void map_draw_vram(void);                           // VBlank: column + up to 8 queued metatiles
uint8_t mt_at(uint16_t x, uint8_t y);    // asm: metatile at a world pixel (0 above/below, wall past end)
uint8_t solid_at(uint16_t x, uint8_t y); // asm: mt_attr[mt_at()] & ATTR_SOLID
uint8_t mt_at_c(uint16_t x, uint8_t y);  // C references for the equivalence test
uint8_t solid_at_c(uint16_t x, uint8_t y);
void map_column(uint16_t tc);            // fill col_buf with tile column tc (asm inside)
void map_column_c(uint16_t tc);

// ---------------------------------------------------------------- gbe_sfx.c
// Sound effects by registers with per-channel priority. The game defines the table:
//   const sfx_t sfx_table[] = { [SFX_JUMP] = { 1, 1, 12, { NR10, NR11, NR12, NR13, NR14 } }, ... };
typedef struct {
    uint8_t ch;         // 1, 2 or 4
    uint8_t prio;       // higher or equal replaces the playing effect on that channel
    uint8_t frames;     // how long the channel stays reserved
    uint8_t r[5];       // NR10-NR14 for ch1; NRx1-NRx4 in r[1..4] for ch2 / ch4
} sfx_t;
extern const sfx_t sfx_table[];
void sound_init(void);
void sfx(uint8_t id);
void sound_update(void);      // once per frame

// ---------------------------------------------------------------- gbe_vram.s
void vram_col16(uint8_t *dst, const uint8_t *src);  // 16 tiles down a BG map column (stride 32)

// ---------------------------------------------------------------- gbe_selftest.c
// Equivalence of every asm routine with its C reference (gb-asm procedure). Tests set
// gbe_eq_request = 1 and read gbe_eq_done / gbe_eq_mismatch. Needs a loaded map.
extern uint8_t gbe_eq_request, gbe_eq_done;
extern uint16_t gbe_eq_mismatch, gbe_eq_count;
void gbe_selftest(void);
