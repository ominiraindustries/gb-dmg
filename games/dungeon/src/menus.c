// TORRE HUNDIDA - pause menu, OBJETOS, ESTADO and the automap (design/ui.md 5-7).
// Overlays reuse the double buffer: the current view + a box from the .screen mockup are composed
// in the canvas and copied like a step (3 frames, no tearing); the cursor is a BG tile moved
// through the VRAM queue on the visible map once the copy is done.
#pragma bank 1
#include <string.h>
#include "game.h"
#include "screen_pause.h"
#include "screen_objetos.h"
#include "screen_estado.h"
#include "screen_mapa.h"

#define COL(at)  ((at) & 31)
#define ROW(at)  ((at) >> 5)

uint8_t menu_page, menu_last = 0, ovl_wait, map_from_menu;
uint8_t obj_list[5], obj_n;
static uint8_t scr_buf[18 * 20];                       // full-screen canvas (automap)
enum { E_POTION, E_KEY, E_DAGGER, E_STAFF, E_AMULET };

static uint8_t *visible_cell(uint8_t row, uint8_t col) {
    return (uint8_t *)(bg_front ? 0x9C00u : 0x9800u) + ((uint16_t)(VIEW_ROW + row) << 5) + col;
}

// rows r0..r1, cols c0..c1 of a banked 18x20 screen map into the 20-wide canvas
static void canvas_box(uint8_t bank, const uint8_t *map, uint8_t *canvas, uint8_t r0, uint8_t r1,
                       uint8_t c0, uint8_t c1) {
    for (; r0 <= r1; r0++)
        bank_memcpy(bank, canvas + r0 * 20 + c0, map + r0 * 20 + c0, c1 - c0 + 1);
}

static void put_text(uint8_t *canvas, uint8_t at, const char *s) {
    txt_tiles(canvas + ROW(at) * 20 + COL(at), s, strlen(s));
}

static void show(uint8_t *canvas, uint8_t rows) {
    bgbuf_start(canvas, rows, VIEW_ROW);
    ovl_wait = 1;
    skip_measure = 1;                                   // menu frames compose in C: not gameplay
}

// ---------------------------------------------------------------- pages
static void page_pause(void) {
    view_compose(shown_x, shown_y, shown_f);
    canvas_box(BANK(screen_pause), screen_pause_map, view_buf, 2, 10, 4, 15);
    menu_page = 0;
    show(view_buf, VIEW_H);
}

static void obj_entries(void) {
    obj_n = 0;
    if (potions) obj_list[obj_n++] = E_POTION;
    if (key_count) obj_list[obj_n++] = E_KEY;
    obj_list[obj_n++] = E_DAGGER;
    if (staff_owned) obj_list[obj_n++] = E_STAFF;
    if (amulet) obj_list[obj_n++] = E_AMULET;
}

static void page_objetos(void) {
    static const char * const names[] = { "Pocion", "Llave", "Daga", "Baculo", "Amuleto" };
    uint8_t i, r0 = ROW(SCREEN_OBJETOS_AT_POCION), c = COL(SCREEN_OBJETOS_AT_POCION);
    uint8_t mc = COL(SCREEN_OBJETOS_AT_X3), *line, t[2];
    view_compose(shown_x, shown_y, shown_f);
    canvas_box(BANK(screen_objetos), screen_objetos_map, view_buf, 1, 10, 1, 18);
    obj_entries();
    for (i = 0; i < 5; i++) memset(view_buf + (r0 + i) * 20 + c - 1, txt_blank, 14);
    for (i = 0; i < obj_n; i++) {
        line = view_buf + (r0 + i) * 20;
        txt_tiles(line + c, names[obj_list[i]], 7);
        t[0] = txt_blank; t[1] = txt_blank;
        if (obj_list[i] == E_POTION) { t[0] = txt_char('x'); t[1] = txt_char('0' + potions); }
        else if (obj_list[i] == E_KEY) { t[0] = txt_char('x'); t[1] = txt_char('0' + key_count); }
        else if ((obj_list[i] == E_DAGGER && !weapon) || (obj_list[i] == E_STAFF && weapon) ||
                 obj_list[i] == E_AMULET) { t[0] = txt_char('E'); t[1] = txt_char('Q'); }
        line[mc] = t[0]; line[mc + 1] = t[1];
    }
    menu_page = 1;
    show(view_buf, VIEW_H);
}

