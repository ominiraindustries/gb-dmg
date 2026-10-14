// GRIFO - vertical shmup for the DMG on the gbe library (design/gdd.md).
// Loop rules (CLAUDE.md): vsync -> frame_begin -> VRAM copies only -> frame_vram_check ->
// logic -> sprites -> frame_end. Globals the tests read must be non-static.
#include "game.h"

// GDD 8: channel, priority, frames, registers (ch1: NR10-14; ch2/ch4: NRx1-x4 in r[1..4])
const sfx_t sfx_table[SFX_COUNT] = {
    [SFX_SHOT]     = { 2, 0, 4,  { 0, 0x81, 0x41, 0xC0, 0x87 } },
    [SFX_HIT]      = { 4, 1, 3,  { 0, 0x3A, 0x61, 0x20, 0xC0 } },
    [SFX_BOOM]     = { 4, 2, 12, { 0, 0x00, 0xA2, 0x55, 0x80 } },
    [SFX_BIG_BOOM] = { 4, 3, 30, { 0, 0x00, 0xF4, 0x71, 0x80 } },
    [SFX_ITEM]     = { 1, 2, 10, { 0x16, 0x80, 0xA2, 0x40, 0x87 } },
    [SFX_POWER]    = { 1, 3, 16, { 0x15, 0x80, 0xF3, 0x00, 0x86 } },
    [SFX_BOMB]     = { 1, 3, 40, { 0x7F, 0x80, 0xF7, 0x00, 0x84 } },
    [SFX_DEATH]    = { 1, 3, 40, { 0x7E, 0x80, 0xF7, 0x80, 0x85 } },
    [SFX_EXTEND]   = { 1, 3, 20, { 0x17, 0x80, 0xF3, 0x80, 0x86 } },
    [SFX_WARN]     = { 2, 3, 15, { 0, 0x80, 0xA4, 0x60, 0x86 } },
    [SFX_BOSS_HIT] = { 4, 1, 4,  { 0, 0x3A, 0x81, 0x40, 0xC0 } },
    [SFX_PAUSE]    = { 1, 3, 6,  { 0x00, 0x80, 0x93, 0xC0, 0x87 } },
    [SFX_START]    = { 1, 3, 16, { 0x16, 0x80, 0xF3, 0x60, 0x86 } },
    [SFX_TICK]     = { 1, 1, 2,  { 0x00, 0x80, 0x51, 0xE0, 0x87 } },
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
