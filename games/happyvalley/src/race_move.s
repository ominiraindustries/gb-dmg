; HAPPY VALLEY - one runner's movement for one tick (GDD 2.4), the hot part of race_tick: speed towards
; the target (launch / normal acceleration, deceleration), blocked by the horse ahead, the course segment,
; the ground lost on a bend, position + fraction, energy drain, the pull counter and the finish.
; C reference: move_one_c() in race.c (same lines of tests/hv_model.py); tests/test_race.py compares
; whole races ROM == model with this and with the C path (race_use_c = 1).
; void move_one(runner_t *r)    DE = r (64-byte record, offsets below = hv.h runner_t)
    .module race_move
    .globl _move_one
    .globl _race_seg_end, _race_seg_n, _race_bends, _race_bk, _rc_dec, _rc_cover_sh, _rc_cost
    .globl _race_t, _race_d16, _race_nfin, _rx

POS     = 0
SPD     = 2
ENE     = 4
VMAX    = 6
TARGET  = 8
FINT    = 12
OVER    = 14
FRAC    = 16
LANE    = 17
DMUL    = 18
ACCL    = 19
ACC     = 20
LAUNCH  = 22
EFF     = 23
COVER   = 26
PULL    = 27
BLOCK   = 28
FIN     = 29
SEG     = 32
DRV     = 46

    .area _DATA
mv_spd: .ds 2
mv_tg:  .ds 2

    .area _CODE

; HL = A * E (8 x 8 -> 16); destroys A, D, E
mul8:
    ld  hl, #0
    ld  d, #0
    or  a, a
    ret z
1$:
    srl a
    jr  nc, 2$
    add hl, de
2$:
    sla e
    rl  d
    or  a, a
    jr  nz, 1$
    ret

_move_one::
    ld  b, d
    ld  c, e                    ; BC = r for the whole function
    ; ---------------------------------------------------- speed towards the target
    ld  hl, #TARGET
    add hl, bc
    ld  a, (hl+)
    ld  (mv_tg), a
    ld  e, a
    ld  a, (hl)
    ld  (mv_tg + 1), a
    ld  d, a                    ; DE = tg
    ld  hl, #SPD
    add hl, bc
    ld  a, (hl+)
    ld  h, (hl)
    ld  l, a                    ; HL = spd
    ld  a, l
    sub a, e
    ld  a, h
    sbc a, d
    jr  nc, 20$                 ; spd >= tg
    push hl                     ; accelerate: s = spd + (launch ? accl : acc)
    ld  hl, #LAUNCH
    add hl, bc
    ld  a, (hl)
    or  a, a
    ld  hl, #ACCL
    jr  nz, 10$
    ld  hl, #ACC
10$:
    add hl, bc
    ld  a, (hl)
    pop hl
    add a, l
    ld  l, a
    adc a, h
    sub a, l
    ld  h, a                    ; HL = s
    ld  a, l
    sub a, e
    ld  a, h
    sbc a, d
    jr  c, 30$                  ; s < tg: spd = s
    ld  h, d
    ld  l, e                    ; else spd = tg
    jr  30$
20$:                            ; spd >= tg: max(tg, spd - DEC)
    ld  a, l
    sub a, e
    ld  e, a
    ld  a, h
    sbc a, d                    ; A:E = spd - tg
    jr  nz, 22$                 ; > 255 > DEC
    ld  a, (_rc_dec)
    cp  a, e
    jr  c, 22$                  ; spd - tg > DEC
    ld  a, (mv_tg)
    ld  l, a
    ld  a, (mv_tg + 1)
    ld  h, a                    ; spd = tg
    jr  30$
22$:
    ld  a, (_rc_dec)
    ld  e, a
    ld  a, l
    sub a, e
    ld  l, a
    jr  nc, 30$
    dec h                       ; spd -= DEC
30$:
    ld  a, l
    ld  (mv_spd), a
    ld  a, h
    ld  (mv_spd + 1), a
    ; ---------------------------------------------------- launch over at vmax - vmax/8
    ld  hl, #LAUNCH
    add hl, bc
    ld  a, (hl)
    or  a, a
    jr  z, 40$
    push hl
    ld  hl, #VMAX
    add hl, bc
    ld  a, (hl+)
    ld  e, a
    ld  d, (hl)                 ; DE = vmax
    ld  h, d
    ld  l, e
    srl h
    rr  l
    srl h
    rr  l
    srl h
    rr  l                       ; HL = vmax >> 3
    ld  a, e
    sub a, l
    ld  e, a
    ld  a, d
    sbc a, h
    ld  d, a                    ; DE = vmax - (vmax >> 3)
    ld  a, (mv_spd)
    sub a, e
    ld  a, (mv_spd + 1)
    sbc a, d
    pop hl
    jr  c, 40$
    xor a, a
    ld  (hl), a                 ; launch = 0
40$:
    ; ---------------------------------------------------- blocked: no faster than the horse ahead
    ld  hl, #BLOCK
    add hl, bc
    ld  a, (hl)
    cp  a, #0xFF
    jr  z, 50$
    ld  l, a
    ld  h, #0
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl                  ; block * 64
    ld  de, #_rx + SPD
    add hl, de
    ld  a, (hl+)
    ld  e, a
    ld  d, (hl)                 ; DE = rx[block].spd
    ld  hl, #mv_spd
    ld  a, e
    sub a, (hl)
    inc hl
    ld  a, d
    sbc a, (hl)
    jr  nc, 50$                 ; not slower
    ld  a, e
    ld  (mv_spd), a
    ld  a, d
    ld  (mv_spd + 1), a
