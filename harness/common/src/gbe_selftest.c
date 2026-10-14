// gbe: equivalence of the engine asm with its C references, run inside the ROM on request.
// Python side: harness/gbtest.py GB.selftest(). Modules are enabled in the game's gbe_config.h.
// GBE_SELFTEST_BANKED in gbe_config.h puts this file (and the C references of gbe_world/gbe_gact
// it holds) in a switchable bank: needs -autobank (games/world_lab: bank 0 was 93 % full).
#include "gbe_config.h"
#ifdef GBE_SELFTEST_BANKED
#pragma bank 255
#endif
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
        spr_rot = rnd8() & 63;
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

#if defined(GBE_SELFTEST_AIM) && defined(GBE_SELFTEST_POOL)
// fire vs fire_c on the scratch records (some taken, sometimes all taken)
static void eq_fire(void) {
    uint16_t r;
    uint8_t a, b, k, x, y, d, sp, ff = fire_first, fn = fire_n, ft = fire_t, fti = fire_tile, fp = fire_prop;
    for (r = 0; r < 300; r++) {
        random_pool();
        for (k = 0; k < EQ_N; k++) if ((r & 7) == 0) pool[EQ_P + k].t = 1;   // full range
        fire_first = EQ_P; fire_n = EQ_N; fire_t = rnd8() | 1; fire_tile = rnd8(); fire_prop = rnd8();
        x = rnd8(); y = rnd8(); d = rnd8(); sp = rnd8();
        memcpy(eq_save, &pool[EQ_P], sizeof(eq_save));
        a = fire(x, y, d, sp);
        memcpy(eq_asm, &pool[EQ_P], sizeof(eq_asm));
        memcpy(&pool[EQ_P], eq_save, sizeof(eq_save));
        b = fire_c(x, y, d, sp);
        if (a != b || memcmp(eq_asm, &pool[EQ_P], sizeof(eq_asm))) gbe_eq_mismatch++;
        gbe_eq_count++;
    }
    pool_clear(EQ_P, EQ_N);
    fire_first = ff; fire_n = fn; fire_t = ft; fire_tile = fti; fire_prop = fp;
}
#endif

#ifdef GBE_SELFTEST_VMAP
// GBE_SELFTEST_VMAP = number of metatiles in the game's mt_tiles (random rows stay inside it)
static void eq_vrow(void) {
    uint16_t r;
    uint8_t m[GBE_VMAP_W], ref[2 * GBE_VMAP_W], save[2 * GBE_VMAP_W], c, v;
    memcpy(save, row_buf, sizeof(save));                       // a row may be pending
    for (r = 0; r < 400; r++) {
        for (c = 0; c < GBE_VMAP_W; c++) {
            v = rnd8();
            while (v >= GBE_SELFTEST_VMAP) v -= GBE_SELFTEST_VMAP;
            m[c] = v;
        }
        gbe_vrow_tiles_c(m, r & 1);
        memcpy(ref, row_buf, sizeof(ref));
        gbe_vrow_tiles(m, r & 1);
        if (memcmp(ref, row_buf, sizeof(ref))) gbe_eq_mismatch++;
        gbe_eq_count++;
    }
    memcpy(row_buf, save, sizeof(save));
}
#endif

#ifdef GBE_SELFTEST_VIEW
#include "view.h"
static uint8_t eq_tmp_view[VIEW_W * VIEW_H];
// view_blit vs view_blit_c on every piece, over a random canvas
static void eq_view(void) {
    static uint8_t ref[VIEW_W * VIEW_H];
    uint8_t id, i, saved = CURRENT_BANK;
    if (view_bank) SWITCH_ROM(view_bank);
    for (id = 0; id < VIEW_P_COUNT; id++) {
        for (i = 0; i < VIEW_W * VIEW_H; i++) view_buf[i] = rnd8();
        memcpy(ref, view_buf, sizeof(ref));
        view_blit_c(view_pcs + view_piece[id]);
        memcpy(eq_tmp_view, view_buf, sizeof(ref));
        memcpy(view_buf, ref, sizeof(ref));
        view_blit(view_pcs + view_piece[id]);
        if (memcmp(eq_tmp_view, view_buf, sizeof(ref))) gbe_eq_mismatch++;
        gbe_eq_count++;
    }
    if (view_bank) SWITCH_ROM(saved);
    // whole composition: asm vs C at random cells and facings of the game's map
    for (i = 0; i < 64; i++) {
        uint8_t x = rnd8() & 15, y = rnd8() & 15, f = rnd8() & 3;
        view_compose_c(x, y, f);
        memcpy(eq_tmp_view, view_buf, sizeof(ref));
        view_compose(x, y, f);
        if (memcmp(eq_tmp_view, view_buf, sizeof(ref))) gbe_eq_mismatch++;
        gbe_eq_count++;
    }
}
#endif

