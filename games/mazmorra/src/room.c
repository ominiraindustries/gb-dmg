// MADRIGUERA - rooms (GDD 2.1, 2.2, 2.6): the camera sits on a 10x8-cell room of the single world map
// and slides RULE SCROLL_SPEED px/f to the next one; the new room's enemies (map 'enemy' objects) are
// created 1 per frame during the slide; enemies (gbe_gact, cell by cell) with hit points, flash,
// knockback, the "puf" and the heart they drop. Collisions in 8-bit screen coordinates.
#include "game.h"
#include "enemies.h"
#include "fx.h"
#include "items.h"

enum { OBJ_ENEMY, OBJ_START };                  // game.json world_objects order

uint8_t room_c, room_r, sliding;
int16_t cam_tx, cam_ty, cam_wx, cam_wy;         // camera target / camera asked this frame (world px)
uint8_t en_hp[GBE_GACT_MAX], en_inv[GBE_GACT_MAX], en_kind[GBE_GACT_MAX], en_knock[GBE_GACT_MAX], en_alive;
uint8_t hitstop;
uint8_t cont_c, cont_r, cont_dir;                 // where FIN 'Continuar' puts Tilo back (room entry)
uint16_t cont_x, cont_y;
uint16_t pk_t[PICKUP_MAX];                      // hearts on the floor: frames left, screen px
uint8_t pk_x[PICKUP_MAX], pk_y[PICKUP_MAX];
uint8_t fx_t, fx_x, fx_y;
static uint8_t slide_dir, slide_walk, sp_n, sp_x[4], sp_y[4], sp_k[4];

static const uint8_t en_tile[3] = { ENEMIES_BABOSA_A, ENEMIES_BABOSA_A, ENEMIES_BABOSA_A };   // M2: the others

// gbe_gact: enemies walk only on floor cells inside the current room (never doors or walls)
uint8_t gact_terrain_ok(uint8_t i, uint8_t x, uint8_t y) {
    uint8_t x0 = room_c * ROOM_W, y0 = room_r * ROOM_H;
    (void)i;
    if ((uint8_t)(x - x0 - 1) >= ROOM_W - 2 || (uint8_t)(y - y0 - 1) >= ROOM_H - 2) return 0;
    return !(wattr_at(x, y) & ATTR_SOLID);
}

static void room_target(uint8_t c, uint8_t r) {
    cam_tx = (int16_t)c * (ROOM_W * 16);
    cam_ty = (int16_t)r * (ROOM_H * 16) - 16;   // room row 0 at screen line 16, under the HUD
}

// the room's enemy objects (its rect touches 1-2 sectors) -> the spawn list
static void collect(uint8_t c, uint8_t r) {
    uint8_t x0 = c * ROOM_W, y0 = r * ROOM_H, sx, k, n;
    world_ev_t *e;
    sp_n = 0;
    for (sx = x0 >> 4; sx <= (uint8_t)((x0 + ROOM_W - 1) >> 4); sx++) {
        n = world_events(sx, y0 >> 4);
        for (k = 0, e = wev; k < n; k++, e++) {
            if (e->type != OBJ_ENEMY || sp_n == 4) continue;
            if ((uint8_t)(e->x - x0) >= ROOM_W || (uint8_t)(e->y - y0) >= ROOM_H) continue;
            sp_x[sp_n] = e->x; sp_y[sp_n] = e->y; sp_k[sp_n] = e->d[0];
            sp_n++;
        }
    }
}

static void spawn_one(void) {
    uint8_t i, k;
    sp_n--;
    k = sp_k[sp_n];
    i = gact_spawn((k + 1) | GACT_ANIM2, sp_x[sp_n], sp_y[sp_n], SPR_ENEMIES + en_tile[k], GACT_WANDER);
    if (i == 0xFF) return;
    gact_speed(i, en_rows[k].fpc);
    en_hp[i] = en_rows[k].hp;
    en_kind[i] = k;
    en_inv[i] = en_knock[i] = 0;
    en_alive++;
}

static void clear_room(void) {
    uint8_t i;
    for (i = 0; i < GBE_GACT_MAX; i++) gact_free(i);
    en_alive = 0;
    memset(pk_t, 0, sizeof(pk_t));
    fx_t = 0;
}

void room_enter_now(uint8_t c, uint8_t r) {
    room_c = c; room_r = r;
    clear_room();
    room_target(c, r);
    cam_wx = cam_tx; cam_wy = cam_ty;
    collect(c, r);
    while (sp_n) spawn_one();
    sliding = 0;
}

void room_slide(uint8_t dir) {
    if (dir == DIR_LEFT) room_c--;
    else if (dir == DIR_RIGHT) room_c++;
    else if (dir == DIR_UP) room_r--;
    else room_r++;
    clear_room();                               // the old room's objects go at once (cheap)
    collect(room_c, room_r);
    room_target(room_c, room_r);
    slide_dir = dir;
    slide_walk = R8(RULE_SCROLL_WALK);
    sliding = 1;
    sword_t = sword_buf = knock_t = 0;
}

static int16_t approach(int16_t v, int16_t to, uint8_t step) {
    if (v < to) return v + step > to ? to : v + step;
    if (v > to) return v - step < to ? to : v - step;
    return v;
}

// the logic is frozen; camera 4 px/f, Tilo 1 px/f for 32 f, 1 enemy of the new room per frame
void room_slide_update(void) {
    cam_wx = approach(cam_wx, cam_tx, R8(RULE_SCROLL_SPEED));
    cam_wy = approach(cam_wy, cam_ty, R8(RULE_SCROLL_SPEED));
    if (slide_walk) { slide_walk--; link_slide_step(slide_dir); }
    if (sp_n) spawn_one();
    if (cam_wx == cam_tx && cam_wy == cam_ty && !slide_walk && !sp_n) {
        sliding = 0;
        cont_c = room_c; cont_r = room_r; cont_x = lx; cont_y = ly; cont_dir = ldir;   // continue point
    }
}

