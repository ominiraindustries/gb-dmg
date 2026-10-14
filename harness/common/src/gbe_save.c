// gbe: one save block in cartridge SRAM (bank 0, 0xA000), validated by a signature, a version,
// the length and a Fletcher-16 checksum (CLAUDE.md: SRAM powers up with garbage; a half-written
// save after a power loss must read as "no save", never as a valid one).
// Needs an MBC with RAM + battery in game.json, e.g. ["-Wm-yt0x1B", "-Wm-ya1"]. SRAM is enabled
// only inside these functions (ENABLE_RAM / DISABLE_RAM).
//
// Layout at 0xA000: 'G' 'B' version len_lo len_hi data[len] sum1 sum2   (len <= 8000)
#include <string.h>
#include "gbe.h"

#define SAVE_BASE ((uint8_t *)0xA000)

static uint16_t fletcher16(const uint8_t *p, uint16_t n) {
    uint8_t a = 0, b = 0;
    while (n--) {
        a += *p++;                   // mod 256 (cheaper than mod 255, still catches swaps/zeros)
        b += a;
    }
    return ((uint16_t)b << 8) | a;
}

// Validate the block in place and copy len bytes to dst. Returns 1 if the save is valid.
uint8_t save_load(void *dst, uint16_t len, uint8_t version) {
    uint8_t *s = SAVE_BASE, ok = 0;
    uint16_t sum;
    ENABLE_RAM;
    SWITCH_RAM(0);
    if (s[0] == 'G' && s[1] == 'B' && s[2] == version && s[3] == (uint8_t)len && s[4] == (uint8_t)(len >> 8)) {
        sum = fletcher16(s + 5, len);
        if (s[5 + len] == (uint8_t)sum && s[6 + len] == (uint8_t)(sum >> 8)) {
            memcpy(dst, s + 5, len);
            ok = 1;
        }
    }
    DISABLE_RAM;
    return ok;
}

// Write data, then the checksum, then the signature last: a power loss in the middle leaves an
// invalid block (the signature is cleared first).
void save_store(const void *src, uint16_t len, uint8_t version) {
    uint8_t *s = SAVE_BASE;
    uint16_t sum;
    ENABLE_RAM;
    SWITCH_RAM(0);
    s[0] = 0;
    s[2] = version; s[3] = (uint8_t)len; s[4] = (uint8_t)(len >> 8);
    memcpy(s + 5, src, len);
    sum = fletcher16(s + 5, len);
    s[5 + len] = (uint8_t)sum; s[6 + len] = (uint8_t)(sum >> 8);
    s[1] = 'B';
    s[0] = 'G';
    DISABLE_RAM;
}

void save_erase(void) {
    ENABLE_RAM;
    SWITCH_RAM(0);
    SAVE_BASE[0] = 0;
    SAVE_BASE[1] = 0;
    DISABLE_RAM;
}
