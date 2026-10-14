// gbe: VRAM write queue with a per-frame tile budget. Text, HUD fields and cursors are composed
// in update() and pushed here (the bytes are copied into the queue, so callers may reuse their
// buffers); vq_draw_vram() (asm, gbe_vq.s) copies FIFO in VBlank, at most vq_budget tiles per
// frame, continuing a long entry in the next frame. Generalizes the HUD queues of platformer/shmup.
//
// The queue is one byte stream: [len, dst_lo, dst_hi, data[len]] ... between vq_rd and vq_wr.
// (An array-of-entries version cost ~150 T per tile in VBlank, games/dungeon; the stream copies
// at ~20 T per tile.)
#include <string.h>
#include "gbe.h"

#define VQ_BYTES 250

uint8_t vq_budget = 48;                 // tiles per VBlank (0 while another big copy runs)
uint8_t vq_lost;                        // pushes dropped because the queue was full (tests: 0)
uint8_t vq_buf[VQ_BYTES], vq_rd, vq_wr;

uint8_t vq_push(uint8_t *dst, const uint8_t *src, uint8_t len) {
    uint8_t *p;
    if (!len) return 1;
    if ((uint16_t)vq_wr + 3 + len > VQ_BYTES) { vq_lost++; return 0; }
    p = vq_buf + vq_wr;
    p[0] = len;
    p[1] = (uint8_t)(uint16_t)dst;
    p[2] = (uint8_t)((uint16_t)dst >> 8);
    memcpy(p + 3, src, len);
    vq_wr += 3 + len;
    return 1;
}

uint8_t vq_push_fill(uint8_t *dst, uint8_t tile, uint8_t len) {
    uint8_t t[32];
    if (len > 32) len = 32;
    memset(t, tile, len);
    return vq_push(dst, t, len);
}

uint8_t vq_pending(void) {
    return vq_rd != vq_wr;
}
