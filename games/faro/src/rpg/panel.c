// FARO kit - the Start panel (ui.md 5, mockups panel / panel_guardar / panel_aviso): a drawer in
// the window (WX 87 = screen cols 10-19, WY 0). Its 18 rows are written with the window still off
// screen (2 frames: one queue entry per row), then it slides in 8 px per frame. Measured: one
// column per frame = 18 one-tile entries at ~90 T each, the queue ran out of VBlank and lost them. Entries, Leo's stats (the HUD sprites move in as the
// PV / saciedad labels), refusals written over the stats, and the save box. Positions come from
// the mockups' SCREEN_* defines (screen coordinates: window col = screen col - 10). Bank 1.
// The composed panel lives in tbox_text (the text box is closed while the panel is open).
#pragma bank 255
#include "rpg.h"
#include "screen_panel.h"
#include "screen_panel_guardar.h"
#include "screen_panel_aviso.h"
#include "tbl_msgs.h"
#include "ui.h"
#include "font.h"

#define PW        10                                    // panel width in tiles
#define WX_OUT    167
#define WX_IN     87
#define WIN(at)   ((uint8_t *)0x9C00 + (at) - 10)       // screen-coordinate define -> window map
#define pbuf      ((uint8_t *)tbox_text)                // 18 rows x 10
#define ROW(r)    (pbuf + (r) * PW)
#define COL(at)   (((at) & 31) - 10)                    // window col of a define
#define STATS0    10                                    // rows 10-16: stats / refusal / save box
#define STATS1    17

enum { PN_CLOSED, PN_IN, PN_MENU, PN_OUT, PN_NOTE, PN_ASK, PN_SAVING, PN_SAVED };
enum { P_CUADERNO, P_MOCHILA, P_EQUIPO, P_ACAMPAR, P_GUARDAR, P_OPCIONES, P_SALIR, P_N };
// M1 has no Mapa: the 7 entries are listed one after the other from the first row (ui.md 5)
static const uint16_t entry_at[P_N] = { SCREEN_PANEL_AT_CUADERNO, SCREEN_PANEL_AT_MOCHILA, SCREEN_PANEL_AT_EQUIPO,
    SCREEN_PANEL_AT_ACAMPAR, SCREEN_PANEL_AT_GUARDAR, SCREEN_PANEL_AT_OPCIONES, SCREEN_PANEL_AT_SALIR };
#define ENTRY0    SCREEN_PANEL_AT_CUADERNO              // first entry; entry i at ENTRY0 + 32 i
uint8_t panel_state, panel_wx = WX_OUT, panel_sel, panel_t, panel_yes;

// screen rows [from, to) of a mockup, cols 10-19 -> pbuf
static void mock_rows(uint8_t bank, const uint8_t *map, uint8_t from, uint8_t to) {
    for (; from < to; from++) bank_memcpy(bank, ROW(from), map + from * 20 + 10, PW);
}

static void blank_cells(uint8_t *p, uint8_t n) { memset(p, txt_blank, n); }

// "a/b" right-aligned in w cells ending at end (inclusive)
static void frac(uint8_t *end, uint8_t a, uint8_t b, uint8_t w) {
    uint8_t *p = end + 1, *first = end + 1 - w;
    do { *--p = txt_font + FONT_DIGIT0 + b % 10; b /= 10; } while (b);
    *--p = txt_char('/');
    do { *--p = txt_font + FONT_DIGIT0 + a % 10; a /= 10; } while (a);
    while (p > first) *--p = txt_blank;
}

static void msg_cells(uint8_t msg, uint8_t *dst, uint8_t n) {
    char s[24];
    msg_expand(msg, "", "", 0, s, sizeof(s) - 1);
    txt_tiles(dst, s, n);
}

