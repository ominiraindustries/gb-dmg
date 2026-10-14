; CABALLERITO-specific asm (the shared routines live in harness/common/src/gbe_*.s)

    .module vram
    .area _CODE

; void walk_on_map(uint8_t i, uint8_t dbl)     i in A, dbl in E (__sdcccall(1)).
;   One enemy physics step (dbl = 1: a 2-frame step). Same behaviour as walk_on_map_c
;   (enemies.c), checked by the equivalence test over the real level:
;     vy = act_vy[i] + (dbl ? 0x80 : 0x40), capped at 0x0300 (signed); act_vy[i] = vy
;     act_move(i) (twice if dbl)
;     front = vx > 0 ? x + 14 : x + 1; if solid_at(front, y + 8): snap x to the block edge
;       ((front & 0xFFF0) - 15 / + 15) and negate act_vx[i]
;     if vy > 0 and solid_at(x + 3, y + 15) || solid_at(x + 12, y + 15): land on the block
;       (act_y = ((y + 15 - 32) & 0xF0) + 16, act_ys = 0, act_vy = 0)
;   Cost ~1300 T (SDCC's version ~3700 T: locals spilled to the stack, long signed compares).
    .area _DATA
wom_i:      .ds 1
wom_dbl:    .ds 1
wom_x:      .ds 2
wom_y:      .ds 1
wom_flags:  .ds 1               ; bit 0: vx > 0, bit 1: vy > 0
    .area _CODE

_walk_on_map::
    ld  (wom_i), a
    ld  c, a
    ld  a, e
    ld  (wom_dbl), a
    ld  b, #0
    ld  hl, #_act_vy            ; vy = act_vy[i] + gravity
    add hl, bc
    add hl, bc
    push hl
    ld  a, (hl+)
    ld  e, a
    ld  d, (hl)
    ld  a, (wom_dbl)
    or  a, a
    ld  a, #0x40
    jr  z, 1$
    ld  a, #0x80
1$:
    add a, e
    ld  e, a
    ld  a, d
    adc a, #0
    ld  d, a
    bit 7, d                    ; negative: no cap
    jr  nz, 3$
    ld  a, d
    cp  a, #3
    jr  c, 3$                   ; < 0x0300
    jr  nz, 2$                  ; >= 0x0400
    ld  a, e
    or  a, a
    jr  z, 3$                   ; == 0x0300
2$:
    ld  de, #0x0300
3$:
    pop hl
    ld  a, e
    ld  (hl+), a
    ld  (hl), d                 ; act_vy[i] = vy
    xor a, a                    ; flags: bit 1 = vy > 0
    bit 7, d
    jr  nz, 4$
    ld  a, d
    or  a, e
    jr  z, 4$
    ld  a, #2
4$:
    ld  (wom_flags), a
    ld  a, (wom_i)
    call _act_move
    ld  a, (wom_dbl)
    or  a, a
    jr  z, 5$
    ld  a, (wom_i)
    call _act_move
5$:
    ld  a, (wom_i)              ; load x, y and the sign of vx
    ld  c, a
    ld  b, #0
    ld  hl, #_act_x
    add hl, bc
    add hl, bc
    ld  a, (hl+)
    ld  (wom_x), a
    ld  a, (hl)
    ld  (wom_x + 1), a
    ld  hl, #_act_y
    add hl, bc
    ld  a, (hl)
    ld  (wom_y), a
    ld  hl, #_act_vx
    add hl, bc
    add hl, bc
    ld  a, (hl+)
    ld  e, a
    ld  d, (hl)
    bit 7, d
    jr  nz, 6$                  ; vx < 0
    ld  a, d
    or  a, e
    jr  z, 6$                   ; vx == 0 counts as "not > 0"
    ld  hl, #wom_flags
    set 0, (hl)
6$:
    ld  a, (wom_x)              ; front = vx > 0 ? x + 14 : x + 1
    ld  e, a
    ld  a, (wom_x + 1)
    ld  d, a
    ld  a, (wom_flags)
    rra
    ld  hl, #14
    jr  c, 7$
    ld  hl, #1
7$:
    add hl, de
    push hl
    ld  d, h
    ld  e, l
    ld  a, (wom_y)
    add a, #8
    call _solid_at
    pop hl
    or  a, a
    jr  z, 9$
    ld  a, l                    ; wall: x = (front & 0xFFF0) -/+ 15, vx = -vx
    and a, #0xF0
    ld  l, a
    ld  a, (wom_flags)
    rra
    ld  de, #0xFFF1             ; -15
    jr  c, 8$
    ld  de, #15
8$:
    add hl, de
    ld  a, l
    ld  (wom_x), a
    ld  a, h
    ld  (wom_x + 1), a
    ld  a, (wom_i)
    ld  c, a
    ld  b, #0
    push hl
    ld  hl, #_act_x
    add hl, bc
    add hl, bc
    pop de
    ld  (hl), e
    inc hl
    ld  (hl), d
    ld  hl, #_act_vx
    add hl, bc
    add hl, bc
    ld  a, (hl)
    cpl
    add a, #1
    ld  (hl+), a
    ld  a, (hl)
    cpl
    adc a, #0
    ld  (hl), a
9$:
    ld  a, (wom_flags)          ; feet only while falling (vy > 0)
    bit 1, a
    ret z
    ld  a, (wom_x)
    ld  e, a
    ld  a, (wom_x + 1)
    ld  d, a
    ld  hl, #3
    add hl, de
    ld  d, h
    ld  e, l
    ld  a, (wom_y)
    add a, #15
    call _solid_at
    or  a, a
    jr  nz, 10$
    ld  a, (wom_x)
    ld  e, a
    ld  a, (wom_x + 1)
    ld  d, a
    ld  hl, #12
    add hl, de
    ld  d, h
    ld  e, l
    ld  a, (wom_y)
    add a, #15
    call _solid_at
    or  a, a
    ret z
10$:
    ld  a, (wom_i)              ; land on the block top
    ld  c, a
    ld  b, #0
    ld  a, (wom_y)
    add a, #0xEF                ; + 15 - 32
    and a, #0xF0
    add a, #16
    ld  hl, #_act_y
    add hl, bc
    ld  (hl), a
    xor a, a
    ld  hl, #_act_ys
    add hl, bc
    ld  (hl), a
    ld  hl, #_act_vy
    add hl, bc
    add hl, bc
    ld  (hl+), a
    ld  (hl), a
    ret
