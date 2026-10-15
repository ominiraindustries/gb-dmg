// MADRIGUERA - Tilo (GDD 2.3-2.5): free movement at RULE LINK_SPEED (8.8) with wall probes on the
// feet box and corner sliding, the sword stab (A) with its buffer, damage, knockback, blinking
// invulnerability and death. Leaving the room through a doorway starts the room slide (room.c).
// Positions: world px (u16); screen coordinates are 8-bit inside the room (LSX, LSY).
#include "game.h"
#include "link.h"

uint16_t lx, ly;
uint8_t lxs, lys, ldir, lanim, lmoving, sword_t, sword_buf, knock_t, knock_dir, inv_t, hp, hp_max, dead_t;
uint16_t deaths;
static uint8_t anim_t, shake_t;

static const int8_t ddx[4] = { 0, 0, -1, 1 }, ddy[4] = { 1, -1, 0, 0 };

static uint8_t solid(uint16_t x, uint16_t y) {
    return wattr_at((uint8_t)(x >> 4), (uint8_t)(y >> 4)) & ATTR_SOLID;
}

// one pixel along an axis with the feet box (x+3..x+12, y+8..y+15) against walls; slide = nudge
// around a corner when only one of the two probes is blocked and the gap is <= RULE CORNER_SLIDE px
static uint8_t step_y(int8_t d, uint8_t slide);

static uint8_t step_x(int8_t d, uint8_t slide) {
    uint16_t ex = d > 0 ? lx + 13 : lx + 2;          // the column the feet would enter
    uint8_t top = solid(ex, ly + 8), bot = solid(ex, ly + 15);
    if (!top && !bot) { lx += d; return 1; }
    if (slide && top != bot) {
        uint8_t need = top ? 16 - ((ly + 8) & 15) : ((ly + 15) & 15) + 1;
        if (need <= R8(RULE_CORNER_SLIDE)) step_y(top ? 1 : -1, 0);
    }
    return 0;
}

static uint8_t step_y(int8_t d, uint8_t slide) {
    uint16_t ey = d > 0 ? ly + 16 : ly + 7;
    uint8_t lft = solid(lx + 3, ey), rgt = solid(lx + 12, ey);
    if (!lft && !rgt) { ly += d; return 1; }
    if (slide && lft != rgt) {
        uint8_t need = lft ? 16 - ((lx + 3) & 15) : ((lx + 12) & 15) + 1;
        if (need <= R8(RULE_CORNER_SLIDE)) step_x(lft ? 1 : -1, 0);
    }
    return 0;
}

void link_place(uint16_t x, uint16_t y, uint8_t dir) {
    lx = x; ly = y; ldir = dir;
    lxs = lys = 0;
    sword_t = sword_buf = knock_t = 0;
    lmoving = 0;
}

void link_slide_step(uint8_t dir) {
    lx += ddx[dir];
    ly += ddy[dir];
    lanim = (++anim_t >> 3) & 1;
}

void link_hurt(uint8_t dmg, uint8_t from_x, uint8_t from_y) {
    int8_t vx, vy;
    if (inv_t || dead_t || (cheat_flags & 1)) return;
    hp = hp > dmg ? hp - dmg : 0;
    vx = (int8_t)(LSX + 8 - from_x);                  // attacker -> Tilo, dominant axis
    vy = (int8_t)(LSY + 8 - from_y);
    if ((vx < 0 ? -vx : vx) >= (vy < 0 ? -vy : vy)) knock_dir = vx < 0 ? DIR_LEFT : DIR_RIGHT;
    else knock_dir = vy < 0 ? DIR_UP : DIR_DOWN;
    knock_t = R8(RULE_KNOCK_FRAMES);
    inv_t = R8(RULE_HURT_INVULN);
    sword_t = sword_buf = 0;
    shake_t = R8(RULE_SHAKE_FRAMES);
    sfx(SFX_HURT);
    if (!hp) { dead_t = R8(RULE_DEATH_FREEZE); deaths++; }
}

// facing: the last axis pressed; on a diagonal keep the facing if it is one of the two
static void face(int8_t dx, int8_t dy) {
    uint8_t h = dx < 0 ? DIR_LEFT : DIR_RIGHT, v = dy < 0 ? DIR_UP : DIR_DOWN;
    if (dx && dy) { if (ldir != h && ldir != v) ldir = h; }
    else if (dx) ldir = h;
    else if (dy) ldir = v;
}

static void sword_box(void) {
    uint8_t x = LSX, y = LSY;
    switch (ldir) {
    case DIR_RIGHT: sword_hits(x + 12, y + 6, 16, 8); break;
    case DIR_LEFT:  sword_hits(x - 12, y + 6, 16, 8); break;
    case DIR_UP:    sword_hits(x + 4, y - 12, 8, 16); break;
    default:        sword_hits(x + 4, y + 12, 8, 16); break;
    }
}

