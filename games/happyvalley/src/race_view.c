// HAPPY VALLEY - the race seen by a side-on TV camera (GDD v1.1 5.1, greybox). Every course is a straight
// (user: "mucho lio, solo una recta": bends and the bend camera cut were dropped; the game's weight is
// the management). Inner rail in front (low), outer lanes higher, the stands and the city behind.
// BG bands moved with raster SCX splits (gbe_raster): skyline (x1/32), stands (x1/2), the track band
// (x1), the near rail (x1.25). One unique visual row per runner (rank by lane then gate, eased 1 px per
// frame). Window rows 14-17: HUD, 2 commentary lines (gbe_vwf), the mini-map (a progress bar,
// double-buffered tiles). The race model runs RV_PER_FRAME runners per frame (fields of 8: a tick
// per frame, x2.4 real time; user: "carreras mas rapidas"); B runs 3 ticks per frame.
// Scale 4 px = 1 m. Bank 1.
#pragma bank 255
#include "hv.h"
#include "greybox.h"
#include "font_mini.h"
#include "minimap_data.h"

#define T(n)        (VRAM_GREYBOX + GREYBOX_##n)
#define BGT(n)      ((uint8_t *)((n) < 128 ? 0x9000 + ((uint16_t)(n) << 4) : 0x8800 + ((uint16_t)((n) - 128) << 4)))
#define SPR_BODY    0                           // 8x16 sprite pairs: body = BOX/BOX, head k = digit/BOX
#define SPR_HEAD    2
#define SPR_POST    (SPR_HEAD + 2 * RN_MAX)          // 3 post kinds (gates, marks, finish), 8x16 pairs
#define TXT_COMMENT (VRAM_TEXT + 0)             // text slot: comment 2 x 13, mini-map 2 x 24 (double buffer)
#define TXT_MM_A    (VRAM_TEXT + 26)
#define TXT_MM_B    (VRAM_TEXT + 50)
#define LINE_W      13
#define RV_PER_FRAME 8                          // runner moves per frame (~3.4k T each with think): a whole tick
enum { RV_GATES, RV_RUN, RV_AFTER, RV_DONE };

int16_t cam;                                    // world px (4 per m) of the screen's left edge, track band
uint8_t rv_phase, rv_t, rv_focus, rv_mode, rv_cur, rv_leader, rv_lead_t, rv_rot;   // cur: next runner to move
uint8_t rv_said, rv_v[RN_MAX], rv_y[RN_MAX], rv_idx[RN_MAX], rv_want[RN_MAX];   // want: feet y of the row
uint8_t rv_cs, rv_sec, rv_min;
uint8_t rv_mm_buf[24 * 16], rv_mm_on, rv_mm_ready;   // image being built / buffer shown / built
static mm_ref_t mm;
static uint8_t mm_path_copy[2 * 160];           // the course's mini-map path (<= 2400 m / 16 + 2 points)
static uint8_t mm_base_copy[24 * 16];
static uint16_t post_x[7];                      // world px of the gates, the 1000-200 m posts, the finish
static uint8_t post_tile[7], post_n;            // tile: the sprite pair
static uint8_t line_buf[LINE_W * 16];
static const char *say_s;
static uint8_t say_k, say_x, say_x0;
char rv_text[40];
uint8_t spr_check, spr_mismatch;                // tests: run sprites_c and the asm on the same state
static uint8_t spr_ref[160], spr_y[RN_MAX];

// ---------------------------------------------------------------- the BG (rows 0-13, 32 columns)
static uint8_t band_tile(uint8_t r, uint8_t c) {
    static const uint8_t sky_h[16] = { 3, 2, 3, 3, 1, 2, 3, 2, 3, 3, 2, 1, 3, 2, 2, 3 };   // towers
    uint8_t h;
    if (r < 3) {                                // skyline: towers on the stands side, hills opposite
        h = c < 16 ? sky_h[c] : (c & 7) < 4 ? 1 : 0;
        return r >= 3 - h ? (c < 16 ? T(SOLID) : T(GRAY)) : T(BLANK);
    }
    if (r < 5) return ((r + c) & 1) ? T(GRAY) : T(DOOR);    // stands: the crowd
    if (r == 5 || r == 13) return (c & 3) == 3 ? T(GRAY) : T(WALL);   // rails
    return (c & 7) == 0 ? T(GRAY) : T(FLOOR);   // turf + a mowing stripe every 64 px
}

