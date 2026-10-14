// FARO kit - the saved game (GDD 8.7) through gbe_save (2 alternating slots, checksum, signature
// last), written and read field by field from the globals: no WRAM copy of the save. A new or
// resized field means a new SAVE_VERSION (old saves then read as "no save").
#pragma bank 255
#include "rpg.h"

#define SAVE_VERSION 2

extern uint8_t warp_map, warp_x, warp_y, warp_dir;
static uint8_t s_map, s_x, s_y, s_dir;          // where Leo is (saved) / appears (loaded)

typedef struct { void *p; uint8_t n; } field_t;
static const field_t fields[] = {
    { &s_map, 1 }, { &s_x, 1 }, { &s_y, 1 }, { &s_dir, 1 },
    { &last_clinic_map, 1 }, { &last_clinic_x, 1 }, { &last_clinic_y, 1 },
    { &steps, 2 }, { &xp, 2 }, { &money, 2 }, { &buff_steps, 2 }, { &skills_known, 2 }, { &rng_state, 2 },
    { &plevel, 1 }, { &pv, 1 }, { &en, 1 }, { &sac, 1 }, { &buff, 1 }, { &p_st, 1 }, { &armor, 1 },
    { &lamp_ring, 1 }, { &has_zurron, 1 }, { &full_n, 1 },
    { weapons, 3 }, { inv, INV_SLOTS }, { reg_seen, 6 }, { reg_caught, 6 }, { kills, SPECIES_SLOTS },
    { recipe_known, 4 }, { full_sp, FULL_SLOTS }, { full_lv, FULL_SLOTS }, { flags, GBE_FLAG_BYTES },
    { vars, 16 },
};
#define NFIELDS (sizeof(fields) / sizeof(fields[0]))

static uint16_t save_len(void) {
    uint8_t k;
    uint16_t n = 0;
    for (k = 0; k < NFIELDS; k++) n += fields[k].n;
    return n;
}

void game_save(void) BANKED {
    uint8_t k;
    s_map = wmap_id; s_x = px; s_y = py; s_dir = pdir;
    save_begin(save_len(), SAVE_VERSION);
    for (k = 0; k < NFIELDS; k++) save_put(fields[k].p, fields[k].n);
    save_end();
    skip_measure = 1;
}

uint8_t save_exists(void) BANKED {
    return save_open(save_len(), SAVE_VERSION);
}

uint8_t game_load(void) BANKED {
    uint8_t k, keep_pv, keep_en;
    if (!save_open(save_len(), SAVE_VERSION)) return 0;
    for (k = 0; k < NFIELDS; k++) save_get(fields[k].p, fields[k].n);
    warp_map = s_map; warp_x = s_x; warp_y = s_y; warp_dir = s_dir;
    if (!rng_state) rng_state = 0xACE1;
    keep_pv = pv; keep_en = en;
    player_stats();                              // maxima from the level; it clamps pv / en
    pv = keep_pv; en = keep_en;
    return 1;
}
