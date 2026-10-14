// TORRE HUNDIDA - shared declarations (design/gdd.md is the spec; section numbers refer to it)
#pragma once
#include "gbe.h"
#include "vram.h"               // VRAM_<TILESET> bases from game.json vram_order
#include "walls.h"
#include "spr.h"
#include "ui.h"
#include "font.h"
#include "view.h"

// ---------------------------------------------------------------- map (GDD 2.0)
enum { CELL_FLOOR, CELL_WALL, CELL_DOOR, CELL_LOCKED, CELL_DOOR_OPEN, CELL_UP, CELL_DOWN };
enum { OBJ_NONE, OBJ_START, OBJ_FAST, OBJ_GUARD, OBJ_GUARD_KEY, OBJ_SLOW, OBJ_POTION, OBJ_STAFF,
       OBJ_AMULET, OBJ_KEY };
enum { IT_NONE, IT_KEY, IT_POTION, IT_STAFF, IT_AMULET };
enum { MON_FAST, MON_GUARD, MON_SLOW };
#define MAP_W      16
#define MON_MAX    12
#define ITEM_MAX   24
#define MS_ALERT   0x01         // mon_state bits (GDD 9.7)
#define MS_WINDUP  0x02
#define MS_DYING   0x04

// ---------------------------------------------------------------- states (GDD 4)
enum { ST_TITLE, ST_PLAY, ST_MENU, ST_MAP, ST_GAMEOVER, ST_CLEAR };
enum { PS_IDLE, PS_BUSY, PS_DYING };

// cheat_flags (tests only)
#define CHEAT_INVINCIBLE 0x01
#define CHEAT_FROZEN     0x02   // monsters do not think
#define CHEAT_ONE_HIT    0x04
#define CHEAT_SEEN_ALL   0x08

// ---------------------------------------------------------------- screen layout (GDD 9.5)
#define VIEW_ROW   8            // the view lives in BG map rows 8-19 of both maps
#define SCY_BASE   64           // ... shown at screen lines 0-95
#define HUD_WY     96           // window (HUD) from line 96, rows 0-5 of $9C00
#define WIN_ROW(r) ((uint8_t *)0x9C00 + ((r) << 5))

// ---------------------------------------------------------------- globals (GDD 9.7)
extern uint8_t state, play_sub, frame, cheat_flags;
extern uint8_t dmap[256], seen[32];
extern uint8_t px, py, pf, shown_x, shown_y, shown_f;
extern uint8_t hp, hp_max, key_count, potions, weapon, staff_owned, amulet, atk_cd, move_cd, kills;
extern uint16_t play_secs;
extern uint8_t mon_type[MON_MAX], mon_x[MON_MAX], mon_y[MON_MAX], mon_hp[MON_MAX], mon_state[MON_MAX];
extern uint8_t mon_move_t[MON_MAX], mon_atk_t[MON_MAX], mon_wind[MON_MAX], mon_item[MON_MAX];
extern uint8_t mon_flash[MON_MAX], mon_count, aware_count;
extern uint8_t item_type[ITEM_MAX], item_x[ITEM_MAX], item_y[ITEM_MAX], item_count, items_total;
extern uint8_t mon_total, hurt_dir, hurt_t, clear_req, items_got, last_roll;
extern const uint8_t cell_class[];
// occupancy maps (cell -> index + 1, 0 = none): O(1) lookups; a scan of the lists cost ~1.2k T per
// lookup and play_sprites / AI did several per frame (~9k T). Tests that edit the lists set
// maps_dirty and the game rebuilds both maps.
extern uint8_t mon_map[256], item_map[256], maps_dirty, dying_count;
void maps_rebuild(void);

// play.c
uint8_t walkable(uint8_t x, uint8_t y);
uint8_t mon_at(uint8_t x, uint8_t y);           // index or 0xFF
void hero_damage(uint8_t dmg, uint8_t dir);      // dir: 0 front, 1 right, 2 back, 3 left
void play_start(void);
void play_update(void);
void play_sprites(void);
void hud_dirty(void);
void say(const char *s);
void say_num(const char *prefix, uint8_t n, const char *suffix);
void mark_seen(void);

// monsters.c
void monsters_load(void);
void monsters_update(void);
void monster_hit(uint8_t m);                     // hero attacks monster m (rolls, damage, death)
uint8_t mon_sprite_base(uint8_t type, uint8_t d);

enum { SFX_BUMP, SFX_SWING, SFX_HIT, SFX_MISS, SFX_KILL, SFX_GROWL, SFX_HURT, SFX_DOOR, SFX_UNLOCK,
       SFX_LOCKED, SFX_PICK, SFX_DRINK, SFX_DEATH, SFX_CLEAR, SFX_MENU_MOVE, SFX_MENU_OK,
       SFX_MENU_BACK, SFX_SAVE, SFX_COUNT };