// rows 10-16 = the stats, with today's values over the mockup's examples (ui.md 5 table)
static void stats(void) {
    uint8_t *r;
    mock_rows(BANK(screen_panel), screen_panel_map, STATS0, STATS1);
    r = pbuf + (SCREEN_PANEL_AT_12 >> 5) * PW + COL(SCREEN_PANEL_AT_12) + SCREEN_PANEL_LEN_12 - 2;
    txt_u16(r, plevel, 2, 0);
    frac(pbuf + (SCREEN_PANEL_AT_32_38 >> 5) * PW + COL(SCREEN_PANEL_AT_32_38) + SCREEN_PANEL_LEN_32_38 - 1, pv, pv_max, 7);
    frac(pbuf + (SCREEN_PANEL_AT_9_13 >> 5) * PW + COL(SCREEN_PANEL_AT_9_13) + SCREEN_PANEL_LEN_9_13 - 1, en, en_max, 5);
    msg_cells(MSG_PANEL_SAC0 + (sac >= (uint8_t)RULE(RULE_SAC_FULL) ? 0 : sac >= (uint8_t)RULE(RULE_SAC_HUNGRY) ? 1 : sac ? 2 : 3),
              pbuf + (SCREEN_PANEL_AT_NORMAL >> 5) * PW + COL(SCREEN_PANEL_AT_NORMAL), SCREEN_PANEL_LEN_NORMAL);
    txt_u16(pbuf + (SCREEN_PANEL_AT_1250 >> 5) * PW + COL(SCREEN_PANEL_AT_1250) + SCREEN_PANEL_LEN_1250 - 4, money, 4, 0);
    blank_cells(pbuf + (SCREEN_PANEL_AT_DIA >> 5) * PW + COL(SCREEN_PANEL_AT_DIA), SCREEN_PANEL_LEN_DIA);   // day / night: M2
}

static void compose(void) {
    uint8_t i;
    mock_rows(BANK(screen_panel), screen_panel_map, 0, STATS0);
    for (i = 0; i < 8; i++) {
        uint8_t *r = ROW((ENTRY0 >> 5) + i) + COL(ENTRY0) - 1;
        r[0] = i == panel_sel ? tbox_cursor : txt_blank;      // not the mockup's cursor
        if (i < P_N) bank_memcpy(BANK(screen_panel), r + 1,
                                 screen_panel_map + (entry_at[i] >> 5) * 20 + (entry_at[i] & 31), PW - COL(ENTRY0));
        else blank_cells(r + 1, PW - COL(ENTRY0));
    }
    stats();
}

// rows [from, to) cols 1-9 of pbuf -> window (through the queue)
static void push_rows(uint8_t from, uint8_t to) {
    for (; from < to; from++) vq_push((uint8_t *)0x9C00 + ((uint16_t)from << 5) + 1, ROW(from) + 1, PW - 1);
}

static void show_stats(void) {
    stats();
    push_rows(STATS0, STATS1);
    hud_panel = 1;
    panel_state = PN_MENU;
}

// a refusal over the stats: wrapped to the 9 cells, from the mockup's first line
static void note(uint8_t msg) {
    char s[48], w[56], *p;
    uint8_t r, c;
    msg_expand(msg, "", "", 0, s, sizeof(s) - 1);
    msg_wrap(s, w, PW - 1, 0);
    for (r = STATS0; r < STATS1; r++) blank_cells(ROW(r) + 1, PW - 1);
    r = SCREEN_PANEL_AVISO_AT_NO_ES >> 5;
    c = COL(SCREEN_PANEL_AVISO_AT_NO_ES);
    for (p = w; *p && r < STATS1; r++) {
        char line[10];
        uint8_t k = 0;
        while (*p && *p != 0x0A && k < PW - 1) line[k++] = *p++;
        line[k] = 0;
        if (*p == 0x0A) p++;
        txt_tiles(ROW(r) + c, line, k);
    }
    push_rows(STATS0, STATS1);
    hud_panel = 2;                                            // the labels would cover the text
    panel_t = 90;
    panel_state = PN_NOTE;
}

static void ask_cursor(void) {
    vq_push(WIN(SCREEN_PANEL_GUARDAR_AT_SI - 1), panel_yes ? &tbox_cursor : &txt_blank, 1);
    vq_push(WIN(SCREEN_PANEL_GUARDAR_AT_NO - 1), panel_yes ? &txt_blank : &tbox_cursor, 1);
}

