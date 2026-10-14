// Moving objects other than Teo: items, projectiles, brick debris, coins out of blocks
// (enemies use the same arrays from step 3). GDD §2.4, §2.7, §2.9.
#include "game.h"

uint8_t act_type[ACT_MAX], act_xs[ACT_MAX], act_y[ACT_MAX], act_ys[ACT_MAX];
uint8_t act_state[ACT_MAX], act_timer[ACT_MAX], act_flip[ACT_MAX];
uint16_t act_x[ACT_MAX];
int16_t act_vx[ACT_MAX], act_vy[ACT_MAX];

// First OAM sprite of each slot (GDD §7.3) and how many 8x16 sprites it uses
static const uint8_t act_spr[ACT_MAX] = { 4, 6, 8, 10, 12, 14, 16, 17, 18, 19, 20, 21, 22, 23 };

#define ITEM_RISE_FRAMES 32
#define ITEM_SPEED       0x0100
#define ITEM_GRAV        0x0040
#define ITEM_FALL_MAX    0x0300
#define SHOT_SPEED       0x0300
#define SHOT_GRAV        0x0060
#define SHOT_BOUNCE      (-0x0200)
#define PUF_FRAMES       8
#define DEBRIS_GRAV      0x0040
#define DEBRIS_LIFE      64
#define COINPOP_FRAMES   24

void actors_clear(void) {
    uint8_t i;
    for (i = 0; i < ACT_MAX; i++) act_type[i] = T_NONE;
}

static void act_move(uint8_t i) {
    uint16_t t = (uint16_t)act_xs[i] + (uint8_t)act_vx[i];
    act_xs[i] = (uint8_t)t;
    act_x[i] += (int8_t)(act_vx[i] >> 8) + (t >> 8);
    t = (uint16_t)act_ys[i] + (uint8_t)act_vy[i];
    act_ys[i] = (uint8_t)t;
    act_y[i] += (int8_t)(act_vy[i] >> 8) + (t >> 8);
}

static void act_spawn(uint8_t i, uint8_t type, uint16_t x, uint8_t y) {
    act_type[i] = type;
    act_x[i] = x;
    act_y[i] = y;
    act_xs[i] = act_ys[i] = 0;
    act_vx[i] = act_vy[i] = 0;
    act_state[i] = act_timer[i] = act_flip[i] = 0;
}

// ---------------------------------------------------------------- spawners

void spawn_item(uint8_t type, uint8_t col, uint8_t row) {
    // Only one item at a time: a new one replaces the old (GDD §2.9)
    act_spawn(A_ITEM, type, (uint16_t)col << 4, Y_BIAS + (row << 4));
    act_timer[A_ITEM] = ITEM_RISE_FRAMES;          // state 0: rising out of the block
}

void spawn_debris(uint8_t col, uint8_t row) {
    static const int16_t vx[4] = { -0x0100, 0x0100, -0x0100, 0x0100 };
    static const int16_t vy[4] = { -0x0400, -0x0400, -0x0280, -0x0280 };
    uint16_t x = (uint16_t)col << 4;
    uint8_t y = Y_BIAS + (row << 4), i;
    for (i = 0; i < 4; i++) {
        act_spawn(A_DEBRIS0 + i, T_DEBRIS, x + ((i & 1) << 3), y + ((i & 2) << 2));
        act_vx[A_DEBRIS0 + i] = vx[i];
        act_vy[A_DEBRIS0 + i] = vy[i];
        act_timer[A_DEBRIS0 + i] = DEBRIS_LIFE;
    }
}

void spawn_coinpop(uint8_t col, uint8_t row) {
    uint8_t i = (act_type[A_COIN0] == T_NONE) ? A_COIN0 : A_COIN0 + 1;
    act_spawn(i, T_COINPOP, ((uint16_t)col << 4) + 4, Y_BIAS + (row << 4) - 16);
    act_vy[i] = -0x0400;
    act_timer[i] = COINPOP_FRAMES;
}

