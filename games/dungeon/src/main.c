// TORRE HUNDIDA - first-person dungeon crawler for the DMG on the gbe library (design/gdd.md).
// M1a demo: floor 1 loaded from its bank, walking and turning with the double-buffered view.
// Loop rules (CLAUDE.md): vsync -> frame_begin -> VRAM copies only -> frame_vram_check ->
// logic -> sprites -> frame_end. Globals the tests read must be non-static.
#include <string.h>
#include "game.h"
#include "floor1.h"

enum { SFX_BUMP, SFX_COUNT };
const sfx_t sfx_table[SFX_COUNT] = {
    [SFX_BUMP] = { 4, 1, 6, { 0, 0x3A, 0x61, 0x60, 0xC0 } },
};

uint8_t dmap[256];
uint8_t px, py, pf, move_cd;
uint8_t frame, last_roll;

// M1a demo save: position + map (GDD 9.5 lists the full M1b block)
typedef struct { uint8_t x, y, f; uint8_t map[256]; } save_t;
static save_t sv;
#define SAVE_VERSION 1
#define WIN_ROW(r) ((uint8_t *)0x9C00 + ((r) << 5))

// GDD 2.0: cell type -> what the view draws
const uint8_t cell_class[] = { VIEW_FREE, VIEW_WALL, VIEW_DOOR, VIEW_LOCKED, VIEW_FREE,
                                      VIEW_UP, VIEW_DOWN };

uint8_t view_cell(uint8_t x, uint8_t y) {
    if ((x | y) & 0xF0) return VIEW_WALL;            // off the map (also -1 = 0xFF)
    return cell_class[dmap[(y << 4) | x]];
}

static uint8_t walkable(uint8_t x, uint8_t y) {
    uint8_t c;
    if ((x | y) & 0xF0) return 0;
    c = dmap[(y << 4) | x];
    return c == CELL_FLOOR || c == CELL_DOOR_OPEN;
}

static void load_floor(void) {
    uint8_t i;
    bank_memcpy(BANK(floor1), dmap, floor1_map, 256);
    for (i = 0; i < FLOOR1_OBJ_COUNT; i++) {
        if (bank_read8(BANK(floor1), &floor1_obj_type[i]) == OBJ_START) {
            px = bank_read8(BANK(floor1), &floor1_obj_x[i]);
            py = bank_read8(BANK(floor1), &floor1_obj_y[i]);
        }
    }
    pf = FLOOR1_FACING;
}

// Margins of the view rows (columns 20-31) = the background row, for the turn slide (GDD 2.1);
// view_buf holds only the BG piece here (2 alternating tiles per row)
static void fill_margins(void) {
    uint8_t r, c, *a;
    for (r = 0; r < VIEW_H; r++) {
        a = (uint8_t *)0x9800u + ((uint16_t)(VIEW_ROW + r) << 5);
        for (c = 20; c < 32; c++) a[c] = a[c + 0x400] = view_buf[r * VIEW_W + (c & 1)];
    }
}

static void init(void) {
    DISPLAY_OFF;
    LCDC_REG = LCDCF_BG8800 | LCDCF_BG9800 | LCDCF_WIN9C00 | LCDCF_OBJ16 | LCDCF_BGON | LCDCF_WINON;
    bank_set_bkg_data(BANK(ui), VRAM_UI, UI_COUNT, ui_tiles);
    set_bkg_data(VRAM_FONT, FONT_COUNT, font_tiles);
    bank_set_bkg_data(BANK(walls), VRAM_WALLS, WALLS_COUNT, walls_tiles);
    bank_set_sprite_data(BANK(spr), 0, SPR_COUNT, spr_tiles);
    view_bank = BANK(view);
    view_map = dmap;
    view_class = cell_class;
    load_floor();
    view_compose_bg();
    fill_margins();
    view_compose(px, py, pf);
    bg_front = 0;
    bgbuf_fill_both(view_buf, VIEW_H, VIEW_ROW);
    scy_shadow = SCY_BASE;
    WY_REG = HUD_WY;
    WX_REG = 7;
    video_init(0, 0xE4, 0xE4, 0xD8);                 // no HUD cut: the window is a fixed bottom band
    txt_font = VRAM_FONT;
    txt_blank = VRAM_UI + UI_BLANK;
    log_init(WIN_ROW(2));
    log_push("PISO 1");
    sound_init();
    SHOW_BKG; SHOW_WIN; SHOW_SPRITES;
    DISPLAY_ON;
}

static void save_game(void) {
    sv.x = px; sv.y = py; sv.f = pf;
    memcpy(sv.map, dmap, 256);
    save_store(&sv, sizeof(sv), SAVE_VERSION);
    log_push("PARTIDA GUARDADA");
    skip_measure = 1;                                // a menu action, not a gameplay frame
}

static void load_game(void) {
    if (!save_load(&sv, sizeof(sv), SAVE_VERSION)) { log_push("NO HAY PARTIDA"); return; }
    px = sv.x; py = sv.y; pf = sv.f;
    memcpy(dmap, sv.map, 256);
    view_compose(px, py, pf);
    bgbuf_start(view_buf, VIEW_H, VIEW_ROW);
    log_push("PARTIDA CARGADA");
    skip_measure = 1;
}

// One action per press, repeat every 12 f while held (GDD 2.1)
static void update(void) {
    uint8_t k = keys, nx = px, ny = py, r;
    if (bgbuf_rows_left) return;                     // the last view is still being copied
    if (pressed & J_START) { save_game(); return; }
    if (pressed & J_SELECT) { load_game(); return; }
    if (move_cd) { move_cd--; return; }
    if (!(k & (J_UP | J_DOWN | J_LEFT | J_RIGHT))) return;
    r = (pf + 1) & 3;
    if (k & J_B) {                                   // B + left/right: side step, B + down: about-face
        if (k & J_LEFT) { nx -= view_dx[r]; ny -= view_dy[r]; }
        else if (k & J_RIGHT) { nx += view_dx[r]; ny += view_dy[r]; }
        else if (k & J_DOWN) pf = (pf + 2) & 3;
    } else if (k & J_UP) { nx += view_dx[pf]; ny += view_dy[pf]; }
    else if (k & J_DOWN) { nx -= view_dx[pf]; ny -= view_dy[pf]; }
    else if (k & J_LEFT) pf = (pf + 3) & 3;
    else if (k & J_RIGHT) pf = r;
    if (nx != px || ny != py) {
        if (walkable(nx, ny)) { px = nx; py = ny; }
        else { sfx(SFX_BUMP); log_push("PARED"); }
    }
    last_roll = rng_next();                          // tests predict it (gbtest.rng_next)
    view_compose(px, py, pf);
    bgbuf_start(view_buf, VIEW_H, VIEW_ROW);
    move_cd = 12;
}

void main(void) {
    init();
    while (1) {
        vsync();
        // VRAM first: GBDK's VBlank ISR already used ~1100 T of the 4560 T of VBlank. Text waits
        // while the view is copied (decided BEFORE the copy: its last chunk ends the copy)
        vq_budget = bgbuf_rows_left ? 0 : 48;
        bgbuf_draw_vram();
        vq_draw_vram();
        frame_vram_check();
        frame_begin();
        if (gbe_eq_request) { gbe_eq_request = 0; gbe_selftest(); skip_measure = 1; }
        update();
        log_update();
        sound_update();
        frame++;
        frame_end();
    }
}
