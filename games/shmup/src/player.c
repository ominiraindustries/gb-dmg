// GRIFO - player: 8-way movement, autofire with 3 weapon levels, bomb, death and respawn,
// collisions of shots and of the player's core (GDD 2.1-2.4, 2.7).
#include "game.h"

#define PLAYER_X0      80
#define PLAYER_Y0      136
#define PLAYER_XMIN    8
#define PLAYER_XMAX    152
#define PLAYER_YMIN    32
#define PLAYER_YMAX    144
#define SPEED_STRAIGHT 0x0180
#define SPEED_DIAG     0x0110
#define FIRE_RATE      8
#define BOMB_FRAMES    90
#define DYING_FRAMES   32
#define RESPAWN_FRAMES 20
#define INV_RESPAWN    120

uint8_t player_x, player_y, player_xs, player_ys, player_inv;
uint8_t power, bombs, lives, continues, extends;
uint8_t fire_cd, burst, bomb_timer, dead_timer, shake_timer;
int8_t tilt;

static const uint8_t score_10[3] = { 0x10, 0, 0 };

void player_reset(void) {
    player_x = PLAYER_X0; player_y = PLAYER_Y0; player_xs = player_ys = 0;
    player_inv = 0; tilt = 0; fire_cd = 0; burst = 0;
    bomb_timer = 0; dead_timer = 0; shake_timer = 0;
}

// Enter from below without control, invulnerable 120 f, enemies hold fire 60 f
void play_respawn(void) {
    play_sub = PS_RESPAWN;
    dead_timer = 0;
    player_x = PLAYER_X0; player_y = 176;
    player_inv = INV_RESPAWN;
    no_fire = 60;
}

// ---------------------------------------------------------------- movement and fire
static void move_axis(uint8_t *p, uint8_t *sub, uint16_t v, uint8_t neg, uint8_t lo, uint8_t hi) {
    uint16_t t = (uint16_t)*sub + (uint8_t)v;
    uint8_t d = (uint8_t)(v >> 8) + (uint8_t)(t >> 8);
    *sub = (uint8_t)t;
    if (neg) *p = (*p < lo + d) ? lo : *p - d;
    else *p = (*p + d > hi) ? hi : *p + d;
}

static void new_shot(uint8_t x, uint8_t y, int16_t vx, int16_t vy, uint8_t tile, uint8_t prop,
                     uint8_t kind) {
    uint8_t i = pool_alloc(P_SHOT, N_SHOT);
    pool_obj_t *o;
    if (i == 0xFF) return;                         // pool full: this part of the burst is lost
    o = &pool[i];
    o->t = 1; o->x = x; o->xs = 0; o->y = y; o->ys = 0; o->vx = vx; o->vy = vy;
    o->s = kind;                                    // 0 beam 1, 1 double beam, 2 side
    o->tile = tile; o->prop = prop;
}

static void fire_burst(void) {
    uint8_t x = player_x + 4, y = player_y - 12;
    burst++;
    new_shot(x, y, 0, -0x0500, power == 1 ? SPR_SHOT1 : SPR_SHOT2, 0, power == 1 ? 0 : 1);
    if (power == 3 && (burst & 1)) {                // side shots on alternate bursts
        new_shot(x - 6, y + 4, -0x0140, -0x04C0, SPR_SHOT_SIDE, S_FLIPX, 2);
        new_shot(x + 6, y + 4, 0x0140, -0x04C0, SPR_SHOT_SIDE, 0, 2);
    }
    sfx(SFX_SHOT);
}

