// gbe: grid actors for top-down games on gbe_world - NPCs and creatures that walk cell by cell.
//
// Records of 24 bytes (gact_t, offsets fixed in gbe_gact.s), GBE_GACT_MAX slots. An actor stands on
// (x, y); while moving it goes to (tx, ty) and step counts the pixels done (0-15) at a speed given
// in frames per cell (8.8 rate). Both cells are taken (gact_at), as are the player's cells
// (gact_px/py and gact_px2/py2, set by the game). Terrain is the game's: it implements
// gact_terrain_ok(i, x, y) (solid cells, water for swimmers...).
// Behaviours are generic and parameterised (STILL, LOOK, WANDER around home, CHASE / FLEE the
// player, HOME, FOLLOW a leader's trail); game logic (sight, alerts, emotes) changes beh.
// At most one actor thinks per frame (round robin; the rule of games/dungeon and the platformer).
// Moving, drawing and gact_at are asm (gbe_gact.s); their C references live in gbe_selftest.c
// (section GBE_SELFTEST_GACT), which can sit in a switchable bank. Measured in world_lab with 12 actors: C 51k T, asm see README.
#include <string.h>
#include "gbe.h"

#define N GBE_GACT_MAX

static const int8_t gdx[4] = { 0, 0, -1, 1 };     // 0 down, 1 up, 2 left, 3 right
static const int8_t gdy[4] = { 1, -1, 0, 0 };
const uint8_t gact_npc_frame[4] = { 0, 8, 16, 16 }; // NPC layout: down 0/4, up 8/12, side 16/20

gact_t gact[N];
const uint8_t gact_count = N;
uint8_t gact_px, gact_py, gact_px2, gact_py2;      // player cells (current, destination)
uint8_t gact_think_next;                           // round-robin cursor
uint8_t gact_prio_mask = 0x20;                     // wmt_attr bit that hides the sprite's feet
uint8_t gact_rng = 0x5A;

static uint8_t rnd(void) {
    gact_rng ^= gact_rng << 3; gact_rng ^= gact_rng >> 5; gact_rng ^= gact_rng << 1;
    return gact_rng;
}

// frames per cell -> 8.8 pixels per frame, rounded up (12 f: 342 * 12 >= 4096)
void gact_speed(uint8_t i, uint8_t frames) {
    uint16_t r = (4096u + frames - 1) / frames;     // once per spawn: the division is fine here
    gact[i].rate_hi = r >> 8;
    gact[i].rate_lo = (uint8_t)r;
}

uint8_t gact_spawn(uint8_t type, uint8_t x, uint8_t y, uint8_t tile, uint8_t beh) {
    uint8_t i;
    gact_t *a = gact;
    for (i = 0; i < N; i++, a++) {
        if (a->type) continue;
        memset(a, 0, sizeof(gact_t));
        a->type = type;
        a->x = a->tx = a->ox = a->hx = x;
        a->y = a->ty = a->oy = a->hy = y;
        a->tile = tile;
        a->prio = GACT_PRIO_DIRTY;
        a->beh = beh;
        a->radius = 4;
        a->leader = 0xFF;
        gact_speed(i, 16);
        return i;
    }
    return 0xFF;
}

void gact_free(uint8_t i) {
    gact[i].type = 0;
}

uint8_t gact_free_cell(uint8_t i, uint8_t x, uint8_t y) {
    if ((x == gact_px && y == gact_py) || (x == gact_px2 && y == gact_py2)) return 0;
    if (gact_at(x, y) != 0xFF) return 0;
    return gact_terrain_ok(i, x, y);
}

// Face dir and start a step if the cell is free. Returns 1 if it moves.
uint8_t gact_try_move(uint8_t i, uint8_t dir) {
    gact_t *a = &gact[i];
    uint8_t x = a->x + gdx[dir], y = a->y + gdy[dir];
    a->dir = dir;
    if (a->moving || !gact_free_cell(i, x, y)) { a->bumped = 1; return 0; }
    a->ox = a->x;
    a->oy = a->y;
    a->tx = x;
    a->ty = y;
    a->moving = 1;
    a->step = a->sub = 0;
    a->bumped = 0;
    return 1;
}

// Step on the axis that closes the larger distance to (x, y) (away: opens it), then the other one
uint8_t gact_step_toward(uint8_t i, uint8_t x, uint8_t y, uint8_t away) {
    int8_t dx = (int8_t)(x - gact[i].x), dy = (int8_t)(y - gact[i].y);
    uint8_t ax = dx < 0 ? -dx : dx, ay = dy < 0 ? -dy : dy, d1, d2, t;
    if (away) { dx = -dx; dy = -dy; }
    d1 = dx < 0 ? 2 : 3;                 // horizontal choice
    d2 = dy < 0 ? 1 : 0;                 // vertical choice
    if (ay > ax) { t = d1; d1 = d2; d2 = t; t = ax; ax = ay; ay = t; }
    if ((ax || away) && gact_try_move(i, d1)) return 1;
    if (ay || away) return gact_try_move(i, d2);
    return 0;
}

static void think(uint8_t i) {
    gact_t *a = &gact[i];
    uint8_t d, x, y;
    int8_t ex, ey;
    switch (a->beh) {
    case GACT_LOOK:
        a->dir = rnd() & 3;
        a->timer = 64 + (rnd() & 63);
        break;
    case GACT_WANDER:
        d = rnd() & 3;
        x = a->x + gdx[d];
        y = a->y + gdy[d];
        ex = (int8_t)(x - a->hx);
        ey = (int8_t)(y - a->hy);
        if (ex < 0) ex = -ex;
        if (ey < 0) ey = -ey;
        if ((uint8_t)ex <= a->radius && (uint8_t)ey <= a->radius) gact_try_move(i, d);
        else a->dir = d;
        a->timer = 48 + (rnd() & 47);
        break;
    case GACT_CHASE:
        gact_step_toward(i, gact_px, gact_py, 0);
        break;
    case GACT_FLEE:
        gact_step_toward(i, gact_px, gact_py, 1);
        break;
    case GACT_HOME:
        if (a->x == a->hx && a->y == a->hy) a->beh = GACT_WANDER;
        else gact_step_toward(i, a->hx, a->hy, 0);
        break;
    case GACT_FOLLOW:
        d = a->leader;
        if (d != 0xFF && gact[d].type) gact_step_toward(i, gact[d].ox, gact[d].oy, 0);
        break;
    }
}

// Once per frame: move every walking actor, count timers, and let one idle actor think
void gact_update(void) {
    uint8_t i, k;
    gact_move_all();
    for (k = 0; k < N; k++) {                       // one thinker per frame
        i = gact_think_next;
        if (++gact_think_next == N) gact_think_next = 0;
        if (gact[i].type && !gact[i].moving && !gact[i].timer && gact[i].beh != GACT_STILL) {
            think(i);
            break;
        }
    }
}

// Pixel position of an actor in world px (top-left of its 16x16)
int16_t gact_wx(uint8_t i) {
    gact_t *a = &gact[i];
    int16_t v = (int16_t)a->x << 4;
    if (a->moving) { if (a->dir == 2) v -= a->step; else if (a->dir == 3) v += a->step; }
    return v;
}

int16_t gact_wy(uint8_t i) {
    gact_t *a = &gact[i];
    int16_t v = (int16_t)a->y << 4;
    if (a->moving) { if (a->dir == 1) v -= a->step; else if (a->dir == 0) v += a->step; }
    return v;
}

