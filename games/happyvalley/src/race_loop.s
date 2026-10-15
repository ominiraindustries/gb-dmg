; HAPPY VALLEY - the rest of race_tick in asm (C measured ~11k T): the runner loop (finished / slow
; start / think every 4 ticks / move) and the stable insertion sort of order[] by pos (descending) with
; the ranks. C reference: the race_use_c path of race_tick() in race.c (tests/test_race.py runs both).
; void race_runners(void)   void race_sort(void)
    .module race_loop
    .globl _race_runners, _race_sort
    .globl _rx, _rn_n, _order, _race_t, _think_asm, _move_one, _rl_from, _rl_to

FIN   = 29
DELAY = 30
RANK  = 31

    .area _DATA
_rl_from:: .ds 1                ; race_runners: runners rl_from .. rl_to - 1 (a tick split over 2 frames)
_rl_to::   .ds 1
rl_i:   .ds 1
rl_t:   .ds 1                   ; sort: the index being inserted
rl_s:   .ds 2                   ; sort: its pos
rl_pos: .ds 28                  ; sort: pos of every runner (no x64 per compare)

    .area _CODE

_race_runners::
    ld  a, (_rl_from)
    ld  (rl_i), a
1$:
    ld  a, (rl_i)
    ld  hl, #_rl_to
    cp  a, (hl)
    ret nc
    ld  l, a                    ; HL = r = rx + i * 64
    ld  h, #0
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    ld  de, #_rx
    add hl, de
    push hl
    ld  de, #FIN
    add hl, de
    ld  a, (hl+)                ; fin
    or  a, a
    jr  nz, 8$
    ld  a, (hl)                 ; delay
    or  a, a
    jr  z, 2$
    dec (hl)
    jr  8$
2$:
    ld  a, (_race_t)            ; think on (t & 3) == (i & 3)
    ld  hl, #rl_i
    xor a, (hl)
    and a, #3
    jr  nz, 3$
    pop de
    push de
    ld  a, (rl_i)
    call _think_asm
3$:
    pop de
    push de
    call _move_one
8$:
    pop hl
    ld  hl, #rl_i
    inc (hl)
    jr  1$

; DE = rl_pos[A]
pos_of:
    add a, a
    ld  e, a
    ld  d, #0
    ld  hl, #rl_pos
    add hl, de
    ld  a, (hl+)
    ld  e, a
    ld  d, (hl)
    ret

_race_sort::
    ld  a, (_rn_n)              ; positions in a compact array
    ld  c, a
    ld  hl, #_rx
    ld  de, #rl_pos
10$:
    ld  a, (hl+)
    ld  (de), a
    inc de
    ld  a, (hl-)
    ld  (de), a
    inc de
    ld  a, l
    add a, #64
    ld  l, a
    jr  nc, 11$
    inc h
11$:
    dec c
    jr  nz, 10$
    ld  b, #1                   ; k
20$:
    ld  a, (_rn_n)
    cp  a, b
    jr  z, 30$
    jr  c, 30$
    ld  hl, #_order             ; t = order[k], s = pos[t]
    ld  e, b
    ld  d, #0
    add hl, de
    ld  a, (hl)
    ld  (rl_t), a
    call pos_of
    ld  a, e
    ld  (rl_s), a
    ld  a, d
    ld  (rl_s + 1), a
    ld  c, b                    ; j = k
21$:
    ld  a, c
    or  a, a
    jr  z, 25$
    ld  hl, #_order - 1         ; p = pos[order[j - 1]]
    ld  e, c
    ld  d, #0
    add hl, de
    ld  a, (hl)
    push hl
    call pos_of
    ld  hl, #rl_s               ; s > p ?  (p - s borrows)
    ld  a, e
    sub a, (hl)
    inc hl
    ld  a, d
    sbc a, (hl)
    pop hl
    jr  nc, 25$                 ; s <= p: stop
    ld  a, (hl+)                ; order[j] = order[j - 1]
    ld  (hl), a
    dec c
    jr  21$
25$:
    ld  hl, #_order             ; order[j] = t
    ld  e, c
    ld  d, #0
    add hl, de
    ld  a, (rl_t)
    ld  (hl), a
    inc b
    jr  20$
30$:
    ld  b, #0                   ; ranks: rx[order[k]].rank = k
31$:
    ld  a, (_rn_n)
    cp  a, b
    ret z
    ld  hl, #_order
    ld  e, b
    ld  d, #0
    add hl, de
    ld  l, (hl)
    ld  h, #0
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    ld  de, #_rx + RANK
    add hl, de
    ld  (hl), b
    inc b
    jr  31$
