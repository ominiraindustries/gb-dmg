// TORRE HUNDIDA - PLAY: hero, view stepping with bob/slide, seen cells, items, doors, attacks,
// HUD status row, sprites (GDD 2.1-2.11, design/ui.md 4).
#include <string.h>
#include "game.h"
#include "floor1.h"
#include "screen_play.h"

#define STEP_BOB    1           // GDD 2.1 effects (constants for the playtest)
#define TURN_SLIDE  1
#define REGEN_F     300
#define W_OFS(at)   ((at) - 12 * 32)                   // window offset of a play.screen define

uint8_t dmap[256], seen[32];
uint8_t px, py, pf, shown_x, shown_y, shown_f;
uint8_t hp, hp_max, key_count, potions, weapon, staff_owned, amulet, atk_cd, move_cd, kills;
uint16_t play_secs;
uint8_t item_type[ITEM_MAX], item_x[ITEM_MAX], item_y[ITEM_MAX], item_count, items_total, items_got;
uint8_t hurt_dir, hurt_t, slash_t, claw_t, bob_t, slide_dir, pending_act, last_roll, clear_req;
uint8_t seen_due, composed;            // mark seen cells the frame after composing; skip sprites
static uint8_t flips_seen, sec_t, hud_flag, hud_buf[20], heart_t;
static uint16_t regen_t;                              // counts to REGEN_F = 300: 8 bits never got there

const uint8_t cell_class[] = { VIEW_FREE, VIEW_WALL, VIEW_DOOR, VIEW_LOCKED, VIEW_FREE, VIEW_UP, VIEW_DOWN };

uint8_t view_cell(uint8_t x, uint8_t y) {
    if ((x | y) & 0xF0) return VIEW_WALL;             // off the map (also -1 = 0xFF)
    return cell_class[dmap[(y << 4) | x]];
}

uint8_t walkable(uint8_t x, uint8_t y) {
    uint8_t c;
    if ((x | y) & 0xF0) return 0;
    c = dmap[(y << 4) | x];
    return c == CELL_FLOOR || c == CELL_DOOR_OPEN;
}

uint8_t mon_map[256], item_map[256], maps_dirty, dying_count;

void maps_rebuild(void) {
    uint8_t i;
    memset(mon_map, 0, 256);
    memset(item_map, 0, 256);
    for (i = 0; i < mon_count; i++)
        if (mon_hp[i]) mon_map[(mon_y[i] << 4) | mon_x[i]] = i + 1;
    for (i = 0; i < item_count; i++)
        if (item_type[i]) item_map[(item_y[i] << 4) | item_x[i]] = i + 1;
    maps_dirty = 0;
}

static uint8_t mon_dying_at(uint8_t x, uint8_t y) {
    uint8_t m;
    if (!dying_count) return 0xFF;
    for (m = 0; m < mon_count; m++)
        if ((mon_state[m] & MS_DYING) && mon_x[m] == x && mon_y[m] == y) return m;
    return 0xFF;
}

uint8_t mon_at(uint8_t x, uint8_t y) {
    if ((x | y) & 0xF0) return 0xFF;
    return mon_map[(y << 4) | x] - 1;                 // 0 - 1 = 0xFF
}

static uint8_t item_at(uint8_t x, uint8_t y) {
    if ((x | y) & 0xF0) return 0xFF;
    return item_map[(y << 4) | x] - 1;
}

// ---------------------------------------------------------------- messages
void say(const char *s) {
    log_push(s);
}

// prefix + n (0xFF = no number) + suffix, <= 18 chars
void say_num(const char *prefix, uint8_t n, const char *suffix) {
    char b[24], *d = b;
    while (*prefix) *d++ = *prefix++;
    if (n != 0xFF) {
        if (n >= 10) *d++ = '0' + n / 10;
        *d++ = '0' + n % 10;
    }
    while (*suffix) *d++ = *suffix++;
    *d = 0;
    log_push(b);
}

// ---------------------------------------------------------------- HUD status row (ui.md 4.1)
void hud_dirty(void) { hud_flag = 1; }

