// GRIFO - HUD: one row of the window at $9C00 (design/ui.md 2) + messages that replace the row
// (FASE 1, PELIGRO, PAUSA) + the boss bar, and a small queue of text writes for the screens.
// Everything is composed in update(); VBlank only copies.
#include <string.h>
#include "game.h"

#define HUD_VRAM ((uint8_t *)0x9C00)
#define TQ_MAX   4

uint8_t hud_buf[20], hud_dirty;
uint8_t score[3], hiscore[3], new_record;
uint8_t hud_msg, hud_msg_timer, hud_bar_px, boss_bar_on;
static uint8_t hud_msg_age, shown_lives, shown_bombs, shown_power, shown_bar = 0xFF;
static uint8_t msg_buf[20], msg_dirty;

// text writes for screens (blinking strings, counters): copied in VBlank
static uint8_t *tq_dst[TQ_MAX];
static uint8_t tq_buf[TQ_MAX][20], tq_len[TQ_MAX], tq_count;

static const uint8_t hud_layout[20] = {
    T_DIGIT0, T_DIGIT0, T_DIGIT0, T_DIGIT0, T_DIGIT0, T_DIGIT0, T_BLANK,
    TILE_UI + UI_ICON_LIFE, T_DIGIT0, T_BLANK,
    TILE_UI + UI_ICON_BOMB, T_DIGIT0, T_BLANK,
    TILE_UI + UI_ICON_POWER, T_DIGIT0,
    T_BLANK, T_BLANK, T_BLANK, T_BLANK, T_BLANK,
};

// ---------------------------------------------------------------- text helpers
// ASCII -> font tiles (space -> BLANK; ! ? - from the font's punctuation)
void text_tiles(uint8_t *d, const char *s) {
    char c;
    while ((c = *s++)) {
        if (c >= 'A' && c <= 'Z') *d = T_LETTER_A + (c - 'A');
        else if (c >= '0' && c <= '9') *d = T_DIGIT0 + (c - '0');
        else if (c == '!') *d = TILE_FONT + FONT_EXCLAM;
        else if (c == '?') *d = TILE_FONT + FONT_QUESTION;
        else if (c == '-') *d = TILE_FONT + FONT_DASH;
        else *d = T_BLANK;
        d++;
    }
}

void bcd_tiles(uint8_t *d, const uint8_t *bcd) {     // 6 digits, leading zeros
    uint8_t i, b;
    for (i = 3; i; i--) {
        b = bcd[i - 1];
        *d++ = T_DIGIT0 + (b >> 4);
        *d++ = T_DIGIT0 + (b & 15);
    }
}

// Queue n tiles for dst (copied next VBlank). Drops the write if the queue is full.
void text_put(uint8_t *dst, const uint8_t *tiles, uint8_t n) {
    if (tq_count == TQ_MAX) return;
    tq_dst[tq_count] = dst;
    memcpy(tq_buf[tq_count], tiles, n);
    tq_len[tq_count] = n;
    tq_count++;
}

void text_put_str(uint8_t *dst, const char *s) {
    uint8_t t[20], n = 0;
    while (s[n]) n++;
    text_tiles(t, s);
    text_put(dst, t, n);
}

// ---------------------------------------------------------------- counters
void hud_init(void) {
    memcpy(hud_buf, hud_layout, 20);
    bcd_tiles(hud_buf, score);
    hud_buf[8] = T_DIGIT0 + (shown_lives = lives);
    hud_buf[11] = T_DIGIT0 + (shown_bombs = bombs);
    hud_buf[14] = T_DIGIT0 + (shown_power = power);
    hud_dirty = HUD_ROW;
    hud_msg = MSG_NONE;
    boss_bar_on = 0;
    shown_bar = 0xFF;
    tq_count = 0;
}

// Extra lives at 20 000 and 50 000 (GDD 2.4): score[2] holds the two top BCD digits
void add_score(const uint8_t *bcd) {
    bcd_add3(score, bcd);
    bcd_tiles(hud_buf, score);
    hud_dirty |= HUD_SCORE;
    if (score[2] >= 0x02 && !(extends & 1)) { extends |= 1; if (lives < 9) lives++; sfx(SFX_EXTEND); }
    if (score[2] >= 0x05 && !(extends & 2)) { extends |= 2; if (lives < 9) lives++; sfx(SFX_EXTEND); }
}

