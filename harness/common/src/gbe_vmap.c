// gbe: vertical metatile map (shmups) - rows of 10 metatiles (20 tiles, the screen width, no
// horizontal scroll), a WRAM ring of the rows near the screen, tile-row streaming into the
// 32-row BG ring, cell changes with queued redraws, scroll stop.
//
// World y grows UP from the bottom of map row 0; scroll_y = world px at the bottom screen line.
// Tile row tr (world px 8tr..8tr+7) lives in BG map row 31 - (tr & 31), so with
// SCY = 112 - scroll_y screen line L shows world px scroll_y + 143 - L.
// Tables from the game: mt_tiles[][4] (TL TR BL BR), as in gbe_map.
#include <string.h>
#include "gbe.h"

#define VM_W      GBE_VMAP_W
#define VM_RING   16                 // metatile rows kept in WRAM (screen shows <= 10)
#define VM_QUEUE  8                  // metatile redraws per frame

uint8_t vmap_ring[VM_RING * VM_W];
const uint8_t *vmap_src;
uint16_t vmap_rows, vmap_mrows, vmap_stop, rows_written, scroll_y;
uint8_t scroll_sub;

uint8_t row_buf[2 * VM_W];           // tile row prepared in the frame, copied in the next VBlank
uint8_t *row_dst;
uint8_t row_pending;

uint8_t *vq_dst[VM_QUEUE];
uint8_t vq_tiles[VM_QUEUE][4];
uint8_t vq_count;

void gbe_vrow_tiles(const uint8_t *m, uint8_t top);   // asm (gbe_vmap.s): fills row_buf

// C reference: the 20 tiles of one half (top = TL TR, bottom = BL BR) of a metatile row
void gbe_vrow_tiles_c(const uint8_t *m, uint8_t top) {
    uint8_t c, *d = row_buf;
    const uint8_t *t;
    for (c = 0; c < VM_W; c++) {
        t = mt_tiles[*m++] + (top ? 0 : 2);
        *d++ = t[0];
        *d++ = t[1];
    }
}

static uint8_t *ring_row(uint16_t r) {
    return &vmap_ring[((uint8_t)r & (VM_RING - 1)) * VM_W];
}

// Prepare tile row tr; the first time a metatile row is needed it is copied into the ring
// (rows past the end read as metatile 0). Objects of rows < vmap_mrows may appear.
static void vmap_row(uint16_t tr) {
    uint16_t r = tr >> 1;
    uint8_t *m = ring_row(r);
    if (r >= vmap_mrows) {
        if (r < vmap_rows) memcpy(m, vmap_src + r * VM_W, VM_W);
        else memset(m, 0, VM_W);
        vmap_mrows = r + 1;
    }
    gbe_vrow_tiles(m, (uint8_t)tr & 1);
    row_dst = (uint8_t *)(0x9800u + ((uint16_t)(31 - ((uint8_t)tr & 31)) << 5));
    row_pending = 1;
}

// LCD off. src: rows * GBE_VMAP_W metatiles, row 0 = bottom. Draws every tile row the screen
// shows at scroll (+ 2 above). stop = scroll_y where vmap_scroll stops (0xFFFF = never).
// Columns 20-31 of the BG are not touched: clear the BG first (init_bkg) to the fill tile.
void vmap_load(const uint8_t *src, uint16_t rows, uint16_t scroll, uint16_t stop) {
    uint16_t tr;
    vmap_src = src;
    vmap_rows = rows;
    vmap_stop = stop;
    scroll_y = scroll;
    scroll_sub = 0;
    vq_count = 0;
    tr = scroll >> 3;
    vmap_mrows = tr >> 1;
    for (; tr <= ((scroll + 143) >> 3) + 1; tr++) {
        vmap_row(tr);
        vram_row20(row_dst, row_buf);
    }
    rows_written = tr;
    row_pending = 0;
    scy_shadow = (uint8_t)(112 - (uint8_t)scroll);
}

// Once per frame: scroll_y += speed (8.8) until vmap_stop, SCY shadow, and at most one new tile
// row (copied by vmap_draw_vram in the next VBlank). Keeps up with speeds <= 8 px/f.
void vmap_scroll(uint16_t speed) {
    uint16_t t;
    if (scroll_y < vmap_stop) {
        t = (uint16_t)scroll_sub + (uint8_t)speed;
        scroll_sub = (uint8_t)t;
        scroll_y += (speed >> 8) + (t >> 8);
        if (scroll_y >= vmap_stop) { scroll_y = vmap_stop; scroll_sub = 0; }
    }
    scy_shadow = (uint8_t)(112 - (uint8_t)scroll_y);
    if (!row_pending && rows_written <= ((scroll_y + 143) >> 3) + 1) {
        vmap_row(rows_written);
        rows_written++;
    }
}

uint8_t vmap_get(uint8_t col, uint16_t row) {
    if (row >= vmap_mrows || row + VM_RING < vmap_mrows) return 0;
    return ring_row(row)[col];
}

// Change a cell in the ring (rows not in the ring are ignored: only change what is near the
// screen). If its tiles are in the BG ring, queue the 4 tiles (copied in VBlank).
void vmap_set(uint8_t col, uint16_t row, uint8_t mt) {
    uint16_t tr = row << 1;
    const uint8_t *t;
    uint8_t *q;
    if (row >= vmap_mrows || row + VM_RING < vmap_mrows) return;
    ring_row(row)[col] = mt;
    if (tr >= rows_written || rows_written > tr + 32) return;   // not drawn / already replaced
    if (vq_count == VM_QUEUE) return;
    t = mt_tiles[mt];
    // top half (tr + 1) is the BG row above the bottom half (tr even: never wraps between them)
    vq_dst[vq_count] = (uint8_t *)(0x9800u + ((uint16_t)(31 - (((uint8_t)tr + 1) & 31)) << 5) + (col << 1));
    q = vq_tiles[vq_count];
    q[0] = t[0]; q[1] = t[1]; q[2] = t[2]; q[3] = t[3];
    vq_count++;
}

void vmap_draw_vram(void) {
    if (row_pending) {
        vram_row20(row_dst, row_buf);
        row_pending = 0;
    }
    if (vq_count) { vram_mt4_list(vq_dst, vq_tiles[0], vq_count); vq_count = 0; }
}
