// world_lab: test bench of gbe_world (4-way scrolling world of 16x16 metatiles in sectors).
// The player walks cell by cell (1 px/f, B held = 2 px/f like the bike); the camera keeps it at
// screen cell (4, 4). Tests compare the visible BG with the map (tests/test_world.py).
#include "gbe.h"
#include "bg.h"
#include "spr.h"
#include "vram.h"
#include "metatiles.h"
#include "map_test.h"


static const int8_t dir_dx[4] = { 0, 0, -1, 1 };    // 0 down, 1 up, 2 left, 3 right
static const int8_t dir_dy[4] = { 1, -1, 0, 0 };

uint8_t px, py, pdir, pstep_px, moving, pspeed;
uint16_t steps;
int16_t want_cam_x, want_cam_y;

static int16_t cam_for(uint8_t x, uint8_t y, uint8_t dir, uint8_t off, uint8_t axis_x) {
    int16_t v = (int16_t)((axis_x ? x : y)) << 4;
    int8_t d = axis_x ? dir_dx[dir] : dir_dy[dir];
    if (d > 0) v += off;
    else if (d < 0) v -= off;
    return v - 64;
}

static void camera(void) {
    want_cam_x = cam_for(px, py, pdir, pstep_px, 1);
    want_cam_y = cam_for(px, py, pdir, pstep_px, 0);
}

void init(void) {
    DISPLAY_OFF;
    set_bkg_data(VRAM_BG, BG_COUNT, bg_tiles);
    set_sprite_data(0, SPR_COUNT, spr_tiles);
    SPRITES_8x16;
    video_init(0, 0xE4, 0xE4, 0xE4);
    px = 34; py = 34; pdir = 0;
    camera();
    world_metatiles(0, mt_tiles[0], mt_attr, MT_COUNT);
    world_load(BANK(map_test), &map_test, px, py, want_cam_x, want_cam_y);
    SHOW_BKG;
    SHOW_SPRITES;
    DISPLAY_ON;
}

static uint8_t held_dir(void) {
    if (keys & J_DOWN) return 0;
    if (keys & J_UP) return 1;
    if (keys & J_LEFT) return 2;
    if (keys & J_RIGHT) return 3;
    return 0xFF;
}

static void try_start(void) {
    uint8_t d = held_dir();
    if (d == 0xFF) return;
    pdir = d;
    if (wattr_at(px + dir_dx[d], py + dir_dy[d]) & ATTR_SOLID) return;
    moving = 1;
    pstep_px = 0;
}

void update(void) {
    pspeed = (keys & J_B) ? 2 : 1;
    if (!moving) try_start();
    if (moving) {
        pstep_px += pspeed;
        if (pstep_px >= 16) {
            px += dir_dx[pdir];
            py += dir_dy[pdir];
            pstep_px = 0;
            moving = 0;
            steps++;
            try_start();                 // chained steps: no dead frame
        }
    }
    camera();
}

void main(void) {
    init();
    vsync();
    vram_late = 0;
    while (1) {
        vsync();
        world_draw_vram();
        frame_vram_check();
        frame_begin();
        if (gbe_eq_request) { gbe_eq_request = 0; gbe_selftest(); skip_measure = 1; }
        update();
        world_update(px, py, want_cam_x, want_cam_y);
        oam16(0, 64 + 8, 64 + 16, SPR_PLAYER, 0);
        frame_end();
    }
}
