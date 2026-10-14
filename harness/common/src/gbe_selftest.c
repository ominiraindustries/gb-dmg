// gbe: equivalence of the engine asm with its C references, run inside the ROM on request.
// Python side: harness/gbtest.py GB.selftest(). Modules are enabled in the game's gbe_config.h.
#include <string.h>
#include "gbe.h"

uint8_t gbe_eq_request, gbe_eq_done;
uint16_t gbe_eq_mismatch, gbe_eq_count;

static uint8_t eq_rng = 0x3C;
static uint8_t rnd8(void) {
    eq_rng ^= eq_rng << 3; eq_rng ^= eq_rng >> 5; eq_rng ^= eq_rng << 1;
    return eq_rng;
}

#ifdef GBE_SELFTEST_MAP
// mt_at / solid_at: every x of the map (+64 past the end) and every y
static void eq_map(void) {
    uint16_t x;
    uint8_t y;
    for (x = 0; x < level_px_w + 64; x++) {
        y = 0;
        do {
            if (mt_at(x, y) != mt_at_c(x, y) || solid_at(x, y) != solid_at_c(x, y)) gbe_eq_mismatch++;
            gbe_eq_count++;
        } while (++y);
    }
}

// column fill: every tile column of the map
static void eq_columns(void) {
    uint16_t tc;
    uint8_t ref[16], r;
    for (tc = 0; tc < (uint16_t)level_cols << 1; tc++) {
        map_column_c(tc);
        for (r = 0; r < 16; r++) ref[r] = col_buf[r];
        map_column(tc);
        for (r = 0; r < 16; r++) if (col_buf[r] != ref[r]) { gbe_eq_mismatch++; break; }
        gbe_eq_count++;
    }
    col_pending = 0;
}
#endif

#ifdef GBE_SELFTEST_ACTORS
// act_move: signed velocities, sub-pixel carries, 16-bit x wrap (uses the last actor slot)
static void eq_act_move(void) {
    uint8_t s = GBE_ACT_MAX - 1, k, xs0, ys0, y0, xs1, ys1, y1, t = act_type[GBE_ACT_MAX - 1];
    uint16_t x0, x1;
    int16_t v;
    for (v = -0x0480; v <= 0x0480; v += 0x0013) {
        for (k = 0; k < 10; k++) {
            xs0 = k * 25;
            x0 = 0xFF80 + (uint16_t)k * 75;
            y0 = 250 - k * 25;
            ys0 = xs0 ^ 0x5A;
            act_x[s] = x0; act_xs[s] = xs0; act_y[s] = y0; act_ys[s] = ys0;
            act_vx[s] = v; act_vy[s] = -v;
            act_move(s);
            x1 = act_x[s]; xs1 = act_xs[s]; y1 = act_y[s]; ys1 = act_ys[s];
            act_x[s] = x0; act_xs[s] = xs0; act_y[s] = y0; act_ys[s] = ys0;
            act_move_c(s);
            if (act_x[s] != x1 || act_xs[s] != xs1 || act_y[s] != y1 || act_ys[s] != ys1) gbe_eq_mismatch++;
            gbe_eq_count++;
        }
    }
    act_type[s] = t;
}
#endif

#ifdef GBE_SELFTEST_POOL
#define EQ_P (GBE_POOL_MAX - 8)            // scratch pool range: the last 8 records
#define EQ_N 8
static pool_obj_t eq_save[EQ_N], eq_asm[EQ_N];

static void random_pool(void) {
    uint8_t k;
    pool_obj_t *o = &pool[EQ_P];
    for (k = 0; k < EQ_N; k++, o++) {
        o->t = rnd8() & 3;                                     // some free records
        o->x = rnd8(); o->xs = rnd8(); o->y = rnd8(); o->ys = rnd8();
        o->vx = (int16_t)((uint16_t)rnd8() << 4) - 0x0800;
        o->vy = (int16_t)((uint16_t)rnd8() << 4) - 0x0800;
        o->tile = rnd8(); o->prop = rnd8() & 0x30;
    }
}

static void eq_pool(void) {
    uint16_t r;
    uint8_t a, b, oam_save[40], ref[40], size, n;
    for (r = 0; r < 600; r++) {
        // pool_move: asm and C from the same state
        random_pool();
        memcpy(eq_save, &pool[EQ_P], sizeof(eq_save));
        pool_move(EQ_P, EQ_N);
        memcpy(eq_asm, &pool[EQ_P], sizeof(eq_asm));
        memcpy(&pool[EQ_P], eq_save, sizeof(eq_save));
        pool_move_c(EQ_P, EQ_N);
        if (memcmp(eq_asm, &pool[EQ_P], sizeof(eq_asm))) gbe_eq_mismatch++;
        gbe_eq_count++;
        // hit_first: random query and object boxes (half of them forced onto an object)
        random_pool();
        hit_qx = rnd8(); hit_qy = rnd8(); hit_qw = (rnd8() & 31) + 1; hit_qh = (rnd8() & 31) + 1;
        hit_ox = rnd8() & 7; hit_oy = rnd8() & 7; hit_ow = (rnd8() & 15) + 1; hit_oh = (rnd8() & 15) + 1;
        if (r & 1) { hit_qx = pool[EQ_P + 3].x; hit_qy = pool[EQ_P + 3].y; }
        a = hit_first(EQ_P, EQ_N);
        b = hit_first_c(EQ_P, EQ_N);
        if (a != b) gbe_eq_mismatch++;
        gbe_eq_count++;
        // spr_group: same OAM bytes (last 10 OAM entries as scratch), sizes 1/2, odd/even ranges
        size = (r & 2) ? 2 : 1;
        n = 5 + (r & 5);                                       // 5..10 slots
        spr_rot = rnd8();
        memcpy(oam_save, &shadow_OAM[30], 40);
        spr_group_c(30, n, EQ_P, EQ_N, size);
        memcpy(ref, &shadow_OAM[30], 40);
        memcpy(&shadow_OAM[30], oam_save, 40);             // same starting bytes for the asm run
        spr_group(30, n, EQ_P, EQ_N, size);
        if (memcmp(ref, &shadow_OAM[30], 40)) gbe_eq_mismatch++;
        memcpy(&shadow_OAM[30], oam_save, 40);
        gbe_eq_count++;
    }
    pool_clear(EQ_P, EQ_N);
}
#endif

void gbe_selftest(void) {
    gbe_eq_mismatch = gbe_eq_count = 0;
#ifdef GBE_SELFTEST_MAP
    eq_map();
    eq_columns();
#endif
#ifdef GBE_SELFTEST_ACTORS
    eq_act_move();
#endif
#ifdef GBE_SELFTEST_POOL
    eq_pool();
#endif
    gbe_eq_done = 1;
}
