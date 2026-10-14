// gbe: 4-way scrolling world of 16x16 metatiles (top-down RPGs and adventures).
//
// A map (harness/world.py, res/maps/*.map) is a grid of sectors of 16x16 cells stored in a ROM bank.
// WRAM keeps the 3x3 sectors around the focus cell (the player): queries never switch banks, and
// one sector is (re)loaded per frame when the focus crosses into another sector.
// The 32x32 BG map is a ring of 16x16 metatiles: cell (x, y) lives at BG metatile (x & 15, y & 15),
// SCX/SCY = camera & 255. The drawn region is 13x12 cells around the camera (screen + 1 cell of
// margin on every side); when the camera crosses a cell boundary the entering column/row is
// queued and drawn at world_edge_budget metatiles per VBlank (vram_mt4_list, ~100 T each).
// Cells are u8: maps up to 15x15 sectors, so coordinates 240-255 are always outside (= border),
// including the "negative" cells the camera shows left of / above cell 0.
#include <string.h>
#include "gbe.h"

#define REG_W   13                   // drawn region: covers the 11x10 cells a scrolled screen shows
#define REG_H   12
#define EQ_N    16                   // edge queue of lines (power of 2)
#define PREP_N  4                    // max metatiles copied per VBlank
#define SLOT_OUT  0xFE               // wslot: position outside the map (border)
#define SLOT_NONE 0xFF               // wslot: sector not loaded yet

uint8_t wmt_tiles[GBE_WORLD_MT][4], wmt_attr[GBE_WORLD_MT];
uint8_t wcache[9 * 256];
uint8_t wcache_sector[9];            // map grid index held by each cache slot (0xFF = empty)
uint8_t wslot[9];                    // slot of each 3x3 position around the focus sector
uint8_t wgrid[256];                  // the map's sector grid (unique sector index per sector)
world_map_t wmap;
uint8_t wmap_bank;
uint8_t wev_sx = 0xFF, wev_sy = 0xFF;    // sector whose objects are in wev[] (gbe_world objects)
uint8_t wosx, wosy;                  // sector of 3x3 position 0 (focus sector - 1; may be 0xFF)
uint8_t wfocus_sx, wfocus_sy;
uint8_t world_loaded_slot;           // slot loaded this frame (0xFF = none): scan its events
uint8_t world_loaded_sx, world_loaded_sy;   // and its sector
int16_t cam_x, cam_y;                // world px at the screen's top-left
uint8_t reg_x, reg_y;                // top-left cell of the drawn region
uint8_t world_edge_budget = 3;
uint8_t eq_x[EQ_N], eq_y[EQ_N], eq_v[EQ_N], eq_n[EQ_N], eq_head, eq_tail, edge_pending;
uint8_t cur_x, cur_y, cur_v, cur_n;   // the line world_prepare is walking
uint16_t world_lost;                 // queue overflows (a test asserts 0)
uint8_t *wprep_dst[PREP_N];
uint8_t wprep_tiles[PREP_N][4];
uint8_t wprep_n;

static const uint8_t pos_x[9] = { 0, 1, 2, 0, 1, 2, 0, 1, 2 };   // no / and % by 3 (SDCC calls a routine)
static const uint8_t pos_y[9] = { 0, 0, 0, 1, 1, 1, 2, 2, 2 };

void world_metatiles(uint8_t bank, const uint8_t *tiles, const uint8_t *attr, uint8_t n) {
    bank_memcpy(bank, wmt_tiles, tiles, (uint16_t)n << 2);
    bank_memcpy(bank, wmt_attr, attr, n);
}

uint8_t wprep_cell(uint8_t x, uint8_t y);           // asm (gbe_world.s)
void wcopy128(uint8_t *dst, const uint8_t *src);    // asm

uint8_t wattr_at(uint8_t x, uint8_t y) {
    return wmt_attr[wmt_at(x, y)];
}

// 3x3 position of a cell, or 0xFF if it is outside the 3x3
static uint8_t wpos(uint8_t x, uint8_t y) {
    uint8_t rx = (uint8_t)((x >> 4) - wosx), ry = (uint8_t)((y >> 4) - wosy);
    if (rx > 2 || ry > 2) return 0xFF;
    return ry * 3 + rx;
}

static const uint16_t bit9[9] = { 1, 2, 4, 8, 16, 32, 64, 128, 256 };
uint8_t gslot[256];                  // cache slot holding each map grid index (0xFF = not cached)
uint8_t wmissing;                    // 3x3 positions waiting for their sector
uint8_t wload_pos = 0xFF, wload_slot, wload_g;   // sector being loaded (half per frame)
uint16_t wused;                      // slots referenced by the 3x3

