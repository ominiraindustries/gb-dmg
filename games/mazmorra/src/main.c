// New game template on the gbe engine library (harness/common/README.md).
// Loop rules (CLAUDE.md): vsync -> frame_begin -> VRAM copies only -> frame_vram_check ->
// logic -> sprites -> frame_end. Globals the tests read must be non-static.
#include "gbe.h"
#include "bg.h"
#include "spr.h"
#include "font.h"

#define PLAYER_W 16
#define PLAYER_H 16
#define TILE_FONT BG_COUNT

enum { SFX_MOVE, SFX_COUNT };
const sfx_t sfx_table[SFX_COUNT] = {
    [SFX_MOVE] = { 2, 1, 4, { 0, 0xBC, 0x61, 0x00, 0xC6 } },
};

uint8_t player_x, player_y;

// LCD off: tiles, an empty background, palettes, interrupts
void init(void) {
    DISPLAY_OFF;
    set_bkg_data(0, BG_COUNT, bg_tiles);
    set_bkg_data(TILE_FONT, FONT_COUNT, font_tiles);
    set_sprite_data(0, SPR_COUNT, spr_tiles);
    init_bkg(BG_DOT);
    SPRITES_8x16;
    video_init(0, 0xE4, 0xE4, 0xE4);          // no HUD cut (hud_cut stays 0)
    sound_init();
    player_x = (SCREENWIDTH - PLAYER_W) / 2;
    player_y = (SCREENHEIGHT - PLAYER_H) / 2;
    SHOW_BKG;
    SHOW_SPRITES;
    DISPLAY_ON;
}

void update(void) {
    if ((keys & J_LEFT) && player_x > 0) player_x--;
    if ((keys & J_RIGHT) && player_x < SCREENWIDTH - PLAYER_W) player_x++;
    if ((keys & J_UP) && player_y > 0) player_y--;
    if ((keys & J_DOWN) && player_y < SCREENHEIGHT - PLAYER_H) player_y++;
    if (pressed & (J_LEFT | J_RIGHT | J_UP | J_DOWN)) sfx(SFX_MOVE);
}

void main(void) {
    init();
    while (1) {
        vsync();
        frame_begin();
        // VBlank work goes here: copy buffers prepared last frame, nothing else
        frame_vram_check();
        update();
        oam16(0, player_x + 8, player_y + 16, SPR_PLAYER, 0);
        sound_update();
        frame_end();
    }
}
