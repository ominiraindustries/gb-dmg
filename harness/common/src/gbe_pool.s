; gbe (pool) - shared engine asm: object pools in 8-bit OAM space, collisions, OAM groups.
; Records of 16 bytes (pool_obj_t in gbe.h), walked with pointers. Field offsets:
;   +0 t  +1 x  +2 xs  +3 y  +4 ys  +5/+6 vx (lo/hi)  +7/+8 vy  +9 s  +10 tm  +11 aux
;   +12 tile  +13 prop  +14 aux2  +15 pad
; C references: gbe_pool.c / gbe_spr.c (*_c), checked by gbe_selftest.c (GBE_SELFTEST_POOL).
; History (games/gbe_lab, shmup peak with 26 objects): C ~1000 T per moved object; asm over
; separate arrays ~350 T (one address per field); these record walkers are the current version.

    .module gbe_pool

    .area _DATA
hf_n:       .ds 1
hq_kx:      .ds 1                   ; hit_qx - hit_ox - hit_ow + 1
hq_rx:      .ds 1                   ; hit_qw + hit_ow - 1 (right after hq_kx)
sg_begin:   .ds 1                   ; low bytes of OAM pointers (shadow_OAM is page-aligned)
sg_end:     .ds 1
sg_left:    .ds 1
sg_k:       .ds 1
sg_n:       .ds 1
sg_pfirst:  .ds 1
sg_size:    .ds 1
sg_x:       .ds 1
sg_y:       .ds 1

    .area _CODE

; HL = &pool[A] (A * 16 + _pool). Clobbers A, DE.
pool_addr::                     ; global: also used by gbe_aim.s
    ld  l, a
    ld  h, #0
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    ld  de, #_pool
    add hl, de
    ret

; void pool_move(uint8_t first, uint8_t n)     first in A, n in E (n >= 1).
;   For each live object: {x : xs} += vx and, if x < 168, {y : ys} += vy; free it when
;   x >= 168 or y >= 176. Same order and arithmetic as pool_move_c.
;   HL walks the record, DE points at the velocity, B counts: no push/pop and no WRAM counter
;   (~370 T per live object before, games/shmup profile).
_pool_move::
    ld  b, e                    ; b = count
    call pool_addr              ; hl = &pool[first] (clobbers A, DE)
1$:
    ld  a, (hl)                 ; t
    or  a, a
    jr  z, 8$
    ld  a, l
    add a, #5
    ld  e, a
    ld  a, h
    adc a, #0
    ld  d, a                    ; de = &vx (+5)
    inc hl
    inc hl                      ; +2 xs
    ld  a, (de)
    add a, (hl)
    ld  (hl-), a                ; xs (ld keeps the carry)
    inc de
    ld  a, (de)
    adc a, (hl)
    ld  (hl), a                 ; x (+1)
    cp  a, #168
    jr  nc, 5$
    inc de                      ; vy (+7)
    inc hl
    inc hl
    inc hl                      ; +4 ys
    ld  a, (de)
    add a, (hl)
    ld  (hl-), a                ; ys
    inc de
    ld  a, (de)
    adc a, (hl)
    ld  (hl), a                 ; y (+3)
    cp  a, #176
    jr  c, 7$
    dec hl
    dec hl                      ; +1
5$:
    dec hl                      ; +0
    ld  (hl), #0                ; left the screen: free
8$:
    ld  a, l                    ; +0 -> next record
    add a, #16
    ld  l, a
    jr  nc, 6$
    inc h
    jr  6$
7$:
    ld  a, l                    ; +3 -> next record
    add a, #13
    ld  l, a
    jr  nc, 6$
    inc h
6$:
    dec b
    jr  nz, 1$
    ret

