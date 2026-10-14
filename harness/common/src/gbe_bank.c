// gbe: reading data from switchable ROM banks (assets listed in game.json "banked_res").
// These functions live in bank 0 (gbe files have no #pragma bank) and restore the caller's bank,
// so any code may call them. Banked code must never SWITCH_ROM itself (it unmaps its own code).
#include <string.h>
#include "gbe.h"

void bank_set_bkg_data(uint8_t bank, uint8_t first, uint8_t n, const uint8_t *data) NONBANKED {
    uint8_t saved = CURRENT_BANK;
    SWITCH_ROM(bank);
    set_bkg_data(first, n, data);
    SWITCH_ROM(saved);
}

void bank_set_sprite_data(uint8_t bank, uint8_t first, uint8_t n, const uint8_t *data) NONBANKED {
    uint8_t saved = CURRENT_BANK;
    SWITCH_ROM(bank);
    set_sprite_data(first, n, data);
    SWITCH_ROM(saved);
}

// Copy n bytes of banked const data to WRAM (or VRAM with the LCD off / in VBlank)
void bank_memcpy(uint8_t bank, void *dst, const void *src, uint16_t n) NONBANKED {
    uint8_t saved = CURRENT_BANK;
    SWITCH_ROM(bank);
    memcpy(dst, src, n);
    SWITCH_ROM(saved);
}

uint8_t bank_read8(uint8_t bank, const uint8_t *p) NONBANKED {
    uint8_t saved = CURRENT_BANK, v;
    SWITCH_ROM(bank);
    v = *p;
    SWITCH_ROM(saved);
    return v;
}
