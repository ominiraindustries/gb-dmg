// world_lab: test bench of gbe_world (4-way scrolling world of 16x16 metatiles in sectors).
// The player walks cell by cell (1 px/f, B held = 2 px/f like the bike); the camera keeps it at
// screen cell (4, 4). Tests compare the visible BG with the map (tests/test_world.py).
#include <string.h>
#include "gbe.h"
#include "bg.h"
#include "spr.h"
#include "vram.h"
#include "metatiles.h"
#include "world_index.h"
#include "ui.h"
#include "font.h"
#include "font_lower.h"
#include "font_es.h"
#include "script_test.h"
#include "script_ids.h"
#include "tbl_items.h"


static const int8_t dir_dx[4] = { 0, 0, -1, 1 };    // 0 down, 1 up, 2 left, 3 right
static const int8_t dir_dy[4] = { 1, -1, 0, 0 };

uint8_t px, py, pdir, pstep_px, moving, pspeed;
// tests/test_vwf.py: vwf_req = 1 draws vwf_str into vwf_buf (20 tiles) from pixel vwf_x -> vwf_end
uint8_t vwf_req, vwf_x, vwf_end, vwf_buf[20 * 16];
char vwf_str[48];
uint16_t steps;
uint8_t actors_on = 1;
uint8_t given_item, given_count, spin_left, npc, tq_test, list_mode, list_chosen = 0xFF, warps;
uint16_t npc_script[GBE_GACT_MAX];      // script of each NPC slot (0xFFFF = none)
enum { OBJ_NPC, OBJ_SIGN, OBJ_WARP };   // order of game.json world_objects
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
    bank_set_bkg_data(BANK(bg), VRAM_BG, BG_COUNT, bg_tiles);
    bank_set_bkg_data(BANK(ui), VRAM_UI, UI_COUNT, ui_tiles);
    bank_set_bkg_data(BANK(font), VRAM_FONT, FONT_COUNT, font_tiles);
    bank_set_bkg_data(BANK(font_lower), VRAM_FONT_LOWER, FONT_LOWER_COUNT, font_lower_tiles);
    bank_set_bkg_data(BANK(font_es), VRAM_FONT_ES, FONT_ES_COUNT, font_es_tiles);
    ui_init();
    LCDC_REG |= LCDCF_WIN9C00;
    WX_REG = 7;
    WY_REG = 144;
    bank_set_sprite_data(BANK(spr), 0, SPR_COUNT, spr_tiles);
    SPRITES_8x16;
    video_init(0, 0xE4, 0xE4, 0xE4);
    px = 34; py = 34; pdir = 0;
    camera();
    world_metatiles(0, mt_tiles[0], mt_attr, MT_COUNT);
    world_load_id(MAP_TEST, px, py, want_cam_x, want_cam_y);
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
    txt_es = VRAM_FONT_ES;
    vwf_font(0, BANK(font), font_tiles, font_vwf);
    vwf_font(1, BANK(font_lower), font_lower_tiles, font_lower_vwf);
    vwf_font(2, BANK(font_es), font_es_tiles, font_es_vwf);
    txt_blank = VRAM_UI + UI_BLANK;
    tbox_name[0] = 'L'; tbox_name[1] = 'e'; tbox_name[2] = 'o'; tbox_name[3] = 0;
}

// gbe_list: the items table in the window (Select opens it)
static void item_row(uint8_t item, uint8_t *buf) {
    items_t r;
    bank_memcpy(BANK(tbl_items), &r, &tbl_items[item], sizeof(r));
    txt_tiles(buf + 1, r.name, 15);
}

