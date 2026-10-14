// GRIFO - level objects: wave script -> formations -> flying enemies (GDD 2.6), ground turrets in
// the BG (GDD 2.8), items (GDD 2.7). Flying things live in pool records:
//   t type, x/y OAM, s state flags, tm age (frames), aux x0 (route origin), aux2 hp, pad flash.
#include "game.h"
#include "stage1.h"

#define SPAWN_Y      0          // OAM Y: screen -16, under the HUD (GDD 2.0)
#define NO_FIRE_DY   32         // never fire from closer than 32 px above the player (GDD 2.6)
#define FORMATIONS   4

// amplitude 24 px, period 128 f (GDD 2.6 WAVE); CARRIER and items scale it
static const int8_t wave_ofs[128] = {
    0, 1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 19, 20, 21, 21, 22, 22, 23,
    23, 23, 24, 24, 24, 24, 24, 24, 24, 24, 24, 23, 23, 23, 22, 22, 21, 21, 20, 19, 19, 18, 17, 16,
    15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 2, 1, 0, -1, -2, -4, -5, -6, -7, -8, -9, -10, -11, -12,
    -13, -14, -15, -16, -17, -18, -19, -19, -20, -21, -21, -22, -22, -23, -23, -23, -24, -24, -24,
    -24, -24, -24, -24, -24, -24, -23, -23, -23, -22, -22, -21, -21, -20, -19, -19, -18, -17, -16,
    -15, -14, -13, -12, -11, -10, -9, -8, -7, -6, -5, -4, -2, -1,
};

// per enemy type (index OBJ_*): hp, base tile, score (BCD, 3 bytes little-endian)
static const uint8_t en_hp[] = { 0, 1, 1, 1, 4, 4, 10, 10 };
static const uint8_t en_tile[] = { 0, SPR_DART_0, SPR_WAVE_0, SPR_WAVE_0, SPR_SWOOP_0, SPR_SWOOP_0,
                                   SPR_CARRIER_0, SPR_CARRIER_0 };
static const uint8_t en_score[][3] = {
    { 0, 0, 0 }, { 0x00, 0x01, 0 }, { 0x50, 0x01, 0 }, { 0x50, 0x01, 0 },
    { 0x00, 0x04, 0 }, { 0x00, 0x04, 0 }, { 0x00, 0x08, 0 }, { 0x00, 0x08, 0 },
};
static const uint8_t score_turret[3] = { 0x00, 0x05, 0 };
const uint8_t score_1000[3] = { 0x00, 0x10, 0 };

uint8_t obj_ptr, no_fire;
uint8_t fm_type[FORMATIONS], fm_x[FORMATIONS], fm_left[FORMATIONS], fm_timer[FORMATIONS];
static uint8_t swoop_row, swoop_delay;

// ---------------------------------------------------------------- firing helpers
// Direction from (x, y) to the player, both top-left OAM of 16x16 boxes. Halved coordinates fit
// 8 bits (OAM differences reach +-167); 1 px of aim error is invisible. int16 version: ~1300 T.
uint8_t aim_at(uint8_t x, uint8_t y) {
    return aim_dir((int8_t)((player_x >> 1) - (x >> 1)), (int8_t)((player_y >> 1) - (y >> 1)));
}

static uint8_t may_fire(uint8_t y) {
    if (no_fire || play_sub >= PS_DYING && play_sub <= PS_RESPAWN) return 0;
    return (uint8_t)(player_y - y) >= NO_FIRE_DY && player_y > y;
}

void bullets_setup(uint8_t tile) {
    fire_first = P_BULLET; fire_n = N_BULLET; fire_t = 1; fire_tile = tile; fire_prop = 0;
}

