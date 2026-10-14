#include <gb/gb.h>
#include <gb/metasprites.h>  // hide_sprites_range
#include <stdint.h>
#include <rand.h>
#include <string.h>
#include "bg.h"
#include "font.h"

// Screen layout (tiles): cols 0-1 wall, 2-11 well, 12 wall, 13-19 panel
#define WELL_X        2
#define WELL_W        10
#define WELL_H        18
#define CELLS         (WELL_W * WELL_H)
#define PANEL_X       13
#define SPAWN_X       3
#define SPAWN_Y       0
#define NEXT_PX       112           // pixel position of the next-piece preview box
#define NEXT_PY       96

// Feel
#define DAS_DELAY     16            // frames before auto-repeat
#define DAS_RATE      6             // frames per auto-repeat step
#define SOFT_DROP     2             // frames per row while soft dropping
#define LOCK_DELAY    30            // frames on the ground before locking
#define MAX_LOCK_RESETS 15          // moves/rotations that restart the lock delay
#define CLEAR_FRAMES  24            // line clear flash duration
#define CURTAIN_RATE  2             // frames per row of the game over curtain
#define MAX_LEVEL     99
#define ROWS_PER_FRAME 4            // well rows copied to VRAM per VBlank

#define TILE_DIGIT0   (BG_COUNT + FONT_DIGIT0)
#define TILE_LETTER_A (BG_COUNT + FONT_LETTER_A)

enum { STATE_TITLE, STATE_PLAY, STATE_CLEARING, STATE_REDRAW, STATE_PAUSE,
       STATE_CURTAIN, STATE_GAMEOVER };
enum { PIECE_I, PIECE_J, PIECE_L, PIECE_O, PIECE_S, PIECE_T, PIECE_Z };

#define SLOT_PIECE 0                // sprites 0-3: falling piece
#define SLOT_NEXT  4                // sprites 4-7: next piece preview

// SRS shapes: [piece][rotation][cell] = (y << 2) | x inside the piece box.
// Generated from the spawn shapes by rotating clockwise (x, y) -> (n-1-y, x).
const uint8_t shapes[7][4][4] = {
    { {0x4,0x5,0x6,0x7}, {0x2,0x6,0xA,0xE}, {0x8,0x9,0xA,0xB}, {0x1,0x5,0x9,0xD} },  // I
    { {0x0,0x4,0x5,0x6}, {0x1,0x2,0x5,0x9}, {0x4,0x5,0x6,0xA}, {0x1,0x5,0x8,0x9} },  // J
    { {0x2,0x4,0x5,0x6}, {0x1,0x5,0x9,0xA}, {0x4,0x5,0x6,0x8}, {0x0,0x1,0x5,0x9} },  // L
    { {0x1,0x2,0x5,0x6}, {0x1,0x2,0x5,0x6}, {0x1,0x2,0x5,0x6}, {0x1,0x2,0x5,0x6} },  // O
    { {0x1,0x2,0x4,0x5}, {0x1,0x5,0x6,0xA}, {0x5,0x6,0x8,0x9}, {0x0,0x4,0x5,0x9} },  // S
    { {0x1,0x4,0x5,0x6}, {0x1,0x5,0x6,0x9}, {0x4,0x5,0x6,0x9}, {0x1,0x4,0x5,0x9} },  // T
    { {0x0,0x1,0x5,0x6}, {0x2,0x5,0x6,0x9}, {0x4,0x5,0x9,0xA}, {0x1,0x4,0x5,0x8} },  // Z
};

