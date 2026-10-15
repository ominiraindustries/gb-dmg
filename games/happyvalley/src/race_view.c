// HAPPY VALLEY - the race seen from above: the track as a small pixel oval (design/gen_track.py), a dot
// per runner (user: the race is "lo de menos"; the game's weight is breeding, markets and management).
// BG rows 0-13: the oval (fixed, loaded with the LCD off). Window rows 14-17 (WY 112): metres to go and
// the clock, the order of the field (dorsals), 2 lines of commentary (gbe_vwf, typed a letter every 4
// frames: ~10k T each, the race takes ~36k of every frame). The race model runs a whole tick per frame (fields of 8: x2.4 real
// time); B runs 3 ticks per frame. Bank: any (the path tables are included here, same bank).
#pragma bank 255
#include "hv.h"
#include "greybox.h"
#include "font_mini.h"
#include "oval_data.h"
#include "oval_path.inc"

#define T(n)        (VRAM_GREYBOX + GREYBOX_##n)
#define BGT(n)      ((uint8_t *)((n) < 128 ? 0x9000 + ((uint16_t)(n) << 4) : 0x8800 + ((uint16_t)((n) - 128) << 4)))
#define LINE_W      20
#define TXT_COMMENT (VRAM_TEXT + 0)             // text slot: comment 2 x 20, then the oval's tiles
#define TXT_OVAL    (VRAM_TEXT + 2 * LINE_W)
#define SPR_DOT     0                           // 8x8 sprites: a 3x3 dot, the leader's ring
#define SPR_LEAD    1
#define RV_PER_FRAME 8                          // runner moves per frame (~3.4k T each with think)
enum { RV_GATES, RV_RUN, RV_AFTER, RV_DONE };

uint8_t rv_phase, rv_t, rv_cur, rv_said, rv_leader, rv_lead_t;   // cur: next runner to move
uint8_t rv_cs, rv_sec, rv_min;
static const uint8_t *path;                     // this track's lap: x, y, nx, ny every 4 m
static uint16_t path_n;
static uint8_t line_buf[LINE_W * 16];
static const char *say_s;
static uint8_t say_k, say_x, say_x0;
char rv_text[40];

// sprite tiles: a 3x3 dot and the leader's 3x3 ring (colour 3), the point at its centre
static const uint8_t dot_tiles[32] = {
    0xE0, 0xE0, 0xE0, 0xE0, 0xE0, 0xE0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0xE0, 0xE0, 0xA0, 0xA0, 0xE0, 0xE0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
};

// ---------------------------------------------------------------- commentary (proportional)
static void say(const char *s) {
    if (s != rv_text) strcpy(rv_text, s);
    vwf_clear(line_buf, LINE_W);
    tiles_push(BGT(TXT_COMMENT), 1, line_buf, LINE_W);   // the old line off (cleared buffer)
    say_s = rv_text; say_k = 0; say_x = 1;
}

void type_letter(void) {                        // 1 letter (every 4 frames)
    char c[2];
    uint8_t a, b;
    if (!say_s) return;
    c[0] = say_s[say_k]; c[1] = 0;
    if (!c[0]) { say_s = 0; return; }
    say_x0 = say_x;                             // a static: SDCC 4.5 (max-allocs 50000) lost a local
    say_x = vwf_draw(line_buf, LINE_W, say_x, c);   // computed before this BANKED call (gbdk gotchas)
    say_k++;
    a = say_x0 >> 3;                            // only the 1-2 tiles the letter touched
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
    else if (rv_lead_t < 255 && ++rv_lead_t == 4 && race_t > 64) { say_num("Manda el ", lead + 1, ""); return; }
    if (!(rv_said & 2) && crs.nseg > 1 && rx[lead].pos >= race_final_from) { rv_said |= 2; say("Entran en la recta"); return; }
    if (!(rv_said & 4) && rem <= 400) { rv_said |= 4; say("Quedan 400 m"); return; }
    if (!(rv_said & 8) && race_nfin) { rv_said |= 8; say_num("\xA1Gana el ", race_winner() + 1, "!"); }
}

// ---------------------------------------------------------------- HUD (window rows 0-1)
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

void hud(uint8_t row) {                         // row 0: metres to go + time; row 1: the order (dorsals)
    uint8_t t[20], lead = order[0], k, d;
    uint16_t rem;
    static const uint16_t pw[4] = { 1000, 100, 10, 1 };
    memset(t, T(BLANK), 20);
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
        vq_push((uint8_t *)0x9C00, t, 20);
    } else {
        for (k = 0; k < rn_n; k++) t[k << 1] = VRAM_FONT_MINI + FONT_MINI_DIGIT0 + order[k] + 1;
        vq_push((uint8_t *)0x9C20, t, 20);
    }
}

