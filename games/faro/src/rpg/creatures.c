// FARO kit - creatures on the map (GDD 2.4): spawn points of the loaded sectors, at most
// RULE SPAWN_MAX alive, never appearing on screen; sight and the "!" alert; behaviours (wander,
// skittish, chaser, sleeper, flyer) on top of gbe_gact; touching = battle.
// Field sprites: 4 resident species slots of 8 tiles (critters.tiles) loaded through gbe_tiles.
// Per-creature data are 8-byte records (cr[], same index as the actor) walked with a pointer:
// arrays indexed by a variable cost ~1.5k T per creature per frame in SDCC (17 lines with 5).
#pragma bank 255
#include "rpg.h"
#include "critters.h"
#include "tbl_spawns.h"

#define PTS 8                                   // spawn points tracked (loaded 3x3 sectors)
uint8_t sp_x[PTS], sp_y[PTS], sp_table[PTS], sp_radius[PTS], sp_actor[PTS], sp_wait[PTS], sp_n;
uint16_t sp_back[PTS];                          // step count when a hunted/captured one comes back

typedef struct {
    uint8_t species, level, point, alert, timer, sleep, vis, beh2;   // species 0xFF = not a creature
} cr_t;
cr_t cr[GBE_GACT_MAX];
uint8_t cr_emotes;                              // creatures showing ! or Zz (0: creatures_draw hides and leaves)
uint8_t slot_species[4] = { 0xFF, 0xFF, 0xFF, 0xFF };
uint8_t cr_turn, cr_point_turn, cr_alive, cr_spawn_t;
uint8_t cr_ids[GBE_GACT_MAX];                  // actor slots of the living creatures (cr_alive of them):
                                               // the per-frame loops visit 5 creatures, not 16 slots
                                               // (an SDCC loop iteration costs 150-300 T even when empty)
uint8_t battle_actor = 0xFF;                    // the creature of the current battle
uint8_t pend_point = 0xFF, pend_sp, pend_lv;    // a spawn in progress (spawn_pending: 3 attempts)
static uint8_t pend_slot = 0xFF, pend_spd, pend_vis, pend_beh2, pend_beh;

#define R8(id) ((uint8_t)RULE(id))

static uint8_t dist(uint8_t a, uint8_t b) { return a > b ? a - b : b - a; }

// ---------------------------------------------------------------- spawn points
void creatures_sector(uint8_t sx, uint8_t sy) BANKED {
    uint8_t k, i;
    world_ev_t *e;
    (void)sx; (void)sy;                          // field_vblank already loaded wev[] of this sector
    for (k = 0, e = wev; k < wev_n; k++, e++) {
        if (e->type != OBJ_SPAWN) continue;
        for (i = 0; i < sp_n; i++) if (sp_x[i] == e->x && sp_y[i] == e->y) break;
        if (i < sp_n) continue;
        if (sp_n == PTS) {                       // forget the farthest point
            uint8_t far = 0, fd = 0, d;
            for (i = 0; i < PTS; i++) {
                d = dist(sp_x[i], px) + dist(sp_y[i], py);
                if (d > fd && sp_actor[i] == 0xFF) { fd = d; far = i; }
            }
            i = far;
        } else i = sp_n++;
        sp_x[i] = e->x; sp_y[i] = e->y; sp_table[i] = e->d[0]; sp_radius[i] = e->d[1];
        sp_actor[i] = 0xFF; sp_wait[i] = 0; sp_back[i] = 0;
    }
}

void creatures_reset(void) BANKED {
    uint8_t i;
    sp_n = 0;
    cr_alive = 0;
    cr_emotes = 0;
    pend_point = pend_slot = 0xFF;
    for (i = 0; i < GBE_GACT_MAX; i++) cr[i].species = 0xFF;
}

