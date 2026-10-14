// GRIFO - vertical shmup for the DMG on the gbe library (design/gdd.md).
// Loop rules (CLAUDE.md): vsync -> frame_begin -> VRAM copies only -> frame_vram_check ->
// logic -> sprites -> frame_end. Globals the tests read must be non-static.
#include "game.h"

enum { SFX_SHOT, SFX_COUNT };
const sfx_t sfx_table[SFX_COUNT] = {
    [SFX_SHOT] = { 2, 0, 4, { 0, 0x81, 0x41, 0xC0, 0x87 } },
};

uint8_t state, play_sub, frame, cheat_flags;

// One VRAM layout for every screen (design/ui.md 0.2): ui 0-23, font 24-64, stage 65-236.
// LCDC bit 4 = 0: BG tiles 0-127 at $9000, 128-255 at $8800; sprites own $8000-$87FF.
static void load_tiles(void) {
    set_bkg_data(TILE_UI, UI_COUNT, ui_tiles);
    set_bkg_data(TILE_FONT, FONT_COUNT, font_tiles);
    set_bkg_data(BG_BASE, BG_COUNT, bg_tiles);
    set_sprite_data(0, SPR_COUNT, spr_tiles);
}

void screen_build(uint8_t which) {
    if (which == ST_PLAY) play_build();
}

void main(void) {
    DISPLAY_OFF;
    LCDC_REG = LCDCF_BG8800 | LCDCF_BG9800 | LCDCF_WIN9C00 | LCDCF_OBJ16 | LCDCF_BGON;
    load_tiles();
    video_init(7, 0xE4, 0xE4, 0xD8);
    sound_init();
    lives = 3; bombs = 2; power = 1; continues = 3;
    show_screen_now(ST_PLAY);                 // TITLE comes in M1b
    while (1) {
        vsync();
        frame_begin();
        play_draw_vram();
        frame_vram_check();
        if (gbe_eq_request) { gbe_eq_request = 0; gbe_selftest(); skip_measure = 1; }
        if (!transition_update()) {
            if (state == ST_PLAY) play_update();
        }
        play_sprites();
        sound_update();
        frame++;
        frame_end();
    }
}
