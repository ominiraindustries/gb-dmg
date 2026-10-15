; HAPPY VALLEY - a runner's decision every 4 ticks (GDD 2.4): fighting the jockey (RNG), the effort by
; phase and tactic, the sprint reserve, the target speed, the nearest horse ahead in its lane (cover /
; blocked), changing lanes. C reference: think_c() in race.c (same lines of tests/hv_model.py);
; tests/test_race.py: whole races ROM == model with the asm and with the C path (race_use_c = 1).
; void think_asm(runner_t *x, uint8_t i)    DE = x, A = i
    .module race_think
    .globl _think_asm
    .globl _rx, _rn_n, _order, _race_t, _race_d16, _race_final_from, _rng_next
    .globl _rc_start16, _rc_spc, _rc_start_eff, _rc_dpct, _rc_dpct_tired, _rc_res_sh, _rc_len, _rc_len2
    .globl _rc_pull_ticks, _rc_lane_mask, _rc_lanes_max, _rc_free_lo, _rc_free_span

POS      = 0
SPD      = 2
ENE      = 4
VMAX     = 6
TARGET   = 8
SPRINT_AT = 10
LANE     = 17
KICK     = 21
EFF      = 23
SPRINT   = 24
RESERVE  = 25
COVER    = 26
PULL     = 27
BLOCK    = 28
FIN      = 29
RANK     = 31
TAC      = 33
JOCK_OK  = 34
PULL_P   = 35
TGV      = 36

    .area _DATA
th_x:     .ds 2
th_i:     .ds 1
th_pos:   .ds 2
th_rem:   .ds 2
th_tac:   .ds 1
th_eff:   .ds 1
th_tg:    .ds 2
th_lane:  .ds 1
th_k:     .ds 1
th_ahead: .ds 1
th_cover: .ds 1
th_g:     .ds 2

    .area _CODE

; BC = th_x
th_bc:
    ld  a, (th_x)
    ld  c, a
    ld  a, (th_x + 1)
    ld  b, a
    ret

; HL = A * E (8 x 8 -> 16); destroys A, D, E
tmul8:
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

; HL = rx + A * 64
th_runner:
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
    ret

; A = 1 if lane A is free for th_x: nobody else (running) in it with pos - FREE_BACK < y < pos + LEN
th_lane_free:
    ld  (th_k + 0), a           ; reuse th_k as the lane (th_k is free here)
    xor a, a
    ld  (th_g), a               ; th_g = runner index
10$:
    ld  a, (th_g)
    ld  hl, #_rn_n
    cp  a, (hl)
    jr  nc, 19$                 ; all checked: free
    call th_runner              ; HL = y
    ld  a, (th_x)
    cp  a, l
    jr  nz, 11$
    ld  a, (th_x + 1)
    cp  a, h
    jr  z, 18$                  ; y == x
11$:
    push hl
    ld  de, #FIN
    add hl, de
    ld  a, (hl)
    or  a, a
    pop hl
    jr  nz, 18$                 ; finished
    push hl
    ld  de, #LANE
    add hl, de
    ld  a, (th_k)
    cp  a, (hl)
    pop hl
    jr  nz, 18$                 ; another lane
    ld  a, (hl+)                ; d = y.pos - pos + FREE_LO
    ld  e, a
    ld  d, (hl)
    ld  hl, #th_pos
    ld  a, e
    sub a, (hl)
    ld  e, a
    inc hl
    ld  a, d
    sbc a, (hl)
    ld  d, a
    ld  a, (_rc_free_lo)
    add a, e
    ld  e, a
    ld  a, d
    adc a, #0
    jr  nz, 18$                 ; d >= 256 > span
    ld  a, (_rc_free_span)
    ld  d, a
    ld  a, e
    cp  a, d
    jr  c, 17$                  ; d < span: taken
18$:
    ld  hl, #th_g
    inc (hl)
    jr  10$
17$:
    xor a, a
    ret
19$:
    ld  a, #1
    ret

_think_asm::
    ld  (th_i), a
    ld  a, e
    ld  (th_x), a
    ld  a, d
    ld  (th_x + 1), a
    ld  b, d
    ld  c, e
    ld  hl, #POS
    add hl, bc
    ld  a, (hl+)
    ld  (th_pos), a
    ld  a, (hl)
    ld  (th_pos + 1), a
    ld  hl, #LANE
    add hl, bc
    ld  a, (hl)
    ld  (th_lane), a
    ld  hl, #TAC
    add hl, bc
    ld  a, (hl)
    ld  (th_tac), a
    ; rem = (d16 - pos) >> 4
    ld  hl, #th_pos
    ld  a, (_race_d16)
    sub a, (hl)
    ld  e, a
    inc hl
    ld  a, (_race_d16 + 1)
    sbc a, (hl)
    ld  d, a
    srl d
    rr  e
    srl d
    rr  e
    srl d
    rr  e
    srl d
    rr  e
    ld  a, e
    ld  (th_rem), a
    ld  a, d
    ld  (th_rem + 1), a
    ; ---------------------------------------------------- fighting the jockey: (t & 31) == i
    ld  a, (_race_t)
    and a, #31
    ld  hl, #th_i
    cp  a, (hl)
    jr  nz, 1$
    call _rng_next
    ld  e, a
    call th_bc
    ld  hl, #PULL_P
    add hl, bc
    ld  a, e
    cp  a, (hl)
    jr  nc, 1$                  ; rng >= pull_p
    ld  hl, #PULL
    add hl, bc
    ld  a, (_rc_pull_ticks)
    ld  (hl), a
