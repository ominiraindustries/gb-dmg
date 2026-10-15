// HAPPY VALLEY - the race model, banked part: the rival field (GDD 2.9), race setup, results, and the
// C references of race_move.s / race_think.s (tests/test_race.py runs both paths against
// tests/hv_model.py). See race.c for the rules of the port.
#pragma bank 255
#include "hv.h"

extern uint16_t race_seg_end[];
extern uint8_t race_seg_n, race_bends, race_bk, rc_dec, rc_cover_sh, rc_cost[];
extern uint8_t rc_len, rc_len2, rc_free_lo, rc_free_span, rc_lane_mask, rc_lanes_max, rc_spc, rc_res_sh;
extern uint8_t rc_pull_ticks, rc_dpct_tired, rc_start_eff[], rc_dpct[];
extern uint16_t rc_start16;
static uint8_t d100;

static int16_t clamp16(int16_t v, int16_t a, int16_t b) { return v < a ? a : v > b ? b : v; }

// ---------------------------------------------------------------- rival field (hv_model.gen_field)
void race_gen_field(uint8_t course, uint8_t lo, uint8_t hi, uint8_t n) BANKED {
    uint8_t k, j, t, r, base;
    bank_memcpy(BANK(tbl_courses), &crs, &tbl_courses[course], sizeof(crs));
    d100 = (uint8_t)(crs.dist / 100);
    rn_n = n;
    for (k = 0; k < n; k++) {                   // RNG: rating, vel res pun tem dpref fat jock estilo surf name x2
        r = lo + rng_range(hi - lo + 1);
        base = 20 + (r >> 1);
        rn_rating[k] = r;
        rn_vel[k] = (uint8_t)clamp16((int16_t)base + rng_range(17) - 8, 1, 99);
        rn_res[k] = (uint8_t)clamp16((int16_t)base + rng_range(17) - 8 + ((int16_t)d100 - 14) * 3, 1, 99);
        rn_pun[k] = (uint8_t)clamp16((int16_t)base + rng_range(17) - 8, 1, 99);
        rn_tem[k] = 30 + rng_range(51);
        rn_dpref[k] = (uint8_t)clamp16((int16_t)d100 + rng_range(5) - 2, 10, 24);
        rn_fat[k] = rng_range(30);
        rn_jock[k] = rng_range(8);
        rn_estilo[k] = rng_range(3);
        rn_tac[k] = rn_estilo[k];
        rn_surf[k] = (int8_t)rng_range(5) - 2;
        rn_name0[k] = rng_range(32);
        rn_name1[k] = rng_range(32);
    }
    for (k = 0; k < n; k++) rn_gate[k] = k + 1;
    for (k = n - 1; k; k--) {                   // Fisher-Yates
        j = rng_range(k + 1);
        t = rn_gate[k]; rn_gate[k] = rn_gate[j]; rn_gate[j] = t;
    }
    for (k = 0; k < n; k++) rn_weight[k] = (uint8_t)clamp16(133 - ((int16_t)hi - rn_rating[k]), 113, 133);
}

