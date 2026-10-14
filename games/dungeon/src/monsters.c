// TORRE HUNDIDA - monsters (GDD 2.5, 2.6): stats in a table, cheap AI, wind-up attacks.
// Timers count down every frame for active monsters; at most one monster "thinks" per frame
// (round robin), the platformer rule against peaks.
#include "game.h"
#include "floor1.h"

// GDD 2.6 table (index MON_*): all values to tune in playtest
static const uint8_t st_hp[] = { 3, 8, 12 };
static const uint8_t st_dmin[] = { 1, 1, 2 }, st_dmax[] = { 2, 3, 4 };
static const uint8_t st_acc[] = { 192, 176, 160 }, st_dodge[] = { 48, 24, 0 }, st_armor[] = { 0, 1, 0 };
static const uint8_t st_move[] = { 24, 40, 64 }, st_atk[] = { 48, 64, 80 }, st_wind[] = { 12, 16, 20 };
static const uint8_t st_detect[] = { 4, 5, 3 }, st_forget[] = { 7, 8, 6 };
static const char * const st_name[] = { "Diablillo", "Armadura", "Ojo" };

uint8_t mon_type[MON_MAX], mon_x[MON_MAX], mon_y[MON_MAX], mon_hp[MON_MAX], mon_state[MON_MAX];
uint8_t mon_move_t[MON_MAX], mon_atk_t[MON_MAX], mon_wind[MON_MAX], mon_item[MON_MAX];
uint8_t mon_flash[MON_MAX], mon_count, aware_count, mon_total, mon_rr;

void monsters_load(void) {
    uint8_t i, t, m;
    mon_count = 0;
    for (i = 0; i < FLOOR1_OBJ_COUNT; i++) {
        t = bank_read8(BANK(floor1), &floor1_obj_type[i]);
        if (t < OBJ_FAST || t > OBJ_SLOW || mon_count == MON_MAX) continue;
        m = mon_count++;
        mon_type[m] = t == OBJ_FAST ? MON_FAST : t == OBJ_SLOW ? MON_SLOW : MON_GUARD;
        mon_item[m] = t == OBJ_GUARD_KEY ? IT_KEY : IT_NONE;
        mon_x[m] = bank_read8(BANK(floor1), &floor1_obj_x[i]);
        mon_y[m] = bank_read8(BANK(floor1), &floor1_obj_y[i]);
        mon_hp[m] = st_hp[mon_type[m]];
        mon_state[m] = 0;
        mon_move_t[m] = st_move[mon_type[m]];
        mon_atk_t[m] = 0;
        mon_wind[m] = 0;
        mon_flash[m] = 0;
    }
    mon_total = mon_count;
    mon_rr = 0;
}

uint8_t mon_sprite_base(uint8_t type, uint8_t d) {
    if (d == 1) return type == MON_FAST ? SPR_FAST_D1 : type == MON_GUARD ? SPR_GUARD_D1 : SPR_SLOW_D1;
    return type == MON_FAST ? SPR_FAST_D2 : type == MON_GUARD ? SPR_GUARD_D2 : SPR_SLOW_D2;
}

static uint8_t dist_x(uint8_t m) { return mon_x[m] > px ? mon_x[m] - px : px - mon_x[m]; }
static uint8_t dist_y(uint8_t m) { return mon_y[m] > py ? mon_y[m] - py : py - mon_y[m]; }

uint8_t free_cell(uint8_t x, uint8_t y) {
    return walkable(x, y) && mon_at(x, y) == 0xFF && !(x == px && y == py);
}

// Greedy step toward the hero: bigger |delta| axis first (tie: x), else the other axis, else wait
static void move_to(uint8_t m, uint8_t x, uint8_t y) {
    mon_map[(mon_y[m] << 4) | mon_x[m]] = 0;
    mon_x[m] = x;
    mon_y[m] = y;
    mon_map[(y << 4) | x] = m + 1;
}

void chase(uint8_t m) {
    uint8_t x = mon_x[m], y = mon_y[m], ax = dist_x(m), ay = dist_y(m);
    int8_t sx = mon_x[m] < px ? 1 : -1, sy = mon_y[m] < py ? 1 : -1;
    if (ax >= ay && ax) {
        if (free_cell(x + sx, y)) { move_to(m, x + sx, y); return; }
        if (ay && free_cell(x, y + sy)) move_to(m, x, y + sy);
    } else if (ay) {
        if (free_cell(x, y + sy)) { move_to(m, x, y + sy); return; }
        if (ax && free_cell(x + sx, y)) move_to(m, x + sx, y);
    }
}

static void wander(uint8_t m) {
    uint8_t d = rng_next() & 3, x = mon_x[m] + view_dx[d], y = mon_y[m] + view_dy[d];
    if (free_cell(x, y)) move_to(m, x, y);
}

// Where the attacker is relative to the hero's facing: 0 front, 1 right, 2 back, 3 left
static uint8_t side_of(uint8_t m) {
    uint8_t d;
    for (d = 0; d < 4; d++)
        if ((uint8_t)(px + view_dx[d]) == mon_x[m] && (uint8_t)(py + view_dy[d]) == mon_y[m]) break;
    return (d - pf) & 3;
}

