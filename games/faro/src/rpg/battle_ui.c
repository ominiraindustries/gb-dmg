// FARO kit - the battle screen (ui.md 6, GDD 3.1): plays the events of battle_core as messages
// (msgs.tbl + names from the tables), PV bars that slide 1 px every 2 frames, the command grid and
// the sub-lists (gbe_list). Everything in the BG ($9800), the window off. Bank: auto.
#pragma bank 255
#include "rpg.h"
#include "ui.h"
#include "uimenu.h"
#include "tbl_msgs.h"
#include "font.h"
#include "screen_combate.h"
#include "screen_combate_atacar.h"

#define BG(at) ((uint8_t *)0x9800 + (at))
enum { BU_MSG, BU_MENU, BU_LIST, BU_WEAPON_FOR_SKILL, BU_END };
enum { CMD_ATACAR, CMD_TECNICA, CMD_OBJETO, CMD_ARTILUGIO, CMD_HUIR, CMD_CAPTURAR };
static const uint16_t cmd_at[6] = { SCREEN_COMBATE_AT_ATACAR, SCREEN_COMBATE_AT_TECNICA, SCREEN_COMBATE_AT_OBJETO,
                                    SCREEN_COMBATE_AT_ARTILUGIO, SCREEN_COMBATE_AT_HUIR, SCREEN_COMBATE_AT_CAPTURAR };
static const uint8_t cmd_len[6] = { SCREEN_COMBATE_LEN_ATACAR, SCREEN_COMBATE_LEN_TECNICA, SCREEN_COMBATE_LEN_OBJETO,
                                    SCREEN_COMBATE_LEN_ARTILUGIO, SCREEN_COMBATE_LEN_HUIR, SCREEN_COMBATE_LEN_CAPTURAR };

uint8_t bu_state, bu_cmd, bu_ev, bu_list_kind, bu_skill, bu_post, bu_cpv_shown, bu_pv_shown, bu_t;
uint8_t bu_ids[24], bu_n, bu_shake;
uint8_t battle_pending_sp, battle_pending_lv, battle_pending_free;
uint8_t battle_back_map, battle_back_x, battle_back_y, battle_back_dir;
static uint16_t bark_c, bark_p;                  // 16384 / pv_max, computed once per battle
#define tmp (tbox_text + 128)                    // expanded message (the wrapped copy goes to tbox_text)

extern uint8_t warp_map, warp_x, warp_y, warp_dir, warp_pending;

// ---------------------------------------------------------------- text
static void row_name(uint8_t kind, uint8_t id, char *dst) {
    if (kind == 0) { items_t r; item_row(id, &r); memcpy(dst, r.name, 15); }
    else if (kind == 1) { skills_t r; bank_memcpy(BANK(tbl_skills), &r, &tbl_skills[id], sizeof(r)); memcpy(dst, r.name, 15); }
    else if (kind == 2) { moves_t r; bank_memcpy(BANK(tbl_moves), &r, &tbl_moves[id], sizeof(r)); memcpy(dst, r.name, 13); }
    else { statuses_t r; bank_memcpy(BANK(tbl_statuses), &r, &tbl_statuses[id], sizeof(r)); memcpy(dst, kind == 3 ? r.msg : r.fin, 13); }
}

// message template + {S} {O} {N} -> tbox_text, wrapped to 18-char lines, 2 lines per page
static void say(uint8_t msg, const char *s, const char *o, uint16_t n) {
    msgs_t m;
    char num[6], *d = tmp, *w, *line, *src;
    uint8_t col, lines, k, len;
    bank_memcpy(BANK(tbl_msgs), &m, &tbl_msgs[msg], sizeof(m));
    for (src = m.t; *src && d < tmp + 112; src++) {
        if (*src == '{' && src[2] == '}') {
            if (src[1] == 'S') for (w = (char *)s; *w; ) *d++ = *w++;
            else if (src[1] == 'O') for (w = (char *)o; *w; ) *d++ = *w++;
            else {
                k = 0;
                do { num[k++] = '0' + n % 10; n /= 10; } while (n);
                while (k) *d++ = num[--k];
            }
            src += 2;
        } else *d++ = *src;
    }
    *d = 0;
    // greedy wrap at spaces
    d = tbox_text; col = 0; lines = 0; line = tmp;
    for (src = tmp; ; ) {
        for (w = src; *w && *w != ' '; w++) ;
        len = (uint8_t)(w - src);
        if (col && col + 1 + len > 18) {
            *d++ = (++lines & 1) ? 0x0A : 0x0C;
            col = 0;
        } else if (col) { *d++ = ' '; col++; }
        memcpy(d, src, len); d += len; col += len;
        if (!*w) break;
        src = w + 1;
    }
    *d = 0;
    (void)line;
    tbox_start(TB_SAY);
}

