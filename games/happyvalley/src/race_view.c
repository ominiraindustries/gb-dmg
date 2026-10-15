// HAPPY VALLEY - the race seen from above over a big oval (user's choice): the track is a gbe_world map
// (res/maps/hv.map, st.map, generated with the path tables by design/gen_track.py from tests/hv_geom.py);
// the camera follows the focus horse; each runner is placed from its course table (a point every 8 m,
// interpolated) plus its lane offset along the track normal. Horses are 8x16 sprites (box over the
// saddlecloth digit, greybox). Bank 1 (calls the bank-0 race and world code). Window rows 15-17 = HUD (monospace digits) + commentary (gbe_vwf).
#pragma bank 255
#include "hv.h"
#include "greybox.h"
#include "font_mini.h"
#include "metatiles.h"
#include "track_data.h"

#define SPR_HORSE  0                            // 8x16 sprite pairs: horse k = tiles 2k (box), 2k+1 (digit)
#define COMMENT_T  16                           // text slot: HUD 0-15 (unused), comment lines 16-53
#define LINE_W     19
#define RV_VIEW_H     120                          // track rows above the window
#define BGT(n)     ((uint8_t *)((n) < 128 ? 0x9000 + ((uint16_t)(n) << 4) : 0x8800 + ((uint16_t)((n) - 128) << 4)))
enum { RV_GATES, RV_RUN, RV_AFTER, RV_DONE };

int16_t cam, cam_cx, cam_cy;                    // camera asked of gbe_world (world px of the top-left)
uint8_t rv_phase, rv_t, rv_focus, rv_mode, rv_leader, rv_lead_t, rv_rot;
uint8_t rv_said;                                // commentary already said (bits)
uint16_t rv_x[RN_MAX], rv_y[RN_MAX];            // world px of each runner this frame
uint8_t rv_cs, rv_sec, rv_min;                  // race clock (ticks x 4 cs), counted, not divided
static const char *say_s;                       // commentary typed 1 letter per frame
static uint8_t say_k, say_x;
static uint8_t line_buf[LINE_W * 16];
uint8_t track_pts[TRACK_MAX_POINTS * 5];        // the course's path table (x16 y16 h), copied at build
uint16_t track_n;
char rv_text[40];

// ---------------------------------------------------------------- commentary (2 proportional lines)
static void say(const char *s) {
    if (s != rv_text) { strcpy(rv_text, s); }
    vwf_clear(line_buf, LINE_W);
    say_s = rv_text; say_k = 0; say_x = 1;
}

// one letter per frame (GDD 5.1 typewriter): a whole line at once cost 140k T
static void type_letter(void) {
    char c[2];
    if (!say_s) return;
    c[0] = say_s[say_k]; c[1] = 0;
    if (!c[0]) { say_s = 0; return; }
    say_x = vwf_draw(line_buf, LINE_W, say_x, c);
    say_k++;
    tiles_push(BGT(VRAM_TEXT + COMMENT_T), 1, line_buf, LINE_W);
}

static char *put_num(char *d, uint8_t v) {
    if (v >= 10) *d++ = '0' + v / 10;
    *d++ = '0' + v % 10;
    return d;
}

static void say_num(const char *a, uint8_t n, const char *b) {
    char *d = rv_text;
    while (*a) *d++ = *a++;
    d = put_num(d, n);
    while (*b) *d++ = *b++;
    *d = 0;
    say(rv_text);
}


void commentary(void) {
    uint8_t lead = order[0];
    uint16_t rem = rx[lead].pos < race_d16 ? (race_d16 - rx[lead].pos) >> 4 : 0;
    if (rv_phase == RV_RUN && !(rv_said & 1)) { rv_said |= 1; say("\xA1Salen!"); return; }
    if (lead != rv_leader) { rv_leader = lead; rv_lead_t = 0; }
    else if (rv_lead_t < 255 && ++rv_lead_t == 32 && race_t > 64) { say_num("Manda el ", lead + 1, ""); return; }
    if (!(rv_said & 2) && rx[lead].pos >= race_final_from) { rv_said |= 2; say("Entran en la recta"); return; }
    if (!(rv_said & 4) && rem <= 400) { rv_said |= 4; say("Quedan 400 metros"); return; }
    if (!(rv_said & 8) && race_nfin) { rv_said |= 8; say_num("\xA1Gana el ", race_winner() + 1, "!"); }
}

// ---------------------------------------------------------------- HUD: "1200M  0:52.40"
static void clock_tick(void) {                  // + 4 centiseconds
    rv_cs += 4;
    if (rv_cs >= 100) { rv_cs -= 100; rv_sec++; if (rv_sec >= 60) { rv_sec = 0; rv_min++; } }
}