// species -> resident sprite slot. An empty slot first; else one no living creature uses (with
// none alive every slot looked free: two species of one table kept stealing slot 0 from each other,
// re-queuing their tiles, and nothing ever spawned). The tiles take 4 frames to arrive; the creature
// appears off screen, so it can spawn at once.
static uint8_t sprite_slot(uint8_t sp, uint8_t fspr) {
    uint8_t k, i, used;
    for (k = 0; k < 4; k++) if (slot_species[k] == sp) return k;
    for (k = 0; k < 4; k++) if (slot_species[k] == 0xFF) break;
    if (k == 4) {
        for (k = 0; k < 4; k++) {
            used = 0;
            for (i = 0; i < GBE_GACT_MAX; i++)
                if (cr[i].species == slot_species[k]) { used = 1; break; }
            if (!used) break;
        }
        if (k == 4) return 0xFF;
    }
    slot_species[k] = sp;
    tiles_push((uint8_t *)0x8000 + ((uint16_t)(SPR_CRITTER + k * 8) << 4), BANK(critters),
               critters_tiles + ((uint16_t)fspr << 7), 8);
    return k;
}

static uint8_t pick_entry(uint8_t table, uint8_t *lv) {
    spawns_t s;
    uint8_t k, total = 0, w[4], r, *e;
    bank_memcpy(BANK(tbl_spawns), &s, &tbl_spawns[table], sizeof(s));
    e = &s.e1;                                   // e1 e1lo e1hi e1w e1hor e1ring (6 bytes per entry)
    for (k = 0; k < 4; k++, e += 6) {
        w[k] = (e[0] != 0xFF && lamp_ring >= e[5]) ? e[3] : 0;
        total += w[k];
    }
    if (!total) return 0xFF;
    r = rng_range(total);
    for (k = 0, e = &s.e1; k < 4; k++, e += 6) {
        if (r < w[k]) { *lv = e[1] + (e[2] > e[1] ? rng_range(e[2] - e[1] + 1) : 0); return e[0]; }
        r -= w[k];
    }
    return 0xFF;
}

static uint8_t on_screen(uint8_t x, uint8_t y) {           // the screen + 1 cell of margin
    return (uint8_t)(x - (uint8_t)((uint16_t)cam_x >> 4) + 1) < 12 && (uint8_t)(y - (uint8_t)((uint16_t)cam_y >> 4) + 1) < 11;
}

static uint8_t free_actor(void) {
    gact_t *g = gact;
    uint8_t k;
    for (k = 0; k < GBE_GACT_MAX; k++, g++) if (!g->type) return 1;
    return 0;
}

// Spawning in three attempts (4 frames apart; one frame did ~30k T, two still made a 120-line frame):
// 1 checks the point and rolls the species and level; 2 picks the sprite slot (its tiles go to the
// queue: tiles_prepare's cost lands in this frame) and reads 5 bytes of the species row; 3 creates
// the actor.
#define SP_FIELD(sp, f) bank_read8(BANK(tbl_species), &tbl_species[sp].f)

static uint8_t point_free(uint8_t i) {
    return sp_actor[i] == 0xFF && gact_at(sp_x[i], sp_y[i]) == 0xFF && !on_screen(sp_x[i], sp_y[i]);
}

static void spawn_pending(void) {
    uint8_t i = pend_point, sp = pend_sp, slot = pend_slot, a;
    cr_t *c;
    if (slot == 0xFF) {                                       // attempt 2
        if (!point_free(i)) { pend_point = 0xFF; return; }
        slot = sprite_slot(sp, SP_FIELD(sp, fspr));
        if (slot == 0xFF) { sp_wait[i] = 60; pend_point = 0xFF; return; }   // 4 species already resident
        pend_slot = slot;
        pend_spd = SP_FIELD(sp, spd); pend_vis = SP_FIELD(sp, vis);
        pend_beh2 = SP_FIELD(sp, beh2); pend_beh = SP_FIELD(sp, beh);
        return;
    }
    pend_point = 0xFF;                                        // attempt 3
    pend_slot = 0xFF;
    if (!point_free(i)) return;
    a = gact_spawn(ACT_CREATURE | GACT_ANIM2, sp_x[i], sp_y[i], SPR_CRITTER + slot * 8, GACT_WANDER);
    if (a == 0xFF) return;
    gact_speed(a, pend_spd);
    gact[a].radius = sp_radius[i];
    c = &cr[a];
    c->species = sp; c->level = pend_lv; c->point = i;
    c->alert = 0; c->timer = 0;
    c->vis = pend_vis; c->beh2 = pend_beh2;
    c->sleep = pend_beh == SPECIES_BEH_DORMILON;
    if (c->sleep || pend_beh == SPECIES_BEH_GUARDIAN) gact[a].beh = GACT_STILL;
    sp_actor[i] = a;
    cr_ids[cr_alive++] = a;
}