static const char *cname(void) {
    static char n[11];
    memcpy(n, b_sp.name, 11);
    return n;
}

// ---------------------------------------------------------------- the two blocks
static void put_num_right(uint16_t end_at, uint16_t v, uint8_t width) {
    uint8_t t[5];
    txt_u16(t, v, width, 0);
    vq_push(BG(end_at - width + 1), t, width);
}

static void bar(uint16_t at, uint8_t pxv) {       // BAR_L + 8 tiles + BAR_R
    uint8_t t[10], k, f;
    t[0] = VRAM_UIMENU + UIMENU_BAR_L;
    for (k = 0; k < 8; k++) {
        f = pxv > (k << 3) ? pxv - (k << 3) : 0;
        t[k + 1] = VRAM_UIMENU + UIMENU_BAR_0 + (f > 8 ? 8 : f);
    }
    t[9] = VRAM_UIMENU + UIMENU_BAR_R;
    vq_push(BG(at), t, 10);
}

static void status_abbr(uint16_t at, uint8_t st) {
    uint8_t t[3];
    if (st == 0xFF) { vq_push_fill(BG(at), txt_blank, 3); return; }
    { statuses_t r; bank_memcpy(BANK(tbl_statuses), &r, &tbl_statuses[st], sizeof(r)); txt_tiles(t, r.abbr, 3); }
    vq_push(BG(at), t, 3);
}

static void draw_creature_block(void) {
    uint8_t t[10];
    txt_tiles(t, b_sp.name, 10);
    vq_push(BG(SCREEN_COMBATE_AT_PINZARRO), t, 10);
    t[0] = txt_char('N'); t[1] = txt_char('v');
    txt_u16(t + 2, b_level, 2, 0);
    if (t[2] == txt_blank) { t[2] = t[3]; t[3] = txt_blank; }
    vq_push(BG(SCREEN_COMBATE_AT_NV3), t, 4);
    status_abbr(SCREEN_COMBATE_AT_DOR, b_cst);
    t[0] = b_ent_t ? VRAM_UIMENU + UIMENU_ST_NET : (b_fly && !b_down) ? VRAM_UIMENU + UIMENU_ST_FLY : txt_blank;
    t[1] = b_calm_t ? VRAM_UIMENU + UIMENU_ST_CALM : txt_blank;
    t[2] = b_lit_t ? VRAM_UIMENU + UIMENU_ST_LIT : txt_blank;
    vq_push(BG(2 * 32 + 10), t, 3);
}

// "a/b" right-aligned in 7 tiles (blanks on the left): digits written right to left
static void frac_tiles(uint8_t *t, uint8_t a, uint8_t b) {
    uint8_t i = 7;
    do { t[--i] = txt_font + FONT_DIGIT0 + b % 10; b /= 10; } while (b);
    t[--i] = txt_char('/');
    do { t[--i] = txt_font + FONT_DIGIT0 + a % 10; a /= 10; } while (a);
    while (i) t[--i] = txt_blank;
}

static void draw_leo_block(void) {
    uint8_t t[8];
    t[0] = txt_char('N'); t[1] = txt_char('v');
    txt_u16(t + 2, plevel, 2, 0);
    if (t[2] == txt_blank) { t[2] = t[3]; t[3] = txt_blank; }
    vq_push(BG(SCREEN_COMBATE_AT_NV5 + SCREEN_COMBATE_LEN_NV5 - 4), t, 4);
    status_abbr(SCREEN_COMBATE_AT_VEN, p_st);
    frac_tiles(t, bu_pv_shown, pv_max);
    vq_push(BG(SCREEN_COMBATE_AT_32_38 + 4 - 6), t, 7);        // "pv/max" right-aligned, ends at col 18
    txt_u16(t, en, 2, 0); t[2] = txt_char('/'); txt_u16(t + 3, en_max, 2, 0);
    vq_push(BG(SCREEN_COMBATE_AT_9_13 + 3 - 4), t, 5);
    t[0] = VRAM_UIMENU + (sac >= 60 ? UIMENU_BOWL_FULL : sac >= 25 ? UIMENU_BOWL_MID : sac ? UIMENU_BOWL_LOW : UIMENU_BOWL_EMPTY);
    vq_push(BG(10 * 32 + 18), t, 1);
}

