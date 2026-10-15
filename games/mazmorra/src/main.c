// MADRIGUERA - glue: init, the frame loop, screen builds (TITLE, PLAY, FIN) and their small updates.
// Loop rules (CLAUDE.md): vsync (+ stale guard) -> VBlank copies -> frame_vram_check -> frame_begin
// -> logic -> world_update -> sprites -> frame_end. VRAM rule (GDD 7.2, lesson of faro): every
// screen_build loads every slot its scene uses (game.json vram_scenes, checked by gb.vram_errors).
#include "game.h"
#include "title.h"
#include "ui.h"
#include "dungeon.h"
#include "link.h"
#include "enemies.h"
#include "fx.h"
#include "items.h"
#include "font_mini.h"
#include "font_mini_lower.h"
#include "font_mini_es.h"
#include "map_mazmorra.h"
#include "screen_title.h"
#include "screen_play.h"
#include "screen_fin.h"

uint8_t scene, cheat_flags, new_game;            // cheat_flags: tests only
uint16_t rules_cache[RULE_COUNT];
enemies_t en_rows[EN_COUNT];
uint8_t title_t, fin_sel;

const sfx_t sfx_table[SFX_COUNT] = {
    [SFX_SWORD] = { 4, 1, 6,  { 0, 0x00, 0x81, 0x21, 0x80 } },
    [SFX_HIT]   = { 1, 2, 8,  { 0x15, 0x80, 0xA2, 0x80, 0x86 } },
    [SFX_KILL]  = { 4, 2, 14, { 0, 0x00, 0xA3, 0x55, 0x80 } },
    [SFX_HURT]  = { 1, 3, 16, { 0x2C, 0x80, 0xF3, 0x00, 0x85 } },
    [SFX_HEART] = { 2, 1, 10, { 0, 0x80, 0x82, 0xC0, 0x87 } },
    [SFX_MENU]  = { 2, 1, 4,  { 0, 0x80, 0x41, 0xC0, 0x87 } },
    [SFX_OK]    = { 1, 2, 10, { 0x15, 0x80, 0x73, 0x40, 0x86 } },
};

// 18 rows of a mockup map -> a BG/window map (LCD off)
static void copy_rows(uint8_t bank, const uint8_t *map, uint8_t *dst, uint8_t from, uint8_t to) {
    for (; from < to; from++) bank_memcpy(bank, dst + ((uint16_t)from << 5), map + from * 20, 20);
}

// the map is loaded: its 'start' object is where a new game begins
static void start_game(void) {
    uint8_t x = 0, y = 0;
    room_find_start(&x, &y);
    cont_c = x / ROOM_W; cont_r = y / ROOM_H;
    cont_x = x; cont_x <<= 4;                     // ((uint16_t)y << 4 lost the high byte in SDCC)
    cont_y = y; cont_y <<= 4;
    cont_dir = DIR_UP;
    hp_max = R8(RULE_HP_START);
    deaths = 0;
}

void screen_build(uint8_t which) {
    lcd_off_redraw_begin();
    bank_set_bkg_data(BANK(ui), VRAM_UI, UI_COUNT, ui_tiles);
    if (which == SC_TITLE) {
        bank_set_bkg_data(BANK(title), VRAM_TITLE, TITLE_COUNT, title_tiles);
        bank_set_bkg_data(BANK(screen_title), SCREEN_TITLE_TEXT_FIRST, SCREEN_TITLE_TEXT_COUNT, screen_title_text);
        copy_rows(BANK(screen_title), screen_title_map, (uint8_t *)0x9800, 0, 18);
        title_t = 0;
        SHOW_BKG;
    } else if (which == SC_PLAY) {
        bank_set_bkg_data(BANK(dungeon), VRAM_DUNGEON, DUNGEON_COUNT, dungeon_tiles);
        bank_set_sprite_data(BANK(link), SPR_LINK, LINK_COUNT, link_tiles);
        bank_set_sprite_data(BANK(enemies), SPR_ENEMIES, ENEMIES_COUNT, enemies_tiles);
        bank_set_sprite_data(BANK(fx), SPR_FX, FX_COUNT, fx_tiles);
        bank_set_sprite_data(BANK(items), SPR_ITEMS, ITEMS_COUNT, items_tiles);
        copy_rows(BANK(screen_play), screen_play_map, (uint8_t *)0x9C00, 0, 2);   // HUD rows
        world_metatiles(BANK(metatiles), mt_tiles[0], mt_attr, MT_COUNT);
        if (new_game) {                           // load once to read the 'start' object
            new_game = 0;
            world_load_id(MAP_MAZMORRA, 0, 0, 0, 0);
            start_game();
        }
        world_load_id(MAP_MAZMORRA, (uint8_t)(cont_x >> 4), (uint8_t)(cont_y >> 4),
                      (int16_t)cont_c * (ROOM_W * 16), (int16_t)cont_r * (ROOM_H * 16) - 16);
        room_enter_now(cont_c, cont_r);
        link_place(cont_x, cont_y, cont_dir);
        hp = hp_max;                              // new game and 'Continuar': full hearts (GDD 2.5)
        inv_t = dead_t = 0;
        hud_reset();
        WX_REG = 7; WY_REG = 0;
        hud_cut = 1;
        SHOW_BKG; SHOW_WIN; SHOW_SPRITES;
    } else {                                      // SC_FIN
        bank_set_bkg_data(BANK(screen_fin), SCREEN_FIN_TEXT_FIRST, SCREEN_FIN_TEXT_COUNT, screen_fin_text);
        copy_rows(BANK(screen_fin), screen_fin_map, (uint8_t *)0x9800, 0, 18);
        fin_sel = 0;
        SHOW_BKG;
    }
    scene = which;
    DISPLAY_ON;
}