static uint8_t digit(uint8_t d) { return VRAM_FONT + FONT_DIGIT0 + d; }

// 2 digits (tens blank if blank_tens and 0): subtraction, not / and % (SDCC calls a routine)
static void two_digits(uint8_t *d, uint8_t v, uint8_t blank_tens) {
    uint8_t t = 0;
    while (v >= 10) { v -= 10; t++; }
    d[0] = (t || !blank_tens) ? digit(t) : txt_blank;
    d[1] = digit(v);
}

void hud_render(void) {
    uint8_t *b = hud_buf, a = W_OFS(SCREEN_PLAY_AT_18_20);
    memset(b, txt_blank, 20);
    b[a - 1] = VRAM_UI + UI_ICON_HP;
    two_digits(b + a, hp, 1);
    b[a + 2] = VRAM_FONT + FONT_SLASH;
    two_digits(b + a + 3, hp_max, 0);
    b[a + 6] = VRAM_UI + (weapon ? UI_ICON_STAFF : UI_ICON_DAGGER);
    b[a + 7] = amulet ? VRAM_UI + UI_ICON_AMULET : txt_blank;
    b[W_OFS(SCREEN_PLAY_AT_1) - 1] = VRAM_UI + UI_ICON_KEY;
    b[W_OFS(SCREEN_PLAY_AT_1)] = digit(key_count);
    b[W_OFS(SCREEN_PLAY_AT_3) - 1] = VRAM_UI + UI_ICON_POTION;
    b[W_OFS(SCREEN_PLAY_AT_3)] = digit(potions);
    b[W_OFS(SCREEN_PLAY_AT_N) - 1] = VRAM_UI + UI_ICON_COMPASS;
    b[W_OFS(SCREEN_PLAY_AT_N)] = VRAM_FONT + FONT_LETTER_A + ("NESO"[pf] - 'A');
    vq_push(WIN_ROW(0), b, 20);
    hud_flag = 0;
}

static void hud_heart(void) {                         // low HP: heart blinks every 16 f
    uint8_t t = VRAM_UI + UI_ICON_HP, a = W_OFS(SCREEN_PLAY_AT_18_20) - 1;
    if (++heart_t < 16) return;
    heart_t = 0;
    if (hp <= hp_max / 4 && hud_buf[a] == t) t = txt_blank;
    else if (hud_buf[a] == t) return;
    hud_buf[a] = t;
    vq_push(WIN_ROW(0) + a, &t, 1);
}

// ---------------------------------------------------------------- seen cells (GDD 2.10)
// gbe_view.c view_mark_seen, from the classes of the last view_compose (same rule as the GDD and
// tests/test_play.py seen_model)
void mark_seen(void) {
    view_mark_seen(seen);
}

// ---------------------------------------------------------------- start / load
static void items_load(void) {
    uint8_t i, t;
    item_count = 0;
    for (i = 0; i < FLOOR1_OBJ_COUNT; i++) {
        t = bank_read8(BANK(floor1), &floor1_obj_type[i]);
        if (t == OBJ_START) {
            px = bank_read8(BANK(floor1), &floor1_obj_x[i]);
            py = bank_read8(BANK(floor1), &floor1_obj_y[i]);
            continue;
        }
        if (t < OBJ_POTION || item_count == ITEM_MAX) continue;
        item_type[item_count] = t == OBJ_POTION ? IT_POTION : t == OBJ_STAFF ? IT_STAFF :
                                t == OBJ_AMULET ? IT_AMULET : IT_KEY;
        item_x[item_count] = bank_read8(BANK(floor1), &floor1_obj_x[i]);
        item_y[item_count] = bank_read8(BANK(floor1), &floor1_obj_y[i]);
        item_count++;
    }
    items_total = item_count;
    for (i = 0; i < FLOOR1_OBJ_COUNT; i++)            // the guard's key counts as an item too
        if (bank_read8(BANK(floor1), &floor1_obj_type[i]) == OBJ_GUARD_KEY) items_total++;
}

