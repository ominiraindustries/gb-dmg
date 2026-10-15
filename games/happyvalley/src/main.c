// HAPPY VALLEY - glue: init, the frame loop, the M1a screens (debug menu -> race -> results) and the
// test hooks (GDD design/gdd.md). Loop rules (CLAUDE.md): vsync (+ stale guard) -> VBlank copies ->
// frame_vram_check -> frame_begin -> logic -> sprites -> frame_end.
#include "hv.h"
#include "greybox.h"
#include "font_mini.h"
#include "font_mini_lower.h"
#include "font_mini_es.h"

enum { SC_MENU, SC_RACE, SC_RESULT };
uint16_t rules_cache[RULE_COUNT];
uint8_t scene, cheat_flags, menu_course;
// tests: race_req = 1 runs a whole race headless: rng_state = race_seed, rivals of course race_req_course
// with ratings race_lo..race_hi, race_req_n runners (tests/test_race.py vs tests/hv_model.py);
// race_req = 2 starts the same race on screen
uint8_t race_req, race_req_course, race_lo, race_hi, race_req_n;
uint16_t race_seed;

const sfx_t sfx_table[2] = {
    { 2, 1, 4, { 0, 0x80, 0x41, 0xC0, 0x87 } },          // cursor
    { 1, 2, 30, { 0x00, 0x80, 0xF1, 0x60, 0x87 } },       // the start bell
};

static void row_text(uint8_t row, uint8_t col, const char *s) {
    uint8_t t[20], n = 0;
    while (s[n] && n < 20 - col) n++;
    txt_tiles(t, s, n);
    set_bkg_tiles(col, row, n, 1, t);
}

static void clear_bg(void) {
    uint8_t r;
    for (r = 0; r < 18; r++) fill_bkg_rect(0, r, 32, 1, VRAM_GREYBOX + GREYBOX_BLANK);
}

static void menu_draw_course(void) {
    char s[12];
    bank_memcpy(BANK(tbl_courses), &crs, &tbl_courses[menu_course], sizeof(crs));
    s[0] = crs.track == COURSES_TRACK_HV ? 'H' : crs.track == COURSES_TRACK_ST ? 'S' : 'A';
    s[1] = crs.track == COURSES_TRACK_HV ? 'V' : crs.track == COURSES_TRACK_ST ? 'T' : 'W';
    s[2] = ' ';
    s[3] = '0' + crs.dist / 1000; s[4] = '0' + (crs.dist / 100) % 10; s[5] = '0' + (crs.dist / 10) % 10; s[6] = '0';
    s[7] = 'M'; s[8] = 0;
    {
        uint8_t t[8];
        txt_tiles(t, s, 8);
        vq_push((uint8_t *)0x9800 + 6 * 32 + 9, t, 8);
    }
}

void screen_build(uint8_t which) {
    uint8_t k;
    lcd_off_redraw_begin();
    txt_font = VRAM_FONT_MINI;
    txt_blank = VRAM_GREYBOX + GREYBOX_BLANK;
    if (which == SC_RACE) rv_build();
    else {
        bank_set_bkg_data(BANK(greybox), VRAM_GREYBOX, GREYBOX_COUNT, greybox_tiles);
        bank_set_bkg_data(BANK(font_mini), VRAM_FONT_MINI, FONT_MINI_COUNT, font_mini_tiles);
        clear_bg();
        if (which == SC_MENU) {
            row_text(1, 3, "HAPPY VALLEY M1A");
            row_text(4, 2, "CARRERA DE PRUEBA");
            row_text(6, 2, "CURSO:");
            row_text(10, 2, "IZQ/DER CAMBIA");
            row_text(11, 2, "A: CORRER");
            row_text(13, 2, "EN CARRERA: A CAMARA");
            row_text(14, 2, "B RAPIDO  START PAUSA");
        } else {
            uint8_t t[20];
            uint16_t cs;
            row_text(0, 1, "RESULTADO");
            for (k = 0; k < rn_n && k < 14; k++) {
                if (res_i[k] == 0xFF) break;
                memset(t, txt_blank, 20);
                txt_u16(t + 1, k + 1, 2, 0);
                txt_u16(t + 5, res_i[k] + 1, 2, 0);
                cs = res_t[k] << 2;
                txt_u16(t + 10, cs / 6000, 1, 0);
                t[11] = txt_char(':');
                txt_u16(t + 12, (cs / 100) % 60, 2, 1);
                t[14] = txt_char('.');
                txt_u16(t + 15, cs % 100, 2, 1);
                set_bkg_tiles(0, 2 + k, 20, 1, t);
            }
            row_text(17, 1, "A: VOLVER");
        }
        SPRITES_8x8;
        hide_sprites_range(0, 40);
        SHOW_BKG;
    }
    scene = which;
    DISPLAY_ON;
}

static void start_race(uint16_t seed, uint8_t course, uint8_t lo, uint8_t hi, uint8_t n) {
    rng_state = seed;
    race_gen_field(course, lo, hi, n);
    race_init(course);
    transition(SC_RACE);
}

static void test_hook(void) {
    if (race_req == 2) { start_race(race_seed, race_req_course, race_lo, race_hi, race_req_n); race_req = 0; return; }
    rng_state = race_seed;
    race_gen_field(race_req_course, race_lo, race_hi, race_req_n);
    race_init(race_req_course);
    while (!race_done) race_tick();
    race_req = 0;
    skip_measure = 1;
}

static void screen_update(void) {
    if (scene == SC_MENU && (pressed & (J_LEFT | J_RIGHT))) {
        menu_course = (pressed & J_LEFT) ? (menu_course ? menu_course - 1 : CRS_COUNT - 1)
                                         : (menu_course + 1 < CRS_COUNT ? menu_course + 1 : 0);
        menu_draw_course();
        sfx(0);
    }
    if (pressed & J_A) {
        if (scene == SC_MENU) {
            bank_memcpy(BANK(tbl_courses), &crs, &tbl_courses[menu_course], sizeof(crs));
            start_race(rng_state ^ sys_time, menu_course, 40, 60, crs.track == COURSES_TRACK_HV ? 12 : 14);
        } else transition(SC_MENU);
    }
}

void main(void) {
    DISPLAY_OFF;
    bank_memcpy(BANK(tbl_rules), rules_cache, tbl_rules, sizeof(rules_cache));
    vwf_font(0, BANK(font_mini), font_mini_tiles, font_mini_vwf);
    vwf_font(1, BANK(font_mini_lower), font_mini_lower_tiles, font_mini_lower_vwf);
    vwf_font(2, BANK(font_mini_es), font_mini_es_tiles, font_mini_es_vwf);
    LCDC_REG |= LCDCF_WIN9C00;
    WY_REG = 144;
    video_init(0, 0xE4, 0xE4, 0x1B);
    sound_init();
    rng_state = 0xACE1;
    show_screen_now(SC_MENU);
    menu_draw_course();
    vsync();
    vram_late = 0;
    while (1) {
        vsync();
        if (LY_REG < 144) vsync();
        frame_vsync_ly = LY_REG;
        world_draw_vram();
        tiles_draw_vram();
        vq_draw_vram();
        frame_vram_check();
        frame_begin();
        if (race_req) test_hook();
        if (!transition_update()) {
            if (scene == SC_RACE) { if (rv_update()) transition(SC_RESULT); }
            else screen_update();
        }
        tiles_prepare();
        sound_update();
        frame_end();
    }
}
