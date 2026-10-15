// HAPPY VALLEY - the race model (GDD 2.4) and the rival field (GDD 2.9). Exact port of
// tests/hv_model.py (== design/race_proto.py): same integer maths, same RNG call order, same horse
// order in every loop. Unsigned differences are written so they never wrap where Python's ints are
// negative (comments mark each one). One struct per runner reached through a pointer (measured: the
// struct-of-arrays version with variable indexes cost 89k T per tick for 14 horses).
#include "hv.h"

uint8_t rn_n, rn_vel[RN_MAX], rn_res[RN_MAX], rn_pun[RN_MAX], rn_tem[RN_MAX], rn_dpref[RN_MAX];
uint8_t rn_fat[RN_MAX], rn_jock[RN_MAX], rn_estilo[RN_MAX], rn_tac[RN_MAX], rn_gate[RN_MAX];
uint8_t rn_weight[RN_MAX], rn_rating[RN_MAX], rn_name0[RN_MAX], rn_name1[RN_MAX];
int8_t rn_surf[RN_MAX];

runner_t rx[RN_MAX];
uint8_t order[RN_MAX];
uint16_t race_t, race_d16, race_final_from;
uint8_t race_nfin, race_done, race_course;
courses_t crs;
static uint16_t seg_end[6];
static uint8_t seg_n, d100, len2;
static uint8_t c_len, c_free_lo, c_free_span, c_lane_mask, c_lanes_max, c_dec, c_cover_sh;
static uint16_t c_spc, c_start16;
uint8_t res_i[RN_MAX];
uint16_t res_t[RN_MAX], res_over[RN_MAX];

static int16_t clamp16(int16_t v, int16_t a, int16_t b) { return v < a ? a : v > b ? b : v; }

// ---------------------------------------------------------------- rival field (hv_model.gen_field)
void race_gen_field(uint8_t course, uint8_t lo, uint8_t hi, uint8_t n) {
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
void race_init(uint8_t course) {
    uint8_t i, k, j, t, apt;
    int16_t v;
    uint16_t acc = 0;
    runner_t *r;
    race_course = course;
    bank_memcpy(BANK(tbl_courses), &crs, &tbl_courses[course], sizeof(crs));
    d100 = (uint8_t)(crs.dist / 100);
    race_d16 = crs.dist << 4;
    c_len = R8(RULE_LEN);                       // per-race constants in plain globals (cheapest access)
    len2 = c_len << 1;
    c_free_lo = R8(RULE_FREE_BACK) - 1;
    c_free_span = R8(RULE_FREE_BACK) - 1 + c_len;
    c_lane_mask = R8(RULE_LANE_MASK);
    c_lanes_max = R8(RULE_LANES_MAX);
    c_dec = R8(RULE_DEC);
    c_cover_sh = R8(RULE_COVER_SH);
    c_spc = RULE(RULE_SPC);
    c_start16 = RULE(RULE_START_M) << 4;
    seg_n = crs.nseg;
    for (k = 0; k < seg_n; k++) { acc += (&crs.m1)[k] << 4; seg_end[k] = acc; }
    race_final_from = seg_n > 1 ? seg_end[seg_n - 2] : 0;
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
        if ((uint16_t)(y->pos - pos + c_free_lo) < c_free_span) return 0;   // d in (-FREE_BACK, LEN), wrap-safe
    }
    return 1;
}

