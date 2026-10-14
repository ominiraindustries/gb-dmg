// Enemies: Limo (WALKER) and Armadín (SHELL -> ball), spawning from the level object list,
// stomps and chains, kicks, shots and block bumps (GDD §2.8, §2.10)
#include "game.h"
#include <string.h>
#include "level1_1.h"

void act_move(uint8_t i);
void act_spawn(uint8_t i, uint8_t type, uint16_t x, uint8_t y);
uint8_t player_touches(uint8_t i, uint8_t ox, uint8_t oy, uint8_t w, uint8_t h);
extern uint8_t act_flip[], act_xs[], act_ys[];

enum { E_WALK, E_SQUASH, E_FLIP, E_BALL, E_BALL_MOVE };

#define ENEMY_COUNT   5
#define ENEMY_SPEED   0x0080
#define ENEMY_GRAV    0x0040
#define ENEMY_FALL    0x0300
#define BALL_SPEED    0x0300
#define SQUASH_FRAMES 30
#define BALL_WAIT     300
#define BALL_TREMBLE  60
#define KICK_GRACE    8
#define FLIP_VY       (-0x0200)
#define SPAWN_AHEAD   (160 + 16)

uint8_t obj_next;                       // next object of the level list to spawn
uint8_t enemy_grace[ENEMY_COUNT], enemy_chain[ENEMY_COUNT];
uint16_t enemy_wait[ENEMY_COUNT];       // ball: frames until it wakes up (> 255)
uint8_t stomp_chain;                    // reset when Teo touches the ground
uint8_t enemy_rot;                      // OAM rotation so overflowing lines flicker, not vanish
uint8_t enemy_phase;                    // half-rate update: enemies with (slot ^ phase) & 1 move

// Chain scores: 100 200 400 500 800 1000 2000 4000 5000 8000, then 1UP (GDD §2.10)
static const uint8_t chain_pts[10][3] = {
    {0x00,0x01,0}, {0x00,0x02,0}, {0x00,0x04,0}, {0x00,0x05,0}, {0x00,0x08,0},
    {0x00,0x10,0}, {0x00,0x20,0}, {0x00,0x40,0}, {0x00,0x50,0}, {0x00,0x80,0} };

static void award_chain(uint8_t *chain) {
    if (*chain < 10) add_score(chain_pts[*chain]);
    else add_life();
    if (*chain < 10) (*chain)++;
}

// Hitbox per enemy state (GDD §2.8): x offset, y offset, w, h
void hitbox(uint8_t i, uint8_t *hb) {
    hb[0] = 2; hb[2] = 12;
    if (act_type[i] == T_SHELL && act_state[i] == E_WALK) { hb[1] = 2; hb[3] = 14; }
    else { hb[1] = 4; hb[3] = 12; }
}

void enemies_reset(uint16_t from_x) {
    uint8_t i;
    obj_next = 0;
    while (obj_next < LEVEL1_1_OBJ_COUNT && ((uint16_t)level1_1_obj_col[obj_next] << 4) < from_x)
        obj_next++;
    stomp_chain = 0;
    for (i = 0; i < ENEMY_COUNT; i++) act_type[A_ENEMY0 + i] = T_NONE;
}

void spawn_enemies(void) {
    uint8_t i, type;
    while (obj_next < LEVEL1_1_OBJ_COUNT
           && ((uint16_t)level1_1_obj_col[obj_next] << 4) < camera_x + SPAWN_AHEAD) {
        type = level1_1_obj_type[obj_next];
        if (type == OBJ_WALKER || type == OBJ_SHELL) {
            for (i = 0; i < ENEMY_COUNT && act_type[A_ENEMY0 + i] != T_NONE; i++) ;
            if (i == ENEMY_COUNT) return;          // no free slot: wait (GDD: max 5 active)
            act_spawn(A_ENEMY0 + i, type == OBJ_WALKER ? T_WALKER : T_SHELL,
                      (uint16_t)level1_1_obj_col[obj_next] << 4,
                      Y_BIAS + (level1_1_obj_row[obj_next] << 4));
            act_vx[A_ENEMY0 + i] = -ENEMY_SPEED;   // start walking left
            enemy_grace[i] = enemy_chain[i] = 0;
            obj_next++;
            return;                                // at most one spawn per frame (CPU spikes)
        }
        obj_next++;
    }
}

void kill_flip(uint8_t i) {
    act_state[i] = E_FLIP;
    act_vy[i] = FLIP_VY;
    add_score(act_type[i] == T_WALKER ? PTS_100 : PTS_200);
    sfx(SFX_KICK);
}

