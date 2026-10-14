// Enemies: Limo (WALKER) and Armadín (SHELL -> ball), spawning from the level object list,
// stomps and chains, kicks, shots and block bumps (GDD §2.8, §2.10)
#include "game.h"
#include <string.h>
#include "level1_1.h"

void act_move(uint8_t i);
void act_spawn(uint8_t i, uint8_t type, uint16_t x, uint8_t y);
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
#define STOP_GRACE    16                      // frames a stopped ball ignores contact
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

// Kicked ball kills: 500 800 1000 2000 4000 5000 8000, then 1UP (GDD §2.10)
static const uint8_t ball_pts[7][3] = {
    {0x00,0x05,0}, {0x00,0x08,0}, {0x00,0x10,0}, {0x00,0x20,0}, {0x00,0x40,0}, {0x00,0x50,0}, {0x00,0x80,0} };

static void award_ball(uint8_t *chain) {
    if (*chain < 7) { add_score(ball_pts[*chain]); (*chain)++; }
    else add_life();
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
// half of them per frame). The game uses the asm walk_on_map in vram.s (~1300 T);
// this C version (~3700 T) is the reference for the equivalence test.
void walk_on_map(uint8_t i, uint8_t dbl);

void walk_on_map_c(uint8_t i, uint8_t dbl) {
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

// ---------------------------------------------------------------- interactions in 8-bit space
// Once per frame every enemy, Teo and the shots get a camera-relative x (+REL so -32..223 fits
// a u8). Collisions and drawing then use 8-bit math: the 16-bit compares against camera_x and
// player_x for every enemy and every pair cost ~7000 T per enemy (QA measurement, M1).
#define REL 32
uint8_t enemy_rx[ENEMY_COUNT];
uint8_t pl_l, pl_r, pl_t, pl_b, pl_c;   // Teo's hitbox: left, right (excl), top, bottom (excl), centre
uint8_t shot_rx[2];

void kick(uint8_t i) {
    uint8_t k = i - A_ENEMY0, c = enemy_rx[k] + 8;
    uint8_t left = c < pl_c || (c == pl_c && player_facing);
    act_state[i] = E_BALL_MOVE;
    act_vx[i] = left ? -BALL_SPEED : BALL_SPEED;
    enemy_grace[k] = KICK_GRACE;
    enemy_chain[k] = 0;
    add_score(PTS_400);
    sfx(SFX_KICK);
}

// Player contact: stomp from above or damage (GDD 2.8 "Pisoton")
void touch_player(uint8_t i, uint8_t ht, uint8_t hh) {
    uint8_t k = i - A_ENEMY0;
    uint8_t stomp = player_vy > 0 && (uint8_t)(pl_b - 1) < (uint8_t)(act_y[i] + ht + (hh >> 1));
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
                enemy_wait[k] = BALL_WAIT + BALL_TREMBLE;
                enemy_grace[k] = STOP_GRACE;    // the same contact must not kick it
            }
        } else {
            player_hurt();
        }
        break;
    case E_BALL:
        if (enemy_grace[k]) break;              // just stopped/curled: ignore this contact
        if (stomp) player_bounce();
        kick(i);
        break;
    case E_BALL_MOVE:
        if (stomp) {
            sfx(SFX_STOMP);
            player_bounce();
            act_state[i] = E_BALL;
            act_vx[i] = 0;
            enemy_wait[k] = BALL_WAIT + BALL_TREMBLE;
            enemy_grace[k] = STOP_GRACE;
        } else if (!enemy_grace[k]) {
            player_hurt();
        }
        break;
    }
}

// Pairs (each once: m > k): walking enemies turn around, a moving ball kills the other one.
// 8-bit 12x12 boxes. Called on alternate frames (enemies move <= 0.5 px/f, the ball 3 px/f:
// 6 px between checks is still less than the 12 px boxes).
static uint8_t pair_active(uint8_t j) {
    uint8_t s = act_state[j];
    return act_type[j] != T_NONE && s != E_FLIP && s != E_SQUASH;
}

