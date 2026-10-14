// gbe: tile DATA queue (16 bytes per tile) - animated BG tiles (water, flowers), sprite frames
// swapped in (bike), a creature's tiles loaded when it appears. The game pushes runs of tiles from
// any bank; tiles_prepare() (logic) copies up to tiles_budget tiles to a WRAM staging buffer with
// the bank switched, tiles_draw_vram() (VBlank) only copies WRAM -> VRAM (tile_copy16 in
// gbe_tiles.s, ~330 T per tile). Runs longer than the budget continue next frame.
#include <string.h>
#include "gbe.h"

#define TQ_N     8                      // queued runs
#define TQ_STAGE 4                      // tiles per VBlank at most

uint8_t *tq_dst[TQ_N];
const uint8_t *tq_src[TQ_N];
uint8_t tq_bank[TQ_N], tq_n[TQ_N], tq_head, tq_tail;
uint8_t tiles_budget = 2, tiles_lost;              // 2 tiles = ~700 T of VBlank
uint8_t tq_stage[TQ_STAGE * 16];
uint8_t *tq_stage_dst[TQ_STAGE];
uint8_t tq_staged;

// dst: VRAM address of the first tile (0x8000 + 16 * index); n tiles from src in bank (0 = bank 0)
uint8_t tiles_push(uint8_t *dst, uint8_t bank, const uint8_t *src, uint8_t n) {
    uint8_t i;
    if ((uint8_t)(tq_tail - tq_head) >= TQ_N) { tiles_lost++; return 0; }
    i = tq_tail & (TQ_N - 1);
    tq_dst[i] = dst;
    tq_bank[i] = bank;
    tq_src[i] = src;
    tq_n[i] = n;
    tq_tail++;
    return 1;
}

uint8_t tiles_pending(void) {
    return (uint8_t)(tq_tail - tq_head) + tq_staged;
}

void tiles_prepare(void) {
    uint8_t i, saved;
    if (tq_staged) return;                       // last frame's tiles not copied yet
    saved = CURRENT_BANK;
    while (tq_head != tq_tail && tq_staged < tiles_budget) {
        i = tq_head & (TQ_N - 1);
        if (tq_bank[i]) SWITCH_ROM(tq_bank[i]);
        memcpy(tq_stage + (tq_staged << 4), tq_src[i], 16);
        tq_stage_dst[tq_staged++] = tq_dst[i];
        tq_dst[i] += 16;
        tq_src[i] += 16;
        if (!--tq_n[i]) tq_head++;
    }
    SWITCH_ROM(saved);
}

void tile_copy16(uint8_t *dst, const uint8_t *src);   // asm

void tiles_draw_vram(void) {
    uint8_t k;
    for (k = 0; k < tq_staged; k++) tile_copy16(tq_stage_dst[k], tq_stage + (k << 4));
    tq_staged = 0;
}
