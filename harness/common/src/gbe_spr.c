// gbe: OAM manager for many objects - priority groups with fixed OAM ranges.
// Lower OAM indices win on the DMG when a line has more than 10 sprites, so groups written to
// smaller OAM indices have priority. Inside a group the first OAM slot rotates every frame
// (spr_rot): objects on a crowded line take turns being dropped (flicker) instead of always
// losing the same ones. Size the group's OAM range >= live objects x size.
// Work done by spr_group_core (asm, gbe_pool.s); spr_group_c is the selftest reference.
// Requires shadow_OAM page-aligned (GBDK places it at 0xC000).
#include "gbe.h"

uint8_t spr_rot;                              // advance once per frame
uint8_t spr_p_oam, spr_p_n, spr_p_first, spr_p_count, spr_p_size, spr_p_start;
void spr_group_core(void);

// First OAM slot (relative to the group) this frame: a multiple of size below oam_n, rotating
static uint8_t group_start(uint8_t oam_n, uint8_t size) {
    uint8_t s = spr_rot & 31, slots = size == 2 ? oam_n >> 1 : oam_n;
    if (slots <= 1) return 0;
    while (s >= slots) s -= slots;
    return size == 2 ? s << 1 : s;
}

void spr_group(uint8_t oam_first, uint8_t oam_n, uint8_t pool_first, uint8_t pool_n, uint8_t size) {
    spr_p_oam = oam_first;
    spr_p_n = oam_n;
    spr_p_first = pool_first;
    spr_p_count = pool_n;
    spr_p_size = size;
    spr_p_start = group_start(oam_n, size);
    spr_group_core();
}

// Reference (same output as spr_group_core): hide the range (Y = 0), then write live objects
// in pool order starting at the rotated slot, wrapping inside the range; stop when full.
void spr_group_c(uint8_t oam_first, uint8_t oam_n, uint8_t pool_first, uint8_t pool_n, uint8_t size) {
    OAM_item_t *begin = &shadow_OAM[oam_first], *end = begin + oam_n, *o;
    pool_obj_t *p = &pool[pool_first];
    uint8_t k, left = size == 2 ? oam_n & 0xFE : oam_n, t, pr;
    for (o = begin; o < end; o++) o->y = 0;                     // Y = 0 hides a slot
    o = begin + group_start(oam_n, size);
    for (k = 0; k < pool_n && left; k++, p++) {
        if (!p->t) continue;
        t = p->tile; pr = p->prop;
        if (size == 2) {
            uint8_t t2 = t + 2;
            if (pr & S_FLIPX) { t2 = t; t += 2; }
            o->y = p->y; o->x = p->x; o->tile = t; o->prop = pr; o++;
            o->y = p->y; o->x = p->x + 8; o->tile = t2; o->prop = pr; o++;
            left -= 2;
        } else {
            o->y = p->y; o->x = p->x; o->tile = t; o->prop = pr; o++;
            left--;
        }
        if (o >= begin + (size == 2 ? oam_n & 0xFE : oam_n)) o = begin;
    }
}
