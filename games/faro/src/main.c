// FARO - glue: init, the main loop and the state machine (GDD 4.2). Rules (CLAUDE.md): vsync ->
// VBlank copies -> frame_vram_check -> frame_begin -> logic -> sprites -> frame_end.
// New game = the script "nueva_partida" (res/scripts): data only (items, flags, then a warp to the
// start map); the field shows the result. The code never names a map or an item.
#include "rpg.h"
#include "ui.h"
#include "font.h"
#include "font_lower.h"
#include "font_es.h"
#include "overworld.h"
#include "interior.h"
#include "faro.h"
#include "metatiles.h"
#include "metatiles_faro.h"
#include "metatiles_interior.h"
#include "leo.h"
#include "npc.h"
#include "fx.h"
#include "battle_leo.h"
#include "battle_pinzarro.h"
#include "battle_dunejo.h"
#include "battle_gavirata.h"
#include "battle_sapoyo.h"
#include "battle_erizal.h"
#include "battle_polifaro.h"

// Field tilesets end below the HUD's sprite tiles 252-255 (ui.md 1.4; the BG tiles 128-255 and the
// sprite tiles 128-255 are the same VRAM): a tileset that grows past it fails the build here
typedef char hud_vram_overworld[(VRAM_OVERWORLD + OVERWORLD_COUNT <= HUD_TILE) ? 1 : -1];
typedef char hud_vram_interior[(VRAM_INTERIOR + INTERIOR_COUNT <= HUD_TILE) ? 1 : -1];
typedef char hud_vram_faro[(VRAM_FARO + FARO_COUNT <= HUD_TILE) ? 1 : -1];

uint8_t state, field_sub, cheat_flags;   // cheat_flags: written by tests only
// tests drive the battle core directly (tests/test_battle.py vs tests/battle_model.py):
// bt_cmd 1 = battle_begin(a, b, c), 2 = battle_turn(a, b, c), 3 = battle_open_turn(), 4 = player_new(),
// 5 = player_stats(), 6 = battle_request(a, b, c)
uint8_t bt_cmd, bt_a, bt_b, bt_c, save_req;   // save_req: tests save from the field

static void test_hook(void) {
    if (bt_cmd == 1) battle_begin(bt_a, bt_b, bt_c);
    else if (bt_cmd == 2) battle_turn(bt_a, bt_b, bt_c);
    else if (bt_cmd == 3) battle_open_turn();
    else if (bt_cmd == 4) player_new();
    else if (bt_cmd == 5) player_stats();
    else if (bt_cmd == 6) battle_request(bt_a, bt_b, bt_c);   // a battle from the field
    bt_cmd = 0;
    skip_measure = 1;
}
extern uint8_t warp_map, warp_x, warp_y, warp_dir, warp_pending;

const sfx_t sfx_table[SFX_COUNT] = {
    [SFX_BUMP]  = { 4, 1, 8, { 0, 0x00, 0x42, 0x61, 0x80 } },
    [SFX_BLIP]  = { 2, 0, 3, { 0, 0x80, 0x41, 0xC0, 0x87 } },
    [SFX_OK]    = { 1, 2, 10, { 0x15, 0x80, 0x73, 0x40, 0x86 } },
    [SFX_PICK]  = { 1, 2, 12, { 0x16, 0x80, 0x82, 0x00, 0x87 } },
};

// Metatile sets in res/metatiles*.mt name order (world.py mtset): their tiles share one VRAM slot
void map_gfx(uint8_t set) {
    if (set == 1) {
        bank_set_bkg_data(BANK(faro), VRAM_FARO, FARO_COUNT, faro_tiles);
        world_metatiles(BANK(metatiles_faro), mt_faro_tiles[0], mt_faro_attr, MT_FARO_COUNT);
    } else if (set == 2) {
        bank_set_bkg_data(BANK(interior), VRAM_INTERIOR, INTERIOR_COUNT, interior_tiles);
        world_metatiles(BANK(metatiles_interior), mt_interior_tiles[0], mt_interior_attr, MT_INTERIOR_COUNT);
    } else {
        bank_set_bkg_data(BANK(overworld), VRAM_OVERWORLD, OVERWORLD_COUNT, overworld_tiles);
        world_metatiles(BANK(metatiles), mt_tiles[0], mt_attr, MT_COUNT);
    }
}

// Battle pictures (species.pic) at BG 128, Leo's back after them (ui.md 6.1). Glue: the asset list.
void battle_gfx(uint8_t pic) {
    switch (pic) {
    case 0: bank_set_bkg_data(BANK(battle_pinzarro), 128, 49, battle_pinzarro_tiles); break;
    case 1: bank_set_bkg_data(BANK(battle_dunejo), 128, 49, battle_dunejo_tiles); break;
    case 2: bank_set_bkg_data(BANK(battle_gavirata), 128, 49, battle_gavirata_tiles); break;
    case 3: bank_set_bkg_data(BANK(battle_sapoyo), 128, 49, battle_sapoyo_tiles); break;
    case 4: bank_set_bkg_data(BANK(battle_erizal), 128, 49, battle_erizal_tiles); break;
    default: bank_set_bkg_data(BANK(battle_polifaro), 128, 49, battle_polifaro_tiles); break;
    }
    bank_set_bkg_data(BANK(battle_leo), 177, BATTLE_LEO_COUNT, battle_leo_tiles);
}

