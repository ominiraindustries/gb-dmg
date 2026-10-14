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
// SCX/SCY, palettes (fades) and, with the HUD cut on, the window/sprites split at line cut_line.
// shake_x/y are added to the scroll shadows; bgp_below (when bgp_below_on) is the BG palette
// below the cut line (flash the playfield, not the HUD). SCY_REG is written every VBlank.
extern uint8_t scx_shadow, scy_shadow, bgp_shadow, obp0_shadow, obp1_shadow;
extern int8_t shake_x, shake_y;
extern uint8_t bgp_below, bgp_below_on;
extern uint8_t hud_cut;       // 1: window visible above cut_line, sprites only below it
void video_init(uint8_t cut_line, uint8_t bgp, uint8_t obp0, uint8_t obp1);   // installs ISRs
void set_fade(uint8_t k);     // 0 = normal palettes .. 3 = white (ui.md 1.2 formula)
void set_fade_dark(uint8_t k);  // 0 = normal .. 3 = black

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

// ---------------------------------------------------------------- gbe_vmap.c / .s
// Vertical metatile map (shmups): GBE_VMAP_W (10) metatiles per row = the screen width, row 0 =
// bottom, world y grows up, scroll_y = world px at the bottom screen line (SCY = 112 - scroll_y).
// WRAM ring of 16 metatile rows, BG ring of 32 tile rows streamed 1 per frame (speed <= 8 px/f).
// Same game tables as gbe_map: mt_tiles[][4]. Map rows past the end read as metatile 0.
#ifndef GBE_VMAP_W
#define GBE_VMAP_W 10
#endif
// OAM Y (8-bit) of the top edge of metatile row r: valid while the row is near the screen
#define VMAP_ROW_Y(r) ((uint8_t)((uint8_t)scroll_y + 144 - ((uint8_t)(r) << 4)))
extern uint8_t vmap_ring[], row_buf[], row_pending, scroll_sub;
extern uint16_t vmap_rows, vmap_mrows, vmap_stop, rows_written, scroll_y;
void vmap_load(const uint8_t *src, uint16_t rows, uint16_t scroll, uint16_t stop);   // LCD off
void vmap_scroll(uint16_t speed);       // per frame: scroll + SCY shadow + <= 1 tile row prepared
uint8_t vmap_get(uint8_t col, uint16_t row);           // ring cell (0 if not in the ring)
void vmap_set(uint8_t col, uint16_t row, uint8_t mt);  // ring cell + queued redraw if drawn
void vmap_draw_vram(void);              // VBlank: row + up to 8 queued metatiles
void gbe_vrow_tiles(const uint8_t *m, uint8_t top);    // asm: row_buf = one half of a metatile row
void gbe_vrow_tiles_c(const uint8_t *m, uint8_t top);  // C reference

// ---------------------------------------------------------------- gbe_aim.c
// Directions: 32 (11.25 deg), dir 0 = down, clockwise on screen: 8 = left, 16 = up, 24 = right.
// aim_vx/aim_vy[spd * 32 + dir]: 8.8 velocity. Speeds: 0 = 1.0, 1 = 1.25, 2 = 1.5, 3 = 2.0 px/f.
extern const int16_t aim_vx[128], aim_vy[128];
#define dir_vx aim_vx                   // speed 0 = the first 32 entries
#define dir_vy aim_vy
uint8_t aim_dir(int8_t dx, int8_t dy);  // direction of (dx, dy) (target - origin); error <= 1
// Bullets go to the pool range fire_first..+fire_n with type fire_t, tile fire_tile, prop fire_prop.
// x, y = OAM position of the new bullet. Return the slot (0xFF if the range is full).
extern uint8_t fire_first, fire_n, fire_t, fire_tile, fire_prop;
uint8_t fire(uint8_t x, uint8_t y, uint8_t dir, uint8_t spd);     // asm (gbe_aim.s)
uint8_t fire_c(uint8_t x, uint8_t y, uint8_t dir, uint8_t spd);   // C reference
// n bullets at dir + step * (k - (n - 1) / 2), k = 0..n-1; returns how many went out
uint8_t fire_fan(uint8_t x, uint8_t y, uint8_t dir, uint8_t n, uint8_t step, uint8_t spd);

