// TORRE HUNDIDA - TITLE, GAMEOVER, CLEAR, loading a floor, saving (design/ui.md 3, 8-10, GDD 9.5).
// Full-screen changes go through gbe_screen (fade, LCD-off build, fade in); death fades to black.
#pragma bank 1
#include <string.h>
#include "game.h"
#include "floor1.h"
#include "screen_title.h"
#include "screen_gameover.h"
#include "screen_clear.h"

#define COL(at)  ((at) & 31)
#define ROW(at)  ((at) >> 5)
#define BG(at)   ((uint8_t *)0x9800 + (at))
#define SAVE_VERSION 1

uint8_t load_req, screen_t, save_status;

// ---------------------------------------------------------------- save (GDD 9.5)
typedef struct {
    uint8_t px, py, pf, hp, hp_max, keys, potions, weapon, staff, amulet, kills, items_got;
    uint16_t secs, rng;
    uint8_t dmap[256], seen[32];
    uint8_t item_type[ITEM_MAX], item_x[ITEM_MAX], item_y[ITEM_MAX], item_count;
    uint8_t mon_hp[MON_MAX], mon_x[MON_MAX], mon_y[MON_MAX], mon_state[MON_MAX], mon_item[MON_MAX];
} save_t;
static save_t sv;

void game_save(void) BANKED {
    sv.px = px; sv.py = py; sv.pf = pf; sv.hp = hp; sv.hp_max = hp_max; sv.keys = key_count;
    sv.potions = potions; sv.weapon = weapon; sv.staff = staff_owned; sv.amulet = amulet;
    sv.kills = kills; sv.items_got = items_got; sv.secs = play_secs; sv.rng = rng_state;
    memcpy(sv.dmap, dmap, 256);
    memcpy(sv.seen, seen, 32);
    memcpy(sv.item_type, item_type, ITEM_MAX); memcpy(sv.item_x, item_x, ITEM_MAX);
    memcpy(sv.item_y, item_y, ITEM_MAX); sv.item_count = item_count;
    memcpy(sv.mon_hp, mon_hp, MON_MAX); memcpy(sv.mon_x, mon_x, MON_MAX); memcpy(sv.mon_y, mon_y, MON_MAX);
    memcpy(sv.mon_item, mon_item, MON_MAX);
    memset(sv.mon_state, 0, MON_MAX);                    // no alert / wind-up across a load
    save_store(&sv, sizeof(sv), SAVE_VERSION);
    save_status = 1;
    say("Partida guardada");
    sfx(SFX_SAVE);
    skip_measure = 1;
}

uint8_t save_exists(void) BANKED {
    return save_load(&sv, sizeof(sv), SAVE_VERSION);
}

static void apply_save(void) {
    px = sv.px; py = sv.py; pf = sv.pf; hp = sv.hp; hp_max = sv.hp_max; key_count = sv.keys;
    potions = sv.potions; weapon = sv.weapon; staff_owned = sv.staff; amulet = sv.amulet;
    kills = sv.kills; items_got = sv.items_got; play_secs = sv.secs; rng_state = sv.rng;
    memcpy(dmap, sv.dmap, 256);
    memcpy(seen, sv.seen, 32);
    memcpy(item_type, sv.item_type, ITEM_MAX); memcpy(item_x, sv.item_x, ITEM_MAX);
    memcpy(item_y, sv.item_y, ITEM_MAX); item_count = sv.item_count;
    memcpy(mon_hp, sv.mon_hp, MON_MAX); memcpy(mon_x, sv.mon_x, MON_MAX); memcpy(mon_y, sv.mon_y, MON_MAX);
    memcpy(mon_item, sv.mon_item, MON_MAX);
    memcpy(mon_state, sv.mon_state, MON_MAX);
    maps_rebuild();
}