// SRS wall kicks as (dx, dy) with y pointing down. Order of transitions:
// 0->R, R->0, R->2, 2->R, 2->L, L->2, L->0, 0->L. CW from r: r*2, CCW from r: (r*2+7)&7.
const int8_t kicks_jlstz[8][5][2] = {
    { {0,0}, {-1,0}, {-1,-1}, {0, 2}, {-1, 2} },
    { {0,0}, { 1,0}, { 1, 1}, {0,-2}, { 1,-2} },
    { {0,0}, { 1,0}, { 1, 1}, {0,-2}, { 1,-2} },
    { {0,0}, {-1,0}, {-1,-1}, {0, 2}, {-1, 2} },
    { {0,0}, { 1,0}, { 1,-1}, {0, 2}, { 1, 2} },
    { {0,0}, {-1,0}, {-1, 1}, {0,-2}, {-1,-2} },
    { {0,0}, {-1,0}, {-1, 1}, {0,-2}, {-1,-2} },
    { {0,0}, { 1,0}, { 1,-1}, {0, 2}, { 1, 2} },
};
const int8_t kicks_i[8][5][2] = {
    { {0,0}, {-2,0}, { 1,0}, {-2, 1}, { 1,-2} },
    { {0,0}, { 2,0}, {-1,0}, { 2,-1}, {-1, 2} },
    { {0,0}, {-1,0}, { 2,0}, {-1,-2}, { 2, 1} },
    { {0,0}, { 1,0}, {-2,0}, { 1, 2}, {-2,-1} },
    { {0,0}, { 2,0}, {-1,0}, { 2,-1}, {-1, 2} },
    { {0,0}, {-2,0}, { 1,0}, {-2, 1}, { 1,-2} },
    { {0,0}, { 1,0}, {-2,0}, { 1, 2}, {-2,-1} },
    { {0,0}, {-1,0}, { 2,0}, {-1,-2}, { 2, 1} },
};

// Frames per row by level (original Game Boy Tetris), level 20+ uses the last entry
const uint8_t gravity_table[21] = {
    53, 49, 45, 41, 37, 33, 28, 22, 17, 11, 10, 9, 8, 7, 6, 6, 5, 5, 4, 4, 3
};

// Line clear points (40, 100, 300, 1200) as packed BCD, little-endian; times (level + 1)
const uint8_t clear_points[4][3] = {
    {0x40, 0x00, 0x00}, {0x00, 0x01, 0x00}, {0x00, 0x03, 0x00}, {0x00, 0x12, 0x00}
};

#include "bcd.h"                    // bcd_add3: shared asm packed BCD add (harness/common/src)

const uint8_t blank_row[WELL_W] = { 0 };   // BG_BLANK

const uint8_t row_off[WELL_H] = {
    0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 170
};

// Game state. Non-static so tests can read and write it by name.
uint8_t state;
uint8_t keys, prev_keys, pressed;
uint8_t board[CELLS];               // tile index per cell, BG_BLANK = empty
uint8_t piece_type, piece_rot, next_type;
int8_t piece_x, piece_y, lowest_y;
uint8_t bag[7], bag_pos;
uint8_t gravity_timer, lock_timer, lock_resets, das_timer, down_locked;
int8_t das_dir;
uint8_t start_level, level, lines_to_next;
uint8_t score[3];                   // packed BCD, little-endian (score[0] = lowest 2 digits)
uint8_t lines[3];
uint8_t full[WELL_H], clear_count, anim_timer, flash_on, curtain_row;
uint8_t frame_start, frame_lines, max_frame_lines, skip_measure;

// VRAM work done right after vsync()
uint8_t row_dirty[WELL_H];           // row is in dirty_list
uint8_t dirty_list[WELL_H], dirty_head, dirty_count;  // FIFO of rows to copy (no scanning)
uint8_t vram_late;                  // times VRAM work ended outside VBlank (must stay 0)
// Rule: tiles are prepared outside VBlank; draw_vram() only copies them.
uint8_t hud_dirty;
uint8_t hud_buf[11];                // score (6), level (2), lines (3) as tiles
#define MAX_TEXTS 6
uint8_t text_x[MAX_TEXTS], text_y[MAX_TEXTS], text_w[MAX_TEXTS], text_head, text_count;
uint8_t text_tiles[MAX_TEXTS][WELL_W];  // FIFO of prepared text rows
uint8_t row_buf[WELL_W];