; uint8_t hit_first(uint8_t first, uint8_t n)  first in A, n in E (n >= 1); returns A.
;   First live object of the range whose box (x + hit_ox, y + hit_oy, hit_ow, hit_oh) overlaps
;   the query box (hit_qx, hit_qy, hit_qw, hit_qh); 0xFF if none. One compare per axis:
;   (uint8)(y - ky) < ry with ky = qy - oy - oh + 1, ry = qh + oh - 1 (same for x), Y first.
;   ky/ry live in D/E, the record pointer in HL: ~100 T per live object rejected on Y (the
;   two-compare version reloaded hit_* from WRAM per object: ~300 T, games/shmup profile).
_hit_first::
    ld  c, a                    ; c = index
    ld  b, e                    ; b = count
    ld  a, (_hit_qy)
    ld  hl, #_hit_oy
    sub a, (hl)
    ld  hl, #_hit_oh
    sub a, (hl)
    inc a
    ld  d, a                    ; d = ky
    ld  a, (_hit_qh)
    add a, (hl)
    dec a
    ld  e, a                    ; e = ry
    ld  a, (_hit_qx)
    ld  hl, #_hit_ox
    sub a, (hl)
    ld  hl, #_hit_ow
    sub a, (hl)
    inc a
    ld  (hq_kx), a
    ld  a, (_hit_qw)
    add a, (hl)
    dec a
    ld  (hq_rx), a
    ld  a, c
    push de
    call pool_addr              ; clobbers A, DE
    pop de
1$:
    ld  a, (hl)                 ; t
    or  a, a
    jr  z, 8$
    inc hl
    inc hl
    inc hl
    ld  a, (hl)                 ; y (+3)
    sub a, d
    cp  a, e
    jr  nc, 7$
    dec hl
    dec hl
    ld  a, (hl)                 ; x (+1)
    push hl
    ld  hl, #hq_kx
    sub a, (hl)
    inc hl                      ; hq_rx
    cp  a, (hl)
    pop hl
    jr  c, 9$
    inc hl
    inc hl                      ; back to +3
7$:
    ld  a, l                    ; +3 -> next record
    add a, #13
    ld  l, a
    jr  nc, 6$
    inc h
    jr  6$
8$:
    ld  a, l                    ; +0 -> next record
    add a, #16
    ld  l, a
    jr  nc, 6$
    inc h
6$:
    inc c
    dec b
    jr  nz, 1$
    ld  a, #0xFF
    ret
9$:
    ld  a, c
    ret

; void spr_group(uint8_t oam_first, uint8_t oam_n, uint8_t pool_first, uint8_t pool_n, uint8_t size)
;   A = oam_first, E = oam_n, stack: pool_first, pool_n, size (1 byte each, removed here).
;   Writes the live objects of the pool range into OAM slots [oam_first, oam_first + used) starting
;   at the rotated slot (spr_rot), wrapping inside the used part (used = oam_n, or oam_n & ~1 for
;   size 2), then hides (Y = 0) the slots left over; an odd last slot of a size-2 group is hidden
;   too. size 2 = tiles t / t + 2 at x / x + 8, swapped with S_FLIPX. Same bytes as spr_group_c.
;   Measured (games/shmup): C wrapper + full hide + WRAM counter cost ~2400 T per group with few
;   objects; only leftovers are hidden now and the record counter lives in D.
_spr_group::
    add a, a
    add a, a
    ld  (sg_begin), a
    ld  a, e
    ld  (sg_n), a
    ldhl sp, #2
    ld  a, (hl+)
    ld  (sg_pfirst), a
    ld  a, (hl+)
    ld  (sg_k), a               ; pool_n
    ld  a, (hl)
    ld  (sg_size), a
    pop hl                      ; return address
    inc sp
    inc sp
    inc sp                      ; callee removes the 3 stack bytes
    push hl
    ; used slots, slots per object, end of the used part
    ld  a, (sg_n)
    ld  b, a                    ; b = slots (objects that fit)
    ld  c, a                    ; c = used OAM entries
    ld  a, (sg_size)
    cp  a, #2
    jr  nz, 1$
    srl b
    res 0, c
    ld  a, (sg_n)
    bit 0, a
    jr  z, 1$                   ; odd range: hide its last slot (never used by size 2)
    dec a
    add a, a
    add a, a
    ld  e, a
    ld  a, (sg_begin)
    add a, e
    ld  l, a
    ld  h, #>_shadow_OAM
    ld  (hl), #0
1$:
    ld  a, c
    ld  (sg_left), a
    add a, a
    add a, a
    ld  e, a
    ld  a, (sg_begin)
    add a, e
    ld  (sg_end), a
    ; first slot this frame: (spr_rot & 31) mod slots (0 when slots <= 1), x2 for size 2
    ; s < 32 and slots >= 2 -> quotient < 16: subtract slots * 8, 4, 2, 1 (a loop of single
    ; subtractions took up to 15 rounds for a 2-slot group)
    ld  a, (_spr_rot)
    and a, #31
    ld  e, a
    ld  a, b
    cp  a, #2
    jr  nc, 2$
    ld  e, #0                   ; slots <= 1
    jr  4$