1$:
    ; ---------------------------------------------------- effort
    ld  hl, #th_pos
    ld  a, (hl+)
    ld  e, a
    ld  d, (hl)
    ld  hl, #_rc_start16
    ld  a, e
    sub a, (hl)
    inc hl
    ld  a, d
    sbc a, (hl)
    jr  nc, 2$                  ; pos >= start16
    ld  a, (th_tac)             ; start: START_EFF[tac]
    ld  e, a
    ld  d, #0
    ld  hl, #_rc_start_eff
    add hl, de
    ld  a, (hl)
    jr  9$
2$:
    ld  hl, #SPRINT_AT          ; rem <= sprint_at ?
    add hl, bc
    ld  a, (hl+)
    ld  e, a
    ld  d, (hl)
    ld  hl, #th_rem
    ld  a, e
    sub a, (hl)
    inc hl
    ld  a, d
    sbc a, (hl)
    jr  c, 4$                   ; sprint_at < rem: not yet
    ld  hl, #JOCK_OK            ; eff = (jock >= 5 && ene < rem * SPC && rem > 150) ? 1 : 3
    add hl, bc
    ld  a, (hl)
    or  a, a
    jr  z, 3$
    ld  a, (th_rem + 1)
    or  a, a
    jr  nz, 21$
    ld  a, (th_rem)
    cp  a, #151
    jr  c, 3$                   ; rem <= 150
21$:
    ld  a, (_rc_spc)            ; HL = rem * SPC (16 x 8)
    ld  e, a
    ld  a, (th_rem)
    call tmul8
    push hl
    ld  a, (_rc_spc)
    ld  e, a
    ld  a, (th_rem + 1)
    call tmul8                  ; high part: L = rem_hi * SPC (fits: product < 65536)
    ld  a, l
    pop hl
    add a, h
    ld  h, a                    ; HL = rem * SPC
    call th_bc
    push hl
    ld  hl, #ENE
    add hl, bc
    ld  a, (hl+)
    ld  e, a
    ld  d, (hl)                 ; DE = ene
    pop hl
    ld  a, e
    sub a, l
    ld  a, d
    sbc a, h
    jr  nc, 3$                  ; ene >= rem * SPC
    ld  a, #1
    jr  9$
3$:
    ld  a, #3
    jr  9$
4$:
    ld  a, (th_tac)
    or  a, a
    jr  nz, 5$
    ld  hl, #RANK               ; front-runner: rank <= 1 ? 1 : 2
    add hl, bc
    ld  a, (hl)
    cp  a, #2
    ld  a, #1
    jr  c, 9$
    ld  a, #2
    jr  9$
5$:
    dec a
    ld  a, #1
    jr  z, 9$                   ; stalker: 1
    xor a, a                    ; closer: 0
9$:
    ld  (th_eff), a
    ; ---------------------------------------------------- the sprint reserve (first time eff 3)
    cp  a, #3
    jr  nz, 10$
    ld  hl, #SPRINT
    add hl, bc
    ld  a, (hl)
    or  a, a
    jr  nz, 10$
    ld  (hl), #1
    ld  hl, #ENE
    add hl, bc
    ld  a, (hl+)
    ld  e, a
    ld  d, (hl)
    ld  a, (_rc_res_sh)
    inc a
11$:
    dec a
    jr  z, 12$
    srl d
    rr  e
    jr  11$
12$:
    ld  hl, #RESERVE
    add hl, bc
    ld  (hl), e
10$:
    ld  hl, #EFF
    add hl, bc
    ld  a, (th_eff)
    ld  (hl), a
    ; ---------------------------------------------------- target = tgv[ene ? eff : 4] (precomputed)
    ld  hl, #ENE
    add hl, bc
    ld  a, (hl+)
    or  a, (hl)
    ld  a, #4
    jr  z, 13$
    ld  a, (th_eff)
13$:
    add a, a
    add a, #TGV
    ld  l, a
    ld  h, #0
    add hl, bc
    ld  a, (hl+)
    ld  e, a
    ld  d, (hl)                 ; DE = tg
    call th_bc
    ld  a, (th_eff)             ; eff 3 with energy: + kick + reserve
    cp  a, #3
    jr  nz, 15$
    ld  hl, #ENE
    add hl, bc
    ld  a, (hl+)
    or  a, (hl)
    jr  z, 15$
    ld  hl, #KICK
    add hl, bc
    ld  a, (hl)
    add a, e
    ld  e, a
    jr  nc, 151$
    inc d
151$:
    ld  hl, #RESERVE
    add hl, bc
    ld  a, (hl)
    add a, e
    ld  e, a
    jr  nc, 15$
    inc d