// ---------------------------------------------------------------- the race
void race_init(uint8_t course) BANKED {
    uint8_t i, k, j, t, apt;
    int16_t v;
    uint16_t acc = 0;
    runner_t *r;
    race_course = course;
    bank_memcpy(BANK(tbl_courses), &crs, &tbl_courses[course], sizeof(crs));
    d100 = (uint8_t)(crs.dist / 100);
    race_d16 = crs.dist << 4;
    rc_len = R8(RULE_LEN);
    rc_len2 = rc_len << 1;
    rc_free_lo = R8(RULE_FREE_BACK) - 1;
    rc_free_span = R8(RULE_FREE_BACK) - 1 + rc_len;
    rc_lane_mask = R8(RULE_LANE_MASK);
    rc_lanes_max = R8(RULE_LANES_MAX);
    rc_res_sh = R8(RULE_RES_SH);
    rc_pull_ticks = R8(RULE_PULL_TICKS);
    rc_dpct_tired = R8(RULE_DPCT_TIRED);
    for (k = 0; k < 3; k++) rc_start_eff[k] = R8(RULE_START_EFF0 + k);
    for (k = 0; k < 4; k++) rc_dpct[k] = R8(RULE_DPCT0 + k);
    rc_dec = R8(RULE_DEC);
    rc_cover_sh = R8(RULE_COVER_SH);
    for (k = 0; k < 4; k++) rc_cost[k] = R8(RULE_COST0 + k);
    race_bends = crs.bends;
    race_bk = crs.bk;
    rc_spc = R8(RULE_SPC);
    rc_start16 = RULE(RULE_START_M) << 4;
    race_seg_n = crs.nseg;
    for (k = 0; k < race_seg_n; k++) { acc += (&crs.m1)[k] << 4; race_seg_end[k] = acc; }
    race_final_from = race_seg_n > 1 ? race_seg_end[race_seg_n - 2] : 0;
    for (i = 0, r = rx; i < rn_n; i++, r++) {   // RNG: forma, sprint noise, delay
        apt = crs.track != COURSES_TRACK_AW ? (uint8_t)rn_surf[i] : (uint8_t)-rn_surf[i];
        v = (int16_t)RULE(RULE_V0) + (int16_t)RULE(RULE_KV) * rn_vel[i] - (int16_t)RULE(RULE_KW) * ((int16_t)rn_weight[i] - 113)
            + (int16_t)RULE(RULE_KJ) * rn_jock[i] + (int16_t)RULE(RULE_KSF) * (int8_t)apt;
        if (d100 < rn_dpref[i]) v -= (int16_t)(rn_dpref[i] - d100) * (int16_t)RULE(RULE_KDS);
        if (rn_fat[i] > R8(RULE_FAT_FROM)) v -= (int16_t)(rn_fat[i] - R8(RULE_FAT_FROM)) * (int16_t)RULE(RULE_FAT_K);
        v += ((int16_t)rng_range(7) - 3) * (int16_t)RULE(RULE_FORMA_K);
        memset(r, 0, sizeof(runner_t));
        r->vmax = (uint16_t)v;
        r->ene = (RULE(RULE_EB) + RULE(RULE_EK) * rn_res[i]) << 4;
        r->lane = rn_gate[i] - 1;
        r->dmul = 8 + (d100 > rn_dpref[i] ? d100 - rn_dpref[i] : 0);
        r->accl = R8(RULE_ACC_L0) + (rn_pun[i] >> 2);
        r->acc = R8(RULE_ACC_0) + (rn_pun[i] >> 4);
        r->kick = rn_pun[i] >> 1;
        r->launch = 1;
        r->eff = R8(RULE_START_EFF0 + rn_tac[i]);
        r->block = 0xFF;
        r->tac = rn_tac[i];
        r->jock_ok = rn_jock[i] >= 5;
        r->pull_p = R8(RULE_PULL_BASE) + ((100 - rn_tem[i]) >> 2)
                    + R8(RULE_MISMATCH0 + (rn_estilo[i] > rn_tac[i] ? rn_estilo[i] - rn_tac[i] : rn_tac[i] - rn_estilo[i]));
        for (k = 0; k < 4; k++) {               // per effort: target speed and drain (no multiply per tick)
            r->tgv[k] = r->vmax - (((r->vmax >> 4) * rc_dpct[k]) >> 4);
            r->drv[k] = (uint8_t)((rc_cost[k] * r->dmul) >> 3);
        }
        r->tgv[4] = r->vmax - (((r->vmax >> 4) * rc_dpct_tired) >> 4);
        r->sprint_at = RULE(RULE_SPRINT_AT0 + rn_tac[i]) + rng_range(41) - 20;
        r->delay = rng_range(4);
    }
    for (i = 0, r = rx; i < rn_n; i++, r++)     // slow starts
        if (rng_next() < ((100 - rn_tem[i]) >> 2) + (10 - rn_jock[i])) r->delay += 8 + rng_range(8);
    for (i = 0; i < rn_n; i++) order[i] = i;    // sorted by gate (insertion: stable, small)
    for (k = 1; k < rn_n; k++)
        for (j = k; j && rn_gate[order[j]] < rn_gate[order[j - 1]]; j--) { t = order[j]; order[j] = order[j - 1]; order[j - 1] = t; }
    for (k = 0; k < rn_n; k++) rx[order[k]].rank = k;
    race_t = 0;
    race_nfin = 0;
    race_done = 0;
}

// lane free: nobody (else, running) in it with pos - FREE_BACK < y < pos + LEN
static uint8_t lane_free(runner_t *x, uint8_t lane) {
    uint8_t k;
    uint16_t pos = x->pos;
    runner_t *y = rx;
    for (k = rn_n; k; k--, y++) {
        if (y == x || y->fin || y->lane != lane) continue;
        if ((uint16_t)(y->pos - pos + rc_free_lo) < rc_free_span) return 0;   // d in (-FREE_BACK, LEN), wrap-safe
    }
    return 1;
}

