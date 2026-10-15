// HAPPY VALLEY - shared declarations (GDD design/gdd.md). Modules: race.c (the race model, GDD 2.4,
// == tests/hv_model.py tick for tick; the rival field, GDD 2.9), main.c (loop, screens, test hooks).
// Balance numbers: res/data/*.tbl, read through RULE().
#pragma once
#include <string.h>
#include "gbe.h"
#include "vram.h"
#include "tbl_rules.h"
#include "tbl_courses.h"

extern uint16_t rules_cache[];
#define RULE(id) (rules_cache[id])
#define R8(id) ((uint8_t)rules_cache[id])

// ---------------------------------------------------------------- race (race.c)
#define RN_MAX 14
// runners: inputs (the stable's horses or gen_field's rivals)
extern uint8_t rn_n, rn_vel[], rn_res[], rn_pun[], rn_tem[], rn_dpref[], rn_fat[], rn_jock[], rn_estilo[];
extern uint8_t rn_tac[], rn_gate[], rn_weight[], rn_rating[], rn_name0[], rn_name1[];
extern int8_t rn_surf[];
// state: one record per runner
typedef struct {
    uint16_t pos, spd, ene, vmax, target, sprint_at, fin_t, over;
    uint8_t frac, lane, dmul, accl, acc, kick, launch, eff, sprint, reserve, cover, pull, block, fin, delay;
    uint8_t rank, seg, tac, jock_ok, pull_p;    // rank: index in order[]; seg: course segment of pos
    uint16_t tgv[5];                            // target by effort 0-3 (vmax - vmax/16 * dpct / 16), 4 = tired
    uint8_t drv[4];                             // energy drain by effort (cost * dmul >> 3)
    uint8_t pad[14];                            // 64 bytes: rx[i] = shifts (37 bytes made SDCC call a multiply)
} runner_t;
extern runner_t rx[];
extern uint8_t order[];
extern uint16_t race_t;
extern uint8_t race_nfin, race_done, race_course;
extern courses_t crs;                           // the course row
extern uint16_t race_d16, race_final_from;
// results in finishing order
extern uint8_t res_i[];
extern uint16_t res_t[], res_over[];
void race_gen_field(uint8_t course, uint8_t lo, uint8_t hi, uint8_t n) BANKED;   // rivals (uses rng_state)
void race_init(uint8_t course) BANKED;                 // pre-race RNG draws, the start
void race_tick(void);                           // one whole tick
void race_runners_range(uint8_t from, uint8_t to);   // part of a tick (split over frames)
void race_tick_end(void);                       // sort, clock, end of race
extern uint8_t rl_from, rl_to;
void move_one(runner_t *r);                     // race_move.s (asm)
void think_asm(runner_t *x, uint8_t i);         // race_think.s (asm)
void think_c(runner_t *x, uint8_t i) BANKED;           // its C reference
void race_runners(void);                        // race_loop.s: think + move every runner
void race_sort(void);                           // race_loop.s: order[] by pos, ranks
void move_one_c(runner_t *r) BANKED;                   // its C reference
extern uint8_t race_use_c;                      // tests: 1 = the C path
void race_results(void) BANKED;
uint8_t race_winner(void) BANKED;                      // the first one past the post so far (0xFF none)
// ---------------------------------------------------------------- race view (race_view.c)
void rv_build(void) BANKED;                     // LCD off
uint8_t rv_update(void) BANKED;                 // per frame; 1 = over
extern int16_t cam;
void place_all(void);                           // race_place.s: rv_x/rv_y of every runner
extern uint16_t rv_x[], rv_y[];