// ---------------------------------------------------------------- spawning
static void spawn_enemy(uint8_t type, uint8_t x) {
    uint8_t i = pool_alloc(P_ENEMY, N_ENEMY);
    pool_obj_t *o;
    if (i == 0xFF) return;
    o = &pool[i];
    o->t = type; o->x = x; o->xs = 0; o->y = SPAWN_Y; o->ys = 0;
    o->vx = 0; o->vy = 0x0180;
    o->s = 0; o->tm = 0; o->aux = x; o->aux2 = en_hp[type]; o->pad = 0;
    o->tile = en_tile[type]; o->prop = 0;
    if (type == OBJ_WAVE || type == OBJ_WAVE_F || type == OBJ_CARRIER_P || type == OBJ_CARRIER_B)
        o->vy = 0x00C0;
    if ((type == OBJ_WAVE || type == OBJ_WAVE_F) && x >= 5 * 16 + 8) o->s = 1;   // mirrored sine
    if (type == OBJ_SWOOP || type == OBJ_SWOOP_G) o->s = swoop_delay;          // fire delay (f)
}

static void spawn_turret(uint8_t col, uint8_t row) {
    uint8_t i = pool_alloc(P_TURRET, N_TURRET);
    pool_obj_t *o;
    if (i == 0xFF) return;
    o = &pool[i];
    o->t = 1; o->x = (col << 4) + 8; o->y = VMAP_ROW_Y(row);
    o->s = MT_TURRET_D; o->tm = 40; o->aux = col; o->aux2 = 6; o->pad = row;
}

static void start_formation(uint8_t type, uint8_t col) {
    uint8_t f, n = 1, real = type;
    if (type == OBJ_DART) n = 3;
    else if (type == OBJ_WAVE || type == OBJ_WAVE_F) n = 4;
    for (f = 0; f < FORMATIONS; f++) {
        if (fm_left[f]) continue;
        fm_type[f] = real; fm_x[f] = (col << 4) + 8; fm_left[f] = n; fm_timer[f] = 0;
        return;
    }
}

// Level objects whose row reached the screen top (turrets: as soon as their row is drawn),
// then formations: at most one enemy appears per frame.
void objects_update(void) {
    uint8_t f, spawned = 0, type, row;
    if (obj_ptr < STAGE1_OBJ_COUNT) {               // one level object per frame (spreads the cost)
        row = stage1_obj_row[obj_ptr];
        type = stage1_obj_type[obj_ptr];
        if (type == OBJ_TURRET) {
            if (row < vmap_mrows) { spawn_turret(stage1_obj_col[obj_ptr], row); obj_ptr++; }
        } else if (((uint16_t)row << 4) <= scroll_y + 144) {
            if (type == OBJ_SWOOP || type == OBJ_SWOOP_G) {
                swoop_delay = (row == swoop_row) ? 12 : 0;   // pairs fire 12 f apart (GDD 2.6)
                swoop_row = row;
            }
            start_formation(type, stage1_obj_col[obj_ptr]);
            obj_ptr++;
            return;                                 // formations start spawning next frame
        }
    }
    for (f = 0; f < FORMATIONS; f++) {
        if (!fm_left[f]) continue;
        if (fm_timer[f]) { fm_timer[f]--; continue; }
        if (spawned) continue;
        spawn_enemy(fm_type[f], fm_x[f]);
        spawned = 1;
        fm_left[f]--;
        fm_timer[f] = fm_type[f] == OBJ_DART ? 13 : 16;
    }
}

void enemies_reset(void) {
    uint8_t f;
    obj_ptr = 0; no_fire = 0; swoop_row = 0xFF;
    for (f = 0; f < FORMATIONS; f++) fm_left[f] = 0;
}

// ---------------------------------------------------------------- per frame
static void explode(pool_obj_t *o) {
    o->t = OBJ_EXPLO; o->tm = 0; o->vx = o->vy = 0; o->tile = SPR_EXPLO_0; o->prop = 0;
}

static void spawn_item(uint8_t type, uint8_t x, uint8_t y) {
    pool_obj_t *o = &pool[P_ITEM];                  // one item at a time: replaces the old one
    o->t = type; o->x = x; o->xs = 0; o->y = y; o->ys = 0; o->vx = 0; o->vy = 0x0080;
    o->tm = 0; o->aux = x; o->tile = type == OBJ_ITEM_P ? SPR_ITEM_P : SPR_ITEM_B; o->prop = 0;
}

