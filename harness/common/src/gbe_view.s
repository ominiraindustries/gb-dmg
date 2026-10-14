; gbe (view) - piece blitter for the first-person view. C reference: view_blit_c (gbe_view.c),
; checked by gbe_selftest.c (GBE_SELFTEST_VIEW) on every piece of the game's view.pcs.

    .module gbe_view

    .area _DATA
vc_pox:  .ds 2
vc_poy:  .ds 2
vc_i:    .ds 1
vc_cx:   .ds 1
vc_c:    .ds 1

    .area _CODE

; void view_blit(const uint8_t *p)   p in DE: row0, rows, then per row: col, len, tiles[len].
;   Copies each row's run into view_buf (20 bytes per row). Unrolled by 4: ~28 T per tile
;   (the 1-tile loop cost 40).
_view_blit::
    ld  a, (de)                 ; row0
    inc de
    ld  l, a
    ld  h, #0
    add hl, hl
    add hl, hl                  ; * 4
    ld  b, h
    ld  c, l
    add hl, hl
    add hl, hl                  ; * 16
    add hl, bc                  ; * 20
    ld  bc, #_view_buf
    add hl, bc
    ld  a, (de)                 ; rows
    inc de
    or  a, a
    ret z
    ld  b, a
1$:
    push hl
    ld  a, (de)                 ; col
    inc de
    add a, l
    ld  l, a
    jr  nc, 2$
    inc h
2$:
    ld  a, (de)                 ; len
    inc de
    ld  c, a
    and a, #3                   ; len % 4 single copies first
    jr  z, 6$
7$:
    push af
    ld  a, (de)
    inc de
    ld  (hl+), a
    pop af
    dec a
    jr  nz, 7$
6$:
    srl c
    srl c                       ; len / 4 groups of 4 (~28 T per tile)
    jr  z, 4$
3$:
    .rept 4
    ld  a, (de)
    inc de
    ld  (hl+), a
    .endm
    dec c
    jr  nz, 3$
4$:
    pop hl
    ld  a, l
    add a, #20
    ld  l, a
    jr  nc, 5$
    inc h
5$:
    dec b
    jr  nz, 1$
    ret

; void view_copy240(uint8_t *dst, const uint8_t *src)   dst in DE, src in BC: 240 bytes.
;   Unrolled 24 x 10 bytes, ~24 T per byte (~5.8k T; the BG piece blit cost ~11.7k).
_view_copy240::
    ld  h, b
    ld  l, c                    ; hl = src
    ld  c, #24
1$:
    .rept 10
    ld  a, (hl+)
    ld  (de), a
    inc de
    .endm
    dec c
    jr  nz, 1$
    ret

; void bgbuf_copy_rows(uint8_t *dst, const uint8_t *src, uint8_t rows)
;   dst in DE (32-aligned BG map row), src in BC (20 bytes per row), rows on the stack.
;   20 T per tile (inc e: a 20-tile run never crosses the 32-byte row), then dst += 32.
_bgbuf_copy_rows::
    ldhl sp, #2
    ld  a, (hl)
    pop hl
    inc sp
    push hl
    push af                     ; rows
    ld  h, b
    ld  l, c                    ; hl = src
    pop af
    ld  b, a
2$:
    .rept 20
    ld  a, (hl+)
    ld  (de), a
    inc e
    .endm
    ld  a, e
    add a, #12                  ; 20 written, +12 = next row
    ld  e, a
    jr  nc, 3$
    inc d
3$:
    dec b
    jr  nz, 2$
    ret

; void view_classify(void)   inputs vc_x, vc_y, vc_f, view_map (16x16 cell types, index
;   y * 16 + x) and view_class (cell type -> VIEW_*). view_cls[i] = class of the cell at
;   (x + ox[f][i], y + oy[f][i]), off the map ((x | y) & 0xF0) = VIEW_WALL; view_solid = 19-bit
;   mask of non-free slots. Same result as calling view_cell() per slot (view_compose_c), which
;   cost ~420 T per slot through the C call; ~90 T here.
_view_classify::
    ld  a, (_vc_f)
    ld  l, a
    ld  h, #0
    ld  b, h
    ld  c, l
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, bc
    add hl, bc
    add hl, bc                  ; f * 19
    push hl
    ld  bc, #_view_lay_ox
    add hl, bc
    ld  a, l
    ld  (vc_pox), a
    ld  a, h
    ld  (vc_pox + 1), a
    pop hl
    ld  bc, #_view_lay_oy
    add hl, bc                  ; hl = oy row
    ld  a, (vc_pox)
    ld  e, a
    ld  a, (vc_pox + 1)
    ld  d, a                    ; de = ox row
    ld  bc, #_view_cls
    ld  a, #19
    ld  (vc_i), a
