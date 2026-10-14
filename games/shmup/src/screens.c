// GRIFO - screens and flow (GDD 4, design/ui.md 4-8): TITLE, PAUSE, CONTINUAR, GAMEOVER, CLEAR.
// Full-screen changes go through gbe_screen (fade out, LCD-off rebuild, fade in); PAUSE and
// CONTINUAR keep the stage in the BG and only use the window.
#include <string.h>
#include "game.h"
#include "uiscreens.h"
#include "screen_title.h"
#include "screen_continuar.h"
#include "screen_clear.h"
#include "screen_gameover.h"

#define BG(r, c)  ((uint8_t *)0x9800 + (r) * 32 + (c))
#define WIN(r, c) ((uint8_t *)0x9C00 + (r) * 32 + (c))

uint8_t screen_timer, screen_sub, count_n, died_in_stage;
static const uint8_t bcd_100[3] = { 0x00, 0x01, 0 };

// ---------------------------------------------------------------- helpers
static void load_screen(const uint8_t *map) {
    lcd_off_redraw_begin();
    set_bkg_data(BG_BASE, UISCREENS_COUNT, uiscreens_tiles);   // over the stage tiles
    set_bkg_tiles(0, 0, 20, 18, map);
    scx_shadow = scy_shadow = 0;
    shake_x = shake_y = 0;
    hud_cut = 0;
    bgp_below_on = 0;
    HIDE_WIN;
    hide_sprites_range(0, 40);
    screen_timer = 0;
    screen_sub = 0;
}

static void put_bcd_now(uint8_t *dst, const uint8_t *bcd) {     // LCD off only
    bcd_tiles(dst, bcd);
}

static uint8_t blink_on(uint8_t t) {
    return (uint8_t)(t % 60) < 30;
}

static void blink_text(uint8_t *dst, const char *s, uint8_t t) {
    uint8_t m = (uint8_t)(t % 60);
    if (m == 0) text_put_str(dst, s);
    else if (m == 30) {
        uint8_t b[20], n = 0;
        while (s[n]) n++;
        memset(b, T_BLANK, n);
        text_put(dst, b, n);
    }
}

void game_start(void) {
    memset(score, 0, 3);
    lives = 3; bombs = 2; power = 1; continues = 3; extends = 0;
    new_record = 0; died_in_stage = 0;
}

// ---------------------------------------------------------------- TITLE
void title_build(void) {
    load_screen(screen_title_map);
    put_bcd_now(BG(12, 10), hiscore);
    SHOW_BKG;
    SHOW_SPRITES;
    state = ST_TITLE;
    DISPLAY_ON;
}

void title_update(void) {
    uint8_t t = ++screen_timer;
    oam16(0, 72 + 8, 56 + 16 + ((t >> 4) & 1), SPR_PLAYER, 0);    // bob 1 px every 16 f
    if (screen_sub == 0) {
        blink_text(BG(10, 4), "PULSA START", t);
        if (pressed & (J_START | J_A)) { sfx(SFX_START); screen_sub = 1; screen_timer = 0; }
    } else {                                             // fast blink 32 f, then go
        if ((t & 3) == 0) text_put_str(BG(10, 4), (t & 4) ? "           " : "PULSA START");
        if (t == 32) { game_start(); transition(ST_PLAY); }
    }
}

// ---------------------------------------------------------------- PAUSE
void pause_toggle(void) {
    if (state == ST_PLAY) {
        state = ST_PAUSE;
        sfx(SFX_PAUSE);
        hud_message(MSG_PAUSA, 0);
        screen_timer = 0;
    } else {
        state = ST_PLAY;
        NR50_REG = 0x77;
        hud_message_end();
    }
}

void pause_update(void) {
    if (++screen_timer == 8) NR50_REG = 0;               // silence after the PAUSE sound
    hud_message_update();
    if (pressed & J_START) pause_toggle();
}

// ---------------------------------------------------------------- CONTINUAR (window only)
// sub 0 fade out, 1 count, 2 fade out to play, 3 fade in to play
static void continue_digits(void) {
    uint8_t d = T_DIGIT0 + count_n, q = T_DIGIT0 + continues;
    text_put(WIN(8, 9), &d, 1);
    text_put(WIN(11, 13), &q, 1);
}

void continue_start(void) {
    hiscore_update();                                    // continuing resets the score
    if (!continues) { transition(ST_GAMEOVER); return; }
    state = ST_CONTINUE;
    if (hud_msg != MSG_NONE) hud_message_end();         // row 0 shows the counters (ui.md 5)
    screen_sub = 0;
    screen_timer = 0;
}

