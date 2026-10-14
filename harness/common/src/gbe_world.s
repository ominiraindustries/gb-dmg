; gbe_world.s - asm queries of gbe_world.c (C reference: wmt_at_c; the selftest compares them).
; Always listed together with gbe_world.c in common_src.
    .module gbe_world_asm
    .area _CODE

; uint8_t wmt_at(uint8_t x, uint8_t y)    x in A, y in E; returns the metatile in A.
;   Cache position = sector - (wosx, wosy) in 0..2 on both axes, else the map border; slot >= 0xFE
;   (outside the map / not loaded) = border. ~140 T (C: ~390 T).
_wmt_at::
    ld  c, a                    ; c = x
    swap a
    and a, #0x0F                ; x >> 4
    ld  hl, #_wosx
    sub a, (hl)
    cp  a, #3
    jr  nc, 9$
    ld  b, a                    ; b = rx
    ld  a, e
    swap a
    and a, #0x0F
    ld  hl, #_wosy
    sub a, (hl)
    cp  a, #3
    jr  nc, 9$
    ld  l, a
    add a, a
    add a, l
    add a, b                    ; ry * 3 + rx
    add a, #<_wslot
    ld  l, a
    ld  a, #0
    adc a, #>_wslot
    ld  h, a
    ld  a, (hl)                 ; slot
    cp  a, #0xFE
    jr  nc, 9$
    ld  b, a
    ld  a, e
    swap a
    and a, #0xF0                ; (y & 15) << 4
    ld  e, a
    ld  a, c
    and a, #0x0F
    or  a, e
    ld  l, a
    ld  h, b                    ; hl = slot * 256 + cell
    ld  bc, #_wcache
    add hl, bc
    ld  a, (hl)
    ret
9$:
    ld  a, (#_wmap + 2)         ; world_map_t.border
    ret

; uint8_t wprep_cell(uint8_t x, uint8_t y)    x in A, y in E.
;   Queue cell (x, y) for the next VBlank in slot wprep_n (BG address + its 4 tiles), wprep_n++,
;   return 1; return 0 (nothing queued) if its sector is still loading. C reference: wprep_cell_c.
_wprep_cell::
    ld  c, a                    ; c = x
    ld  d, e                    ; d = y
    swap a
    and a, #0x0F
    ld  hl, #_wosx
    sub a, (hl)
    cp  a, #3
    jr  nc, 5$
    ld  b, a
    ld  a, d
    swap a
    and a, #0x0F
    ld  hl, #_wosy
    sub a, (hl)
    cp  a, #3
    jr  nc, 5$
    ld  l, a
    add a, a
    add a, l
    add a, b
    add a, #<_wslot
    ld  l, a
    ld  a, #0
    adc a, #>_wslot
    ld  h, a
    ld  a, (hl)
    cp  a, #0xFF
    jr  z, 8$                   ; sector loading: wait
    cp  a, #0xFE
    jr  z, 5$
    ld  b, a
    ld  a, d
    swap a
    and a, #0xF0
    ld  l, a
    ld  a, c
    and a, #0x0F
    or  a, l
    ld  l, a
    ld  a, b
    add a, #>_wcache
    ld  h, a
    ld  a, l
    add a, #<_wcache
    ld  l, a
    jr  nc, 4$
    inc h
4$:
    ld  a, (hl)
    jr  6$
5$:
    ld  a, (#_wmap + 2)         ; border
6$:
    ld  e, a                    ; e = metatile
    ld  a, (#_wprep_n)
    ld  b, a                    ; b = n
    add a, a
    add a, #<_wprep_dst
    ld  l, a
    ld  a, #0
    adc a, #>_wprep_dst
    ld  h, a                    ; hl = &wprep_dst[n]
    ld  a, d
    and a, #3
    rrca
    rrca                        ; (y & 3) << 6
    ld  (hl), a
    ld  a, c
    and a, #0x0F
    add a, a                    ; (x & 15) << 1
    or  a, (hl)
    ld  (hl+), a                ; low byte of 0x9800 + (y & 15) * 64 + (x & 15) * 2
    ld  a, d
    and a, #0x0F
    srl a
    srl a
    add a, #0x98
    ld  (hl), a                 ; high byte
    ld  a, b
    add a, a
    add a, a
    add a, #<_wprep_tiles
    ld  c, a
    ld  a, #0
    adc a, #>_wprep_tiles
    ld  b, a                    ; bc = wprep_tiles[n]
    ld  l, e
    ld  h, #0
    add hl, hl
    add hl, hl
    ld  de, #_wmt_tiles
    add hl, de                  ; hl = wmt_tiles[mt]
    ld  a, (hl+)
    ld  (bc), a
    inc bc
    ld  a, (hl+)
    ld  (bc), a
    inc bc
    ld  a, (hl+)
    ld  (bc), a
    inc bc
    ld  a, (hl)
    ld  (bc), a
    ld  hl, #_wprep_n
    inc (hl)
    ld  a, #1
    ret
8$:
    xor a, a
    ret

; void wcopy128(uint8_t *dst, const uint8_t *src)    dst in DE, src in BC. 128 bytes, ~3.1k T
;   (GBDK memcpy through bank_memcpy: ~4.2k T for the same half sector).
_wcopy128::
    ld  h, b
    ld  l, c
    ld  c, #16
1$:
    .rept 8
    ld  a, (hl+)
    ld  (de), a
    inc de
    .endm
    dec c
    jr  nz, 1$
    ret
