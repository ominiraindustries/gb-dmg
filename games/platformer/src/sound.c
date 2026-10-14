// Sound effects by registers (GDD §8.1). A new effect replaces the one playing on its channel
// only if its priority is >= ; the channel stays "busy" for the effect's duration.
#include "game.h"

typedef struct {
    uint8_t ch;         // 1, 2 or 4
    uint8_t prio;       // 1..3
    uint8_t frames;     // how long the channel is reserved
    uint8_t r[5];       // NRx0..NRx4 (ch1) / NRx1..NRx4 (ch2, ch4: r[0] unused)
} sfx_t;

static const sfx_t sfx_table[SFX_COUNT] = {
    [SFX_JUMP_SMALL]   = { 1, 1, 12, { 0x15, 0x80, 0x82, 0x00, 0x85 } },
    [SFX_JUMP_BIG]     = { 1, 1, 12, { 0x14, 0x80, 0x92, 0x00, 0x84 } },
    [SFX_COIN]         = { 1, 2, 16, { 0x00, 0x80, 0xF3, 0x9D, 0x87 } },
    [SFX_STOMP]        = { 4, 2, 10, { 0, 0x30, 0xA1, 0x50, 0xC0 } },
    [SFX_BUMP]         = { 4, 1, 8,  { 0, 0x38, 0x91, 0x70, 0xC0 } },
    [SFX_BREAK]        = { 4, 2, 20, { 0, 0x00, 0xF3, 0x61, 0x80 } },
    [SFX_POWER_APPEAR] = { 1, 2, 30, { 0x27, 0x80, 0xF4, 0x00, 0x84 } },
    [SFX_POWER_GET]    = { 1, 3, 30, { 0x16, 0x80, 0xF5, 0x00, 0x83 } },
    [SFX_SHOOT]        = { 4, 1, 6,  { 0, 0x3A, 0x81, 0x30, 0xC0 } },
    [SFX_KICK]         = { 4, 2, 10, { 0, 0x30, 0xB1, 0x40, 0xC0 } },
    [SFX_HURT]         = { 1, 3, 30, { 0x2D, 0x80, 0xF4, 0x00, 0x86 } },
    [SFX_ONEUP]        = { 1, 3, 30, { 0x17, 0x80, 0xF6, 0x00, 0x85 } },
    [SFX_TICK]         = { 1, 1, 3,  { 0x00, 0x80, 0x61, 0xC0, 0x87 } },
    [SFX_PAUSE]        = { 1, 3, 16, { 0x00, 0x80, 0xA2, 0x00, 0x86 } },
    [SFX_DEATH]        = { 1, 3, 60, { 0x2F, 0x80, 0xF7, 0x00, 0x85 } },
    [SFX_HURRY]        = { 1, 3, 20, { 0x00, 0x80, 0xF2, 0xC0, 0x87 } },
};

uint8_t ch_prio[5], ch_busy[5];        // indexed by channel number

void sound_init(void) {
    NR52_REG = 0x80;                    // APU on first
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

void sound_update(void) {               // once per frame
    if (ch_busy[1]) ch_busy[1]--;
    if (ch_busy[2]) ch_busy[2]--;
    if (ch_busy[4]) ch_busy[4]--;
}