// Asm 10-tile copy (src/vram.s), ~3x faster than vram_row(). Same VBlank-only rule.
void vram_copy10(uint8_t *dst, const uint8_t *src);
#define WELL_ROW_VRAM(r) ((uint8_t *)(0x9800u + ((uint16_t)(r) << 5) + WELL_X))

void mark_row(uint8_t r) {
    uint8_t slot;
    if (row_dirty[r]) return;
    row_dirty[r] = 1;
    slot = dirty_head + dirty_count;
    if (slot >= WELL_H) slot -= WELL_H;
    dirty_list[slot] = r;
    dirty_count++;
}

// Copies n tiles into the BG map at (x, y). Only call with the LCD off or during VBlank:
// writes in mode 3 are silently lost. Much faster than set_bkg_tiles (no STAT waits).
void vram_row(uint8_t x, uint8_t y, const uint8_t *src, uint8_t n) {
    uint8_t *dst = (uint8_t *)(0x9800u + ((uint16_t)y << 5) + x);
    do *dst++ = *src++; while (--n);
}

void game_over(void);
void hide_piece(void);
void title_screen(void);

// ---------------------------------------------------------------- sound

void sound_init(void) {
    NR52_REG = 0x80;
    NR50_REG = 0x77;
    NR51_REG = 0xFF;
}

void sfx_move(void)     { NR21_REG = 0xBC; NR22_REG = 0x61; NR23_REG = 0x00; NR24_REG = 0xC6; }
void sfx_rotate(void)   { NR21_REG = 0xB8; NR22_REG = 0x81; NR23_REG = 0x40; NR24_REG = 0xC7; }
void sfx_lock(void)     { NR41_REG = 0x38; NR42_REG = 0x81; NR43_REG = 0x50; NR44_REG = 0xC0; }
void sfx_drop(void)     { NR41_REG = 0x30; NR42_REG = 0xA2; NR43_REG = 0x61; NR44_REG = 0xC0; }
void sfx_line(void)     { NR10_REG = 0x15; NR11_REG = 0x80; NR12_REG = 0xF3; NR13_REG = 0x00; NR14_REG = 0x86; }
void sfx_tetris(void)   { NR10_REG = 0x16; NR11_REG = 0x80; NR12_REG = 0xF6; NR13_REG = 0x00; NR14_REG = 0x85; }
void sfx_gameover(void) { NR41_REG = 0x00; NR42_REG = 0xF3; NR43_REG = 0x71; NR44_REG = 0x80; }

// ---------------------------------------------------------------- VRAM

// Renders s centered in w tiles (w <= WELL_W); NULL gives a blank row
void render_text(uint8_t *dst, uint8_t w, const char *s) {
    uint8_t i, len = 0;
    for (i = 0; i < w; i++) dst[i] = BG_BLANK;
    if (s) {
        while (s[len]) len++;
        dst += (w - len) >> 1;
        for (i = 0; i < len; i++, dst++) {
            char c = s[i];
            if (c >= '0' && c <= '9') *dst = TILE_DIGIT0 + (c - '0');
            else if (c >= 'A' && c <= 'Z') *dst = TILE_LETTER_A + (c - 'A');
        }
    }
}

void queue_text(uint8_t x, uint8_t y, uint8_t w, const char *s) {
    uint8_t slot = text_head + text_count;
    if (text_count == MAX_TEXTS) return;
    if (slot >= MAX_TEXTS) slot -= MAX_TEXTS;
    text_x[slot] = x;
    text_y[slot] = y;
    text_w[slot] = w;
    render_text(text_tiles[slot], w, s);
    text_count++;
}

// Copies the oldest queued text to VRAM (VBlank or LCD off only)
void draw_next_text(void) {
    vram_row(text_x[text_head], text_y[text_head], text_tiles[text_head], text_w[text_head]);
    if (++text_head == MAX_TEXTS) text_head = 0;
    text_count--;
}

