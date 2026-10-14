// FARO kit - the field: Leo walking cell by cell on gbe_world, camera, talking and using things,
// map objects (NPCs, items, signs, warps, triggers, patches), Leo's sprite. GDD 2.1-2.3.
// Per-frame code: bank 0 (no #pragma bank). Content-free: everything comes from the map objects.
#include "rpg.h"

const int8_t dir_dx[4] = { 0, 0, -1, 1 };
const int8_t dir_dy[4] = { 1, -1, 0, 0 };

uint8_t px, py, pdir, pstep_px, pmoving, psneak, psub, phold, pbump, panim;
uint16_t steps;
int16_t cam_want_x, cam_want_y;
uint8_t last_clinic_map, last_clinic_x, last_clinic_y;
uint16_t act_script[GBE_GACT_MAX];
uint8_t act_obj_x[GBE_GACT_MAX], act_obj_y[GBE_GACT_MAX];
uint8_t warp_map, warp_x, warp_y, warp_dir, warp_pending;
uint8_t focus_sx, focus_sy, field_set = 0xFF;   // field_set: metatile set in VRAM
uint8_t script_actor = 0xFF;                      // the NPC whose script runs (face_player, walk)
uint8_t auto_dir, auto_n, npc_dir, npc_n, npc_walking, emote_who, emote_e, emote_t, was_script;
uint8_t demo_end_request;

#define TURN_FRAMES 6            // a tap shorter than this only turns (GDD 2.1)
#define BUMP_FRAMES 16

// ---------------------------------------------------------------- terrain
uint8_t gact_terrain_ok(uint8_t i, uint8_t x, uint8_t y) {
    (void)i;
    return !(wattr_at(x, y) & ATTR_SOLID);
}

static uint8_t blocked(uint8_t x, uint8_t y) {
    return (wattr_at(x, y) & ATTR_SOLID) || gact_at(x, y) != 0xFF;
}

static void camera(void) {
    int16_t ox = 0, oy = 0;
    if (pmoving) { ox = dir_dx[pdir] * (int16_t)pstep_px; oy = dir_dy[pdir] * (int16_t)pstep_px; }
    cam_want_x = ((int16_t)px << 4) + ox - 64;
    cam_want_y = ((int16_t)py << 4) + oy - 64;
    gact_px = px; gact_py = py;
    gact_px2 = pmoving ? px + dir_dx[pdir] : px;
    gact_py2 = pmoving ? py + dir_dy[pdir] : py;
}

// ---------------------------------------------------------------- map objects
static uint8_t actor_from(uint8_t x, uint8_t y) {
    uint8_t i;
    for (i = 0; i < GBE_GACT_MAX; i++)
        if (gact[i].type && act_obj_x[i] == x && act_obj_y[i] == y) return i;
    return 0xFF;
}

uint8_t look_tile(uint8_t look) BANKED;

// A sector entered the cache: its NPCs and items become actors, patches apply, spawn points start
static void sector_loaded(uint8_t sx, uint8_t sy) {
    uint8_t k, i;
    world_ev_t *e;
    world_events(sx, sy);
    for (k = 0, e = wev; k < wev_n; k++, e++) {
        switch (e->type) {
        case OBJ_NPC:
            if (actor_from(e->x, e->y) != 0xFF) break;
            i = gact_spawn(ACT_NPC | GACT_ANIMF, e->x, e->y, SPR_NPC + look_tile(e->d[0]),
                           e->d[2] == 2 ? GACT_WANDER : e->d[2] == 1 ? GACT_LOOK : GACT_STILL);
            if (i == 0xFF) break;
            gact[i].dir = e->d[1];
            gact[i].radius = 2;
            act_script[i] = EV_U16(e, 3);
            act_obj_x[i] = e->x; act_obj_y[i] = e->y;
            break;
        case OBJ_ITEM:
            if (flag_get(EV_U16(e, 2)) || actor_from(e->x, e->y) != 0xFF) break;
            i = gact_spawn(ACT_ITEM | GACT_ANIM2, e->x, e->y, SPR_FX + 6, GACT_STILL);
            if (i == 0xFF) break;
            act_obj_x[i] = e->x; act_obj_y[i] = e->y;
            break;
        case OBJ_PATCH:
            if (flag_get(EV_U16(e, 0))) world_set_cell(e->x, e->y, e->d[2]);
            break;
        }
    }
    creatures_sector(sx, sy);
}

// Patch objects of the loaded 3x3 again (after a script: it may have set their flags)
static void refresh_patches(void) {
    uint8_t sx, sy, k;
    world_ev_t *e;
    for (sy = focus_sy - 1; sy != (uint8_t)(focus_sy + 2); sy++)
        for (sx = focus_sx - 1; sx != (uint8_t)(focus_sx + 2); sx++) {
            if (sx >= wmap.w || sy >= wmap.h) continue;
            world_events(sx, sy);
            for (k = 0, e = wev; k < wev_n; k++, e++)
                if (e->type == OBJ_PATCH && flag_get(EV_U16(e, 0))) world_set_cell(e->x, e->y, e->d[2]);
        }
}