static uint8_t en_sx(uint8_t i) { return (uint8_t)(gact_wx(i) - cam_x); }
static uint8_t en_sy(uint8_t i) { return (uint8_t)(gact_wy(i) - cam_y); }

// boxes [a, a + aw) and [b, b + bw) overlap, in 8-bit screen space (CLAUDE.md symmetric test)
#define OVER(a, aw, b, bw) ((uint8_t)((uint8_t)((b) - (a)) + (bw) - 1) < (uint8_t)((aw) + (bw) - 1))

static void kill(uint8_t i) {
    uint8_t x = en_sx(i), y = en_sy(i), k, n = en_rows[en_kind[i]].heart;
    gact_free(i);
    en_alive--;
    fx_t = 16; fx_x = x; fx_y = y;
    sfx(SFX_KILL);
    if (n && !rng_range(n))
        for (k = 0; k < PICKUP_MAX; k++)
            if (!pk_t[k]) { pk_t[k] = RULE(RULE_PICKUP_LIFE); pk_x[k] = x + 4; pk_y[k] = y; break; }
}

uint8_t sword_hits(uint8_t x0, uint8_t y0, uint8_t w, uint8_t h) {
    uint8_t i, n = 0, ex, ey;
    int8_t vx, vy;
    for (i = 0; i < GBE_GACT_MAX; i++) {
        if (!gact[i].type || en_inv[i]) continue;
        ex = en_sx(i) + 2; ey = en_sy(i) + 2;
        if (!OVER(x0, w, ex, 12) || !OVER(y0, h, ey, 12)) continue;
        n++;
        hitstop = R8(RULE_HITSTOP);
        if (!--en_hp[i]) { kill(i); continue; }
        en_inv[i] = R8(RULE_ENEMY_INVULN);
        sfx(SFX_HIT);
        vx = (int8_t)(ex + 6 - (LSX + 8));            // Tilo -> enemy: knocked one cell away
        vy = (int8_t)(ey + 6 - (LSY + 8));
        gact_speed(i, R8(RULE_ENEMY_KNOCK_FPC));
        gact[i].beh = GACT_STILL;
        en_knock[i] = 1;
        if ((vx < 0 ? -vx : vx) >= (vy < 0 ? -vy : vy)) gact_try_move(i, vx < 0 ? DIR_LEFT : DIR_RIGHT);
        else gact_try_move(i, vy < 0 ? DIR_UP : DIR_DOWN);
    }
    return n;
}

void enemies_touch_link(void) {
    uint8_t i, ex, ey, hx = LSX + 2, hy = LSY + 4;
    for (i = 0; i < GBE_GACT_MAX; i++) {
        if (!gact[i].type) continue;
        ex = en_sx(i) + 2; ey = en_sy(i) + 2;
        if (OVER(hx, 12, ex, 12) && OVER(hy, 12, ey, 12)) {
            link_hurt(en_rows[en_kind[i]].dmg, ex + 6, ey + 6);
            return;
        }
    }
}

void room_update(void) {
    uint8_t i;
    gact_t *g;
    if (!(cheat_flags & 2)) gact_update();
    for (i = 0, g = gact; i < GBE_GACT_MAX; i++, g++) {
        if (!g->type) continue;
        if (en_inv[i]) { en_inv[i]--; g->prop = (en_inv[i] & 2) ? S_PALETTE : 0; }   // flash: OBP1
        if (en_knock[i] && !g->moving) {
            en_knock[i] = 0;
            gact_speed(i, en_rows[en_kind[i]].fpc);
            g->beh = GACT_WANDER;
        }
    }
    enemies_touch_link();
    for (i = 0; i < PICKUP_MAX; i++) {
        if (!pk_t[i]) continue;
        pk_t[i]--;
        if (OVER(LSX + 2, 12, pk_x[i], 8) && OVER(LSY + 4, 12, pk_y[i] + 4, 8)) {
            pk_t[i] = 0;
            hp = hp + R8(RULE_HEART_HEAL) > hp_max ? hp_max : hp + R8(RULE_HEART_HEAL);
            sfx(SFX_HEART);
        }
    }
    if (fx_t) fx_t--;
}

void room_draw(void) {
    uint8_t i;
    gact_draw(OAM_ENEMIES);
    for (i = 0; i < PICKUP_MAX; i++) {
        if (pk_t[i] && (pk_t[i] > RULE(RULE_PICKUP_BLINK) || (pk_t[i] & 4)))
            oam8(OAM_PICKUPS + i, pk_x[i] + 8, pk_y[i] + 16, SPR_ITEMS + ITEMS_HEART, 0);
        else shadow_OAM[OAM_PICKUPS + i].y = 0;
    }
    if (fx_t) oam16(OAM_FX, fx_x + 8, fx_y + 16, SPR_FX + (fx_t > 8 ? FX_PUF_0 : FX_PUF_1), 0);
    else shadow_OAM[OAM_FX].y = shadow_OAM[OAM_FX + 1].y = 0;
}

// the map's 'start' object (the new game's cell)
uint8_t room_find_start(uint8_t *x, uint8_t *y) {
    uint8_t sx, sy, k, n;
    for (sy = 0; sy < wmap.h; sy++)
        for (sx = 0; sx < wmap.w; sx++) {
            n = world_events(sx, sy);
            for (k = 0; k < n; k++)
                if (wev[k].type == OBJ_START) { *x = wev[k].x; *y = wev[k].y; return 1; }
        }
    return 0;
}
