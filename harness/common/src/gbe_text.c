// gbe: text with the shared font (harness/common/font.tiles: 0-9, A-Z, - ! . : ? /) and a
// message log typed into a window/BG area through the VRAM queue (gbe_vq).
// The game sets txt_font = VRAM_FONT and txt_blank = its blank tile.
#include <string.h>
#include "gbe.h"
#include "font.h"

uint8_t txt_font, txt_blank, txt_lower, txt_es;   // VRAM bases of font_lower / font_es (0 = none)

uint8_t txt_char(char c) {
    if (c >= 'A' && c <= 'Z') return txt_font + FONT_LETTER_A + (c - 'A');
    if (c >= 'a' && c <= 'z')                    // lowercase: font_lower if loaded, else uppercase
        return txt_lower ? txt_lower + (c - 'a') : txt_font + FONT_LETTER_A + (c - 'a');
    if (c >= '0' && c <= '9') return txt_font + FONT_DIGIT0 + (c - '0');
    switch (c) {
    case '-': return txt_font + FONT_DASH;
    case '!': return txt_font + FONT_EXCLAM;
    case '.': return txt_font + FONT_DOT;
    case ':': return txt_font + FONT_COLON;
    case '?': return txt_font + FONT_QUESTION;
    case '/': return txt_font + FONT_SLASH;
    }
    if (txt_es) {                                // font_es.tiles: COMMA APOSTROPHE EXCL_OPEN QUEST_OPEN
        if (c == ',') return txt_es;
        if (c == 0x27) return txt_es + 1;        // apostrophe
        if ((uint8_t)c == 0xA1) return txt_es + 2;   // '¡' (script.py / tables.py encode Latin-1)
        if ((uint8_t)c == 0xBF) return txt_es + 3;   // '¿'
    }
    return txt_blank;
}

// Up to n tiles from s, padded with blanks; returns the text length written
uint8_t txt_tiles(uint8_t *dst, const char *s, uint8_t n) {
    uint8_t k = 0;
    while (k < n && s[k]) { dst[k] = txt_char(s[k]); k++; }
    memset(dst + k, txt_blank, n - k);
    return k;
}

// v in `width` digits, right-aligned; leading zeros if zero_pad, else blanks
void txt_u16(uint8_t *dst, uint16_t v, uint8_t width, uint8_t zero_pad) {
    uint8_t *d = dst + width;
    do {
        *--d = txt_font + FONT_DIGIT0 + (uint8_t)(v % 10);
        v /= 10;
    } while (v && d > dst);
    while (d > dst) *--d = zero_pad ? txt_font + FONT_DIGIT0 : txt_blank;
}
