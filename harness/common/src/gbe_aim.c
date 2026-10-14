// gbe: aiming and bullet patterns (32 directions). Tables generated with Python (math.sin/cos/
// atan2); dir 0 = down, clockwise on screen (8 = left, 16 = up, 24 = right):
//   vx = -sin(dir * 11.25 deg), vy = cos(dir * 11.25 deg), 8.8 fixed point.
// aim_vx/aim_vy[spd * 32 + dir]: speeds 0 = 1.0, 1 = 1.25 (v + v>>2), 2 = 1.5 (v + v>>1), 3 = 2.0.
// fire() is asm (gbe_aim.s, ~2000 T in C per bullet); fire_c is the selftest reference.
#include "gbe.h"

const int16_t aim_vx[128] = {
    0, -50, -98, -142, -181, -213, -237, -251,
    -256, -251, -237, -213, -181, -142, -98, -50,
    0, 50, 98, 142, 181, 213, 237, 251,
    256, 251, 237, 213, 181, 142, 98, 50,
    0, -63, -123, -178, -227, -267, -297, -314,
    -320, -314, -297, -267, -227, -178, -123, -63,
    0, 62, 122, 177, 226, 266, 296, 313,
    320, 313, 296, 266, 226, 177, 122, 62,
    0, -75, -147, -213, -272, -320, -356, -377,
    -384, -377, -356, -320, -272, -213, -147, -75,
    0, 75, 147, 213, 271, 319, 355, 376,
    384, 376, 355, 319, 271, 213, 147, 75,
    0, -100, -196, -284, -362, -426, -474, -502,
    -512, -502, -474, -426, -362, -284, -196, -100,
    0, 100, 196, 284, 362, 426, 474, 502,
    512, 502, 474, 426, 362, 284, 196, 100
};
const int16_t aim_vy[128] = {
    256, 251, 237, 213, 181, 142, 98, 50,
    0, -50, -98, -142, -181, -213, -237, -251,
    -256, -251, -237, -213, -181, -142, -98, -50,
    0, 50, 98, 142, 181, 213, 237, 251,
    320, 313, 296, 266, 226, 177, 122, 62,
    0, -63, -123, -178, -227, -267, -297, -314,
    -320, -314, -297, -267, -227, -178, -123, -63,
    0, 62, 122, 177, 226, 266, 296, 313,
    384, 376, 355, 319, 271, 213, 147, 75,
    0, -75, -147, -213, -272, -320, -356, -377,
    -384, -377, -356, -320, -272, -213, -147, -75,
    0, 75, 147, 213, 271, 319, 355, 376,
    512, 502, 474, 426, 362, 284, 196, 100,
    0, -100, -196, -284, -362, -426, -474, -502,
    -512, -502, -474, -426, -362, -284, -196, -100,
    0, 100, 196, 284, 362, 426, 474, 502
};

// First quadrant: aim_tab[ay * 16 + ax] = round(atan2(ax, ay) / 11.25 deg), 0 (down) .. 8 (side)
static const uint8_t aim_tab[256] = {
    0, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8,
    0, 4, 6, 6, 7, 7, 7, 7, 7, 7, 7, 8, 8, 8, 8, 8,
    0, 2, 4, 5, 6, 6, 6, 7, 7, 7, 7, 7, 7, 7, 7, 7,
    0, 2, 3, 4, 5, 5, 6, 6, 6, 6, 7, 7, 7, 7, 7, 7,
    0, 1, 2, 3, 4, 5, 5, 5, 6, 6, 6, 6, 6, 6, 7, 7,
    0, 1, 2, 3, 3, 4, 4, 5, 5, 5, 6, 6, 6, 6, 6, 6,
    0, 1, 2, 2, 3, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 6,
    0, 1, 1, 2, 3, 3, 4, 4, 4, 5, 5, 5, 5, 5, 6, 6,
    0, 1, 1, 2, 2, 3, 3, 4, 4, 4, 5, 5, 5, 5, 5, 6,
    0, 1, 1, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 5, 5,
    0, 1, 1, 1, 2, 2, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5,
    0, 0, 1, 1, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5,
    0, 0, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 4, 4, 5,
    0, 0, 1, 1, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 4,
    0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4,
    0, 0, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4
};

uint8_t fire_first, fire_n, fire_t, fire_tile, fire_prop;

// Halving both components keeps the angle within the table's precision: error <= 1 direction
// (checked against atan2 in games/shmup/tests/test_game.py).
uint8_t aim_dir(int8_t dx, int8_t dy) {
    uint8_t ax = dx < 0 ? (uint8_t)-dx : (uint8_t)dx;
    uint8_t ay = dy < 0 ? (uint8_t)-dy : (uint8_t)dy, q;
    while ((ax | ay) & 0xF0) { ax >>= 1; ay >>= 1; }
    q = aim_tab[(uint8_t)(ay << 4) | ax];
    if (dy >= 0) return dx > 0 ? (uint8_t)(32 - q) & 31 : q;
    return dx > 0 ? 16 + q : 16 - q;
}

uint8_t fire_c(uint8_t x, uint8_t y, uint8_t dir, uint8_t spd) {
    uint8_t i = pool_alloc(fire_first, fire_n), k;
    pool_obj_t *o;
    if (i == 0xFF) return 0xFF;
    o = &pool[i];
    dir &= 31;
    k = ((spd & 3) << 5) | dir;
    o->t = fire_t;
    o->x = x; o->xs = 0;
    o->y = y; o->ys = 0;
    o->vx = aim_vx[k];
    o->vy = aim_vy[k];
    o->s = dir; o->tm = 0; o->aux = 0;
    o->tile = fire_tile; o->prop = fire_prop;
    return i;
}

uint8_t fire_fan(uint8_t x, uint8_t y, uint8_t dir, uint8_t n, uint8_t step, uint8_t spd) {
    uint8_t k, d = dir, out = 0;
    for (k = (n - 1) >> 1; k; k--) d -= step;
    for (k = 0; k < n; k++, d += step)
        if (fire(x, y, d, spd) != 0xFF) out++;
    return out;
}
