// FARO kit - battle core (GDD 3): Leo vs one creature, turn by turn. Pure rules: no drawing, no
// text. Each turn appends EVENTS (b_ev) that the battle screen plays. Numbers come from the tables
// (species, moves, items, skills, statuses, player, rules). Bank 1.
//
// Determinism: the Python model (games/faro/tests/battle_model.py) reproduces every number with the
// same rng_next() calls IN THE SAME ORDER. Change one, change the other (test_battle.py checks it).
// RNG order per attack: accuracy (unless sure) -> crit -> damage spread -> status chance -> wake.
#pragma bank 255
#include "rpg.h"

uint8_t b_species, b_level, b_cpv, b_cpv_max, b_catk, b_cdef, b_cagi;
uint8_t b_cst, b_cst_t;                         // creature main status (0xFF none) and turns
uint8_t b_ent_t, b_calm_t, b_lit_t, b_def_t, b_def_sh, b_down, b_fly;
uint8_t b_pdeb_t, b_pdeb_sh;                     // Leo's ATQ lowered (a creature move DEBUFF)
uint8_t b_cdeb_t, b_cdeb_sh;                     // the creature's ATQ lowered (Leo's technique)
uint8_t b_bait, b_flee_tries, b_last_move, b_aim, b_turn, b_result, b_free, b_seen;
uint8_t b_new_species, b_loot_n, b_loot_item[3], b_loot_cnt[3], b_levelups;
uint16_t b_xp;
uint8_t b_ev[B_EV_MAX][4], b_ev_n;
species_t b_sp;
moves_t b_mv[4];

static uint16_t R(uint8_t id) { return RULE(id); }
void apply_status(uint8_t target, uint8_t st);
void end_status(uint8_t target);

static void ev(uint8_t t, uint8_t a, uint8_t b, uint8_t c) {
    if (b_ev_n == B_EV_MAX) return;
    b_ev[b_ev_n][0] = t; b_ev[b_ev_n][1] = a; b_ev[b_ev_n][2] = b; b_ev[b_ev_n][3] = c;
    b_ev_n++;
}

static void st_row(uint8_t id, statuses_t *r) {
    bank_memcpy(BANK(tbl_statuses), r, &tbl_statuses[id], sizeof(statuses_t));
}

// turns of a status: tmin..tmax (an RNG call only when it is a range)
static uint8_t st_turns(statuses_t *r) {
    if (r->tmax > r->tmin) return r->tmin + rng_range(r->tmax - r->tmin + 1);
    return r->tmin;
}

// ---------------------------------------------------------------- setup (GDD 3.3)
static uint8_t cstat(uint8_t base, uint8_t tier, uint8_t sh) {
    return base + (uint8_t)(((uint16_t)tier * b_level * 3) >> sh);
}

// free: 1 = Leo's first turn is free (advantage), 2 = the creature's (ambush / it touched Leo)
void battle_begin(uint8_t species, uint8_t lvl, uint8_t free) BANKED {
    uint8_t k;
    uint16_t v;
    b_species = species;
    b_level = lvl;
    bank_memcpy(BANK(tbl_species), &b_sp, &tbl_species[species], sizeof(species_t));
    for (k = 0; k < 4; k++) {
        uint8_t m = (&b_sp.m1)[k * 2];          // m1 w1 m2 w2 ... are consecutive u8 columns
        if (m != 0xFF) bank_memcpy(BANK(tbl_moves), &b_mv[k], &tbl_moves[m], sizeof(moves_t));
    }
    v = 10 + (((uint16_t)b_sp.tpv * lvl * 3) >> 3);
    b_cpv_max = v > 255 ? 255 : (uint8_t)v;
    b_cpv = b_cpv_max;
    b_catk = cstat(4, b_sp.tat, 4);
    b_cdef = cstat(3, b_sp.tdf, 4);
    b_cagi = cstat(2, b_sp.tag, 4);
    b_cst = 0xFF; b_cst_t = 0;
    b_ent_t = b_calm_t = b_lit_t = b_def_t = b_pdeb_t = b_cdeb_t = b_down = 0;
    b_fly = b_sp.vuela;
    b_bait = (uint8_t)R(RULE_QBAIT_NONE);
    b_flee_tries = 0;
    b_last_move = 0xFF;
    b_aim = 0;
    b_turn = 0;
    b_result = B_ONGOING;
    b_free = free;
    b_seen = 0;
    b_ev_n = 0;
    b_loot_n = 0;
    b_xp = 0;
    b_levelups = 0;
    reg_set(reg_seen, species);
}

