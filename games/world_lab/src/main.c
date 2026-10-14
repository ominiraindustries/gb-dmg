// world_lab: test bench of gbe_world (4-way scrolling world of 16x16 metatiles in sectors).
// The player walks cell by cell (1 px/f, B held = 2 px/f like the bike); the camera keeps it at
// screen cell (4, 4). Tests compare the visible BG with the map (tests/test_world.py).
#include "gbe.h"
#include "bg.h"
#include "spr.h"
#include "vram.h"
#include "metatiles.h"
#include "map_test.h"
#include "ui.h"
#include "font.h"
#include "font_lower.h"
#include "script_test.h"
#include "script_ids.h"


static const int8_t dir_dx[4] = { 0, 0, -1, 1 };    // 0 down, 1 up, 2 left, 3 right
static const int8_t dir_dy[4] = { 1, -1, 0, 0 };

uint8_t px, py, pdir, pstep_px, moving, pspeed;
uint16_t steps;
uint8_t actors_on = 1;
uint8_t given_item, given_count, spin_left, npc;
static void ui_init(void);

const sfx_t sfx_table[1] = { { 0, 0, 0, { 0, 0, 0, 0, 0 } } };                 // tests may clear it before the first frame
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
    set_bkg_data(VRAM_UI, UI_COUNT, ui_tiles);
    set_bkg_data(VRAM_FONT, FONT_COUNT, font_tiles);
    set_bkg_data(VRAM_FONT_LOWER, FONT_LOWER_COUNT, font_lower_tiles);
    ui_init();
    LCDC_REG |= LCDCF_WIN9C00;
    WX_REG = 7;
    WY_REG = 144;
    set_sprite_data(0, SPR_COUNT, spr_tiles);
    SPRITES_8x16;
    video_init(0, 0xE4, 0xE4, 0xE4);
    px = 34; py = 34; pdir = 0;
    camera();
    world_metatiles(0, mt_tiles[0], mt_attr, MT_COUNT);
    world_load(BANK(map_test), &map_test, px, py, want_cam_x, want_cam_y);
    SHOW_BKG;
    SHOW_SPRITES;
    SHOW_WIN;
    DISPLAY_ON;
}

// gbe_gact: actors may walk on any non-solid cell
uint8_t gact_terrain_ok(uint8_t i, uint8_t x, uint8_t y) {
    (void)i;
    return !(wattr_at(x, y) & ATTR_SOLID);
}

// 12 actors around the start: wanderers, 2 that flee, a leader with 2 followers
static void spawn_actors(void) {
    static const uint8_t ax[12] = { 30, 38, 36, 28, 40, 33, 26, 42, 35, 37, 39, 29 };
    static const uint8_t ay[12] = { 30, 30, 38, 36, 34, 27, 33, 38, 40, 26, 28, 40 };
    uint8_t k, i, beh;
    for (k = 0; k < 12; k++) {
        beh = k < 7 ? GACT_WANDER : k < 9 ? GACT_FLEE : k == 9 ? GACT_WANDER : GACT_FOLLOW;
        i = gact_spawn(1 | GACT_ANIM2, ax[k], ay[k], SPR_CRITTER, beh);
        gact_speed(i, k & 1 ? 12 : 24);
        gact[i].radius = 5;
        if (k >= 10) { gact[i].leader = k - 1; gact_speed(i, 12); }
    }
}

// gbe_script game ops (res/scripts/ops.txt)
uint8_t script_game_op(uint8_t op) {
    if (op == OP_GIVE) { given_item = script_args[0]; given_count += script_args[1]; return 0; }
    if (op == OP_SPIN) { spin_left = script_args[0]; return 1; }   // busy until spin_left = 0
    return 0;
}

static void spin_update(void) {
    if (!spin_left) return;
    if ((spin_left & 7) == 0) gact[npc].dir = (gact[npc].dir + 1) & 3;
    if (!--spin_left) script_resume();
}

static void ui_init(void) {
    uint8_t k;
    for (k = 0; k < 9; k++) tbox_frame[k] = VRAM_UI + UI_FRAME_TL + k;
    tbox_arrow = VRAM_UI + UI_ARROW;
    tbox_cursor = VRAM_UI + UI_CURSOR;
    txt_font = VRAM_FONT;
    txt_lower = VRAM_FONT_LOWER;
    txt_blank = VRAM_UI + UI_BLANK;
    tbox_name[0] = 'L'; tbox_name[1] = 'e'; tbox_name[2] = 'o'; tbox_name[3] = 0;
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
    if (gact_at(px + dir_dx[d], py + dir_dy[d]) != 0xFF) return;
    moving = 1;
    pstep_px = 0;
}

void update(void) {
    uint8_t a;
    if (script_active) { camera(); return; }          // total pause while a script runs
    if (!moving && (pressed & J_A)) {                 // talk to the actor in front
        a = gact_at(px + dir_dx[pdir], py + dir_dy[pdir]);
        if (a == npc && gact[a].type) {
            gact[a].dir = pdir ^ 1;                   // face the player
            script_run(SCRIPT_NPC_HOLA);
            return;
        }
    }
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
    gact_px = px; gact_py = py;
    gact_px2 = moving ? px + dir_dx[pdir] : px;
    gact_py2 = moving ? py + dir_dy[pdir] : py;
}

void main(void) {
    init();
    vsync();
    vram_late = 0;
    if (actors_on) spawn_actors();
    npc = gact_spawn(2, 34, 32, SPR_PLAYER, GACT_STILL);   // NPC two cells above the start
    while (1) {
        vsync();
        world_draw_vram();
        vq_draw_vram();
        WY_REG = tbox_visible ? 96 : 144;
        frame_vram_check();
        frame_begin();
        if (gbe_eq_request) { gbe_eq_request = 0; gbe_selftest(); skip_measure = 1; }
        update();
        tbox_update();
        script_update();
        spin_update();
        world_update(px, py, want_cam_x, want_cam_y);
        gact_update();
        gact_draw(2);
        oam16(0, 64 + 8, 64 + 16, SPR_PLAYER, 0);
        frame_end();
    }
}