static void think(runner_t *x, uint8_t i) {
    uint8_t rank = x->rank, k, eff, tac = x->tac, lane = x->lane, lane_turn, dp, cover = 0;
    uint16_t rem, tg, g, pos = x->pos, vmax = x->vmax;
    runner_t *y, *ahead = 0;
    rem = (race_d16 - pos) >> 4;
    if ((race_t & 31) == i)                     // fighting the jockey
        if (rng_next() < x->pull_p) x->pull = R8(RULE_PULL_TICKS);
    if (pos < c_start16) eff = R8(RULE_START_EFF0 + tac);
    else if (rem <= x->sprint_at) eff = (x->jock_ok && x->ene < rem * c_spc && rem > 150) ? 1 : 3;
    else if (tac == 0) eff = rank <= 1 ? 1 : 2;
    else if (tac == 1) eff = 1;
    else eff = 0;
    if (eff == 3 && !x->sprint) { x->sprint = 1; x->reserve = (uint8_t)(x->ene >> R8(RULE_RES_SH)); }
    x->eff = eff;
    dp = x->ene ? R8(RULE_DPCT0 + eff) : R8(RULE_DPCT_TIRED);
    tg = vmax - (((vmax >> 4) * dp) >> 4);
    if (eff == 3 && x->ene) tg += x->kick + x->reserve;
    x->target = tg;
    for (k = rank; k--; ) {                     // nearest horse ahead in my lane
        y = &rx[order[k]];
        if (y->pos <= pos) continue;            // g <= 0 (Python: not > 2 LEN, not counted)
        g = y->pos - pos;
        if (g > len2) break;
        if (y->lane == lane && !y->fin) {
            cover = 1;
            if (g <= c_len) ahead = y;
            break;
        }
    }
    x->cover = cover;
    x->block = 0xFF;
    lane_turn = (race_t & c_lane_mask) == (i & c_lane_mask);
    if (ahead && tg > ahead->spd) {
        if (lane_turn && lane < c_lanes_max && lane_free(x, lane + 1)) x->lane = lane + 1;
        else x->block = (uint8_t)(ahead - rx);
    } else if (lane_turn && lane && lane_free(x, lane - 1)) {
        if (!(pos >= race_final_from && tac != 0 && eff == 3)) x->lane = lane - 1;
    }
}

void race_tick(void) {
    uint8_t i, k, j, t, dr;
    uint16_t tg, s, prog, spd;
    runner_t *r = rx;
    for (i = 0; i < rn_n; i++, r++) {
        if (r->fin) continue;
        if (r->delay) { r->delay--; continue; }
        if ((race_t & 3) == (i & 3)) think(r, i);
        tg = r->target;
        spd = r->spd;
        if (spd < tg) { s = spd + (r->launch ? r->accl : r->acc); spd = s < tg ? s : tg; }
        else spd = (uint16_t)(spd - tg) > c_dec ? spd - c_dec : tg;   // max(tg, spd - DEC)
        if (r->launch && spd >= r->vmax - (r->vmax >> 3)) r->launch = 0;
        if (r->block != 0xFF && rx[r->block].spd < spd) spd = rx[r->block].spd;
        r->spd = spd;
        prog = spd;
        while (r->seg < seg_n && r->pos >= seg_end[r->seg]) r->seg++;   // == on_bend(pos): pos only grows
        if (r->seg < seg_n && ((crs.bends >> r->seg) & 1)) prog -= ((spd >> 4) * (r->lane * crs.bk)) >> 5;
        s = r->frac + prog;
        r->pos += s >> 8;
        r->frac = (uint8_t)s;
        if (r->ene) {
            dr = (uint8_t)((R8(RULE_COST0 + r->eff) * r->dmul) >> 3);
            if (r->pull) dr <<= 1;
            else if (r->cover) dr -= dr >> c_cover_sh;
            r->ene = r->ene > dr ? r->ene - dr : 0;
        }
        if (r->pull) r->pull--;
        if (r->pos >= race_d16) { r->fin = 1; r->fin_t = race_t; r->over = r->pos - race_d16; race_nfin++; }
    }
    for (k = 1; k < rn_n; k++) {                // stable insertion sort, pos descending
        t = order[k];
        s = rx[t].pos;
        for (j = k; j && s > rx[order[j - 1]].pos; j--) order[j] = order[j - 1];
        order[j] = t;
    }
    for (k = 0; k < rn_n; k++) rx[order[k]].rank = k;
    race_t++;
    if (race_nfin >= rn_n || race_t >= RULE(RULE_MAX_TICKS)) { race_done = 1; race_results(); }
}

// finishing order: tick ascending, overshoot descending, index ascending (Python's stable sort)
void race_results(void) {
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

uint8_t race_winner(void) {
    uint8_t k, w = 0xFF;
    for (k = 0; k < rn_n; k++) {
        if (!rx[k].fin) continue;
        if (w == 0xFF || rx[k].fin_t < rx[w].fin_t || (rx[k].fin_t == rx[w].fin_t && rx[k].over > rx[w].over)) w = k;
    }
    return w;
}
