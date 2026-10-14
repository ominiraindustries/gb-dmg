// gbe: story flags (bitset) and small variables, saved with the game. Ids come from
// res/scripts/flags.txt / vars.txt (harness/script.py -> script_ids.h: F_*, V_*).
#include "gbe.h"

uint8_t flags[GBE_FLAG_BYTES];
uint8_t vars[16];

static const uint8_t bit8[8] = { 1, 2, 4, 8, 16, 32, 64, 128 };

uint8_t flag_get(uint16_t f) {
    return flags[f >> 3] & bit8[f & 7];
}

void flag_set(uint16_t f) {
    flags[f >> 3] |= bit8[f & 7];
}

void flag_clr(uint16_t f) {
    flags[f >> 3] &= ~bit8[f & 7];
}
