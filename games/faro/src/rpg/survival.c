// FARO kit - survival in the field (GDD 2.5): hunger by steps, regeneration while full (or the
// REGEN buff), starving (never kills), EN regen, field poison, the buff's duration and perishable
// food going off. All numbers come from rules.tbl / buffs.tbl. Bank 1.
// Counters run per completed step (thinking or reading costs nothing); they are not saved, so a
// loaded game restarts them (at most one period of difference).
// One-shot warnings are scripts of res/scripts/sistema.evs (the kit has no text): the field runs
// survival_script after the step (0xFFFF = none).
#pragma bank 255
#include "rpg.h"

#define PERISH_MAX 16
uint8_t food_age;                               // saved: age of the perishables in the bag
uint8_t perish_n, perish_ids[PERISH_MAX];       // items with 'perece' (survival_init)
uint8_t role_item[ITEMS_ROLE_COUNT];          // the item with each system role (0xFF none): LENA, SAL...
uint16_t survival_script = 0xFFFF;
static uint8_t c_sac, c_regen, c_en, c_starve, c_poison, c_age;

void survival_init(void) BANKED {
    uint8_t id, r;
    perish_n = 0;
    memset(role_item, 0xFF, sizeof(role_item));
    for (id = 0; id < ITEM_COUNT; id++) {
        if (bank_read8(BANK(tbl_items), &tbl_items[id].perece) && perish_n < PERISH_MAX) perish_ids[perish_n++] = id;
        r = bank_read8(BANK(tbl_items), &tbl_items[id].role);
        if (r && r < sizeof(role_item) && role_item[r] == 0xFF) role_item[r] = id;
    }
}

static uint8_t tick(uint8_t *c, uint8_t period) {
    if (++*c < period) return 0;
    *c = 0;
    return 1;
}

static void warn(uint16_t sid, uint16_t flag) {
    if (flag_get(flag) || survival_script != 0xFFFF) return;
    survival_script = sid;              // the script sets the flag (it can also re-arm it)
}

// Half (rounded up) of every perishable turns into its 'pasado' version (GDD 2.5)
static void spoil(void) {
    uint8_t k, id, n, to;
    for (k = 0; k < perish_n; k++) {
        id = perish_ids[k];
        if (!inv[id]) continue;
        n = (inv[id] + 1) >> 1;
        to = bank_read8(BANK(tbl_items), &tbl_items[id].pasado);
        inv[id] -= n;
        inv_add(to, n);                 // past the cap: the rest is lost
#ifdef SID_AVISO_PASADO
        warn(SID_AVISO_PASADO, F_AVISO_PASADO);
#endif
    }
}

static uint8_t has_perishable(void) {
    uint8_t k;
    for (k = 0; k < perish_n; k++) if (inv[perish_ids[k]]) return 1;
    return 0;
}

void survival_step(void) BANKED {
    uint8_t regen = 0;
    if (tick(&c_sac, (uint8_t)RULE(RULE_SAC_STEPS)) && sac) {
        sac--;
#ifdef SID_AVISO_HAMBRE
        if (sac == (uint8_t)RULE(RULE_SAC_HUNGRY) - 1) warn(SID_AVISO_HAMBRE, F_AVISO_HAMBRE);
#endif
#ifdef SID_AVISO_DEBIL
        if (sac == 0) warn(SID_AVISO_DEBIL, F_AVISO_DEBIL);
#endif
    }
    if (buff != 0xFF) {
        if (bank_read8(BANK(tbl_buffs), &tbl_buffs[buff].kind) == BUFFS_KIND_REGEN)
            regen = bank_read8(BANK(tbl_buffs), &tbl_buffs[buff].val);
        if (!buff_steps || !--buff_steps) buff = 0xFF;
    }
    if (!regen && sac >= (uint8_t)RULE(RULE_SAC_FULL)) regen = (uint8_t)RULE(RULE_REGEN_STEPS);
    if (regen && tick(&c_regen, regen) && pv < pv_max) pv++;
    if (sac == 0 && tick(&c_starve, (uint8_t)RULE(RULE_STARVE_STEPS)) && pv > 1) pv--;
    if (sac >= (uint8_t)RULE(RULE_SAC_HUNGRY) && tick(&c_en, (uint8_t)RULE(RULE_EN_STEPS)) && en < en_max) en++;
    if (p_st == ST_ENVENENADO && tick(&c_poison, (uint8_t)RULE(RULE_POISON_STEPS)) && pv > 1) pv--;
    if (tick(&c_age, (uint8_t)RULE(RULE_AGE_STEPS))) {
        if (!has_perishable()) food_age = 0;
        else if (++food_age >= (uint8_t)RULE(RULE_AGE_SPOIL)) {
            spoil();
            food_age = (uint8_t)RULE(RULE_AGE_AFTER);
        }
    }
}