// On a sector change: which slot holds each position (gslot: 9 lookups, no search)
static void remap(void) {
    uint8_t i, r, c, sx, sy, s, g;
    wused = 0;
    wmissing = 0;
    wload_pos = 0xFF;                // a half-loaded sector is dropped (its old sector was evicted)
    i = 0;
    g = (uint8_t)(wosy * wmap.w + wosx);            // one multiply, then additions
    sy = wosy;
    for (r = 0; r < 3; r++, sy++, g += wmap.w - 3) {
        sx = wosx;
        for (c = 0; c < 3; c++, sx++, g++, i++) {
            if (sx >= wmap.w || sy >= wmap.h) { wslot[i] = SLOT_OUT; continue; }
            s = gslot[g];
            wslot[i] = s;
            if (s == SLOT_NONE) wmissing++;
            else wused |= bit9[s];
        }
    }
}

static void copy_half(uint8_t *dst, const uint8_t *src) {
    uint8_t saved = CURRENT_BANK;
    SWITCH_ROM(wmap_bank);
    wcopy128(dst, src);
    SWITCH_ROM(saved);
}

// One half sector (128 B) per call: start a missing sector in a free slot, or finish one.
// Returns 0 when nothing is left to load.
static uint8_t load_step(void) {
    uint8_t i, k, old;
    const uint8_t *src;
    if (wload_pos != 0xFF) {
        src = wmap.sectors + ((uint16_t)wgrid[wload_g] << 8) + 128;
        copy_half(wcache + ((uint16_t)wload_slot << 8) + 128, src);
        wcache_sector[wload_slot] = wload_g;
        gslot[wload_g] = wload_slot;
        wslot[wload_pos] = wload_slot;
        world_loaded_slot = wload_slot;
        world_loaded_sx = wosx + pos_x[wload_pos];
        world_loaded_sy = wosy + pos_y[wload_pos];
        wload_pos = 0xFF;
        wmissing--;
        return 1;
    }
    if (!wmissing) return 0;
    for (i = 0; wslot[i] != SLOT_NONE; i++) ;
    for (k = 0; wused & bit9[k]; k++) ;
    old = wcache_sector[k];
    if (old != 0xFF) gslot[old] = SLOT_NONE;
    wcache_sector[k] = 0xFF;
    wused |= bit9[k];
    wload_pos = i;
    wload_slot = k;
    wload_g = (uint8_t)(wosy + pos_y[i]) * wmap.w + (uint8_t)(wosx + pos_x[i]);
    copy_half(wcache + ((uint16_t)k << 8), wmap.sectors + ((uint16_t)wgrid[wload_g] << 8));
    return 1;
}

void world_focus(uint8_t x, uint8_t y) {
    uint8_t sx = x >> 4, sy = y >> 4;
    world_loaded_slot = 0xFF;
    if (sx != wfocus_sx || sy != wfocus_sy) {
        wfocus_sx = sx;
        wfocus_sy = sy;
        wosx = sx - 1;
        wosy = sy - 1;
        remap();
        return;                      // the load starts next frame: no remap + copy peak
    }
    load_step();
}

// Edge queue of LINES (a column or a row of the region): pushing one is O(1); world_prepare walks
// them cell by cell. Single cells (world_set_cell) are lines of length 1.
static void push(uint8_t x, uint8_t y, uint8_t vert, uint8_t n) {
    uint8_t i;
    if ((uint8_t)(eq_tail - eq_head) >= EQ_N) { world_lost++; return; }
    i = eq_tail & (EQ_N - 1);
    eq_x[i] = x;
    eq_y[i] = y;
    eq_v[i] = vert;
    eq_n[i] = n;
    eq_tail++;
}

#define queue_col(x) push((x), reg_y, 1, REG_H)
#define queue_row(y) push(reg_x, (y), 0, REG_W)

void world_camera(int16_t x, int16_t y) {
    uint8_t nx = (uint8_t)((uint16_t)x >> 4) - 1, ny = (uint8_t)((uint16_t)y >> 4) - 1;
    cam_x = x;
    cam_y = y;
    scx_shadow = (uint8_t)x;
    scy_shadow = (uint8_t)y;
    while (reg_x != nx) {
        if ((int8_t)(nx - reg_x) > 0) { reg_x++; queue_col(reg_x + REG_W - 1); }
        else { reg_x--; queue_col(reg_x); }
    }
    while (reg_y != ny) {
        if ((int8_t)(ny - reg_y) > 0) { reg_y++; queue_row(reg_y + REG_H - 1); }
        else { reg_y--; queue_row(reg_y); }
    }
}

static uint8_t *bg_cell(uint8_t x, uint8_t y) {
    return (uint8_t *)0x9800u + ((uint16_t)(y & 15) << 6) + ((x & 15) << 1);
}

// Prepare up to world_edge_budget queued metatiles for the next VBlank. Entries that left the
// region are dropped (their BG slot may belong to another cell now); entries whose sector is
// still loading wait.
void world_prepare(void) {
    uint8_t i;
    wprep_n = 0;
    while (wprep_n < world_edge_budget) {
        if (!cur_n) {                                      // next line from the queue
            if (eq_head == eq_tail) break;
            i = eq_head & (EQ_N - 1);
            cur_x = eq_x[i]; cur_y = eq_y[i]; cur_v = eq_v[i]; cur_n = eq_n[i];
            eq_head++;
        }
        if ((uint8_t)(cur_x - reg_x) < REG_W && (uint8_t)(cur_y - reg_y) < REG_H && !wprep_cell(cur_x, cur_y))
            break;                                         // its sector is still loading
        if (cur_v) cur_y++; else cur_x++;
        cur_n--;
    }
    edge_pending = (uint8_t)(eq_tail - eq_head) + (cur_n ? 1 : 0);
}

