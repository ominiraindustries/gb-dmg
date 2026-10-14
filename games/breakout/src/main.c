#include <gb/gb.h>
#include <stdint.h>
#include "bg.h"
#include "spr.h"

// Layout in screen pixels. Row 0 = HUD, row 1 = top wall, columns 0 and 19 = side walls.
#define FIELD_LEFT    8
#define FIELD_RIGHT   152          // exclusive
#define FIELD_TOP     16
#define FIELD_BOTTOM  144
#define BRICK_ROW0    3            // first brick tile row
#define BRICK_ROWS    6
#define BRICK_COLS    9            // 16 px bricks between the walls
#define BRICK_COUNT   (BRICK_ROWS * BRICK_COLS)
#define PADDLE_Y      132
#define PADDLE_W      24
#define PADDLE_H      4
#define PADDLE_SPEED  2
#define BALL_SIZE     4
#define TITLE_ROW     10
#define TEXT_ROW      12
#define START_LIVES   3
#define BASE_SPEED    0x0140       // vertical speed in 1/256 px per frame
#define LEVEL_SPEEDUP 0x0020
#define MAX_LEVEL_SPEEDUPS 5

enum { STATE_TITLE, STATE_SERVE, STATE_PLAY, STATE_GAMEOVER, STATE_CLEAR };

// Sprite slots
#define SPR_SLOT_PADDLE 0          // 0..2
#define SPR_SLOT_BALL   3

// Game state. Non-static so tests can read and write it by name.
uint8_t state;
uint8_t keys, prev_keys, pressed;
uint8_t paddle_x;
uint16_t ball_x, ball_y;           // 8.8 fixed point, top-left of the 4x4 ball
int16_t ball_vx, ball_vy;          // 1/256 px per frame
uint16_t speed;                    // current vertical speed magnitude
uint8_t px, py;                    // ball pixel position (integer part)
uint8_t bricks[BRICK_COUNT];       // 0 = broken, else points/10 (top rows are worth more)
uint8_t bricks_left;
uint8_t lives;
uint8_t level;
uint8_t score[5];                  // decimal digits, most significant first
uint8_t frame_start, frame_lines, max_frame_lines;  // profiling, see measure_frame()

// VRAM work queued during the frame and done right after vsync()
#define MAX_CLEARS 4
uint8_t clear_x[MAX_CLEARS], clear_y[MAX_CLEARS], clear_count;
uint8_t hud_dirty;
uint8_t bricks_redraw;             // next brick row to redraw, BRICK_ROWS = done
#define MAX_TEXTS 2
uint8_t text_row[MAX_TEXTS];
const char *text_str[MAX_TEXTS];   // NULL clears the row
uint8_t text_count;

uint8_t row_buf[18];
uint8_t hit_x, hit_y;              // tile of the last brick found by brick_at()

// Horizontal speed by where the ball hits the paddle (7 zones of 4 px)
const int16_t bounce_vx[7] = { -0x01C0, -0x0140, -0x00C0, 0, 0x00C0, 0x0140, 0x01C0 };

// ---------------------------------------------------------------- sound

void sound_init(void) {
    NR52_REG = 0x80;               // APU on first
    NR50_REG = 0x77;
    NR51_REG = 0xFF;
}

void sfx_paddle(void) {            // CH2, ~523 Hz, 62 ms
    NR21_REG = 0xB0; NR22_REG = 0xC1; NR23_REG = 0x05; NR24_REG = 0xC7;
}

void sfx_wall(void) {              // CH2, ~1 kHz, 31 ms
    NR21_REG = 0xB8; NR22_REG = 0x81; NR23_REG = 0x83; NR24_REG = 0xC7;
}

void sfx_brick(void) {             // CH1, ~1.3 kHz, 25% duty
    NR10_REG = 0x00; NR11_REG = 0x70; NR12_REG = 0xD1; NR13_REG = 0x9D; NR14_REG = 0xC7;
}