// ---------------------------------------------------------------- effective stats
static uint8_t p_atk(void) {
    uint8_t a = patk;
    if (buff == BUFF_FUERZA) a += a >> 2;
    if (b_pdeb_t) a -= a >> b_pdeb_sh;
    return a;
}
static uint8_t p_def(void) { return buff == BUFF_CORAZA ? pdef + (pdef >> 2) : pdef; }
static uint8_t p_agi(void) {
    uint8_t a = pagi;
    if (buff == BUFF_AGIL) a += a >> 2;
    if (sac == 0) a >>= (uint8_t)R(RULE_FAINT_AGI_SH);
    return a;
}
static uint8_t c_def(void) { return b_def_t ? b_cdef + (b_cdef >> b_def_sh) : b_cdef; }
static uint8_t c_agi(void) { return b_ent_t ? b_cagi >> 1 : b_cagi; }
static uint8_t c_flying(void) { return b_fly && !b_down && !b_ent_t; }

// ---------------------------------------------------------------- damage (GDD 3.4)
// RECIP[d] = 1024 / d, computed once per call (d >= 4): 16-bit division, a few per turn only
static uint8_t r16(uint8_t atk, uint8_t def) {
    uint16_t r;
    if (def < (uint8_t)R(RULE_DEF_MIN)) def = (uint8_t)R(RULE_DEF_MIN);
    r = ((uint16_t)atk * (1024u / def)) >> 6;
    if (r < R(RULE_R16_MIN)) r = R(RULE_R16_MIN);
    if (r > R(RULE_R16_MAX)) r = R(RULE_R16_MAX);
    return (uint8_t)r;
}

#define HITF_CRIT 1
#define HITF_WEAK 2
#define HITF_RESIST 4
#define HITF_IMMUNE 8