void link_update(void) {
    int8_t dx = 0, dy = 0;
    uint8_t n, cx, cy;
    uint16_t acc;
    if (inv_t) inv_t--;
    if (shake_t) { shake_t--; shake_x = !shake_t ? 0 : (shake_t & 1) ? 1 : -1; }   // +-1 px (gbe_video)
    if (dead_t) return;
    if (knock_t) {                                    // no control while knocked back; walls stop it
        knock_t--;
        for (n = R8(RULE_KNOCK_SPEED); n; n--) {
            if (knock_dir >= DIR_LEFT) step_x(ddx[knock_dir], 0); else step_y(ddy[knock_dir], 0);
        }
        return;
    }
    if (sword_t) {                                    // Tilo does not move during the stab
        if (sword_t >= R8(RULE_SWORD_BUFFER_FROM) && (pressed & J_A)) sword_buf = 1;
        if (sword_t >= R8(RULE_SWORD_ACTIVE_FROM) && sword_t <= R8(RULE_SWORD_ACTIVE_TO)) sword_box();
        if (++sword_t >= R8(RULE_SWORD_FRAMES)) {
            sword_t = 0;
            if (sword_buf) { sword_buf = 0; sword_t = 1; sfx(SFX_SWORD); }
        }
        return;
    }
    if (pressed & J_A) { sword_t = 1; sfx(SFX_SWORD); return; }
    if (keys & J_LEFT) dx = -1; else if (keys & J_RIGHT) dx = 1;
    if (keys & J_UP) dy = -1; else if (keys & J_DOWN) dy = 1;
    lmoving = dx || dy;
    if (!lmoving) return;
    face(dx, dy);
    if (++anim_t >= 8) { anim_t = 0; lanim ^= 1; }
    if (dx) {
        acc = lxs + RULE(RULE_LINK_SPEED);
        lxs = (uint8_t)acc;
        for (n = acc >> 8; n; n--) step_x(dx, !dy);
    }
    if (dy) {
        acc = lys + RULE(RULE_LINK_SPEED);
        lys = (uint8_t)acc;
        for (n = acc >> 8; n; n--) step_y(dy, !dx);
    }
    cx = (uint8_t)((lx + 8) >> 4);                   // feet centre out of the room: next room
    cy = (uint8_t)((ly + 12) >> 4);
    if (cx < room_c * ROOM_W) room_slide(DIR_LEFT);
    else if (cx >= room_c * ROOM_W + ROOM_W) room_slide(DIR_RIGHT);
    else if (cy < room_r * ROOM_H) room_slide(DIR_UP);
    else if (cy >= room_r * ROOM_H + ROOM_H) room_slide(DIR_DOWN);
}

// Tilo 16x16 (2 sprites) + the sword (GDD 2.4: vertical 1 sprite, horizontal 2); blink 4/4 while
// invulnerable (hidden by y = 0, never by x)
void link_draw(void) {
    uint8_t x = LSX + 8, y = LSY + 16, tile, prop = 0, s = sword_t;
    if (inv_t && (inv_t & 4) && !dead_t) {
        shadow_OAM[OAM_LINK].y = shadow_OAM[OAM_LINK + 1].y = 0;
    } else {
        if (knock_t || dead_t) tile = LINK_HURT;
        else if (s) tile = ldir == DIR_DOWN ? LINK_STAB_DOWN : ldir == DIR_UP ? LINK_STAB_UP : LINK_STAB_SIDE;
        else tile = ldir == DIR_DOWN ? LINK_DOWN_A : ldir == DIR_UP ? LINK_UP_A : LINK_SIDE_A;
        if (!s && !knock_t && !dead_t && (lmoving || sliding) && lanim) tile += 4;   // *_B frames
        if (ldir == DIR_LEFT) prop = S_FLIPX;
        oam16(OAM_LINK, x, y, SPR_LINK + tile, prop);
    }
    if (!s || s > 12) {
        shadow_OAM[OAM_SWORD].y = shadow_OAM[OAM_SWORD + 1].y = 0;
        return;
    }
    switch (ldir) {
    case DIR_UP:
        oam8(OAM_SWORD, x + 4, y - 12, SPR_LINK + LINK_SWORD_V, 0);
        shadow_OAM[OAM_SWORD + 1].y = 0;
        break;
    case DIR_DOWN:
        oam8(OAM_SWORD, x + 4, y + 12, SPR_LINK + LINK_SWORD_V, S_FLIPY);
        shadow_OAM[OAM_SWORD + 1].y = 0;
        break;
    case DIR_RIGHT:
        oam16(OAM_SWORD, x + 12, y, SPR_LINK + LINK_SWORD_H, 0);
        break;
    default:
        oam16(OAM_SWORD, x - 12, y, SPR_LINK + LINK_SWORD_H, S_FLIPX);
        break;
    }
}
