; gbe (vram) - shared engine asm (harness/common/src). Measured and equivalence-tested in
; games/platformer. Call VRAM writers only in VBlank or with the LCD off.

    .module gbe_vram
    .area _CODE

; void vram_col16(uint8_t *dst, const uint8_t *src)
;   dst in DE (BG map address of the top tile), src in BC (16 tile indices), __sdcccall(1).
;   Writes src[0..15] down the column: dst, dst+32, ... dst+480. Clobbers AF BC DE HL.
;   Cost: 32 T per tile, ~560 T per call.
_vram_col16::
    ld  h, d
    ld  l, e
    ld  de, #32
    .rept 16
    ld  a, (bc)
    ld  (hl), a
    inc bc
    add hl, de
    .endm
    ret

; void vram_mt4_list(uint8_t **dst, const uint8_t *tiles, uint8_t n)
;   dst in DE (array of BG addresses), tiles in BC (n x 4: TL TR BL BR), n on the stack (n >= 1).
;   Writes each metatile at dst[i], dst[i] + 1, + 32, + 33. VBlank / LCD off only.
;   ~100 T per metatile; the C loops of gbe_map / gbe_vmap cost ~600 T, and four in one frame (a
;   boss row erased in games/shmup) ran past VBlank.
;   Covered by the games' VRAM-vs-map tests (platformer, shmup), not by the selftest.
_vram_mt4_list::
    ldhl sp, #2
    ld  a, (hl)                 ; n
    pop hl
    inc sp                      ; callee removes the stack byte
    push hl
    push af                     ; n (in A) on the stack
    ld  h, d
    ld  l, e                    ; hl = dst array
    ld  d, b
    ld  e, c                    ; de = tiles
    pop af
    ld  b, a
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
    ret