// One attack. side 0 = Leo attacks the creature, 1 = the creature attacks Leo.
// acc 255 = sure; crit_t = crit threshold /256 (0 = RULE CRIT); mul8 = technique multiplier in eighths
// (8 = x1); suave = never kills. Returns the damage dealt (0 = miss or immune).
static uint8_t attack(uint8_t side, uint8_t pot, uint8_t dtype, uint8_t acc, uint8_t crit_t,
                      uint8_t st, uint8_t stp, uint8_t mul8, uint8_t suave, uint8_t defsh) {
    uint8_t atk, def, agi_a, agi_d, f = 0, hit = 1, bit;
    int16_t a;
    uint16_t d;
    statuses_t sr;
    if (side == 0) { atk = p_atk(); def = c_def(); agi_a = p_agi(); agi_d = c_agi(); }
    else { atk = b_catk; def = p_def(); agi_a = c_agi(); agi_d = p_agi(); }
    if (defsh) def >>= defsh;
    // accuracy
    if (!(side == 0 && b_aim) && acc != 255) {
        a = acc;
        if (agi_d > agi_a) a -= (int16_t)R(RULE_ACC_AGI) * (agi_d - agi_a);
        if (a < (int16_t)R(RULE_ACC_MIN)) a = R(RULE_ACC_MIN);
        if ((side == 0 ? p_st : b_cst) == ST_CEGADO) a >>= 1;
        if (side == 0 && c_flying()) a -= R(RULE_FLY_ACC);
        hit = rng_next() < (uint8_t)(a < 0 ? 0 : a);
    }
    if (!hit) { ev(EV_MISS, side, 0, 0); return 0; }
    // damage
    d = ((uint16_t)pot * r16(atk, def)) >> 4;
    bit = (uint8_t)(1u << dtype);
    if (side == 0) {
        if (b_sp.inmune & bit) { ev(EV_HIT, 1, 0, HITF_IMMUNE); return 0; }
        if (b_sp.debil & bit) { d <<= 1; f |= HITF_WEAK; }
        else if (b_sp.resiste & bit) { d >>= 1; f |= HITF_RESIST; }
    }
    if (!crit_t) crit_t = (uint8_t)R(RULE_CRIT);
    if (side == 0 && b_aim) crit_t = (uint8_t)R(RULE_CRIT_AIM);
    if (rng_next() < crit_t) { d += d >> 1; f |= HITF_CRIT; }
    if (side == 0) {
        if (sac == 0) d >>= (uint8_t)R(RULE_FAINT_DMG_SH);
        else if (sac < (uint8_t)R(RULE_SAC_HUNGRY)) d -= d >> (uint8_t)R(RULE_HUNGRY_DMG_SH);
        if (p_st == ST_QUEMADO) d -= d >> 2;
    } else if (b_cst == ST_QUEMADO) d -= d >> 2;
    d = (d * mul8) >> 3;
    d -= (d * (rng_next() & (uint8_t)R(RULE_DMG_RND))) >> 8;
    if (d == 0) d = 1;
    if (d > 255) d = 255;
    if (side == 0) {
        if (suave && d >= b_cpv) d = b_cpv - 1;
        b_cpv -= d < b_cpv ? (uint8_t)d : b_cpv;
    } else pv -= d < pv ? (uint8_t)d : pv;
    ev(EV_HIT, side == 0 ? 1 : 0, (uint8_t)d, f);
    if (side == 0) b_aim = 0;
    // status of the attack
    if (st != 0xFF && stp && rng_next() < stp) apply_status(side == 0 ? 1 : 0, st);
    // waking up on a hit
    if (d) {
        uint8_t ts = side == 0 ? b_cst : p_st;
        if (ts != 0xFF) {
            st_row(ts, &sr);
            if (sr.despierta && rng_next() < sr.despierta) end_status(side == 0 ? 1 : 0);
        }
    }
    return (uint8_t)d;
}

// ---------------------------------------------------------------- statuses (GDD 3.8)
// target 0 = Leo, 1 = the creature. Main statuses only if there is none; flags reset their turns.
void apply_status(uint8_t target, uint8_t st) {
    statuses_t r;
    uint8_t t;
    st_row(st, &r);
    if (r.kind == STATUSES_KIND_PRINCIPAL) {
        if ((target ? b_cst : p_st) != 0xFF) return;
        t = st_turns(&r);
        if (target) { b_cst = st; b_cst_t = t; } else { p_st = st; p_st_t = t; }
    } else {
        if (target == 0) return;                 // flags only on the creature
        t = st_turns(&r);
        if (st == ST_ENREDADO) b_ent_t = t;
        else if (st == ST_CALMADO) b_calm_t = t;
        else if (st == ST_ILUMINADO) b_lit_t = t;
        else if (st == ST_DERRIBADO) b_down = 1;
    }
    ev(EV_STATUS, target, st, 0);
}

void end_status(uint8_t target) {
    uint8_t st = target ? b_cst : p_st;
    if (st == 0xFF) return;
    if (target) { b_cst = 0xFF; b_cst_t = 0; } else { p_st = 0xFF; p_st_t = 0; }
    ev(EV_STATUS_END, target, st, 0);
}

// a turn lost to a status (DORMIDO, ATURDIDO, RENDIDO: 'pierde')
static uint8_t loses_turn(uint8_t target) {
    statuses_t r;
    uint8_t st = target ? b_cst : p_st;
    if (st == 0xFF) return 0;
    st_row(st, &r);
    if (!r.pierde) return 0;
    ev(EV_SKIP, target, st, 0);
    return 1;
}