// ---------------------------------------------------------------- floor (LCD off)
// Margins of the view rows (columns 20-31) = the background row, for the turn slide (GDD 2.1);
// view_buf holds only the BG piece here (2 alternating tiles per row)
static void fill_margins(void) {
    uint8_t r, c, *a;
    for (r = 0; r < VIEW_H; r++) {
        a = (uint8_t *)0x9800u + ((uint16_t)(VIEW_ROW + r) << 5);
        for (c = 20; c < 32; c++) a[c] = a[c + 0x400] = view_buf[r * VIEW_W + (c & 1)];
    }
}

static void build_play(void) {
    uint8_t loaded = 0;
    bank_set_bkg_data(BANK(walls), VRAM_WALLS, WALLS_COUNT, walls_tiles);   // over the screens' art
    play_start();                                        // floor 1 from its bank
    if (load_req) loaded = save_exists();
    if (loaded) apply_save();
    load_req = 0;
    memset((uint8_t *)0x9C00, txt_blank, 6 * 32);        // HUD rows of the window
    log_init(WIN_ROW(2) + 1, 18);
    view_compose_bg();
    fill_margins();
    view_compose(px, py, pf);
    view_mark_seen(seen);
    bg_front = 0;
    LCDC_REG &= ~LCDCF_BG9C00;
    bgbuf_fill_both(view_buf, VIEW_H, VIEW_ROW);
    shown_x = px; shown_y = py; shown_f = pf;
    hud_dirty();
    say(loaded ? "Partida cargada" : "Piso 1");
    scy_shadow = SCY_BASE;
    scx_shadow = 0;
    WY_REG = HUD_WY;
    WX_REG = 7;
    SHOW_BKG; SHOW_WIN; SHOW_SPRITES;
    state = ST_PLAY;
    DISPLAY_ON;
}

static void build_full(uint8_t bank, const uint8_t *map) {
    uint8_t r;
    lcd_off_redraw_begin();
    scy_shadow = 0;
    bg_front = 0;
    LCDC_REG &= ~LCDCF_BG9C00;
    bank_set_bkg_data(BANK(uiscreens), VRAM_UISCREENS, UISCREENS_COUNT, uiscreens_tiles);   // walls' slot
    for (r = 0; r < 18; r++) bank_memcpy(bank, (uint8_t *)0x9800 + ((uint16_t)r << 5), map + r * 20, 20);
    hide_sprites_range(0, 40);
    screen_t = 0;
}

// ---------------------------------------------------------------- TITLE (ui.md 3)
static void build_title(void) {
    uint8_t has = save_exists();
    build_full(BANK(screen_title), screen_title_map);
    if (!has) memset(BG(SCREEN_TITLE_AT_CONTINUAR), txt_blank, SCREEN_TITLE_LEN_CONTINUAR);
    *BG(SCREEN_TITLE_AT_CONTINUAR - 1) = txt_blank;      // the mockup's cursor
    SHOW_BKG;
    state = ST_TITLE;
    DISPLAY_ON;
    menu_open(2, has ? 1 : 0, has ? 0 : 2, BG(SCREEN_TITLE_AT_NUEVA_PARTIDA - 1),
              SCREEN_TITLE_AT_CONTINUAR - SCREEN_TITLE_AT_NUEVA_PARTIDA, VRAM_UI + UI_CURSOR, txt_blank);
}

void title_update(void) BANKED {
    uint8_t r = menu_update();
    if (r == MENU_NONE && (pressed & J_START)) r = menu_sel;
    if (r > 1) return;
    rng_state ^= ((uint16_t)DIV_REG << 8) | frame;      // seed (GDD 2.0)
    if (!rng_state) rng_state = 0xACE1;
    sfx(SFX_MENU_OK);
    load_req = r == 1;
    transition(ST_PLAY);
}