// Posts are sprites (OAM 32-39, 4 x 8x16 = rows 5-12, at most 2 on screen): as BG columns they were 9
// one-tile vq entries each and the race's short VBlank could not drain them (vq_lost). After sprites().
void posts(void) {                              // pointers: indexed u16 arrays cost ~800 T per post
    uint8_t k, n = 2, y, x, t;
    uint16_t c = (uint16_t)cam - 8, sx;
    const uint16_t *px = post_x;
    const uint8_t *pt = post_tile;
    OAM_item_t *o = shadow_OAM + 32;
    for (k = post_n; k && n; k--, px++, pt++) {
        sx = *px - c;                           // OAM x of the pole
        if (sx >= 168) continue;
        x = (uint8_t)sx; t = *pt;
        for (y = 56; y < 120; y += 16) { o->y = y; o->x = x; o->tile = t; o->prop = 0; o++; }
        n--;
    }
}

// ---------------------------------------------------------------- commentary (2 lines, proportional)
static void say(const char *s) {
    if (s != rv_text) strcpy(rv_text, s);
    vwf_clear(line_buf, LINE_W);
    say_s = rv_text; say_k = 0; say_x = 1;
}

void type_letter(void) {                 // 1 letter (rv_update: every 2 frames, the tile queue's pace)
    char c[2];
    uint8_t a, b;
    if (!say_s) return;
    c[0] = say_s[say_k]; c[1] = 0;
    if (!c[0]) { say_s = 0; return; }
    say_x0 = say_x;                             // a static: SDCC 4.5 (max-allocs 50000) lost a local
    say_x = vwf_draw(line_buf, LINE_W, say_x, c);   // computed before this BANKED call (gbdk gotchas)
    say_k++;
    a = say_x0 >> 3;                            // only the 1-2 tiles the letter touched (the whole
                                                // line every letter flooded the tile queue)
    b = say_x > 0 ? (say_x - 1) >> 3 : 0;
    if (b >= LINE_W) b = LINE_W - 1;
    tiles_push(BGT(TXT_COMMENT + a), 1, line_buf + (a << 4), b - a + 1);
}

static void say_num(const char *a, uint8_t n, const char *b) {
    char *d = rv_text;
    while (*a) *d++ = *a++;
    if (n >= 10) *d++ = '0' + n / 10;
    *d++ = '0' + n % 10;
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
    if (!(rv_said & 2) && crs.nseg > 1 && rx[lead].pos >= race_final_from) { rv_said |= 2; say("Entran en la recta"); return; }
    if (!(rv_said & 4) && rem <= 400) { rv_said |= 4; say("Quedan 400 m"); return; }
    if (!(rv_said & 8) && race_nfin) { rv_said |= 8; say_num("\xA1Gana el ", race_winner() + 1, "!"); }
}

// ---------------------------------------------------------------- HUD (window rows 14-15)
static void clock_tick(void) {
    rv_cs += 4;
    if (rv_cs >= 100) { rv_cs -= 100; rv_sec++; if (rv_sec >= 60) { rv_sec = 0; rv_min++; } }
}

static void digits2(uint8_t *t, uint8_t v) {
    uint8_t d = 0;
    while (v >= 10) { v -= 10; d++; }
    t[0] = VRAM_FONT_MINI + FONT_MINI_DIGIT0 + d;
    t[1] = VRAM_FONT_MINI + FONT_MINI_DIGIT0 + v;
}

void hud(uint8_t row) {                        // row 0: metres to go + time; row 1: place / runners
    uint8_t t[14], lead = order[0], k, d;
    uint16_t rem;
    static const uint16_t pw[4] = { 1000, 100, 10, 1 };
    memset(t, T(BLANK), 14);
    if (!row) {
        rem = rx[lead].pos < race_d16 ? (race_d16 - rx[lead].pos) >> 4 : 0;
        for (k = 0; k < 4; k++) {
            for (d = 0; rem >= pw[k]; d++) rem -= pw[k];
            t[k] = VRAM_FONT_MINI + FONT_MINI_DIGIT0 + d;
        }
        t[4] = VRAM_FONT_MINI + GBE_FONT_LETTER_A + ('M' - 'A');
        t[6] = VRAM_FONT_MINI + FONT_MINI_DIGIT0 + rv_min;
        t[7] = VRAM_FONT_MINI + FONT_MINI_COLON;
        digits2(t + 8, rv_sec);
        t[10] = VRAM_FONT_MINI + FONT_MINI_DOT;
        digits2(t + 11, rv_cs);
        vq_push((uint8_t *)0x9C00, t, 14);
    } else {
        digits2(t, rx[rv_focus].rank + 1);
        t[2] = VRAM_FONT_MINI + FONT_MINI_SLASH;
        digits2(t + 3, rn_n);
        t[6] = VRAM_FONT_MINI + GBE_FONT_LETTER_A + (rv_mode ? 'U' - 'A' : 'L' - 'A');   // camera: L leader / U last
        vq_push((uint8_t *)0x9C20, t, 14);
    }
}

