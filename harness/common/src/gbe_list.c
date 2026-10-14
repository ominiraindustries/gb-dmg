// gbe: scrolling list (inventories, shops, the bestiary) - n items, k visible rows, cursor tile,
// hold-to-repeat (16 f, then every 6 f), 'more above / below' arrows, A = choose, B = back.
// The game renders rows: list_row(item, buf) fills list_w tiles (called for the visible rows when
// the list scrolls; items >= n get blanks). Rows and arrows go through gbe_vq.
// The callback is a plain near pointer: call list_open / list_update from the same ROM bank as
// the callback (or from bank 0 with the callback in bank 0) - gbe_list never switches banks.
#include <string.h>
#include "gbe.h"

uint8_t list_n, list_sel, list_top, list_k, list_w, list_rep;
uint8_t *list_dst0;                      // map address of row 0's first text cell
uint8_t list_stride;                     // map bytes between rows (32, or 64 for 2-row items)
uint8_t *list_up_at, *list_down_at;      // arrow cells (0 = none)
uint8_t list_cursor, list_blank, list_arrow_up, list_arrow_down, list_border;
void (*list_row)(uint8_t item, uint8_t *buf);

static void draw_rows(void) {
    uint8_t r, buf[20];
    uint8_t *d = list_dst0;
    for (r = 0; r < list_k; r++, d += list_stride) {
        if (list_top + r < list_n) list_row(list_top + r, buf);
        else memset(buf, list_blank, list_w);
        buf[0] = (list_top + r == list_sel) ? list_cursor : list_blank;   // column 0 = cursor
        vq_push(d, buf, list_w);
    }
    if (list_up_at) vq_push(list_up_at, list_top ? &list_arrow_up : &list_border, 1);
    if (list_down_at) vq_push(list_down_at, list_top + list_k < list_n ? &list_arrow_down : &list_border, 1);
}

static void cursor(uint8_t on) {
    vq_push(list_dst0 + (uint16_t)(list_sel - list_top) * list_stride, on ? &list_cursor : &list_blank, 1);
}

// dst0: first cell of row 0 (the cursor column; text starts one cell right); w <= 20 tiles
void list_open(uint8_t n, uint8_t sel, uint8_t k, uint8_t *dst0, uint8_t stride, uint8_t w,
               void (*row)(uint8_t, uint8_t *)) {
    list_n = n;
    list_k = k;
    list_dst0 = dst0;
    list_stride = stride;
    list_w = w;
    list_row = row;
    list_rep = 0;
    list_sel = (n && sel >= n) ? n - 1 : sel;
    list_top = list_sel >= k ? list_sel - k + 1 : 0;
    draw_rows();
}

void list_redraw(void) {
    if (list_sel >= list_n && list_n) list_sel = list_n - 1;
    if (list_top && list_top + list_k > list_n) list_top = list_n > list_k ? list_n - list_k : 0;
    draw_rows();
}

static void move(int8_t d) {
    uint8_t old_top = list_top;
    if (!list_n) return;
    cursor(0);
    if (d > 0) list_sel = (list_sel + 1 == list_n) ? 0 : list_sel + 1;
    else list_sel = list_sel ? list_sel - 1 : list_n - 1;
    if (list_sel < list_top) list_top = list_sel;
    else if (list_sel >= list_top + list_k) list_top = list_sel - list_k + 1;
    if (list_top != old_top) draw_rows();
    else cursor(1);
}

uint8_t list_update(void) {
    if (pressed & J_A) return list_n ? list_sel : MENU_NONE;
    if (pressed & J_B) return MENU_BACK;
    if (keys & (J_UP | J_DOWN)) {
        if ((pressed & (J_UP | J_DOWN)) || ++list_rep >= 16) {
            if (!(pressed & (J_UP | J_DOWN))) list_rep = 10;      // then every 6 frames
            move((keys & J_DOWN) ? 1 : -1);
        }
    } else list_rep = 0;
    return MENU_NONE;
}
