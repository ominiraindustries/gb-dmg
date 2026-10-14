// FARO kit - Leo's state: plevel, stats from player.tbl, XP, money, equipment, the inventory with its
// caps (caps.tbl), the bestiary bits, captured lanterns. GDD 3.2, 3.9, 5.3, 8.7. Bank 1.
#pragma bank 255
#include "rpg.h"

uint8_t plevel, pv, pv_max, en, en_max, patk, pdef, pagi, sac, buff, p_st, p_st_t, armor, lamp_ring;
uint16_t xp, money, buff_steps, skills_known;
uint8_t weapons[3];
uint8_t inv[INV_SLOTS];
uint8_t reg_seen[6], reg_caught[6], kills[SPECIES_SLOTS];
uint8_t recipe_known[4];
uint8_t full_n, full_sp[FULL_SLOTS], full_lv[FULL_SLOTS];
uint8_t has_zurron;

uint16_t rule(uint8_t id) BANKED {
    uint16_t v;
    bank_memcpy(BANK(tbl_rules), &v, &tbl_rules[id].v, 2);
    return v;
}

void item_row(uint8_t id, items_t *r) BANKED {
    bank_memcpy(BANK(tbl_items), r, &tbl_items[id], sizeof(items_t));
}

// Base stats of the plevel (player.tbl) + clothes DEF; buffs and hunger apply in battle
void player_stats(void) BANKED {
    player_t r;
    items_t it;
    bank_memcpy(BANK(tbl_player), &r, &tbl_player[plevel - 1], sizeof(r));
    pv_max = r.pv;
    en_max = r.en;
    patk = r.atq;
    pdef = r.def;
    pagi = r.agi;
    if (armor != 0xFF) { item_row(armor, &it); pdef += it.val; }
    if (pv > pv_max) pv = pv_max;
    if (en > en_max) en = en_max;
}

void player_new(void) BANKED {
    memset(inv, 0, sizeof(inv));
    memset(reg_seen, 0, sizeof(reg_seen));
    memset(reg_caught, 0, sizeof(reg_caught));
    memset(kills, 0, sizeof(kills));
    memset(recipe_known, 0, sizeof(recipe_known));
    memset(weapons, 0xFF, sizeof(weapons));
    full_n = 0;
    armor = 0xFF;
    plevel = (uint8_t)rule(RULE_START_LEVEL);
    xp = 0;
    {
        player_t r;                                           // XP already earned to reach the plevel
        bank_memcpy(BANK(tbl_player), &r, &tbl_player[plevel - 1], sizeof(r));
        xp = r.xpacum;
    }
    player_stats();
    pv = pv_max;
    en = en_max;
    sac = (uint8_t)rule(RULE_SAC_START);
    money = rule(RULE_START_MONEY);
    buff = 0xFF; buff_steps = 0;
    p_st = 0xFF; p_st_t = 0;
    skills_known = 0;
    lamp_ring = 0;
    has_zurron = 0;
}

// XP and plevel ups: PV/EN rise as much as their maximum (GDD 3.2). Returns the levels gained.
uint8_t player_gain_xp(uint16_t n) BANKED {
    player_t r;
    uint8_t ups = 0, old_pv, old_en;
    xp += n;
    while (plevel < 40) {
        bank_memcpy(BANK(tbl_player), &r, &tbl_player[plevel], sizeof(r));      // next plevel's row
        if (xp < r.xpacum) break;
        old_pv = pv_max; old_en = en_max;
        plevel++;
        ups++;
        player_stats();
        pv += pv_max - old_pv;
        en += en_max - old_en;
    }
    return ups;
}

// ---------------------------------------------------------------- inventory (GDD 5.3)
uint8_t inv_cap(uint8_t id) BANKED {
    items_t it;
    caps_t c;
    item_row(id, &it);
    bank_memcpy(BANK(tbl_caps), &c, &tbl_caps[it.tope], sizeof(c));
    return has_zurron ? c.zurron : c.tope;
}

// Add up to n; returns how many fitted
uint8_t inv_add(uint8_t id, uint8_t n) BANKED {
    uint8_t cap = inv_cap(id), room;
    room = inv[id] >= cap ? 0 : cap - inv[id];
    if (n > room) n = room;
    inv[id] += n;
    return n;
}

uint8_t inv_take(uint8_t id, uint8_t n) BANKED {
    if (inv[id] < n) return 0;
    inv[id] -= n;
    return 1;
}

uint8_t player_has_ability_b(uint16_t mask) BANKED {
    uint8_t id;
    items_t it;
    for (id = 0; id < ITEM_COUNT; id++) {
        if (!inv[id]) continue;
        item_row(id, &it);
        if (it.ability & mask) return 1;
    }
    return 0;
}

// ---------------------------------------------------------------- bestiary bits
static const uint8_t bit8[8] = { 1, 2, 4, 8, 16, 32, 64, 128 };
uint8_t reg_has(uint8_t *set, uint8_t sp) BANKED { return set[sp >> 3] & bit8[sp & 7]; }
void reg_set(uint8_t *set, uint8_t sp) BANKED { set[sp >> 3] |= bit8[sp & 7]; }

// NPC look -> first tile of its 16 in npc.tiles (looks.tbl)
uint8_t look_tile(uint8_t look) BANKED {
    looks_t r;
    bank_memcpy(BANK(tbl_looks), &r, &tbl_looks[look], sizeof(r));
    return r.spr;
}

// ---------------------------------------------------------------- script ops helpers
// give: silent (the scripts narrate it); weapons and clothes get equipped if there is room
uint8_t ops_give(uint8_t id, uint8_t n) BANKED {
    items_t it;
    uint8_t got = inv_add(id, n), k;
    item_row(id, &it);
    if (it.cat == ITEMS_CAT_ARMA) {
        for (k = 0; k < 3 && weapons[k] != id; k++) ;
        if (k == 3) for (k = 0; k < 3; k++) if (weapons[k] == 0xFF) { weapons[k] = id; break; }
    } else if (it.cat == ITEMS_CAT_ROPA && armor == 0xFF) {
        armor = id;
        player_stats();
    }
    return got == n;
}

// clinic = 1: also the wake-up point after fainting (GDD 2.9)
void ops_heal(uint8_t clinic) BANKED {
    pv = pv_max;
    en = en_max;
    p_st = 0xFF;
    p_st_t = 0;
    if (clinic) { last_clinic_map = wmap_id; last_clinic_x = px; last_clinic_y = py; }
}

uint8_t ops_reg_count(void) BANKED {
    uint8_t k, n = 0, b;
    for (k = 0; k < 6; k++) for (b = reg_caught[k]; b; b >>= 1) n += b & 1;
    return n;
}