static void try_spawn(uint8_t i) {
    uint8_t sp, lv, x = sp_x[i], y = sp_y[i], far = R8(RULE_SPAWN_DESPAWN);
    if (pend_point != 0xFF) { spawn_pending(); return; }
    if (sp_actor[i] != 0xFF) return;
    if (sp_wait[i]) { sp_wait[i]--; return; }
    if (sp_back[i] && (int16_t)(steps - sp_back[i]) < 0) return;
    if (cr_alive >= R8(RULE_SPAWN_MAX) || on_screen(x, y)) return;
    // never where think() would remove it at once (spawn, despawn, re-queue its tiles: churn)
    if (dist(x, px) >= far || dist(y, py) >= far) return;
    if (gact_at(x, y) != 0xFF || !free_actor()) return;   // cheap checks before the table copies
    sp = pick_entry(sp_table[i], &lv);
    if (sp == 0xFF) return;
    pend_point = i; pend_sp = sp; pend_lv = lv;
}

// ---------------------------------------------------------------- behaviour
static void despawn(uint8_t a, uint8_t wait) {
    uint8_t i = cr[a].point;
    if (i < PTS && sp_actor[i] == a) { sp_actor[i] = 0xFF; sp_wait[i] = wait; }
    gact_free(a);
    cr[a].species = 0xFF;
    for (i = 0; i < cr_alive; i++)
        if (cr_ids[i] == a) { cr_ids[i] = cr_ids[--cr_alive]; break; }
}

// the creature of the battle that just ended (GDD 2.4: hunted/captured come back after N steps)
void creatures_after_battle(uint8_t result) BANKED {
    uint8_t a = battle_actor, i;
    battle_actor = 0xFF;
    if (a == 0xFF || cr[a].species == 0xFF) return;
    i = cr[a].point;
    if (result == B_HUNTED || result == B_CAPTURED) {
        if (i < PTS) sp_back[i] = steps + RULE(RULE_SPAWN_KILL_STEPS);
        despawn(a, 0);
    } else despawn(a, 255);
}

static void think(uint8_t a, cr_t *c, gact_t *g) {
    uint8_t dx = dist(g->x, px), dy = dist(g->y, py), vis;
    if (dx > R8(RULE_SPAWN_DESPAWN) || dy > R8(RULE_SPAWN_DESPAWN)) { despawn(a, R8(RULE_SPAWN_RESPAWN_F) >> 2); return; }
    if (c->sleep) { g->beh = GACT_STILL; return; }          // woken by Leo's steps (creatures_step)
    vis = c->vis;
    if (psneak) vis >>= R8(RULE_SNEAK_VIS_SH);
    if (!c->alert && dx + dy <= vis) {
        c->alert = 1;
        c->timer = R8(RULE_ALERT_F);
        g->beh = GACT_STILL;
        sfx(SFX_BLIP);
        return;
    }
    if (c->alert == 1 && !c->timer) {            // after the "!": the alerted behaviour
        c->alert = 2;
        if (c->beh2 == SPECIES_BEH2_ASUSTADIZO || c->beh2 == SPECIES_BEH2_VOLADOR) { g->beh = GACT_FLEE; c->timer = R8(RULE_FLEE_F); }
        else if (c->beh2 == SPECIES_BEH2_PERSEGUIDOR) { g->beh = GACT_CHASE; c->timer = 255; }
        else { g->beh = GACT_WANDER; c->alert = 0; }
    }
    if (c->alert == 2 && !c->timer) { g->beh = GACT_HOME; c->alert = 0; }
}