void sfx_lose(void) {              // CH4 noise rumble
    NR41_REG = 0x00; NR42_REG = 0xF3; NR43_REG = 0x71; NR44_REG = 0x80;
}

// ---------------------------------------------------------------- VRAM queue

void queue_text(uint8_t row, const char *s) {
    if (text_count < MAX_TEXTS) {
        text_row[text_count] = row;
        text_str[text_count] = s;
        text_count++;
    }
}

void draw_text_row(uint8_t row, const char *s) {
    uint8_t i, len = 0, x;
    for (i = 0; i < 18; i++) row_buf[i] = BG_BLANK;
    if (s) {
        while (s[len]) len++;
        x = (18 - len) >> 1;
        for (i = 0; i < len; i++, x++) {
            char c = s[i];
            if (c >= '0' && c <= '9') row_buf[x] = BG_DIGIT0 + (c - '0');
            else if (c >= 'A' && c <= 'Z') row_buf[x] = BG_LETTER_A + (c - 'A');
        }
    }
    set_bkg_tiles(1, row, 18, 1, row_buf);
}

void draw_hud(void) {
    uint8_t i;
    for (i = 0; i < 5; i++) row_buf[i] = BG_DIGIT0 + score[i];
    set_bkg_tiles(1, 0, 5, 1, row_buf);
    for (i = 0; i < 3; i++) row_buf[i] = (lives > 2 - i) ? BG_LIFE : BG_BLANK;
    set_bkg_tiles(16, 0, 3, 1, row_buf);
}

void draw_brick_row(uint8_t row) {
    uint8_t i, *b = &bricks[row * BRICK_COLS];
    uint8_t l = (row & 1) ? BG_BRICK_B_L : BG_BRICK_A_L;
    for (i = 0; i < 18; i += 2, b++) {
        row_buf[i]     = *b ? l : BG_BLANK;
        row_buf[i + 1] = *b ? l + 1 : BG_BLANK;
    }
    set_bkg_tiles(1, BRICK_ROW0 + row, 18, 1, row_buf);
}

// Runs right after vsync(), while the PPU is in VBlank
void draw_vram(void) {
    uint8_t i;
    for (i = 0; i < clear_count; i++) {
        set_bkg_tile_xy(clear_x[i], clear_y[i], BG_BLANK);
        set_bkg_tile_xy(clear_x[i] + 1, clear_y[i], BG_BLANK);
    }
    clear_count = 0;
    if (hud_dirty) {
        draw_hud();
        hud_dirty = 0;
    }
    for (i = 0; i < text_count; i++) draw_text_row(text_row[i], text_str[i]);
    text_count = 0;
    if (bricks_redraw < BRICK_ROWS) draw_brick_row(bricks_redraw++);
}

// ---------------------------------------------------------------- game logic

void add_score(uint8_t tens) {
    uint8_t i = 3;
    score[i] += tens;
    while (score[i] > 9) {
        score[i] -= 10;
        if (i == 0) {              // overflow: cap at 99990
            score[0] = score[1] = score[2] = score[3] = 9;
            break;
        }
        score[--i]++;
    }
    hud_dirty = 1;
}

void start_level(void) {
    uint8_t row, col, *b = bricks;
    for (row = 0; row < BRICK_ROWS; row++)
        for (col = 0; col < BRICK_COLS; col++)
            *b++ = BRICK_ROWS - row;
    bricks_left = BRICK_COUNT;
    bricks_redraw = 0;
    speed = BASE_SPEED + LEVEL_SPEEDUP * (level < MAX_LEVEL_SPEEDUPS ? level : MAX_LEVEL_SPEEDUPS);
}

void serve(void) {
    state = STATE_SERVE;
    queue_text(TEXT_ROW, "PRESS A");
}

void new_game(void) {
    uint8_t i;
    for (i = 0; i < 5; i++) score[i] = 0;
    lives = START_LIVES;
    level = 0;
    hud_dirty = 1;
    start_level();
    queue_text(TITLE_ROW, 0);
    serve();
}

