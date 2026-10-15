; HAPPY VALLEY - every runner's world px on the oval (race view, bank 0): the course table point at its
; metre (track_pts: a point every 8 m = 128 pos units: x16 y16 heading), interpolated, plus the lane
; offset along the track normal from lane_off[heading * 16 + lane] (design/gen_track.py; no multiply).
; Past the last point (after the post) the runner goes straight on east by (pos - last) / 4 px.
; Visual only (not part of the model). C version measured 4.6k T per runner; this ~0.8k.
; void place_all(void)   -> rv_x[k], rv_y[k] for k < rn_n
    .module race_place
    .globl _place_all
    .globl _rx, _rn_n, _track_pts, _track_n, _lane_off, _rv_x, _rv_y

LANE = 17

    .area _DATA
pk:     .ds 1                   ; runner index
pf:     .ds 1                   ; fraction 0..127
pextra: .ds 2                   ; px past the last point
ph:     .ds 1                   ; heading
plane:  .ds 1
px0:    .ds 2
py0:    .ds 2

    .area _CODE

; A = (|D| * F) >> 7 with the sign of D (D = s8 in A on entry, F in E); destroys B, C, H, L
smul7:
    ld  b, #0                   ; sign
    bit 7, a
    jr  z, 1$
    cpl
    inc a
    inc b
1$:
    ld  hl, #0                  ; HL = A * E
    ld  c, a
    ld  d, #0
2$:
    srl c
    jr  nc, 3$
    add hl, de
3$:
    sla e
    rl  d
    ld  a, c
    or  a, a
    jr  nz, 2$
    add hl, hl                  ; >> 7 = (<< 1) >> 8
    ld  a, h
    dec b
    ret nz
    cpl
    inc a
    ret

_place_all::
    xor a, a
    ld  (pk), a
10$:
    ld  a, (pk)
    ld  hl, #_rn_n
    cp  a, (hl)
    ret nc
    ; ---------------------------------------------------- the runner: pos, lane
    ld  l, a
    ld  h, #0
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    ld  de, #_rx
    add hl, de
    ld  a, (hl+)
    ld  e, a
    ld  d, (hl)                 ; DE = pos
    ld  bc, #LANE - 1
    add hl, bc
    ld  a, (hl)
    ld  (plane), a
    ; idx = pos >> 7, f = pos & 127
    ld  a, e
    and a, #0x7F
    ld  (pf), a
    ld  a, e
    rla                         ; bit 7 -> carry
    ld  a, d
    rla
    ld  c, a                    ; C = idx low (idx = D * 2 + bit7(E)), carry = bit 8
    ld  a, #0
    rla
    ld  b, a                    ; BC = idx
    xor a, a
    ld  (pextra), a
    ld  (pextra + 1), a
    ; last = track_n - 1; if idx >= last: extra = (pos - last * 128) >> 2, idx = last - 1, f = 127
    ld  hl, #_track_n
    ld  a, (hl+)
    ld  h, (hl)
    ld  l, a
    dec hl                      ; HL = last
    ld  a, c
    sub a, l
    ld  a, b
    sbc a, h
    jr  c, 20$
    push hl                     ; extra
    ld  a, l                    ; HL = last * 128 = last << 7
    srl h
    rr  l
    ld  h, l
    ld  l, #0
    rr  l                       ; (last >> 1) << 8 | (bit0 << 7)
    ld  a, e
    sub a, l
    ld  e, a
    ld  a, d
    sbc a, h
    ld  d, a                    ; DE = pos - last * 128
    srl d
    rr  e
    srl d
    rr  e
    ld  a, e
    ld  (pextra), a
    ld  a, d
    ld  (pextra + 1), a
    pop hl
    dec hl
    ld  b, h
    ld  c, l                    ; idx = last - 1
    ld  a, #127
    ld  (pf), a
20$:
    ; HL = track_pts + idx * 5
    ld  h, b
    ld  l, c
    add hl, hl
    add hl, hl
    add hl, bc
    ld  de, #_track_pts
    add hl, de
    ld  a, (hl+)
    ld  (px0), a
    ld  a, (hl+)
    ld  (px0 + 1), a
    ld  a, (hl+)
    ld  (py0), a
    ld  a, (hl+)
    ld  (py0 + 1), a
    ld  a, (hl+)
    ld  (ph), a
    ; dx = x1 - x0 (s8), dy = y1 - y0
    ld  a, (px0)
    ld  b, a
    ld  a, (hl+)                ; x1 low
    sub a, b
    ld  b, a                    ; B = dx
    inc hl                      ; skip x1 high
    ld  a, (py0)
    ld  c, a
    ld  a, (hl)                 ; y1 low
    sub a, c
    push af                     ; dy
    ld  a, (pf)
    ld  e, a
    ld  a, b
    call smul7                  ; A = dx * f >> 7
    ld  c, a                    ; c = s8 value, b = its sign mask (before the add: rlca kills carry)
    rlca
    sbc a, a
    ld  b, a
    ld  hl, #px0
    ld  a, c
    add a, (hl)
    ld  (hl+), a
    ld  a, b
    adc a, (hl)
    ld  (hl), a
    pop af
    ld  b, a
    ld  a, (pf)
    ld  e, a
    ld  a, b
    call smul7                  ; A = dy * f >> 7
    ld  c, a                    ; c = s8 value, b = its sign mask (before the add: rlca kills carry)
    rlca
    sbc a, a
    ld  b, a
    ld  hl, #py0
    ld  a, c
    add a, (hl)
    ld  (hl+), a
    ld  a, b
    adc a, (hl)
    ld  (hl), a
    ; ---------------------------------------------------- lane offset: x += off(h), y -= off(h + 16)
    ld  a, (ph)
    call lane_at                ; A = lane_off[h * 16 + lane]
    ld  c, a                    ; c = s8 value, b = its sign mask (before the add: rlca kills carry)
    rlca
    sbc a, a
    ld  b, a
    ld  hl, #px0
    ld  a, c
    add a, (hl)
    ld  (hl+), a
    ld  a, b
    adc a, (hl)
    ld  (hl), a
    ld  a, (ph)
    add a, #16
    and a, #63
    call lane_at
    ld  c, a                    ; y -= off (sign mask first: rlca kills the borrow)
    rlca
    sbc a, a
    ld  b, a
    ld  hl, #py0
    ld  a, (hl)
    sub a, c
    ld  (hl+), a
    ld  a, (hl)
    sbc a, b
    ld  (hl), a
    ; ---------------------------------------------------- store rv_x[k] = x0 + extra, rv_y[k] = y0
    ld  a, (pk)
    add a, a
    ld  e, a
    ld  d, #0
    ld  hl, #_rv_x
    add hl, de
    ld  a, (pextra)
    ld  b, a
    ld  a, (px0)
    add a, b
    ld  (hl+), a
    ld  a, (pextra + 1)
    ld  b, a
    ld  a, (px0 + 1)
    adc a, b
    ld  (hl), a
    ld  hl, #_rv_y
    add hl, de
    ld  a, (py0)
    ld  (hl+), a
    ld  a, (py0 + 1)
    ld  (hl), a
    ld  hl, #pk
    inc (hl)
    jp  10$

; A = lane_off[A * 16 + lane]
lane_at:
    ld  l, a
    ld  h, #0
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    ld  a, (plane)
    ld  e, a
    ld  d, #0
    add hl, de
    ld  de, #_lane_off
    add hl, de
    ld  a, (hl)
    ret