// ---------------------------------------------------------------- results
static void creature_down(void) {
    if (b_sp.beh == SPECIES_BEH_GUARDIAN) {          // a guardian surrenders (never lost, GDD 3.6)
        b_cpv = 0;
        if (b_cst != ST_RENDIDO) { b_cst = 0xFF; apply_status(1, ST_RENDIDO); }
        return;
    }
    b_result = B_HUNTED;
}

static void give_xp(uint8_t doubled) {
    b_xp = (((uint16_t)b_sp.xp * b_level) >> (uint8_t)R(RULE_XP_SH)) + R(RULE_XP_ADD);
    if (doubled) b_xp <<= (uint8_t)R(RULE_XP_NEW_SH);
}

// loot of a hunted creature (GDD 5.4): b1 always (lo-hi), b2 / b3 with chance /256
static void roll_loot(void) {
    uint8_t n;
    b_loot_n = 0;
    if (b_sp.b1 != 0xFF) {
        n = b_sp.b1lo;
        if (b_sp.b1hi > b_sp.b1lo) n += rng_range(b_sp.b1hi - b_sp.b1lo + 1);
        if (buff == BUFF_CAZADOR) n++;
        b_loot_item[b_loot_n] = b_sp.b1; b_loot_cnt[b_loot_n++] = n;
    }
    if (b_sp.b2 != 0xFF && rng_next() < b_sp.b2p) { b_loot_item[b_loot_n] = b_sp.b2; b_loot_cnt[b_loot_n++] = 1; }
    if (b_sp.b3 != 0xFF && rng_next() < b_sp.b3p) { b_loot_item[b_loot_n] = b_sp.b3; b_loot_cnt[b_loot_n++] = 1; }
}

// ---------------------------------------------------------------- Leo's actions (GDD 3.5)
static void use_weapon(uint8_t weapon, uint8_t mul8, uint8_t suave, uint8_t defsh, uint8_t hits) {
    items_t w;
    item_row(weapon, &w);
    while (hits-- && b_result == B_ONGOING && b_cpv) {
        attack(0, w.pot, w.dtype, w.acc, w.crit, w.st, w.stp, mul8, suave, defsh);
        if (!b_cpv) creature_down();
    }
}

static void do_skill(uint8_t id, uint8_t weapon) {
    skills_t s;
    uint8_t stp;
    bank_memcpy(BANK(tbl_skills), &s, &tbl_skills[id], sizeof(s));
    en = en >= s.en ? en - s.en : 0;
    ev(EV_USE, 0, B_USE_SKILL, id);
    switch (s.efecto) {
    case SKILLS_EFECTO_ENERGIA:
        en = en + s.val > en_max ? en_max : en + s.val;
        ev(EV_EN, 0, s.val, 0);
        break;
    case SKILLS_EFECTO_VER:
        b_seen = 1;
        ev(EV_REVEAL, 1, 0, 0);
        break;
    case SKILLS_EFECTO_ATAQUE:
        if (s.dtype == 0xFF) use_weapon(weapon, s.mul ? s.mul : 8, s.suave, s.defsh, s.golpes ? s.golpes : 1);
        else {
            uint8_t d = attack(0, s.pot, s.dtype, 255, 0, s.st, s.stp, s.mul ? s.mul : 8, s.suave, s.defsh);
            if (!b_cpv) creature_down();
            if (s.retro && d) { d >>= s.retro; pv -= d < pv ? d : pv; ev(EV_HIT, 0, d, 0); }
        }
        break;
    case SKILLS_EFECTO_ESTADO:
        stp = (s.fams & (1u << b_sp.fam)) ? s.stp2 : s.stp;
        if (rng_next() < stp) apply_status(1, s.st);
        else ev(EV_MISS, 0, 0, 0);
        break;
    case SKILLS_EFECTO_CURA:
        {
            uint8_t h = pv_max >> s.val;
            pv = (uint16_t)pv + h > pv_max ? pv_max : pv + h;
            ev(EV_HEAL, 0, h, 0);
            if (s.limpia) end_status(0);
        }
        break;
    case SKILLS_EFECTO_PUNTERIA:
        b_aim = 1;
        ev(EV_AIM, 0, 0, 0);
        break;
    case SKILLS_EFECTO_DEBUFF:
        b_cdeb_t = s.turnos;                         // the creature's ATQ (GDD: Grito)
        b_cdeb_sh = s.val;
        b_catk -= b_catk >> s.val;
        ev(EV_DEBUFF, 1, 0, 0);
        break;
    }
}