void launch(void) {
    state = STATE_PLAY;
    ball_vx = (paddle_x & 1) ? 0x00C0 : -0x00C0;
    ball_vy = -(int16_t)speed;
    queue_text(TEXT_ROW, 0);
}

void move_paddle(void) {
    if ((keys & J_LEFT) && paddle_x > FIELD_LEFT) paddle_x -= PADDLE_SPEED;
    if ((keys & J_RIGHT) && paddle_x < FIELD_RIGHT - PADDLE_W) paddle_x += PADDLE_SPEED;
}

// Returns the brick index at pixel (x, y) or 0xFF. Sets hit_x/hit_y to its left tile.
uint8_t brick_at(uint8_t x, uint8_t y) {
    uint8_t row = (y >> 3) - BRICK_ROW0;
    uint8_t col = ((x >> 3) - 1) >> 1;
    uint8_t idx;
    if (row >= BRICK_ROWS || col >= BRICK_COLS) return 0xFF;
    idx = row * BRICK_COLS + col;
    if (!bricks[idx]) return 0xFF;
    hit_x = 1 + (col << 1);
    hit_y = BRICK_ROW0 + row;
    return idx;
}

void break_brick(uint8_t idx) {
    add_score(bricks[idx]);
    bricks[idx] = 0;
    bricks_left--;
    if (clear_count < MAX_CLEARS) {
        clear_x[clear_count] = hit_x;
        clear_y[clear_count] = hit_y;
        clear_count++;
    }
    if (bricks_left == BRICK_COUNT * 2 / 3 || bricks_left == BRICK_COUNT / 3) speed += 0x20;
    sfx_brick();
}

void lose_life(void) {
    sfx_lose();
    lives--;
    hud_dirty = 1;
    if (lives == 0) {
        state = STATE_GAMEOVER;
        queue_text(TEXT_ROW, "GAME OVER");
    } else {
        serve();
    }
}

void move_ball(void) {
    uint16_t old;
    uint8_t edge, idx;

    // X axis: walls, then bricks at the leading edge
    old = ball_x;
    ball_x += ball_vx;
    px = ball_x >> 8;
    py = ball_y >> 8;
    if (px < FIELD_LEFT) {
        ball_x = (uint16_t)FIELD_LEFT << 8;
        ball_vx = -ball_vx;
        sfx_wall();
    } else if (px > FIELD_RIGHT - BALL_SIZE) {
        ball_x = (uint16_t)(FIELD_RIGHT - BALL_SIZE) << 8;
        ball_vx = -ball_vx;
        sfx_wall();
    } else {
        edge = ball_vx > 0 ? px + BALL_SIZE - 1 : px;
        idx = brick_at(edge, py);
        if (idx == 0xFF) idx = brick_at(edge, py + BALL_SIZE - 1);
        if (idx != 0xFF) {
            break_brick(idx);
            ball_x = old;
            ball_vx = -ball_vx;
        }
    }
    px = ball_x >> 8;

    // Y axis: top wall, bricks, paddle, bottom
    old = ball_y;
    ball_y += ball_vy;
    py = ball_y >> 8;
    if (py < FIELD_TOP) {
        ball_y = (uint16_t)FIELD_TOP << 8;
        ball_vy = -ball_vy;
        sfx_wall();
    } else if (ball_vy > 0 && py + BALL_SIZE > PADDLE_Y && py < PADDLE_Y + PADDLE_H
               && px + BALL_SIZE > paddle_x && px < paddle_x + PADDLE_W) {
        ball_y = (uint16_t)(PADDLE_Y - BALL_SIZE) << 8;
        ball_vy = -(int16_t)speed;
        idx = (uint8_t)(px + BALL_SIZE - paddle_x) >> 2;   // 1..27 -> zone 0..6
        if (bounce_vx[idx]) ball_vx = bounce_vx[idx];
        else ball_vx = ball_vx < 0 ? -0x0060 : 0x0060;
        sfx_paddle();
    } else if (py >= FIELD_BOTTOM) {
        lose_life();
        return;
    } else {
        edge = ball_vy > 0 ? py + BALL_SIZE - 1 : py;
        idx = brick_at(px, edge);
        if (idx == 0xFF) idx = brick_at(px + BALL_SIZE - 1, edge);
        if (idx != 0xFF) {
            break_brick(idx);
            ball_y = old;
            ball_vy = -ball_vy;
        }
    }

    if (bricks_left == 0) {
        state = STATE_CLEAR;
        queue_text(TEXT_ROW, "STAGE CLEAR");
    }
}

