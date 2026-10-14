// HUD in the window layer, 2 rows at the top (design/ui.md §2). Values are rendered into
// hud_buf outside VBlank; hud_draw_vram() copies only the dirty fields.
#include "game.h"

#define WIN_MAP ((uint8_t *)0x9C00u)
#define T_BLANK  (TILE_UI + UI_BLANK)
#define T_DIGIT0 (TILE_FONT + FONT_DIGIT0)
#define T_A      (TILE_FONT + FONT_LETTER_A)

// Field positions (row, col) from ui.md §2
#define COL_SCORE 1
#define COL_COINS 12
#define COL_LIVES 12
#define COL_WORLD 16
#define COL_TIMEICON 15
#define COL_TIME  16

enum { HUD_SCORE = 1, HUD_COINS = 2, HUD_LIVES = 4, HUD_TIME = 8, HUD_TIMEICON = 16, HUD_ROW0 = 32 };
uint8_t pause_row[20];
uint8_t hud_paused;                     // 0 normal, 1 "PAUSA" shown, 2 "PAUSA" hidden (blink)

uint8_t hud_buf[2][20];
uint8_t hud_dirty;
uint8_t score[3];                       // packed BCD, little-endian (score[0] = lowest 2 digits)
uint8_t coins, lives, world, stage;
uint16_t time_units;

void put_text(uint8_t *dst, const char *s) {        // also used by flow.c (LCD off)
    while (*s) {
        char c = *s++;
        if (c >= 'A' && c <= 'Z') *dst = T_A + (c - 'A');
        else if (c >= '0' && c <= '9') *dst = T_DIGIT0 + (c - '0');
        else if (c == '-') *dst = TILE_FONT + FONT_DASH;
        else *dst = T_BLANK;
        dst++;
    }
}

static void put_2digits(uint8_t *dst, uint8_t v) {
    uint8_t tens = 0;
    while (v >= 10) { v -= 10; tens++; }
    dst[0] = T_DIGIT0 + tens;
    dst[1] = T_DIGIT0 + v;
}

void hud_set_score(void) {
    uint8_t *d = &hud_buf[1][COL_SCORE];
    d[0] = T_DIGIT0 + (score[2] >> 4); d[1] = T_DIGIT0 + (score[2] & 15);
    d[2] = T_DIGIT0 + (score[1] >> 4); d[3] = T_DIGIT0 + (score[1] & 15);
    d[4] = T_DIGIT0 + (score[0] >> 4); d[5] = T_DIGIT0 + (score[0] & 15);
    hud_dirty |= HUD_SCORE;
}

void hud_set_coins(void) { put_2digits(&hud_buf[0][COL_COINS], coins); hud_dirty |= HUD_COINS; }
void hud_set_lives(void) { put_2digits(&hud_buf[1][COL_LIVES], lives); hud_dirty |= HUD_LIVES; }

void hud_set_time(uint16_t units) {
    uint8_t *d = &hud_buf[1][COL_TIME];
    uint8_t h = 0;
    while (units >= 100) { units -= 100; h++; }
    d[0] = T_DIGIT0 + h;
    put_2digits(d + 1, (uint8_t)units);
    hud_dirty |= HUD_TIME;
}

// Points as packed BCD, little-endian (GDD §2.10)
const uint8_t PTS_50[3]   = { 0x50, 0x00, 0x00 };
const uint8_t PTS_100[3]  = { 0x00, 0x01, 0x00 };
const uint8_t PTS_200[3]  = { 0x00, 0x02, 0x00 };
const uint8_t PTS_400[3]  = { 0x00, 0x04, 0x00 };
const uint8_t PTS_1000[3] = { 0x00, 0x10, 0x00 };

void add_score(const uint8_t *bcd) {
    bcd_add3(score, bcd);
    hud_set_score();
}

void add_life(void) {
    if (lives < 99) lives++;
    hud_set_lives();
    sfx(SFX_ONEUP);
}

void add_coin(void) {
    sfx(SFX_COIN);
    if (++coins == 100) {               // 100 coins = extra life
        coins = 0;
        add_life();
    }
    hud_set_coins();
}

static void copy(uint8_t *dst, const uint8_t *src, uint8_t n) {
    do *dst++ = *src++; while (--n);
}

// LCD off: build both rows and copy them whole
void hud_init(void) {
    uint8_t i;
    for (i = 0; i < 20; i++) hud_buf[0][i] = hud_buf[1][i] = T_BLANK;
    put_text(&hud_buf[0][1], "PUNTOS");
    hud_buf[0][10] = TILE_UI + UI_ICON_COIN;
    hud_buf[0][11] = (uint8_t)(TILE_UI + UI_ICON_TIMES);
    hud_buf[0][COL_WORLD] = T_DIGIT0 + world;
    hud_buf[0][COL_WORLD + 1] = TILE_FONT + FONT_DASH;
    hud_buf[0][COL_WORLD + 2] = T_DIGIT0 + stage;
    hud_buf[1][10] = TILE_UI + UI_ICON_HEAD;
    hud_buf[1][11] = (uint8_t)(TILE_UI + UI_ICON_TIMES);
    hud_buf[1][COL_TIMEICON] = TILE_UI + UI_ICON_TIME;
    hud_set_score();
    hud_set_coins();
    hud_set_lives();
    hud_set_time(time_units);
    copy(WIN_MAP, hud_buf[0], 20);
    copy(WIN_MAP + 32, hud_buf[1], 20);
    hud_dirty = 0;
}

// PAUSE: row 0 becomes "PAUSA" at cols 7-11, blinking; restored from hud_buf (ui.md §5)
void hud_pause(uint8_t mode) {
    uint8_t i;
    hud_paused = mode;
    for (i = 0; i < 20; i++) pause_row[i] = T_BLANK;
    if (mode == 1) put_text(&pause_row[7], "PAUSA");
    hud_dirty |= HUD_ROW0;
}

// VBlank only. At most 13 tiles in play (score 6 + coins 2 + lives 2 + time 3); 20 in pause.
void hud_draw_vram(void) {
    uint8_t d = hud_dirty;
    if (!d) return;
    if (d & HUD_ROW0) copy(WIN_MAP, hud_paused ? pause_row : hud_buf[0], 20);
    if (d & HUD_SCORE) copy(WIN_MAP + 32 + COL_SCORE, &hud_buf[1][COL_SCORE], 6);
    if (d & HUD_COINS) copy(WIN_MAP + COL_COINS, &hud_buf[0][COL_COINS], 2);
    if (d & HUD_LIVES) copy(WIN_MAP + 32 + COL_LIVES, &hud_buf[1][COL_LIVES], 2);
    if (d & HUD_TIME) copy(WIN_MAP + 32 + COL_TIME, &hud_buf[1][COL_TIME], 3);
    hud_dirty = 0;
}
