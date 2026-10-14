// FARO - shared declarations of the game (named rpg.h: res/faro.tiles generates a faro.h) (GDD games/faro/design/gdd.md).
// Layers (GDD 10.1): engine = harness/common gbe_*; RPG kit = src/rpg/*.c (genre rules, NO content:
// no species/item/map ids or texts - those come from res/data tables, maps and scripts);
// glue = src/main.c. Kit modules that are not per-frame hot code live in ROM bank 1 (BANKED).
#pragma once
#include <string.h>
#include "gbe.h"
#include "vram.h"
#include "world_index.h"
#include "script_ids.h"
#include "metatiles.h"

enum { SFX_BUMP, SFX_BLIP, SFX_OK, SFX_PICK, SFX_COUNT };
extern uint8_t cheat_flags;

// ---------------------------------------------------------------- states (GDD 4.2)
enum { ST_TITLE, ST_FIELD, ST_BATTLE, ST_MENU, ST_FAINT, ST_DEMO_END };
extern uint8_t state, field_sub;

// ---------------------------------------------------------------- VRAM (GDD 7.2, ui.md 1)
// Sprite tiles 0-127 at $8000 (8x16 mode): Leo 0-31, NPC looks 32-79, creatures 80-111, effects 112-127.
#define SPR_LEO      0
#define SPR_NPC      32
#define SPR_CRITTER  80
#define SPR_FX       112
#define OAM_HUD      0          // 2 HUD icons
#define OAM_LEO      2          // 2
#define OAM_FX       4          // 4: shadow / stone / emotes
#define OAM_ACTORS   8          // 12 actors x 2

// ---------------------------------------------------------------- field (src/rpg/field.c)
enum { DIR_DOWN, DIR_UP, DIR_LEFT, DIR_RIGHT };
extern const int8_t dir_dx[4], dir_dy[4];
extern uint8_t px, py, pdir, pstep_px, pmoving, psneak;
extern uint16_t steps;
extern int16_t cam_want_x, cam_want_y;
extern uint8_t last_clinic_map, last_clinic_x, last_clinic_y;
// actor kinds (gact type low bits; GACT_ANIM2 / GACT_ANIMF are layout flags)
enum { ACT_NONE, ACT_NPC, ACT_ITEM, ACT_CREATURE };
#define ACT_KIND(t) ((t) & 0x0F)
extern uint16_t act_script[GBE_GACT_MAX];      // NPC: script id; item: object index
extern uint8_t act_obj_x[GBE_GACT_MAX], act_obj_y[GBE_GACT_MAX];   // map object that made the actor
// map object types: order of game.json "world_objects"
enum { OBJ_NPC, OBJ_SIGN, OBJ_WARP, OBJ_ITEM, OBJ_SPAWN, OBJ_FORAGE, OBJ_TRIGGER, OBJ_PATCH };
#define EV_U16(e, k) ((e)->d[k] | ((uint16_t)(e)->d[(k) + 1] << 8))

void field_enter(uint8_t map, uint8_t x, uint8_t y, uint8_t dir);   // LCD off
void field_update(void);
void field_draw(void);
void field_vblank(void);
void map_gfx(uint8_t mtset);          // glue (main.c): LCD off, load a metatile set's tiles + table
extern uint8_t field_set;

// ---------------------------------------------------------------- hooks other kit modules provide
// (stubs until each module exists; the field calls them)
uint8_t player_has_ability(uint16_t ability_mask);   // bank 0 (src/rpg/script_ops.c)
void survival_step(void) BANKED;                // once per completed step (hunger, spoilage, regen)
void creatures_sector(uint8_t sx, uint8_t sy) BANKED;   // spawn points of a sector that loaded
void creatures_update(void) BANKED;
uint8_t creature_touch(uint8_t act) BANKED;     // player bumped into a creature actor: 1 = battle
void item_pickup(uint8_t item, uint8_t n) BANKED;
void forage(uint8_t table, uint8_t x, uint8_t y) BANKED;
void menu_open_panel(void) BANKED;

// ---------------------------------------------------------------- screens (src/rpg/title.c ...)
#define TITLE_NONE 0xFF
enum { TITLE_CONTINUE, TITLE_NEW, TITLE_OPTIONS };
void title_build(void) BANKED;          // LCD off
uint8_t title_update(void) BANKED;      // TITLE_NONE or the choice
uint8_t save_exists(void) BANKED;       // a valid save in SRAM

