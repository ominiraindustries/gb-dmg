// FARO kit - the saved game (GDD 8.7) through gbe_save (2 alternating slots, checksum, signature
// last). Bank: auto. A new field means a new SAVE_VERSION (old saves then read as "no save").
#pragma bank 255
#include "rpg.h"

#define SAVE_VERSION 1

typedef struct {
    uint8_t map, x, y, dir, clinic_map, clinic_x, clinic_y;
    uint16_t steps, xp, money, buff_steps, skills, rng;
    uint8_t level, pv, en, sac, buff, st, armor, lamp, zurron, full_n;
    uint8_t weapons[3], inv[INV_SLOTS], seen[6], caught[6], kills[SPECIES_SLOTS], recipes[4];
    uint8_t full_sp[FULL_SLOTS], full_lv[FULL_SLOTS];
    uint8_t flags[GBE_FLAG_BYTES], vars[16];
} save_t;
static save_t sv;

extern uint8_t warp_map, warp_x, warp_y, warp_dir;

void game_save(void) BANKED {
    sv.map = wmap_id; sv.x = px; sv.y = py; sv.dir = pdir;
    sv.clinic_map = last_clinic_map; sv.clinic_x = last_clinic_x; sv.clinic_y = last_clinic_y;
    sv.steps = steps; sv.xp = xp; sv.money = money; sv.buff_steps = buff_steps; sv.skills = skills_known;
    sv.rng = rng_state;
    sv.level = plevel; sv.pv = pv; sv.en = en; sv.sac = sac; sv.buff = buff; sv.st = p_st; sv.armor = armor;
    sv.lamp = lamp_ring; sv.zurron = has_zurron; sv.full_n = full_n;
    memcpy(sv.weapons, weapons, 3);
    memcpy(sv.inv, inv, INV_SLOTS);
    memcpy(sv.seen, reg_seen, 6);
    memcpy(sv.caught, reg_caught, 6);
    memcpy(sv.kills, kills, SPECIES_SLOTS);
    memcpy(sv.recipes, recipe_known, 4);
    memcpy(sv.full_sp, full_sp, FULL_SLOTS);
    memcpy(sv.full_lv, full_lv, FULL_SLOTS);
    memcpy(sv.flags, flags, GBE_FLAG_BYTES);
    memcpy(sv.vars, vars, 16);
    save_store(&sv, sizeof(sv), SAVE_VERSION);
    skip_measure = 1;
}

uint8_t save_exists(void) BANKED {
    return save_load(&sv, sizeof(sv), SAVE_VERSION);
}

uint8_t game_load(void) BANKED {
    if (!save_load(&sv, sizeof(sv), SAVE_VERSION)) return 0;
    warp_map = sv.map; warp_x = sv.x; warp_y = sv.y; warp_dir = sv.dir;
    last_clinic_map = sv.clinic_map; last_clinic_x = sv.clinic_x; last_clinic_y = sv.clinic_y;
    steps = sv.steps; xp = sv.xp; money = sv.money; buff_steps = sv.buff_steps; skills_known = sv.skills;
    rng_state = sv.rng ? sv.rng : 0xACE1;
    plevel = sv.level; sac = sv.sac; buff = sv.buff; p_st = sv.st; armor = sv.armor;
    lamp_ring = sv.lamp; has_zurron = sv.zurron; full_n = sv.full_n;
    memcpy(weapons, sv.weapons, 3);
    memcpy(inv, sv.inv, INV_SLOTS);
    memcpy(reg_seen, sv.seen, 6);
    memcpy(reg_caught, sv.caught, 6);
    memcpy(kills, sv.kills, SPECIES_SLOTS);
    memcpy(recipe_known, sv.recipes, 4);
    memcpy(full_sp, sv.full_sp, FULL_SLOTS);
    memcpy(full_lv, sv.full_lv, FULL_SLOTS);
    memcpy(flags, sv.flags, GBE_FLAG_BYTES);
    memcpy(vars, sv.vars, 16);
    player_stats();
    pv = sv.pv; en = sv.en;
    return 1;
}