// ---------------------------------------------------------------- mini-map (window cols 14-19)
static void mm_dot(uint8_t x, uint8_t y) {      // 2x2 px of colour 3
    uint8_t *p, m, k;
    for (k = 0; k < 2; k++, y++) {
        p = rv_mm_buf + ((uint16_t)((y >> 3) * 6 + (x >> 3)) << 4) + ((y & 7) << 1);
        m = 0x80 >> (x & 7);
        p[0] |= m; p[1] |= m;
        if ((x & 7) == 7) { p += 16; m = 0x80; } else m >>= 1;
        p[0] |= m; p[1] |= m;
    }
}

static uint8_t mm_index_of(uint8_t k) {
    uint16_t rem = rx[k].pos < race_d16 ? (race_d16 - rx[k].pos) >> 4 : 0;   // metres to go
    uint8_t idx = (uint8_t)(rem >> MM_STEP_SH);
    return idx >= mm.n ? mm.n - 1 : idx;
}

static void mm_dots(uint8_t from, uint8_t to) {
    uint8_t k, idx, x, y;
    for (k = from; k < to; k++) {
        idx = mm_index_of(k) << 1;
        x = mm_path_copy[idx]; y = mm_path_copy[idx + 1];
        mm_dot(x, y);
    }
}

// m = rv_t & 63, the heavy steps on even frames free of rows/hud (rv_update's schedule): 4 base,
// 8 and 10 dots, 13-23 (odd) tiles to the hidden buffer (4 a time), 44 show
// it once the tiles are in VRAM. While built and not shown the buffer is kept (the queue points into it).
void minimap(uint8_t m) {
    uint8_t tile0 = rv_mm_on ? TXT_MM_B : TXT_MM_A, half = rn_n >> 1, t[6], r, c;   // the hidden one
    if (m == 44) {
        if (!rv_mm_ready || tiles_pending()) return;
        for (r = 0; r < 4; r++) {
            for (c = 0; c < 6; c++) t[c] = tile0 + r * 6 + c;
            vq_push((uint8_t *)0x9C00 + gbe_row32(r) + 14, t, 6);
        }
        rv_mm_on ^= 1;
        rv_mm_ready = 0;
    } else if (rv_mm_ready) return;
    else if (m == 4) memcpy(rv_mm_buf, mm_base_copy, sizeof(rv_mm_buf));
    else if (m == 8) mm_dots(0, half);
    else if (m == 10) mm_dots(half, rn_n);
    else if (m >= 13 && m <= 23 && (m & 1)) {   // runs of 4 (a run of 24 held the queue's head and
        c = (m - 13) >> 1;                      // the letters behind it got lost)
        tiles_push(BGT(tile0 + (c << 2)), 1, rv_mm_buf + (c << 6), 4);
        if (c == 5) rv_mm_ready = 1;
    }
}

// ---------------------------------------------------------------- rows, sprites, camera
void rows(void) {
    uint8_t k, j, a, key[RN_MAX];
    for (k = 0; k < rn_n; k++) key[k] = (rx[k].lane << 4) + rn_gate[k];
    for (k = 1; k < rn_n; k++) {                // outside first (v = 0 the outermost)
        a = rv_idx[k];
        for (j = k; j && key[a] > key[rv_idx[j - 1]]; j--) rv_idx[j] = rv_idx[j - 1];
        rv_idx[j] = a;
    }
    for (k = 0; k < rn_n; k++) { a = rv_idx[k]; rv_v[a] = k; rv_want[a] = 102 - 7 * (rn_n - 1 - k); }   // 8 rows over the turf
}