static uint8_t bar_px(uint8_t v, uint16_t bark) { return (uint8_t)(((uint16_t)v * bark) >> 8); }

static void bars_now(void) {
    bar(3 * 32 + 3, bar_px(bu_cpv_shown, bark_c));
    bar(8 * 32 + 9, bar_px(bu_pv_shown, bark_p));
}

// slide the shown PV towards the real one: 1 every 2 frames (ui.md 6.1)
static void bars_update(void) {
    if (++bu_t & 1) return;
    if (bu_cpv_shown != b_cpv) { bu_cpv_shown += bu_cpv_shown < b_cpv ? 1 : -1; bar(3 * 32 + 3, bar_px(bu_cpv_shown, bark_c)); }
    if (bu_pv_shown != pv) { bu_pv_shown += bu_pv_shown < pv ? 1 : -1; bar(8 * 32 + 9, bar_px(bu_pv_shown, bark_p)); draw_leo_block(); }
}

// ---------------------------------------------------------------- build (LCD off)
void battle_build(void) BANKED {
    uint8_t r, c;
    battle_gfx(b_sp.pic);                        // glue: creature picture at BG 128, Leo's back after it
    bank_set_bkg_data(BANK(uimenu), VRAM_UIMENU, UIMENU_COUNT, uimenu_tiles);
    for (r = 0; r < 18; r++)
        bank_memcpy(BANK(screen_combate), BG((uint16_t)r << 5), screen_combate_map + r * 20, 20);
    for (r = 0; r < 7; r++) for (c = 0; c < 7; c++) *BG((r << 5) + 13 + c) = 128 + r * 7 + c;
    for (r = 0; r < 6; r++) for (c = 0; c < 5; c++) *BG(((7 + r) << 5) + 1 + c) = 128 + 49 + r * 5 + c;
    hide_sprites_range(0, 40);
    scx_shadow = scy_shadow = 0;
    bark_c = 16384u / b_cpv_max;
    bark_p = 16384u / pv_max;
    bu_cpv_shown = b_cpv;
    bu_pv_shown = pv;
    tbox_win = (uint8_t *)0x9800;                // messages in the BG box (rows 12-17)
    tbox_row = 12;
    tbox_speaker[0] = 0;
    tbox_visible = 0;
    tbox_auto = 40;
    state = ST_BATTLE;
    SHOW_BKG; HIDE_WIN;
}

void battle_request(uint8_t sp, uint8_t lv, uint8_t free) BANKED {
    battle_pending_sp = sp; battle_pending_lv = lv; battle_pending_free = free;
    battle_back_map = wmap_id; battle_back_x = px; battle_back_y = py; battle_back_dir = pdir;
    sac = sac > (uint8_t)RULE(RULE_SAC_BATTLE) ? sac - (uint8_t)RULE(RULE_SAC_BATTLE) : 0;
    transition(ST_BATTLE);
}

// called from screen_build(ST_BATTLE)
void battle_enter(void) BANKED {
    battle_begin(battle_pending_sp, battle_pending_lv, battle_pending_free);
    battle_build();
    draw_creature_block();
    draw_leo_block();
    bars_now();
    say(battle_pending_free == 2 ? MSG_INTRO_AMBUSH : battle_pending_free == 1 ? MSG_INTRO_ADV : MSG_INTRO, cname(), "", 0);
    battle_open_turn();                          // an ambush: the creature acts before the first choice
    bu_ev = 0;
    bu_post = 0;
    bu_state = BU_MSG;
}