// New game on floor 1 (the view itself is drawn by the caller with the LCD off)
void play_start(void) {
    bank_memcpy(BANK(floor1), dmap, floor1_map, 256);
    memset(seen, 0, sizeof(seen));
    items_load();
    monsters_load();
    dying_count = 0;
    maps_rebuild();
    pf = FLOOR1_FACING;
    hp = hp_max = 20; key_count = 0; potions = 1; weapon = 0; staff_owned = 0; amulet = 0;
    atk_cd = move_cd = kills = 0; items_got = 0; play_secs = 0;
    hurt_t = slash_t = claw_t = bob_t = 0; pending_act = 0;
    shown_x = px; shown_y = py; shown_f = pf;
    flips_seen = view_flips;
    play_sub = PS_IDLE;
    mark_seen();
    hud_render();
}

// ---------------------------------------------------------------- actions
void hero_damage(uint8_t dmg, uint8_t dir) {
    hurt_dir = dir;
    hurt_t = 8;
    if (dir == 0) claw_t = 8;
    sfx(SFX_HURT);
    say_num("Te hiere: ", dmg, "");
    if (cheat_flags & CHEAT_INVINCIBLE) return;
    hp = hp > dmg ? hp - dmg : 0;
    hud_dirty();
    if (!hp) {
        play_sub = PS_DYING;
        sfx(SFX_DEATH);
    }
}

void pick_up(void) {
    uint8_t i = item_at(px, py), t;
    if (i == 0xFF) return;
    t = item_type[i];
    if ((t == IT_KEY && key_count == 9) || (t == IT_POTION && potions == 9)) {
        say("No puedes");
        say("llevar mas");
        return;
    }
    if (t == IT_KEY) { key_count++; say("Coges una llave"); }
    else if (t == IT_POTION) { potions++; say("Coges una pocion"); }
    else if (t == IT_STAFF) { weapon = 1; staff_owned = 1; say("Coges el baculo"); }
    else { amulet = 1; say("Coges el amuleto"); }
    item_type[i] = IT_NONE;
    item_map[(py << 4) | px] = 0;
    items_got++;
    sfx(SFX_PICK);
    hud_dirty();
}

// The step frame only composes (~37k T): seen cells (automap only) the next frame, and the
// sprites are not rebuilt this frame (the screen still shows the old view for 3 frames)
void start_view(void) {
    view_compose(px, py, pf);
    bgbuf_start(view_buf, VIEW_H, VIEW_ROW);
    play_sub = PS_BUSY;
    seen_due = 1;
    composed = 1;
}

// A on the cell in front (GDD 2.5, 2.8)
static void act_front(void) {
    uint8_t fx = px + view_dx[pf], fy = py + view_dy[pf], m, *c;
    m = mon_at(fx, fy);
    if (m != 0xFF) {
        if (atk_cd) return;
        atk_cd = weapon ? 28 : 20;
        slash_t = 8;
        sfx(SFX_SWING);
        monster_hit(m);
        return;
    }
    if ((fx | fy) & 0xF0) return;
    c = &dmap[(fy << 4) | fx];
    if (*c == CELL_DOOR) { *c = CELL_DOOR_OPEN; sfx(SFX_DOOR); say("Abres la puerta"); start_view(); }
    else if (*c == CELL_LOCKED) {
        if (key_count) { key_count--; *c = CELL_DOOR_OPEN; sfx(SFX_UNLOCK); say("Usas la llave"); hud_dirty(); start_view(); }
        else { sfx(SFX_LOCKED); say("Esta cerrada"); }
    } else if (*c == CELL_UP) { sfx(SFX_LOCKED); say("El hueco se cerro"); }
    else if (!atk_cd) { atk_cd = weapon ? 28 : 20; slash_t = 8; sfx(SFX_SWING); }
}

