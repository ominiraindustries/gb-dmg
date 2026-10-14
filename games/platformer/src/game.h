// CABALLERITO - shared declarations. Design: design/gdd.md, UI: design/ui.md.
#pragma once
#include <gb/gb.h>
#include <gb/metasprites.h>  // hide_sprites_range
#include <stdint.h>
#include "metatiles.h"
#include "bg.h"
#include "font.h"
#include "ui.h"
#include "spr.h"
#include "bcd.h"

// World coordinates (GDD §2.0): x = u16 px, y = u8 px with Y_BIAS (level row 0 starts at y = 32).
// With the HUD on top and SCY = 0xF0, OAM y == world y and OAM x == x - camera_x + 8.
#define Y_BIAS        32
#define LEVEL_ROWS    8
#define LEVEL_MAX_COLS 255
#define PIT_Y         (Y_BIAS + LEVEL_ROWS * 16)   // top edge below this row = fell in a pit

enum { STATE_TITLE, STATE_INTRO, STATE_PLAY, STATE_PAUSE, STATE_DYING, STATE_GOAL, STATE_CLEAR,
       STATE_GAMEOVER };

// BG tile layout in VRAM: level tileset at 0, shared font after it, HUD icons after the font
#define TILE_FONT     BG_COUNT
#define TILE_UI       (BG_COUNT + FONT_COUNT)

// --- main.c
extern uint8_t state, keys, prev_keys, pressed;
extern uint8_t frame_lines, max_frame_lines, skip_measure, vram_late;
extern uint8_t cheat_flags;                        // written by tests only
#define CHEAT_INVINCIBLE 1
#define CHEAT_NO_TIMER   2

// --- level.c
extern uint8_t level[];
extern uint8_t level_cols;                         // N metatile columns
extern uint16_t camera_x;
extern uint8_t scx_shadow;
extern uint16_t cols_written;                      // next tile column to stream
void level_load(uint16_t cam);                     // LCD must be off; camera starts at cam
void level_update_camera(void);
uint8_t mt_at(uint16_t x, uint8_t y);              // metatile id at a world pixel (pits/walls handled)
uint8_t solid_at(uint16_t x, uint8_t y);
void level_draw_vram(void);
void block_set(uint8_t col, uint8_t row, uint8_t mt);   // change level[] and redraw if on screen

// --- blocks.c
void block_hit(uint8_t col, uint8_t row);          // hit from below by the player
void collect_coins(void);                          // map coins touched by the player

// --- hud.c / score
extern uint8_t score[3], coins, lives, world, stage;
extern uint16_t time_units;
void hud_init(void);                               // LCD off: draws both window rows
void hud_draw_vram(void);
void hud_set_time(uint16_t units);
void hud_set_lives(void);
void add_score(const uint8_t *bcd);                // packed BCD, 3 bytes little-endian
void add_coin(void);
void add_life(void);
extern const uint8_t PTS_50[3], PTS_100[3], PTS_200[3], PTS_400[3], PTS_1000[3];

// --- player.c
enum { FORM_SMALL, FORM_BIG, FORM_SHOT };
extern uint16_t player_x;
extern uint8_t player_y;
extern int16_t player_vx, player_vy;
extern uint8_t player_form, player_on_ground, player_facing, player_freeze, player_inv;
extern uint8_t hb_y, hb_h;
#define HB_X 3
#define HB_W 10
void player_spawn(uint16_t x, uint8_t y);
void player_update(void);
void player_draw(void);
void player_power_up(uint8_t item_type);
void player_hurt(void);
void player_bounce(void);                          // after a stomp
void player_kill(void);                            // time over
extern uint8_t player_dead;                        // 1 = pit, 2 = killed

// --- actors.c  (struct of arrays, fixed slot ranges = fixed OAM ranges, GDD §7.3)
#define A_ENEMY0  0                                // 5 enemies (step 3)
#define A_ITEM    5
#define A_SHOT0   6                                // 2 projectiles
#define A_DEBRIS0 8                                // 4 brick pieces
#define A_COIN0   12                               // 2 coins popping out of blocks
#define ACT_MAX   14
enum { T_NONE, T_WALKER, T_SHELL, T_ITEM_GROW, T_ITEM_SHOT, T_ITEM_1UP, T_SHOT, T_PUF, T_DEBRIS,
       T_COINPOP };
extern uint8_t act_type[], act_y[], act_state[], act_timer[];
extern uint16_t act_x[];
extern int16_t act_vx[], act_vy[];
void actors_clear(void);
void actors_update(void);
void actors_draw(void);
void spawn_item(uint8_t type, uint8_t col, uint8_t row);
void spawn_debris(uint8_t col, uint8_t row);
void spawn_coinpop(uint8_t col, uint8_t row);
uint8_t spawn_shot(uint16_t x, uint8_t y, uint8_t left);
void bump_actors_on_block(uint8_t col, uint8_t row);
void oam16(uint8_t nb, uint8_t ox, uint8_t y, uint8_t tile, uint8_t prop);  // 16x16 = 2 sprites
void act_move(uint8_t i);                          // asm (vram.s): position += velocity, 8.8
// enemies.c
void enemies_reset(uint16_t from_x);               // spawn list restarts at the first object >= x
void enemies_update(void);
void enemies_draw(void);
void bump_enemies_on_block(uint16_t x, uint8_t top);

// --- sound.c
enum { SFX_JUMP_SMALL, SFX_JUMP_BIG, SFX_COIN, SFX_STOMP, SFX_BUMP, SFX_BREAK, SFX_POWER_APPEAR,
       SFX_POWER_GET, SFX_SHOOT, SFX_KICK, SFX_HURT, SFX_ONEUP, SFX_TICK, SFX_PAUSE, SFX_DEATH,
       SFX_HURRY, SFX_COUNT };
void sound_init(void);
void sfx(uint8_t id);
void sound_update(void);

// --- vram.s (call only in VBlank or with the LCD off)
void vram_col16(uint8_t *dst, const uint8_t *src);  // 16 tiles down a BG map column (stride 32)
