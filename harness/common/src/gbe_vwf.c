// gbe: proportional (variable-width) text. Each glyph is drawn at its ink width plus a 1 px gap into
// a strip of tiles in WRAM (one 8 px row of text); the game copies the strip to VRAM (tiles_push or
// LCD off) and points map cells at it. Reference and test decoder: harness/vwf.py (the ROM's strip
// must equal vwf.render byte for byte). Glyph metrics are generated per font: <font>_vwf[] =
// (first ink column << 4) | ink width (harness/asciitiles.py).
// The game registers its fonts once: vwf_font(0, BANK(font), font_tiles, font_vwf) for digits, A-Z
// and - ! . : ? /; 1 = font_lower (a-z); 2 = font_es (, ' ¡ ¿). Any font with the same labels works
// (font_mini...). Cost: ~1.5-2.5k T per glyph in C: draw outside VBlank (a typewriter: 1-2 per frame).
#include <string.h>
#include "gbe_config.h"
#ifdef GBE_BANKED
#pragma bank 255
#endif
#include "gbe.h"

typedef struct { uint8_t bank; const uint8_t *tiles; const uint8_t *met; } vwf_set_t;
static vwf_set_t sets[3];
uint8_t vwf_space = 3;                  // pixels of a ' ' (vwf.py SPACE)

void vwf_font(uint8_t k, uint8_t bank, const uint8_t *tiles, const uint8_t *metrics) GBE_FAR {
    sets[k].bank = bank; sets[k].tiles = tiles; sets[k].met = metrics;
}

// font set and glyph index of c; 0xFF = space / not in the fonts (same table as gbe_text txt_char)
static uint8_t glyph(char c, uint8_t *set) {
    *set = 0;
    if (c >= 'A' && c <= 'Z') return GBE_FONT_LETTER_A + (c - 'A');
    if (c >= '0' && c <= '9') return GBE_FONT_DIGIT0 + (c - '0');
    switch (c) {
    case '-': return GBE_FONT_DASH;
    case '!': return GBE_FONT_EXCLAM;
    case '.': return GBE_FONT_DOT;
    case ':': return GBE_FONT_COLON;
    case '?': return GBE_FONT_QUESTION;
    case '/': return GBE_FONT_SLASH;
    }
    if (c >= 'a' && c <= 'z') { *set = 1; return c - 'a'; }
    *set = 2;
    if (c == ',') return 0;
    if (c == 0x27) return 1;
    if ((uint8_t)c == 0xA1) return 2;   // '¡' (Latin-1, as script.py / tables.py encode it)
    if ((uint8_t)c == 0xBF) return 3;   // '¿'
    return 0xFF;
}

static uint8_t metric(char c, uint8_t *set, uint8_t *g) {
    *g = glyph(c, set);
    if (*g == 0xFF || !sets[*set].met) return 0;
    return bank_read8(sets[*set].bank, sets[*set].met + *g);
}

uint8_t vwf_width(const char *s) GBE_FAR {
    uint8_t x = 0, set, g, m;
    for (; *s; s++) {
        m = metric(*s, &set, &g);
        x += (m & 15) ? (m & 15) + 1 : vwf_space;
    }
    return x;
}

void vwf_clear(uint8_t *buf, uint8_t ntiles) GBE_FAR {
    memset(buf, 0, (uint16_t)ntiles << 4);
}

// Draw s into buf (ntiles tiles, already cleared or holding earlier text) from pixel x; returns the
// pen position after it. Pixels past the strip are dropped.
uint8_t vwf_draw(uint8_t *buf, uint8_t ntiles, uint8_t x, const char *s) GBE_FAR {
    uint8_t data[16], set, g, m, first, sh, k, v, *t0, *t1;
    for (; *s; s++) {
        m = metric(*s, &set, &g);
        if (!(m & 15)) { x += vwf_space; continue; }
        first = m >> 4;
        bank_memcpy(sets[set].bank, data, sets[set].tiles + ((uint16_t)g << 4), 16);
        sh = x & 7;
        k = x >> 3;
        t0 = k < ntiles ? buf + ((uint16_t)k << 4) : 0;
        t1 = (sh && k + 1 < ntiles) ? buf + ((uint16_t)(k + 1) << 4) : 0;
        for (k = 0; k < 16; k++) {
            v = data[k] << first;
            if (t0) t0[k] |= v >> sh;
            if (t1) t1[k] |= v << (8 - sh);
        }
        x += (m & 15) + 1;
    }
    return x;
}