1$:
    ld  a, (_vc_y)
    add a, (hl)                 ; cy
    inc hl
    push hl
    ld  h, a
    ld  a, (de)
    inc de
    push de
    ld  d, a
    ld  a, (_vc_x)
    add a, d                    ; cx
    ld  l, a
    or  a, h
    and a, #0xF0
    ld  a, #1                   ; VIEW_WALL off the map
    jr  nz, 2$
    ld  a, h
    swap a
    or  a, l                    ; y * 16 + x
    ld  l, a
    ld  a, (_view_map)
    add a, l
    ld  l, a
    ld  a, (_view_map + 1)
    adc a, #0
    ld  h, a
    ld  a, (hl)                 ; cell type
    ld  hl, #_view_class + 0
    ld  e, a
    ld  a, (hl+)
    ld  h, (hl)
    add a, e
    ld  l, a
    jr  nc, 3$
    inc h
3$:
    ld  a, (hl)                 ; class
2$:
    ld  (bc), a
    inc bc
    pop de
    pop hl
    ld  a, (vc_i)
    dec a
    ld  (vc_i), a
    jr  nz, 1$
    ld  hl, #_view_cls + 18     ; slot 18 first: after 19 left shifts slot 0 is bit 0
    ld  b, #19
    ld  c, #0
    ld  d, c
    ld  e, c
4$:
    ld  a, (hl-)
    add a, #0xFF                ; carry = slot not free
    rl  e
    rl  d
    rl  c
    dec b
    jr  nz, 4$
    ld  a, e
    ld  (_view_solid), a
    ld  a, d
    ld  (_view_solid + 1), a
    ld  a, c
    ld  (_view_solid + 2), a
    ret

; blit piece A (id): view_blit(view_pcs + view_piece[A])
blit_id:
    add a, a
    ld  e, a
    ld  d, #0
    ld  hl, #_view_piece
    add hl, de
    ld  a, (hl+)
    ld  h, (hl)
    ld  l, a
    ld  de, #_view_pcs
    add hl, de
    ld  d, h
    ld  e, l
    jp  _view_blit

; void view_paint(void)   slots in painting order: skip free and fully covered slots (masks
;   view_occ), choose wall / door (+ lock) / stairs for the center fronts, blit.
_view_paint::
    xor a, a
    ld  (vc_i), a
1$:
    ld  a, (vc_i)
    ld  e, a
    ld  d, #0
    ld  hl, #_view_cls
    add hl, de
    ld  a, (hl)
    or  a, a
    jp  z, 9$                   ; free
    ld  (vc_c), a
    ld  hl, #_view_occ_first
    add hl, de
    ld  a, (hl+)
    ld  b, a                    ; first mask
    ld  a, (hl)
    sub a, b
    jr  z, 5$                   ; no masks: visible
    ld  c, a                    ; c = masks to test
    ld  l, b
    ld  h, #0
    ld  d, h
    ld  e, l
    add hl, hl
    add hl, de                  ; first * 3
    ld  de, #_view_occ
    add hl, de
2$:
    ld  a, (_view_solid)
    and a, (hl)
    cp  a, (hl)
    inc hl
    jr  nz, 31$
    ld  a, (_view_solid + 1)
    and a, (hl)
    cp  a, (hl)
    inc hl
    jr  nz, 32$
    ld  a, (_view_solid + 2)
    and a, (hl)
    cp  a, (hl)
    jp  z, 9$                   ; every slot of this mask is solid: hidden
    inc hl
    jr  33$
31$:
    inc hl
32$:
    inc hl
33$:
    dec c
    jr  nz, 2$
5$:
    ld  a, (vc_i)
    ld  e, a
    ld  d, #0
    ld  hl, #_view_lay_l
    add hl, de
    ld  a, (hl)
    or  a, a
    jr  nz, 7$                  ; not a center slot
    ld  hl, #_view_lay_d
    add hl, de
    ld  a, (hl)
    or  a, a
    jr  z, 7$
    ld  e, a                    ; e = depth (d = 1..3), d = 0
    ld  a, (vc_c)
    cp  a, #1                   ; VIEW_WALL
    jr  z, 7$
    cp  a, #4                   ; VIEW_DOWN
    jr  z, 6$
    ld  hl, #_view_door_p       ; DOOR, LOCKED, UP
    add hl, de
    ld  a, (hl)
    push de
    call blit_id
    pop de
    ld  a, (vc_c)
    cp  a, #3                   ; VIEW_LOCKED
    jr  z, 61$
    cp  a, #5                   ; VIEW_UP
    jr  nz, 9$
61$:
    ld  hl, #_view_lock_p
    add hl, de
    ld  a, (hl)
    call blit_id
    jr  9$
6$:
    ld  hl, #_view_stair_p
    add hl, de
    ld  a, (hl)
    call blit_id
    jr  9$
7$:
    ld  a, (vc_i)
    ld  e, a
    ld  d, #0
    ld  hl, #_view_lay_p
    add hl, de
    ld  a, (hl)
    call blit_id
9$:
    ld  a, (vc_i)
    inc a
    ld  (vc_i), a
    cp  a, #19
    jp  nz, 1$
    ret