// ---------------------------------------------------------------- GAMEOVER (ui.md 8)
static void build_gameover(void) {
    build_full(BANK(screen_gameover), screen_gameover_map);
    *BG(SCREEN_GAMEOVER_AT_CONTINUAR - 1) = txt_blank;
    SHOW_BKG;
    state = ST_GAMEOVER;
    set_fade_dark(3);                                    // fade in from black (16 f)
    DISPLAY_ON;
    menu_open(2, 0, 0, BG(SCREEN_GAMEOVER_AT_CONTINUAR - 1),
              SCREEN_GAMEOVER_AT_TITULO - SCREEN_GAMEOVER_AT_CONTINUAR, VRAM_UI + UI_CURSOR, txt_blank);
}

// PV 0: fade to black over 32 f, then the game-over screen fades in from black
void dying_update(void) BANKED {
    uint8_t t = ++screen_t;
    if ((t & 7) == 0 && t < 32) set_fade_dark(t >> 3);
    if (t == 32) { BGP_REG = OBP0_REG = 0xFF; bgp_shadow = obp0_shadow = 0xFF; }
    if (t == 40) build_gameover();
}

void gameover_update(void) BANKED {
    uint8_t t = ++screen_t, r;
    if (t <= 16) { set_fade_dark(3 - ((t - 1) >> 2)); if (t == 16) set_fade(0); return; }
    r = menu_update();
    if (r == MENU_NONE && (pressed & J_START)) r = menu_sel;
    if (r > 1) return;
    sfx(SFX_MENU_OK);
    load_req = r == 0;                                   // CONTINUAR: last save (or a new floor)
    transition(r == 0 ? ST_PLAY : ST_TITLE);
}

// ---------------------------------------------------------------- CLEAR (ui.md 9)
static void frac(uint16_t at, uint8_t len, uint8_t a, uint8_t b) {   // at: row * 32 + col > 255   // "a/b" right-aligned
    uint8_t t[5], *d = BG(at + len - 5);
    txt_u16(t, a, 2, 0); t[2] = txt_char('/'); txt_u16(t + 3, b, 2, 0);
    if (t[3] == txt_blank) { t[3] = t[4]; t[4] = txt_blank; memmove(t + 1, t, 4); t[0] = txt_blank; }
    memcpy(d, t, 5);
}

static void build_clear(void) {
    uint8_t m = play_secs / 60, s = play_secs % 60, t[5];
    build_full(BANK(screen_clear), screen_clear_map);
    txt_u16(t, m > 99 ? 99 : m, 2, 1); t[2] = txt_char(':'); txt_u16(t + 3, s, 2, 1);
    memcpy(BG(SCREEN_CLEAR_AT_04_12), t, 5);
    frac(SCREEN_CLEAR_AT_6_8, SCREEN_CLEAR_LEN_6_8, kills, mon_total);
    frac(SCREEN_CLEAR_AT_5_6, SCREEN_CLEAR_LEN_5_6, items_got, items_total);
    SHOW_BKG;
    state = ST_CLEAR;
    DISPLAY_ON;
}

void clear_update(void) BANKED {
    uint8_t t = ++screen_t;
    if ((t % 60) == 0) vq_push_fill(BG(SCREEN_CLEAR_AT_PULSA_START), txt_blank, SCREEN_CLEAR_LEN_PULSA_START);
    else if ((t % 60) == 30) {
        uint8_t b[16];
        txt_tiles(b, "Pulsa Start", SCREEN_CLEAR_LEN_PULSA_START);
        vq_push(BG(SCREEN_CLEAR_AT_PULSA_START), b, SCREEN_CLEAR_LEN_PULSA_START);
    }
    if (t > 30 && (pressed & (J_START | J_A))) { sfx(SFX_MENU_OK); transition(ST_TITLE); }
}

// gbe_screen: build the next screen with the LCD off (called through screen_build in main.c)
void screen_build_b(uint8_t which) BANKED {
    if (which == ST_PLAY) { lcd_off_redraw_begin(); build_play(); }
    else if (which == ST_TITLE) build_title();
    else if (which == ST_CLEAR) build_clear();
    else build_gameover();
}