static void list_start(void) {
    uint8_t row[20];
    memset(row, VRAM_UI + UI_BLANK, 20);
    for (row[0] = 0; row[0] < 5; row[0]++) ;
    vq_push_fill((uint8_t *)0x9C00, VRAM_UI + UI_FRAME_T, 20);
    vq_push_fill((uint8_t *)0x9C00 + 4 * 32, VRAM_UI + UI_FRAME_B, 20);
    list_cursor = VRAM_UI + UI_CURSOR;
    list_blank = VRAM_UI + UI_BLANK;
    list_arrow_up = list_arrow_down = VRAM_UI + UI_ARROW;
    list_border = VRAM_UI + UI_FRAME_T;
    list_up_at = (uint8_t *)0x9C00 + 18;
    list_down_at = 0;
    list_open(ITEM_COUNT, 0, 3, (uint8_t *)0x9C00 + 32 + 1, 32, 16, item_row);
    list_mode = 1;
}

// NPC objects of every sector of the (small) current map become actors
static void spawn_objects(void) {
    uint8_t sx, sy, k, i;
    world_ev_t *e;
    npc = 0xFF;
    for (sy = 0; sy < wmap.h; sy++)
        for (sx = 0; sx < wmap.w; sx++) {
            world_events(sx, sy);
            for (k = 0, e = wev; k < wev_n; k++, e++) {
                if (e->type != OBJ_NPC) continue;
                i = gact_spawn(2, e->x, e->y, SPR_PLAYER, GACT_STILL);
                if (i == 0xFF) continue;
                gact[i].dir = e->d[2];
                npc_script[i] = e->d[0] | ((uint16_t)e->d[1] << 8);
                if (npc == 0xFF) npc = i;
            }
        }
}

// Arrived on a warp object: change map with the LCD off (one blank frame)
static void warp(world_ev_t *e) {
    uint8_t i;
    DISPLAY_OFF;
    for (i = 0; i < GBE_GACT_MAX; i++) gact_free(i);
    px = e->d[1];
    py = e->d[2];
    i = e->d[0];
    camera();
    world_load_id(i, px, py, want_cam_x, want_cam_y);
    if (i == MAP_TEST && actors_on) spawn_actors();
    spawn_objects();
    warps++;
    skip_measure = 1;
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
    if (gact_at(px + dir_dx[d], py + dir_dy[d]) != 0xFF) return;
    moving = 1;
    pstep_px = 0;
}

void update(void) {
    uint8_t a;
    if (script_active) { camera(); return; }          // total pause while a script runs
    if (list_mode) {
        a = list_update();
        if (a != MENU_NONE) { list_chosen = a; list_mode = 0; }
        camera();
        return;
    }
    if (!moving && (pressed & J_SELECT)) { list_start(); camera(); return; }
    if (!moving && (pressed & J_A)) {                 // talk to the actor or the object in front
        uint8_t fx = px + dir_dx[pdir], fy = py + dir_dy[pdir];
        world_ev_t *e;
        a = gact_at(fx, fy);
        if (a != 0xFF && npc_script[a] != 0xFFFF) {
            gact[a].dir = pdir ^ 1;                   // face the player
            script_run_id(npc_script[a]);
            return;
        }
        e = world_event_at(fx, fy);
        if (e && e->type == OBJ_SIGN) { script_run_id(e->d[0] | ((uint16_t)e->d[1] << 8)); return; }
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
            {
                world_ev_t *e = world_event_at(px, py);
                if (e && e->type == OBJ_WARP) { warp(e); camera(); return; }
            }
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
    memset(npc_script, 0xFF, sizeof(npc_script));
    spawn_objects();
    while (1) {
        vsync();
        world_draw_vram();
        vq_draw_vram();
        tiles_draw_vram();
        WY_REG = tbox_visible ? 96 : list_mode ? 104 : 144;
        frame_vram_check();
        frame_begin();
        if (gbe_eq_request) { gbe_eq_request = 0; gbe_selftest(); skip_measure = 1; }
        if (vwf_req) { vwf_req = 0; vwf_clear(vwf_buf, 20); vwf_end = vwf_draw(vwf_buf, 20, vwf_x, vwf_str); skip_measure = 1; }
        update();
        if (tq_test) { tq_test = 0; tiles_push((uint8_t *)0x8000 + 60 * 16, BANK(spr), spr_tiles, 6); }
        tiles_prepare();
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