static void do_item(uint8_t id) {
    items_t it;
    uint8_t k;
    item_row(id, &it);
    inv_take(id, 1);
    ev(EV_USE, 0, B_USE_ITEM, id);
    if (it.sac) sac = (uint16_t)sac + it.sac > R(RULE_SAC_MAX) ? (uint8_t)R(RULE_SAC_MAX) : sac + it.sac;
    if (it.pv) { k = it.pv == 255 ? pv_max - pv : it.pv; pv = (uint16_t)pv + k > pv_max ? pv_max : pv + k; ev(EV_HEAL, 0, k, 0); }
    if (it.en) en = (uint16_t)en + it.en > en_max ? en_max : en + it.en;
    if (it.cura && p_st != 0xFF && p_st < 8 && (it.cura & (1u << p_st))) end_status(0);
    if (it.buff != 0xFF) { buff = it.buff; buff_steps = it.bpasos; ev(EV_BUFF, 0, it.buff, 0); }
    if (it.st != 0xFF && it.stp && rng_next() < it.stp) apply_status(0, it.st);
}

static void do_gadget(uint8_t id) {
    items_t it;
    uint8_t ok;
    item_row(id, &it);
    if (it.cat != ITEMS_CAT_LLAVE) inv_take(id, 1);
    ev(EV_USE, 0, B_USE_GADGET, id);
    switch (it.efecto) {
    case ITEMS_EFECTO_RED:
        if (rng_next() < it.stp) apply_status(1, ST_ENREDADO); else ev(EV_MISS, 0, 0, 0);
        if (c_flying() == 0 && b_fly && !b_down) { b_down = 1; ev(EV_STATUS, 1, ST_DERRIBADO, 0); }
        break;
    case ITEMS_EFECTO_CEBO:
        ok = (b_sp.come & it.cebo) != 0;
        if (ok) {
            b_calm_t = (uint8_t)R(RULE_BAIT_TURNS);
            b_bait = (uint8_t)(id == b_sp.cebo ? R(RULE_QBAIT_FAV) : R(RULE_QBAIT_OTHER));
        }
        ev(EV_BAIT, 1, ok, 0);
        break;
    case ITEMS_EFECTO_ATAQUE:
        attack(0, it.pot, it.dtype, it.acc, it.crit, it.st, it.stp, 8, 0, 0);
        if (!b_cpv) creature_down();
        if (b_result == B_ONGOING && it.derriba && b_fly && !b_down && rng_next() < it.derriba) {
            b_down = 1; ev(EV_STATUS, 1, ST_DERRIBADO, 0);
        }
        break;
    case ITEMS_EFECTO_ESTADO:
        if (rng_next() < it.acc && rng_next() < it.stp) apply_status(1, it.st); else ev(EV_MISS, 0, 0, 0);
        break;
    case ITEMS_EFECTO_ILUMINAR:
        apply_status(1, ST_ILUMINADO);
        if (b_sp.hor == SPECIES_HOR_NOCHE && rng_next() < (uint8_t)R(RULE_LAMP_NIGHT_CEG)) apply_status(1, ST_CEGADO);
        break;
    case ITEMS_EFECTO_DERRIBAR:
        if (b_fly && !b_down) { b_down = 1; ev(EV_STATUS, 1, ST_DERRIBADO, 0); } else ev(EV_MISS, 0, 0, 0);
        break;
    }
}

