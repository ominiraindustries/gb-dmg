// gbe: dialogue box in the window - typewriter, pages with a blinking 'more' arrow, speaker tab,
// yes/no question and a 2x2 choice. Text comes from gbe_script (bytes of harness/script.py: lines
// already wrapped, 0x0A new line, 0x0C new page, 0x01 player name, 0 end).
//
// Layout (defaults = games/faro ui.md 4, a 20x6 box at window rows tbox_row..+5): frame pieces
// tbox_frame[9] (TL T TR L blank R BL B BR), text lines at rows +2 and +4 from column 1, speaker tab
// at row 0 from column 3 (blank before and after), arrow at row +5 column 17, yes/no on line 2 at
// columns tbox_yes_col / tbox_no_col, choices at columns 2 and 11 of lines 1-2 (cursor one column
// before). All tiles go through gbe_vq (1-2 per frame while typing, 8 when A finishes a page).
// The game shows the window while tbox_visible (WY = 96 in VBlank) and sets the tile variables.
#include <string.h>
#include "gbe_config.h"
#ifdef GBE_BANKED
#pragma bank 255
#endif
#include "gbe.h"

#define TB_W 20
#define TB_TEXT 256

uint8_t *tbox_win = (uint8_t *)0x9C00;      // window map base
uint8_t tbox_row;                           // box top row in the window map
uint8_t tbox_frame[9];                      // TL T TR L blank R BL B BR
uint8_t tbox_arrow, tbox_cursor;            // 'more' arrow tile, choice cursor tile
uint8_t tbox_speed = 1;                     // frames per character (0 = 2 characters per frame)
uint8_t tbox_yes_col = 3, tbox_no_col = 9;
char tbox_name[8];                          // player name ({N}), zero-terminated
char tbox_text[TB_TEXT];                    // current text (copied in by gbe_script)
char tbox_speaker[13];
uint8_t tbox_state, tbox_visible, tbox_answer, tbox_nchoices;
uint8_t tbox_pos, tbox_line, tbox_col, tbox_timer, tbox_name_i, tbox_fast;
static const char *const yes_no[2] = { "Si", "No" };
static uint8_t choice_at[4];                // text offsets of the choices in tbox_text

static uint8_t *cell(uint8_t row, uint8_t col) {
    return tbox_win + ((uint16_t)(tbox_row + row) << 5) + col;
}

static void draw_frame(void) {
    uint8_t r, row[TB_W];
    row[0] = tbox_frame[0]; memset(row + 1, tbox_frame[1], TB_W - 2); row[TB_W - 1] = tbox_frame[2];
    if (tbox_speaker[0]) {                  // tab: blank, name, blank
        uint8_t n = txt_tiles(row + 3, tbox_speaker, 12);
        row[2] = txt_blank;
        row[3 + n] = txt_blank;
        if (3 + n + 1 < TB_W - 1) memset(row + 4 + n, tbox_frame[1], TB_W - 5 - n);
    }
    vq_push(cell(0, 0), row, TB_W);
    row[0] = tbox_frame[3]; memset(row + 1, tbox_frame[4], TB_W - 2); row[TB_W - 1] = tbox_frame[5];
    for (r = 1; r < 5; r++) vq_push(cell(r, 0), row, TB_W);
    row[0] = tbox_frame[6]; memset(row + 1, tbox_frame[7], TB_W - 2); row[TB_W - 1] = tbox_frame[8];
    vq_push(cell(5, 0), row, TB_W);
}

static void clear_lines(void) {
    vq_push_fill(cell(2, 1), txt_blank, TB_W - 2);
    vq_push_fill(cell(4, 1), txt_blank, TB_W - 2);
}

static void arrow(uint8_t on) {
    uint8_t t = on ? tbox_arrow : tbox_frame[7];
    vq_push(cell(5, 17), &t, 1);
}

// Start showing tbox_text (kind: TB_SAY, TB_ASK, TB_CHOICE). Opens the box if closed.
void tbox_start(uint8_t kind) GBE_FAR {
    if (!tbox_visible) { draw_frame(); tbox_visible = 1; }
    else clear_lines();
    tbox_pos = tbox_line = tbox_col = tbox_name_i = 0;
    tbox_timer = tbox_fast = 0;
    tbox_answer = 0;
    tbox_state = kind;
    if (kind == TB_CHOICE) {                // tbox_text = n zero-terminated options
        uint8_t k, i = 0;
        for (k = 0; k < tbox_nchoices; k++) { choice_at[k] = i; while (tbox_text[i]) i++; i++; }
        tbox_state = TB_CHOOSE;
        tbox_draw_choices();
    }
}