uint8_t spawn_shot(uint16_t x, uint8_t y, uint8_t left) {
    uint8_t i = A_SHOT0;
    if (act_type[i] != T_NONE) i++;
    if (act_type[i] != T_NONE) return 0;           // max 2 on screen
    act_spawn(i, T_SHOT, x, y);
    act_vx[i] = left ? -SHOT_SPEED : SHOT_SPEED;
    act_vy[i] = 0x0100;
    return 1;
}

// A block hit from below kicks the item standing on it (enemies: step 3)
void bump_actors_on_block(uint8_t col, uint8_t row) {
    uint8_t top = Y_BIAS + (row << 4);
    uint16_t x = (uint16_t)col << 4;
    if (act_type[A_ITEM] == T_ITEM_GROW || act_type[A_ITEM] == T_ITEM_1UP) {
        if (act_state[A_ITEM] && (uint8_t)(act_y[A_ITEM] + 16) == top
            && act_x[A_ITEM] + 16 > x && act_x[A_ITEM] < x + 16) {
            act_vy[A_ITEM] = -0x0300;
            act_vx[A_ITEM] = -act_vx[A_ITEM];
        }
    }
}

// ---------------------------------------------------------------- per type

static uint8_t player_touches(uint8_t i, uint8_t ox, uint8_t oy, uint8_t w, uint8_t h) {
    uint16_t ax = act_x[i] + ox, px = player_x + HB_X;
    uint8_t ay = act_y[i] + oy, py = player_y + hb_y;
    return ax < px + HB_W && px < ax + w && ay < py + hb_h && py < ay + h;
}

// Walking item: same map collision idea as the player, simpler (16x16 box)
static void item_walk(uint8_t i) {
    uint16_t front;
    uint8_t feet;
    act_vy[i] += ITEM_GRAV;
    if (act_vy[i] > ITEM_FALL_MAX) act_vy[i] = ITEM_FALL_MAX;
    act_move(i);
    front = act_vx[i] > 0 ? act_x[i] + 15 : act_x[i];
    if (solid_at(front, act_y[i] + 8)) {
        act_x[i] = act_vx[i] > 0 ? (front & 0xFFF0) - 16 : (front & 0xFFF0) + 16;
        act_vx[i] = -act_vx[i];
    }
    feet = act_y[i] + 15;
    if (act_vy[i] > 0 && (solid_at(act_x[i] + 2, feet) || solid_at(act_x[i] + 13, feet))) {
        act_y[i] = (((feet - Y_BIAS) & 0xF0) + Y_BIAS) - 16;
        act_ys[i] = 0;
        act_vy[i] = 0;
    }
}

static void update_item(uint8_t i) {
    if (act_state[i] == 0) {                       // rising out of the block, no collision
        act_vy[i] = -0x0080;
        act_move(i);
        if (--act_timer[i] == 0) {
            act_state[i] = 1;
            act_vy[i] = 0;
            act_vx[i] = (act_type[i] == T_ITEM_SHOT) ? 0 : ITEM_SPEED;
        }
        return;
    }
    if (act_type[i] != T_ITEM_SHOT) item_walk(i);
    if (player_touches(i, 2, 2, 12, 14)) {
        player_power_up(act_type[i]);
        act_type[i] = T_NONE;
    }
}

static void update_shot(uint8_t i) {
    uint8_t feet;
    act_vy[i] += SHOT_GRAV;
    act_move(i);
    if (solid_at(act_x[i] + (act_vx[i] > 0 ? 6 : 1), act_y[i] + 3)) {
        act_type[i] = T_PUF;                       // hit a wall
        act_timer[i] = PUF_FRAMES;
        return;
    }
    feet = act_y[i] + 6;
    if (act_vy[i] > 0 && solid_at(act_x[i] + 3, feet)) {
        act_y[i] = (((feet - Y_BIAS) & 0xF0) + Y_BIAS) - 7;
        act_vy[i] = SHOT_BOUNCE;
    }
    act_flip[i]++;
}

