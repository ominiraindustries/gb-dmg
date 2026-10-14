// TORRE HUNDIDA - first-person dungeon crawler for the DMG on the gbe library (design/gdd.md).
// Loop rules (CLAUDE.md): vsync -> VRAM copies -> frame_vram_check -> frame_begin -> logic ->
// sprites -> frame_end (VRAM first: GBDK's VBlank ISR already used ~1100 T of VBlank).
// Globals the tests read must be non-static.
#include <string.h>
#include "game.h"

// GDD 8: channel, priority, frames, registers (ch1: NR10-14; ch2/ch4: NRx1-x4 in r[1..4])
const sfx_t sfx_table[SFX_COUNT] = {
    [SFX_BUMP]      = { 4, 1, 6,  { 0, 0x3A, 0x61, 0x60, 0xC0 } },
    [SFX_SWING]     = { 4, 0, 6,  { 0, 0x3A, 0x41, 0x30, 0xC0 } },
    [SFX_HIT]       = { 4, 2, 6,  { 0, 0x3A, 0x81, 0x50, 0xC0 } },
    [SFX_MISS]      = { 1, 1, 6,  { 0x00, 0x80, 0x52, 0x40, 0x86 } },
    [SFX_KILL]      = { 4, 3, 16, { 0, 0x00, 0xA2, 0x55, 0x80 } },
    [SFX_GROWL]     = { 1, 2, 12, { 0x7C, 0x80, 0xA3, 0x20, 0x84 } },
    [SFX_HURT]      = { 4, 3, 10, { 0, 0x00, 0xC2, 0x71, 0x80 } },
    [SFX_DOOR]      = { 4, 2, 12, { 0, 0x00, 0x73, 0x60, 0x80 } },
    [SFX_UNLOCK]    = { 1, 3, 12, { 0x16, 0x80, 0xA2, 0x40, 0x87 } },
    [SFX_LOCKED]    = { 1, 2, 8,  { 0x00, 0x80, 0x93, 0x00, 0x84 } },
    [SFX_PICK]      = { 1, 2, 10, { 0x15, 0x80, 0xA2, 0x80, 0x87 } },
    [SFX_DRINK]     = { 1, 2, 16, { 0x17, 0x80, 0xA2, 0x00, 0x86 } },
    [SFX_DEATH]     = { 1, 3, 40, { 0x7E, 0x80, 0xF7, 0x80, 0x85 } },
    [SFX_CLEAR]     = { 1, 3, 30, { 0x16, 0x80, 0xF3, 0x60, 0x86 } },
    [SFX_MENU_MOVE] = { 1, 1, 3,  { 0x00, 0x80, 0x51, 0xE0, 0x87 } },
    [SFX_MENU_OK]   = { 1, 2, 6,  { 0x00, 0x80, 0x93, 0xC0, 0x87 } },
    [SFX_MENU_BACK] = { 1, 2, 6,  { 0x00, 0x80, 0x93, 0x80, 0x86 } },
    [SFX_SAVE]      = { 1, 3, 16, { 0x15, 0x80, 0xF3, 0x00, 0x87 } },
};

uint8_t state, play_sub, frame, cheat_flags;

// gbe_screen calls screen_build() near: this bank-0 wrapper reaches the banked builder
void screen_build(uint8_t which) {
    screen_build_b(which);
}

// Once at boot (LCD off): every tileset stays loaded (vram_order fits in 256), ISRs, sound
static void init(void) {
    DISPLAY_OFF;
    LCDC_REG = LCDCF_BG8800 | LCDCF_BG9800 | LCDCF_WIN9C00 | LCDCF_OBJ16 | LCDCF_BGON;
    bank_set_bkg_data(BANK(ui), VRAM_UI, UI_COUNT, ui_tiles);
    bank_set_bkg_data(BANK(font), VRAM_FONT, FONT_COUNT, font_tiles);
    bank_set_bkg_data(BANK(font_lower), VRAM_FONT_LOWER, FONT_LOWER_COUNT, font_lower_tiles);
    // walls and uiscreens share one slot (vram_order): each screen build loads the one it needs
    bank_set_sprite_data(BANK(spr), 0, SPR_COUNT, spr_tiles);
    view_bank = BANK(view);
    view_map = dmap;
    view_class = cell_class;
    txt_font = VRAM_FONT;
    txt_blank = VRAM_UI + UI_BLANK;
    txt_lower = VRAM_FONT_LOWER;
    video_init(0, 0xE4, 0xE4, 0xD8);                 // no HUD cut: the window is a fixed bottom band
    sound_init();
    show_screen_now(ST_TITLE);
    vsync();                                         // a stale VBlank flag made the first
    vram_late = 0;                                   // loop frame copy outside VBlank
}

void main(void) {
    init();
    while (1) {
        vsync();
        // VRAM first. Text waits while the view is copied (decided BEFORE the copy: its last
        // chunk ends the copy and the queue would then run past VBlank)
        vq_budget = bgbuf_rows_left ? 0 : 48;
        bgbuf_draw_vram();
        vq_draw_vram();
        frame_vram_check();
        frame_begin();
        if (gbe_eq_request) { gbe_eq_request = 0; gbe_selftest(); skip_measure = 1; }
        if (!transition_update()) {
            switch (state) {
            case ST_TITLE:    title_update(); break;
            case ST_PLAY:
                if (play_sub == PS_DYING) dying_update();
                else play_update();
                if (clear_req) { clear_req = 0; transition(ST_CLEAR); }
                break;
            case ST_MENU:
            case ST_MAP:      menus_update(); log_update(); break;
            case ST_GAMEOVER: gameover_update(); break;
            case ST_CLEAR:    clear_update(); break;
            }
        }
        if (state == ST_PLAY) play_sprites();
        else if (state == ST_MAP) { hide_sprites_range(1, 40); map_sprites(); }
        else hide_sprites_range(0, 40);
        sound_update();
        frame++;
        frame_end();
    }
}
