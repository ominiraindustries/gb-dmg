; gbe (vmap) - vertical map asm: tile row preparation and the 20-tile VRAM row copy.
; C reference: gbe_vrow_tiles_c in gbe_vmap.c, checked by gbe_selftest.c (GBE_SELFTEST_VMAP).

    .module gbe_vmap
    .area _CODE

; void gbe_vrow_tiles(const uint8_t *m, uint8_t top)   m in DE, top in A.
;   row_buf[2c], row_buf[2c + 1] = mt_tiles[m[c]][0..1] (top) or [2..3] (bottom), c = 0..9.
;   Unrolled: ~100 T per metatile (BC = &mt_tiles[0][half], HL = BC + 4 * mt).
_gbe_vrow_tiles::
    ld  bc, #_mt_tiles
    or  a, a
    jr  nz, 1$
    inc bc
    inc bc                      ; bottom half: tiles 2, 3
1$:
    k = 0
    .rept 10
    ld  a, (de)
    inc de
    ld  l, a
    ld  h, #0
    add hl, hl
    add hl, hl
    add hl, bc
    ld  a, (hl+)
    ld  (_row_buf + k), a
    ld  a, (hl)
    ld  (_row_buf + k + 1), a
    k = k + 2
    .endm
    ret

; void vram_row20(uint8_t *dst, const uint8_t *src)   dst in DE, src in BC.
;   20 consecutive BG map bytes (one screen-wide tile row). VBlank or LCD off only.
;   24 T per tile, ~520 T per call.
_vram_row20::
    ld  h, d
    ld  l, e
    .rept 20
    ld  a, (bc)
    ld  (hl+), a
    inc bc
    .endm
    ret

; void vmap_flush_queue(void)
;   Copies the vq_count queued metatiles (vq_dst[i] = BG address of TL, vq_tiles[i] = TL TR BL
;   BR) and empties the queue. VBlank only. ~100 T per metatile; the C loop cost ~600 T and four
;   of them (a boss row erased in one frame) ran past VBlank (games/shmup vram_late).
;   Covered by the game's VRAM-vs-map tests (games/shmup check_screen), not by the selftest.
_vmap_flush_queue::
    ld  a, (_vq_count)
    or  a, a
    ret z
    ld  b, a
    ld  hl, #_vq_dst
    ld  de, #_vq_tiles
1$:
    ld  a, (hl+)
    ld  c, a
    ld  a, (hl+)
    push hl
    ld  h, a
    ld  l, c                    ; hl = destination (TL)
    ld  a, (de)
    inc de
    ld  (hl+), a
    ld  a, (de)
    inc de
    ld  (hl), a
    ld  a, l
    add a, #31                  ; next BG row, left column
    ld  l, a
    jr  nc, 2$
    inc h
2$:
    ld  a, (de)
    inc de
    ld  (hl+), a
    ld  a, (de)
    inc de
    ld  (hl), a
    pop hl
    dec b
    jr  nz, 1$
    xor a, a
    ld  (_vq_count), a
    ret
