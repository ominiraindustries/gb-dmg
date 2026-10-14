// Blocks hit from below and map coins (GDD §2.6, §2.7, §2.10)
#include "game.h"

void block_hit(uint8_t col, uint8_t row) {
    uint8_t mt = level[((uint16_t)col << 3) | row];
    switch (mt_attr[mt] & CLS_MASK) {
    case CLS_Q_COIN:
        block_set(col, row, MT_USED);
        spawn_coinpop(col, row);
        add_coin();
        add_score(PTS_200);
        break;
    case CLS_Q_POWER:
        block_set(col, row, MT_USED);
        spawn_item(player_form == FORM_SMALL ? T_ITEM_GROW : T_ITEM_SHOT, col, row);
        sfx(SFX_POWER_APPEAR);
        break;
    case CLS_HIDDEN_1UP:
        block_set(col, row, MT_USED);
        spawn_item(T_ITEM_1UP, col, row);
        sfx(SFX_POWER_APPEAR);
        break;
    case CLS_BRICK:
        if (player_form == FORM_SMALL) {
            sfx(SFX_BUMP);
        } else {
            block_set(col, row, MT_SKY);
            spawn_debris(col, row);
            add_score(PTS_50);
            sfx(SFX_BREAK);
        }
        break;
    default:
        sfx(SFX_BUMP);
        return;
    }
    bump_actors_on_block(col, row);
}

static void try_coin(uint16_t x, uint8_t y) {
    uint8_t row;
    if (mt_at(x, y) != MT_COIN) return;
    row = (uint8_t)(y - Y_BIAS) >> 4;
    block_set(x >> 4, row, MT_SKY);
    add_coin();
    add_score(PTS_200);
}

// Corners of the player's hitbox (coins are 16x16 cells; corners are enough for a 10 px box)
extern uint8_t coin_cols[];

static uint8_t col_has_coin(uint16_t x) {
    uint8_t c = x >> 4;
    return coin_cols[c >> 3] & (1 << (c & 7));
}

void collect_coins(void) {
    uint16_t l = player_x + HB_X, r = player_x + HB_X + HB_W - 1;
    if (!col_has_coin(l) && !col_has_coin(r)) return;   // most columns have no coins
    uint8_t t = player_y + hb_y, b = player_y + hb_y + hb_h - 1;
    try_coin(l, t); try_coin(r, t);
    try_coin(l, b); try_coin(r, b);
    if (hb_h > 16) { try_coin(l, t + 14); try_coin(r, t + 14); }
}
