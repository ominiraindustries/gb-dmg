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