// ---------------------------------------------------------------- script ops support
void field_face_player(void) {
    if (script_actor != 0xFF && !gact[script_actor].moving) gact[script_actor].dir = pdir ^ 1;
}

uint8_t field_npc_walk(uint8_t dir, uint8_t n) {
    if (script_actor == 0xFF || !n) return 0;
    npc_dir = dir;
    npc_n = n;
    npc_walking = 1;
    return 1;
}

uint8_t field_auto_walk(uint8_t dir, uint8_t n) {
    if (!n) return 0;
    auto_dir = dir;
    auto_n = n;
    return 1;
}

void field_emote(uint8_t who, uint8_t e) {
    emote_who = who;
    emote_e = e > 2 ? 1 : e;                      // ! ? Zz (heart: '?' until it is drawn)
    emote_t = 40;
}

// Actors whose sector left the 3x3 cache go away (they come back when it loads again)
static void despawn_far(void) {
    uint8_t i, s;
    for (i = 0; i < GBE_GACT_MAX; i++) {
        if (!gact[i].type) continue;
        s = (gact[i].x >> 4) - focus_sx + 1;
        if (s > 2) { gact_free(i); continue; }
        s = (gact[i].y >> 4) - focus_sy + 1;
        if (s > 2) gact_free(i);
    }
}

// LCD off: load the map around (x, y), its objects, Leo facing dir
void field_enter(uint8_t map, uint8_t x, uint8_t y, uint8_t dir) {
    uint8_t i, sx, sy;
    for (i = 0; i < GBE_GACT_MAX; i++) gact_free(i);
    px = x; py = y; pdir = dir;
    pmoving = pstep_px = pbump = phold = 0;
    camera();
    i = world_map_mtset(map);                       // the map's tiles + metatiles first
    if (i != field_set) { field_set = i; map_gfx(i); }
    world_load_id(map, px, py, cam_want_x, cam_want_y);
    focus_sx = px >> 4;
    focus_sy = py >> 4;
    for (sy = focus_sy - 1; sy != (uint8_t)(focus_sy + 2); sy++)
        for (sx = focus_sx - 1; sx != (uint8_t)(focus_sx + 2); sx++)
            if (sx < wmap.w && sy < wmap.h) sector_loaded(sx, sy);
    state = ST_FIELD;
}

static void warp_to(world_ev_t *e) {
    warp_map = e->d[0];
    warp_x = e->d[1];
    warp_y = e->d[2];
    warp_dir = e->d[3];
    warp_pending = 1;
    transition(ST_FIELD);           // fade out -> screen_build -> field_enter(warp_*) -> fade in
}

// ---------------------------------------------------------------- talking / using (A)
static void use_front(void) {
    uint8_t fx = px + dir_dx[pdir], fy = py + dir_dy[pdir], a;
    world_ev_t *e;
    a = gact_at(fx, fy);
    if (a == 0xFF && (wattr_at(fx, fy) & 0x1F) == ATTR_K_COUNTER)    // talk across a counter
        a = gact_at(fx + dir_dx[pdir], fy + dir_dy[pdir]);
    if (a != 0xFF) {
        switch (ACT_KIND(gact[a].type)) {
        case ACT_NPC:
            if (!gact[a].moving) gact[a].dir = pdir ^ 1;      // face Leo (0<->1, 2<->3)
            script_actor = a;
            script_run_id(act_script[a]);
            return;
        case ACT_ITEM:
            e = world_event_at(act_obj_x[a], act_obj_y[a]);
            if (e && e->type == OBJ_ITEM) {
                flag_set(EV_U16(e, 2));
                gact_free(a);
                item_pickup(e->d[0], e->d[1]);
            }
            return;
        case ACT_CREATURE:
            creature_touch(a);
            return;
        }
    }
    e = world_event_at(fx, fy);
    if (!e) return;
    script_actor = 0xFF;
    if (e->type == OBJ_SIGN) script_run_id(EV_U16(e, 0));
    else if (e->type == OBJ_FORAGE) forage(e->d[0], fx, fy);
}

// ---------------------------------------------------------------- walking (GDD 2.1)
static uint8_t held_dir(void) {
    if (keys & J_DOWN) return DIR_DOWN;
    if (keys & J_UP) return DIR_UP;
    if (keys & J_LEFT) return DIR_LEFT;
    if (keys & J_RIGHT) return DIR_RIGHT;
    return 0xFF;
}