// Movement and turning: 1 action per press, repeat every 12 f while held (GDD 2.1)
uint8_t move(uint8_t k) {
    uint8_t nx = px, ny = py, r = (pf + 1) & 3, c;
    if (k & J_B) {
        if (k & J_LEFT) { nx -= view_dx[r]; ny -= view_dy[r]; }
        else if (k & J_RIGHT) { nx += view_dx[r]; ny += view_dy[r]; }
        else if (k & J_DOWN) { pf = (pf + 2) & 3; slide_dir = 1; }
        else return 0;
    } else if (k & J_UP) { nx += view_dx[pf]; ny += view_dy[pf]; }
    else if (k & J_DOWN) { nx -= view_dx[pf]; ny -= view_dy[pf]; }
    else if (k & J_LEFT) { pf = (pf + 3) & 3; slide_dir = 2; }
    else if (k & J_RIGHT) { pf = r; slide_dir = 1; }
    else return 0;
    if (nx != px || ny != py) {
        c = ((nx | ny) & 0xF0) ? CELL_WALL : dmap[(ny << 4) | nx];
        if (c == CELL_DOWN && (k & J_UP)) {
            say("Bajas la escalera");
            sfx(SFX_CLEAR);
            clear_req = 1;                          // screens.c takes it from here
            return 1;
        }
        if (!walkable(nx, ny) || mon_at(nx, ny) != 0xFF) {
            sfx(SFX_BUMP);
            if (c == CELL_UP) say("El hueco se cerro");
            shake_y = 1;
            bob_t = 0;
            return 1;
        }
        px = nx; py = ny;
        bob_t = STEP_BOB ? 4 : 0;
        pick_up();
    }
    hud_dirty();                                    // compass
    start_view();
    return 1;
}

void play_update(void) {
    uint8_t k = keys;
    if (maps_dirty) maps_rebuild();
    if (seen_due) { seen_due = 0; mark_seen(); }
    if (play_sub == PS_DYING) return;
    if (++sec_t == 60) { sec_t = 0; if (play_secs < 5999) play_secs++; }
    if (atk_cd) atk_cd--;
    if (slash_t) slash_t--;
    if (claw_t) claw_t--;
    if (hurt_t) { hurt_t--; shake_x = hurt_t ? ((hurt_t & 2) ? 2 : -2) : 0; }
    if (shake_y && !hurt_t) shake_y = 0;
    if (!aware_count && hp < hp_max) {
        if (++regen_t >= REGEN_F) { regen_t = 0; hp++; hud_dirty(); }
    } else regen_t = 0;
    // the view copy: slide while copying a turn, bob after a step, sprites follow the shown view
    if (play_sub == PS_BUSY) {
        if (TURN_SLIDE && slide_dir) scx_shadow += slide_dir == 1 ? 8 : -8;
        if (view_flips != flips_seen) {
            flips_seen = view_flips;
            play_sub = PS_IDLE;
            scx_shadow = 0;
            slide_dir = 0;
            shown_x = px; shown_y = py; shown_f = pf;
        }
    }
    if (bob_t) { bob_t--; scy_shadow = SCY_BASE + (bob_t > 1 ? bob_t - 1 : 0); }
    else scy_shadow = SCY_BASE;
    if (play_sub == PS_IDLE && state == ST_PLAY) {
        if (pressed & J_START) { menu_enter(); return; }
        if (pressed & J_SELECT) { map_enter(0); return; }
        if (pressed & J_A) act_front();
        else if (move_cd) move_cd--;
        else if (move(k)) move_cd = 12;
    }
    if (!composed) monsters_update();                // AI never on the compose frame
    if (hud_flag) hud_render();
    hud_heart();
    log_update();
}

// ---------------------------------------------------------------- sprites (GDD 2.3, 7.3)
#define OAM_FX     0            // slash / claw / side arrow
#define OAM_ITEM   4
#define OAM_MON    6

static void spr_hide(uint8_t first, uint8_t n) {
    uint8_t *o = &shadow_OAM[first].y;
    while (n--) { *o = 0; o += 4; }
}

// cols x rows sprites (8x16) from consecutive tile pairs, written through one pointer (indexing
// shadow_OAM[oam].field per write cost ~600 T per sprite)
static void draw_block(uint8_t oam, uint8_t base, uint8_t cols, uint8_t rows, uint8_t x, uint8_t y, uint8_t prop) {
    uint8_t *o = &shadow_OAM[oam].y, c, sx;
    y += 16;
    x += 8;
    while (rows--) {
        for (c = cols, sx = x; c; c--, sx += 8, base += 2) {
            *o++ = y;
            *o++ = sx;
            *o++ = base;
            *o++ = prop;
        }
        y += 16;
    }
}