void attack_lands(uint8_t m) {
    uint8_t t = mon_type[m], acc = st_acc[t] - (amulet ? 32 : 0), dmg;
    if (rng_next() < acc) {
        dmg = st_dmin[t] + rng_range(st_dmax[t] - st_dmin[t] + 1);
        hero_damage(dmg, side_of(m));
    } else {
        say("Esquivas");
    }
}

void think(uint8_t m) {
    uint8_t t = mon_type[m], md = dist_x(m) + dist_y(m);
    if (md <= st_detect[t]) mon_state[m] |= MS_ALERT;
    else if (md > st_forget[t]) mon_state[m] &= ~MS_ALERT;
    if (mon_state[m] & (MS_WINDUP | MS_DYING)) return;
    if (mon_state[m] & MS_ALERT) {
        if (md == 1) {
            if (!mon_atk_t[m]) {                       // wind-up: warn, the hero may step away
                mon_state[m] |= MS_WINDUP;
                mon_wind[m] = st_wind[t];
                sfx(SFX_GROWL);
            }
        } else if (!mon_move_t[m]) {
            chase(m);
            mon_move_t[m] = st_move[t];
        }
    } else if (t == MON_FAST && !mon_move_t[m]) {
        wander(m);
        mon_move_t[m] = 72;
    }
}

// Timers of active monsters (Chebyshev <= 8), half of the monsters per frame (even / odd
// slots) with steps of 2: the whole list every frame cost ~10k T (SDCC arrays). A wind-up may end
// 1 frame late; nobody can tell.
static uint8_t half, aware_half[2];

static uint8_t tick2(uint8_t t) { return t > 2 ? t - 2 : 0; }

void monsters_update(void) {
    uint8_t m, n, s, dx, dy, aw = 0;
    half ^= 1;
    for (m = half; m < mon_count; m += 2) {
        s = mon_state[m];
        if (!mon_hp[m] && !(s & MS_DYING)) continue;
        mon_flash[m] = tick2(mon_flash[m]);
        if (s & MS_DYING) {                            // blink 24 f then gone
            mon_wind[m] = tick2(mon_wind[m]);
            if (!mon_wind[m]) { mon_state[m] = 0; dying_count--; }
            continue;
        }
        dx = mon_x[m] - px; if (dx & 0x80) dx = -dx;
        dy = mon_y[m] - py; if (dy & 0x80) dy = -dy;
        if ((dx | dy) & 0xF8 && (dx > 8 || dy > 8)) continue;   // only active monsters count time
        if (s & MS_ALERT) aw++;
        mon_move_t[m] = tick2(mon_move_t[m]);
        mon_atk_t[m] = tick2(mon_atk_t[m]);
        if ((s & MS_WINDUP) && !(mon_wind[m] = tick2(mon_wind[m]))) {
            mon_state[m] = s & ~MS_WINDUP;
            if (dx + dy == 1) attack_lands(m);
            mon_atk_t[m] = st_atk[mon_type[m]];
            mon_move_t[m] = st_move[mon_type[m]];
        }
    }
    aware_half[half] = aw;
    aware_count = aware_half[0] + aware_half[1];
    if (cheat_flags & CHEAT_FROZEN) return;
    for (n = 0; n < mon_count; n++) {                  // one live monster thinks per frame
        m = mon_rr;
        if (++mon_rr >= mon_count) mon_rr = 0;
        if (mon_hp[m]) { think(m); return; }
    }
}

// Hero attack on monster m (GDD 2.5)
void monster_hit(uint8_t m) {
    uint8_t t = mon_type[m], dmin = weapon ? 2 : 1, dmax = weapon ? 4 : 2, dmg;
    mon_state[m] |= MS_ALERT;
    if (!(cheat_flags & CHEAT_ONE_HIT) && rng_next() >= 208 - st_dodge[t]) {
        say("Fallas");
        sfx(SFX_MISS);
        return;
    }
    dmg = dmin + rng_range(dmax - dmin + 1);
    dmg = dmg > st_armor[t] ? dmg - st_armor[t] : 1;
    if (cheat_flags & CHEAT_ONE_HIT) dmg = 99;
    mon_flash[m] = 6;
    sfx(SFX_HIT);
    if (mon_hp[m] > dmg) {
        mon_hp[m] -= dmg;
        say_num("Golpe: ", dmg, "");
        return;
    }
    mon_hp[m] = 0;
    mon_state[m] = MS_DYING;
    mon_wind[m] = 24;
    mon_map[(mon_y[m] << 4) | mon_x[m]] = 0;
    dying_count++;
    kills++;
    sfx(SFX_KILL);
    say_num(st_name[t], 0xFF, " cae");
    if (mon_item[m] && item_count < ITEM_MAX) {        // the key falls on its cell
        item_type[item_count] = mon_item[m];
        item_x[item_count] = mon_x[m];
        item_y[item_count] = mon_y[m];
        item_count++;
        item_map[(mon_y[m] << 4) | mon_x[m]] = item_count;
        say("Suelta una llave");
    }
}