// Start a step in the held direction (a short tap in a new direction only turns)
static void try_walk(uint8_t chained) {
    uint8_t d = held_dir(), nx, ny, a;
    if (d == 0xFF) { phold = 0; return; }
    if (d != pdir && !chained) {
        pdir = d;
        phold = 1;
        return;
    }
    if (phold && phold < TURN_FRAMES) { phold++; return; }
    pdir = d;
    nx = px + dir_dx[d];
    ny = py + dir_dy[d];
    a = gact_at(nx, ny);
    if (a != 0xFF && ACT_KIND(gact[a].type) == ACT_CREATURE) { creature_touch(a); return; }
    if (blocked(nx, ny)) {
        if (!pbump) { pbump = BUMP_FRAMES; sfx(SFX_BUMP); }
        return;
    }
    pmoving = 1;
    pstep_px = 0;
    psub = 0;
}

static void step_done(void) {
    world_ev_t *e;
    px += dir_dx[pdir];
    py += dir_dy[pdir];
    pmoving = pstep_px = 0;
    steps++;
    survival_step();
    if (auto_n) {                                   // a scripted walk: no triggers, no chaining
        if (!--auto_n) script_resume();
        return;
    }
    e = world_event_at(px, py);
    if (e) {
        if (e->type == OBJ_WARP) { warp_to(e); return; }
        if (e->type == OBJ_TRIGGER && !flag_get(EV_U16(e, 2))) {   // the SCRIPT sets the flag when
            script_run_id(EV_U16(e, 0));                         // it is done (a locked door that
            return;                                              // says "closed" keeps firing)
        }
    }
    try_walk(1);                    // chained steps: no dead frame
}

void field_update(void) {
    if (warp_pending) return;
    if (pbump) pbump--;
    if (!pmoving && !script_active && !tbox_visible) {
        if (pressed & J_START) { menu_open_panel(); return; }
        if (pressed & J_A) { use_front(); camera(); return; }
        try_walk(0);
    }
    if (!pmoving && auto_n) {                       // scripted walk (op pwalk)
        pdir = auto_dir;
        if (blocked(px + dir_dx[pdir], py + dir_dy[pdir])) { auto_n = 0; script_resume(); }
        else { pmoving = 1; pstep_px = 0; psub = 0; }
    }
    if (pmoving) {
        psneak = (keys & J_B) && !auto_n ? 1 : 0;
        if (!psneak || (psub ^= 1)) pstep_px++;           // sneaking: 0.5 px/f (GDD 2.1)
        if ((pstep_px & 7) == 0) panim ^= 1;
        if (pstep_px >= 16) step_done();
    }
    camera();
}

// After the logic: world streaming, objects of newly loaded sectors, actors, creatures
void field_vblank(void) {
    uint8_t sx = px >> 4, sy = py >> 4;
    world_update(px, py, cam_want_x, cam_want_y);
    if (sx != focus_sx || sy != focus_sy) { focus_sx = sx; focus_sy = sy; despawn_far(); }
    if (world_loaded_slot != 0xFF) sector_loaded(world_loaded_sx, world_loaded_sy);
    if (!script_active) { gact_update(); creatures_update(); }
    else gact_move_all();                           // scripted NPC walks still move
    if (npc_walking && !gact[script_actor].moving) {
        if (npc_n && gact_try_move(script_actor, npc_dir)) npc_n--;
        else { npc_walking = 0; script_resume(); }
    }
    if (was_script && !script_active) refresh_patches();   // flags a script set (a lit lens...)
    was_script = script_active;
    if (emote_t) emote_t--;
}

// Leo: down 0 / up 8 / side 16 (+4 stepping; down/up alternate steps flipped), left = side flipped
void field_draw(void) {
    uint8_t tile, prop = 0;
    if (pdir >= DIR_LEFT) {
        tile = SPR_LEO + 16 + ((pmoving || pbump) && panim ? 4 : 0);
        if (pdir == DIR_LEFT) prop = S_FLIPX;
    } else {
        tile = SPR_LEO + (pdir == DIR_UP ? 8 : 0);
        if (pmoving || pbump) { tile += 4; if (panim) prop = S_FLIPX; }
    }
    if (wattr_at(px, py) & ATTR_PRIO) prop |= S_PRIORITY;
    oam16(OAM_LEO, 64 + 8, 64 + 16, tile, prop);
    gact_draw(OAM_ACTORS);
    if (emote_t) {                                  // above Leo or the speaking NPC
        int16_t ex = 64, ey = 64;
        if (emote_who == 0 && script_actor != 0xFF) { ex = gact_wx(script_actor) - cam_x; ey = gact_wy(script_actor) - cam_y; }
        oam8(OAM_FX, (uint8_t)ex + 4 + 8, (uint8_t)ey - 16 + 16, SPR_FX + (emote_e << 1), 0);
    } else shadow_OAM[OAM_FX].y = 0;
}