// LCD off only
void draw_text(uint8_t x, uint8_t y, uint8_t w, const char *s) {
    render_text(row_buf, w, s);
    vram_row(x, y, row_buf, w);
}

// Right-aligned BCD number with leading zeros blanked
void render_bcd(uint8_t *dst, const uint8_t *d, uint8_t n) {
    uint8_t i, lead = 1;
    for (i = 0; i < n; i++) {
        if (d[i] || i == n - 1) lead = 0;
        dst[i] = lead ? BG_BLANK : TILE_DIGIT0 + d[i];
    }
}

// Call whenever score, level or lines change (outside VBlank)
void update_hud(void) {
    uint8_t lv[2], sc[6], i;
    for (i = 0; i < 3; i++) {
        sc[4 - (i << 1)] = score[i] >> 4;
        sc[5 - (i << 1)] = score[i] & 0x0F;
    }
    lv[0] = 0;
    lv[1] = level;
    while (lv[1] > 9) { lv[1] -= 10; lv[0]++; }
    render_bcd(hud_buf, sc, 6);
    render_bcd(hud_buf + 6, lv, 2);
    render_bcd(hud_buf + 8, lines, 3);
    hud_dirty = 1;
}

void draw_hud(void) {
    vram_row(PANEL_X, 2, hud_buf, 6);
    vram_row(PANEL_X + 4, 5, hud_buf + 6, 2);
    vram_row(PANEL_X + 3, 8, hud_buf + 8, 3);
}

void draw_row(uint8_t r) {
    if (flash_on && full[r]) {
        vram_copy10(WELL_ROW_VRAM(r), blank_row);
    } else {
        vram_copy10(WELL_ROW_VRAM(r), &board[row_off[r]]);
    }
}

// Runs right after vsync(), while the PPU is in VBlank
void draw_vram(void) {
    uint8_t r, n = 0;
    if (dirty_count) {              // well rows first
        do {
            r = dirty_list[dirty_head];
            if (++dirty_head == WELL_H) dirty_head = 0;
            row_dirty[r] = 0;
            draw_row(r);
            n++;
        } while (--dirty_count && n < ROWS_PER_FRAME);
    } else if (hud_dirty) {         // then the HUD, then one text per frame
        draw_hud();
        hud_dirty = 0;
    } else if (text_count) {
        draw_next_text();
    }
    if (LY_REG < 144) vram_late++;
}

// ---------------------------------------------------------------- scoring

void add_bcd(uint8_t *d, uint8_t n, const uint8_t *add) {
    uint8_t carry = 0;
    while (n--) {
        d[n] += add[n] + carry;
        carry = 0;
        if (d[n] > 9) { d[n] -= 10; carry = 1; }
    }
    if (carry) {                    // overflow: cap at all nines
        for (n = 0; n < 3; n++) d[n] = 9;
    }
}

void add_points(uint8_t n) {        // drop points, n < 100
    uint8_t add[3] = {0, 0, 0};
    while (n >= 10) { n -= 10; add[0] += 0x10; }
    add[0] |= n;
    bcd_add3(score, add);
    update_hud();
}

void score_lines(void) {
    uint8_t i, m, add[3] = {0, 0, 0}, term[3];
    // points x (level + 1) by double-and-add: at most 7 doublings instead of level+1 additions
    // (QA measured a 4-line clear at level 99 using 149 of 154 scanlines with the plain loop)
    for (i = 0; i < 3; i++) term[i] = clear_points[clear_count - 1][i];
    for (m = level + 1; m; m >>= 1) {
        if (m & 1) bcd_add3(score, term);
        if (m > 1) bcd_add3(term, term);
    }
    add[2] = clear_count;
    add_bcd(lines, 3, add);
    if (lines_to_next <= clear_count) {
        if (level < MAX_LEVEL) level++;  // the HUD shows 2 digits
        lines_to_next += 10;
    }
    lines_to_next -= clear_count;
    update_hud();
}