// gbe_screen calls this with the LCD off between a fade out and a fade in
void screen_build(uint8_t which) {
    lcd_off_redraw_begin();
    if (which == ST_TITLE) { field_set = 0xFF; title_build(); }   // the title overwrites the set's slot
    else if (which == ST_BATTLE) battle_enter();
    else if (which == ST_FIELD) {
        if (field_set == 0xFF)                  // from the title: its beam was loaded over the NPC looks
            bank_set_sprite_data(BANK(npc), SPR_NPC, NPC_COUNT, npc_tiles);
        field_enter(warp_map, warp_x, warp_y, warp_dir);
        warp_pending = 0;
        SHOW_BKG; SHOW_SPRITES; SHOW_WIN;           // the window is hidden by WY = 144 (main loop)
    }
    DISPLAY_ON;
}

static void ui_init(void) {
    tbox_frame[0] = VRAM_UI + UI_FRAME_TL; tbox_frame[1] = VRAM_UI + UI_FRAME_T;
    tbox_frame[2] = VRAM_UI + UI_FRAME_TR; tbox_frame[3] = VRAM_UI + UI_FRAME_L;
    tbox_frame[4] = VRAM_UI + UI_BLANK;    tbox_frame[5] = VRAM_UI + UI_FRAME_R;
    tbox_frame[6] = VRAM_UI + UI_FRAME_BL; tbox_frame[7] = VRAM_UI + UI_FRAME_B;
    tbox_frame[8] = VRAM_UI + UI_FRAME_BR;
    tbox_arrow = VRAM_UI + UI_ARROW_DOWN;
    tbox_cursor = VRAM_UI + UI_CURSOR;
    tbox_row = 0;
    txt_font = VRAM_FONT;
    txt_lower = VRAM_FONT_LOWER;
    txt_es = VRAM_FONT_ES;
    txt_blank = VRAM_UI + UI_BLANK;
    memcpy(tbox_name, "Leo", 4);
}

// Run the data-only script "nueva_partida" to its end: items, flags and the start warp
static void new_game(void) {
    player_new();
    memset(flags, 0, sizeof(flags));
    memset(vars, 0, sizeof(vars));
    warp_map = 0; warp_x = 8; warp_y = 8; warp_dir = DIR_DOWN;
#ifdef SID_NUEVA_PARTIDA
    script_run_id(SID_NUEVA_PARTIDA);
    while (script_active && script_state == SS_RUN) script_update();
    script_active = 0;
#endif
}

void init(void) {
    DISPLAY_OFF;
    bank_set_bkg_data(BANK(ui), VRAM_UI, UI_COUNT, ui_tiles);
    bank_set_bkg_data(BANK(font), VRAM_FONT, FONT_COUNT, font_tiles);
    bank_set_bkg_data(BANK(font_lower), VRAM_FONT_LOWER, FONT_LOWER_COUNT, font_lower_tiles);
    bank_set_bkg_data(BANK(font_es), VRAM_FONT_ES, FONT_ES_COUNT, font_es_tiles);
    bank_set_sprite_data(BANK(leo), SPR_LEO, LEO_COUNT, leo_tiles);
    bank_set_sprite_data(BANK(npc), SPR_NPC, NPC_COUNT, npc_tiles);
    bank_set_sprite_data(BANK(fx), SPR_FX, 16, fx_tiles);
    SPRITES_8x16;
    LCDC_REG |= LCDCF_WIN9C00;
    WX_REG = 7;
    WY_REG = 144;
    video_init(0, 0xE4, 0xE4, 0xD8);          // ui.md: BGP/OBP0 0xE4
    sound_init();
    rules_load();
    survival_init();
    ui_init();
    vq_budget = 32;
    gact_think_every = 2;                       // NPCs think on even frames, creatures on odd ones
    show_screen_now(ST_TITLE);
}

void main(void) {
    init();
    vsync();
    vram_late = 0;
    while (1) {
        vsync();
        if (LY_REG < 144) vsync();               // stale: the last frame ran past VBlank
        frame_vsync_ly = LY_REG;
        world_draw_vram();                      // fixed-size copies first,
        tiles_draw_vram();
        vq_draw_vram();                         // the queue last: it stops by itself at the end of VBlank
        if (panel_state && state == ST_FIELD) { WY_REG = 0; WX_REG = panel_wx; }
        else { WX_REG = 7; WY_REG = (tbox_visible && state == ST_FIELD) ? 96 : 144; }
        frame_vram_check();
        frame_begin();
        if (gbe_eq_request) { gbe_eq_request = 0; gbe_selftest(); skip_measure = 1; }
        if (bt_cmd) test_hook();
        if (save_req) { save_req = 0; game_save(); }
        if (!transition_update()) {
            switch (state) {
            case ST_TITLE:
                {
                    uint8_t c = title_update();
                    if (c == TITLE_NEW) { new_game(); warp_pending = 1; transition(ST_FIELD); }
                    else if (c == TITLE_CONTINUE && game_load()) { warp_pending = 1; transition(ST_FIELD); }
                }
                break;
            case ST_BATTLE:
                battle_update();
                break;
            case ST_FIELD:
                if (panel_state) { panel_update(); break; }    // the field is paused under the panel
                if (tbox_visible || script_active) { tbox_update(); script_update(); }
                field_update();
                field_vblank();
                break;
            }
        }
        if (state != ST_TITLE && ++play_f >= 60) {   // play time (59.7 Hz: close enough for h:mm)
            play_f = 0;
            if (++play_sec >= 60) { play_sec = 0; if (play_min < 5999) play_min++; }
        }
        tiles_prepare();
        if (state == ST_FIELD) field_draw();
        sound_update();
        frame_end();
    }
}
