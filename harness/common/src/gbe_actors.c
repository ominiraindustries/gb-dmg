// gbe: actor arrays (struct of arrays). Sizes from gbe_config.h (GBE_ACT_MAX).
#include "gbe.h"

uint8_t act_type[GBE_ACT_MAX], act_xs[GBE_ACT_MAX], act_y[GBE_ACT_MAX], act_ys[GBE_ACT_MAX];
uint8_t act_state[GBE_ACT_MAX], act_timer[GBE_ACT_MAX], act_flip[GBE_ACT_MAX];
uint16_t act_x[GBE_ACT_MAX];
int16_t act_vx[GBE_ACT_MAX], act_vy[GBE_ACT_MAX];

void act_spawn(uint8_t i, uint8_t type, uint16_t x, uint8_t y) {
    act_type[i] = type;
    act_x[i] = x;
    act_y[i] = y;
    act_xs[i] = act_ys[i] = 0;
    act_vx[i] = act_vy[i] = 0;
    act_state[i] = act_timer[i] = act_flip[i] = 0;
}

// Reference C version of act_move (the engine uses the asm one in gbe_actors.s)
void act_move_c(uint8_t i) {
    uint16_t t = (uint16_t)act_xs[i] + (uint8_t)act_vx[i];
    act_xs[i] = (uint8_t)t;
    act_x[i] += (int8_t)(act_vx[i] >> 8) + (t >> 8);
    t = (uint16_t)act_ys[i] + (uint8_t)act_vy[i];
    act_ys[i] = (uint8_t)t;
    act_y[i] += (int8_t)(act_vy[i] >> 8) + (t >> 8);
}