static uint8_t *digits2(uint8_t *t, uint8_t v) { // 2 digits with a leading zero, no division
    uint8_t d = 0;
    while (v >= 10) { v -= 10; d++; }
    t[0] = VRAM_FONT_MINI + FONT_MINI_DIGIT0 + d;
    t[1] = VRAM_FONT_MINI + FONT_MINI_DIGIT0 + v;
    return t + 2;
}

void hud(void) {
    uint8_t t[16], lead = order[0], k, d;
    uint16_t rem = rx[lead].pos < race_d16 ? (race_d16 - rx[lead].pos) >> 4 : 0;
    static const uint16_t pw[4] = { 1000, 100, 10, 1 };
    memset(t, VRAM_TEXT, 16);                   // text tile 0 of the slot stays blank
    for (k = 0; k < 4; k++) {                   // metres to go, 4 digits by subtraction
        for (d = 0; rem >= pw[k]; d++) rem -= pw[k];
        t[1 + k] = VRAM_FONT_MINI + FONT_MINI_DIGIT0 + d;
    }
    t[5] = VRAM_FONT_MINI + GBE_FONT_LETTER_A + ('M' - 'A');
    t[8] = VRAM_FONT_MINI + FONT_MINI_DIGIT0 + rv_min;
    t[9] = VRAM_FONT_MINI + FONT_MINI_COLON;
    digits2(t + 10, rv_sec);
    t[12] = VRAM_FONT_MINI + FONT_MINI_DOT;
    digits2(t + 13, rv_cs);
    vq_push((uint8_t *)0x9C00, t, 16);
}


// ---------------------------------------------------------------- runners on the oval
static int8_t sin_tab[64];

// world px of runner k: the course table point at its metre (interpolated) + lane x the track normal
static void place(uint8_t k) {
    runner_t *r = &rx[k];
    uint16_t p = r->pos, idx = p >> 7, last = track_n - 1;
    uint8_t f = (uint8_t)(p & 127), h, *a;
    int16_t x, y, off;
    if (idx >= last) {                          // past the post: straight on (east, the home straight)
        a = track_pts + (last << 2) + last;
        x = a[0] | (a[1] << 8); y = a[2] | (a[3] << 8); h = a[4];
        x += (p - (last << 7)) >> 2;
    } else {
        a = track_pts + (idx << 2) + idx;
        x = a[0] | (a[1] << 8); y = a[2] | (a[3] << 8); h = a[4];
        x += ((int16_t)((a[5] | (a[6] << 8)) - x) * f) >> 7;
        y += ((int16_t)((a[7] | (a[8] << 8)) - y) * f) >> 7;
    }
    off = r->lane * TRACK_LANE_PX;              // outward = (sin h, -cos h)
    x += (sin_tab[h] * off) >> 6;
    y -= (sin_tab[(h + 16) & 63] * off) >> 6;
    rv_x[k] = x; rv_y[k] = y;
}

void sprites(void) {
    uint8_t k, n, i;
    uint16_t sx, sy;
    OAM_item_t *o = shadow_OAM;
    i = rv_rot;                                 // rotating start: >10 per line flicker, never vanish
    for (n = rn_n; n; n--) {
        k = i;
        if (++i >= rn_n) i = 0;
        sx = rv_x[k] - cam_x + 4;               // OAM x = screen x - 4 + 8
        sy = rv_y[k] - cam_y + 8;               // OAM y = screen y - 8 + 16
        if (sx >= 168 || sy >= RV_VIEW_H + 8 || sy < 8) continue;
        o->y = (uint8_t)sy; o->x = (uint8_t)sx; o->tile = SPR_HORSE + (k << 1); o->prop = 0; o++;
    }
    while (o < shadow_OAM + 40) { o->y = 0; o++; }
    if (++rv_rot >= rn_n) rv_rot = 0;
}

// camera centred on the focus, clamped to the map, at most 8 px per frame per axis (gbe_world: 16)
static int16_t towards(int16_t v, int16_t to) {
    if (v < to) return to - v > 8 ? v + 8 : to;
    if (v > to) return v - to > 8 ? v - 8 : to;
    return v;
}

static int16_t cam_tx, cam_ty;
static void cam_target(void) {
    int16_t mw = (int16_t)wmap.w << 8, mh = (int16_t)wmap.h << 8;
    cam_tx = (int16_t)rv_x[rv_focus] - 80;
    cam_ty = (int16_t)rv_y[rv_focus] - 60;
    if (cam_tx < 0) cam_tx = 0; else if (cam_tx > mw - 160) cam_tx = mw - 160;
    if (cam_ty < 0) cam_ty = 0; else if (cam_ty > mh - RV_VIEW_H) cam_ty = mh - RV_VIEW_H;
}

