// gbe: 16-bit xorshift (7, 9, 8), one global state. rng_next() returns the low 8 bits.
// harness/gbtest.py rng_next() is the same algorithm: tests predict combat rolls from rng_state.
#include "gbe.h"

uint16_t rng_state = 0xACE1;

uint8_t rng_next(void) {
    uint16_t s = rng_state;
    s ^= s << 7;
    s ^= s >> 9;
    s ^= s << 8;
    rng_state = s;
    return (uint8_t)s;
}

// 0 .. n-1 (n >= 1), by rejection-free multiply (no division)
uint8_t rng_range(uint8_t n) {
    return (uint8_t)(((uint16_t)rng_next() * n) >> 8);
}
