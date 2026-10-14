// gbe: side-scrolling metatile map in WRAM, camera and column streaming, cell changes.
// Sizes from gbe_config.h (GBE_MAP_MAX_COLS). Tables from the game: mt_tiles, mt_attr.
#include <string.h>
#include "gbe.h"

#define STREAM_AHEAD 21              // visible tile columns are cam_tile .. cam_tile + 20
#define BLK_QUEUE    8               // metatile redraws per frame (4 was too few: a 2x3 coin group)

uint8_t level[GBE_MAP_MAX_COLS * GBE_MAP_ROWS];   // column-major: (col << 3) | row
uint8_t level_cols, map_wall_mt;
uint16_t level_px_w, camera_x, camera_max, cols_written;

uint8_t col_buf[16];                 // column prepared in the frame, copied in the next VBlank
uint8_t *col_dst;
uint8_t col_pending;

uint8_t *blk_dst[BLK_QUEUE];
uint8_t blk_tiles[BLK_QUEUE][4];
uint8_t blk_count;

void gbe_column_tiles(const uint8_t *m, uint8_t h);   // asm (gbe_map.s): fills col_buf

// ---------------------------------------------------------------- C references (selftest)
uint8_t mt_at_c(uint16_t x, uint8_t y) {
    uint8_t row;
    if (y < GBE_Y_BIAS) return 0;                     // above the map
    row = (uint8_t)(y - GBE_Y_BIAS) >> 4;
    if (row >= GBE_MAP_ROWS) return 0;                // below it (pits)
    if (x >= level_px_w) return map_wall_mt;          // invisible wall at the end
    return level[((x >> 4) << 3) | row];
}

uint8_t solid_at_c(uint16_t x, uint8_t y) {
    return mt_attr[mt_at_c(x, y)] & ATTR_SOLID;
}

void map_column_c(uint16_t tc) {
    uint8_t r, h = tc & 1;
    const uint8_t *m = &level[(tc >> 1) << 3], *t;
    uint8_t *dst = col_buf;
    for (r = 0; r < GBE_MAP_ROWS; r++) {
        t = mt_tiles[m[r]] + h;
        *dst++ = t[0];
        *dst++ = t[2];
    }
}

// ---------------------------------------------------------------- streaming

// Fills col_buf with world tile column tc (blank past the end) and its VRAM destination
// in the 32-column BG ring
void map_column(uint16_t tc) {
    if ((tc >> 1) >= level_cols) memset(col_buf, mt_tiles[0][0], 16);
    else gbe_column_tiles(&level[(tc >> 1) << 3], tc & 1);
    col_dst = (uint8_t *)(0x9800u + (tc & 31));
    col_pending = 1;
}

// LCD off: copy the map to WRAM and draw the 22 tile columns around the camera
void map_load(const uint8_t *src, uint8_t cols, uint16_t cam, uint8_t wall_mt) {
    uint16_t c, first;
    level_cols = cols;
    map_wall_mt = wall_mt;
    // NOT "(uint16_t)cols << 4": SDCC 4.5.1 stored 0 as the high byte here (level_px_w = 128
    // instead of 3200, the whole map read as solid). The multiply compiles correctly; the
    // engine selftest and the platformer tests catch a regression.
    level_px_w = (uint16_t)cols * 16;
    camera_max = level_px_w - 160;
    memcpy(level, src, (uint16_t)cols * GBE_MAP_ROWS);
    if (cam > camera_max) cam = camera_max;
    camera_x = cam;
    scx_shadow = (uint8_t)cam;
    first = cam >> 3;
    for (c = first; c <= first + STREAM_AHEAD; c++) {
        map_column(c);
        vram_col16(col_dst, col_buf);
    }
    cols_written = first + STREAM_AHEAD + 1;
    col_pending = 0;
    blk_count = 0;
}

// Camera follows target_x keeping it <= lead px from the left edge, never goes back,
// clamps at the end, and prepares at most one new column per frame (VBlank budget)
void map_follow(uint16_t target_x, uint8_t lead) {
    if (target_x > camera_x + lead) {
        camera_x = target_x - lead;
        if (camera_x > camera_max) camera_x = camera_max;
    }
    scx_shadow = (uint8_t)camera_x;
    if (!col_pending && cols_written <= (camera_x >> 3) + STREAM_AHEAD) {
        map_column(cols_written);
        cols_written++;
    }
}

// Change a cell; if it is already in the VRAM ring, queue its 4 tiles (prepared here, copied
// in VBlank). Otherwise streaming will read the new value later.
void map_set(uint8_t col, uint8_t row, uint8_t mt) {
    uint16_t tc = (uint16_t)col << 1;
    const uint8_t *t = mt_tiles[mt];
    uint8_t *q;
    level[(tc << 2) | row] = mt;
    if (tc + 1 >= cols_written || tc + 32 < cols_written) return;
    if (blk_count == BLK_QUEUE) return;
    blk_dst[blk_count] = (uint8_t *)(0x9800u + ((uint16_t)row << 6) + (tc & 31));
    q = blk_tiles[blk_count];
    q[0] = t[0]; q[1] = t[1]; q[2] = t[2]; q[3] = t[3];
    blk_count++;
}

void map_draw_vram(void) {
    if (col_pending) {
        vram_col16(col_dst, col_buf);
        col_pending = 0;
    }
    if (blk_count) { vram_mt4_list(blk_dst, blk_tiles[0], blk_count); blk_count = 0; }
}