void camera(void) {
    cam_target();
    cam_cx = towards(cam_cx, cam_tx);
    cam_cy = towards(cam_cy, cam_ty);
}

// ---------------------------------------------------------------- build (LCD off) and frame
void rv_build(void) BANKED {
    uint8_t c, k;
    track_ref_t tr;
    bank_set_bkg_data(BANK(greybox), VRAM_GREYBOX, GREYBOX_COUNT, greybox_tiles);
    bank_set_bkg_data(BANK(font_mini), VRAM_FONT_MINI, FONT_MINI_COUNT, font_mini_tiles);
    for (k = 0; k < RN_MAX; k++) {              // horse k: box over its saddlecloth digit
        bank_set_sprite_data(BANK(greybox), SPR_HORSE + (k << 1), 1, greybox_tiles + (GREYBOX_BOX << 4));
        bank_set_sprite_data(BANK(font_mini), SPR_HORSE + (k << 1) + 1, 1, font_mini_tiles + (((k + 1) % 10) << 4));
    }
    bank_memcpy(BANK(track_data), &tr, &track_index[race_course], sizeof(tr));
    track_n = tr.n;
    bank_memcpy(BANK(track_data), track_pts, tr.pts, tr.n * 5);
    bank_memcpy(BANK(track_data), sin_tab, sine64, 64);
    vwf_clear(line_buf, LINE_W);                // text slot: blank tile 0, two empty comment lines
    set_bkg_data(VRAM_TEXT, 1, line_buf);
    set_bkg_data(VRAM_TEXT + COMMENT_T, LINE_W, line_buf);
    set_bkg_data(VRAM_TEXT + COMMENT_T + LINE_W, LINE_W, line_buf);
    for (c = 0; c < 32; c++) {
        *((uint8_t *)0x9C00 + c) = VRAM_TEXT;
        *((uint8_t *)0x9C20 + c) = c < LINE_W ? VRAM_TEXT + COMMENT_T + c : VRAM_TEXT;
        *((uint8_t *)0x9C40 + c) = c < LINE_W ? VRAM_TEXT + COMMENT_T + LINE_W + c : VRAM_TEXT;
    }
    for (k = 0; k < rn_n; k++) place(k);
    rv_mode = 0;
    rv_focus = order[0];
    world_metatiles(BANK(metatiles), mt_tiles[0], mt_attr, MT_COUNT);
    world_load_id(tr.map, 0, 0, 0, 0);          // map header first (its size clamps the camera)
    cam_target();
    cam_cx = cam_tx; cam_cy = cam_ty;
    world_load_id(tr.map, (uint8_t)(rv_x[rv_focus] >> 4), (uint8_t)(rv_y[rv_focus] >> 4), cam_cx, cam_cy);
    rv_phase = RV_GATES; rv_t = 0; rv_said = 0; rv_leader = 0xFF; rv_lead_t = 0; rv_rot = 0;
    rv_cs = rv_sec = rv_min = 0;
    say_s = 0;
    txt_font = VRAM_FONT_MINI;
    WX_REG = 7; WY_REG = RV_VIEW_H;
    SPRITES_8x16;
    SHOW_BKG; SHOW_WIN; SHOW_SPRITES;
}

// once per frame; returns 1 when the race scene is over
uint8_t rv_update(void) BANKED {
    uint8_t k;
    if (rv_phase == RV_GATES) { if (++rv_t >= 60) { rv_phase = RV_RUN; rv_t = 0; } }
    else if (rv_phase == RV_RUN) {
        if (pressed & J_START) { rv_phase |= 0x80; return 0; }   // pause
        for (k = (keys & J_B) ? 3 : 1; k && !race_done; k--) { race_tick(); clock_tick(); }
        if (race_done) { rv_phase = RV_AFTER; rv_t = 0; }
    } else if (rv_phase == (RV_RUN | 0x80)) { if (pressed & J_START) rv_phase = RV_RUN; return 0; }
    else if (rv_phase == RV_AFTER) { if (++rv_t >= 60) rv_phase = RV_DONE; }
    else return 1;
    if (pressed & J_A) rv_mode ^= 1;            // camera: the leader / the last one (M1b: your horse)
    rv_focus = rv_mode ? order[rn_n - 1] : order[0];
    for (k = 0; k < rn_n; k++) place(k);
    camera();
    world_update((uint8_t)(rv_x[rv_focus] >> 4), (uint8_t)(rv_y[rv_focus] >> 4), cam_cx, cam_cy);
    if (!say_s && (!(rv_t & 15) || rv_phase == RV_RUN)) commentary();
    type_letter();
    if (!(race_t & 7)) hud();
    sprites();
    return 0;
}