// ---------------------------------------------------------------- pieces

uint8_t bag_next(void) {
    uint8_t i, j, t;
    if (bag_pos >= 7) {
        for (i = 0; i < 7; i++) bag[i] = i;
        for (i = 6; i > 0; i--) {   // Fisher-Yates
            // smallest mask covering 0..i halves the rejected rand() calls
            t = i >= 4 ? 7 : (i >= 2 ? 3 : 1);
            do j = rand() & t; while (j > i);
            t = bag[i]; bag[i] = bag[j]; bag[j] = t;
        }
        bag_pos = 0;
    }
    return bag[bag_pos++];
}

// Slow general case, also handles cells above the well (y < 0)
uint8_t fits_slow(uint8_t rot, int8_t x, int8_t y) {
    const uint8_t *c = shapes[piece_type][rot];
    uint8_t i;
    int8_t cx, cy;
    for (i = 0; i < 4; i++, c++) {
        cx = x + (*c & 3);
        cy = y + (*c >> 2);
        if ((uint8_t)cx >= WELL_W) return 0;   // negative wraps to >= 128
        if (cy >= WELL_H) return 0;
        if (cy >= 0 && board[row_off[cy] + cx] != BG_BLANK) return 0;
    }
    return 1;
}

// Cache of the shape being tested: board offsets (dy * 10 + dx) and extents.
// Decoding the shape on every call cost ~2050 T; the cached path is a few hundred.
uint8_t shape_key = 0xFF, shape_off[4], shape_minx, shape_maxx, shape_maxy;

void cache_shape(uint8_t key, uint8_t rot) {
    const uint8_t *c = shapes[piece_type][rot];
    uint8_t i, dx, dy;
    shape_key = key;
    shape_minx = 3;
    shape_maxx = shape_maxy = 0;
    for (i = 0; i < 4; i++, c++) {
        dx = *c & 3;
        dy = *c >> 2;
        shape_off[i] = row_off[dy] + dx;
        if (dx < shape_minx) shape_minx = dx;
        if (dx > shape_maxx) shape_maxx = dx;
        if (dy > shape_maxy) shape_maxy = dy;
    }
}

uint8_t fits(uint8_t rot, int8_t x, int8_t y) {
    uint8_t key = (piece_type << 2) | rot;
    const uint8_t *b;
    if (y < 0) return fits_slow(rot, x, y);
    if (key != shape_key) cache_shape(key, rot);
    if (x + (int8_t)shape_minx < 0 || x + (int8_t)shape_maxx >= WELL_W
        || y + (int8_t)shape_maxy >= WELL_H) return 0;
    b = board + row_off[y] + x;
    return !(b[shape_off[0]] | b[shape_off[1]] | b[shape_off[2]] | b[shape_off[3]]);  // BG_BLANK == 0
}

uint8_t grounded(void) {
    return !fits(piece_rot, piece_x, piece_y + 1);
}

// A successful move or rotation on the ground restarts the lock delay (limited)
void moved(void) {
    if (lock_timer && lock_resets < MAX_LOCK_RESETS) {
        lock_timer = 0;
        lock_resets++;
    }
}

void shift(int8_t dx) {
    if (fits(piece_rot, piece_x + dx, piece_y)) {
        piece_x += dx;
        sfx_move();
        moved();
    }
}

void rotate(uint8_t cw) {
    uint8_t rot, k;
    const int8_t (*kick)[2];
    if (piece_type == PIECE_O) return;
    rot = (piece_rot + (cw ? 1 : 3)) & 3;
    k = cw ? piece_rot << 1 : ((piece_rot << 1) + 7) & 7;
    kick = piece_type == PIECE_I ? kicks_i[k] : kicks_jlstz[k];
    for (k = 0; k < 5; k++, kick++) {
        if (fits(rot, piece_x + (*kick)[0], piece_y + (*kick)[1])) {
            piece_x += (*kick)[0];
            piece_y += (*kick)[1];
            piece_rot = rot;
            sfx_rotate();
            moved();
            return;
        }
    }
}

