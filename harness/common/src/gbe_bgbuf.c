// gbe: double buffer with the two BG maps ($9800 / $9C00, LCDC bit 3). A WRAM canvas (20 tiles
// wide) is copied into the hidden map a few rows per VBlank; when the last row is copied, still
// in VBlank, LCDC bit 3 flips and the whole new picture appears at once (no tearing, no LCD off).
// The window may use rows 0-5 of $9C00 (HUD at the bottom): keep the canvas rows elsewhere.
// Measured in games/dungeon (12 rows x 20 tiles): see harness/common/README.md.
#include "gbe.h"

uint8_t bg_front;                   // 0: $9800 visible, 1: $9C00 visible
void bgbuf_copy_rows(uint8_t *dst, const uint8_t *src, uint8_t rows);   // asm (gbe_view.s), 20 T/tile
uint8_t bgbuf_rows_left, bgbuf_rows_per = 4, view_flips;
uint8_t bgbuf_flip_xor;             // extra LCDC bits toggled in the flip VBlank (e.g. the window
                                    // off for a full-screen map), cleared after use
static const uint8_t *bb_src;
static uint8_t *bb_dst;

// Start copying `rows` rows of 20 tiles from src into map row dst_row of the hidden map
void bgbuf_start(const uint8_t *src, uint8_t rows, uint8_t dst_row) {
    bb_src = src;
    bb_dst = (uint8_t *)(bg_front ? 0x9800u : 0x9C00u) + ((uint16_t)dst_row << 5);
    bgbuf_rows_left = rows;
}

// VBlank: copy up to bgbuf_rows_per rows; flip the visible map after the last one
void bgbuf_draw_vram(void) {
    uint8_t n = bgbuf_rows_per;
    if (!bgbuf_rows_left) return;
    if ((LCDC_REG & LCDCF_ON) && LY_REG < 144) return;   // VBlank already over: next frame
    if (n > bgbuf_rows_left) n = bgbuf_rows_left;
    bgbuf_copy_rows(bb_dst, bb_src, n);
    bb_dst += (uint16_t)n << 5;
    bb_src += (uint16_t)n * 20;
    bgbuf_rows_left -= n;
    if (!bgbuf_rows_left) {
        bg_front ^= 1;
        LCDC_REG ^= LCDCF_BG9C00 | bgbuf_flip_xor;
        bgbuf_flip_xor = 0;
        view_flips++;
    }
}

// Write the same rows to BOTH maps (LCD off: loading a floor), so either map is valid
void bgbuf_fill_both(const uint8_t *src, uint8_t rows, uint8_t dst_row) {
    uint8_t *a = (uint8_t *)0x9800u + ((uint16_t)dst_row << 5);
    while (rows--) {
        vram_row20(a, src);
        vram_row20(a + 0x400, src);
        a += 32;
        src += 20;
    }
}
