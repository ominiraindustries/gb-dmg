; gbe (vq) - VBlank copy of the VRAM write queue (stream [len, dst_lo, dst_hi, data] between
; vq_rd and vq_wr, see gbe_vq.c). Covered by the games' text/HUD VRAM tests (games/dungeon).

    .module gbe_vq
    .area _DATA
vq_left: .ds 1

    .area _CODE

; void vq_draw_vram(void)   VBlank only. Copies whole entries while the budget lasts; an entry
;   larger than what is left is copied in part and its header rewritten just before the rest.
;   ~20 T per tile + ~90 T per entry.
_vq_draw_vram::
    ld  a, (_vq_budget)
    or  a, a
    ret z
    ld  (vq_left), a
1$:
    ldh a, (0x40)               ; LCD on and VBlank over (LY < 144): stop, the rest goes next
    bit 7, a                    ; frame (after a long frame vsync() can return late: a write in
    jr  z, 11$                  ; mode 3 is lost silently, games/dungeon)
    ldh a, (0x44)
    cp  a, #144
    ret c
    cp  a, #152                 ; < 2 lines (~900 T) of VBlank left: an entry (<= ~500 T) could
    ret nc                      ; spill into line 0
11$:
    ld  a, (_vq_rd)
    ld  b, a
    ld  a, (_vq_wr)
    cp  a, b
    jr  z, 8$                   ; empty
    ld  hl, #_vq_buf
    ld  a, l
    add a, b
    ld  l, a
    jr  nc, 2$
    inc h
2$:
    ld  a, (hl+)                ; len
    ld  c, a
    ld  a, (hl+)
    ld  e, a
    ld  a, (hl+)
    ld  d, a                    ; de = dst
    ld  a, (vq_left)
    cp  a, c
    jr  c, 5$                   ; budget < len: partial copy
    sub a, c
    ld  (vq_left), a
    ld  a, b
    add a, #3
    add a, c
    ld  (_vq_rd), a             ; whole entry consumed
3$:
    ld  a, (hl+)
    ld  (de), a
    inc de
    dec c
    jr  nz, 3$
    ld  a, (vq_left)
    or  a, a
    jr  nz, 1$
    jr  8$
5$:                             ; copy `budget` bytes, rewrite the header before the rest
    ld  b, a                    ; b = n = budget (>= 1)
    ld  a, c
    sub a, b
    ld  c, a                    ; c = remaining length
6$:
    ld  a, (hl+)
    ld  (de), a
    inc de
    dec b
    jr  nz, 6$
    dec hl
    ld  (hl), d                 ; header: len, dst_lo, dst_hi in the last 3 consumed bytes
    dec hl
    ld  (hl), e
    dec hl
    ld  (hl), c
    ld  a, (vq_left)            ; vq_rd += n (the header now sits at old rd + n)
    ld  b, a
    ld  a, (_vq_rd)
    add a, b
    ld  (_vq_rd), a
    xor a, a
    ld  (vq_left), a
    ret
8$:
    ld  a, (_vq_rd)             ; empty: rewind the stream
    ld  b, a
    ld  a, (_vq_wr)
    cp  a, b
    ret nz
    xor a, a
    ld  (_vq_rd), a
    ld  (_vq_wr), a
    ret
