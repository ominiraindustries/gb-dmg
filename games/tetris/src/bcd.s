; Packed BCD score arithmetic (2 digits per byte, little-endian: byte 0 = lowest digits).
;
; void bcd_add3(uint8_t *dst, const uint8_t *src)
;   dst in DE, src in BC (__sdcccall(1)). dst += src, saturating at 999999. Clobbers AF HL DE.
;   16-bit inc and ld do not touch flags, so the carry survives between bytes for adc/daa.
;
; Cost: ~100 T, vs ~2000 T for the C digit-per-byte loop it replaces.

    .module bcd
    .area _CODE

_bcd_add3::
    ld  h, b
    ld  l, c
    ld  a, (de)
    add a, (hl)
    daa
    ld  (de), a
    inc de
    inc hl
    ld  a, (de)
    adc a, (hl)
    daa
    ld  (de), a
    inc de
    inc hl
    ld  a, (de)
    adc a, (hl)
    daa
    ld  (de), a
    ret nc
    ld  a, #0x99            ; overflow: saturate at 999999
    ld  (de), a
    dec de
    ld  (de), a
    dec de
    ld  (de), a
    ret
