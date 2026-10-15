// HAPPY VALLEY - the race model (GDD 2.4), bank 0 part: state, constants, race_tick (asm hot parts:
// race_move.s, race_think.s). Setup, results and the C references: race_cold.c (bank 1). Exact port of
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
uint16_t race_seg_end[6];                      // read by race_move.s
uint8_t race_seg_n, race_bends, race_bk, rc_dec, rc_cover_sh, rc_cost[4], race_use_c;   // use_c: tests
// per-race constants in plain globals (cheapest access; race_think.s reads them)
uint8_t rc_len, rc_len2, rc_free_lo, rc_free_span, rc_lane_mask, rc_lanes_max, rc_spc, rc_res_sh;
uint8_t rc_pull_ticks, rc_dpct_tired, rc_start_eff[3], rc_dpct[4];
uint16_t rc_start16;
uint8_t res_i[RN_MAX];
uint16_t res_t[RN_MAX], res_over[RN_MAX];

// runners from..to-1 of the current tick (think every 4 ticks, move): a tick may be split in two
// calls (two frames), the result is the same as one call (runners are processed in index order)
void race_runners_range(uint8_t from, uint8_t to) {
    uint8_t i;
    runner_t *r;
    if (!race_use_c) { rl_from = from; rl_to = to; race_runners(); return; }   // race_loop.s
    for (i = from, r = rx + from; i < to; i++, r++) {
        if (r->fin) continue;
        if (r->delay) { r->delay--; continue; }
        if ((race_t & 3) == (i & 3)) think_c(r, i);
        move_one_c(r);
    }
}

// the end of a tick: order by pos, ranks, the clock, the end of the race
void race_tick_end(void) {
    uint8_t k, j, t;
    uint16_t s;
    if (!race_use_c) race_sort();
    else {
        for (k = 1; k < rn_n; k++) {            // stable insertion sort, pos descending
            t = order[k];
            s = rx[t].pos;
            for (j = k; j && s > rx[order[j - 1]].pos; j--) order[j] = order[j - 1];
            order[j] = t;
        }
        for (k = 0; k < rn_n; k++) rx[order[k]].rank = k;
    }
    race_t++;
    if (race_nfin >= rn_n || race_t >= RULE(RULE_MAX_TICKS)) { race_done = 1; race_results(); }
}

void race_tick(void) {
    race_runners_range(0, rn_n);
    race_tick_end();
}
