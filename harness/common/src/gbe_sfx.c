// gbe: sound effects by registers with per-channel priority (table provided by the game)
#include <string.h>
#include "gbe.h"

uint8_t ch_prio[5], ch_busy[5];        // indexed by channel number 1, 2, 4

void sound_init(void) {
    NR52_REG = 0x80;                    // APU on first: other registers are read-only while off
    NR50_REG = 0x77;
    NR51_REG = 0xFF;
}

// Each channel's registers are consecutive (NR10-14 at FF10, NR21-24 at FF16, NR41-44 at FF20;
// FF15 and FF1F are unused, writes ignored): one memcpy of the 5 bytes writes them in order,
// trigger (NRx4) last. Field-by-field through the struct pointer cost ~1300 T (shmup profile).
static uint8_t * const sfx_regs[5] = { 0, (uint8_t *)0xFF10, (uint8_t *)0xFF15, 0, (uint8_t *)0xFF1F };

void sfx(uint8_t id) {
    const uint8_t *p = (const uint8_t *)&sfx_table[id];
    uint8_t ch = p[0];
    if (ch_busy[ch] && p[1] < ch_prio[ch]) return;
    ch_prio[ch] = p[1];
    ch_busy[ch] = p[2];
    memcpy(sfx_regs[ch], p + 3, 5);
}

void sound_update(void) {
    if (ch_busy[1]) ch_busy[1]--;
    if (ch_busy[2]) ch_busy[2]--;
    if (ch_busy[4]) ch_busy[4]--;
}
