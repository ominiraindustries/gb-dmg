// Shared packed BCD helpers (harness/common/src/bcd.s). Use from a game with
// "common_src": ["bcd.s"] in game.json and #include "bcd.h".
#pragma once
#include <stdint.h>

// dst += src, 3 bytes of packed BCD, little-endian (byte 0 = lowest 2 digits), saturates at 999999
void bcd_add3(uint8_t *dst, const uint8_t *src);