void update(void) {
    switch (state) {
    case STATE_TITLE:
        if (pressed & J_START) new_game();
        break;
    case STATE_SERVE:
        move_paddle();
        ball_x = (uint16_t)(paddle_x + (PADDLE_W - BALL_SIZE) / 2) << 8;
        ball_y = (uint16_t)(PADDLE_Y - BALL_SIZE) << 8;
        if (pressed & J_A) launch();
        break;
    case STATE_PLAY:
        move_paddle();
        move_ball();
        break;
    case STATE_GAMEOVER:
        if (pressed & J_START) new_game();
        break;
    case STATE_CLEAR:
        if (pressed & J_START) {
            level++;
            start_level();
            serve();
        }
        break;
    }
}

void draw_sprites(void) {
    move_sprite(SPR_SLOT_PADDLE,     paddle_x + 8,  (uint8_t)(PADDLE_Y + 16));
    move_sprite(SPR_SLOT_PADDLE + 1, paddle_x + 16, (uint8_t)(PADDLE_Y + 16));
    move_sprite(SPR_SLOT_PADDLE + 2, paddle_x + 24, (uint8_t)(PADDLE_Y + 16));
    if (state == STATE_SERVE || state == STATE_PLAY)
        move_sprite(SPR_SLOT_BALL, (ball_x >> 8) + 8, (ball_y >> 8) + 16);
    else
        hide_sprite(SPR_SLOT_BALL);
}

// Scanlines used since vsync() returned (VBlank starts at LY 144). 255 = missed a frame.
void measure_frame(void) {
    uint8_t ly = LY_REG;
    if ((uint8_t)sys_time != frame_start) frame_lines = 255;
    else frame_lines = ly >= 144 ? ly - 144 : ly + 10;
    if (frame_lines > max_frame_lines) max_frame_lines = frame_lines;
}

// ---------------------------------------------------------------- setup

void init(void) {
    uint8_t row;
    DISPLAY_OFF;
    BGP_REG = OBP0_REG = OBP1_REG = DMG_PALETTE(DMG_WHITE, DMG_LITE_GRAY, DMG_DARK_GRAY, DMG_BLACK);
    set_bkg_data(0, BG_COUNT, bg_tiles);
    set_sprite_data(0, SPR_COUNT, spr_tiles);
    set_sprite_tile(SPR_SLOT_PADDLE, SPR_PADDLE_L);
    set_sprite_tile(SPR_SLOT_PADDLE + 1, SPR_PADDLE_M);
    set_sprite_tile(SPR_SLOT_PADDLE + 2, SPR_PADDLE_R);
    set_sprite_tile(SPR_SLOT_BALL, SPR_BALL);

    init_bkg(BG_BLANK);
    fill_bkg_rect(0, 1, 20, 1, BG_WALL);
    fill_bkg_rect(0, 2, 1, 16, BG_WALL);
    fill_bkg_rect(19, 2, 1, 16, BG_WALL);

    lives = START_LIVES;
    start_level();
    for (row = 0; row < BRICK_ROWS; row++) draw_brick_row(row);
    bricks_redraw = BRICK_ROWS;
    draw_hud();
    draw_text_row(TITLE_ROW, "BREAKOUT");
    draw_text_row(TEXT_ROW, "PRESS START");

    paddle_x = (FIELD_LEFT + FIELD_RIGHT - PADDLE_W) / 2;
    state = STATE_TITLE;
    sound_init();

    SHOW_BKG;
    SHOW_SPRITES;
    DISPLAY_ON;
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
