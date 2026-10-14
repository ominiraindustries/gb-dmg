; gbe (pool) - shared engine asm: object pools in 8-bit OAM space, collisions, OAM groups.
; Records of 16 bytes (pool_obj_t in gbe.h), walked with pointers. Field offsets:
;   +0 t  +1 x  +2 xs  +3 y  +4 ys  +5/+6 vx (lo/hi)  +7/+8 vy  +9 s  +10 tm  +11 aux
;   +12 tile  +13 prop  +14 aux2  +15 pad
; C references: gbe_pool.c / gbe_spr.c (*_c), checked by gbe_selftest.c (GBE_SELFTEST_POOL).
; History (games/gbe_lab, shmup peak with 26 objects): C ~1000 T per moved object; asm over
; separate arrays ~350 T (one address per field); these record walkers are the current version.

    .module gbe_pool

    .area _DATA
pm_n:       .ds 1
hf_n:       .ds 1
hq_y2:      .ds 1                   ; hit_qy + hit_qh
hq_x2:      .ds 1                   ; hit_qx + hit_qw
sg_begin:   .ds 1                   ; low bytes of OAM pointers (shadow_OAM is page-aligned)
sg_end:     .ds 1
sg_left:    .ds 1
sg_k:       .ds 1

    .area _CODE

; HL = &pool[A] (A * 16 + _pool). Clobbers A, DE.
pool_addr:
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
_pool_move::
    push de
    call pool_addr
    pop de
    ld  a, e
    ld  (pm_n), a
1$:
    ld  a, (hl)                 ; t
    or  a, a
    jr  z, 9$
    push hl
    ld  bc, #5
    add hl, bc                  ; -> vx lo
    ld  a, (hl+)
    ld  e, a
    ld  a, (hl+)
    ld  d, a                    ; de = vx
    ld  a, (hl+)
    ld  c, a
    ld  b, (hl)                 ; bc = vy
    pop hl
    push hl
    inc hl
    inc hl                      ; -> xs
    ld  a, (hl)
    add a, e
    ld  (hl-), a                ; xs (carry kept: ld does not touch flags)
    ld  a, (hl)
    adc a, d
    ld  (hl+), a                ; x
    cp  a, #168
    jr  nc, 7$
    inc hl
    inc hl                      ; -> ys
    ld  a, (hl)
    add a, c
    ld  (hl-), a                ; ys
    ld  a, (hl)
    adc a, b
    ld  (hl), a                 ; y
    cp  a, #176
    jr  c, 8$
7$:
    pop hl
    ld  (hl), #0                ; left the screen: free
    jr  9$
8$:
    pop hl
9$:
    ld  de, #16
    add hl, de
    ld  a, (pm_n)
    dec a
    ld  (pm_n), a
    jr  nz, 1$
    ret

; uint8_t hit_first(uint8_t first, uint8_t n)  first in A, n in E (n >= 1); returns A.
;   First live object of the range whose box (x + hit_ox, y + hit_oy, hit_ow, hit_oh) overlaps
;   the query box (hit_qx, hit_qy, hit_qw, hit_qh); 0xFF if none. Y first (early out).
_hit_first::
    ld  c, a                    ; c = index
    ld  a, e
    ld  (hf_n), a
    ld  a, (_hit_qy)
    ld  hl, #_hit_qh
    add a, (hl)
    ld  (hq_y2), a
    ld  a, (_hit_qx)
    ld  hl, #_hit_qw
    add a, (hl)
    ld  (hq_x2), a
    ld  a, c
    call pool_addr
1$:
    ld  a, (hl)
    or  a, a
    jr  z, 8$
    push hl
    inc hl
    ld  b, (hl)                 ; b = x
    inc hl
    inc hl
    ld  a, (hl)                 ; y
    ld  hl, #_hit_oy
    add a, (hl)
    ld  d, a                    ; d = ot
    ld  a, (hq_y2)
    cp  a, d
    jr  c, 7$                   ; need ot < qy + qh
    jr  z, 7$
    ld  a, d
    ld  hl, #_hit_oh
    add a, (hl)
    ld  e, a
    ld  a, (_hit_qy)
    cp  a, e
    jr  nc, 7$                  ; need qy < ot + oh
    ld  a, b
    ld  hl, #_hit_ox
    add a, (hl)
    ld  d, a                    ; d = ol
    ld  a, (hq_x2)
    cp  a, d
    jr  c, 7$
    jr  z, 7$
    ld  a, d
    ld  hl, #_hit_ow
    add a, (hl)
    ld  e, a
    ld  a, (_hit_qx)
    cp  a, e
    jr  nc, 7$
    pop hl
    ld  a, c                    ; hit
    ret
7$:
    pop hl
8$:
    ld  de, #16
    add hl, de
    inc c
    ld  a, (hf_n)
    dec a
    ld  (hf_n), a
    jr  nz, 1$
    ld  a, #0xFF
    ret