static void bomb(void) {
    uint8_t i;
    pool_obj_t *o = &pool[P_BULLET];
    for (i = 0; i < N_BULLET; i++, o++)            // +10 for every bullet erased
        if (o->t) { o->t = 0; add_score(score_10); }
    for (i = 0; i < N_ENEMY; i++)
        if (pool[P_ENEMY + i].t && pool[P_ENEMY + i].t < OBJ_EXPLO && pool[P_ENEMY + i].y >= 16)
            enemy_damage(P_ENEMY + i, 8);
    for (i = 0; i < N_TURRET; i++) {
        o = &pool[P_TURRET + i];
        if (o->t && o->y >= 16 && o->y < 160) turret_damage(P_TURRET + i, 8);
    }
    boss_damage(8);
    if (!(cheat_flags & CHEAT_BOMBS)) bombs--;
    bomb_timer = BOMB_FRAMES;
    player_inv = BOMB_FRAMES;
    no_fire = BOMB_FRAMES;
    shake_timer = 16;
    set_fade(1);
    sfx(SFX_BOMB);
}

void player_update(void) {
    uint8_t k = keys, dx = k & (J_LEFT | J_RIGHT), dy = k & (J_UP | J_DOWN);
    uint16_t v = (dx && dy) ? SPEED_DIAG : SPEED_STRAIGHT;

    if (shake_timer) {                              // SCY +-2 every 2 f (bomb 16 f, death 12 f)
        shake_timer--;
        shake_y = shake_timer ? ((shake_timer & 2) ? 2 : -2) : 0;
    }
    if (bomb_timer) {
        if (bomb_timer == BOMB_FRAMES - 4) set_fade(0);
        bomb_timer--;
    }
    if (play_sub == PS_DYING) {
        if (++dead_timer == DYING_FRAMES) {
            if (power > 1) power--;
            if (bombs < 2) bombs = 2;
            if (!lives) { continue_start(); return; }   // CONTINUAR screen (GDD 2.4)
            play_respawn();
        }
        return;
    }
    if (play_sub == PS_OUTRO) return;               // the boss outro flies the player away
    if (play_sub == PS_RESPAWN) {                   // enter from below, no control
        player_y -= 2;
        if (player_y <= PLAYER_Y0) { player_y = PLAYER_Y0; play_sub = PS_NORMAL; }
        if (player_inv) player_inv--;
        return;
    }
    if (dx == J_LEFT) move_axis(&player_x, &player_xs, v, 1, PLAYER_XMIN, PLAYER_XMAX);
    if (dx == J_RIGHT) move_axis(&player_x, &player_xs, v, 0, PLAYER_XMIN, PLAYER_XMAX);
    if (dy == J_UP) move_axis(&player_y, &player_ys, v, 1, PLAYER_YMIN, PLAYER_YMAX);
    if (dy == J_DOWN) move_axis(&player_y, &player_ys, v, 0, PLAYER_YMIN, PLAYER_YMAX);
    // banked frame after 6 f pressing, back to normal 6 f after release (visual only)
    if (dx == J_LEFT) { if (tilt > -12) tilt--; }
    else if (dx == J_RIGHT) { if (tilt < 12) tilt++; }
    else if (tilt > 0) tilt--;
    else if (tilt < 0) tilt++;

    if (fire_cd) fire_cd--;
    if ((keys & J_A) && !fire_cd) { fire_burst(); fire_cd = FIRE_RATE; }
    if ((pressed & J_B) && !bomb_timer && (bombs || (cheat_flags & CHEAT_BOMBS))) bomb();
    if (player_inv) player_inv--;
}

// ---------------------------------------------------------------- collisions
static void kill_player(void) {
    uint8_t i;
    for (i = 0; i < N_BULLET; i++) pool[P_BULLET + i].t = 0;   // no points (GDD 2.4)
    play_sub = PS_DYING;
    dead_timer = 0;
    shake_timer = 12;
    lives--;
    died_in_stage = 1;
    sfx(SFX_DEATH);
}

// First live (not exploding) enemy of [i, P_ENEMY + N_ENEMY) overlapping the query box
uint8_t hit_enemy(uint8_t i) {
    uint8_t e;
    while (i < P_ENEMY + N_ENEMY) {
        e = hit_first(i, P_ENEMY + N_ENEMY - i);
        if (e == 0xFF || pool[e].t < OBJ_EXPLO) return e;
        i = e + 1;
    }
    return 0xFF;
}