// Capture (GDD 3.6). Every factor in quarters, u16 steps.
static uint8_t q_status(void) {
    statuses_t r;
    uint8_t q = (uint8_t)R(RULE_QST_NONE), v;
    if (b_cst != 0xFF) { st_row(b_cst, &r); q = r.q; }
    if (b_ent_t) { st_row(ST_ENREDADO, &r); v = r.q; if (v > q) q = v; }
    if (b_down) { st_row(ST_DERRIBADO, &r); v = r.q; if (v > q) q = v; }
    if (b_calm_t) { st_row(ST_CALMADO, &r); v = r.q; if (v > q) q = v; }
    return q;
}

static void do_capture(uint8_t lantern) {
    items_t it;
    uint16_t v = b_sp.catch;
    uint8_t q, roll, shakes, cond = 1;
    item_row(lantern, &it);
    inv_take(lantern, 1);
    ev(EV_THROW, 0, lantern, 0);
    q = (b_cpv << 3) <= b_cpv_max ? (uint8_t)R(RULE_QHP_12) : (b_cpv << 2) <= b_cpv_max ? (uint8_t)R(RULE_QHP_25)
      : (b_cpv << 1) <= b_cpv_max ? (uint8_t)R(RULE_QHP_50) : (uint8_t)R(RULE_QHP_HI);
    v = (v * q) >> 2;
    v = (v * q_status()) >> 2;
    q = it.val;
    if (it.fam != 0xFF && it.fam == b_sp.fam) q = it.val2;
    if (buff == BUFF_MANO_FIRME) q += 2;
    if (it.val == 255) v = 255; else v = (v * q) >> 2;
    v = (v * b_bait) >> 2;
    if (b_sp.cond == SPECIES_COND_ESTADO) cond = b_cst == b_sp.cond_st;
    else if (b_sp.cond == SPECIES_COND_SUELO) cond = b_down || b_ent_t;
    else if (b_sp.cond == SPECIES_COND_FAROL) cond = lantern == b_sp.cond_it;
    if (!cond) v = 0;
    roll = rng_next();
    if (v >= 255 || roll < v) {
        ev(EV_SHAKES, 1, 3, 1);
        b_new_species = !reg_has(reg_caught, b_species);
        if (b_new_species) reg_set(reg_caught, b_species);
        else if (full_n < FULL_SLOTS) { full_sp[full_n] = b_species; full_lv[full_n++] = b_level; }
        give_xp(b_new_species);
        b_result = B_CAPTURED;
        return;
    }
    shakes = roll < (v << 1) ? 2 : roll < (v << 2) ? 1 : 0;
    ev(EV_SHAKES, 1, shakes, 0);
    if (!cond) ev(EV_NOCOND, 1, 0, 0);
    if ((b_sp.beh == SPECIES_BEH_ASUSTADIZO || b_sp.beh == SPECIES_BEH_VOLADOR) && rng_next() < b_sp.escapa) {
        ev(EV_FLEE, 1, 1, 0);
        b_result = B_ESCAPED;
    }
}

static void do_flee(void) {
    int16_t p;
    uint8_t ok;
    b_flee_tries++;
    if (b_sp.beh == SPECIES_BEH_GUARDIAN) ok = 0;
    else if (b_ent_t) ok = 1;
    else {
        p = (int16_t)R(RULE_FLEE_BASE) + (int16_t)R(RULE_FLEE_AGI) * ((int16_t)p_agi() - c_agi())
            + (int16_t)R(RULE_FLEE_TRY) * (b_flee_tries - 1);
        if (p < (int16_t)R(RULE_FLEE_MIN)) p = R(RULE_FLEE_MIN);
        if (p > (int16_t)R(RULE_FLEE_MAX)) p = R(RULE_FLEE_MAX);
        ok = rng_next() < (uint8_t)p;
    }
    ev(EV_FLEE, 0, ok, 0);
    if (ok) b_result = B_FLED;
}

