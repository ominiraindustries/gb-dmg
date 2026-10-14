// gbe: direct shadow OAM writes
#include "gbe.h"

void oam16(uint8_t nb, uint8_t ox, uint8_t y, uint8_t tile, uint8_t prop) {
    OAM_item_t *o = &shadow_OAM[nb];
    uint8_t t2 = tile + 2;
    if (prop & S_FLIPX) { t2 = tile; tile += 2; }
    o->y = y; o->x = ox; o->tile = tile; o->prop = prop;
    o++;
    o->y = y; o->x = ox + 8; o->tile = t2; o->prop = prop;
}

void oam8(uint8_t nb, uint8_t ox, uint8_t y, uint8_t tile, uint8_t prop) {
    OAM_item_t *o = &shadow_OAM[nb];
    o->y = y; o->x = ox; o->tile = tile; o->prop = prop;
}
