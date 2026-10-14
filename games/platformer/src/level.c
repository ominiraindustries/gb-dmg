// CABALLERITO layer over gbe_map: level data, coin columns, HUD-behind rows (GDD §2.0, §2.5)
#include <string.h>
#include "game.h"
#include "level1_1.h"

uint8_t coin_cols[32];                        // bit per column: the column holds map coins

// LCD off: load 1-1 with the camera at cam
void level_load(uint16_t cam) {
    uint16_t c;
    map_load(level1_1_map, LEVEL1_1_WIDTH, cam, MT_HARD);   // invisible wall past the end
    memset(coin_cols, 0, sizeof(coin_cols));
    for (c = 0; c < (uint16_t)level_cols * LEVEL_ROWS; c++)
        if (level[c] == MT_COIN) coin_cols[c >> 6] |= 1 << ((c >> 3) & 7);
    // BG rows 30-31 show behind the window HUD (SCY = 0xF0): keep them blank
    memset((uint8_t *)(0x9800u + 30 * 32), BG_BLANK, 64);
}
