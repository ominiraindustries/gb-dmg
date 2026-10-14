; gbe (actors) - shared engine asm (harness/common/src). Measured and equivalence-tested in
; games/platformer. Call VRAM writers only in VBlank or with the LCD off.

    .module gbe_actors
    .area _CODE

; void act_move(uint8_t i)                    i in A (__sdcccall(1)). Clobbers AF BC DE HL.
;   {act_x[i] (u16) : act_xs[i]} += act_vx[i] (s16 8.8, sign-extended)
;   {act_y[i] (u8)  : act_ys[i]} += act_vy[i] (8.8, wraps in 8 bits like the C version)
;   Reference C version: act_move_c (gbe_actors.c); checked by the equivalence test.
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