// ---------------------------------------------------------------- events -> messages
static uint8_t play_event(void) {                // 1 = a message was started
    uint8_t *e = b_ev[bu_ev++];
    char o[16];
    const char *who = e[1] ? cname() : "Leo";
    switch (e[0]) {
    case EV_USE:
        if (e[2] == B_USE_MOVE) { row_name(2, e[3], o); say(MSG_USE_MOVE, cname(), o, 0); }
        else if (e[2] == B_USE_SKILL) { row_name(1, e[3], o); say(MSG_USE_SKILL, "Leo", o, 0); }
        else { row_name(0, e[3], o); say(e[2] == B_USE_WEAPON ? MSG_USE_WEAPON : e[2] == B_USE_ITEM ? MSG_USE_ITEM : MSG_USE_GADGET, "Leo", o, 0); }
        return 1;
    case EV_MISS: say(e[1] ? MSG_MISS_C : MSG_MISS_P, who, "", 0); return 1;
    case EV_HIT:
        if (e[3] & 8) { say(MSG_IMMUNE, who, "", 0); return 1; }
        if (e[1]) shake_x = 2; else shake_y = 2;
        bu_shake = 8;
        say(e[3] & 1 ? MSG_CRIT : (e[3] & 2) ? MSG_WEAK : (e[3] & 4) ? MSG_RESIST : (e[1] ? MSG_HIT_C : MSG_HIT_P), who, "", e[2]);
        return 1;
    case EV_STATUS: row_name(3, e[2], o); say(MSG_STATUS, who, o, 0); draw_creature_block(); draw_leo_block(); return 1;
    case EV_STATUS_END: row_name(4, e[2], o); if (!o[0]) return 0; say(MSG_STATUS_END, who, o, 0); draw_creature_block(); draw_leo_block(); return 1;
    case EV_SKIP: say(MSG_SKIP, who, "", 0); return 1;
    case EV_DOT: say(MSG_DOT, who, "", e[2]); return 1;
    case EV_HEAL: say(MSG_HEAL, who, "", e[2]); return 1;
    case EV_EN: say(MSG_EN, "Leo", "", e[2]); draw_leo_block(); return 1;
    case EV_REVEAL: say(MSG_REVEAL, cname(), "", b_cpv); return 1;
    case EV_AIM: say(MSG_AIM, "Leo", "", 0); return 1;
    case EV_DEBUFF: say(e[1] ? MSG_DEBUFF_C : MSG_DEBUFF_P, who, "", 0); return 1;
    case EV_DEFUP: say(MSG_DEFUP, cname(), "", 0); return 1;
    case EV_BUFF: say(MSG_BUFF, "Leo", "", 0); return 1;
    case EV_BAIT: say(e[2] ? MSG_BAIT_OK : MSG_BAIT_NO, cname(), "", 0); draw_creature_block(); return 1;
    case EV_THROW: row_name(0, e[2], o); say(MSG_THROW, "Leo", o, 0); return 1;
    case EV_SHAKES: say(e[3] ? MSG_CAPTURED : MSG_FAILED, cname(), "", 0); return 1;
    case EV_NOCOND: say(MSG_NOCOND, cname(), "", 0); return 1;
    case EV_FLEE:
        if (e[1]) say(e[2] ? MSG_C_FLEE : MSG_C_FLEE_NO, cname(), "", 0);
        else say(e[2] ? MSG_FLEE_OK : MSG_FLEE_NO, "Leo", "", 0);
        return 1;
    case EV_STEAL: row_name(0, e[2], o); say(MSG_STEAL, cname(), o, 0); return 1;
    case EV_WATCH: say(MSG_WATCH, cname(), "", 0); return 1;
    case EV_END:
        if (e[1] == B_HUNTED) { say(MSG_HUNTED, cname(), "", 0); return 1; }
        if (e[1] == B_FAINTED) { say(MSG_FAINTED, "Leo", "", 0); return 1; }
        return 0;
    }
    return 0;
}

// after the battle: new light, XP, loot (into the bag), level ups - one message each
static uint8_t play_post(void) {
    char o[16];
    switch (bu_post++) {
    case 0: if (b_result == B_CAPTURED && b_new_species) { say(MSG_NEW_LIGHT, cname(), "", 0); return 1; } return 0;
    case 1: if (b_xp) { say(MSG_XP, "", "", b_xp); return 1; } return 0;
    case 2: case 3: case 4:
        if (bu_post - 3 < b_loot_n) {
            uint8_t k = bu_post - 3;
            inv_add(b_loot_item[k], b_loot_cnt[k]);
            row_name(0, b_loot_item[k], o);
            say(MSG_LOOT, "", o, b_loot_cnt[k]);
            return 1;
        }
        return 0;
    case 5: if (b_levelups) { say(MSG_LEVEL, "", "", plevel); draw_leo_block(); return 1; } return 0;
    }
    bu_post = 0xFF;
    return 0;
}