void play_sprites(void) {
    uint8_t d, m = 0xFF, it = 0xFF, cx = shown_x, cy = shown_y, prop = 0, wind = 0;
    int8_t sx = -(int8_t)scx_shadow - shake_x;
    if (composed) { composed = 0; return; }        // compose frame: keep last frame's OAM
    spr_hide(0, 18);
    if (state != ST_PLAY || play_sub == PS_DYING || slide_dir) return;
    for (d = 1; d <= 3; d++) {                          // nearest monster / item in the center column
        cx += view_dx[shown_f];
        cy += view_dy[shown_f];
        if (m == 0xFF) {
            m = mon_at(cx, cy);
            if (m == 0xFF) m = mon_dying_at(cx, cy);
            if (m != 0xFF) break;
        }
        if (it == 0xFF && d <= 2) {
            it = item_at(cx, cy);
            if (it != 0xFF) it |= d << 6;               // remember the depth
        }
        if (!walkable(cx, cy)) break;
    }
    if (it != 0xFF && (m == 0xFF || ((it >> 6) <= d))) {
        uint8_t i = it & 0x3F, t = item_type[i];
        if ((it >> 6) == 1) {
            if (t == IT_STAFF || t == IT_AMULET)
                draw_block(OAM_ITEM, t == IT_STAFF ? SPR_STAFF : SPR_AMULET, 2, 1, 72 + sx, 64, 0);
            else draw_block(OAM_ITEM, t == IT_KEY ? SPR_KEY : SPR_POTION, 1, 1, 76 + sx, 64, 0);
        } else {
            draw_block(OAM_ITEM, SPR_SACK, 1, 1, 76 + sx, 62, 0);
        }
    }
    if (m != 0xFF && (mon_state[m] & MS_DYING) && (frame & 1)) m = 0xFF;   // blink while dying
    if (m != 0xFF) {
        wind = (mon_state[m] & MS_WINDUP) ? 2 : 0;
        if (mon_flash[m]) { prop = S_PALETTE; obp1_shadow = 0x54; }
        else if (wind) { prop = S_PALETTE; obp1_shadow = 0xF8; }
        if (d == 1) draw_block(OAM_MON, mon_sprite_base(mon_type[m], 1), 4, 3, 64 + sx, 30 + wind, prop);
        else if (d == 2) draw_block(OAM_MON, mon_sprite_base(mon_type[m], 2), 2, 2, 72 + sx, 38 + wind, prop);
        else {
            draw_block(OAM_MON, SPR_EYE, 1, 1, 72 + sx, 44, prop);
            draw_block(OAM_MON + 1, SPR_EYE, 1, 1, 80 + sx, 44, prop | S_FLIPX);
        }
    }
    if (slash_t) draw_block(OAM_FX, SPR_SLASH, 2, 1, 72, 40, 0);
    else if (claw_t) draw_block(OAM_FX, SPR_CLAW, 2, 1, 72, 48, 0);
    else {                                              // side / back attack warning arrow
        for (m = 0; m < mon_count; m++) {
            uint8_t s, dx;
            if (!(mon_state[m] & MS_WINDUP)) continue;
            for (s = 0; s < 4; s++)
                if ((uint8_t)(px + view_dx[s]) == mon_x[m] && (uint8_t)(py + view_dy[s]) == mon_y[m]) break;
            s = (s - pf) & 3;
            if (s == 0 || (frame & 8)) continue;
            dx = s == 1 ? 148 : s == 3 ? 4 : 76;
            draw_block(OAM_FX, s == 2 ? SPR_ARROW_UP : SPR_ARROW_RIGHT, 1, 1, dx, s == 2 ? 80 : 44,
                       s == 3 ? S_FLIPX : s == 2 ? S_FLIPY : 0);
            break;
        }
    }
}
