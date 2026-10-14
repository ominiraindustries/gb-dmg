// gbe: sound effects by registers with per-channel priority (table provided by the game)
#include "gbe.h"

uint8_t ch_prio[5], ch_busy[5];        // indexed by channel number 1, 2, 4

void sound_init(void) {
    NR52_REG = 0x80;                    // APU on first: other registers are read-only while off
    NR50_REG = 0x77;
    NR51_REG = 0xFF;
}

void sfx(uint8_t id) {
    const sfx_t *s = &sfx_table[id];
    uint8_t ch = s->ch;
    if (ch_busy[ch] && s->prio < ch_prio[ch]) return;
    ch_prio[ch] = s->prio;
    ch_busy[ch] = s->frames;
    if (ch == 1) {
        NR10_REG = s->r[0]; NR11_REG = s->r[1]; NR12_REG = s->r[2]; NR13_REG = s->r[3]; NR14_REG = s->r[4];
    } else if (ch == 2) {
        NR21_REG = s->r[1]; NR22_REG = s->r[2]; NR23_REG = s->r[3]; NR24_REG = s->r[4];
    } else {
        NR41_REG = s->r[1]; NR42_REG = s->r[2]; NR43_REG = s->r[3]; NR44_REG = s->r[4];
    }
}

void sound_update(void) {
    if (ch_busy[1]) ch_busy[1]--;
    if (ch_busy[2]) ch_busy[2]--;
    if (ch_busy[4]) ch_busy[4]--;
}