// Leo finished a step: sleepers near him may wake (GDD 2.4 DORMILON)
void creatures_step(void) BANKED {
    uint8_t k, a, p = psneak ? R8(RULE_WAKE_SNEAK) : R8(RULE_WAKE_WALK);
    cr_t *c;
    gact_t *g;
    for (k = 0; k < cr_alive; k++) {
        a = cr_ids[k]; c = &cr[a]; g = &gact[a];
        if (!c->sleep) continue;
        if (dist(g->x, px) + dist(g->y, py) <= R8(RULE_WAKE_DIST) && p && rng_next() < p) { c->sleep = 0; c->alert = 0; }
    }
}

void creatures_update(void) BANKED {
    uint8_t k, a, e = 0, think_done = !gact_think_frame;   // creatures think on the NPCs' off frames
    cr_t *c;
    gact_t *g;
    if (sp_n && !(++cr_spawn_t & 3) && !step_frame) {   // one spawn point every 4 frames, not with a step's end
        if (++cr_point_turn >= sp_n) cr_point_turn = 0;
        try_spawn(cr_point_turn);
    }
    if (!cr_alive) { cr_emotes = 0; return; }
    if (cr_turn >= cr_alive) cr_turn = 0;
    for (k = 0; k < cr_alive; k++) {             // one pass: timers, emotes, chasers, one thinker
        a = cr_ids[k]; c = &cr[a]; g = &gact[a];
        if (c->timer) c->timer--;
        if (c->alert == 1 || c->sleep) e++;
        if (g->moving) continue;
        if (c->alert == 2 && g->beh == GACT_CHASE && dist(g->x, px) + dist(g->y, py) == 1 && !(cheat_flags & 1)) {
            battle_actor = a;                    // a chasing creature next to Leo attacks: ambush
            battle_request(c->species, c->level, 2);
            return;
        }
        if (!think_done && k >= cr_turn) { cr_turn = k + 1; think_done = 1; think(a, c, g); if (cr_alive <= k) break; }
    }
    if (!think_done) cr_turn = 0;               // round robin: next time from the first
    cr_emotes = e;
}

// Leo walked into / used A on a creature: advantage unless it had seen him
uint8_t creature_touch(uint8_t a) BANKED {
    cr_t *c = &cr[a];
    if (c->species == 0xFF || (cheat_flags & 1)) return 0;   // tests: 1 = creatures never start battles
    battle_actor = a;
    battle_request(c->species, c->level, (c->alert && !c->sleep) ? 0 : 1);
    return 1;
}

// emotes over alerted / sleeping creatures (OAM_FX + 1..3), placed from the actor's OAM entry that
// gact_draw just wrote (no position maths here)
void creatures_draw(void) BANKED {
    uint8_t k, a, n = 1;
    cr_t *c;
    OAM_item_t *o;
    if (cr_emotes) {
        for (k = 0; k < cr_alive && n < 4; k++) {
            a = cr_ids[k]; c = &cr[a]; o = &shadow_OAM[OAM_ACTORS + (a << 1)];
            if (!(c->alert == 1 || c->sleep) || !o->y) continue;
            oam8(OAM_FX + n, o->x + 4, o->y - 16, SPR_FX + (c->sleep ? 4 : 0), 0);
            n++;
        }
    }
    for (; n < 4; n++) shadow_OAM[OAM_FX + n].y = 0;
}

// A creature that has seen Leo (alert) at <= d cells (Chebyshev): no camping (GDD 2.7)
uint8_t creatures_alert_near(uint8_t d) BANKED {
    uint8_t k, a;
    for (k = 0; k < cr_alive; k++) {
        a = cr_ids[k];
        if (cr[a].alert && dist(gact[a].x, px) <= d && dist(gact[a].y, py) <= d) return 1;
    }
    return 0;
}
