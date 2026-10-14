; gbe (aim) - bullet spawn in asm. C reference: fire_c in gbe_aim.c (GBE_SELFTEST_AIM).

    .module gbe_aim

    .area _DATA
fr_x:   .ds 1
fr_y:   .ds 1
fr_dir: .ds 1
fr_k:   .ds 1

    .area _CODE

; uint8_t fire(uint8_t x, uint8_t y, uint8_t dir, uint8_t spd)
;   A = x, E = y, stack: dir, spd (1 byte each, removed here). First free record of
;   [fire_first, fire_first + fire_n) becomes a bullet: t = fire_t, position (x, y), velocity
;   aim_vx/aim_vy[spd * 32 + dir], s = dir, tm = aux = 0, tile/prop = fire_tile/fire_prop.
;   Returns the record index in A, 0xFF if the range is full.
_fire::
    ld  (fr_x), a
    ld  a, e
    ld  (fr_y), a
    ldhl sp, #2
    ld  a, (hl+)
    and a, #31
    ld  (fr_dir), a
    ld  b, a
    ld  a, (hl)
    and a, #3
    swap a
    add a, a                    ; spd * 32
    or  a, b
    ld  (fr_k), a               ; table index (< 128)
    pop hl
    inc sp
    inc sp
    push hl
    ld  a, (_fire_first)
    ld  c, a                    ; c = index
    call pool_addr              ; hl = &pool[first] (clobbers A, DE)
    ld  a, (_fire_n)
    ld  b, a
    ld  de, #16
1$:
    ld  a, (hl)
    or  a, a
    jr  z, 2$
    add hl, de
    inc c
    dec b
    jr  nz, 1$
    ld  a, #0xFF
    ret
2$:
    push bc
    ld  a, (_fire_t)
    ld  (hl+), a                ; t
    ld  a, (fr_x)
    ld  (hl+), a                ; x
    xor a, a
    ld  (hl+), a                ; xs
    ld  a, (fr_y)
    ld  (hl+), a                ; y
    xor a, a
    ld  (hl+), a                ; ys
    ld  a, (fr_k)
    add a, a                    ; * 2 (int16 tables), < 256
    ld  c, a
    ld  b, #0
    push hl
    ld  hl, #_aim_vx
    add hl, bc
    ld  a, (hl+)
    ld  e, a
    ld  d, (hl)                 ; de = vx
    ld  hl, #_aim_vy
    add hl, bc
    ld  a, (hl+)
    ld  c, a
    ld  b, (hl)                 ; bc = vy
    pop hl
    ld  a, e
    ld  (hl+), a
    ld  a, d
    ld  (hl+), a                ; vx
    ld  a, c
    ld  (hl+), a
    ld  a, b
    ld  (hl+), a                ; vy
    ld  a, (fr_dir)
    ld  (hl+), a                ; s = dir
    xor a, a
    ld  (hl+), a                ; tm
    ld  (hl+), a                ; aux
    ld  a, (_fire_tile)
    ld  (hl+), a
    ld  a, (_fire_prop)
    ld  (hl), a
    pop bc
    ld  a, c
    ret