// the save box over the stats: name, lights, play time, "¿Guardar?" Si / No
static void ask_save(void) {
    uint8_t *r;
    mock_rows(BANK(screen_panel_guardar), screen_panel_guardar_map, STATS0, STATS1);
    r = pbuf + (SCREEN_PANEL_GUARDAR_AT_5 >> 5) * PW + COL(SCREEN_PANEL_GUARDAR_AT_5) + SCREEN_PANEL_GUARDAR_LEN_5 - 2;
    txt_u16(r, ops_reg_count(), 2, 0);
    r = pbuf + (SCREEN_PANEL_GUARDAR_AT_1_23 >> 5) * PW + COL(SCREEN_PANEL_GUARDAR_AT_1_23) + SCREEN_PANEL_GUARDAR_LEN_1_23 - 5;
    txt_u16(r, play_min / 60, 2, 0);                          // h:mm, up to 99:59
    r[2] = txt_char(':');
    txt_u16(r + 3, play_min % 60, 2, 1);
    push_rows(STATS0, STATS1);
    panel_yes = 1;
    ask_cursor();
    hud_panel = 2;
    panel_state = PN_ASK;
}

static void save_line(uint8_t msg) {
    uint8_t t[PW - 1];
    msg_cells(msg, t, PW - 1);
    vq_push(WIN((SCREEN_PANEL_GUARDAR_AT_GUARDAR_2 & ~31) + 11), t, PW - 1);
    vq_push_fill(WIN((SCREEN_PANEL_GUARDAR_AT_SI & ~31) + 11), txt_blank, PW - 1);
}

void panel_open(void) BANKED {
    compose();
    menu_open(P_N, panel_sel, 0, WIN(ENTRY0 - 1), 32, tbox_cursor, txt_blank);
    panel_t = 0;
    panel_wx = WX_OUT;
    panel_state = PN_IN;
    sfx(SFX_OK);
}

static void panel_close(void) {
    hud_panel = 0;
    panel_state = PN_OUT;
}

// once per field frame while panel_state != PN_CLOSED (the field is paused)
void panel_update(void) BANKED {
    uint8_t r, i;
    switch (panel_state) {
    case PN_IN:                                               // rows 0-8, rows 9-17, then slide
        if (vq_pending()) return;
        if (panel_t < 2) {
            for (i = panel_t ? 9 : 0; i < (panel_t ? 18 : 9); i++)
                vq_push((uint8_t *)0x9C00 + ((uint16_t)i << 5), ROW(i), PW);
            panel_t++;
            return;
        }
        panel_wx -= 8;
        if (panel_wx <= WX_IN) { panel_wx = WX_IN; panel_state = PN_MENU; hud_panel = 1; }
        return;
    case PN_OUT:
        panel_wx += 8;
        if (panel_wx >= WX_OUT) { panel_wx = WX_OUT; panel_state = PN_CLOSED; }
        return;
    case PN_NOTE:
        if (!--panel_t || (pressed & (J_A | J_B))) show_stats();
        return;
    case PN_ASK:
        if (vq_pending()) return;
        if (pressed & (J_LEFT | J_RIGHT)) { panel_yes ^= 1; ask_cursor(); sfx(SFX_BLIP); }
        else if ((pressed & J_B) || ((pressed & J_A) && !panel_yes)) show_stats();
        else if (pressed & J_A) { save_line(MSG_PANEL_SAVING); panel_state = PN_SAVING; }
        return;
    case PN_SAVING:                                           // "Guardando" is on screen: save now
        if (vq_pending()) return;
        game_save();
        sfx(SFX_OK);
        save_line(MSG_PANEL_SAVED);
        panel_t = 60;
        panel_state = PN_SAVED;
        return;
    case PN_SAVED:
        if (!--panel_t) show_stats();
        return;
    }
    if (pressed & J_START) { panel_close(); return; }               // PN_MENU
    r = menu_update();
    if (r == MENU_NONE) return;
    if (r == MENU_BACK || r == P_SALIR) { panel_close(); return; }
    panel_sel = r;
    sfx(SFX_OK);
    if (r == P_GUARDAR) ask_save();
    else if (r == P_ACAMPAR) {
        r = camp_check();
        note(r != 0xFF ? r : MSG_PANEL_SOON);                 // the camp screen is the next module
    } else note(MSG_PANEL_SOON);                              // Cuaderno, Mochila, Equipo, Opciones
}