15$:
    ld  a, e
    ld  (th_tg), a
    ld  a, d
    ld  (th_tg + 1), a
    ld  hl, #TARGET
    add hl, bc
    ld  (hl), e
    inc hl
    ld  (hl), d
    ; ---------------------------------------------------- the nearest horse ahead in my lane
    xor a, a
    ld  (th_cover), a
    ld  a, #0xFF
    ld  (th_ahead), a
    ld  hl, #RANK
    add hl, bc
    ld  a, (hl)
    ld  (th_k), a
20$:
    ld  a, (th_k)
    or  a, a
    jr  z, 29$
    dec a
    ld  (th_k), a
    ld  e, a
    ld  d, #0
    ld  hl, #_order
    add hl, de
    ld  a, (hl)                 ; j
    ld  (th_g + 1), a           ; keep j
    call th_runner              ; HL = y
    push hl
    ld  a, (hl+)
    ld  e, a
    ld  d, (hl)                 ; DE = y.pos
    ld  hl, #th_pos
    ld  a, e
    sub a, (hl)
    ld  e, a
    inc hl
    ld  a, d
    sbc a, (hl)
    ld  d, a                    ; DE = g = y.pos - pos
    pop hl
    jr  c, 20$                  ; y.pos < pos: g <= 0, continue
    ld  a, d
    or  a, e
    jr  z, 20$                  ; g == 0
    ld  a, d
    or  a, a
    jr  nz, 29$                 ; g > 255 > 2 LEN: stop
    ld  a, (_rc_len2)
    cp  a, e
    jr  c, 29$                  ; g > 2 LEN: stop
    push hl                     ; same lane and running?
    push de
    ld  de, #LANE
    add hl, de
    ld  a, (th_lane)
    cp  a, (hl)
    pop de
    pop hl
    jr  nz, 20$
    push de
    ld  de, #FIN
    add hl, de
    ld  a, (hl)
    pop de
    or  a, a
    jr  nz, 20$
    ld  a, #1
    ld  (th_cover), a
    ld  a, (_rc_len)
    cp  a, e
    jr  c, 29$                  ; g > LEN: covered, not blocked
    ld  a, (th_g + 1)
    ld  (th_ahead), a
29$:
    call th_bc
    ld  hl, #COVER
    add hl, bc
    ld  a, (th_cover)
    ld  (hl), a
    ld  hl, #BLOCK
    add hl, bc
    ld  (hl), #0xFF
    ; ---------------------------------------------------- lanes
    ld  a, (_rc_lane_mask)      ; lane_turn: (t & mask) == (i & mask)
    ld  d, a
    ld  a, (th_i)
    and a, d
    ld  e, a
    ld  a, (_race_t)
    and a, d
    cp  a, e
    ld  a, #0
    jr  nz, 30$
    inc a
30$:
    ld  (th_k), a               ; th_k = lane_turn
    ld  a, (th_ahead)
    cp  a, #0xFF
    jr  z, 40$
    call th_runner              ; tg > ahead.spd ?
    ld  de, #SPD
    add hl, de
    ld  a, (hl+)
    ld  e, a
    ld  d, (hl)
    ld  hl, #th_tg
    ld  a, e
    sub a, (hl)
    inc hl
    ld  a, d
    sbc a, (hl)                 ; ahead.spd - tg: carry if tg > spd
    jr  nc, 40$
    ld  a, (th_k)               ; move out a lane if allowed and free, else blocked
    or  a, a
    jr  z, 35$
    ld  a, (_rc_lanes_max)
    ld  e, a
    ld  a, (th_lane)
    cp  a, e
    jr  nc, 35$
    inc a
    push af
    call th_lane_free
    ld  e, a
    pop af
    bit 0, e
    jr  z, 35$
    ld  e, a
    call th_bc
    ld  hl, #LANE
    add hl, bc
    ld  (hl), e
    ret
35$:
    call th_bc
    ld  hl, #BLOCK
    add hl, bc
    ld  a, (th_ahead)
    ld  (hl), a
    ret
40$:
    ld  a, (th_k)               ; not blocked: move in a lane on my turn if free
    or  a, a
    ret z
    ld  a, (th_lane)
    or  a, a
    ret z
    dec a
    push af
    call th_lane_free
    ld  e, a
    pop af
    bit 0, e
    ret z
    ld  d, a                    ; D = lane - 1
    ld  hl, #th_pos             ; not when closing (pos >= final_from && tac != 0 && eff == 3)
    ld  a, (hl+)
    ld  e, a
    ld  b, (hl)
    ld  hl, #_race_final_from
    ld  a, e
    sub a, (hl)
    inc hl
    ld  a, b
    sbc a, (hl)
    jr  c, 45$                  ; pos < final_from
    ld  a, (th_tac)
    or  a, a
    jr  z, 45$
    ld  a, (th_eff)
    cp  a, #3
    ret z
45$:
    call th_bc
    ld  hl, #LANE
    add hl, bc
    ld  (hl), d
    ret
