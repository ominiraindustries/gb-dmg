; gbe_tiles.s - VBlank copy of the staged tiles (gbe_tiles.c).
    .module gbe_tiles_asm
    .area _CODE

; void tile_copy16(uint8_t *dst, const uint8_t *src)    dst in DE (16-aligned VRAM tile), src in BC.
;   inc e only: a tile never crosses a 256-byte boundary. ~330 T (GBDK memcpy: ~480 T for 16 B,
;   and 4 of them with the other VBlank copies ran past VBlank in world_lab: vram_late).
_tile_copy16::
    ld  h, b
    ld  l, c
    .rept 15
    ld  a, (hl+)
    ld  (de), a
    inc e
    .endm
    ld  a, (hl)
    ld  (de), a
    ret
