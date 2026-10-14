// GRIFO - shared declarations (design/gdd.md is the spec; section numbers refer to it)
#pragma once
#include "gbe.h"
#include "bcd.h"
#include "metatiles.h"         // generated from res/metatiles.mt
#include "bg.h"
#include "spr.h"
#include "ui.h"
#include "font.h"
#include "vram.h"                // VRAM_<TILESET> bases from game.json vram_order

// ---------------------------------------------------------------- VRAM (design/ui.md 0.2)
#define TILE_UI     VRAM_UI
#define TILE_FONT   VRAM_FONT
#define T_DIGIT0    (TILE_FONT + FONT_DIGIT0)
#define T_LETTER_A  (TILE_FONT + FONT_LETTER_A)
#define T_BLANK     (TILE_UI + UI_BLANK)
#define BG_BASE     VRAM_BG   // stage tiles; uiscreens loads into the same slot

// ---------------------------------------------------------------- level objects (stage1.lvl)
enum {
    OBJ_NONE, OBJ_DART, OBJ_WAVE, OBJ_WAVE_F, OBJ_SWOOP, OBJ_SWOOP_G,
    OBJ_CARRIER_P, OBJ_CARRIER_B, OBJ_TURRET
};
// runtime record types (after the level object types)
#define OBJ_EXPLO        20     // explosion in screen space
#define OBJ_EXPLO_SCROLL 21     // explosion on the ground (follows the scroll; pad = map row)
#define OBJ_ITEM_P       30
#define OBJ_ITEM_B       31

// ---------------------------------------------------------------- pools (gbe_pool records)
// OAM groups follow the GDD 7.3 priority order; pool ranges are independent of OAM order.
#define P_BULLET   0            // enemy bullets
#define N_BULLET   12
#define P_ENEMY    12           // flying enemies (and their explosions)
#define N_ENEMY    6
#define P_ITEM     18
#define N_ITEM     1
#define P_SHOT     19           // player shots
#define N_SHOT     8
#define P_EXPLO    27           // extra explosions (turrets, boss)
#define N_EXPLO    2
#define P_TURRET   29           // ground turrets: logical records, never drawn (BG metatiles)
#define N_TURRET   4
#define P_GAME_END 33
// GBE_POOL_MAX (gbe_config.h) adds 8 scratch records for the engine selftest

#define OAM_PLAYER 0
#define OAM_BULLET 2
#define OAM_ENEMY  14
#define OAM_ITEM   26
#define OAM_SHOT   28
#define OAM_EXPLO  36

// ---------------------------------------------------------------- states (GDD 4)
enum { ST_TITLE, ST_PLAY, ST_PAUSE, ST_CONTINUE, ST_GAMEOVER, ST_CLEAR };
enum { PS_NORMAL, PS_DYING, PS_RESPAWN, PS_BOSS_INTRO, PS_BOSS, PS_BOSS_DEAD, PS_OUTRO };

// cheat_flags (written only by tests)
#define CHEAT_INVINCIBLE 0x01
#define CHEAT_BOMBS      0x02
#define CHEAT_FREEZE     0x04   // objects frozen, only OAM rebuilt
#define CHEAT_SCROLL     0x08   // scroll speed forced to cheat_scroll
#define CHEAT_STRESS     0x10   // keep every pool full (frame budget measurement)
#define CHEAT_NO_LEVEL   0x20   // level objects do not appear (isolated mechanic tests)

#define SCROLL_SPEED 0x0080     // 0.5 px/f (GDD 2.9)

enum { SFX_SHOT, SFX_HIT, SFX_BOOM, SFX_BIG_BOOM, SFX_ITEM, SFX_POWER, SFX_BOMB, SFX_DEATH,
       SFX_EXTEND, SFX_WARN, SFX_BOSS_HIT, SFX_PAUSE, SFX_START, SFX_TICK, SFX_COUNT };

extern uint8_t state, play_sub, frame, cheat_flags;
extern uint16_t scroll_speed, cheat_scroll;
extern uint8_t player_x, player_y, player_inv, power, bombs, lives, continues, extends;
extern uint8_t score[3], hiscore[3];

// hud.c
#define HUD_SCORE 0x01
#define HUD_LIVES 0x02
#define HUD_BOMBS 0x04
#define HUD_POWER 0x08
#define HUD_BAR   0x10
#define HUD_ROW   0x80          // whole row (after a message)
enum { MSG_NONE, MSG_FASE, MSG_PELIGRO, MSG_PAUSA };
extern uint8_t hud_buf[20], hud_dirty, hud_msg, hud_msg_timer, hud_bar_px, boss_bar_on, new_record;
void hud_init(void);
void hud_update(void);          // counters -> hud_buf (outside VBlank)
void hud_draw_vram(void);       // VBlank: text queue, message or dirty counters
void add_score(const uint8_t *bcd);
void add_score_hundreds(uint8_t n);
void add_score_tens(uint8_t n);
void hiscore_update(void);
void hud_message(uint8_t msg, uint8_t frames);
void hud_message_end(void);
void hud_message_update(void);
void text_tiles(uint8_t *d, const char *s);
void bcd_tiles(uint8_t *d, const uint8_t *bcd);
void text_put(uint8_t *dst, const uint8_t *tiles, uint8_t n);
void text_put_str(uint8_t *dst, const char *s);

// boss.c
enum { BOSS_NONE, BOSS_INTRO, BOSS_FIGHT, BOSS_DEAD, BOSS_OUTRO, BOSS_DONE };
extern uint8_t boss_hp, boss_phase, boss_state;
extern int8_t boss_dx, boss_dy;
void boss_reset(void);
void boss_update(void);
void boss_damage(uint8_t dmg);
uint8_t boss_overlaps(uint8_t x, uint8_t y, uint8_t w, uint8_t h);

// screens.c
extern uint8_t died_in_stage;
void game_start(void);
void title_build(void);
void title_update(void);
void pause_toggle(void);
void pause_update(void);
void continue_start(void);
void continue_update(void);
void gameover_build(void);
void gameover_update(void);
void stage_clear(void);
void clear_build(void);
void clear_update(void);

// enemies.c
extern uint8_t obj_ptr, no_fire, fire_busy, kill_quiet;
extern const int8_t wave_ofs[128];
extern const uint8_t score_1000[3];
uint8_t aim_at(uint8_t x, uint8_t y);
void bullets_setup(uint8_t tile);
void enemies_reset(void);
void formations_clear(void);
void objects_update(void);
void enemies_update(void);
void turrets_update(void);
void effects_update(void);
void enemy_damage(uint8_t i, uint8_t dmg);
void turret_damage(uint8_t i, uint8_t dmg);

// player.c
extern uint8_t player_xs, player_ys, bomb_timer, dead_timer;
void player_reset(void);
void play_respawn(void);
void player_update(void);
void player_collide(void);
void player_sprites(void);

// play.c
void play_build(void);          // LCD off: stage, HUD, registers
void play_update(void);
void play_sprites(void);
void play_draw_vram(void);
