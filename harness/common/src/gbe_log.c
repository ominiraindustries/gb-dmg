// gbe: 4-line message log typed through gbe_vq (games/dungeon). Split from gbe_text.c so games
// without a log do not carry it in bank 0. Needs gbe_text.c.
#include <string.h>
#include "gbe.h"

// ---------------------------------------------------------------- message log
// LOG_LINES lines of log_w (<= 20) tiles at log_dst (map rows 32 apart). A new message scrolls
// the lines up (all lines re-queued), then its characters appear log_speed per frame.
#define LOG_LINES 4
#define LOG_W     20
#define LOG_PEND  4

uint8_t log_lines[LOG_LINES][LOG_W];
uint8_t log_pending, log_typing, log_speed = 2, log_w = LOG_W;
static uint8_t *log_dst;
static char log_q[LOG_PEND][LOG_W + 1];
static uint8_t log_q_head, log_len, log_pos;

void log_init(uint8_t *dst, uint8_t width) {
    log_dst = dst;
    log_w = width > LOG_W ? LOG_W : width;
    memset(log_lines, txt_blank, sizeof(log_lines));
    log_pending = log_typing = 0;
    log_q_head = 0;
}

// Queue a message (<= 20 chars); dropped if 4 are already waiting
void log_push(const char *s) {
    uint8_t i;
    if (log_pending == LOG_PEND) return;
    i = log_q_head + log_pending;
    if (i >= LOG_PEND) i -= LOG_PEND;
    {                                   // not strncpy: GBDK's is C, ~290 T per byte
        char *d = log_q[i];
        uint8_t k = LOG_W;
        k = log_w;
        while (k-- && *s) *d++ = *s++;
        *d = 0;
    }
    log_pending++;
}

static void log_redraw(void) {
    uint8_t r;
    for (r = 0; r < LOG_LINES; r++) vq_push(log_dst + ((uint16_t)r << 5), log_lines[r], log_w);
}

// Once per frame (not in VBlank): start the next message or type the current one
void log_update(void) {
    uint8_t n, *line = log_lines[LOG_LINES - 1];
    if (!log_typing) {
        if (!log_pending) return;
        // scroll up: a forward copy to a lower address, so memcpy (asm) is safe here; GBDK's
        // memmove is C and cost ~11k T for these 60 bytes (games/dungeon profile)
        memcpy(log_lines[0], log_lines[1], (LOG_LINES - 1) * LOG_W);
        log_len = txt_tiles(line, log_q[log_q_head], log_w);
        memset(line, txt_blank, LOG_W);                   // revealed progressively
        log_pos = 0;
        log_typing = 1;
        log_redraw();
        return;
    }
    n = log_pos;                                          // only the new characters are queued
    while (log_pos < log_len && log_pos - n < log_speed) {
        line[log_pos] = txt_char(log_q[log_q_head][log_pos]);
        log_pos++;
    }
    if (log_pos > n)
        vq_push(log_dst + ((uint16_t)(LOG_LINES - 1) << 5) + n, line + n, log_pos - n);
    if (log_pos >= log_len) {
        log_typing = 0;
        if (++log_q_head == LOG_PEND) log_q_head = 0;
        log_pending--;
    }
}