// ---------------------------------------------------------------- the dots
// metres to go -> a path point (one lap of points: long races go round twice), then out by the lane.
// Was 38k T with % 3 and i * 3 (SDCC divides); 4 bytes per point now, still ~2k T per runner in C:
// phase 0-3 updates runners k = phase, phase + 4 (a dot moves a pixel every few frames); 4 = all.
void dots(uint8_t phase) {
    uint8_t k, off, x, y, step = phase < 4 ? 4 : 1, *o;
    uint16_t i;
    const uint8_t *p;
    runner_t *r;
    if (phase >= 4) phase = 0;
    o = (uint8_t *)shadow_OAM + (phase << 2);
    r = rx + phase;
    for (k = phase; k < rn_n; k += step, r += step, o += step << 2) {
        i = r->pos < race_d16 ? (race_d16 - r->pos) >> (4 + OVAL_STEP_SH) : 0;
        if (i >= path_n) { i -= path_n; if (i >= path_n) i -= path_n; }
        p = path + (i << 2);
        off = r->lane;
        off = 2 + (off > 6 ? 3 : off >> 1);    // px out from the rail (the band is 6 px)
        x = p[0]; y = p[1];
        if (p[2] == 1) x += off; else if (p[2]) x -= off;
        if (p[3] == 1) y += off; else if (p[3]) y -= off;
        o[0] = y + 15; o[1] = x + 7;            // OAM: the dot centred on the point
        o[2] = k == order[0] ? SPR_LEAD : SPR_DOT; o[3] = 0;
    }
    if (step == 1) for (; k < 40; k++, o += 4) o[0] = 0;
}

// ---------------------------------------------------------------- build (LCD off) and frame
void rv_build(void) BANKED {
    uint8_t r, c, k;
    oval_t ov;
    bank_set_bkg_data(BANK(greybox), VRAM_GREYBOX, GREYBOX_COUNT, greybox_tiles);
    bank_set_bkg_data(BANK(font_mini), VRAM_FONT_MINI, FONT_MINI_COUNT, font_mini_tiles);
    set_sprite_data(SPR_DOT, 2, dot_tiles);
    bank_memcpy(BANK(oval_data), &ov, &oval_index[crs.track], sizeof(ov));
    bank_set_bkg_data(BANK(oval_data), TXT_OVAL, ov.n, ov.tiles);
    for (r = 0; r < 14; r++) {                  // the oval: BG rows 0-13
        bank_memcpy(BANK(oval_data), (uint8_t *)0x9800 + gbe_row32(r), ov.map + r * 20, 20);
        for (c = 0; c < 20; c++) *((uint8_t *)0x9800 + gbe_row32(r) + c) += TXT_OVAL;
    }
    path = oval_path[crs.track]; path_n = oval_n[crs.track];
    vwf_clear(line_buf, LINE_W);                // window: HUD rows 0-1, comment rows 2-3
    set_bkg_data(TXT_COMMENT, LINE_W, line_buf);
    set_bkg_data(TXT_COMMENT + LINE_W, LINE_W, line_buf);
    for (r = 0; r < 4; r++)
        for (c = 0; c < 20; c++) *((uint8_t *)0x9C00 + gbe_row32(r) + c) = T(BLANK);
    for (c = 0; c < LINE_W; c++) {
        *((uint8_t *)0x9C40 + c) = TXT_COMMENT + c;
        *((uint8_t *)0x9C60 + c) = TXT_COMMENT + LINE_W + c;
    }
    rv_phase = RV_GATES; rv_t = 0; rv_said = 0; rv_leader = 0xFF; rv_lead_t = 0; rv_cur = 0;
    rv_cs = rv_sec = rv_min = 0;
    say_s = 0;
    txt_font = VRAM_FONT_MINI;
    scx_shadow = scy_shadow = 0;
    hide_sprites_range(0, 40);
    dots(4);
    for (k = 0; k < 2; k++) hud(k);
    WX_REG = 7; WY_REG = 112;
    SPRITES_8x8;
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
    else if (rv_phase == RV_AFTER) { if (++rv_t >= 90) rv_phase = RV_DONE; }
    else return 1;
    rv_t++;
    k = rv_t & 15;                              // one job per even frame, letters on odd ones
    if (k == 2) hud(0);
    else if (k == 6 || k == 14) hud(1);
    else if (k == 10 && !say_s) commentary();
    if ((rv_t & 3) == 1) type_letter();         // a letter every 4 frames (~10k T with the race)
    dots(rv_t & 3);
    return 0;
}