void continue_update(void) {
    uint8_t t = ++screen_timer, k;
    if (screen_sub == 0) {                               // fade out, then window full screen
        k = 1 + (t >> 2);
        set_fade(k > 3 ? 3 : k);
        if (t == 16) {
            count_n = 9;
            continue_digits();
            hud_cut = 0;
            LCDC_REG = (LCDC_REG | LCDCF_WINON) & ~LCDCF_OBJON;
            screen_sub = 1; screen_timer = 0;
        }
    } else if (screen_sub == 1) {
        if (t <= 16) { k = (t - 1) >> 2; set_fade(k >= 3 ? 0 : 3 - k); }
        else blink_text(WIN(13, 4), "PULSA START", t - 16);
        if (t >= 46 && (pressed & J_START)) {            // continue in place (GDD 2.4)
            uint8_t i;
            sfx(SFX_START);
            continues--;
            memset(score, 0, 3);
            lives = 3; power = 1; bombs = 2; extends = 0; died_in_stage = 1;
            for (i = 0; i < N_BULLET; i++) pool[P_BULLET + i].t = 0;
            bcd_tiles(hud_buf, score);
            screen_sub = 2; screen_timer = 0;
            return;
        }
        if (t > 16 && ((t - 16) % 60) == 0) {
            if (!count_n) { transition(ST_GAMEOVER); return; }
            count_n--;
            continue_digits();
            sfx(SFX_TICK);
        }
    } else if (screen_sub == 2) {
        k = 1 + (t >> 2);
        set_fade(k > 3 ? 3 : k);
        if (t == 16) {
            hud_cut = 1;                                 // HUD cut back on (VBlank ISR restores LCDC)
            hud_dirty = HUD_ROW;
            screen_sub = 3; screen_timer = 0;
        }
    } else {
        k = (t - 1) >> 2;
        set_fade(k >= 3 ? 0 : 3 - k);
        if (t == 16) {
            set_fade(0);
            state = ST_PLAY;
            play_respawn();
        }
    }
}

// ---------------------------------------------------------------- GAMEOVER
void gameover_build(void) {
    hiscore_update();
    load_screen(screen_gameover_map);
    put_bcd_now(BG(7, 11), score);
    put_bcd_now(BG(9, 11), hiscore);
    memset(BG(11, 4), T_BLANK, 13);                      // the mockup shows NUEVO RECORD!: blinks if set
    SHOW_BKG;
    state = ST_GAMEOVER;
    DISPLAY_ON;
}

void gameover_update(void) {
    uint8_t t = ++screen_timer;
    if (new_record) blink_text(BG(11, 4), "NUEVO RECORD!", t);
    if (t == 180 || (t >= 30 && (pressed & (J_START | J_A)))) transition(ST_TITLE);
}

// ---------------------------------------------------------------- CLEAR (bonus count)
// ui.md 7: bombs left x 2000 (+100/f, one bomb every 20 f), then the no-death bonus 10 000
// drains 100/f into the score; Start/A finishes the count at once.
static uint8_t bonus_left;                               // hundreds left (100 = 10 000)

void stage_clear(void) {
    transition(ST_CLEAR);
}

static void bonus_tiles(uint8_t *b) {                    // 5 tiles: d1 d2 d3 0 0
    uint8_t r = bonus_left, d1 = 0, d2 = 0;
    if (r >= 100) { d1 = 1; r -= 100; }
    while (r >= 10) { d2++; r -= 10; }
    b[0] = T_DIGIT0 + d1; b[1] = T_DIGIT0 + d2; b[2] = T_DIGIT0 + r;
    b[3] = b[4] = T_DIGIT0;
}

static void clear_numbers(void) {
    uint8_t b[6];
    bcd_tiles(b, score);
    text_put(BG(8, 11), b, 6);
    bonus_tiles(b);
    text_put(BG(6, 12), b, 5);
    b[0] = T_DIGIT0 + count_n;
    text_put(BG(4, 9), b, 1);
}

void clear_build(void) {
    load_screen(screen_clear_map);
    count_n = bombs;
    bonus_left = died_in_stage ? 0 : 100;
    *BG(4, 9) = T_DIGIT0 + count_n;
    bonus_tiles(BG(6, 12));
    put_bcd_now(BG(8, 11), score);
    put_bcd_now(BG(10, 11), hiscore);
    memset(BG(12, 3), T_BLANK, 13);
    SHOW_BKG;
    state = ST_CLEAR;
    DISPLAY_ON;
}

void clear_update(void) {
    uint8_t t = ++screen_timer;
    if (screen_sub == 0) {                               // 30 f before counting
        if (t == 30) { screen_sub = 1; screen_timer = 0; }
        return;
    }
    if (screen_sub == 1) {
        if (pressed & (J_START | J_A)) {                 // finish at once
            while (count_n) { uint8_t k; for (k = 0; k < 20; k++) add_score(bcd_100); count_n--; }
            while (bonus_left) { add_score(bcd_100); bonus_left--; }
        } else if (count_n) {
            add_score(bcd_100);
            if ((uint8_t)(t % 20) == 0) count_n--;
        } else if (bonus_left) {
            add_score(bcd_100);
            bonus_left--;
        }
        if ((t & 3) == 0) sfx(SFX_TICK);
        clear_numbers();
        if (!count_n && !bonus_left) {
            uint8_t b[6];
            screen_sub = 2; screen_timer = 0;
            hiscore_update();
            bcd_tiles(b, hiscore);
            text_put(BG(10, 11), b, 6);
        }
        return;
    }
    if (new_record) blink_text(BG(12, 3), "NUEVO RECORD!", t);
    if (t == 255 || (t >= 30 && (pressed & (J_START | J_A)))) transition(ST_TITLE);
}