// the specification of sprites() (race_spr.s); race_use_c picks this one (test_view_sprites)
void sprites_c(void) {
    uint8_t n, k, i, feet, want;
    uint16_t sx;
    OAM_item_t *o = shadow_OAM;
    i = rv_rot;
    for (n = rn_n; n; n--) {                    // nearest row first, rotating start (flicker, not vanish)
        k = rv_idx[(uint8_t)(rn_n - 1 - i)];
        if (++i >= rn_n) i = 0;
        want = rv_want[k];
        feet = rv_y[k];
        if (feet < want) feet++; else if (feet > want) feet--;
        rv_y[k] = feet;
        sx = (rx[k].pos >> 2) - (uint16_t)cam + 8;   // OAM x of the body (nose = +16)
        if (sx >= 168) continue;
        o->y = feet + 1; o->x = (uint8_t)sx; o->tile = SPR_BODY; o->prop = 0; o++;
        o->y = feet + 1; o->x = (uint8_t)sx + 8; o->tile = SPR_HEAD + (k << 1); o->prop = 0; o++;
    }
    while (o < shadow_OAM + 40) { o->y = 0; o++; }
    if (++rv_rot >= rn_n) rv_rot = 0;
}

void camera(void) {
    int16_t f = (int16_t)(rx[rv_focus].pos >> 2) + 16, lead = (int16_t)(rx[order[0]].pos >> 2) + 16, obj = f - 88, d;
    if (lead - obj > 152) obj = lead - 152 < f - 24 ? lead - 152 : f - 24;
    d = obj - cam;
    cam += d > 6 ? 6 : d < -6 ? -6 : d;
}

// SCX per band (gbe_raster): line 0 skyline (scx_shadow), 24 stands, 40 track, 104 near rail
void raster(void) {
    uint8_t c = (uint8_t)cam;
    scx_shadow = (uint8_t)(cam >> 5);
    raster_line[0] = 24; raster_scx[0] = (uint8_t)(cam >> 1);
    raster_line[1] = 40; raster_scx[1] = c;
    raster_line[2] = 104; raster_scx[2] = c + (uint8_t)(cam >> 2);
    raster_n = 3;
    raster_commit();
}

// ---------------------------------------------------------------- build (LCD off) and frame
void rv_build(void) BANKED {
    uint8_t r, c, k;
    static const uint16_t marks[5] = { 1000, 800, 600, 400, 200 };
    bank_set_bkg_data(BANK(greybox), VRAM_GREYBOX, GREYBOX_COUNT, greybox_tiles);
    bank_set_bkg_data(BANK(font_mini), VRAM_FONT_MINI, FONT_MINI_COUNT, font_mini_tiles);
    bank_set_sprite_data(BANK(greybox), SPR_BODY, 1, greybox_tiles + (GREYBOX_BOX << 4));
    bank_set_sprite_data(BANK(greybox), SPR_BODY + 1, 1, greybox_tiles + (GREYBOX_BOX << 4));
    for (k = 0; k < 6; k++)                     // posts: gates BOX, marks DOOR, finish CHECK
        bank_set_sprite_data(BANK(greybox), SPR_POST + k, 1,
                             greybox_tiles + ((k < 2 ? GREYBOX_BOX : k < 4 ? GREYBOX_DOOR : GREYBOX_CHECK) << 4));
    for (k = 0; k < RN_MAX; k++) {              // head k: dorsal (1-9, then A-E for 10-14) over a box
        c = k < 9 ? GBE_FONT_DIGIT0 + k + 1 : GBE_FONT_LETTER_A + k - 9;
        bank_set_sprite_data(BANK(font_mini), SPR_HEAD + (k << 1), 1, font_mini_tiles + (c << 4));
        bank_set_sprite_data(BANK(greybox), SPR_HEAD + (k << 1) + 1, 1, greybox_tiles + (GREYBOX_BOX << 4));
    }
    for (r = 0; r < 14; r++)
        for (c = 0; c < 32; c++) *((uint8_t *)0x9800 + gbe_row32(r) + c) = band_tile(r, c);
    vwf_clear(line_buf, LINE_W);                // window: HUD rows 0-1, comment rows 2-3, mini-map cols 14-19
    set_bkg_data(TXT_COMMENT, LINE_W, line_buf);
    set_bkg_data(TXT_COMMENT + LINE_W, LINE_W, line_buf);
    for (r = 0; r < 4; r++)
        for (c = 0; c < 32; c++) *((uint8_t *)0x9C00 + gbe_row32(r) + c) = T(BLANK);
    for (c = 0; c < LINE_W; c++) {
        *((uint8_t *)0x9C40 + c) = TXT_COMMENT + c;
        *((uint8_t *)0x9C60 + c) = TXT_COMMENT + LINE_W + c;
    }
    bank_memcpy(BANK(minimap_data), &mm, &mm_index[race_course], sizeof(mm));
    bank_memcpy(BANK(minimap_data), mm_base_copy, mm.base, sizeof(mm_base_copy));
    bank_memcpy(BANK(minimap_data), mm_path_copy, mm.path, mm.n << 1);
    set_bkg_data(TXT_MM_A, 24, mm_base_copy);
    rv_mm_ready = 0;
    tiles_budget = 2;                           // VBlank left after vsync() in the race: ~5 lines (main.c)
    for (r = 0; r < 4; r++)
        for (c = 0; c < 6; c++) *((uint8_t *)0x9C00 + gbe_row32(r) + 14 + c) = TXT_MM_A + r * 6 + c;
    rv_mm_on = 1;                               // A shown (rv_mm_on = 1: A), B hidden
    post_n = 0;                                 // gates, posts at 1000-200 m to go, the finish
    post_x[post_n] = 16; post_tile[post_n++] = SPR_POST;
    for (k = 0; k < 5; k++)
        if (marks[k] < crs.dist) { post_x[post_n] = (crs.dist - marks[k]) << 2; post_tile[post_n++] = SPR_POST + 2; }
    post_x[post_n] = (crs.dist << 2) + 16; post_tile[post_n++] = SPR_POST + 4;
    for (k = 0; k < rn_n; k++) rv_idx[k] = k;
    rows();
    for (k = 0; k < rn_n; k++) rv_y[k] = rv_want[k];
    rv_mode = 0; rv_focus = order[0];
    cam = -72;
    rv_phase = RV_GATES; rv_t = 0; rv_said = 0; rv_leader = 0xFF; rv_lead_t = 0; rv_rot = 0; rv_cur = 0;
    rv_cs = rv_sec = rv_min = 0;
    say_s = 0;
    txt_font = VRAM_FONT_MINI;
    scy_shadow = 0;
    raster();
    WX_REG = 7; WY_REG = 112;
    SPRITES_8x16;
    SHOW_BKG; SHOW_WIN; SHOW_SPRITES;
}

