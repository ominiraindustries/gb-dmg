// GRIFO - PLAY state: vertical scroll, player, shots, enemy bullets, sprites (GDD 2).
// Everything flying lives in 8-bit OAM space (GDD 2.0); only the BG scrolls.
#include <string.h>
#include "game.h"
#include "stage1.h"

#define PLAYER_X0     80
#define PLAYER_Y0     136
#define PLAYER_XMIN   8
#define PLAYER_XMAX   152
#define PLAYER_YMIN   32
#define PLAYER_YMAX   144
#define SPEED_STRAIGHT 0x0180
#define SPEED_DIAG     0x0110
#define FIRE_RATE      8
#define STOP_SCROLL    ((uint16_t)STAGE1_STOP_ROW * 16 - 112)   // top of the boss at line 16

uint8_t player_x, player_y, player_xs, player_ys, player_inv, player_tilt;
uint8_t power, bombs, lives, continues, fire_cd;
uint16_t scroll_speed, cheat_scroll;
uint8_t aim_req, aim_dx, aim_dy, aim_out;     // test hook: aim_out = aim_dir(aim_dx, aim_dy)

// ---------------------------------------------------------------- build (LCD off)
void play_build(void) {
    lcd_off_redraw_begin();
    init_bkg(T_BLANK);                                      // columns 20-31 = fog for the boss
    memset((uint8_t *)0x9C00, T_BLANK, 32 * 18);            // window
    vmap_load(stage1_map, STAGE1_HEIGHT, 0, STOP_SCROLL);
    scx_shadow = 0;
    player_x = PLAYER_X0; player_y = PLAYER_Y0; player_xs = player_ys = 0;
    player_inv = 0; player_tilt = 0; fire_cd = 0;
    pool_clear(0, P_EXPLO + N_EXPLO);
    scroll_speed = SCROLL_SPEED;
    hud_init();
    WX_REG = 7;
    WY_REG = 0;
    hud_cut = 1;
    SHOW_BKG; SHOW_WIN; SHOW_SPRITES;
    state = ST_PLAY;
    play_sub = PS_NORMAL;
    DISPLAY_ON;
}

// ---------------------------------------------------------------- player (GDD 2.1, 2.2)
static void move_axis(uint8_t *p, uint8_t *sub, uint16_t v, uint8_t neg, uint8_t lo, uint8_t hi) {
    uint16_t t = (uint16_t)*sub + (uint8_t)v;
    uint8_t d = (uint8_t)(v >> 8) + (uint8_t)(t >> 8);
    *sub = (uint8_t)t;
    if (neg) *p = (*p < lo + d) ? lo : *p - d;
    else *p = (*p + d > hi) ? hi : *p + d;
}

static void player_update(void) {
    uint8_t k = keys, dx = k & (J_LEFT | J_RIGHT), dy = k & (J_UP | J_DOWN);
    uint16_t v = (dx && dy) ? SPEED_DIAG : SPEED_STRAIGHT;
    if (dx == J_LEFT) move_axis(&player_x, &player_xs, v, 1, PLAYER_XMIN, PLAYER_XMAX);
    if (dx == J_RIGHT) move_axis(&player_x, &player_xs, v, 0, PLAYER_XMIN, PLAYER_XMAX);
    if (dy == J_UP) move_axis(&player_y, &player_ys, v, 1, PLAYER_YMIN, PLAYER_YMAX);
    if (dy == J_DOWN) move_axis(&player_y, &player_ys, v, 0, PLAYER_YMIN, PLAYER_YMAX);
    if (fire_cd) fire_cd--;
    if ((keys & J_A) && !fire_cd) {
        uint8_t i = pool_alloc(P_SHOT, N_SHOT);
        if (i != 0xFF) {
            pool_obj_t *o = &pool[i];
            o->t = 1; o->x = player_x + 4; o->xs = 0; o->y = player_y - 12; o->ys = 0;
            o->vx = 0; o->vy = -0x0500; o->tile = SPR_SHOT1; o->prop = 0;
        }
        fire_cd = FIRE_RATE;
    }
}

