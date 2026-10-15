// MADRIGUERA - shared declarations (GDD design/gdd.md, UI design/ui.md).
// Modules: main.c (loop, screens), link.c (Tilo: move, sword, damage), room.c (rooms, slide,
// enemies, pickups), hud.c (hearts in the window). Balance numbers: res/data/*.tbl (RULE(), en_*).
#pragma once
#include <string.h>
#include "gbe.h"
#include "vram.h"
#include "metatiles.h"
#include "world_index.h"
#include "tbl_rules.h"
#include "tbl_enemies.h"

// ---------------------------------------------------------------- screens and states
enum { SC_TITLE, SC_PLAY, SC_FIN };
extern uint8_t scene;

// ---------------------------------------------------------------- VRAM homes (GDD 7.2, game.json vram_scenes)
#define SPR_LINK     0           // sprite tiles (8x16 mode)
#define SPR_ENEMIES  46
#define SPR_FX       76
#define SPR_ITEMS    98
#define OAM_LINK     0           // 2
#define OAM_SWORD    2           // 2
#define OAM_FX       4           // 2 (puf / spark)
#define OAM_ENEMIES  6           // GBE_GACT_MAX x 2
#define OAM_PICKUPS  18          // PICKUP_MAX
#define PICKUP_MAX   4

// ---------------------------------------------------------------- rules (WRAM copy of rules.tbl)
extern uint16_t rules_cache[];
#define RULE(id) (rules_cache[id])
#define R8(id) ((uint8_t)rules_cache[id])
extern enemies_t en_rows[];

// ---------------------------------------------------------------- rooms (room.c, GDD 2.1-2.2, 2.6)
#define ROOM_W 10
#define ROOM_H 8
extern uint8_t room_c, room_r, sliding;       // current room; sliding: frames left of the slide
extern int16_t cam_tx, cam_ty;                // camera target (world px)
extern uint8_t en_hp[], en_inv[], en_kind[], en_alive;
extern uint8_t hitstop, cont_c, cont_r, cont_dir;
extern uint16_t cont_x, cont_y;
extern int16_t cam_wx, cam_wy;
uint8_t room_find_start(uint8_t *x, uint8_t *y);
void room_enter_now(uint8_t c, uint8_t r);    // LCD off: camera on the room, its enemies
void room_slide(uint8_t dir);                 // start the slide to the neighbour room
void room_update(void);                       // enemies, pickups, fx (not while sliding)
void room_slide_update(void);
void room_draw(void);
uint8_t sword_hits(uint8_t x0, uint8_t y0, uint8_t w, uint8_t h);   // screen box; returns hits
void enemies_touch_link(void);

// ---------------------------------------------------------------- Tilo (link.c, GDD 2.3-2.5)
enum { DIR_DOWN, DIR_UP, DIR_LEFT, DIR_RIGHT };
extern uint16_t lx, ly;                       // world px of the 16x16 sprite's top-left
extern uint8_t lxs, lys, ldir, lanim, sword_t, sword_buf, knock_t, knock_dir, inv_t, hp, hp_max, dead_t;
extern uint16_t deaths;
#define LSX ((uint8_t)(lx - cam_x))           // screen x / y (valid inside the room)
#define LSY ((uint8_t)(ly - cam_y))
void link_place(uint16_t x, uint16_t y, uint8_t dir);
void link_update(void);
void link_slide_step(uint8_t dir);            // 1 px during a room slide
void link_hurt(uint8_t dmg, uint8_t from_x, uint8_t from_y);
void link_draw(void);

// ---------------------------------------------------------------- HUD (hud.c, ui.md)
void hud_reset(void);
void hud_update(void);

// ---------------------------------------------------------------- sound
enum { SFX_SWORD, SFX_HIT, SFX_KILL, SFX_HURT, SFX_HEART, SFX_MENU, SFX_OK, SFX_COUNT };

// ---------------------------------------------------------------- tests and debugging
extern uint8_t cheat_flags;                   // tests only: 1 = invincible, 2 = frozen enemies