// value right-aligned with its last tile at col 17, on the row of a label define
static void put_right(uint8_t at_row, const uint8_t *tiles, uint8_t n) {
    memcpy(view_buf + at_row * 20 + 18 - n, tiles, n);
}

static void page_estado(void) {
    uint8_t t[5], m = play_secs / 60, s = play_secs % 60;
    view_compose(shown_x, shown_y, shown_f);
    canvas_box(BANK(screen_estado), screen_estado_map, view_buf, 1, 10, 1, 18);
    memset(view_buf + ROW(SCREEN_ESTADO_AT_PV) * 20 + 12, txt_blank, 6);
    txt_u16(t, hp, 2, 0); t[2] = txt_char('/'); txt_u16(t + 3, hp_max, 2, 1);
    put_right(ROW(SCREEN_ESTADO_AT_PV), t, 5);
    t[0] = txt_char(weapon ? '2' : '1'); t[1] = txt_char('-'); t[2] = txt_char(weapon ? '4' : '2');
    put_right(ROW(SCREEN_ESTADO_AT_ATAQUE), t, 3);
    t[0] = txt_char(amulet ? '1' : '0');
    put_right(ROW(SCREEN_ESTADO_AT_DEFENSA), t, 1);
    memset(view_buf + ROW(SCREEN_ESTADO_AT_DERROTADOS) * 20 + 16, txt_blank, 2);
    txt_u16(t, kills, 2, 0);
    put_right(ROW(SCREEN_ESTADO_AT_DERROTADOS), t, 2);
    if (m > 99) { m = 99; s = 59; }
    txt_u16(t, m, 2, 1); t[2] = txt_char(':'); txt_u16(t + 3, s, 2, 1);
    put_right(ROW(SCREEN_ESTADO_AT_TIEMPO), t, 5);
    t[0] = txt_char('1');
    put_right(ROW(SCREEN_ESTADO_AT_PISO), t, 1);
    menu_page = 2;
    show(view_buf, VIEW_H);
}

// ---------------------------------------------------------------- automap (GDD 2.10)
static const uint8_t am_tile[] = { UI_AM_FLOOR, UI_AM_WALL, UI_AM_DOOR, UI_AM_LOCKED, UI_AM_OPEN,
                                   UI_AM_UP, UI_AM_DOWN };

static void page_map(void) {
    uint8_t x, y, *d, all = cheat_flags & CHEAT_SEEN_ALL;
    bank_memcpy(BANK(screen_mapa), scr_buf, screen_mapa_map, 18 * 20);
    for (y = 0; y < 16; y++) {
        d = scr_buf + (1 + y) * 20 + 2;
        for (x = 0; x < 16; x++)
            d[x] = (all || (seen[(y << 1) | (x >> 3)] & (0x80 >> (x & 7))))
                   ? VRAM_UI + am_tile[dmap[(y << 4) | x]] : txt_blank;
    }
    state = ST_MAP;
    bgbuf_flip_xor = LCDCF_WINON;                       // window off with the swap (ui.md 7.1)
    bgbuf_start(scr_buf, 18, VIEW_ROW);
    ovl_wait = 1;
    skip_measure = 1;
}

static void map_close(void) {
    view_compose(shown_x, shown_y, shown_f);
    bgbuf_flip_xor = LCDCF_WINON;                       // window back on with the swap
    if (map_from_menu) { canvas_box(BANK(screen_pause), screen_pause_map, view_buf, 2, 10, 4, 15); menu_page = 0; state = ST_MENU; }
    else state = ST_PLAY;
    bgbuf_start(view_buf, VIEW_H, VIEW_ROW);
    ovl_wait = map_from_menu;
    skip_measure = 1;
}