// One physics step. dbl = 1: a 2-frame step (walking enemies update every other frame,
// half of them per frame - measured ~3300 T per call, so this halves the enemy cost).
// Locals instead of act_*[i] on every access.
void walk_on_map(uint8_t i, uint8_t dbl) {
    uint16_t x, front;
    uint8_t y, feet;
    int16_t vx = act_vx[i], vy = act_vy[i] + (dbl ? 2 * ENEMY_GRAV : ENEMY_GRAV);
    if (vy > ENEMY_FALL) vy = ENEMY_FALL;
    act_vy[i] = vy;
    act_move(i);                                   // asm, ~240 T per step
    if (dbl) act_move(i);
    x = act_x[i];
    y = act_y[i];
    front = vx > 0 ? x + 14 : x + 1;
    if (solid_at(front, y + 8)) {
        x = vx > 0 ? (front & 0xFFF0) - 15 : (front & 0xFFF0) + 15;
        vx = -vx;
    }
    feet = y + 15;
    if (vy > 0 && (solid_at(x + 3, feet) || solid_at(x + 12, feet))) {
        y = (((feet - Y_BIAS) & 0xF0) + Y_BIAS) - 16;
        act_ys[i] = 0;
        vy = 0;
    }
    act_x[i] = x;
    act_y[i] = y;
    act_vx[i] = vx;
    act_vy[i] = vy;
}

void kick(uint8_t i) {
    int16_t d = (int16_t)(act_x[i] + 8) - (int16_t)(player_x + 8);
    uint8_t left = d < 0 || (d == 0 && player_facing);
    act_state[i] = E_BALL_MOVE;
    act_vx[i] = left ? -BALL_SPEED : BALL_SPEED;
    enemy_grace[i - A_ENEMY0] = KICK_GRACE;
    enemy_chain[i - A_ENEMY0] = 0;
    add_score(PTS_400);
    sfx(SFX_KICK);
}

// Player contact: stomp from above or damage (GDD §2.8 "Pisotón")
void touch_player(uint8_t i, const uint8_t *hb) {
    uint8_t feet = player_y + hb_y + hb_h - 1;
    uint8_t stomp = player_vy > 0 && feet < act_y[i] + hb[1] + (hb[3] >> 1);
    switch (act_state[i]) {
    case E_WALK:
        if (stomp) {
            sfx(SFX_STOMP);
            award_chain(&stomp_chain);
            player_bounce();
            if (act_type[i] == T_WALKER) {
                act_state[i] = E_SQUASH;
                act_timer[i] = SQUASH_FRAMES;
            } else {
                act_state[i] = E_BALL;
                act_vx[i] = 0;
                enemy_wait[i - A_ENEMY0] = BALL_WAIT + BALL_TREMBLE;
                enemy_grace[i - A_ENEMY0] = 0;
            }
        } else {
            player_hurt();
        }
        break;
    case E_BALL:
        if (stomp) player_bounce();
        kick(i);
        break;
    case E_BALL_MOVE:
        if (stomp) {
            sfx(SFX_STOMP);
            player_bounce();
            act_state[i] = E_BALL;
            act_vx[i] = 0;
            enemy_wait[i - A_ENEMY0] = BALL_WAIT + BALL_TREMBLE;
        } else if (!enemy_grace[i - A_ENEMY0]) {
            player_hurt();
        }
        break;
    }
}

uint8_t boxes_overlap(uint8_t a, uint8_t b) {
    return act_x[a] + 2 < act_x[b] + 14 && act_x[b] + 2 < act_x[a] + 14
        && act_y[a] + 4 < act_y[b] + 16 && act_y[b] + 4 < act_y[a] + 16;
}

void enemy_vs_enemy(uint8_t i) {
    uint8_t j;
    for (j = A_ENEMY0; j < A_ENEMY0 + ENEMY_COUNT; j++) {
        if (j == i || act_type[j] == T_NONE || act_state[j] == E_FLIP || act_state[j] == E_SQUASH)
            continue;
        if ((uint16_t)(act_x[j] - act_x[i] + 12) >= 24) continue;   // cheap x reject first
        if (!boxes_overlap(i, j)) continue;
        if (act_state[i] == E_BALL_MOVE) {         // moving ball kills everything (chain)
            act_state[j] = E_FLIP;
            act_vy[j] = FLIP_VY;
            award_chain(&enemy_chain[i - A_ENEMY0]);
            sfx(SFX_KICK);
        } else if (act_state[i] == E_WALK && act_state[j] != E_BALL_MOVE) {
            // both turn around: i walks away from j
            act_vx[i] = act_x[i] < act_x[j] ? -ENEMY_SPEED : ENEMY_SPEED;
        }
    }
}

