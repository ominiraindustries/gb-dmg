; VRAM copy routines for CABALLERITO. Call only in VBlank or with the LCD off.
;
; void vram_col16(uint8_t *dst, const uint8_t *src)
;   dst in DE (BG map address of the top tile), src in BC (16 tile indices), __sdcccall(1).
;   Writes src[0..15] down the column: dst, dst+32, ... dst+480. Clobbers AF BC DE HL.
;   Cost: 32 T per tile (ld a,(bc) 8 + ld (hl),a 8 + inc bc 8 + add hl,de 8), ~560 T per call.

    .module vram
    .area _CODE

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