static void ball_kills(uint8_t ball, uint8_t victim) {
    act_state[victim] = E_FLIP;
    act_vy[victim] = FLIP_VY;
    award_ball(&enemy_chain[ball - A_ENEMY0]);
    sfx(SFX_KICK);
}

void enemy_vs_enemy(uint8_t k) {
    uint8_t i = A_ENEMY0 + k, j, m, si, sj;
    uint8_t rx = enemy_rx[k], y = act_y[i];
    for (m = k + 1, j = i + 1; m < ENEMY_COUNT; m++, j++) {
        if (!pair_active(j)) continue;
        // |d| < 12 on both axes: (d + 11) < 23 is symmetric ((d + 12) < 24 was not: -12 hit, +12 missed)
        if ((uint8_t)(enemy_rx[m] - rx + 11) >= 23) continue;
        if ((uint8_t)(act_y[j] - y + 11) >= 23) continue;
        si = act_state[i];
        sj = act_state[j];
        if (si == E_BALL_MOVE && sj != E_BALL_MOVE) ball_kills(i, j);
        else if (sj == E_BALL_MOVE && si != E_BALL_MOVE) ball_kills(j, i);
        else if (si == E_WALK && sj == E_WALK) {   // both turn around, away from each other
            if (rx < enemy_rx[m]) { act_vx[i] = -ENEMY_SPEED; act_vx[j] = ENEMY_SPEED; }
            else { act_vx[i] = ENEMY_SPEED; act_vx[j] = -ENEMY_SPEED; }
        }
        if (act_state[i] == E_FLIP) return;
    }
}

