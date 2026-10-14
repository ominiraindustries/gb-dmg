; gbe (map) - shared engine asm (harness/common/src). Measured and equivalence-tested in
; games/platformer. Call VRAM writers only in VBlank or with the LCD off.

    .module gbe_map
    .area _CODE

; uint8_t mt_at(uint16_t x, uint8_t y)        x in DE, y in A (__sdcccall(1)), returns A.
;   Metatile id at a world pixel: 0 above the level or below row 7 (pits),
;   map_wall_mt at x >= level_px_w (invisible wall), else level[((x >> 1) & 0xFFF8) | row].
;   The index trick: (x >> 4) << 3 == (x >> 1) & ~7. Reference C version: mt_at_c (gbe_map.c).
;   Cost: ~124 T (C version ~200 T). Clobbers AF C DE HL.
_mt_at::
    sub a, #32                  ; a = y - Y_BIAS
    jr  c, 1$                   ; above the level
    cp  a, #128
    jr  nc, 1$                  ; row >= 8: pit
    ld  c, a
    ld  hl, #_level_px_w
    ld  a, e
    sub a, (hl)
    inc hl
    ld  a, d
    sbc a, (hl)
    jr  nc, 2$                  ; x >= level_px_w
    srl d
    rr  e
    ld  a, e
    and a, #0xF8
    ld  e, a
    ld  a, c
    swap a
    and a, #0x0F                ; row
    or  a, e
    ld  l, a
    ld  h, d
    ld  de, #_level
    add hl, de
    ld  a, (hl)
    ret
1$:
    xor a, a                    ; MT_SKY
    ret
2$:
    ld  a, (_map_wall_mt)       ; wall metatile chosen by the game (map_load)
    ret

; uint8_t solid_at(uint16_t x, uint8_t y)     mt_attr[mt_at(x, y)] & ATTR_SOLID. ~190 T (C ~372 T).
_solid_at::
    call _mt_at
    ld  e, a
    ld  d, #0
    ld  hl, #_mt_attr
    add hl, de
    ld  a, (hl)
    and a, #0x80
    ret

; void gbe_column_tiles(const uint8_t *m, uint8_t h)    m in DE, h in A (__sdcccall(1)).
;   Fills col_buf[16] with one BG tile column of 8 metatiles: for each row r,
;   col_buf[2r] = mt_tiles[m[r]][h] (top), col_buf[2r+1] = mt_tiles[m[r]][2 + h] (bottom).
;   id * 4 has its low 2 bits clear, so "+ h" is an OR with no carry.
;   Reference: map_column_c (gbe_map.c). Cost ~1300 T (C ~3600 T).
_gbe_column_tiles::
    ld  c, a                    ; c = h (0 or 1)
    ld  b, #8                   ; rows
    ld  hl, #_col_buf
1$:
    push bc
    push hl                     ; dst
    ld  a, (de)                 ; metatile id
    inc de
    push de                     ; m
    ld  l, a
    ld  h, #0
    add hl, hl
    add hl, hl                  ; id * 4
    ld  a, l
    or  a, c
    ld  l, a                    ; + h
    ld  de, #_mt_tiles
    add hl, de
    ld  a, (hl+)
    inc hl
    ld  e, a                    ; top tile
    ld  d, (hl)                 ; bottom tile
    pop bc                      ; bc = m
    pop hl                      ; hl = dst
    ld  (hl), e
    inc hl
    ld  (hl), d
    inc hl
    ld  d, b
    ld  e, c                    ; de = m
    pop bc                      ; b = rows left, c = h
    dec b
    jr  nz, 1$
    ret