// the C reference of race_think.s (think_asm)
void think_c(runner_t *x, uint8_t i) BANKED {
    uint8_t rank = x->rank, k, eff, tac = x->tac, lane = x->lane, lane_turn, cover = 0;
    uint16_t rem, tg, g, pos = x->pos;
    runner_t *y, *ahead = 0;
    rem = (race_d16 - pos) >> 4;
    if ((race_t & 31) == i)                     // fighting the jockey
        if (rng_next() < x->pull_p) x->pull = R8(RULE_PULL_TICKS);
    if (pos < rc_start16) eff = R8(RULE_START_EFF0 + tac);
    else if (rem <= x->sprint_at) eff = (x->jock_ok && x->ene < rem * rc_spc && rem > 150) ? 1 : 3;
    else if (tac == 0) eff = rank <= 1 ? 1 : 2;
    else if (tac == 1) eff = 1;
    else eff = 0;
    if (eff == 3 && !x->sprint) { x->sprint = 1; x->reserve = (uint8_t)(x->ene >> R8(RULE_RES_SH)); }
    x->eff = eff;
    tg = x->tgv[x->ene ? eff : 4];
    if (eff == 3 && x->ene) tg += x->kick + x->reserve;
    x->target = tg;
    for (k = rank; k--; ) {                     // nearest horse ahead in my lane
        y = &rx[order[k]];
        if (y->pos <= pos) continue;            // g <= 0 (Python: not > 2 LEN, not counted)
        g = y->pos - pos;
        if (g > rc_len2) break;
        if (y->lane == lane && !y->fin) {
            cover = 1;
            if (g <= rc_len) ahead = y;
            break;
        }
    }
    x->cover = cover;
    x->block = 0xFF;
    lane_turn = (race_t & rc_lane_mask) == (i & rc_lane_mask);
    if (ahead && tg > ahead->spd) {
        if (lane_turn && lane < rc_lanes_max && lane_free(x, lane + 1)) x->lane = lane + 1;
        else x->block = (uint8_t)(ahead - rx);
    } else if (lane_turn && lane && lane_free(x, lane - 1)) {
        if (!(pos >= race_final_from && tac != 0 && eff == 3)) x->lane = lane - 1;
    }
}

// one runner's movement for one tick: the C reference of race_move.s (move_one)
void move_one_c(runner_t *r) BANKED {
    uint8_t dr;
    uint16_t tg = r->target, s, prog, spd = r->spd;
    if (spd < tg) { s = spd + (r->launch ? r->accl : r->acc); spd = s < tg ? s : tg; }
    else spd = (uint16_t)(spd - tg) > rc_dec ? spd - rc_dec : tg;   // max(tg, spd - DEC)
    if (r->launch && spd >= r->vmax - (r->vmax >> 3)) r->launch = 0;
    if (r->block != 0xFF && rx[r->block].spd < spd) spd = rx[r->block].spd;
    r->spd = spd;
    prog = spd;
    while (r->seg < race_seg_n && r->pos >= race_seg_end[r->seg]) r->seg++;   // == on_bend(pos): pos only grows
    if (r->seg < race_seg_n && ((race_bends >> r->seg) & 1)) prog -= ((spd >> 4) * (r->lane * race_bk)) >> 5;
    s = r->frac + prog;
    r->pos += s >> 8;
    r->frac = (uint8_t)s;
    if (r->ene) {
        dr = r->drv[r->eff];
        if (r->pull) dr <<= 1;
        else if (r->cover) dr -= dr >> rc_cover_sh;
        r->ene = r->ene > dr ? r->ene - dr : 0;
    }
    if (r->pull) r->pull--;
    if (r->pos >= race_d16) { r->fin = 1; r->fin_t = race_t; r->over = r->pos - race_d16; race_nfin++; }
}

// finishing order: tick ascending, overshoot descending, index ascending (Python's stable sort)
void race_results(void) BANKED {
    uint8_t k, j, t, n = 0, a, b;
    for (k = 0; k < rn_n; k++) if (rx[k].fin) res_i[n++] = k;
    for (k = 1; k < n; k++)
        for (j = k; j; j--) {
            a = res_i[j]; b = res_i[j - 1];
            if (rx[a].fin_t < rx[b].fin_t || (rx[a].fin_t == rx[b].fin_t && rx[a].over > rx[b].over)) {
                t = res_i[j]; res_i[j] = res_i[j - 1]; res_i[j - 1] = t;
            } else break;
        }
    for (k = 0; k < n; k++) { res_t[k] = rx[res_i[k]].fin_t; res_over[k] = rx[res_i[k]].over; }
    for (; k < rn_n; k++) res_i[k] = 0xFF;
}

uint8_t race_winner(void) BANKED {
    uint8_t k, w = 0xFF;
    for (k = 0; k < rn_n; k++) {
        if (!rx[k].fin) continue;
        if (w == 0xFF || rx[k].fin_t < rx[w].fin_t || (rx[k].fin_t == rx[w].fin_t && rx[k].over > rx[w].over)) w = k;
    }
    return w;
}
