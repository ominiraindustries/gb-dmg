// FARO kit - TITLE (ui.md 2): logo, the lighthouse beam sweeping, "Pulsa Start", then the menu
// Continuar / Nueva partida / Opciones. Bank 1.
#pragma bank 1
#include "rpg.h"
#include "title.h"
#include "uispr.h"
#include "ui.h"
#include "leo.h"
#include "screen_title.h"
#include "screen_title_menu.h"

#define SPR_BEAM   SPR_NPC          // uispr.tiles go where the NPC looks live (not used on the title)
#define BEAM_Y     (52 + 16)
uint8_t title_phase, title_t, title_choice;

static void beam(void) {
    uint8_t t = title_t, k, n;                   // 240-frame cycle (ui.md 2)
    OAM_item_t *o = &shadow_OAM[2];
    n = t < 120 ? 8 : t < 152 ? 8 - ((t - 120) >> 2) : t < 200 ? 0 : 1 + (t - 200) / 5;
    if (n > 8) n = 8;
    for (k = 0; k < 8; k++, o++) {
        o->y = k < n ? BEAM_Y : 0;
        o->x = 128 - 8 * k + 8;
        o->tile = SPR_BEAM + UISPR_BEAM_0 + 2 * k;
        o->prop = S_PRIORITY;                    // behind the logo, the text and the tower
    }
    if (t >= 152 && t < 168) {                   // flash
        o = &shadow_OAM[2];
        o[0].y = o[1].y = BEAM_Y;
        o[0].x = 128 + 8; o[1].x = 136 + 8;
        o[0].tile = SPR_BEAM + UISPR_BEAM_FLASH; o[1].tile = SPR_BEAM + UISPR_BEAM_FLASH;
        o[1].prop = S_PRIORITY | S_FLIPX;
        bgp_shadow = t < 160 ? 0x94 : 0xE4;
    }
    if (++title_t == 240) title_t = 0;
}

void title_build(void) BANKED {
    uint8_t r;
    bank_set_bkg_data(BANK(title), VRAM_TITLE, TITLE_COUNT, title_tiles);
    bank_set_sprite_data(BANK(uispr), SPR_BEAM, UISPR_COUNT, uispr_tiles);
    for (r = 0; r < 18; r++)
        bank_memcpy(BANK(screen_title), (uint8_t *)0x9800 + ((uint16_t)r << 5), screen_title_map + r * 20, 20);
    scx_shadow = scy_shadow = 0;
    hide_sprites_range(0, 40);
    oam16(0, 112 + 8, 95 + 16, SPR_LEO + LEO_SIDE_A, 0);
    title_phase = 0;
    title_t = 0;
    state = ST_TITLE;
    SHOW_BKG; SHOW_SPRITES; HIDE_WIN;
}

// state 2: copy rows 8-12 cols 2-17 of the menu mockup (80 tiles through the queue; the block
// covers "Pulsa Start"), without the mockup's cursor: gbe_menu draws the real one
static void show_menu(void) {
    uint8_t r, buf[16];
    for (r = 8; r <= 12; r++) {
        bank_memcpy(BANK(screen_title_menu), buf, screen_title_menu_map + r * 20 + 2, 16);
        for (title_choice = 0; title_choice < 16; title_choice++)
            if (buf[title_choice] == VRAM_UI + UI_CURSOR) buf[title_choice] = txt_blank;
        vq_push((uint8_t *)0x9800 + ((uint16_t)r << 5) + 2, buf, 16);
    }
    if (!save_exists())
        vq_push_fill((uint8_t *)0x9800 + SCREEN_TITLE_MENU_AT_CONTINUAR, txt_blank, SCREEN_TITLE_MENU_LEN_CONTINUAR);
    menu_open(3, save_exists() ? 0 : 1, save_exists() ? 0 : 1,
              (uint8_t *)0x9800 + SCREEN_TITLE_MENU_AT_CONTINUAR - 1,
              SCREEN_TITLE_MENU_AT_NUEVA_PARTIDA - SCREEN_TITLE_MENU_AT_CONTINUAR,
              VRAM_UI + UI_CURSOR, txt_blank);
}

// returns TITLE_NONE while on the title, else the choice (0 continue, 1 new game, 2 options)
uint8_t title_update(void) BANKED {
    uint8_t r;
    beam();
    if (title_phase == 0) {
        if (title_t % 60 == 0) {
            uint8_t b[16];
            bank_memcpy(BANK(screen_title), b, screen_title_map + SCREEN_TITLE_AT_PULSA_START - (SCREEN_TITLE_AT_PULSA_START >> 5) * 12, SCREEN_TITLE_LEN_PULSA_START);
            vq_push((uint8_t *)0x9800 + SCREEN_TITLE_AT_PULSA_START, b, SCREEN_TITLE_LEN_PULSA_START);
        } else if (title_t % 60 == 30)
            vq_push_fill((uint8_t *)0x9800 + SCREEN_TITLE_AT_PULSA_START, txt_blank, SCREEN_TITLE_LEN_PULSA_START);
        if (pressed & (J_START | J_A)) {
            rng_state ^= ((uint16_t)DIV_REG << 8) | title_t;          // GDD 2.0 seed
            if (!rng_state) rng_state = 0xACE1;
            sfx(SFX_OK);
            show_menu();
            title_phase = 1;
        }
        return TITLE_NONE;
    }
    r = menu_update();
    if (r == MENU_BACK) {                                      // back to "Pulsa Start": restore the rows
        uint8_t row, buf[16];
        for (row = 8; row <= 12; row++) {
            bank_memcpy(BANK(screen_title), buf, screen_title_map + row * 20 + 2, 16);
            vq_push((uint8_t *)0x9800 + ((uint16_t)row << 5) + 2, buf, 16);
        }
        title_phase = 0;
        return TITLE_NONE;
    }
    if (r == MENU_NONE) return TITLE_NONE;
    sfx(SFX_OK);
    title_choice = r;
    return r;
}
