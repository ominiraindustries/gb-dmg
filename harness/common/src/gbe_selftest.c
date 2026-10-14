// gbe: equivalence of the engine asm with its C references, run inside the ROM on request.
// Python side: harness/gbtest.py GB.selftest() (sets gbe_eq_request, waits for gbe_eq_done).
#include "gbe.h"

uint8_t gbe_eq_request, gbe_eq_done;
uint16_t gbe_eq_mismatch, gbe_eq_count;

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

void gbe_selftest(void) {
    gbe_eq_mismatch = gbe_eq_count = 0;
    eq_map();
    eq_act_move();
    eq_columns();
    gbe_eq_done = 1;
}
