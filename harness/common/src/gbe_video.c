// gbe: VBlank register shadows, palette fades and the top-HUD window cut (LYC interrupt)
#include "gbe.h"

uint8_t scx_shadow, scy_shadow;
int8_t shake_x, shake_y;            // added to SCX/SCY in VBlank (screen shake without touching logic)
uint8_t bgp_below, bgp_below_on;    // BG palette below the cut line when on (boss flash under a HUD)
uint8_t bgp_shadow = 0xE4, obp0_shadow = 0xE4, obp1_shadow = 0xD8;
uint8_t bgp_base = 0xE4, obp0_base = 0xE4, obp1_base = 0xD8;
uint8_t hud_cut;

// At cut_line (LYC): wait for HBlank, then window off and sprites on in a single LCDC write,
// so sprites never draw over the HUD and nothing tears mid-line.
static void lcd_isr(void) {
    if (!hud_cut) return;
    while (STAT_REG & STATF_BUSY) ;
    LCDC_REG = (LCDC_REG & ~LCDCF_WINON) | LCDCF_OBJON;
    if (bgp_below_on) BGP_REG = bgp_below;
}

// Start of VBlank: same moment GBDK DMAs the shadow OAM, so BG scroll and sprites change together
static void vbl_isr(void) {
    SCX_REG = scx_shadow + shake_x;
    SCY_REG = scy_shadow + shake_y;
    BGP_REG = bgp_shadow;
    OBP0_REG = obp0_shadow;
    OBP1_REG = obp1_shadow;
    if (hud_cut) LCDC_REG = (LCDC_REG | LCDCF_WINON) & ~LCDCF_OBJON;
}

void video_init(uint8_t cut_line, uint8_t bgp, uint8_t obp0, uint8_t obp1) {
    bgp_base = bgp_shadow = bgp;
    obp0_base = obp0_shadow = obp0;
    obp1_base = obp1_shadow = obp1;
    CRITICAL {
        STAT_REG = STATF_LYC;
        LYC_REG = cut_line;
        add_LCD(lcd_isr);
        add_LCD(nowait_int_handler);          // per-scanline effect: skip GBDK's mode wait
        add_VBL(vbl_isr);
    }
    set_interrupts(VBL_IFLAG | LCD_IFLAG);
}

// Each 2-bit shade c becomes max(c - k, 0): k = 0 normal .. 3 all white
static uint8_t fade_pal(uint8_t pal, uint8_t k) {
    uint8_t out = 0, i, c;
    for (i = 0; i < 8; i += 2) {
        c = (pal >> i) & 3;
        c = c > k ? c - k : 0;
        out |= c << i;
    }
    return out;
}

// Each 2-bit shade c becomes min(c + k, 3): k = 0 normal .. 3 all black (death fade)
static uint8_t dark_pal(uint8_t pal, uint8_t k) {
    uint8_t out = 0, i, c;
    for (i = 0; i < 8; i += 2) {
        c = ((pal >> i) & 3) + k;
        out |= (c > 3 ? 3 : c) << i;
    }
    return out;
}

void set_fade_dark(uint8_t k) {
    bgp_shadow = dark_pal(bgp_base, k);
    obp0_shadow = dark_pal(obp0_base, k);
    obp1_shadow = dark_pal(obp1_base, k);
}

void set_fade(uint8_t k) {
    bgp_shadow = fade_pal(bgp_base, k);
    obp0_shadow = fade_pal(obp0_base, k);
    obp1_shadow = fade_pal(obp1_base, k);
}