// ---------------------------------------------------------------- gbe_pool.c / .s
// Object pools in 8-bit OAM space (X = screen x + 8, Y = screen y + 16). GBE_POOL_MAX records of
// 16 bytes (the asm walks records with ld a,(hl+); field offsets are fixed, see gbe_pool.s).
// Moving frees objects that leave the screen (X >= 168 or Y >= 176, any side).
typedef struct {
    uint8_t t;              // +0  type, 0 = free
    uint8_t x, xs;          // +1  OAM x, sub-pixel
    uint8_t y, ys;          // +3  OAM y, sub-pixel
    int16_t vx, vy;         // +5  8.8 px/frame
    uint8_t s, tm, aux;     // +9  game use (state, timer, anything)
    uint8_t tile, prop;     // +12 what gbe_spr draws
    uint8_t aux2, pad;      // +14
} pool_obj_t;
extern pool_obj_t pool[];
uint8_t pool_alloc(uint8_t first, uint8_t n);      // first free slot of the range, 0xFF if full
void pool_clear(uint8_t first, uint8_t n);
void pool_move(uint8_t first, uint8_t n);          // asm (gbe_pool.s), n >= 1
void pool_move_c(uint8_t first, uint8_t n);
// Collisions: set the query box and the pool object box, then hit_first(first, n) returns the
// first live object of the range that overlaps, or 0xFF. 8-bit circular overlap (one compare per
// axis): fine for OAM coordinates; qw + ow and qh + oh must be <= 256.
extern uint8_t hit_qx, hit_qy, hit_qw, hit_qh, hit_ox, hit_oy, hit_ow, hit_oh;
uint8_t hit_first(uint8_t first, uint8_t n);       // asm, n >= 1
uint8_t hit_first_c(uint8_t first, uint8_t n);

// ---------------------------------------------------------------- gbe_spr.c
// OAM manager: one call per priority group (lower OAM slots = higher priority on the DMG).
// spr_rot: advance once per frame, cycling through 2 x a common multiple of the groups' slot
// counts (< 64; e.g. 48 for groups of 12, 6, 8, 2 slots): consecutive frames start each group
// half a group apart, so a sprite dropped on a crowded line is drawn the next frame.
extern uint8_t spr_rot;
// size 1: one sprite per object; size 2: 16x16 (tile, tile + 2). pool_n >= 1.
void spr_group(uint8_t oam_first, uint8_t oam_n, uint8_t pool_first, uint8_t pool_n, uint8_t size);
void spr_group_c(uint8_t oam_first, uint8_t oam_n, uint8_t pool_first, uint8_t pool_n, uint8_t size);

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
void vram_mt4_list(uint8_t **dst, const uint8_t *tiles, uint8_t n);   // n metatiles (n >= 1)
void vram_row20(uint8_t *dst, const uint8_t *src);  // 20 consecutive BG map bytes, 24 T/tile

// ---------------------------------------------------------------- gbe_view.c / .s
// First-person grid view (crawlers): pieces from res/view.pcs (harness/fpview.py) composed far to
// near into view_buf (20x12 tile indices). The game defines view_cell() and links view.c.
#define VIEW_W 20
#define VIEW_H 12
enum { VIEW_FREE, VIEW_WALL, VIEW_DOOR, VIEW_LOCKED, VIEW_DOWN, VIEW_UP };
extern uint8_t view_buf[], view_bank;           // view_bank = BANK(view) if banked, else 0
extern const uint8_t *view_map, *view_class;    // 16x16 cell types + type -> VIEW_* (asm reads them)
extern const int8_t view_dx[4], view_dy[4];     // facing 0 N, 1 E, 2 S, 3 W
uint8_t view_cell(uint8_t x, uint8_t y);        // provided by the game (off the map = VIEW_WALL)
void view_compose(uint8_t x, uint8_t y, uint8_t f);      // asm core (gbe_view.s)
void view_compose_c(uint8_t x, uint8_t y, uint8_t f);    // C reference
void view_compose_bg(void);                     // background piece only (map margins)
void view_mark_seen(uint8_t *seen);             // after view_compose: 16x16 bit map of seen cells
void view_blit(const uint8_t *piece);           // asm
void view_blit_c(const uint8_t *piece);         // C reference

// ---------------------------------------------------------------- gbe_bgbuf.c
// Double buffer on the two BG maps (LCDC bit 3): copy a 20-wide WRAM canvas into the hidden map
// bgbuf_rows_per rows per VBlank, then flip. bg_front = visible map (0 $9800, 1 $9C00).
extern uint8_t bg_front, bgbuf_rows_left, bgbuf_rows_per, view_flips, bgbuf_flip_xor;
void bgbuf_start(const uint8_t *src, uint8_t rows, uint8_t dst_row);
void bgbuf_draw_vram(void);                     // VBlank
void bgbuf_fill_both(const uint8_t *src, uint8_t rows, uint8_t dst_row);   // LCD off

