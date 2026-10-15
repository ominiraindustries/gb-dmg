// HAPPY VALLEY - the race seen side-on (GDD 5.1, greybox): BG rows 0-14 = track scrolled with SCX (row 0
// rail with a 64 px pattern, turf below, a periodic 32-column map: only the post columns are written,
// through gbe_vq, when they come in and erased when they leave); one 8 px row per runner (rank by lane
// then gate, eased 1 px/frame); window rows 15-17 = HUD (monospace digits) + 2 commentary lines
// (proportional, gbe_vwf). Scale 1 px = 0.5 m (x = pos >> 3). Camera on the focus (the leader for now).
#include "hv.h"
#include "greybox.h"
#include "font_mini.h"

#define SPR_BOX    GREYBOX_BOX                  // sprite tiles: greybox at 0, digits at SPR_DIGIT
#define SPR_DIGIT  16
#define TRACK_ROWS 15
#define COMMENT_T  16                           // text slot: HUD 0-15 (unused), comment lines 16-53
#define LINE_W     19
#define BGT(n)     ((uint8_t *)((n) < 128 ? 0x9000 + ((uint16_t)(n) << 4) : 0x8800 + ((uint16_t)((n) - 128) << 4)))
enum { RV_GATES, RV_RUN, RV_AFTER, RV_DONE };

int16_t cam, cam_want;                          // world px (0.5 m) of the screen's left edge
uint8_t rv_phase, rv_t, rv_focus, rv_row[RN_MAX], rv_y[RN_MAX], rv_leader, rv_lead_t;
uint8_t rv_said;                                // commentary already said (bits)
uint8_t rv_idx[RN_MAX], rv_d1[RN_MAX], rv_d0[RN_MAX];   // horses by row; dorsal digit tiles (0 = none)
uint8_t rv_cs, rv_sec, rv_min;                  // race clock (ticks x 4 cs), counted, not divided
static const char *say_s;                       // commentary typed 1 letter per frame
static uint8_t say_k, say_x;
static uint16_t post_x[6];                      // world px of the posts (gates, 800-200 m, finish)
static uint8_t post_tile[6], post_n, post_on;
static uint8_t line_buf[LINE_W * 16];
char rv_text[40];

// ---------------------------------------------------------------- BG columns
static void column(uint8_t c, uint8_t tile) {
    uint8_t r, t;
    for (r = 0; r < TRACK_ROWS; r++) {
        t = tile;
        if (tile == 0xFF) t = r ? VRAM_GREYBOX + GREYBOX_FLOOR : VRAM_GREYBOX + ((c >> 2) & 1 ? GREYBOX_GRAY : GREYBOX_WALL);
        vq_push((uint8_t *)0x9800 + ((uint16_t)r << 5) + c, &t, 1);
    }
}

void posts(void) {
    uint8_t k;
    int16_t sx;
    for (k = 0; k < post_n; k++) {
        sx = (int16_t)post_x[k] - cam;
        if (sx > -8 && sx < 168) {
            if (!(post_on & (1 << k))) { post_on |= 1 << k; column((uint8_t)(post_x[k] >> 3) & 31, post_tile[k]); }
        } else if (post_on & (1 << k)) { post_on &= ~(1 << k); column((uint8_t)(post_x[k] >> 3) & 31, 0xFF); }
    }
}

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
    if ((rv_cs += 4) >= 100) { rv_cs -= 100; if (++rv_sec >= 60) { rv_sec = 0; rv_min++; } }
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

// ---------------------------------------------------------------- rows and sprites
// row of each horse = rank by (lane, gate); rv_idx stays almost sorted between calls (cheap insertion)
void rows(void) {
    uint8_t k, j, a, key[RN_MAX];
    for (k = 0; k < rn_n; k++) key[k] = (rx[k].lane << 4) + rn_gate[k];
    for (k = 1; k < rn_n; k++) {
        a = rv_idx[k];
        for (j = k; j && key[a] < key[rv_idx[j - 1]]; j--) rv_idx[j] = rv_idx[j - 1];
        rv_idx[j] = a;
    }
    for (k = 0; k < rn_n; k++) rv_row[rv_idx[k]] = k;

}

void sprites(void) {
    uint8_t k, y, want, x;
    uint16_t sx;
    OAM_item_t *o = shadow_OAM;
    for (k = 0; k < rn_n; k++) {
        want = 8 + (rv_row[k] << 3);
        y = rv_y[k];
        if (y < want) y++; else if (y > want) y--;
        rv_y[k] = y;
        sx = (rx[k].pos >> 3) - (uint16_t)cam + 8;            // OAM x of the box (the horse's nose)
        if (sx >= 168) continue;                             // off screen (also 'negative')
        x = (uint8_t)sx;
        y += 16;
        o->y = y; o->x = x; o->tile = SPR_BOX; o->prop = 0; o++;
        if (rv_d1[k]) { x += 8; o->y = y; o->x = x; o->tile = rv_d1[k]; o->prop = 0; o++; }
        x += 8; o->y = y; o->x = x; o->tile = rv_d0[k]; o->prop = 0; o++;
    }
    while (o < shadow_OAM + 40) { o->y = 0; o++; }
}

