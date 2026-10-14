// gbe: save in cartridge SRAM with two alternating slots ($A000 and $B000, bank 0), each validated
// by a signature, version, sequence number, length and Fletcher-16 checksum. A store goes to the
// slot NOT holding the newest valid save, signature written last: a power cut in the middle of a
// store leaves the previous save intact (CLAUDE.md: SRAM powers up with garbage).
// Needs an MBC with RAM + battery in game.json, e.g. ["-Wm-yt0x1B", "-Wm-ya1"]. SRAM is enabled
// only inside these functions (ENABLE_RAM / DISABLE_RAM). len <= 4000.
//
// Slot layout: 'G' 'B' version seq len_lo len_hi data[len] sum1 sum2
#include <string.h>
#include "gbe_config.h"
#ifdef GBE_BANKED
#pragma bank 255
#endif
#include "gbe.h"

#define SLOT0 ((uint8_t *)0xA000)
#define SLOT1 ((uint8_t *)0xB000)
#define HDR   6

uint8_t save_slot, save_seq;            // slot / sequence of the last valid load or store

static uint16_t fletcher16(const uint8_t *p, uint16_t n) {
    uint8_t a = 0, b = 0;
    while (n--) {
        a += *p++;                   // mod 256 (cheaper than mod 255, still catches swaps/zeros)
        b += a;
    }
    return ((uint16_t)b << 8) | a;
}

static uint8_t slot_ok(const uint8_t *s, uint16_t len, uint8_t version) {
    uint16_t sum;
    if (s[0] != 'G' || s[1] != 'B' || s[2] != version || s[4] != (uint8_t)len || s[5] != (uint8_t)(len >> 8))
        return 0;
    sum = fletcher16(s + HDR, len);
    return s[HDR + len] == (uint8_t)sum && s[HDR + 1 + len] == (uint8_t)(sum >> 8);
}

// 0 or 1 = the newest valid slot, 0xFF = none (SRAM must be enabled)
static uint8_t newest(uint16_t len, uint8_t version) {
    uint8_t a = slot_ok(SLOT0, len, version), b = slot_ok(SLOT1, len, version);
    if (a && b) return (int8_t)(SLOT1[3] - SLOT0[3]) > 0 ? 1 : 0;   // sequence, modulo 256
    if (a) return 0;
    if (b) return 1;
    return 0xFF;
}

// Copy the newest valid save to dst. Returns 1 if there is one.
uint8_t save_load(void *dst, uint16_t len, uint8_t version) GBE_FAR {
    uint8_t n, *s;
    ENABLE_RAM;
    SWITCH_RAM(0);
    n = newest(len, version);
    if (n != 0xFF) {
        s = n ? SLOT1 : SLOT0;
        memcpy(dst, s + HDR, len);
        save_slot = n;
        save_seq = s[3];
    }
    DISABLE_RAM;
    return n != 0xFF;
}

void save_store(const void *src, uint16_t len, uint8_t version) GBE_FAR {
    uint8_t n, seq = 0, *s;
    uint16_t sum;
    ENABLE_RAM;
    SWITCH_RAM(0);
    n = newest(len, version);
    if (n != 0xFF) seq = (n ? SLOT1 : SLOT0)[3] + 1;
    save_slot = n == 0 ? 1 : 0;                 // the other slot (slot 0 when there is none)
    s = save_slot ? SLOT1 : SLOT0;
    s[0] = 0;                                   // invalid while writing
    s[1] = 0;
    s[2] = version; s[3] = seq; s[4] = (uint8_t)len; s[5] = (uint8_t)(len >> 8);
    memcpy(s + HDR, src, len);
    sum = fletcher16(s + HDR, len);
    s[HDR + len] = (uint8_t)sum; s[HDR + 1 + len] = (uint8_t)(sum >> 8);
    s[1] = 'B';
    s[0] = 'G';                                 // signature last
    save_seq = seq;
    DISABLE_RAM;
}

void save_erase(void) GBE_FAR {
    ENABLE_RAM;
    SWITCH_RAM(0);
    SLOT0[0] = SLOT0[1] = 0;
    SLOT1[0] = SLOT1[1] = 0;
    DISABLE_RAM;
}
