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
extern uint8_t cheat_flags;                        // written by tests only: bit0 invincible, bit1 no timer

// --- level.c
extern uint8_t level[];
extern uint8_t level_cols;                         // N metatile columns
extern uint16_t camera_x;
extern uint8_t scx_shadow;
extern uint16_t cols_written;                      // next tile column to stream
void level_load(void);                             // LCD must be off
void level_update_camera(void);
uint8_t mt_at(uint16_t x, uint8_t y);              // metatile id at a world pixel (pits/walls handled)
uint8_t solid_at(uint16_t x, uint8_t y);
void level_draw_vram(void);

// --- hud.c
void hud_init(void);                               // LCD off: draws both window rows
void hud_draw_vram(void);
void hud_set_time(uint16_t units);

// --- player.c
extern uint16_t player_x;
extern uint8_t player_y;
extern int16_t player_vx, player_vy;
extern uint8_t player_form, player_on_ground, player_facing;
void player_spawn(uint16_t x, uint8_t y);
void player_update(void);
void player_draw(void);

// --- vram.s (call only in VBlank or with the LCD off)
void vram_col16(uint8_t *dst, const uint8_t *src);  // 16 tiles down a BG map column (stride 32)
