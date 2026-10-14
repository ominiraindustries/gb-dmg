#include <gb/gb.h>
#include <gb/metasprites.h>  // hide_sprites_range, metasprites (not included by gb.h)
#include <stdint.h>

// 2bpp tiles: 2 bytes per row (low plane, high plane)
static const uint8_t tile_bg[16] = {
    0x00,0x00, 0x00,0x00, 0x00,0x00, 0x10,0x00,
    0x00,0x00, 0x00,0x00, 0x00,0x00, 0x00,0x00,
};
static const uint8_t tile_player[16] = {
    0x3C,0x3C, 0x7E,0x42, 0xFF,0xA5, 0xFF,0x81,
    0xFF,0xA5, 0xFF,0x99, 0x7E,0x42, 0x3C,0x3C,
};

#define PLAYER_W 8
#define PLAYER_H 8

// Non-static globals: tests read them by name through the .noi symbol file
uint8_t player_x, player_y;

void main(void) {
    DISPLAY_OFF;
    set_bkg_data(0, 1, tile_bg);
    fill_bkg_rect(0, 0, 20, 18, 0);
    set_sprite_data(0, 1, tile_player);
    set_sprite_tile(0, 0);

    player_x = (SCREENWIDTH - PLAYER_W) / 2;
    player_y = (SCREENHEIGHT - PLAYER_H) / 2;

    SHOW_BKG;
    SHOW_SPRITES;
    DISPLAY_ON;

    while (1) {
        uint8_t j = joypad();
        if ((j & J_LEFT) && player_x > 0) player_x--;
        if ((j & J_RIGHT) && player_x < SCREENWIDTH - PLAYER_W) player_x++;
        if ((j & J_UP) && player_y > 0) player_y--;
        if ((j & J_DOWN) && player_y < SCREENHEIGHT - PLAYER_H) player_y++;

        // Shadow OAM is copied to real OAM by DMA in the VBlank interrupt
        move_sprite(0, player_x + 8, player_y + 16);
        vsync();
    }
}
