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

; void column_tiles(const uint8_t *m, uint8_t h)    m in DE, h in A (__sdcccall(1)).
;   Fills col_buf[16] with one BG tile column of 8 metatiles: for each row r,
;   col_buf[2r] = mt_tiles[m[r]][h] (top), col_buf[2r+1] = mt_tiles[m[r]][2 + h] (bottom).
;   id * 4 has its low 2 bits clear, so "+ h" is an OR with no carry.
;   Reference: the C loop in prepare_column_c (level.c). Cost ~1300 T (C ~3600 T).
_column_tiles::
    ld  c, a                    ; c = h (0 or 1)
    ld  b, #8                   ; rows
    ld  hl, #_col_buf
1$:
    push bc
    push hl                     ; dst
    ld  a, (de)                 ; metatile id
    inc de
    push de                     ; m
    ld  l, a
    ld  h, #0
    add hl, hl
    add hl, hl                  ; id * 4
    ld  a, l
    or  a, c
    ld  l, a                    ; + h
    ld  de, #_mt_tiles
    add hl, de
    ld  a, (hl+)
    inc hl
    ld  e, a                    ; top tile
    ld  d, (hl)                 ; bottom tile
    pop bc                      ; bc = m
    pop hl                      ; hl = dst
    ld  (hl), e
    inc hl
    ld  (hl), d
    inc hl
    ld  d, b
    ld  e, c                    ; de = m
    pop bc                      ; b = rows left, c = h
    dec b
    jr  nz, 1$
    ret

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
