// gbe: first-person grid view (dungeon crawlers). The view (20x12 tiles) is a mosaic of tile
// indices: pieces of res/view.pcs (harness/fpview.py: format, geometry, reference compositor)
// copied far to near into view_buf. Nothing is generated per pixel.
//
// The game provides:
//   view_map = its 16x16 map of cell types (y * 16 + x) and view_class = a table cell type ->
//   VIEW_FREE / VIEW_WALL / VIEW_DOOR / VIEW_LOCKED / VIEW_DOWN / VIEW_UP (off the map: VIEW_WALL),
//   uint8_t view_cell(uint8_t x, uint8_t y) with the same answer (used by the C reference)
//   view_bank = BANK(view) if "view" is in banked_res (0 = not banked)
// and links the generated view.c (view_pcs, view_piece) from res/view.pcs.
// Same painting rules as fpview.pieces_for(); tests compare the ROM's view_buf with fpview.compose().
#include "gbe.h"
#include "view.h"                       // generated: VIEW_P_* ids, view_pcs, view_piece

uint8_t view_buf[VIEW_W * VIEW_H];
uint8_t view_bg[VIEW_W * VIEW_H];       // the BG piece alone, copied first by view_compose
uint8_t view_bank;
void view_copy240(uint8_t *dst, const uint8_t *src);   // asm, ~20 T per byte

void view_blit(const uint8_t *p);       // asm (gbe_view.s)

// C reference of view_blit: row0, rows, then per row col, len, tiles[len]
void view_blit_c(const uint8_t *p) {
    uint8_t rows, len, *d = view_buf + (uint16_t)p[0] * VIEW_W, *q;
    rows = p[1];
    p += 2;
    while (rows--) {
        q = d + *p++;
        len = *p++;
        while (len--) *q++ = *p++;
        d += VIEW_W;
    }
}

#define BLIT(id) view_blit(view_pcs + view_piece[id])

// Painting order (fpview ORDER / FRONTS / SIDES): d, l, piece for a wall; center fronts (l = 0)
// pick wall / door / stairs + lock by class.
const uint8_t view_lay_d[] = { 3, 3, 3, 3, 3,  2, 2, 2, 2,  2, 2, 2,  1, 1,  1, 1, 1,  0, 0 };
const int8_t view_lay_l[] = { -2, -1, 0, 1, 2,  -2, -1, 1, 2,  -1, 0, 1,  -1, 1,  -1, 0, 1,  -1, 1 };
// cell offsets per facing: d * dir + l * right (no multiplies at run time: they were ~15k T)
const int8_t view_lay_ox[4][19] = {
    { -2, -1, 0, 1, 2, -2, -1, 1, 2, -1, 0, 1, -1, 1, -1, 0, 1, -1, 1 },
    { 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 0, 0 },
    { 2, 1, 0, -1, -2, 2, 1, -1, -2, 1, 0, -1, 1, -1, 1, 0, -1, 1, -1 },
    { -3, -3, -3, -3, -3, -2, -2, -2, -2, -2, -2, -2, -1, -1, -1, -1, -1, 0, 0 },
};
const int8_t view_lay_oy[4][19] = {
    { -3, -3, -3, -3, -3, -2, -2, -2, -2, -2, -2, -2, -1, -1, -1, -1, -1, 0, 0 },
    { -2, -1, 0, 1, 2, -2, -1, 1, 2, -1, 0, 1, -1, 1, -1, 0, 1, -1, 1 },
    { 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 0, 0 },
    { 2, 1, 0, -1, -2, 2, 1, -1, -2, 1, 0, -1, 1, -1, 1, 0, -1, 1, -1 },
};
const uint8_t view_lay_p[] = {
    VIEW_P_F3L2, VIEW_P_F3L1, VIEW_P_F3C, VIEW_P_F3R1, VIEW_P_F3R2,
    VIEW_P_S2L2, VIEW_P_S2L1, VIEW_P_S2R1, VIEW_P_S2R2,
    VIEW_P_F2L1, VIEW_P_F2C, VIEW_P_F2R1,
    VIEW_P_S1L1, VIEW_P_S1R1,
    VIEW_P_F1L1, VIEW_P_F1C, VIEW_P_F1R1,
    VIEW_P_S0L, VIEW_P_S0R,
};
const uint8_t view_door_p[] = { 0, VIEW_P_D1, VIEW_P_D2, VIEW_P_D3 };
const uint8_t view_stair_p[] = { 0, VIEW_P_E1, VIEW_P_E2, VIEW_P_E3 };
const uint8_t view_lock_p[] = { 0, VIEW_P_LK1, VIEW_P_LK2, VIEW_P_LK3 };
const int8_t view_dx[4] = { 0, 1, 0, -1 };   // facing 0 N, 1 E, 2 S, 3 W
const int8_t view_dy[4] = { -1, 0, 1, 0 };

