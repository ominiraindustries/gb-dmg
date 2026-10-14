// gbe: object pools in 8-bit OAM space and collisions. Array of 16-byte records (not struct of
// arrays): on the SM83 the asm walks a record with ld a,(hl+) instead of re-deriving one
// address per field (measured in games/gbe_lab: struct-of-arrays asm cost ~350 T per moved
// object). The asm is in gbe_pool.s; the *_c functions are the selftest references.
//
// Coordinates are OAM coordinates: X = screen x + 8, Y = screen y + 16. Visible area: X 0..167,
// Y 0..159. An object whose X >= 168 or Y >= 176 after moving is freed (left/top exits wrap to
// >= 168 / >= 176 too, so one compare per axis covers every side).
#include "gbe.h"

pool_obj_t pool[GBE_POOL_MAX];

uint8_t pool_alloc(uint8_t first, uint8_t n) {
    pool_obj_t *o = &pool[first];
    uint8_t i = first;
    do {
        if (!o->t) return i;
        o++; i++;
    } while (--n);
    return 0xFF;
}

void pool_clear(uint8_t first, uint8_t n) {
    pool_obj_t *o = &pool[first];
    do { o->t = 0; o++; } while (--n);
}

// Reference: position += velocity (8.8) for every live object of the range; free on exit.
// n >= 1. The x exit is checked before y is updated (the asm does the same).
void pool_move_c(uint8_t first, uint8_t n) {
    pool_obj_t *o = &pool[first];
    uint16_t t;
    do {
        if (o->t) {
            t = (uint16_t)o->xs + (uint8_t)o->vx;
            o->xs = (uint8_t)t;
            o->x += (uint8_t)(o->vx >> 8) + (uint8_t)(t >> 8);
            if (o->x >= 168) {
                o->t = 0;
            } else {
                t = (uint16_t)o->ys + (uint8_t)o->vy;
                o->ys = (uint8_t)t;
                o->y += (uint8_t)(o->vy >> 8) + (uint8_t)(t >> 8);
                if (o->y >= 176) o->t = 0;
            }
        }
        o++;
    } while (--n);
}

// ---------------------------------------------------------------- collisions
// Query box (hit_qx, hit_qy, hit_qw, hit_qh) against the boxes of a pool range, all objects of
// the range using the same box: (x + hit_ox, y + hit_oy, hit_ow, hit_oh).
uint8_t hit_qx, hit_qy, hit_qw, hit_qh, hit_ox, hit_oy, hit_ow, hit_oh;

uint8_t hit_first_c(uint8_t first, uint8_t n) {
    // [y + oy, +oh) overlaps [qy, +qh)  <=>  y - (qy - oy - oh + 1) in [0, qh + oh - 1)  (8-bit)
    uint8_t ky = hit_qy - hit_oy - hit_oh + 1, ry = hit_qh + hit_oh - 1;
    uint8_t kx = hit_qx - hit_ox - hit_ow + 1, rx = hit_qw + hit_ow - 1;
    pool_obj_t *o = &pool[first];
    uint8_t i = first;
    do {
        if (o->t && (uint8_t)(o->y - ky) < ry && (uint8_t)(o->x - kx) < rx) return i;
        o++; i++;
    } while (--n);
    return 0xFF;
}