void shots_vs_enemy(uint8_t i, uint8_t ht, uint8_t hh) {
    uint8_t s, k = i - A_ENEMY0, l = enemy_rx[k] + 2, t = act_y[i] + ht;
    for (s = 0; s < 2; s++) {
        if (act_type[A_SHOT0 + s] != T_SHOT) continue;
        if ((uint8_t)(shot_rx[s] + 7) > l && (uint8_t)(shot_rx[s] + 1) < (uint8_t)(l + 12)
            && (uint8_t)(act_y[A_SHOT0 + s] + 7) > t
            && (uint8_t)(act_y[A_SHOT0 + s] + 1) < (uint8_t)(t + hh)) {
            act_type[A_SHOT0 + s] = T_PUF;
            act_timer[A_SHOT0 + s] = 8;
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
    uint8_t i, k, st, ht, hh, l, t, any_shot;
    if (player_on_ground) stomp_chain = 0;
    spawn_enemies();
    enemy_phase ^= 1;

    // Pass 1: physics, despawn, relative x
    for (k = 0, i = A_ENEMY0; k < ENEMY_COUNT; k++, i++) {
        if (act_type[i] == T_NONE) continue;
        act_flip[i]++;
        if (enemy_grace[k]) enemy_grace[k]--;
        switch (act_state[i]) {
        case E_SQUASH:
            if (--act_timer[i] == 0) { act_type[i] = T_NONE; continue; }
            break;
        case E_FLIP:                               // falls off the screen without collision
            act_vy[i] += ENEMY_GRAV;
            act_move(i);
            break;
        case E_BALL:
            if (--enemy_wait[k] == 0) {            // wakes up and walks towards Teo
                act_state[i] = E_WALK;
                act_vx[i] = player_x < act_x[i] ? -ENEMY_SPEED : ENEMY_SPEED;
            }
            if (((k ^ enemy_phase) & 1) == 0) walk_on_map(i, 1);
            break;
        case E_BALL_MOVE:                          // fast: full rate so it does not judder
            walk_on_map(i, 0);
            break;
        default:                                   // half rate (GDD budget, see walk_on_map)
            if (((k ^ enemy_phase) & 1) == 0) walk_on_map(i, 1);
        }
        // Enemies only exist from camera-32 to camera+200, so x - camera + REL always fits a u8
        if (act_x[i] + 32 < camera_x || act_x[i] > camera_x + 200 || act_y[i] >= PIT_Y + 16) {
            act_type[i] = T_NONE;
            continue;
        }
        enemy_rx[k] = (uint8_t)(act_x[i] - camera_x) + REL;
    }

    // Pass 2: interactions (8-bit)
    pl_l = (uint8_t)(player_x - camera_x) + (REL + HB_X);
    pl_r = pl_l + HB_W;
    pl_c = pl_l + (HB_W >> 1);
    pl_t = player_y + hb_y;
    pl_b = pl_t + hb_h;
    shot_rx[0] = (uint8_t)(act_x[A_SHOT0] - camera_x) + REL;
    shot_rx[1] = (uint8_t)(act_x[A_SHOT0 + 1] - camera_x) + REL;
    any_shot = act_type[A_SHOT0] == T_SHOT || act_type[A_SHOT0 + 1] == T_SHOT;
    for (k = 0, i = A_ENEMY0; k < ENEMY_COUNT; k++, i++) {
        if (act_type[i] == T_NONE) continue;
        st = act_state[i];
        if (st == E_FLIP || st == E_SQUASH) continue;
        if (act_type[i] == T_SHELL && st == E_WALK) { ht = 2; hh = 14; } else { ht = 4; hh = 12; }
        l = enemy_rx[k] + 2;
        t = act_y[i] + ht;
        if (l < pl_r && pl_l < (uint8_t)(l + 12) && t < pl_b && pl_t < (uint8_t)(t + hh))
            touch_player(i, ht, hh);
        if (act_type[i] == T_NONE || act_state[i] == E_FLIP) continue;
        if (any_shot) shots_vs_enemy(i, ht, hh);
        if (enemy_phase && pair_active(i)) enemy_vs_enemy(k);
    }
}

// Writes the two 8x16 sprites per enemy through one OAM pointer: oam16() takes 5 arguments and
// SDCC passes the 3rd+ on the stack (measured ~1400 T per enemy with the call).
void enemies_draw(void) {
    uint8_t i, k, rx, tile, t2, prop, f, type, st, y;
    OAM_item_t *o;
    memset(&shadow_OAM[4], 0, ENEMY_COUNT * 2 * sizeof(OAM_item_t));   // hide the whole range
    if (++enemy_rot == ENEMY_COUNT) enemy_rot = 0;
    o = &shadow_OAM[4 + (enemy_rot << 1)];         // rotating start slot: overflow flickers
    for (k = 0, i = A_ENEMY0; k < ENEMY_COUNT; k++, i++) {
        if (o == &shadow_OAM[4 + 2 * ENEMY_COUNT]) o = &shadow_OAM[4];
        type = act_type[i];
        rx = enemy_rx[k];
        if (type == T_NONE || rx < 16 || rx >= 192) { o += 2; continue; }   // off screen
        st = act_state[i];
        f = act_flip[i];
        prop = 0;
        if (type == T_WALKER) {
            tile = st == E_SQUASH ? SPR_LIMO_SQUASH : SPR_LIMO_WALK;
            if (st == E_WALK && (f & 8)) prop = S_FLIPX;
        } else if (st == E_WALK || st == E_FLIP) {
            tile = (f & 8) ? SPR_ARMADIN_WALK2 : SPR_ARMADIN_WALK1;
            if (act_vx[i] < 0) prop = S_FLIPX;
        } else {
            tile = SPR_ARMADIN_BALL;
            if (st == E_BALL && enemy_wait[k] < BALL_TREMBLE && (f & 4)) tile = SPR_ARMADIN_PEEK;
            if (st == E_BALL_MOVE && (f & 4)) prop = S_FLIPX;
        }
        if (st == E_FLIP) prop |= S_FLIPY;
        t2 = tile + 2;
        if (prop & S_FLIPX) { t2 = tile; tile += 2; }
        y = act_y[i];
        rx -= REL - 8;                             // OAM x = screen x + 8
        o->y = y; o->x = rx; o->tile = tile; o->prop = prop; o++;
        o->y = y; o->x = rx + 8; o->tile = t2; o->prop = prop; o++;
    }
}