// ---------------------------------------------------------------- stress (frame budget tests)
// CHEAT_STRESS keeps every pool full: bullets fanned at the player from the top, enemies drifting
// down, so the budget test measures the GDD 9.3 peak without depending on the wave script.
static void stress_spawn(void) {
    uint8_t i;
    pool_obj_t *o;
    fire_first = P_BULLET; fire_n = N_BULLET; fire_t = 1; fire_tile = SPR_EBULLET; fire_prop = 0;
    if ((frame & 7) == 0) {
        uint8_t x = 24 + (frame & 0x70);
        fire_fan(x, 24, aim_dir(player_x + 4 - x, player_y + 4 - 24), 3, 2, 1);
    }
    if ((i = pool_alloc(P_ENEMY, N_ENEMY)) != 0xFF) {
        o = &pool[i];
        o->t = OBJ_DART; o->x = 16 + ((frame * 37) & 127); o->xs = 0; o->y = 8; o->ys = 0;
        o->vx = (frame & 1) ? 0x0040 : -0x0040; o->vy = 0x0080;
        o->tile = SPR_DART_0; o->prop = 0;
    }
}

// Shots vs enemies on alternate frames (gbe README: fast shots cannot tunnel 12 px boxes)
static void collide(void) {
    uint8_t s, e;
    pool_obj_t *o;
    if (frame & 1) {
        hit_ox = 2; hit_oy = 2; hit_ow = 12; hit_oh = 12;           // enemy box 12x12 (GDD 2.6)
        o = &pool[P_SHOT];
        for (s = 0; s < N_SHOT; s++, o++) {
            if (!o->t) continue;
            hit_qx = o->x + 2; hit_qy = o->y; hit_qw = 4; hit_qh = 12;
            if ((e = hit_first(P_ENEMY, N_ENEMY)) != 0xFF) { o->t = 0; pool[e].t = 0; }
        }
    }
    if (cheat_flags & CHEAT_INVINCIBLE) return;
    // player core 4x4 at (6,6) vs bullets 4x4 centered in the 8x8 (GDD 2.1, 2.5)
    hit_qx = player_x + 6; hit_qy = player_y + 6; hit_qw = 4; hit_qh = 4;
    hit_ox = 2; hit_oy = 2; hit_ow = 4; hit_oh = 4;
    if ((e = hit_first(P_BULLET, N_BULLET)) != 0xFF) pool[e].t = 0;   // death comes in M1b
}

void play_update(void) {
    uint16_t speed = (cheat_flags & CHEAT_SCROLL) ? cheat_scroll : scroll_speed;
    vmap_scroll(speed);
    if (aim_req) { aim_out = aim_dir((int8_t)aim_dx, (int8_t)aim_dy); aim_req = 0; }
    player_update();
    if (cheat_flags & CHEAT_STRESS) stress_spawn();
    if (!(cheat_flags & CHEAT_FREEZE)) {
        pool_move(P_BULLET, N_BULLET);
        pool_move(P_ENEMY, N_ENEMY);
        pool_move(P_SHOT, N_SHOT);
    }
    collide();
    hud_update();
}

void play_sprites(void) {
    uint8_t t = SPR_PLAYER;
    if (player_inv & 4) {                                     // blink while invulnerable
        shadow_OAM[OAM_PLAYER].y = shadow_OAM[OAM_PLAYER + 1].y = 0;
    } else {
        oam16(OAM_PLAYER, player_x, player_y, t, 0);
    }
    spr_group(OAM_BULLET, 12, P_BULLET, N_BULLET, 1);
    spr_group(OAM_ENEMY, 12, P_ENEMY, N_ENEMY, 2);
    spr_group(OAM_ITEM, 2, P_ITEM, N_ITEM, 2);
    spr_group(OAM_SHOT, 8, P_SHOT, N_SHOT, 1);
    spr_group(OAM_EXPLO, 4, P_EXPLO, N_EXPLO, 2);
    spr_rot++;
}

void play_draw_vram(void) {
    vmap_draw_vram();
    hud_draw_vram();
}