// ---------------------------------------------------------------- entry points
void menu_enter(void) BANKED {
    state = ST_MENU;
    sfx(SFX_MENU_OK);
    page_pause();
}

void map_enter(uint8_t from_menu) BANKED {
    map_from_menu = from_menu;
    page_map();
}

static void close_all(void) {
    state = ST_PLAY;
    view_compose(shown_x, shown_y, shown_f);
    bgbuf_start(view_buf, VIEW_H, VIEW_ROW);
    play_sub = PS_BUSY;                                  // sprites come back with the swap
    sfx(SFX_MENU_BACK);
}

static void open_cursor(void) {
    if (menu_page == 0) {
        menu_open(5, menu_last, 0, visible_cell(ROW(SCREEN_PAUSE_AT_OBJETOS), COL(SCREEN_PAUSE_AT_OBJETOS) - 1),
                  32, VRAM_UI + UI_CURSOR, txt_blank);
    } else if (menu_page == 1) {
        uint8_t sel = menu_sel < obj_n ? menu_sel : obj_n - 1;
        menu_open(obj_n, sel, 0, visible_cell(ROW(SCREEN_OBJETOS_AT_POCION), COL(SCREEN_OBJETOS_AT_POCION) - 1),
                  32, VRAM_UI + UI_CURSOR, txt_blank);
    }
}

static void use_object(uint8_t e) {
    uint8_t h;
    if (e == E_POTION) {
        if (hp >= hp_max) { say("Ya estas sano"); sfx(SFX_LOCKED); return; }
        h = hp_max - hp > 10 ? 10 : hp_max - hp;
        hp += h;
        potions--;
        say_num("Recuperas ", h, " PV");
        sfx(SFX_DRINK);
    } else if (e == E_DAGGER && weapon) { weapon = 0; say("Equipas la daga"); sfx(SFX_MENU_OK); }
    else if (e == E_STAFF && !weapon) { weapon = 1; say("Equipas el baculo"); sfx(SFX_MENU_OK); }
    else { sfx(SFX_MENU_BACK); return; }
    hud_dirty();
    page_objetos();                                      // counts / EQ marks / list length changed
}

void menus_update(void) BANKED {
    uint8_t r;
    if (bgbuf_rows_left) return;                         // copy in progress: input ignored
    if (ovl_wait) { ovl_wait = 0; open_cursor(); return; }
    if (state == ST_MAP) {
        if (pressed & (J_B | J_SELECT)) map_close();
        else if (pressed & J_START) { map_from_menu = 0; map_close(); }
        return;
    }
    if (pressed & J_START) { close_all(); return; }
    if (menu_page == 2) {                                // ESTADO: read-only
        if (pressed & (J_A | J_B)) page_pause();
        return;
    }
    r = menu_update();
    if (r == MENU_NONE) return;
    if (menu_page == 1) {
        if (r == MENU_BACK) { page_pause(); return; }
        use_object(obj_list[r]);
        return;
    }
    if (r == MENU_BACK || r == 4) { close_all(); return; }
    menu_last = r;
    if (r == 0) { menu_sel = 0; page_objetos(); }
    else if (r == 1) page_estado();
    else if (r == 2) map_enter(1);
    else if (r == 3) {
        game_save();
        ovl_wait = 0;                                    // the menu stays, cursor on GUARDAR
    }
}

// hero arrow on the automap (ui.md 7.2): blinks 16/16
void map_sprites(void) BANKED {
    uint8_t *o = &shadow_OAM[0].y, t = SPR_ARROW_UP, p = 0;
    if (pf == 1) t = SPR_ARROW_RIGHT;
    else if (pf == 2) p = S_FLIPY;
    else if (pf == 3) { t = SPR_ARROW_RIGHT; p = S_FLIPX; }
    o[0] = (frame & 16) || bgbuf_rows_left ? 0 : (uint8_t)((1 + py) * 8 + 16);
    o[1] = (2 + px) * 8 + 8;
    o[2] = t;
    o[3] = p;
}