#ifdef GBE_SELFTEST_WORLD
// ---- C references of gbe_world.s (specification of the asm)
#define SLOT_OUT  0xFE
#define SLOT_NONE 0xFF
extern uint8_t wosx, wosy, wslot[], wcache[], wprep_n, wprep_tiles[][4], *wprep_dst[];
extern world_map_t wmap;

// C reference of the query (the asm wmt_at in gbe_world.s must match it: selftest)
uint8_t wmt_at_c(uint8_t x, uint8_t y) {
    uint8_t rx = (uint8_t)((x >> 4) - wosx), ry = (uint8_t)((y >> 4) - wosy), s;
    if (rx > 2 || ry > 2) return wmap.border;
    s = wslot[ry * 3 + rx];
    if (s >= SLOT_OUT) return wmap.border;
    return wcache[((uint16_t)s << 8) | (uint8_t)((y << 4) | (x & 15))];
}

// C reference of wprep_cell (selftest)
uint8_t wprep_cell_c(uint8_t x, uint8_t y) {
    uint8_t rx = (uint8_t)((x >> 4) - wosx), ry = (uint8_t)((y >> 4) - wosy);
    if (rx <= 2 && ry <= 2 && wslot[ry * 3 + rx] == SLOT_NONE) return 0;
    wprep_dst[wprep_n] = (uint8_t *)0x9800u + ((uint16_t)(y & 15) << 6) + ((x & 15) << 1);
    memcpy(wprep_tiles[wprep_n], wmt_tiles[wmt_at_c(x, y)], 4);
    wprep_n++;
    return 1;
}

// wmt_at and wprep_cell: every cell of the 256x256 u8 plane (cache, border, outside, loading)
uint8_t wprep_cell(uint8_t x, uint8_t y);
static void eq_world_pass(void) {
    uint8_t x = 0, y = 0, a, b, ta[4], *da;
    do {
        x = 0;
        do {
            if (wmt_at(x, y) != wmt_at_c(x, y)) gbe_eq_mismatch++;
            wprep_n = 0;
            a = wprep_cell(x, y);
            memcpy(ta, wprep_tiles[0], 4); da = wprep_dst[0];
            wprep_n = 0;
            b = wprep_cell_c(x, y);
            if (a != b || wprep_n != b || (a && (memcmp(ta, wprep_tiles[0], 4) || da != wprep_dst[0])))
                gbe_eq_mismatch++;
            gbe_eq_count++;
        } while (++x);
    } while (++y);
    wprep_n = 0;
}

static void eq_world(void) {
    uint8_t keep = wslot[0];
    eq_world_pass();
    wslot[0] = 0xFF;                 // a sector "still loading"
    eq_world_pass();
    wslot[0] = keep;
}
#endif

#ifdef GBE_SELFTEST_GACT
// ---- C references of gbe_gact.s (specification of the asm)
#define N GBE_GACT_MAX
// C reference of gact_at: actor standing on or walking into (x, y), else 0xFF
uint8_t gact_at_c(uint8_t x, uint8_t y) {
    uint8_t i;
    gact_t *a = gact;
    for (i = 0; i < N; i++, a++) {
        if (!a->type) continue;
        if ((a->x == x && a->y == y) || (a->tx == x && a->ty == y)) return i;
    }
    return 0xFF;
}

// C reference of gact_move_all: timers, walking, arrival, walk animation
void gact_move_all_c(void) {
    uint8_t i, t;
    gact_t *a = gact;
    for (i = 0; i < N; i++, a++) {
        if (!a->type) continue;
        if (a->timer) a->timer--;
        if (!a->moving) continue;
        t = a->sub + a->rate_lo;
        a->step += a->rate_hi + (t < a->sub);
        a->sub = t;
        if (a->step >= 16) {
            a->x = a->tx;
            a->y = a->ty;
            a->step = a->sub = 0;
            a->moving = 0;
            a->prio = GACT_PRIO_DIRTY;
        }
        if ((a->step & 7) == 0) a->anim ^= 1;
    }
}

