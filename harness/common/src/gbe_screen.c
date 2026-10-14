// gbe: screen transitions (fade out -> LCD-off rebuild -> fade in), 16 + 16 frames
#include "gbe.h"

uint8_t trans_phase, trans_timer, trans_next, trans_own_fadein;   // phase 0 none, 1 out, 2 in

void transition(uint8_t next) {
    trans_phase = 1;
    trans_timer = 0;
    trans_next = next;
}

static void build(uint8_t which) {
    trans_own_fadein = 0;
    screen_build(which);
    trans_phase = trans_own_fadein ? 0 : 2;
    trans_timer = 0;
}

void show_screen_now(uint8_t which) {
    build(which);
}

uint8_t transition_update(void) {
    uint8_t k;
    if (trans_phase == 1) {                    // fade out: k = 1, 2, 3, 3 every 4 frames
        k = 1 + (trans_timer >> 2);
        set_fade(k > 3 ? 3 : k);
        if (++trans_timer == 16) build(trans_next);
        return 1;
    }
    if (trans_phase == 2) {                    // fade in: k = 3, 2, 1, 0
        k = trans_timer >> 2;
        set_fade(k >= 3 ? 0 : 3 - k);
        if (++trans_timer == 16) {
            trans_phase = 0;
            set_fade(0);
        }
        return 1;
    }
    return 0;
}

// Common start of every full-screen redraw: LCD off (GBDK waits for VBlank), screen white,
// window and sprites off, scroll 0, and the frame excluded from the budget measurement.
void lcd_off_redraw_begin(void) {
    DISPLAY_OFF;
    hide_sprites_range(0, 40);
    set_fade(3);
    BGP_REG = OBP0_REG = OBP1_REG = 0;
    hud_cut = 0;
    HIDE_WIN;
    HIDE_SPRITES;
    SCX_REG = SCY_REG = 0;
    scx_shadow = 0;
    skip_measure = 1;
}