void spawn(void) {
    piece_type = next_type;
    next_type = bag_next();
    piece_rot = 0;
    piece_x = SPAWN_X;
    piece_y = SPAWN_Y;
    lowest_y = SPAWN_Y;
    gravity_timer = lock_timer = lock_resets = 0;
    down_locked = (keys & J_DOWN) ? 1 : 0;   // soft drop must be re-pressed for each piece
    const uint8_t *c = shapes[next_type][0];
    for (uint8_t i = 0; i < 4; i++, c++) {
        set_sprite_tile(SLOT_PIECE + i, BG_BLOCK_I + piece_type);
        set_sprite_tile(SLOT_NEXT + i, BG_BLOCK_I + next_type);
        move_sprite(SLOT_NEXT + i, ((*c & 3) << 3) + (NEXT_PX + 8), ((*c >> 2) << 3) + (NEXT_PY + 16));
    }
    if (!fits(piece_rot, piece_x, piece_y)) {
        game_over();
        return;
    }
    state = STATE_PLAY;
}

uint8_t row_full(uint8_t r) {
    uint8_t i, *b = &board[row_off[r]];
    for (i = 0; i < WELL_W; i++)
        if (b[i] == BG_BLANK) return 0;
    return 1;
}

void lock_piece(void) {
    const uint8_t *c = shapes[piece_type][piece_rot];
    uint8_t i, tile = BG_BLOCK_I + piece_type, above = 0;
    int8_t cy;
    for (i = 0; i < 4; i++, c++) {
        cy = piece_y + (*c >> 2);
        if (cy < 0) {
            above = 1;
            continue;
        }
        board[row_off[cy] + piece_x + (*c & 3)] = tile;
        mark_row(cy);
    }
    if (above) {                    // locked partly above the well
        game_over();
        return;
    }
    clear_count = 0;
    for (cy = piece_y < 0 ? 0 : piece_y; cy < piece_y + 4 && cy < WELL_H; cy++) {
        if (row_full(cy)) {
            full[cy] = 1;
            clear_count++;
        }
    }
    if (clear_count) {
        state = STATE_CLEARING;
        hide_piece();               // the piece is part of the board now
        anim_timer = 0;
        flash_on = 0;
        if (clear_count == 4) sfx_tetris(); else sfx_line();
    } else {
        sfx_lock();
        spawn();
    }
}

// Removes full rows, moving the rows above down. Walks bottom-up with pointers:
// indexing board[row_off[w] + i] with int8_t rows cost ~466 T per byte (measured).
void collapse(void) {
    uint8_t r = WELL_H, i, lowest = 0, found = 0;
    uint8_t *src = &board[CELLS], *dst = &board[CELLS];
    while (r) {
        r--;
        src -= WELL_W;
        if (full[r]) {
            if (!found) { lowest = r; found = 1; }
            full[r] = 0;
        } else {
            dst -= WELL_W;
            if (dst != src) memcpy(dst, src, WELL_W);
        }
    }
    if (dst != board) memset(board, BG_BLANK, dst - board);
    for (i = 0; i <= lowest; i++) mark_row(i);
}

// ---------------------------------------------------------------- states

void hide_piece(void) {
    hide_sprites_range(SLOT_PIECE, SLOT_PIECE + 4);
}

void game_over(void) {
    state = STATE_CURTAIN;
    curtain_row = 0;
    anim_timer = 0;
    hide_sprites_range(SLOT_PIECE, SLOT_NEXT + 4);
    sfx_gameover();
}

void new_game(void) {
    uint8_t i;
    initrand(((uint16_t)DIV_REG << 8) | (uint8_t)sys_time);
    for (i = 0; i < 3; i++) score[i] = 0;
    for (i = 0; i < 3; i++) lines[i] = 0;
    level = start_level;
    lines_to_next = 10;
    update_hud();
    text_head = text_count = 0;     // drop pending title texts: the 5 clears below cover them
    for (i = 0; i < 4; i++) queue_text(WELL_X, 4 + (i << 2), WELL_W, 0);   // clear title texts
    queue_text(WELL_X, 9, WELL_W, 0);
    bag_pos = 7;
    next_type = bag_next();
    spawn();
}