// ---------------------------------------------------------------- data tables (res/data, banked)
#include "tbl_rules.h"
#include "tbl_items.h"
#include "tbl_player.h"
#include "tbl_caps.h"
#include "tbl_species.h"
#include "tbl_moves.h"
#include "tbl_skills.h"
#include "tbl_statuses.h"
#include "tbl_looks.h"
#include "tbl_buffs.h"
#include "tbl_families.h"

// ---------------------------------------------------------------- Leo (src/rpg/player.c, GDD 8.7)
#define INV_SLOTS     128
#define SPECIES_SLOTS 48
#define FULL_SLOTS    24
extern uint8_t plevel, pv, pv_max, en, en_max, patk, pdef, pagi, sac, buff, p_st, p_st_t, armor, lamp_ring;
extern uint16_t xp, money, buff_steps, skills_known;
extern uint8_t weapons[3], inv[INV_SLOTS], reg_seen[6], reg_caught[6], kills[SPECIES_SLOTS], recipe_known[4];
extern uint8_t full_n, full_sp[FULL_SLOTS], full_lv[FULL_SLOTS], has_zurron;
uint16_t rule(uint8_t id) BANKED;
void item_row(uint8_t id, items_t *r) BANKED;
void player_stats(void) BANKED;
void player_new(void) BANKED;
uint8_t player_gain_xp(uint16_t n) BANKED;
uint8_t inv_cap(uint8_t id) BANKED;
uint8_t inv_add(uint8_t id, uint8_t n) BANKED;
uint8_t inv_take(uint8_t id, uint8_t n) BANKED;
uint8_t player_has_ability_b(uint16_t mask) BANKED;
uint8_t reg_has(uint8_t *set, uint8_t sp) BANKED;
void reg_set(uint8_t *set, uint8_t sp) BANKED;

// ---------------------------------------------------------------- battle core (src/rpg/battle_core.c)
enum { B_ONGOING, B_HUNTED, B_CAPTURED, B_FLED, B_ESCAPED, B_FAINTED };          // b_result
enum { B_ACT_ATTACK, B_ACT_SKILL, B_ACT_ITEM, B_ACT_GADGET, B_ACT_CAPTURE, B_ACT_FLEE };
enum { B_USE_WEAPON, B_USE_SKILL, B_USE_ITEM, B_USE_GADGET, B_USE_MOVE };      // EV_USE kinds
// events b_ev[i] = { type, a, b, c } (the screen plays them; who/target: 0 Leo, 1 the creature)
enum { EV_USE,          // who, kind, id
       EV_MISS,         // who missed
       EV_HIT,          // target, damage, flags (1 crit, 2 weak, 4 resist, 8 immune)
       EV_STATUS,       // target, status
       EV_STATUS_END,   // target, status
       EV_SKIP,         // who, status (lost turn)
       EV_DOT,          // target, damage, status
       EV_HEAL,         // who, amount
       EV_EN,           // amount
       EV_REVEAL, EV_AIM, EV_DEBUFF, EV_DEFUP, EV_BUFF,
       EV_BAIT,         // 1, eaten
       EV_THROW,        // 0, lantern
       EV_SHAKES,       // 1, shakes, captured
       EV_NOCOND,       // the light slips away (capture condition)
       EV_FLEE,         // who, ok
       EV_STEAL,        // 1, item
       EV_WATCH,        // the creature only watches
       EV_END };        // result
#define B_EV_MAX 24
extern uint8_t b_species, b_level, b_cpv, b_cpv_max, b_catk, b_cdef, b_cagi, b_cst, b_cst_t;
extern uint8_t b_ent_t, b_calm_t, b_lit_t, b_def_t, b_deb_t, b_down, b_fly, b_bait, b_flee_tries;
extern uint8_t b_aim, b_turn, b_result, b_free, b_seen, b_new_species, b_levelups;
extern uint8_t b_loot_n, b_loot_item[3], b_loot_cnt[3];
extern uint16_t b_xp;
extern uint8_t b_ev[B_EV_MAX][4], b_ev_n;
extern species_t b_sp;
void battle_begin(uint8_t species, uint8_t lvl, uint8_t free) BANKED;
void battle_open_turn(void) BANKED;
void battle_turn(uint8_t kind, uint8_t id, uint8_t weapon) BANKED;
