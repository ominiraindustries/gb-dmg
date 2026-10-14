// CABALLERITO - shared declarations. Design: design/gdd.md, UI: design/ui.md.
// Engine pieces (frame loop, OAM, fades/transitions, HUD cut, actors, scrolling map, SFX) come
// from the shared library harness/common/src/gbe*.c/.s (see gbe.h).
#pragma once
#include "gbe.h"
#include "metatiles.h"
#include "bg.h"
#include "font.h"
#include "ui.h"
#include "spr.h"
#include "bcd.h"

// World coordinates (GDD §2.0): x = u16 px, y = u8 px with Y_BIAS (level row 0 starts at y = 32).
// With the HUD on top and SCY = 0xF0, OAM y == world y and OAM x == x - camera_x + 8.
#define Y_BIAS        GBE_Y_BIAS
#define LEVEL_ROWS    GBE_MAP_ROWS
#define PIT_Y         (Y_BIAS + LEVEL_ROWS * 16)   // top edge below this row = fell in a pit

enum { STATE_TITLE, STATE_INTRO, STATE_PLAY, STATE_PAUSE, STATE_DYING, STATE_GOAL, STATE_CLEAR,
       STATE_GAMEOVER };

// BG tile layout in VRAM: level tileset at 0, shared font after it, HUD icons after the font
#define TILE_FONT     BG_COUNT
#define TILE_UI       (BG_COUNT + FONT_COUNT)

// --- main.c
extern uint8_t state;
extern uint8_t cheat_flags;                        // written by tests only
#define CHEAT_INVINCIBLE 1
#define CHEAT_NO_TIMER   2
void new_game(void);
void load_level(void);                             // LCD off: level, enemies, Teo, HUD

// --- flow.c (screens, goal); transitions come from gbe_screen
enum { SCR_TITLE, SCR_INTRO, SCR_CLEAR, SCR_GAMEOVER };
void update_screens(void);
void ui_draw_vram(void);
void goal_reset(void);
uint8_t goal_check(void);
void update_goal(void);
void draw_banner(void);
extern uint8_t record[3];

// --- level.c (game layer over gbe_map)
#define CAMERA_LEAD   64                           // Teo stays <= 64 px from the left edge (GDD §2.5)
void level_load(uint16_t cam);                     // LCD off: map, coin columns, HUD-behind rows
#define level_update_camera() map_follow(player_x, CAMERA_LEAD)
#define level_draw_vram()     map_draw_vram()
#define block_set(c, r, m)    map_set(c, r, m)

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
void hud_pause(uint8_t mode);
void hud_time_icon(uint8_t on);
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
void player_animate(void);
extern uint8_t player_dead;                        // 1 = pit, 2 = killed

// --- actors.c  (slot ranges = fixed OAM ranges, GDD §7.3; arrays live in gbe_actors)
#define A_ENEMY0  0                                // 5 enemies
#define A_ITEM    5
#define A_SHOT0   6                                // 2 projectiles
#define A_DEBRIS0 8                                // 4 brick pieces
#define A_COIN0   12                               // 2 coins popping out of blocks
#define ACT_MAX   GBE_ACT_MAX
enum { T_NONE, T_WALKER, T_SHELL, T_ITEM_GROW, T_ITEM_SHOT, T_ITEM_1UP, T_SHOT, T_PUF, T_DEBRIS,
       T_COINPOP };
void actors_clear(void);
void actors_update(void);
void actors_draw(void);
void spawn_item(uint8_t type, uint8_t col, uint8_t row);
void spawn_debris(uint8_t col, uint8_t row);
void spawn_coinpop(uint8_t col, uint8_t row);
uint8_t spawn_shot(uint16_t x, uint8_t y, uint8_t left);
void bump_actors_on_block(uint8_t col, uint8_t row);
// enemies.c
void enemies_reset(uint16_t from_x);               // spawn list restarts at the first object >= x
void enemies_update(void);
void enemies_draw(void);
void bump_enemies_on_block(uint16_t x, uint8_t top);

// --- sound.c: the effect table for gbe_sfx
enum { SFX_JUMP_SMALL, SFX_JUMP_BIG, SFX_COIN, SFX_STOMP, SFX_BUMP, SFX_BREAK, SFX_POWER_APPEAR,
       SFX_POWER_GET, SFX_SHOOT, SFX_KICK, SFX_HURT, SFX_ONEUP, SFX_TICK, SFX_PAUSE, SFX_DEATH,
       SFX_HURRY, SFX_COUNT };
