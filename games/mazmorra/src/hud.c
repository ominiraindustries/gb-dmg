// MADRIGUERA - the HUD (ui.md 3): window row 0 above the LYC cut at line 16; hearts in cols 1-5
// (hp in half hearts, hp_max / 2 containers). Rewritten through gbe_vq only when what it shows
// changes; with hp <= 2 the last heart blinks with HEART_EMPTY 16/16 f.
#include "game.h"
#include "ui.h"

static uint8_t shown_hp = 0xFF, shown_max, shown_blink;

void hud_reset(void) { shown_hp = 0xFF; }

void hud_update(void) {
    uint8_t t[5], k, n = hp_max >> 1, b = (hp && hp <= 2 && !dead_t) ? (uint8_t)(sys_time >> 4) & 1 : 0;
    if (hp == shown_hp && hp_max == shown_max && b == shown_blink) return;
    shown_hp = hp; shown_max = hp_max; shown_blink = b;
    for (k = 0; k < 5; k++) {
        if (k >= n) t[k] = VRAM_UI + UI_BLANK;
        else t[k] = VRAM_UI + (hp >= 2 * k + 2 ? UI_HEART_FULL : hp == 2 * k + 1 ? UI_HEART_HALF : UI_HEART_EMPTY);
    }
    if (b) t[(hp - 1) >> 1] = VRAM_UI + UI_HEART_EMPTY;   // the last non-empty heart
    vq_push((uint8_t *)0x9C00 + 1, t, 5);
}
