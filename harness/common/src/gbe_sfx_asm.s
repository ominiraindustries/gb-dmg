; gbe (sfx) - sfx() in asm. Same behaviour as the C version kept in gbe_sfx.c as sfx_c (the
; C one cost ~1000 T per call in games/shmup, which plays SHOT every 8 frames).
; sfx_t: ch, prio, frames, r[5]. Registers: ch1 NR10-14 at FF10, ch2 NR21-24 at FF16 (r[0] goes
; to the unused FF15), ch4 NR41-44 at FF20 (r[0] to the unused FF1F). Trigger written last.

    .module gbe_sfx_asm
    .area _CODE

; void sfx(uint8_t id)    id in A
_sfx::
    ld  l, a
    ld  h, #0
    add hl, hl
    add hl, hl
    add hl, hl
    ld  de, #_sfx_table
    add hl, de                  ; hl = &sfx_table[id]
    ld  a, (hl+)
    ld  c, a                    ; c = channel
    ld  b, #0
    ld  a, (hl+)
    ld  d, a                    ; d = prio
    ld  a, (hl+)
    ld  e, a                    ; e = frames
    push hl                     ; -> r[0]
    ld  hl, #_ch_busy
    add hl, bc
    ld  a, (hl)
    or  a, a
    jr  z, 1$
    push hl
    ld  hl, #_ch_prio
    add hl, bc
    ld  a, d
    cp  a, (hl)
    pop hl
    jr  nc, 1$
    pop hl                      ; busy with a higher priority effect
    ret
1$:
    ld  (hl), e                 ; ch_busy[ch] = frames
    ld  hl, #_ch_prio
    add hl, bc
    ld  (hl), d                 ; ch_prio[ch] = prio
    ld  a, c
    ld  c, #0x10
    dec a
    jr  z, 2$
    ld  c, #0x15
    dec a
    jr  z, 2$
    ld  c, #0x1F
2$:
    pop hl
    .rept 5
    ld  a, (hl+)
    ldh (c), a
    inc c
    .endm
    ret