// "Pulsa Start" blinks 30/30 f (ui.md 2); Start or A: a new game
static void title_update(void) {
    uint8_t t[SCREEN_TITLE_TILES_PULSA_START], k;
    if (title_t == 0 || title_t == 30) {
        for (k = 0; k < SCREEN_TITLE_TILES_PULSA_START; k++)
            t[k] = title_t ? VRAM_UI + UI_BLANK : SCREEN_TITLE_TILE_PULSA_START + k;
        vq_push((uint8_t *)0x9800 + SCREEN_TITLE_AT_PULSA_START, t, SCREEN_TITLE_TILES_PULSA_START);
    }
    if (++title_t >= 60) title_t = 0;
    if (pressed & (J_START | J_A)) {
        rng_state ^= ((uint16_t)DIV_REG << 8) | title_t;
        if (!rng_state) rng_state = 0xACE1;
        sfx(SFX_OK);
        new_game = 1;
        transition(SC_PLAY);
    }
}

// ui.md 4: cursor one column left of the chosen option
static void fin_cursor(void) {
    uint8_t c = VRAM_UI + UI_CURSOR, b = VRAM_UI + UI_BLANK;
    vq_push((uint8_t *)0x9800 + SCREEN_FIN_AT_CONTINUAR - 1, fin_sel ? &b : &c, 1);
    vq_push((uint8_t *)0x9800 + SCREEN_FIN_AT_SALIR - 1, fin_sel ? &c : &b, 1);
}

static void fin_update(void) {
    if (pressed & (J_UP | J_DOWN)) { fin_sel ^= 1; fin_cursor(); sfx(SFX_MENU); }
    if (pressed & (J_A | J_START)) {
        sfx(SFX_OK);
        transition(fin_sel ? SC_TITLE : SC_PLAY);
    }
}

static void play_update(void) {
    if (hitstop) { hitstop--; return; }           // everything frozen but the sound (GDD 2.4)
    if (sliding) { room_slide_update(); return; }
    if (dead_t) { if (!--dead_t) transition(SC_FIN); return; }
    link_update();
    if (!sliding) room_update();
}

void main(void) {
    DISPLAY_OFF;
    bank_memcpy(BANK(tbl_rules), rules_cache, tbl_rules, sizeof(rules_cache));
    bank_memcpy(BANK(tbl_enemies), en_rows, tbl_enemies, sizeof(en_rows));
    vwf_font(0, BANK(font_mini), font_mini_tiles, font_mini_vwf);
    vwf_font(1, BANK(font_mini_lower), font_mini_lower_tiles, font_mini_lower_vwf);
    vwf_font(2, BANK(font_mini_es), font_mini_es_tiles, font_mini_es_vwf);
    SPRITES_8x16;
    LCDC_REG |= LCDCF_WIN9C00;
    video_init(16, 0xE4, 0xE4, 0x1B);             // OBP1 inverted: the enemies' hurt flash
    sound_init();
    world_edge_budget = 4;                        // 16 metatiles per 16 px of slide (GDD 2.2)
    gact_px = gact_py = gact_px2 = gact_py2 = 0xFF;   // enemies may enter Tilo's cell (GDD 2.6)
    show_screen_now(SC_TITLE);
    vsync();
    vram_late = 0;
    while (1) {
        vsync();
        if (LY_REG < 144) vsync();               // stale: the last frame ran past VBlank
        frame_vsync_ly = LY_REG;
        world_draw_vram();
        tiles_draw_vram();
        vq_draw_vram();
        frame_vram_check();
        frame_begin();
        if (gbe_eq_request) { gbe_eq_request = 0; gbe_selftest(); skip_measure = 1; }
        if (!transition_update()) {
            if (scene == SC_TITLE) title_update();
            else if (scene == SC_PLAY) play_update();
            else fin_update();
        }
        if (scene == SC_PLAY) {
            world_update((uint8_t)((lx + 8) >> 4), (uint8_t)((ly + 12) >> 4), cam_wx, cam_wy);
            link_draw();
            room_draw();
            hud_update();
        } else if (scene == SC_FIN && title_t != 0xFE) { fin_cursor(); title_t = 0xFE; }
        tiles_prepare();
        sound_update();
        frame_end();
    }
}