; void spr_group_core(void)   parameters in spr_p_* (set by spr_group() in gbe_spr.c).
;   Hides OAM slots [oam, oam + n) (Y = 0), then writes live objects of the pool range in order
;   starting at slot oam + start, wrapping inside the used part of the range (n & ~1 for size 2),
;   until the slots run out. size 2 = tiles t / t + 2 at x / x + 8, swapped with S_FLIPX.
;   Fields are copied straight from the record to the OAM (no temporaries): x, y kept in E, D;
;   tile and prop re-read from the record for the second half. Same bytes as spr_group_c.
_spr_group_core::
    ld  a, (_spr_p_oam)
    add a, a
    add a, a
    ld  l, a
    ld  (sg_begin), a
    ld  h, #>_shadow_OAM
    ld  a, (_spr_p_n)
    ld  c, a
    xor a, a
1$:
    ld  (hl+), a                ; Y = 0 hides the slot
    inc l
    inc l
    inc l
    dec c
    jr  nz, 1$
    ld  a, (_spr_p_n)
    ld  c, a
    ld  a, (_spr_p_size)
    cp  a, #2
    jr  nz, 2$
    res 0, c                    ; size 2 uses an even number of slots
2$:
    ld  a, c
    ld  (sg_left), a
    add a, a
    add a, a
    ld  b, a
    ld  a, (sg_begin)
    add a, b
    ld  (sg_end), a             ; end of the used slots
    ld  a, (_spr_p_start)
    add a, a
    add a, a
    ld  b, a
    ld  a, (sg_begin)
    add a, b
    ld  l, a                    ; hl = first slot this frame
    push hl
    ld  a, (_spr_p_first)
    call pool_addr
    ld  b, h
    ld  c, l                    ; bc = &pool[first]
    pop hl
    ld  a, (_spr_p_count)
    ld  (sg_k), a
    ld  a, (sg_left)
    ld  e, a                    ; e = slots left (register, not WRAM: measured ~470 T/object before)
    ld  a, (_spr_p_size)
    cp  a, #2
    jr  z, 20$
; ---- size 1: one sprite per object
10$:
    ld  a, (bc)                 ; t
    or  a, a
    jr  z, 18$
    inc bc
    ld  a, (bc)
    ld  d, a                    ; d = x (+1)
    inc bc
    inc bc
    ld  a, (bc)                 ; y (+3)
    ld  (hl+), a
    ld  a, d
    ld  (hl+), a
    ld  a, c
    add a, #9
    ld  c, a
    ld  a, b
    adc a, #0
    ld  b, a                    ; -> tile (+12)
    ld  a, (bc)
    ld  (hl+), a
    inc bc
    ld  a, (bc)                 ; prop (+13)
    ld  (hl+), a
    dec e
    ret z                       ; range full
    inc bc
    inc bc
    inc bc                      ; next record
    ld  a, (sg_end)             ; wrap
    cp  a, l
    jr  nz, 17$
    ld  a, (sg_begin)
    ld  l, a
17$:
    ld  a, (sg_k)
    dec a
    ld  (sg_k), a
    jr  nz, 10$
    ret
18$:
    ld  a, c                    ; free record: bc += 16
    add a, #16
    ld  c, a
    ld  a, b
    adc a, #0
    ld  b, a
    jr  17$
; ---- size 2: two sprites (tile, tile + 2; S_FLIPX swaps them), second at x + 8
20$:
    ld  a, (bc)
    or  a, a
    jr  z, 28$
    inc bc
    ld  a, (bc)
    ld  d, a                    ; d = x
    inc bc
    inc bc
    ld  a, (bc)                 ; y
    ld  (hl+), a
    ld  a, d
    ld  (hl+), a
    ld  a, c
    add a, #10
    ld  c, a
    ld  a, b
    adc a, #0
    ld  b, a                    ; -> prop (+13)
    ld  a, (bc)
    dec bc
    bit 5, a
    ld  a, (bc)                 ; tile (+12)
    jr  z, 21$
    add a, #2
21$:
    ld  (hl+), a                ; left tile
    inc bc
    ld  a, (bc)
    ld  (hl+), a                ; prop
    dec bc
    dec bc
    dec bc
    dec bc
    dec bc
    dec bc
    dec bc
    dec bc
    dec bc
    dec bc                      ; back to y (+3)
    ld  a, (bc)
    ld  (hl+), a
    ld  a, d
    add a, #8
    ld  (hl+), a
    ld  a, c
    add a, #10
    ld  c, a
    ld  a, b
    adc a, #0
    ld  b, a                    ; -> prop (+13)
    ld  a, (bc)
    dec bc
    bit 5, a
    ld  a, (bc)
    jr  nz, 22$
    add a, #2
22$:
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
    ld  a, (sg_k)
    dec a
    ld  (sg_k), a
    jr  nz, 20$
    ret
28$:
    ld  a, c
    add a, #16
    ld  c, a
    ld  a, b
    adc a, #0
    ld  b, a
    jr  27$