void shots_vs_enemy(uint8_t i, const uint8_t *hb) {
    uint8_t s;
    for (s = A_SHOT0; s < A_SHOT0 + 2; s++) {
        if (act_type[s] != T_SHOT) continue;
        if (act_x[s] + 7 > act_x[i] + hb[0] && act_x[s] + 1 < act_x[i] + hb[0] + hb[2]
            && act_y[s] + 7 > act_y[i] + hb[1] && act_y[s] + 1 < act_y[i] + hb[1] + hb[3]) {
            act_type[s] = T_PUF;
            act_timer[s] = 8;
            kill_flip(i);
            return;
        }
    }
}

// Block hit from below kills enemies standing on it (called from bump_actors_on_block)
void bump_enemies_on_block(uint16_t x, uint8_t top) {
    uint8_t i;
    for (i = A_ENEMY0; i < A_ENEMY0 + ENEMY_COUNT; i++) {
        if (act_type[i] == T_NONE || act_state[i] == E_FLIP || act_state[i] == E_SQUASH) continue;
        if ((uint8_t)(act_y[i] + 16) == top && act_x[i] + 14 > x && act_x[i] + 2 < x + 16) kill_flip(i);
    }
}

void enemies_update(void) {
    uint8_t i, hb[4];
    uint8_t mine;
    if (player_on_ground) stomp_chain = 0;
    spawn_enemies();
    enemy_phase ^= 1;
    for (i = A_ENEMY0; i < A_ENEMY0 + ENEMY_COUNT; i++) {
        if (act_type[i] == T_NONE) continue;
        act_flip[i]++;
        mine = ((i ^ enemy_phase) & 1) == 0;     // this enemy's physics frame
        switch (act_state[i]) {
        case E_SQUASH:
            if (--act_timer[i] == 0) act_type[i] = T_NONE;
            continue;
        case E_FLIP:                               // falls off the screen without collision
            act_vy[i] += ENEMY_GRAV;
            act_move(i);
            if (act_y[i] >= PIT_Y + 16) act_type[i] = T_NONE;
            continue;
        case E_BALL:
            if (--enemy_wait[i - A_ENEMY0] == 0) { // wakes up and walks towards Teo
                act_state[i] = E_WALK;
                act_vx[i] = player_x < act_x[i] ? -ENEMY_SPEED : ENEMY_SPEED;
            }
            if (mine) walk_on_map(i, 1);
            break;
        case E_BALL_MOVE:                          // fast: full rate so it does not judder
            if (enemy_grace[i - A_ENEMY0]) enemy_grace[i - A_ENEMY0]--;
            walk_on_map(i, 0);
            break;
        default:
            if (mine) walk_on_map(i, 1);
        }
        if (act_x[i] + 32 < camera_x || act_y[i] >= PIT_Y + 16) {
            act_type[i] = T_NONE;
            continue;
        }
        hitbox(i, hb);
        if (player_touches(i, hb[0], hb[1], hb[2], hb[3])) touch_player(i, hb);
        if (act_type[i] == T_NONE || act_state[i] == E_FLIP) continue;
        shots_vs_enemy(i, hb);
        if (act_state[i] == E_WALK || act_state[i] == E_BALL_MOVE) enemy_vs_enemy(i);
    }
}

void enemies_draw(void) {
    uint8_t i, k, s, ox, tile, prop, f;
    memset(&shadow_OAM[4], 0, ENEMY_COUNT * 2 * sizeof(OAM_item_t));   // hide the whole range
    if (++enemy_rot == ENEMY_COUNT) enemy_rot = 0;
    for (k = 0; k < ENEMY_COUNT; k++) {
        i = A_ENEMY0 + k;
        if (act_type[i] == T_NONE || act_x[i] + 16 < camera_x || act_x[i] > camera_x + 168) continue;
        s = 4 + ((k + enemy_rot >= ENEMY_COUNT ? k + enemy_rot - ENEMY_COUNT : k + enemy_rot) << 1);
        f = act_flip[i];
        prop = 0;
        if (act_type[i] == T_WALKER) {
            tile = act_state[i] == E_SQUASH ? SPR_LIMO_SQUASH : SPR_LIMO_WALK;
            if (act_state[i] == E_WALK && (f & 8)) prop = S_FLIPX;
        } else if (act_state[i] == E_WALK || act_state[i] == E_FLIP) {
            tile = (f & 8) ? SPR_ARMADIN_WALK2 : SPR_ARMADIN_WALK1;
            if (act_vx[i] < 0) prop = S_FLIPX;
        } else {
            tile = SPR_ARMADIN_BALL;
            if (act_state[i] == E_BALL && enemy_wait[k] < BALL_TREMBLE && (f & 4)) tile = SPR_ARMADIN_PEEK;
            if (act_state[i] == E_BALL_MOVE && (f & 4)) prop = S_FLIPX;
        }
        if (act_state[i] == E_FLIP) prop |= S_FLIPY;
        ox = (uint8_t)(act_x[i] - camera_x) + 8;
        oam16(s, ox, act_y[i], tile, prop);
    }
}