void show_level_select(void) {
    static char digit[2];
    digit[0] = '0' + start_level;
    digit[1] = 0;
    queue_text(WELL_X, 9, WELL_W, digit);
}

void update_play(void) {
    uint8_t soft, rows;

    if (pressed & J_START) {
        state = STATE_PAUSE;
        hide_piece();
        queue_text(PANEL_X, 15, 7, "PAUSE");
        return;
    }
    if (pressed & J_A) rotate(1);
    if (pressed & J_B) rotate(0);

    // Auto-repeat follows the most recently pressed direction
    if (pressed & J_LEFT) { das_dir = -1; das_timer = 0; shift(-1); }
    else if (pressed & J_RIGHT) { das_dir = 1; das_timer = 0; shift(1); }
    else if (keys & (J_LEFT | J_RIGHT)) {
        if (!(keys & (das_dir < 0 ? J_LEFT : J_RIGHT))) {   // released it, the other is still held
            das_dir = -das_dir;
            das_timer = 0;
        }
        if (++das_timer >= DAS_DELAY) {
            das_timer = DAS_DELAY - DAS_RATE;
            shift(das_dir);
        }
    }

    if (pressed & J_UP) {           // hard drop
        rows = 0;
        while (fits(piece_rot, piece_x, piece_y + 1)) {
            piece_y++;
            rows++;
        }
        if (rows) add_points(rows << 1);
        sfx_drop();
        lock_piece();
        return;
    }

    if (!(keys & J_DOWN)) down_locked = 0;
    soft = (keys & J_DOWN) && !down_locked;
    if (++gravity_timer >= (soft ? SOFT_DROP : gravity_table[level < 20 ? level : 20])) {
        gravity_timer = 0;
        if (fits(piece_rot, piece_x, piece_y + 1)) {
            piece_y++;
            if (soft) add_points(1);
        } else if (soft) {
            lock_piece();
            return;
        }
    }

    if (piece_y > lowest_y) {       // reaching a new row gives the lock resets back
        lowest_y = piece_y;
        lock_resets = 0;
    }
    if (grounded()) {
        if (++lock_timer >= LOCK_DELAY) lock_piece();
    } else if (lock_resets < MAX_LOCK_RESETS) {
        lock_timer = 0;             // airborne: restart, unless resets are used up (else a floor
    }                               // kick that lifts the piece one row could stall it forever)
}

void update(void) {
    uint8_t r;
    switch (state) {
    case STATE_TITLE:
        if ((pressed & J_LEFT) && start_level > 0) { start_level--; show_level_select(); }
        if ((pressed & J_RIGHT) && start_level < 9) { start_level++; show_level_select(); }
        if (pressed & J_START) new_game();
        break;
    case STATE_PLAY:
        update_play();
        break;
    case STATE_CLEARING:
        anim_timer++;
        if ((anim_timer & 3) == 0) {
            flash_on ^= 1;
            for (r = 0; r < WELL_H; r++)
                if (full[r]) mark_row(r);
        }
        if (anim_timer >= CLEAR_FRAMES) {
            flash_on = 0;
            score_lines();
            collapse();
            state = STATE_REDRAW;
        }
        break;
    case STATE_REDRAW:
        if (!dirty_count) spawn();
        break;
    case STATE_PAUSE:
        if (pressed & J_START) {
            state = STATE_PLAY;
            queue_text(PANEL_X, 15, 7, 0);
        }
        break;
    case STATE_CURTAIN:
        if (++anim_timer >= CURTAIN_RATE) {
            anim_timer = 0;
            for (r = 0; r < WELL_W; r++) board[row_off[curtain_row] + r] = BG_WALL;
            mark_row(curtain_row);
            if (++curtain_row == WELL_H) {
                state = STATE_GAMEOVER;
                queue_text(WELL_X, 7, WELL_W, "GAME");
                queue_text(WELL_X, 8, WELL_W, "OVER");
                queue_text(WELL_X, 11, WELL_W, "PRESS");
                queue_text(WELL_X, 12, WELL_W, "START");
            }
        }
        break;
    case STATE_GAMEOVER:
        if (pressed & J_START) title_screen();
        break;
    }
}

