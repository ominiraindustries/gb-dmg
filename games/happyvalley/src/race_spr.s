; HAPPY VALLEY - sprites(): the runners into shadow OAM (2 8x16 sprites each), asm port of sprites_c in
; race_view.c (the specification; test_view_sprites compares both). C 22k T per frame, this ~3k.
; Nearest row first, rotating start (flicker, not vanish); feet eased 1 px/frame towards rv_want;
; x = pos / 4 - cam + 8, off screen if >= 168 (16 bits, unsigned). Unused entries get y = 0.
; void sprites(void)
    .module race_spr
    .globl _sprites
    .globl _rv_rot, _rn_n, _rv_idx, _rv_want, _rv_y, _rx, _cam, _shadow_OAM

    .area _DATA
sp_i:   .ds 1
sp_n:   .ds 1
sp_k:   .ds 1
sp_fy:  .ds 1
sp_o:   .ds 2

    .area _CODE

_sprites::
    ld  a, (_rv_rot)
    ld  (sp_i), a
    ld  a, (_rn_n)
    ld  (sp_n), a
    ld  hl, #_shadow_OAM
    ld  a, l
    ld  (sp_o), a
    ld  a, h
    ld  (sp_o + 1), a
10$:
    ld  a, (sp_n)
    or  a, a
    jp  z, 40$
    dec a
    ld  (sp_n), a
    ld  a, (sp_i)               ; k = rv_idx[rn_n - 1 - i]
    ld  b, a
    ld  a, (_rn_n)
    dec a
    sub a, b
    ld  e, a
    ld  d, #0
    ld  hl, #_rv_idx
    add hl, de
    ld  a, (hl)
    ld  (sp_k), a
    inc b                       ; if (++i >= rn_n) i = 0
    ld  a, (_rn_n)
    cp  a, b
    jr  nz, 11$
    ld  b, #0
11$:
    ld  a, b
    ld  (sp_i), a
    ld  a, (sp_k)               ; feet = rv_y[k] eased towards rv_want[k]
    ld  e, a
    ld  hl, #_rv_want
    add hl, de
    ld  c, (hl)
    ld  hl, #_rv_y
    add hl, de
    ld  a, (hl)
    cp  a, c
    jr  z, 13$
    jr  c, 12$
    dec a
    jr  13$
12$:
    inc a
13$:
    ld  (hl), a
    inc a
    ld  (sp_fy), a              ; OAM y = feet + 1
    ld  h, d                    ; HL = &rx[k] (64 bytes each), pos first
    ld  l, e
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    ld  bc, #_rx
    add hl, bc
    ld  a, (hl+)
    ld  h, (hl)
    ld  l, a
    srl h                       ; pos >> 2
    rr  l
    srl h
    rr  l
    ld  a, (_cam)               ; - cam + 8
    ld  c, a
    ld  a, (_cam + 1)
    ld  b, a
    ld  a, l
    sub a, c
    ld  l, a
    ld  a, h
    sbc a, b
    ld  h, a
    ld  bc, #8
    add hl, bc
    ld  a, h                    ; >= 168: off screen
    or  a, a
    jr  nz, 10$
    ld  a, l
    cp  a, #168
    jr  nc, 10$
    ld  c, a                    ; C = x
    ld  a, (sp_fy)
    ld  b, a                    ; B = y
    ld  a, (sp_o)
    ld  l, a
    ld  a, (sp_o + 1)
    ld  h, a
    ld  a, b                    ; body: y, x, tile 0, prop 0
    ld  (hl+), a
    ld  a, c
    ld  (hl+), a
    xor a, a
    ld  (hl+), a
    ld  (hl+), a
    ld  a, b                    ; head: y, x + 8, tile 2 + 2k, prop 0
    ld  (hl+), a
    ld  a, c
    add a, #8
    ld  (hl+), a
    ld  a, (sp_k)
    add a, a
    add a, #2
    ld  (hl+), a
    xor a, a
    ld  (hl+), a
    ld  a, l
    ld  (sp_o), a
    ld  a, h
    ld  (sp_o + 1), a
    jp  10$
40$:                            ; the rest: y = 0 (shadow_OAM is page aligned: 40 x 4 = 0xA0)
    ld  a, (sp_o)
    ld  l, a
    ld  a, (sp_o + 1)
    ld  h, a
41$:
    ld  a, l
    cp  a, #0xA0
    jr  nc, 42$
    ld  (hl), #0
    add a, #4
    ld  l, a
    jr  41$
42$:
    ld  a, (_rv_rot)            ; if (++rv_rot >= rn_n) rv_rot = 0
    inc a
    ld  b, a
    ld  a, (_rn_n)
    cp  a, b
    jr  nz, 43$
    ld  b, #0
43$:
    ld  a, b
    ld  (_rv_rot), a
    ret
