; gbe_gact.s - asm of gbe_gact.c (C references: gact_move_all_c, gact_at_c, gact_draw_c; selftest
; GBE_SELFTEST_GACT compares records and OAM). Always listed together with gbe_gact.c.
; gact_t record (24 bytes): 0 type, 1 x, 2 y, 3 tx, 4 ty, 5 dir, 6 step, 7 sub, 8 rate_lo,
; 9 rate_hi, 10 moving, 11 timer, 12 anim, 13 tile, 14 prop, 15 prio, 16 beh ... 23 (C only).
    .module gbe_gact_asm

    .area _DATA
_gd_base:   .ds 2
_gd_oam:    .ds 2
_gd_n:      .ds 1
_gd_x:      .ds 1
_gd_y:      .ds 1
_gd_dir:    .ds 1
_gd_step:   .ds 1
_gd_mov:    .ds 1
_gd_ox:     .ds 1
_gd_oy:     .ds 1
_gd_prop:   .ds 1
_gd_cx:     .ds 1
_gd_csx:    .ds 1
_gd_cy:     .ds 1
_gd_csy:    .ds 1

    .area _CODE

; void gact_move_all(void): timers, walking (8.8 rate), arrival (x,y = tx,ty; prio dirty), animation
_gact_move_all::
    ld  hl, #_gact
    ld  a, (#_gact_count)
    ld  b, a
1$:
    ld  a, (hl)                 ; type
    or  a, a
    jr  z, 8$
    push hl
    ld  de, #11
    add hl, de                  ; timer
    ld  a, (hl)
    or  a, a
    jr  z, 2$
    dec (hl)
2$:
    dec hl                      ; 10 moving
    ld  a, (hl)
    or  a, a
    jr  z, 7$
    dec hl                      ; 9 rate_hi
    ld  c, (hl)
    dec hl                      ; 8 rate_lo
    ld  a, (hl-)                ; hl = 7 sub
    add a, (hl)
    ld  (hl-), a                ; sub = t, hl = 6 step
    ld  a, (hl)
    adc a, c
    ld  (hl), a
    cp  a, #16
    jr  c, 5$
    pop hl                      ; arrival
    push hl
    inc hl                      ; 1 x
    ld  d, h
    ld  e, l
    inc hl
    inc hl                      ; 3 tx
    ld  a, (hl+)
    ld  (de), a                 ; x = tx
    inc de
    ld  a, (hl+)                ; ty, hl = 5
    ld  (de), a                 ; y = ty
    inc hl                      ; 6
    xor a, a
    ld  (hl+), a                ; step = 0
    ld  (hl+), a                ; sub = 0, hl = 8
    inc hl
    inc hl                      ; 10
    ld  (hl), a                 ; moving = 0
    ld  de, #5
    add hl, de                  ; 15
    ld  (hl), #0xFF             ; prio dirty
    xor a, a                    ; step = 0 for the animation test
5$:
    and a, #7
    jr  nz, 7$
    pop hl
    push hl
    ld  de, #12
    add hl, de                  ; anim ^= 1
    ld  a, (hl)
    xor a, #1
    ld  (hl), a
7$:
    pop hl
8$:
    ld  de, #24
    add hl, de
    dec b
    jr  nz, 1$
    ret

; uint8_t gact_at(uint8_t x, uint8_t y)    x in A, y in E: slot on or walking into (x, y), else 0xFF
_gact_at::
    ld  d, a
    ld  hl, #_gact
    ld  a, (#_gact_count)
    ld  b, a
    ld  c, #0
1$:
    ld  a, (hl)
    or  a, a
    jr  z, 5$
    inc hl
    ld  a, (hl+)                ; x
    cp  a, d
    jr  nz, 2$
    ld  a, (hl)                 ; y
    cp  a, e
    jr  z, 9$
2$:
    inc hl                      ; 3
    ld  a, (hl+)                ; tx
    cp  a, d
    jr  nz, 3$
    ld  a, (hl)                 ; ty
    cp  a, e
    jr  z, 9$
3$:
    ld  a, l
    add a, #20                  ; hl was base + 4
    jr  6$
5$:
    ld  a, l
    add a, #24
6$:
    ld  l, a
    jr  nc, 7$
    inc h
7$:
    inc c
    dec b
    jr  nz, 1$
    ld  a, #0xFF
    ret
9$:
    ld  a, c
    ret

; void gact_draw(uint8_t first)    first OAM slot in A; 2 sprites (16x16) per actor slot
_gact_draw::
    ld  l, a
    ld  h, #0
    add hl, hl
    add hl, hl
    ld  bc, #_shadow_OAM
    add hl, bc
    ld  a, l
    ld  (#_gd_oam), a
    ld  a, h
    ld  (#_gd_oam + 1), a
    ld  a, (#_gact_count)
    ld  (#_gd_n), a
    ld  hl, #_cam_x             ; camera cell (u8, wraps) and sub-cell, once per call
    ld  a, (hl+)
    ld  e, a
    and a, #0x0F
    ld  (#_gd_csx), a
    ld  a, (hl+)                ; high byte of cam_x, hl = cam_y
    swap a
    and a, #0xF0
    ld  d, a
    ld  a, e
    swap a
    and a, #0x0F
    or  a, d
    ld  (#_gd_cx), a
    ld  hl, #_cam_y
    ld  a, (hl+)
    ld  e, a
    and a, #0x0F
    ld  (#_gd_csy), a
    ld  a, (hl)
    swap a
    and a, #0xF0
    ld  d, a
    ld  a, e
    swap a
    and a, #0x0F
    or  a, d
    ld  (#_gd_cy), a
    ld  hl, #_gact
20$:
    ld  a, l
    ld  (#_gd_base), a
    ld  a, h
    ld  (#_gd_base + 1), a
    ld  a, (hl)                 ; type
    or  a, a
    jp  z, 80$
    inc hl
    ld  a, (hl+)                ; x
    ld  (#_gd_x), a
    ld  a, (hl+)                ; y, hl = 3
    ld  (#_gd_y), a
    inc hl
    inc hl                      ; 5
    ld  a, (hl+)                ; dir, hl = 6
    ld  (#_gd_dir), a
    ld  a, (hl)                 ; step
    ld  (#_gd_step), a
    ld  de, #4
    add hl, de                  ; 10
    ld  a, (hl)                 ; moving
    ld  (#_gd_mov), a
    or  a, a
    jr  nz, 21$
    ld  (#_gd_step), a          ; idle: no pixel offset
21$:
    ; ---- 8-bit screen position: cells relative to the camera cell, wrap-around u8 OAM coordinates.
    ;      x: rx = x - cam_cx must be -1..10, OAM x = (rx << 4) - cam_sx + 8 -+ step (left / right)
    ;      y: ry = y - cam_cy must be -1..9,  OAM y = (ry << 4) - cam_sy + 16 -+ step (up / down)
    ld  a, (#_gd_step)
    ld  d, a                    ; d = step (0 when idle)
    ld  a, (#_gd_dir)
    ld  e, a                    ; e = dir
    ld  a, (#_gd_x)
    ld  hl, #_gd_cx
    sub a, (hl)
    ld  c, a                    ; c = rx
    inc a
    cp  a, #12
    jp  nc, 80$
    ld  a, c
    swap a
    and a, #0xF0
    ld  hl, #_gd_csx
    sub a, (hl)
    add a, #8
    ld  c, a
    ld  a, e
    cp  a, #2
    jr  nz, 22$
    ld  a, c
    sub a, d
    ld  c, a
    jr  24$
22$:
    cp  a, #3
    jr  nz, 24$
    ld  a, c
    add a, d
    ld  c, a
24$:
    ld  a, c
    ld  (#_gd_ox), a
    ld  a, (#_gd_y)
    ld  hl, #_gd_cy
    sub a, (hl)
    ld  c, a                    ; c = ry
    inc a
    cp  a, #11
    jp  nc, 80$
    ld  a, c
    swap a
    and a, #0xF0
    ld  hl, #_gd_csy
    sub a, (hl)
    add a, #16
    ld  c, a
    ld  a, e
    cp  a, #1
    jr  nz, 26$
    ld  a, c
    sub a, d
    ld  c, a
    jr  28$
26$:
    or  a, a
    jr  nz, 28$
    ld  a, c
    add a, d
    ld  c, a
28$:
    ld  a, c
    ld  (#_gd_oy), a            ; OAM y = sy + 16
    ; ---- priority bit (tall grass), computed once per cell
    ld  hl, #_gd_base
    ld  a, (hl+)
    ld  h, (hl)
    ld  l, a
    ld  de, #15
    add hl, de
    ld  a, (hl)
    cp  a, #0xFF
    jr  nz, 31$
    push hl
    ld  a, (#_gd_y)
    ld  e, a
    ld  a, (#_gd_x)
    call _wattr_at
    ld  hl, #_gact_prio_mask
    and a, (hl)
    jr  z, 30$
    ld  a, #0x80                ; S_PRIORITY
30$:
    pop hl
    ld  (hl), a
31$:
    ld  c, a                    ; prio
    dec hl                      ; 14 prop
    ld  a, (hl-)                ; hl = 13
    or  a, c
    ld  c, a
    ld  a, (#_gd_dir)
    cp  a, #2
    jr  nz, 32$
    set 5, c                    ; S_FLIPX
32$:
    ld  a, c
    ld  (#_gd_prop), a
    ld  a, (hl-)                ; tile, hl = 12
    ld  c, a
    ld  b, (hl)                 ; anim
    ld  hl, #_gd_base
    ld  a, (hl+)
    ld  h, (hl)
    ld  l, a
    ld  a, (hl)                 ; type
    bit 7, a
    jr  z, 33$
    ld  a, b                    ; GACT_ANIM2: tile + (anim ? 4 : 0)
    or  a, a
    ld  a, c
    jr  z, 35$
    add a, #4
    jr  35$
33$:
    bit 6, a
    jr  z, 34$
    ld  a, (#_gd_dir)           ; GACT_ANIMF: down 0, up 4, side 8 (+4 stepping); down/up step = flip X
    cp  a, #2
    jr  c, 38$
    ld  a, (#_gd_mov)
    and a, b
    ld  a, c
    jr  z, 39$
    add a, #4
39$:
    add a, #8
    jr  35$
38$:
    ld  e, a                    ; dir 0 / 1
    ld  a, (#_gd_mov)
    and a, b
    jr  z, 40$
    ld  a, (#_gd_prop)
    xor a, #0x20                ; S_FLIPX on the stepping frame
    ld  (#_gd_prop), a
40$:
    ld  a, e
    add a, a
    add a, a
    add a, c
    jr  35$
34$:
    ld  a, (#_gd_dir)           ; NPC: tile + npc_frame[dir] + (moving && anim ? 4 : 0)
    add a, #<_gact_npc_frame
    ld  l, a
    ld  a, #0
    adc a, #>_gact_npc_frame
    ld  h, a
    ld  a, c
    add a, (hl)
    ld  c, a
    ld  a, (#_gd_mov)
    and a, b
    ld  a, c
    jr  z, 35$
    add a, #4
35$:
    ld  c, a                    ; c = tile
    ld  hl, #_gd_oam
    ld  a, (hl+)
    ld  h, (hl)
    ld  l, a
    ld  a, (#_gd_oy)
    ld  b, a
    ld  (hl), b                 ; sprite 1: y, x, tile (+2 if flipped), prop
    inc hl
    ld  a, (#_gd_ox)
    ld  (hl+), a
    ld  a, (#_gd_prop)
    bit 5, a
    ld  a, c
    jr  z, 36$
    add a, #2
36$:
    ld  (hl+), a
    ld  a, (#_gd_prop)
    ld  (hl+), a
    ld  (hl), b                 ; sprite 2: y, x + 8, tile + 2 (tile if flipped), prop
    inc hl
    ld  a, (#_gd_ox)
    add a, #8
    ld  (hl+), a
    ld  a, (#_gd_prop)
    bit 5, a
    ld  a, c
    jr  nz, 37$
    add a, #2
37$:
    ld  (hl+), a
    ld  a, (#_gd_prop)
    ld  (hl+), a
    jr  90$
80$:                            ; free or off-screen: y = 0 on both sprites
    ld  hl, #_gd_oam
    ld  a, (hl+)
    ld  h, (hl)
    ld  l, a
    xor a, a
    ld  (hl), a
    ld  de, #4
    add hl, de
    ld  (hl), a
    add hl, de
90$:
    ld  a, l
    ld  (#_gd_oam), a
    ld  a, h
    ld  (#_gd_oam + 1), a
    ld  hl, #_gd_base
    ld  a, (hl+)
    ld  h, (hl)
    ld  l, a
    ld  de, #24
    add hl, de
    ld  a, (#_gd_n)
    dec a
    ld  (#_gd_n), a
    jp  nz, 20$
    ret