void draw_sprites(void) {
    const uint8_t *c;
    uint8_t i;
    int8_t cy;
    if (state == STATE_PLAY) {
        c = shapes[piece_type][piece_rot];
        for (i = 0; i < 4; i++, c++) {
            cy = piece_y + (*c >> 2);
            if (cy < 0) hide_sprite(SLOT_PIECE + i);
            else move_sprite(SLOT_PIECE + i, ((piece_x + (*c & 3)) << 3) + (WELL_X * 8 + 8),
                             (cy << 3) + 16);
        }
    }
}

// Scanlines used since vsync() returned (VBlank starts at LY 144). 255 = missed a frame.
void measure_frame(void) {
    uint8_t ly = LY_REG;
    if (skip_measure) {             // frame spent redrawing with the LCD off on purpose
        skip_measure = 0;
        return;
    }
    if ((uint8_t)sys_time != frame_start) frame_lines = 255;
    else frame_lines = ly >= 144 ? ly - 144 : ly + 10;
    if (frame_lines > max_frame_lines) max_frame_lines = frame_lines;
}

// ---------------------------------------------------------------- setup

// Full screen redraw with the LCD off: walls, empty well, panel, title texts
void title_screen(void) {
    uint8_t i;
    DISPLAY_OFF;
    hide_sprites_range(0, 8);
    init_bkg(BG_BLANK);
    fill_bkg_rect(0, 0, 2, 18, BG_WALL);
    fill_bkg_rect(12, 0, 1, 18, BG_WALL);
    for (i = 0; i < CELLS; i++) board[i] = BG_BLANK;
    for (i = 0; i < WELL_H; i++) row_dirty[i] = full[i] = 0;
    dirty_head = dirty_count = 0;
    draw_text(PANEL_X, 1, 7, "SCORE");
    draw_text(PANEL_X, 4, 7, "LEVEL");
    draw_text(PANEL_X, 7, 7, "LINES");
    draw_text(PANEL_X, 10, 7, "NEXT");
    update_hud();
    draw_hud();
    hud_dirty = 0;
    draw_text(WELL_X, 4, WELL_W, "BLOCKS");
    draw_text(WELL_X, 8, WELL_W, "LEVEL");
    draw_text(WELL_X, 12, WELL_W, "PRESS");
    draw_text(WELL_X, 16, WELL_W, "START");
    text_head = text_count = 0;
    show_level_select();
    while (text_count) draw_next_text();
    state = STATE_TITLE;
    skip_measure = 1;
    DISPLAY_ON;
}

void init(void) {
    DISPLAY_OFF;
    BGP_REG = OBP0_REG = OBP1_REG = DMG_PALETTE(DMG_WHITE, DMG_LITE_GRAY, DMG_DARK_GRAY, DMG_BLACK);
    set_bkg_data(0, BG_COUNT, bg_tiles);
    set_bkg_data(BG_COUNT, FONT_COUNT, font_tiles);
    set_sprite_data(0, BG_COUNT, bg_tiles);
    sound_init();
    SHOW_BKG;
    SHOW_SPRITES;
    title_screen();
}

void main(void) {
    init();
    while (1) {
        vsync();
        frame_start = (uint8_t)sys_time;
        draw_vram();
        prev_keys = keys;
        keys = joypad();
        pressed = keys & ~prev_keys;
        update();
        draw_sprites();
        measure_frame();
    }
}