// C reference of gact_draw: every slot from OAM `first` (2 sprites each), 16x16; free and
// off-screen ones hidden (y = 0). Tile: GACT_ANIM2 = 2 frames 0/4 facing right, else the NPC
// layout; left = the side frame flipped. PRIO cells (tall grass) set the OAM priority bit.
void gact_draw_c(uint8_t first) {
    uint8_t i, tile, prop;
    int16_t sx, sy;
    gact_t *a = gact;
    OAM_item_t *o = &shadow_OAM[first];
    for (i = 0; i < N; i++, a++, o += 2) {
        if (!a->type) { o[0].y = o[1].y = 0; continue; }
        sx = gact_wx(i) - cam_x;
        sy = gact_wy(i) - cam_y;
        if ((uint16_t)(sx + 16) >= 176 || (uint16_t)(sy + 16) >= 160) { o[0].y = o[1].y = 0; continue; }
        if (a->prio == GACT_PRIO_DIRTY) a->prio = (wattr_at(a->x, a->y) & gact_prio_mask) ? S_PRIORITY : 0;
        prop = a->prop | a->prio;
        if (a->dir == 2) prop |= S_FLIPX;
        if (a->type & GACT_ANIM2) tile = a->tile + (a->anim ? 4 : 0);
        else tile = a->tile + gact_npc_frame[a->dir] + ((a->moving && a->anim) ? 4 : 0);
        oam16(first + (i << 1), (uint8_t)sx + 8, (uint8_t)sy + 16, tile, prop);
    }
}

// gact_move_all / gact_draw / gact_at: random records around the camera, C vs asm on copies
// (records and the OAM range compared); uses OAM 20-39 as scratch
static gact_t eq_gsave[GBE_GACT_MAX], eq_gref[GBE_GACT_MAX];
static uint8_t eq_oref[GBE_GACT_MAX * 8];
static void eq_gact_random(void) {
    uint8_t i, cx = (uint8_t)((uint16_t)cam_x >> 4), cy = (uint8_t)((uint16_t)cam_y >> 4);
    gact_t *a = gact;
    for (i = 0; i < GBE_GACT_MAX; i++, a++) {
        a->type = (rnd8() & 3) ? (rnd8() | 1) : 0;
        a->x = cx + (rnd8() & 15) - 3;
        a->y = cy + (rnd8() & 15) - 3;
        a->dir = rnd8() & 3;
        a->moving = rnd8() & 1;
        a->tx = a->x + (a->dir == 3) - (a->dir == 2);
        a->ty = a->y + (a->dir == 0) - (a->dir == 1);
        a->step = rnd8() & 15;
        a->sub = rnd8();
        a->rate_lo = rnd8();
        a->rate_hi = rnd8() & 1;
        a->timer = rnd8() & 3;
        a->anim = rnd8() & 1;
        a->tile = rnd8() & 0x7C;
        a->prop = rnd8() & 0x10;
        a->prio = (rnd8() & 1) ? 0xFF : (rnd8() & 0x80);
    }
}
static void eq_gact(void) {
    uint8_t k, x, y, first = 40 - GBE_GACT_MAX * 2;
    for (k = 0; k < 200; k++) {
        eq_gact_random();
        memcpy(eq_gsave, gact, sizeof(eq_gsave));
        gact_move_all_c();
        gact_draw_c(first);
        memcpy(eq_gref, gact, sizeof(eq_gref));
        memcpy(eq_oref, &shadow_OAM[first], sizeof(eq_oref));
        memcpy(gact, eq_gsave, sizeof(eq_gsave));
        gact_move_all();
        gact_draw(first);
        if (memcmp(eq_gref, gact, sizeof(eq_gref)) || memcmp(eq_oref, &shadow_OAM[first], sizeof(eq_oref)))
            gbe_eq_mismatch++;
        for (y = 0; y < 8; y++) {
            x = gact[rnd8() % GBE_GACT_MAX].x + (rnd8() & 1);
            if (gact_at(x, gact[y].ty) != gact_at_c(x, gact[y].ty)) gbe_eq_mismatch++;
        }
        gbe_eq_count++;
    }
    memset(gact, 0, sizeof(eq_gsave));
}
#endif

void gbe_selftest(void) GBE_SELFTEST_ATTR {
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
#if defined(GBE_SELFTEST_AIM) && defined(GBE_SELFTEST_POOL)
    eq_fire();
#endif
#ifdef GBE_SELFTEST_VMAP
    eq_vrow();
#endif
#ifdef GBE_SELFTEST_WORLD
    eq_world();
#endif
#ifdef GBE_SELFTEST_GACT
    eq_gact();
#endif
#ifdef GBE_SELFTEST_VIEW
    eq_view();
#endif
    gbe_eq_done = 1;
}
