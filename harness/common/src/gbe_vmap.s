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
