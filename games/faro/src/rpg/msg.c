// FARO kit - system messages (res/data/msgs.tbl): the kit has no text of its own. A template's
// {S} {O} {N} are filled at run time and the result is wrapped at spaces to the width of the box
// that shows it (text box 18, Start panel 9). Bank 1.
#pragma bank 255
#include "rpg.h"
#include "tbl_msgs.h"

// msgs[msg] with {S} = s, {O} = o, {N} = n -> dst (at most max chars + the 0)
void msg_expand(uint8_t msg, const char *s, const char *o, uint16_t n, char *dst, uint8_t max) BANKED {
    msgs_t m;
    char num[6], *d = dst, *end = dst + max, *src;
    const char *w;
    uint8_t k;
    bank_memcpy(BANK(tbl_msgs), &m, &tbl_msgs[msg], sizeof(m));
    for (src = m.t; *src && d < end; src++) {
        if (*src == '{' && src[2] == '}') {
            w = src[1] == 'S' ? s : src[1] == 'O' ? o : 0;
            if (w) while (*w && d < end) *d++ = *w++;
            else {
                k = 0;
                do { num[k++] = '0' + n % 10; n /= 10; } while (n);
                while (k && d < end) *d++ = num[--k];
            }
            src += 2;
        } else *d++ = *src;
    }
    *d = 0;
}

// Greedy wrap of src into dst: lines of <= w chars broken at spaces with 0x0A; paged = the text
// box's 2-line pages (breaks alternate 0x0A new line / 0x0C new page). Returns the line count.
uint8_t msg_wrap(const char *src, char *dst, uint8_t w, uint8_t paged) BANKED {
    const char *e;
    uint8_t col = 0, lines = 1, len;
    for (;;) {
        for (e = src; *e && *e != ' '; e++) ;
        len = (uint8_t)(e - src);
        if (col && col + 1 + len > w) {
            *dst++ = (paged && !(lines & 1)) ? 0x0C : 0x0A;
            lines++;
            col = 0;
        } else if (col) { *dst++ = ' '; col++; }
        memcpy(dst, src, len); dst += len; col += len;
        if (!*e) break;
        src = e + 1;
    }
    *dst = 0;
    return lines;
}