// ---------------------------------------------------------------- menu and lists
static void menu_draw(void) {
    uint8_t r, buf[20];
    for (r = 12; r < 18; r++) {                   // the command box of the mockup
        bank_memcpy(BANK(screen_combate), buf, screen_combate_map + r * 20, 20);
        vq_push(BG((uint16_t)r << 5), buf, 20);
    }
    for (r = 0; r < 6; r++) vq_push(BG(cmd_at[r] - 1), r == bu_cmd ? &tbox_cursor : &txt_blank, 1);
}

static void open_menu(void) {
    tbox_close();
    menu_draw();
    bu_state = BU_MENU;
}

static void list_row_cb(uint8_t i, uint8_t *buf) {
    char n[16];
    uint8_t id = bu_ids[i];
    memset(buf, txt_blank, 18);
    if (bu_list_kind == CMD_TECNICA) {
        skills_t s;
        bank_memcpy(BANK(tbl_skills), &s, &tbl_skills[id], sizeof(s));
        txt_tiles(buf + 1, s.name, 14);
        txt_u16(buf + 16, s.en, 2, 0);
        return;
    }
    row_name(0, id, n);
    txt_tiles(buf + 1, n, 14);
    if (bu_list_kind != CMD_ATACAR && bu_list_kind != 0xFE && inv[id]) txt_u16(buf + 16, inv[id], 2, 0);
}

static void open_list(uint8_t kind) {
    uint8_t i, r;
    items_t it;
    bu_n = 0;
    bu_list_kind = kind;
    if (kind == CMD_ATACAR || kind == 0xFE) {
        for (i = 0; i < 3; i++) if (weapons[i] != 0xFF) bu_ids[bu_n++] = weapons[i];
    } else if (kind == CMD_TECNICA) {
        for (i = 0; i < 16; i++) if (skills_known & (1u << i)) bu_ids[bu_n++] = i;
    } else {
        for (i = 0; i < ITEM_COUNT && bu_n < sizeof(bu_ids); i++) {
            if (!inv[i]) continue;
            item_row(i, &it);
            if (!(it.uso & ITEMS_USO_COMBATE)) continue;
            if (kind == CMD_CAPTURAR ? it.efecto == ITEMS_EFECTO_CAPTURA
                : kind == CMD_ARTILUGIO ? (it.bolsa == ITEMS_BOLSA_ARTILUGIOS || (it.cat == ITEMS_CAT_LLAVE && it.efecto >= ITEMS_EFECTO_RED && it.efecto <= ITEMS_EFECTO_DERRIBAR))
                : (it.efecto == ITEMS_EFECTO_CONSUMIR)) bu_ids[bu_n++] = i;
        }
    }
    skip_measure = 1;                            // scanning the item table takes a couple of frames
    if (!bu_n) {
        say(kind == CMD_CAPTURAR ? MSG_NO_LANTERN : MSG_NOTHING, "", "", 0);
        bu_state = BU_MSG;
        bu_ev = b_ev_n;                          // no events: back to the menu after the message
        return;
    }
    for (r = 12; r < 18; r++) {                   // the list box of the "Atacar" mockup, tab = command name
        uint8_t buf[20];                          // (rows 14-16: list_open draws them; the queue is 250 B)
        if (r >= 14 && r <= 16) continue;
        bank_memcpy(BANK(screen_combate_atacar), buf, screen_combate_atacar_map + r * 20, 20);
        vq_push(BG((uint16_t)r << 5), buf, 20);
    }
    {
        uint8_t buf[10];
        uint8_t k = kind == 0xFE ? CMD_ATACAR : kind;
        uint16_t at = cmd_at[k];
        bank_memcpy(BANK(screen_combate), buf, screen_combate_map + (at >> 5) * 20 + (at & 31), cmd_len[k]);
        vq_push_fill(BG(SCREEN_COMBATE_ATACAR_AT_ATACAR), VRAM_UI + UI_FRAME_T, 9);
        vq_push(BG(SCREEN_COMBATE_ATACAR_AT_ATACAR), buf, cmd_len[k]);
    }
    list_cursor = VRAM_UI + UI_CURSOR;
    list_blank = txt_blank;
    list_arrow_up = VRAM_UIMENU + UIMENU_ARROW_UP;
    list_arrow_down = VRAM_UI + UI_ARROW_DOWN;
    list_border = VRAM_UI + UI_FRAME_B;
    list_up_at = 0;
    list_down_at = BG(17 * 32 + 17);
    list_open(bu_n, 0, 3, BG(14 * 32 + 1), 32, 18, list_row_cb);
    bu_state = kind == 0xFE ? BU_WEAPON_FOR_SKILL : BU_LIST;
}

