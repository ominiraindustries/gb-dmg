// Level map in WRAM, camera and column streaming (GDD §2.0, §2.5, §2.6)
#include <string.h>
#include "game.h"
#include "level1_1.h"

uint8_t level[LEVEL_MAX_COLS * LEVEL_ROWS];   // column-major: (col << 3) | row
uint8_t level_cols;
uint16_t level_px_w;                          // level_cols * 16
uint16_t camera_x, camera_max;
uint8_t scx_shadow;
uint16_t cols_written;                        // next BG tile column to stream (world tile column)

// Column prepared in update(), copied in the next VBlank
uint8_t col_buf[16];
uint8_t *col_dst;
uint8_t col_pending;

#define CAMERA_LEAD   64                      // player stays <= 64 px from the left edge
#define STREAM_AHEAD  21                      // visible tile columns are cam_tile .. cam_tile + 20

uint8_t mt_at(uint16_t x, uint8_t y) {
    uint8_t row;
    if (y < Y_BIAS) return MT_SKY;            // above the level
    row = (uint8_t)(y - Y_BIAS) >> 4;
    if (row >= LEVEL_ROWS) return MT_SKY;     // pit
    if (x >= level_px_w) return MT_HARD;      // invisible wall at the end
    return level[((x >> 4) << 3) | row];
}

uint8_t solid_at(uint16_t x, uint8_t y) {
    return mt_attr[mt_at(x, y)] & ATTR_SOLID;
}

// Fills col_buf with world tile column tc and sets its VRAM destination (ring of 32 columns)
void prepare_column(uint16_t tc) {
    uint8_t r, h = tc & 1;
    const uint8_t *m, *t;
    uint8_t *dst = col_buf;
    if ((tc >> 1) >= level_cols) {
        memset(col_buf, BG_BLANK, 16);
    } else {
        m = &level[(tc >> 1) << 3];
        for (r = 0; r < LEVEL_ROWS; r++) {
            t = mt_tiles[m[r]] + h;
            *dst++ = t[0];
            *dst++ = t[2];
        }
    }
    col_dst = (uint8_t *)(0x9800u + (tc & 31));
    col_pending = 1;
}

// LCD off: copy the map to WRAM and draw the first 22 tile columns
void level_load(void) {
    uint8_t c;
    level_cols = LEVEL1_1_WIDTH;
    level_px_w = (uint16_t)level_cols << 4;
    camera_max = level_px_w - 160;
    memcpy(level, level1_1_map, (uint16_t)level_cols * LEVEL_ROWS);
    camera_x = 0;
    scx_shadow = 0;
    for (c = 0; c <= STREAM_AHEAD; c++) {
        prepare_column(c);
        vram_col16(col_dst, col_buf);
    }
    cols_written = STREAM_AHEAD + 1;
    col_pending = 0;
    // BG rows 30-31 show behind the window HUD (SCY = 0xF0): keep them blank
    memset((uint8_t *)(0x9800u + 30 * 32), BG_BLANK, 64);
}

// After the player moved: follow (never back), clamp, queue at most one new column
void level_update_camera(void) {
    extern uint16_t player_x;
    if (player_x > camera_x + CAMERA_LEAD) {
        camera_x = player_x - CAMERA_LEAD;
        if (camera_x > camera_max) camera_x = camera_max;
    }
    scx_shadow = (uint8_t)camera_x;
    if (!col_pending && cols_written <= (camera_x >> 3) + STREAM_AHEAD) {
        prepare_column(cols_written);
        cols_written++;
    }
}

void level_draw_vram(void) {
    if (col_pending) {
        vram_col16(col_dst, col_buf);
        col_pending = 0;
    }
}