void camera(void) {
    int16_t f = (int16_t)(rx[rv_focus].pos >> 3), lead = (int16_t)(rx[order[0]].pos >> 3), c = f - 72;
    if (lead > c + 144) c = lead - 144 < f - 16 ? lead - 144 : f - 16;
    cam_want = c;
    if (cam < c) cam += c - cam > 3 ? 3 : c - cam;
    else if (cam > c) cam -= cam - c > 3 ? 3 : cam - c;
    scx_shadow = (uint8_t)cam;
}

// ---------------------------------------------------------------- build (LCD off) and frame
void rv_build(void) {
    uint8_t c, r, t, k;
    static const uint16_t marks[4] = { 800, 600, 400, 200 };
    bank_set_bkg_data(BANK(greybox), VRAM_GREYBOX, GREYBOX_COUNT, greybox_tiles);
    bank_set_bkg_data(BANK(font_mini), VRAM_FONT_MINI, FONT_MINI_COUNT, font_mini_tiles);
    bank_set_sprite_data(BANK(greybox), 0, GREYBOX_COUNT, greybox_tiles);
    bank_set_sprite_data(BANK(font_mini), SPR_DIGIT, 10, font_mini_tiles);
    for (r = 0; r < TRACK_ROWS; r++)
        for (c = 0; c < 32; c++) {
            t = r ? VRAM_GREYBOX + GREYBOX_FLOOR : VRAM_GREYBOX + ((c >> 2) & 1 ? GREYBOX_GRAY : GREYBOX_WALL);
            *((uint8_t *)0x9800 + ((uint16_t)r << 5) + c) = t;
        }
    vwf_clear(line_buf, LINE_W);                // text slot: blank tile 0, two empty comment lines
    set_bkg_data(VRAM_TEXT, 1, line_buf);
    set_bkg_data(VRAM_TEXT + COMMENT_T, LINE_W, line_buf);
    set_bkg_data(VRAM_TEXT + COMMENT_T + LINE_W, LINE_W, line_buf);
    for (c = 0; c < 32; c++) {
        *((uint8_t *)0x9C00 + c) = VRAM_TEXT;
        *((uint8_t *)0x9C20 + c) = c < LINE_W ? VRAM_TEXT + COMMENT_T + c : VRAM_TEXT;
        *((uint8_t *)0x9C40 + c) = c < LINE_W ? VRAM_TEXT + COMMENT_T + LINE_W + c : VRAM_TEXT;
    }
    post_n = 0;                                 // gates, the 800-200 m posts, the finish
    post_x[post_n] = 4; post_tile[post_n++] = VRAM_GREYBOX + GREYBOX_BOX;
    for (k = 0; k < 4; k++)
        if (marks[k] < crs.dist) { post_x[post_n] = (crs.dist - marks[k]) << 1; post_tile[post_n++] = VRAM_GREYBOX + GREYBOX_DOOR; }
    post_x[post_n] = crs.dist << 1; post_tile[post_n++] = VRAM_GREYBOX + GREYBOX_CHECK;
    post_on = 0;
    for (k = 0; k < rn_n; k++) {
        rv_idx[k] = k;
        rv_d1[k] = k + 1 >= 10 ? SPR_DIGIT + 1 : 0;
        rv_d0[k] = SPR_DIGIT + (k + 1 >= 10 ? k + 1 - 10 : k + 1);
    }
    rows();
    for (k = 0; k < rn_n; k++) rv_y[k] = 8 + (rv_row[k] << 3);
    rv_cs = rv_sec = rv_min = 0;
    say_s = 0;
    rv_focus = order[0];
    cam = cam_want = -72;
    scx_shadow = (uint8_t)cam; scy_shadow = 0;
    rv_phase = RV_GATES; rv_t = 0; rv_said = 0; rv_leader = 0xFF; rv_lead_t = 0;
    txt_font = VRAM_FONT_MINI;
    WX_REG = 7; WY_REG = 120;
    SPRITES_8x8;
    SHOW_BKG; SHOW_WIN; SHOW_SPRITES;
}

// once per frame; returns 1 when the race scene is over
uint8_t rv_update(void) {
    uint8_t k;
    if (rv_phase == RV_GATES) { if (++rv_t >= 60) { rv_phase = RV_RUN; rv_t = 0; } }
    else if (rv_phase == RV_RUN) {
        if (pressed & J_START) rv_phase |= 0x80;            // pause
        for (k = (keys & J_B) ? 3 : 1; k && !race_done; k--) { race_tick(); clock_tick(); }
        if (race_done) { rv_phase = RV_AFTER; rv_t = 0; }
    } else if (rv_phase == (RV_RUN | 0x80)) { if (pressed & J_START) rv_phase = RV_RUN; return 0; }
    else if (rv_phase == RV_AFTER) { if (++rv_t >= 60) rv_phase = RV_DONE; }
    else return 1;
    if (pressed & J_A) rv_focus = rv_focus == order[0] ? order[rn_n - 1] : order[0];   // M1b: your horse
    if (!(race_t & 7)) rows();
    camera();
    posts();
    if (!say_s && (!(rv_t & 15) || rv_phase == RV_RUN)) commentary();
    type_letter();
    if (!(race_t & 7)) hud();
    sprites();
    return 0;
}