static void do_turn(uint8_t kind, uint8_t id, uint8_t weapon) {
    battle_turn(kind, id, weapon);
    draw_leo_block();
    draw_creature_block();
    bu_ev = 0;
    bu_post = 0;
    bu_state = BU_MSG;
    tbox_close();
    skip_measure = 1;
}

static void choose(uint8_t i) {
    uint8_t id = bu_ids[i];
    if (bu_list_kind == CMD_ATACAR) { do_turn(B_ACT_ATTACK, id, 0xFF); return; }
    if (bu_list_kind == 0xFE) { do_turn(B_ACT_SKILL, bu_skill, id); return; }
    if (bu_list_kind == CMD_TECNICA) {
        skills_t s;
        bank_memcpy(BANK(tbl_skills), &s, &tbl_skills[id], sizeof(s));
        if (s.en > en) { sfx(SFX_BUMP); return; }
        bu_skill = id;
        if (s.efecto == SKILLS_EFECTO_ATAQUE && s.dtype == 0xFF) { open_list(0xFE); return; }   // which weapon
        do_turn(B_ACT_SKILL, id, 0xFF);
        return;
    }
    do_turn(bu_list_kind == CMD_CAPTURAR ? B_ACT_CAPTURE : bu_list_kind == CMD_ARTILUGIO ? B_ACT_GADGET : B_ACT_ITEM, id, 0xFF);
}

// ---------------------------------------------------------------- exit
static void leave(void) {
    uint8_t r = b_result;
    creatures_after_battle(r);
    tbox_close();
    tbox_auto = 0;
    tbox_win = (uint8_t *)0x9C00;
    tbox_row = 0;
    if (r == B_FAINTED) {                        // GDD 2.9: wake at the last clinic, half the money
        money >>= (uint8_t)RULE(RULE_DEATH_MONEY_SH);
        ops_heal(0);
        warp_map = last_clinic_map; warp_x = last_clinic_x; warp_y = last_clinic_y; warp_dir = DIR_DOWN;
    } else {
        warp_map = battle_back_map; warp_x = battle_back_x; warp_y = battle_back_y; warp_dir = battle_back_dir;
    }
    field_set = 0xFF;                            // the battle overwrote the tileset slot
    warp_pending = 1;
    bu_state = BU_END;
    transition(ST_FIELD);
}

void battle_update(void) BANKED {
    uint8_t r;
    bars_update();
    if (bu_shake) {                               // +-2 px, flipping every 2 frames, 8 frames
        if (!(--bu_shake & 1)) { shake_x = -shake_x; shake_y = -shake_y; }
        if (!bu_shake) shake_x = shake_y = 0;
    }
    switch (bu_state) {
    case BU_MSG:
        if (tbox_state != TB_OPEN && tbox_state != TB_CLOSED) { tbox_update(); return; }
        if (bu_cpv_shown != b_cpv || bu_pv_shown != pv) return;      // let the bars finish
        if (bu_ev < b_ev_n) { if (!play_event()) battle_update(); return; }
        if (b_result == B_ONGOING) { open_menu(); return; }
        if (bu_post != 0xFF) { if (!play_post()) battle_update(); return; }
        leave();
        return;
    case BU_MENU:
        if (vq_pending()) return;                // the box is still being drawn (ui.md 6.4)
        r = bu_cmd;
        if (pressed & J_LEFT) r &= ~1;
        if (pressed & J_RIGHT) r |= 1;
        if ((pressed & J_UP) && r >= 2) r -= 2;
        if ((pressed & J_DOWN) && r < 4) r += 2;
        if (r != bu_cmd) {
            vq_push(BG(cmd_at[bu_cmd] - 1), &txt_blank, 1);
            bu_cmd = r;
            vq_push(BG(cmd_at[bu_cmd] - 1), &tbox_cursor, 1);
            sfx(SFX_BLIP);
        }
        if (pressed & J_A) {
            sfx(SFX_OK);
            if (bu_cmd == CMD_HUIR) do_turn(B_ACT_FLEE, 0, 0xFF);
            else open_list(bu_cmd);
        }
        return;
    case BU_LIST:
    case BU_WEAPON_FOR_SKILL:
        if (vq_pending()) return;
        r = list_update();
        if (r == MENU_BACK) { open_menu(); return; }
        if (r != MENU_NONE) choose(r);
        return;
    }
}
