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

; uint8_t mt_at(uint16_t x, uint8_t y)        x in DE, y in A (__sdcccall(1)), returns A.
;   Metatile id at a world pixel: MT_SKY (0) above the level or below row 7 (pits),
;   MT_HARD (7) at x >= level_px_w (invisible wall), else level[((x >> 1) & 0xFFF8) | row].
;   The index trick: (x >> 4) << 3 == (x >> 1) & ~7. Reference C version: mt_at_c (level.c).
;   Cost: ~124 T (C version ~200 T). Clobbers AF C DE HL.
_mt_at::
    sub a, #32                  ; a = y - Y_BIAS
    jr  c, 1$                   ; above the level
    cp  a, #128
    jr  nc, 1$                  ; row >= 8: pit
    ld  c, a
    ld  hl, #_level_px_w
    ld  a, e
    sub a, (hl)
    inc hl
    ld  a, d
    sbc a, (hl)
    jr  nc, 2$                  ; x >= level_px_w
    srl d
    rr  e
    ld  a, e
    and a, #0xF8
    ld  e, a
    ld  a, c
    swap a
    and a, #0x0F                ; row
    or  a, e
    ld  l, a
    ld  h, d
    ld  de, #_level
    add hl, de
    ld  a, (hl)
    ret
1$:
    xor a, a                    ; MT_SKY
    ret
2$:
    ld  a, #7                   ; MT_HARD
    ret

; uint8_t solid_at(uint16_t x, uint8_t y)     mt_attr[mt_at(x, y)] & ATTR_SOLID. ~190 T (C ~372 T).
_solid_at::
    call _mt_at
    ld  e, a
    ld  d, #0
    ld  hl, #_mt_attr
    add hl, de
    ld  a, (hl)
    and a, #0x80
    ret

; void act_move(uint8_t i)                    i in A (__sdcccall(1)). Clobbers AF BC DE HL.
;   {act_x[i] (u16) : act_xs[i]} += act_vx[i] (s16 8.8, sign-extended)
;   {act_y[i] (u8)  : act_ys[i]} += act_vy[i] (8.8, wraps in 8 bits like the C version)
;   Reference C version: act_move_c (actors.c); checked by the equivalence test.
;   Cost: ~240 T (C version ~1500 T: SDCC re-derives &array[i] and sign-extends with 16-bit ops).
;   Flags note: pop, inc hl, ld and ld (hl+) do not touch the carry between add and adc.
_act_move::
    ld  c, a
    ld  b, #0
    ld  hl, #_act_vx
    add hl, bc
    add hl, bc
    ld  e, (hl)                 ; vx low  (sub-pixels)
    inc hl
    ld  d, (hl)                 ; vx high (pixels, signed)
    ld  hl, #_act_x
    add hl, bc
    add hl, bc
    push hl                     ; &act_x[i]
    ld  hl, #_act_xs
    add hl, bc
    ld  a, d
    rlca
    sbc a, a
    ld  b, a                    ; b = sign extension of vx high (0x00 / 0xFF)
    ld  a, (hl)
    add a, e
    ld  (hl), a                 ; xs += low, carry out
    pop hl
    ld  a, (hl)
    adc a, d
    ld  (hl+), a                ; x low += high + carry
    ld  a, (hl)
    adc a, b
    ld  (hl), a                 ; x high += sign + carry
    ld  b, #0
    ld  hl, #_act_vy
    add hl, bc
    add hl, bc
    ld  e, (hl)
    inc hl
    ld  d, (hl)
    ld  hl, #_act_y
    add hl, bc
    push hl                     ; &act_y[i]
    ld  hl, #_act_ys
    add hl, bc
    ld  a, (hl)
    add a, e
    ld  (hl), a                 ; ys += low, carry out
    pop hl
    ld  a, (hl)
    adc a, d
    ld  (hl), a                 ; y += high + carry
    ret