2$:
    cp  a, #32
    jr  nc, 4$                  ; slots >= 32: s < slots already
    add a, a
    add a, a
    add a, a
    ld  d, a                    ; d = slots * 8 (<= 248)
    ld  a, e
    .rept 4
    cp  a, d
    jr  c, .+3
    sub a, d
    srl d
    .endm
    ld  e, a
4$:
    ld  a, (sg_size)
    cp  a, #2
    jr  nz, 5$
    sla e
5$:
    ld  a, e
    add a, a
    add a, a
    ld  e, a
    ld  a, (sg_begin)
    add a, e
    push af                     ; first slot (low byte)
    ld  a, (sg_pfirst)
    call pool_addr
    ld  b, h
    ld  c, l                    ; bc = &pool[pool_first]
    pop af
    ld  l, a
    ld  h, #>_shadow_OAM
    ld  a, (sg_left)
    or  a, a
    ret z                       ; size 2 with a 1-slot range: nothing fits
    ld  e, a                    ; e = OAM entries left
    ld  a, (sg_k)
    ld  d, a                    ; d = records to visit
    ld  a, (sg_size)
    cp  a, #2
    jr  z, 20$
; ---- size 1
10$:
    ld  a, (bc)                 ; t
    or  a, a
    jr  z, 18$
    inc bc
    inc bc
    inc bc
    ld  a, (bc)                 ; y (+3)
    ld  (hl+), a
    dec bc
    dec bc
    ld  a, (bc)                 ; x (+1)
    ld  (hl+), a
    ld  a, c
    add a, #11
    ld  c, a
    jr  nc, 11$
    inc b
11$:
    ld  a, (bc)                 ; tile (+12)
    ld  (hl+), a
    inc bc
    ld  a, (bc)                 ; prop (+13)
    ld  (hl+), a
    dec e
    ret z                       ; every slot written
    inc bc
    inc bc
    inc bc                      ; next record
    ld  a, (sg_end)
    cp  a, l
    jr  nz, 17$
    ld  a, (sg_begin)
    ld  l, a
17$:
    dec d
    jr  nz, 10$
    jr  40$
18$:
    ld  a, c                    ; free record: bc += 16
    add a, #16
    ld  c, a
    jr  nc, 17$
    inc b
    jr  17$
; ---- size 2 (x, y kept in WRAM: D and E are busy)
20$:
    ld  a, (bc)
    or  a, a
    jr  z, 28$
    inc bc
    ld  a, (bc)
    ld  (sg_x), a               ; x (+1)
    inc bc
    inc bc
    ld  a, (bc)                 ; y (+3)
    ld  (hl+), a
    ld  (sg_y), a
    ld  a, (sg_x)
    ld  (hl+), a
    ld  a, c
    add a, #10
    ld  c, a
    jr  nc, 21$
    inc b
21$:
    ld  a, (bc)                 ; prop (+13)
    dec bc
    bit 5, a                    ; S_FLIPX
    ld  a, (bc)                 ; tile (+12)
    jr  z, 22$
    add a, #2
22$:
    ld  (hl+), a                ; left tile
    inc bc
    ld  a, (bc)
    ld  (hl+), a                ; prop
    ld  a, (sg_y)
    ld  (hl+), a
    ld  a, (sg_x)
    add a, #8
    ld  (hl+), a
    ld  a, (bc)                 ; prop
    dec bc
    bit 5, a
    ld  a, (bc)                 ; tile
    jr  nz, 23$
    add a, #2
23$:
    ld  (hl+), a                ; right tile
    inc bc
    ld  a, (bc)
    ld  (hl+), a                ; prop
    dec e
    dec e
    ret z
    inc bc
    inc bc
    inc bc
    ld  a, (sg_end)
    cp  a, l
    jr  nz, 27$
    ld  a, (sg_begin)
    ld  l, a
27$:
    dec d
    jr  nz, 20$
    jr  40$
28$:
    ld  a, c
    add a, #16
    ld  c, a
    jr  nc, 27$
    inc b
    jr  27$
; ---- hide the e entries left, continuing from hl and wrapping
40$:
    ld  a, (sg_end)
    ld  d, a
41$:
    xor a, a
    ld  (hl), a
    ld  a, l
    add a, #4
    ld  l, a
    cp  a, d
    jr  nz, 42$
    ld  a, (sg_begin)
    ld  l, a
42$:
    dec e
    jr  nz, 41$
    ret