static void player_act(uint8_t kind, uint8_t id, uint8_t weapon) {
    if (loses_turn(0)) return;
    switch (kind) {
    case B_ACT_ATTACK: ev(EV_USE, 0, B_USE_WEAPON, id); use_weapon(id, 8, 0, 0, 1); break;
    case B_ACT_SKILL: do_skill(id, weapon); break;
    case B_ACT_ITEM: do_item(id); break;
    case B_ACT_GADGET: do_gadget(id); break;
    case B_ACT_CAPTURE: do_capture(id); break;
    case B_ACT_FLEE: do_flee(); break;
    }
}

// ---------------------------------------------------------------- creature AI (GDD 3.7)
static uint8_t choose_move(void) {
    uint8_t k, w[4], total = 0, r, m;
    moves_t *mv;
    // (1) low PV and it can flee or heal: 50 %
    if ((b_cpv << (uint8_t)R(RULE_AI_LOW_SH)) <= b_cpv_max) {
        for (k = 0; k < 4; k++) {
            m = (&b_sp.m1)[k * 2];
            if (m == 0xFF) continue;
            if (b_mv[k].efecto == MOVES_EFECTO_HUIR || b_mv[k].efecto == MOVES_EFECTO_CURA) {
                if (rng_next() < (uint8_t)R(RULE_AI_LOW_P)) return k;
                break;
            }
        }
    }
    for (k = 0; k < 4; k++) {
        m = (&b_sp.m1)[k * 2];
        w[k] = m == 0xFF ? 0 : (&b_sp.w1)[k * 2];
        mv = &b_mv[k];
        if (mv->efecto == MOVES_EFECTO_ESTADO && p_st == 0xFF) w[k] *= (uint8_t)R(RULE_AI_ST_MUL);   // (2)
        if (b_calm_t && mv->efecto == MOVES_EFECTO_DANO) w[k] = 0;                                  // (3)
        if (mv->efecto == MOVES_EFECTO_DEFENSA && b_last_move == k) w[k] = 0;                       // (4)
        if (mv->efecto == MOVES_EFECTO_HUIR && (b_ent_t || b_down)) w[k] = 0;
        total += w[k];
    }
    if (!total) return 0xFF;                       // nothing to do: it watches
    r = rng_range(total);
    for (k = 0; k < 4; k++) { if (r < w[k]) return k; r -= w[k]; }
    return 0xFF;
}

static void creature_act(void) {
    uint8_t k;
    moves_t *mv;
    if (loses_turn(1)) return;
    k = choose_move();
    if (k == 0xFF) { ev(EV_WATCH, 1, 0, 0); return; }
    b_last_move = k;
    mv = &b_mv[k];
    ev(EV_USE, 1, B_USE_MOVE, (&b_sp.m1)[k * 2]);
    switch (mv->efecto) {
    case MOVES_EFECTO_DANO:
        attack(1, mv->pot, mv->dtype, mv->acc, 0, mv->st, mv->stp, 8, 0, 0);
        if (!pv) b_result = B_FAINTED;
        break;
    case MOVES_EFECTO_ESTADO:
        if (mv->acc != 255 && rng_next() >= mv->acc) { ev(EV_MISS, 1, 0, 0); break; }
        if (rng_next() < mv->stp) apply_status(0, mv->st); else ev(EV_MISS, 1, 0, 0);
        break;
    case MOVES_EFECTO_DEFENSA:
        b_def_t = mv->turnos; b_def_sh = mv->val;
        ev(EV_DEFUP, 1, 0, 0);
        break;
    case MOVES_EFECTO_DEBUFF:
        b_pdeb_t = mv->turnos; b_pdeb_sh = mv->val;
        ev(EV_DEBUFF, 0, 0, 0);
        break;
    case MOVES_EFECTO_CURA:
        {
            uint8_t h = b_cpv_max >> mv->val;
            b_cpv = (uint16_t)b_cpv + h > b_cpv_max ? b_cpv_max : b_cpv + h;
            ev(EV_HEAL, 1, h, 0);
        }
        break;
    case MOVES_EFECTO_HUIR:
        if (rng_next() < mv->stp) { ev(EV_FLEE, 1, 1, 0); b_result = B_ESCAPED; }
        else ev(EV_FLEE, 1, 0, 0);
        break;
    case MOVES_EFECTO_ROBAR:
        if (rng_next() >= mv->acc) { ev(EV_MISS, 1, 0, 0); break; }
        {
            items_t it;
            for (k = 0; k < ITEM_COUNT; k++) {
                if (!inv[k]) continue;
                item_row(k, &it);
                if (it.bolsa == ITEMS_BOLSA_COMIDA) { inv[k]--; ev(EV_STEAL, 1, k, 0); return; }
            }
            ev(EV_MISS, 1, 0, 0);
        }
        break;
    }
}