void world_update(uint8_t fx, uint8_t fy, int16_t cx, int16_t cy) {
    world_focus(fx, fy);
    world_camera(cx, cy);
    world_prepare();
}

void world_draw_vram(void) {
    if (wprep_n) {
        vram_mt4_list(wprep_dst, wprep_tiles[0], wprep_n);
        wprep_n = 0;
    }
}

// LCD off: load a map, the 3x3 around (fx, fy), and draw the whole region at camera (cx, cy)
void world_load(uint8_t bank, const world_map_t *map, uint8_t fx, uint8_t fy, int16_t cx, int16_t cy) {
    uint8_t r, c, x, y;
    wmap_bank = bank;
    wev_sx = 0xFF;                   // objects of the old map are stale
    bank_memcpy(bank, &wmap, map, sizeof(world_map_t));
    bank_memcpy(bank, wgrid, wmap.grid, wmap.w * wmap.h);
    memset(wcache_sector, 0xFF, 9);
    memset(gslot, 0xFF, sizeof(gslot));
    wfocus_sx = wfocus_sy = 0xFF;
    world_focus(fx, fy);
    while (load_step()) ;
    world_loaded_slot = 0xFF;
    eq_head = eq_tail = 0;
    cur_n = 0;
    wprep_n = 0;
    cam_x = cx;
    cam_y = cy;
    scx_shadow = (uint8_t)cx;
    scy_shadow = (uint8_t)cy;
    reg_x = (uint8_t)((uint16_t)cx >> 4) - 1;
    reg_y = (uint8_t)((uint16_t)cy >> 4) - 1;
    y = reg_y;
    for (r = 0; r < REG_H; r++, y++) {
        x = reg_x;
        for (c = 0; c < REG_W; c++, x++) {
            wprep_dst[0] = bg_cell(x, y);
            memcpy(wprep_tiles[0], wmt_tiles[wmt_at(x, y)], 4);
            vram_mt4_list(wprep_dst, wprep_tiles[0], 1);
        }
    }
    edge_pending = 0;
}

// ---------------------------------------------------------------- objects (world.py events)
world_ev_t wev[GBE_WORLD_EV_MAX];
uint8_t wev_n, wmap_id;

// Copy the objects of sector (sx, sy) of the current map to wev[] (outside the map: none)
uint8_t world_events(uint8_t sx, uint8_t sy) {
    uint16_t idx[2];
    uint8_t g;
    wev_sx = sx;
    wev_sy = sy;
    wev_n = 0;
    if (sx >= wmap.w || sy >= wmap.h || !wmap.evidx) return 0;
    g = sy * wmap.w + sx;
    bank_memcpy(wmap_bank, idx, wmap.evidx + g, 4);
    wev_n = (uint8_t)(idx[1] - idx[0]);
    if (wev_n > GBE_WORLD_EV_MAX) wev_n = GBE_WORLD_EV_MAX;
    if (wev_n) bank_memcpy(wmap_bank, wev, wmap.events + (idx[0] << 3), (uint16_t)wev_n << 3);
    return wev_n;
}

world_ev_t *world_event_at(uint8_t x, uint8_t y) {
    uint8_t k;
    if ((x >> 4) != wev_sx || (y >> 4) != wev_sy) world_events(x >> 4, y >> 4);
    for (k = 0; k < wev_n; k++)
        if (wev[k].x == x && wev[k].y == y) return &wev[k];
    return 0;
}

BANKREF_EXTERN(world_maps)
extern const gbe_ref_t world_maps[];

// LCD off: load map MAP_<NAME> (world.py world_index)
void world_load_id(uint8_t id, uint8_t fx, uint8_t fy, int16_t cx, int16_t cy) {
    gbe_ref_t r;
    bank_memcpy(BANK(world_maps), &r, &world_maps[id], sizeof(r));
    wmap_id = id;
    wev_sx = 0xFF;
    world_load((uint8_t)(uint16_t)r.bank, (const world_map_t *)r.ptr, fx, fy, cx, cy);
}

// Change a cell in the cache (a temporary patch: lost when its sector is reloaded) and redraw it
void world_set_cell(uint8_t x, uint8_t y, uint8_t mt) {
    uint8_t p = wpos(x, y);
    if (p == 0xFF || wslot[p] >= SLOT_OUT) return;
    wcache[((uint16_t)wslot[p] << 8) | (uint8_t)((y << 4) | (x & 15))] = mt;
    if ((uint8_t)(x - reg_x) < REG_W && (uint8_t)(y - reg_y) < REG_H) push(x, y, 0, 1);
}