void collect_item(void) {
    pool_obj_t *o = &pool[P_ITEM];
    uint8_t d;
    if (!o->t) return;
    d = o->x - player_x;
    if (!GBE_WITHIN(d, 12)) return;
    d = o->y - player_y;
    if (!GBE_WITHIN(d, 12)) return;
    if (o->t == OBJ_ITEM_P) {
        if (power < 3) { power++; sfx(SFX_POWER); } else { add_score(score_1000); sfx(SFX_ITEM); }
    } else {
        if (bombs < 4) bombs++; else add_score(score_1000);
        sfx(SFX_ITEM);
    }
    o->t = 0;
}

// Shots vs enemies and turrets every 2nd frame per shot (a 5 px/f shot cannot skip a 14 px box
// in 2 frames); the player's core vs bullets and enemy bodies every frame.
// Boxes favour the player: shots hit 14x14 enemies, the core is hit by 12x12 bodies (GDD 2.6
// has 12 or 14 per type).
void player_collide(void) {
    uint8_t s, e, dmg;
    pool_obj_t *o;
    {
        uint8_t turrets = pool[P_TURRET].t | pool[P_TURRET + 1].t | pool[P_TURRET + 2].t |
                          pool[P_TURRET + 3].t;
        hit_ox = 1; hit_oy = 1; hit_ow = 14; hit_oh = 14;    // enemies and turrets: 14x14
        // half of the shots each frame: every shot is checked every 2nd frame, and the cost
        // is the same every frame (all 8 on one frame was a 12k T peak)
        o = &pool[P_SHOT + ((frame & 1) << 2)];
        for (s = 0; s < N_SHOT / 2; s++, o++) {
            if (!o->t) continue;
            if (o->s == 1) { hit_qx = o->x; hit_qw = 8; dmg = 2; }
            else { hit_qx = o->x + 2; hit_qw = 4; dmg = power == 1 || o->s == 2 ? 1 : 2; }
            hit_qy = o->y + 2; hit_qh = o->s == 2 ? 8 : 12;
            if ((e = hit_enemy(P_ENEMY)) != 0xFF) { o->t = 0; enemy_damage(e, dmg); continue; }
            if (boss_overlaps(hit_qx, hit_qy, hit_qw, hit_qh)) { o->t = 0; boss_damage(dmg); continue; }
            if (turrets && (e = hit_first(P_TURRET, N_TURRET)) != 0xFF) { o->t = 0; turret_damage(e, dmg); }
        }
    }
    collect_item();
    if (play_sub != PS_NORMAL || player_inv || (cheat_flags & CHEAT_INVINCIBLE)) return;
    hit_qx = player_x + 6; hit_qy = player_y + 6; hit_qw = 4; hit_qh = 4;    // 4x4 core
    hit_ox = 2; hit_oy = 2; hit_ow = 4; hit_oh = 4;                          // bullet 4x4
    if (hit_first(P_BULLET, N_BULLET) != 0xFF) { kill_player(); return; }
    hit_ox = 2; hit_oy = 2; hit_ow = 12; hit_oh = 12;
    if (hit_enemy(P_ENEMY) != 0xFF || boss_overlaps(player_x + 6, player_y + 6, 4, 4)) kill_player();
}

void player_sprites(void) {
    uint8_t t = SPR_PLAYER;
    if (play_sub == PS_DYING) {
        t = dead_timer < 11 ? SPR_PEXPLO_0 : dead_timer < 22 ? SPR_PEXPLO_1 : SPR_PEXPLO_2;
    } else {
        if (tilt < -6) t = SPR_PLAYER_BANK_L;
        else if (tilt > 6) t = SPR_PLAYER_BANK_R;
        if (player_inv && bomb_timer == 0 && (player_inv & 4)) {   // blink after respawn only
            shadow_OAM[OAM_PLAYER].y = shadow_OAM[OAM_PLAYER + 1].y = 0;
            return;
        }
    }
    oam16(OAM_PLAYER, player_x, player_y, t, 0);
}