50$:
    ld  hl, #SPD
    add hl, bc
    ld  a, (mv_spd)
    ld  (hl+), a
    ld  a, (mv_spd + 1)
    ld  (hl), a                 ; r->spd = spd
    ; ---------------------------------------------------- segment of pos (pos only grows)
    ld  hl, #POS
    add hl, bc
    ld  a, (hl+)
    ld  e, a
    ld  d, (hl)                 ; DE = pos
    ld  hl, #SEG
    add hl, bc
    push hl                     ; &seg
60$:
    pop hl
    push hl
    ld  a, (hl)
    ld  hl, #_race_seg_n
    cp  a, (hl)
    jr  nc, 62$                 ; seg >= seg_n
    ld  l, a
    ld  h, #0
    add hl, hl
    push de
    ld  de, #_race_seg_end
    add hl, de
    pop de
    ld  a, e
    sub a, (hl)
    inc hl
    ld  a, d
    sbc a, (hl)
    jr  c, 62$                  ; pos < seg_end[seg]
    pop hl
    inc (hl)
    push hl
    jr  60$
62$:
    pop hl
    ld  a, (hl)                 ; seg
    ; ---------------------------------------------------- prog = spd (- bend loss)
    ld  hl, #_race_seg_n
    cp  a, (hl)
    jr  nc, 70$
    ld  e, a
    inc e
    ld  a, (_race_bends)
63$:
    dec e
    jr  z, 64$
    srl a
    jr  63$
64$:
    and a, #1
    jr  z, 70$
    ld  hl, #LANE
    add hl, bc
    ld  e, (hl)
    ld  a, (_race_bk)
    call mul8                   ; HL = lane * bk (<= 65)
    ld  e, l
    ld  a, (mv_spd + 1)
    swap a
    and a, #0xF0
    ld  d, a
    ld  a, (mv_spd)
    swap a
    and a, #0x0F
    or  a, d                    ; A = spd >> 4 (spd < 4096)
    call mul8                   ; HL = (spd >> 4) * (lane * bk)
    srl h
    rr  l
    srl h
    rr  l
    srl h
    rr  l
    srl h
    rr  l
    srl h
    rr  l                       ; >> 5
    ld  a, (mv_spd)
    sub a, l
    ld  e, a
    ld  a, (mv_spd + 1)
    sbc a, h
    ld  d, a                    ; DE = prog
    jr  71$
70$:
    ld  a, (mv_spd)
    ld  e, a
    ld  a, (mv_spd + 1)
    ld  d, a
71$:
    ; ---------------------------------------------------- pos.frac += prog
    ld  hl, #FRAC
    add hl, bc
    ld  a, (hl)
    add a, e
    ld  (hl), a
    ld  a, d
    adc a, #0
    ld  e, a                    ; whole metres/16 gained
    ld  hl, #POS
    add hl, bc
    ld  a, (hl)
    add a, e
    ld  (hl+), a
    ld  a, (hl)
    adc a, #0
    ld  (hl), a
    ; ---------------------------------------------------- energy
    ld  hl, #ENE
    add hl, bc
    ld  a, (hl+)
    or  a, (hl)
    jr  z, 90$
    ld  hl, #EFF
    add hl, bc
    ld  a, (hl)
    add a, #DRV
    ld  l, a
    ld  h, #0
    add hl, bc
    ld  e, (hl)                 ; E = dr = drv[eff] (precomputed cost * dmul >> 3)
    ld  hl, #PULL
    add hl, bc
    ld  a, (hl)
    or  a, a
    jr  z, 82$
    sla e                       ; pulling: double
    jr  84$
82$:
    ld  hl, #COVER
    add hl, bc
    ld  a, (hl)
    or  a, a
    jr  z, 84$
    ld  a, (_rc_cover_sh)       ; covered: dr -= dr >> COVER_SH
    ld  d, e
    inc a
83$:
    dec a
    jr  z, 831$
    srl d
    jr  83$
831$:
    ld  a, e
    sub a, d
    ld  e, a
84$:
    ld  hl, #ENE
    add hl, bc
    ld  a, (hl)
    sub a, e
    ld  d, a
    inc hl
    ld  a, (hl)
    sbc a, #0
    jr  c, 85$                  ; ene < dr: 0
    ld  (hl-), a
    ld  (hl), d
    jr  90$
85$:
    xor a, a
    ld  (hl-), a
    ld  (hl), a
90$:
    ; ---------------------------------------------------- pull counter
    ld  hl, #PULL
    add hl, bc
    ld  a, (hl)
    or  a, a
    jr  z, 95$
    dec (hl)
95$:
    ; ---------------------------------------------------- finish
    ld  hl, #POS
    add hl, bc
    ld  a, (hl+)
    ld  e, a
    ld  d, (hl)
    ld  hl, #_race_d16
    ld  a, e
    sub a, (hl)
    ld  e, a
    inc hl
    ld  a, d
    sbc a, (hl)
    ld  d, a                    ; DE = pos - d16
    ret c
    ld  hl, #FIN
    add hl, bc
    ld  (hl), #1
    ld  hl, #OVER
    add hl, bc
    ld  a, e
    ld  (hl+), a
    ld  (hl), d
    ld  hl, #FINT
    add hl, bc
    ld  a, (_race_t)
    ld  (hl+), a
    ld  a, (_race_t + 1)
    ld  (hl), a
    ld  hl, #_race_nfin
    inc (hl)
    ret