void hiscore_update(void) {
    uint8_t i = 3;
    while (i--) {
        if (score[i] > hiscore[i]) { memcpy(hiscore, score, 3); new_record = 1; return; }
        if (score[i] < hiscore[i]) return;
    }
}

// Boss bar (ui.md 2.3): cap, 3 tiles of 8 px, cap; px 0..24
static void bar_tiles(void) {
    uint8_t i, v, px = hud_bar_px;
    hud_buf[15] = TILE_UI + UI_BAR_CAP_L;
    for (i = 0; i < 3; i++) {
        v = px > 8 ? 8 : px;
        px -= v;
        hud_buf[16 + i] = TILE_UI + UI_BAR_0 + v;
    }
    hud_buf[19] = TILE_UI + UI_BAR_CAP_R;
}

void hud_update(void) {
    if (lives != shown_lives) { hud_buf[8] = T_DIGIT0 + (shown_lives = lives); hud_dirty |= HUD_LIVES; }
    if (bombs != shown_bombs) { hud_buf[11] = T_DIGIT0 + (shown_bombs = bombs); hud_dirty |= HUD_BOMBS; }
    if (power != shown_power) { hud_buf[14] = T_DIGIT0 + (shown_power = power); hud_dirty |= HUD_POWER; }
    if (boss_bar_on && hud_bar_px != shown_bar) { shown_bar = hud_bar_px; bar_tiles(); hud_dirty |= HUD_BAR; }
    if (!boss_bar_on && shown_bar != 0xFF) {
        shown_bar = 0xFF;
        memset(&hud_buf[15], T_BLANK, 5);
        hud_dirty |= HUD_BAR;
    }
}

// ---------------------------------------------------------------- messages (ui.md 2.4)
// The message replaces the whole row; hud_buf keeps updating underneath and is copied back
// (20 tiles) when the message ends. PELIGRO and PAUSA blink 30 f visible / 30 f hidden.
static void msg_compose(uint8_t visible) {
    memset(msg_buf, T_BLANK, 20);
    if (!visible) return;
    if (hud_msg == MSG_FASE) text_tiles(&msg_buf[7], "FASE 1");
    else if (hud_msg == MSG_PAUSA) text_tiles(&msg_buf[7], "PAUSA");
    else if (hud_msg == MSG_PELIGRO) {
        msg_buf[4] = msg_buf[14] = TILE_UI + UI_ICON_BOSS;
        text_tiles(&msg_buf[6], "PELIGRO");
    }
}

// frames = 0: until hud_message_end()
void hud_message(uint8_t msg, uint8_t frames) {
    hud_msg = msg;
    hud_msg_timer = frames;
    hud_msg_age = 0;
    msg_compose(1);
    msg_dirty = 1;
}

void hud_message_end(void) {
    hud_msg = MSG_NONE;
    hud_dirty = HUD_ROW;
}

void hud_message_update(void) {
    if (hud_msg == MSG_NONE) return;
    if (hud_msg != MSG_FASE) {
        if (++hud_msg_age == 60) hud_msg_age = 0;
        if (hud_msg_age == 0) { msg_compose(1); msg_dirty = 1; }
        else if (hud_msg_age == 30) { msg_compose(0); msg_dirty = 1; }
    }
    if (hud_msg_timer && !--hud_msg_timer) hud_message_end();
}

void hud_draw_vram(void) {
    uint8_t d = hud_dirty, i;
    for (i = 0; i < tq_count; i++) memcpy(tq_dst[i], tq_buf[i], tq_len[i]);
    tq_count = 0;
    if (hud_msg != MSG_NONE) {
        if (msg_dirty) { vram_row20(HUD_VRAM, msg_buf); msg_dirty = 0; }
        return;                                  // counters wait under the message
    }
    if (!d) return;
    hud_dirty = 0;
    if (d & HUD_ROW) { vram_row20(HUD_VRAM, hud_buf); return; }
    if (d & HUD_SCORE) memcpy(HUD_VRAM, hud_buf, 6);
    if (d & HUD_LIVES) HUD_VRAM[8] = hud_buf[8];
    if (d & HUD_BOMBS) HUD_VRAM[11] = hud_buf[11];
    if (d & HUD_POWER) HUD_VRAM[14] = hud_buf[14];
    if (d & HUD_BAR) memcpy(HUD_VRAM + 15, hud_buf + 15, 5);
}