// ---------------------------------------------------------------- gbe_vq.c
// VRAM write queue with a tile budget per VBlank (bytes are copied in: callers may reuse buffers)
extern uint8_t vq_budget, vq_lost;
uint8_t vq_push(uint8_t *dst, const uint8_t *src, uint8_t len);   // 0 = no room (vq_lost++)
uint8_t vq_push_fill(uint8_t *dst, uint8_t tile, uint8_t len);
uint8_t vq_pending(void);
void vq_draw_vram(void);                        // VBlank (asm, ~20 T per tile)

// ---------------------------------------------------------------- gbe_text.c
// Shared font text (0-9 A-Z - ! . : ? /) + a 4-line message log typed through gbe_vq.
// The game sets txt_font = VRAM_FONT, txt_blank = its blank tile; needs "font" in common_res.
extern uint8_t txt_font, txt_blank;
uint8_t txt_char(char c);
uint8_t txt_tiles(uint8_t *dst, const char *s, uint8_t n);       // pads with blanks
void txt_u16(uint8_t *dst, uint16_t v, uint8_t width, uint8_t zero_pad);
extern uint8_t log_lines[4][20], log_pending, log_typing, log_speed, log_w;
void log_init(uint8_t *dst, uint8_t width);     // 4 lines of width (<= 20) at dst (rows 32 apart)
void log_push(const char *s);                   // <= 20 chars, up to 4 waiting
void log_update(void);                          // per frame (outside VBlank)

// ---------------------------------------------------------------- gbe_menu.c
// Vertical menu: cursor tile through gbe_vq, repeat 16/6 f, wrap, disabled options skipped.
#define MENU_NONE 0xFF
#define MENU_BACK 0xFE
extern uint8_t menu_n, menu_sel, menu_disabled;
void menu_open(uint8_t n, uint8_t sel, uint8_t disabled, uint8_t *cursor0, uint8_t stride,
               uint8_t cursor_tile, uint8_t blank_tile);
uint8_t menu_update(void);                      // MENU_NONE / index chosen with A / MENU_BACK (B)

// ---------------------------------------------------------------- gbe_rng.c
// 16-bit xorshift; tests predict it (gbtest.rng_next). Seed rng_state from DIV + frames on a key press.
extern uint16_t rng_state;
uint8_t rng_next(void);
uint8_t rng_range(uint8_t n);          // 0 .. n-1

// ---------------------------------------------------------------- gbe_bank.c
// Banked assets: game.json "banked_res": ["walls", "level1"] puts the generated files in switchable
// banks (BANKREF(<stem>)); load them with BANK(<stem>) from any code:
//   bank_set_bkg_data(BANK(walls), first, WALLS_COUNT, walls_tiles);
void bank_set_bkg_data(uint8_t bank, uint8_t first, uint8_t n, const uint8_t *data) NONBANKED;
void bank_set_sprite_data(uint8_t bank, uint8_t first, uint8_t n, const uint8_t *data) NONBANKED;
void bank_memcpy(uint8_t bank, void *dst, const void *src, uint16_t n) NONBANKED;
uint8_t bank_read8(uint8_t bank, const uint8_t *p) NONBANKED;

// ---------------------------------------------------------------- gbe_save.c
// Save in cartridge SRAM (needs an MBC with RAM + battery: -Wm-yt0x1B -Wm-ya1): two alternating
// slots with signature, version, sequence, length and checksum; a torn write keeps the previous
// save. len <= 4000.
extern uint8_t save_slot, save_seq;
uint8_t save_load(void *dst, uint16_t len, uint8_t version);   // 1 = newest valid save copied
void save_store(const void *src, uint16_t len, uint8_t version);
void save_erase(void);

// ---------------------------------------------------------------- gbe_selftest.c
// Equivalence of every asm routine with its C reference (gb-asm procedure). Tests call
// gb.selftest() (sets gbe_eq_request; the game calls gbe_selftest()). Which modules are checked
// comes from gbe_config.h: GBE_SELFTEST_MAP (needs a loaded map), GBE_SELFTEST_ACTORS,
// GBE_SELFTEST_POOL (uses the last 8 pool slots as scratch and the last 10 OAM entries),
// GBE_SELFTEST_VMAP <metatile count of mt_tiles>, GBE_SELFTEST_AIM (needs _POOL's scratch),
// GBE_SELFTEST_VIEW (every piece of the game's view.pcs).
extern uint8_t gbe_eq_request, gbe_eq_done;
extern uint16_t gbe_eq_mismatch, gbe_eq_count;
void gbe_selftest(void);
