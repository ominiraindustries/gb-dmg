// gbe: vertical menu with a cursor tile, hold-to-repeat (16 f, then every 6 f), wrap-around,
// disabled options skipped, A = choose, B = back. The game draws the box and the texts (text
// helpers, or a .screen map); the menu only moves the cursor through the VRAM queue.
#include "gbe_config.h"
#ifdef GBE_BANKED
#pragma bank 255
#endif
#include "gbe.h"

uint8_t menu_n, menu_sel, menu_disabled, menu_rep;
static uint8_t *menu_cursor0;           // VRAM address of the cursor on option 0
static uint8_t menu_stride, menu_tile, menu_blank;

// cursor0: map address of the cursor cell for option 0; stride: map bytes between options (32 =
// next row); disabled: bit i = option i cannot be chosen (e.g. CONTINUAR without a save).
void menu_open(uint8_t n, uint8_t sel, uint8_t disabled, uint8_t *cursor0, uint8_t stride,
               uint8_t cursor_tile, uint8_t blank_tile) GBE_FAR {
    menu_n = n;
    menu_disabled = disabled;
    menu_cursor0 = cursor0;
    menu_stride = stride;
    menu_tile = cursor_tile;
    menu_blank = blank_tile;
    menu_rep = 0;
    menu_sel = sel;
    while ((menu_disabled >> menu_sel) & 1) if (++menu_sel == menu_n) menu_sel = 0;
    vq_push(menu_cursor0 + (uint16_t)menu_sel * menu_stride, &menu_tile, 1);
}

static void menu_move(int8_t dir) {
    uint8_t old = menu_sel, k = menu_n;
    do {
        menu_sel = dir > 0 ? (menu_sel + 1 == menu_n ? 0 : menu_sel + 1)
                           : (menu_sel ? menu_sel - 1 : menu_n - 1);
    } while (((menu_disabled >> menu_sel) & 1) && --k);
    if (menu_sel == old) return;
    vq_push(menu_cursor0 + (uint16_t)old * menu_stride, &menu_blank, 1);
    vq_push(menu_cursor0 + (uint16_t)menu_sel * menu_stride, &menu_tile, 1);
}

// Once per frame: MENU_NONE, the chosen index (A), or MENU_BACK (B)
uint8_t menu_update(void) GBE_FAR {
    uint8_t k = keys & (J_UP | J_DOWN);
    if (pressed & J_A) return menu_sel;
    if (pressed & J_B) return MENU_BACK;
    if (!k) { menu_rep = 0; return MENU_NONE; }
    if (pressed & k) { menu_rep = 16; menu_move(k & J_UP ? -1 : 1); }
    else if (!--menu_rep) { menu_rep = 6; menu_move(k & J_UP ? -1 : 1); }
    return MENU_NONE;
}