void tbox_speaker_set(const char *s) GBE_FAR {
    strncpy(tbox_speaker, s, 12);           // rare (once per speaker): GBDK strncpy is slow C
    tbox_speaker[12] = 0;
    if (tbox_visible) draw_frame();
}

void tbox_close(void) GBE_FAR {
    tbox_visible = 0;
    tbox_state = TB_CLOSED;
}

// next character to print, expanding the player's name; 0 = end of text
static char next_char(void) {
    char c;
    if (tbox_name_i) {
        c = tbox_name[tbox_name_i - 1];
        if (c) { tbox_name_i++; return c; }
        tbox_name_i = 0;
    }
    c = tbox_text[tbox_pos];
    if (c == 0x01) { tbox_pos++; tbox_name_i = 1; return next_char(); }
    if (c) tbox_pos++;
    return c;
}

static void cursor_at(uint8_t row, uint8_t col, uint8_t on) {
    uint8_t t = on ? tbox_cursor : txt_blank;
    vq_push(cell(row, col), &t, 1);
}

void tbox_draw_choices(void) GBE_FAR {
    uint8_t k, row, col, t[TB_W];
    if (tbox_state == TB_YESNO) {
        for (k = 0; k < 2; k++) {
            col = k ? tbox_no_col : tbox_yes_col;
            txt_tiles(t, yes_no[k], 2);
            vq_push(cell(4, col), t, 2);
            cursor_at(4, col - 1, tbox_answer == k);
        }
        return;
    }
    for (k = 0; k < tbox_nchoices; k++) {
        row = (k & 2) ? 4 : 2;
        col = (k & 1) ? 11 : 2;
        vq_push(cell(row, col), t, txt_tiles(t, tbox_text + choice_at[k], 8));
        cursor_at(row, col - 1, tbox_answer == k);
    }
}

// Once per frame (outside VBlank). Returns 1 while the box needs the player (typing or waiting).
uint8_t tbox_update(void) GBE_FAR {
    uint8_t n, k, t;
    char c;
    switch (tbox_state) {
    case TB_SAY:
    case TB_ASK:
        if (pressed & (J_A | J_B)) tbox_fast = 1;          // finish the page (8 per frame)
        if (tbox_timer && !tbox_fast) { tbox_timer--; return 1; }
        n = tbox_fast ? 8 : (tbox_speed == 0 || (keys & J_A)) ? 2 : 1;
        for (k = 0; k < n; k++) {
            c = next_char();
            if (c == 0 || c == 0x0C) {
                if (tbox_state == TB_ASK && c == 0) {
                    tbox_state = TB_YESNO;
                    tbox_draw_choices();
                } else {
                    tbox_state = c ? TB_PAGE : TB_END;
                    tbox_timer = 0;
                    if (c) arrow(1);
                }
                return 1;
            }
            if (c == 0x0A) { tbox_line++; tbox_col = 0; continue; }
            if (tbox_col < TB_W - 2) {
                t = txt_char(c);
                vq_push(cell(tbox_line ? 4 : 2, 1 + tbox_col), &t, 1);
                tbox_col++;
            }
        }
        tbox_timer = tbox_speed > 1 ? tbox_speed - 1 : 0;
        return 1;
    case TB_PAGE:                            // arrow blinks 16/16 f; A or B: next page
        if (pressed & (J_A | J_B)) {
            arrow(0);
            clear_lines();
            tbox_line = tbox_col = tbox_fast = 0;
            tbox_state = TB_SAY;
            return 1;
        }
        if ((++tbox_timer & 15) == 0) arrow(tbox_timer & 16);
        return 1;
    case TB_END:
        if (pressed & (J_A | J_B)) { tbox_state = TB_OPEN; return 0; }
        return 1;
    case TB_YESNO:
        if (pressed & (J_LEFT | J_RIGHT | J_UP | J_DOWN)) { tbox_answer ^= 1; tbox_draw_choices(); }
        if (pressed & J_A) { tbox_state = TB_OPEN; return 0; }
        if (pressed & J_B) { tbox_answer = 1; tbox_state = TB_OPEN; return 0; }
        return 1;
    case TB_CHOOSE:
        k = tbox_answer;
        if (pressed & (J_LEFT | J_RIGHT)) k ^= 1;
        if (pressed & (J_UP | J_DOWN)) k ^= 2;
        if (k < tbox_nchoices && k != tbox_answer) { tbox_answer = k; tbox_draw_choices(); }
        if (pressed & J_A) { tbox_state = TB_OPEN; return 0; }
        if (pressed & J_B) { tbox_answer = tbox_nchoices - 1; tbox_state = TB_OPEN; return 0; }
        return 1;
    }
    return 0;
}