void enemy_damage(uint8_t i, uint8_t dmg) {
    pool_obj_t *o = &pool[i];
    if (o->t >= OBJ_EXPLO) return;
    o->pad = 1;                                     // flash with OBP1 ~2 f (GDD 2.6)
    if (o->aux2 > dmg) { o->aux2 -= dmg; sfx(SFX_HIT); return; }
    add_score(en_score[o->t]);
    if (o->t == OBJ_CARRIER_P || o->t == OBJ_CARRIER_B)
        spawn_item(o->t == OBJ_CARRIER_P ? OBJ_ITEM_P : OBJ_ITEM_B, o->x, o->y);
    explode(o);
    sfx(SFX_BOOM);
}

// SWOOP state in s: 0x80 stopped, 0x40 leaving, 0x20 / 0x10 fan 1 / 2 fired, low nibble = pair
// delay (0 or 12 f). Runs on think frames (every 2nd frame): conditions use >=, not ==.
static void swoop(pool_obj_t *o) {
    uint8_t s = o->s, t;
    if (!(s & 0x80)) {                              // diving
        if (o->y >= 56) { o->s = s | 0x80; o->vy = 0; o->tm = 0; }
        return;
    }
    if (o->tm >= 40 && !(s & 0x40)) {               // leave toward the nearest edge, climbing
        s |= 0x40;
        o->vx = o->x < 80 ? -0x0100 : 0x0100;
        o->vy = -0x0100;
    }
    t = o->tm - (s & 0x0F);
    if (t < 0x80 && t >= 20 && !(s & 0x20)) {
        s |= 0x20;
        if (may_fire(o->y)) {
            bullets_setup(SPR_EBULLET);
            fire_fan(o->x + 4, o->y + 4, aim_at(o->x, o->y), 3, 2, 1);
        }
    } else if (o->t == OBJ_SWOOP_G && t < 0x80 && t >= 36 && !(s & 0x10)) {
        s |= 0x10;
        if (may_fire(o->y)) {
            bullets_setup(SPR_EBULLET);
            fire_fan(o->x + 4, o->y + 4, aim_at(o->x, o->y), 3, 2, 2);
        }
    }
    o->s = s;
}

static uint8_t anim;

// Think (alternate frames, GDD 2.6): animation, flash, steering, state changes, firing
void enemy_think(pool_obj_t *o) {
    uint8_t t = o->t;
    if (o->pad) o->pad--;
    o->prop = o->pad ? S_PALETTE : 0;
    o->tile = en_tile[t] + anim;
    if (t == OBJ_DART) {                            // drift 0.25 px/f toward the player below y 32
        if (o->y >= 48) {
            uint8_t d = player_x - o->x;
            o->vx = GBE_WITHIN(d, 9) ? 0 : (d & 0x80) ? -0x0040 : 0x0040;
        }
    } else if (t == OBJ_SWOOP || t == OBJ_SWOOP_G) {
        swoop(o);
    } else if (t == OBJ_WAVE_F && o->tm >= 48 && !(o->s & 0x40)) {
        o->s |= 0x40;
        if (may_fire(o->y)) {
            bullets_setup(SPR_EBULLET);
            fire(o->x + 4, o->y + 4, aim_at(o->x, o->y), 0);
        }
    }
}

// Every frame: age, explosion frames, route x (WAVE / CARRIER from tables). Returns 1 if the
// enemy is alive and not exploding.
uint8_t enemy_frame(pool_obj_t *o) {
    uint8_t t = o->t, tm = ++o->tm;
    if (t == OBJ_EXPLO) {                           // 2 frames of 8 f, then free
        if (tm == 8) o->tile = SPR_EXPLO_1;
        else if (tm == 16) o->t = 0;
        return 0;
    }
    if (t == OBJ_WAVE || t == OBJ_WAVE_F) {
        tm &= 127;
        o->x = (o->s & 1) ? o->aux - wave_ofs[tm] : o->aux + wave_ofs[tm];
    } else if (t >= OBJ_CARRIER_P) {                // CARRIER: slow sway +-6 px
        o->x = o->aux + (wave_ofs[(tm >> 1) & 127] >> 2);
    }
    return 1;
}