static void update_debris(uint8_t i) {
    act_vy[i] += DEBRIS_GRAV;
    act_move(i);
    act_flip[i]++;
    if (--act_timer[i] == 0 || act_y[i] >= PIT_Y + 16) act_type[i] = T_NONE;
}

static void update_coinpop(uint8_t i) {
    act_vy[i] += 0x0040;
    act_move(i);
    act_flip[i]++;
    if (--act_timer[i] == 0) act_type[i] = T_NONE;
}

void actors_update(void) {
    uint8_t i;
    for (i = A_ITEM; i < ACT_MAX; i++) {
        switch (act_type[i]) {
        case T_NONE: continue;
        case T_ITEM_GROW: case T_ITEM_SHOT: case T_ITEM_1UP: update_item(i); break;
        case T_SHOT: update_shot(i); break;
        case T_PUF: if (--act_timer[i] == 0) act_type[i] = T_NONE; break;
        case T_DEBRIS: update_debris(i); break;
        case T_COINPOP: update_coinpop(i); break;
        }
        // despawn when far off the left of the camera, or fallen out of the level
        if (act_type[i] != T_NONE
            && (act_x[i] + 32 < camera_x || act_x[i] > camera_x + 192 || act_y[i] >= PIT_Y + 16)) {
            act_type[i] = T_NONE;
        }
    }
}

// ---------------------------------------------------------------- drawing

static void draw16(uint8_t s, uint8_t tile, uint8_t ox, uint8_t y, uint8_t prop) {
    if (prop & S_FLIPX) {
        set_sprite_tile(s, tile + 2); set_sprite_tile(s + 1, tile);
    } else {
        set_sprite_tile(s, tile); set_sprite_tile(s + 1, tile + 2);
    }
    set_sprite_prop(s, prop); set_sprite_prop(s + 1, prop);
    move_sprite(s, ox, y);
    move_sprite(s + 1, ox + 8, y);
}

static void draw8(uint8_t s, uint8_t tile, uint8_t ox, uint8_t y, uint8_t prop) {
    set_sprite_tile(s, tile);
    set_sprite_prop(s, prop);
    move_sprite(s, ox, y);
}

void actors_draw(void) {
    static const uint8_t spin_tile[4] = { SPR_COIN_SPIN0, SPR_COIN_SPIN1, SPR_COIN_SPIN2, SPR_COIN_SPIN1 };
    uint8_t i, s, ox, f;
    for (i = A_ITEM; i < ACT_MAX; i++) {
        s = act_spr[i];
        if (act_type[i] == T_NONE || act_x[i] + 16 < camera_x || act_x[i] > camera_x + 168) {
            hide_sprite(s);
            if (i == A_ITEM) hide_sprite(s + 1);
            continue;
        }
        ox = (uint8_t)(act_x[i] - camera_x) + 8;
        f = act_flip[i];
        switch (act_type[i]) {
        case T_ITEM_GROW:
        case T_ITEM_SHOT:
        case T_ITEM_1UP: {
            uint8_t tile = act_type[i] == T_ITEM_GROW ? SPR_ITEM_YELMO
                         : act_type[i] == T_ITEM_SHOT ? SPR_ITEM_PERGAMINO : SPR_ITEM_POCION;
            // behind the block while rising out of it
            draw16(s, tile, ox, act_y[i], act_state[i] ? 0 : S_PRIORITY);
            break;
        }
        case T_SHOT:   draw8(s, SPR_CHISPA, ox, act_y[i], (f & 4) ? S_FLIPX | S_FLIPY : 0); break;
        case T_PUF:    draw8(s, SPR_PUF, ox, act_y[i], 0); break;
        case T_DEBRIS: draw8(s, SPR_DEBRIS, ox, act_y[i], (f & 8) ? S_FLIPX : ((f & 4) ? S_FLIPY : 0)); break;
        case T_COINPOP: {
            uint8_t k = (f >> 2) & 3;
            draw8(s, spin_tile[k], ox, act_y[i], k == 3 ? S_FLIPX : 0);
            break;
        }
        }
    }
}
