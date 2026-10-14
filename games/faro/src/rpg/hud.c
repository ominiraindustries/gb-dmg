// FARO kit - the field HUD (GDD 4.4, ui.md 3): two 8x16 sprites, heart (PV) and bowl (saciedad), no
// BG tiles. Each icon has a band; a band change copies the 2 tiles of the new state into its VRAM
// slot through the tile queue and shows the icon HUD_SHOW frames even if the new band is 'fine'.
// Fine = hidden, half = shown, empty = blinking. With the Start panel open they are its labels.
// Slots: sprite tiles 252-255 (= BG 252-255 at $8800, kept free by the field tilesets). Bank 0
// (every field frame).
#include "rpg.h"
#include "uispr.h"

#define HUD_SHOW  180
static uint8_t last_pv = 0xFF, last_pvm, last_sac, last_panel;   // what the sprites show now
uint8_t hud_band[2], hud_show[2], hud_panel;    // [0] heart, [1] bowl; hud_panel: 1 panel labels, 2 hidden

void hud_reset(void) {
    hud_band[0] = hud_band[1] = 0xFF;           // reload both slots, without the 'changed' show
    hud_show[0] = hud_show[1] = 0;
    last_pv = 0xFF;
}

static void band(uint8_t k, uint8_t b, uint8_t first) {
    if (b == hud_band[k]) return;
    if (!tiles_push((uint8_t *)0x8000 + ((uint16_t)(HUD_TILE + 2 * k) << 4), BANK(uispr),
                    uispr_tiles + ((uint16_t)(first + 2 * b) << 4), 2)) return;   // queue full: next frame
    if (hud_band[k] != 0xFF) hud_show[k] = HUD_SHOW;
    hud_band[k] = b;
}

void hud_draw(void) {
    uint8_t k, b, on;
    uint16_t p = pv;
    if (pv == last_pv && pv_max == last_pvm && sac == last_sac && hud_band[0] != 0xFF && hud_band[1] != 0xFF
        && !hud_show[0] && !hud_show[1] && !hud_panel && !last_panel && hud_band[0] < 2 && hud_band[1] < 2)
        return;                                 // nothing changes on screen (1.9k T a frame otherwise)
    last_pv = pv; last_pvm = pv_max; last_sac = sac; last_panel = hud_panel;
    band(0, p * 2 >= pv_max ? 0 : p * 4 >= pv_max ? 1 : 2, UISPR_HEART_FULL);
    band(1, sac >= (uint8_t)RULE(RULE_SAC_FULL) ? 0 : sac >= (uint8_t)RULE(RULE_SAC_HUNGRY) ? 1 : sac ? 2 : 3,
         UISPR_BOWL_FULL);
    for (k = 0; k < 2; k++) {
        b = hud_band[k];
        if (hud_panel == 2) { shadow_OAM[OAM_HUD + k].y = 0; continue; }   // panel text over the labels
        if (hud_panel) { oam8(OAM_HUD + k, 88 + 8, 96 + 16 + 16 * k, HUD_TILE + 2 * k, 0); continue; }
        if (hud_show[k]) hud_show[k]--;
        if (b == 0xFF) on = 0;
        else if (b == 3) on = sys_time & 8;                 // nothing in the bowl: fast blink
        else if (b == 2) on = sys_time & 16;
        else on = b == 1 || hud_show[k];
        if (on) oam8(OAM_HUD + k, (k ? 14 : 4) + 8, 4 + 16, HUD_TILE + 2 * k, 0);
        else shadow_OAM[OAM_HUD + k].y = 0;
    }
}