// ---------------------------------------------------------------- end of turn
static void tick_status(uint8_t target) {
    statuses_t r;
    uint8_t st = target ? b_cst : p_st, d, mx = target ? b_cpv_max : pv_max;
    if (st == 0xFF) return;
    st_row(st, &r);
    if (r.dot) {
        d = mx >> r.dot;
        if (!d) d = 1;
        if (target) { b_cpv -= d < b_cpv ? d : b_cpv; if (!b_cpv) creature_down(); }
        else { pv -= d < pv ? d : pv; if (!pv) b_result = B_FAINTED; }
        ev(EV_DOT, target, d, st);
    }
    if (target == 0 && st == ST_ENVENENADO) return;            // Leo's poison lasts until cured
    if (r.tmin && (target ? b_cst_t : p_st_t)) {
        if (target ? !--b_cst_t : !--p_st_t) end_status(target);
    }
}

static uint8_t tick_flag(uint8_t *t, uint8_t st) {
    if (*t && !--*t) { ev(EV_STATUS_END, 1, st, 0); return 1; }
    return 0;
}

static void end_turn(void) {
    tick_status(0);
    if (b_result == B_ONGOING) tick_status(1);
    tick_flag(&b_ent_t, ST_ENREDADO);
    tick_flag(&b_calm_t, ST_CALMADO);
    tick_flag(&b_lit_t, ST_ILUMINADO);
    if (b_def_t) b_def_t--;
    if (b_pdeb_t) b_pdeb_t--;
    if (b_cdeb_t && !--b_cdeb_t) b_catk = cstat(4, b_sp.tat, 4);
    b_turn++;
}

// ---------------------------------------------------------------- one turn
// The creature's free first turn (ambush) runs from battle_open_turn() before Leo's first choice.
void battle_open_turn(void) BANKED {
    b_ev_n = 0;
    if (b_free == 2) { creature_act(); b_free = 0; }
}

void battle_turn(uint8_t kind, uint8_t id, uint8_t weapon) BANKED {
    uint8_t first;
    b_ev_n = 0;
    if (b_free == 1) {                                   // advantage: Leo acts, the creature does not
        b_free = 0;
        player_act(kind, id, weapon);
    } else {
        uint8_t rp = rng_next() & (uint8_t)R(RULE_INIT_RND), rc = rng_next() & (uint8_t)R(RULE_INIT_RND);
        first = (uint16_t)p_agi() + rp >= (uint16_t)c_agi() + rc;
        if (first) {
            player_act(kind, id, weapon);
            if (b_result == B_ONGOING) creature_act();
        } else {
            creature_act();
            if (b_result == B_ONGOING) player_act(kind, id, weapon);
        }
    }
    if (b_result == B_ONGOING) end_turn();
    if (b_result == B_HUNTED) {
        give_xp(0);
        roll_loot();
        if (kills[b_species] < 255) kills[b_species]++;
    }
    if (b_result == B_HUNTED || b_result == B_CAPTURED) b_levelups = player_gain_xp(b_xp);
    if (b_result != B_ONGOING) ev(EV_END, b_result, 0, 0);
}
