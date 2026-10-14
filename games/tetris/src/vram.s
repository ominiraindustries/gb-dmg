; Fast VRAM row copy for the well (10 tiles). Call only in VBlank or with the LCD off.
;
; void vram_copy10(uint8_t *dst, const uint8_t *src)
;   dst in DE, src in BC (__sdcccall(1)), no stack args, clobbers AF HL DE.
;   dst must not cross a 256-byte page within the 10 bytes (true for a BG map row segment
;   starting at a column <= 22), so only E is incremented.
;
; Cost: 20 T per tile (ld a,(hl+) 8 + ld (de),a 8 + inc e 4), ~228 T per row with the
; call and setup, vs ~760 T for the C loop in vram_row() (SDCC keeps the counter on the stack).

    .module vram
    .area _CODE

_vram_copy10::
    ld  h, b
    ld  l, c
    ld  a, (hl+)
    ld  (de), a
    inc e
    ld  a, (hl+)
    ld  (de), a
    inc e
    ld  a, (hl+)
    ld  (de), a
    inc e
    ld  a, (hl+)
    ld  (de), a
    inc e
    ld  a, (hl+)
    ld  (de), a
    inc e
    ld  a, (hl+)
    ld  (de), a
    inc e
    ld  a, (hl+)
    ld  (de), a
    inc e
    ld  a, (hl+)
    ld  (de), a
    inc e
    ld  a, (hl+)
    ld  (de), a
    inc e
    ld  a, (hl)
    ld  (de), a
    ret
