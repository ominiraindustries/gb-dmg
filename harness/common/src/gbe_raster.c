// gbe: raster SCX splits - up to RASTER_MAX horizontal scroll changes per frame at chosen lines
// (parallax bands, a track that curves away, wavy water). The game fills raster_line[] / raster_scx[]
// (lines ascending, >= 1) and raster_n in its update, then raster_commit(); the VBlank handler takes
// the new table at the start of the next frame (double buffer: the ISR never reads a half-written one).
// Line 0's SCX stays gbe_video's scx_shadow (+ shake_x). Each entry costs one LYC interrupt (~150 T,
// the handler in gbe_raster.s waits for HBlank before writing SCX, so the split is clean).
// Needs video_init() first (it enables the LYC interrupt); call raster_init() after it. The HUD cut of
// gbe_video (hud_cut) and the raster both use LYC: a game uses one or the other.
// PyBoy draws mid-frame SCX changes, so tests see the bands; real-hardware timing: check on a device.
#include <string.h>
#include "gbe.h"

uint8_t raster_n, raster_line[RASTER_MAX], raster_scx[RASTER_MAX];   // the game's table
uint8_t rs_n, rs_line[RASTER_MAX], rs_scx[RASTER_MAX], rs_i;         // the ISR's copy (gbe_raster.s)
static uint8_t pending;

void raster_commit(void) {
    pending = 1;
}

// start of VBlank: take a committed table, arm the first split
static void raster_vbl(void) {
    uint8_t k, *d, *s;
    if (pending) {                              // only the used entries (2 x RASTER_MAX memcpy cost
        rs_n = k = raster_n;                    // ~3 lines of VBlank every frame in happyvalley)
        for (d = rs_line, s = raster_line; k; k--) *d++ = *s++;
        for (k = rs_n, d = rs_scx, s = raster_scx; k; k--) *d++ = *s++;
        pending = 0;
    }
    rs_i = 0;
    LYC_REG = rs_n ? rs_line[0] - 1 : 0xFF;
}

void raster_init(void) {
    raster_n = rs_n = 0;
    CRITICAL {
        remove_LCD(nowait_int_handler);         // the raster handler must run before it (it exits)
        add_LCD(raster_isr);
        add_LCD(nowait_int_handler);
        add_VBL(raster_vbl);
    }
}