// view_compose_bg() must have run once (it fills view_bg).
// Exact culling (fpview.occlusion, generated in view.c): a slot is skipped when every slot of one
// of its masks is solid, i.e. nearer pieces cover all its tiles. Same result as painting all
// (tests compare with fpview.compose, which paints everything); ~2x overdraw before.
uint8_t view_cls[19], view_solid[3], vc_x, vc_y, vc_f;
const uint8_t *view_map;                // 16x16 cell types (y * 16 + x), read by the asm
const uint8_t *view_class;              // cell type -> VIEW_* (the same as view_cell does)
void view_classify(void);               // asm: view_cls[] + view_solid bitmask (calls view_cell)
void view_paint(void);                  // asm: culling + piece choice + view_blit

// The C loops of view_compose_c cost ~27k T (SDCC: arrays and pointers); asm ~5k (gbe_view.s)
void view_compose(uint8_t x, uint8_t y, uint8_t f) {
    uint8_t saved = CURRENT_BANK;
    vc_x = x; vc_y = y; vc_f = f & 3;
    view_classify();
    if (view_bank) SWITCH_ROM(view_bank);
    view_copy240(view_buf, view_bg);
    view_paint();
    if (view_bank) SWITCH_ROM(saved);
}

// C reference of view_compose (selftest: same view_buf for random positions on the game's map)
void view_compose_c(uint8_t x, uint8_t y, uint8_t f) {
    uint8_t i, c, d, k, saved = CURRENT_BANK, bit = 1, by = 0, cls[19], solid[3];
    const int8_t *ox = view_lay_ox[f & 3], *oy = view_lay_oy[f & 3];
    const uint8_t *m, *end;
    solid[0] = solid[1] = solid[2] = 0;
    for (i = 0; i < sizeof(view_lay_p); i++) {
        c = cls[i] = view_cell(x + ox[i], y + oy[i]);
        if (c != VIEW_FREE) solid[by] |= bit;
        if (!(bit <<= 1)) { bit = 1; by++; }
    }
    if (view_bank) SWITCH_ROM(view_bank);
    view_copy240(view_buf, view_bg);
    for (i = 0; i < sizeof(view_lay_p); i++) {
        c = cls[i];
        if (c == VIEW_FREE) continue;
        m = view_occ + view_occ_first[i] * 3;
        end = view_occ + view_occ_first[i + 1] * 3;
        for (k = 0; m < end; m += 3)
            if ((solid[0] & m[0]) == m[0] && (solid[1] & m[1]) == m[1] && (solid[2] & m[2]) == m[2]) { k = 1; break; }
        if (k) continue;                                  // hidden behind nearer walls
        d = view_lay_d[i];
        if (view_lay_l[i] == 0 && d) {
            if (c == VIEW_DOOR || c == VIEW_LOCKED || c == VIEW_UP) BLIT(view_door_p[d]);
            else if (c == VIEW_DOWN) BLIT(view_stair_p[d]);
            else BLIT(view_lay_p[i]);
            if (c == VIEW_LOCKED || c == VIEW_UP) BLIT(view_lock_p[d]);
        } else {
            BLIT(view_lay_p[i]);
        }
    }
    if (view_bank) SWITCH_ROM(saved);
}

// Only the background piece (ceiling / darkness / floor): margins of the map for slides and bobs
void view_compose_bg(void) {
    uint8_t saved = CURRENT_BANK;
    if (view_bank) SWITCH_ROM(view_bank);
    BLIT(VIEW_P_BG);
    if (view_bank) SWITCH_ROM(saved);
    view_copy240(view_bg, view_buf);
}