// once per frame; returns 1 when the race scene is over
uint8_t rv_update(void) BANKED {
    uint8_t k, n, budget;
    if (rv_phase == RV_GATES) { if (++rv_t >= 40) { rv_phase = RV_RUN; rv_t = 0; } }
    else if (rv_phase == RV_RUN) {
        if (pressed & J_START) { rv_phase |= 0x80; return 0; }
        budget = (keys & J_B) ? rn_n * 3 : RV_PER_FRAME;    // B: 3 ticks per frame
        while (budget && !race_done) {          // runners in index order: same result as whole ticks
            n = rn_n - rv_cur;
            if (n > budget) n = budget;
            race_runners_range(rv_cur, rv_cur + n);
            rv_cur += n; budget -= n;
            if (rv_cur >= rn_n) { race_tick_end(); clock_tick(); rv_cur = 0; }
        }
        if (race_done) { rv_phase = RV_AFTER; rv_t = 0; }
    } else if (rv_phase == (RV_RUN | 0x80)) { if (pressed & J_START) rv_phase = RV_RUN; return 0; }
    else if (rv_phase == RV_AFTER) { if (++rv_t >= 45) rv_phase = RV_DONE; }
    else return 1;
    rv_t++;
    if (pressed & J_A) rv_mode ^= 1;            // camera: the leader / the last one (M1b: your horse)
    rv_focus = rv_mode ? order[rn_n - 1] : order[0];
    camera();
    raster();
    k = rv_t & 15;                              // one heavy job (~10k T) per even frame, letters on odd
    if (k == 0) rows();                         // ones; the race takes ~34k T of every frame
    else if (k == 2) hud(0);
    else if (k == 6) hud(1);
    else if (k == 14 && !say_s) commentary();  // even: not with a letter (odd frames)
    minimap(rv_t & 63);                         // even frames 4, 8, 10, 12 (mod 16): a refresh per 64
    if (rv_t & 1) type_letter();
    if (spr_check) {                            // equivalence: C, then asm from the same state
        memcpy(spr_y, rv_y, RN_MAX); k = rv_rot;
        sprites_c();
        memcpy(spr_ref, shadow_OAM, 160);
        memcpy(rv_y, spr_y, RN_MAX); rv_rot = k;
        sprites();
        if (memcmp(spr_ref, shadow_OAM, 160)) spr_mismatch++;
    } else sprites();
    posts();
    return 0;
}
