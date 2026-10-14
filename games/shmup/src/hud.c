// GRIFO - HUD: one row of the window at $9C00 (design/ui.md 2). Counters are composed into
// hud_buf in update(); VBlank only copies the fields marked dirty.
#include <string.h>
#include "game.h"

#define HUD_VRAM ((uint8_t *)0x9C00)

uint8_t hud_buf[20], hud_dirty;
uint8_t score[3], hiscore[3];
static uint8_t shown_lives, shown_bombs, shown_power;

static const uint8_t hud_layout[20] = {
    T_DIGIT0, T_DIGIT0, T_DIGIT0, T_DIGIT0, T_DIGIT0, T_DIGIT0, T_BLANK,
    TILE_UI + UI_ICON_LIFE, T_DIGIT0, T_BLANK,
    TILE_UI + UI_ICON_BOMB, T_DIGIT0, T_BLANK,
    TILE_UI + UI_ICON_POWER, T_DIGIT0,
    T_BLANK, T_BLANK, T_BLANK, T_BLANK, T_BLANK,
};

static void score_tiles(void) {
    uint8_t i, b, *d = &hud_buf[0];
    for (i = 3; i; i--) {
        b = score[i - 1];
        *d++ = T_DIGIT0 + (b >> 4);
        *d++ = T_DIGIT0 + (b & 15);
    }
}

void hud_init(void) {
    memcpy(hud_buf, hud_layout, 20);
    score_tiles();
    hud_buf[8] = T_DIGIT0 + (shown_lives = lives);
    hud_buf[11] = T_DIGIT0 + (shown_bombs = bombs);
    hud_buf[14] = T_DIGIT0 + (shown_power = power);
    hud_dirty = HUD_ROW;
}

// Extra lives at 20 000 and 50 000 (GDD 2.4): score[2] holds the two top BCD digits
void add_score(const uint8_t *bcd) {
    bcd_add3(score, bcd);
    score_tiles();
    hud_dirty |= HUD_SCORE;
    if (score[2] >= 0x02 && !(extends & 1)) { extends |= 1; if (lives < 9) lives++; sfx(SFX_EXTEND); }
    if (score[2] >= 0x05 && !(extends & 2)) { extends |= 2; if (lives < 9) lives++; sfx(SFX_EXTEND); }
}

void hud_update(void) {
    if (lives != shown_lives) { hud_buf[8] = T_DIGIT0 + (shown_lives = lives); hud_dirty |= HUD_LIVES; }
    if (bombs != shown_bombs) { hud_buf[11] = T_DIGIT0 + (shown_bombs = bombs); hud_dirty |= HUD_BOMBS; }
    if (power != shown_power) { hud_buf[14] = T_DIGIT0 + (shown_power = power); hud_dirty |= HUD_POWER; }
}

void hud_draw_vram(void) {
    uint8_t d = hud_dirty;
    if (!d) return;
    hud_dirty = 0;
    if (d & HUD_ROW) { vram_row20(HUD_VRAM, hud_buf); return; }
    if (d & HUD_SCORE) memcpy(HUD_VRAM, hud_buf, 6);
    if (d & HUD_LIVES) HUD_VRAM[8] = hud_buf[8];
    if (d & HUD_BOMBS) HUD_VRAM[11] = hud_buf[11];
    if (d & HUD_POWER) HUD_VRAM[14] = hud_buf[14];
}