// Small per-enemy functions on purpose: in one big loop SDCC kept the record pointer on the
// stack and paid ~10 instructions per field access (~1500 T per enemy, measured).
void enemies_update(void) {
    uint8_t i;
    pool_obj_t *o = &pool[P_ENEMY];
    anim = ((frame >> 3) & 1) << 2;
    for (i = 0; i < N_ENEMY; i++, o++) {
        if (o->t && enemy_frame(o) && !((i ^ frame) & 1)) enemy_think(o);
    }
}

// Turrets: Y follows the scroll (computed, not accumulated: GDD 9.4), aim and fire while in
// screen y 16..96, turn the metatile toward the player at most every 16 f, free below the screen.
void turrets_update(void) {
    uint8_t i, y, d, mt;
    pool_obj_t *o = &pool[P_TURRET];
    for (i = 0; i < N_TURRET; i++, o++) {
        if (!o->t) continue;
        y = o->y = VMAP_ROW_Y(o->pad);
        if (y >= 160 && y < 208) { o->t = 0; continue; }     // left the screen at the bottom
        if (y < 32 || y > 112) continue;                     // fires only from screen y 16..96
        if (((frame + (i << 2)) & 15) == 0) {
            d = aim_at(o->x, y);
            mt = (d >= 4 && d <= 11) ? MT_TURRET_L : (d >= 21 && d <= 28) ? MT_TURRET_R : MT_TURRET_D;
            if (mt != o->s) { o->s = mt; vmap_set(o->aux, o->pad, mt); }
        }
        if (--o->tm) continue;
        o->tm = 96;
        if (may_fire(y)) {
            bullets_setup(SPR_EBULLET);
            fire(o->x + 4, y + 4, aim_at(o->x, y), o->pad < 81 ? 0 : 1);
        }
    }
}

void turret_damage(uint8_t i, uint8_t dmg) {
    pool_obj_t *o = &pool[i], *e;
    uint8_t k;
    if (o->aux2 > dmg) { o->aux2 -= dmg; sfx(SFX_HIT); return; }
    o->t = 0;
    vmap_set(o->aux, o->pad, MT_CRATER);
    add_score(score_turret);
    sfx(SFX_BIG_BOOM);
    if ((k = pool_alloc(P_EXPLO, N_EXPLO)) != 0xFF) {
        e = &pool[k];
        e->t = OBJ_EXPLO_SCROLL; e->x = o->x; e->y = o->y; e->xs = e->ys = 0; e->vx = e->vy = 0;
        e->tm = 0; e->pad = o->pad; e->tile = SPR_EXPLO_0; e->prop = 0;   // stays on its map row
    }
}

// Extra explosions (turrets, boss) and the item
void effects_update(void) {
    uint8_t i;
    pool_obj_t *o = &pool[P_EXPLO];
    for (i = 0; i < N_EXPLO; i++, o++) {
        if (!o->t) continue;
        o->tm++;
        if (o->tm == 8) o->tile = SPR_EXPLO_1;
        if (o->tm == 16) o->t = 0;
        else if (o->t == OBJ_EXPLO_SCROLL) o->y = VMAP_ROW_Y(o->pad);
    }
    o = &pool[P_ITEM];
    if (o->t) {                                     // sway +-7 px, period 64 f; blink OBP0/OBP1
        int8_t w = wave_ofs[(o->tm << 1) & 127];
        o->tm++;
        o->x = o->aux + (w >> 2) + (w >> 4);
        o->prop = (o->tm & 8) ? S_PALETTE : 0;
    }
}
