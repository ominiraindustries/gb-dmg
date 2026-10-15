; gbe: the inner loop of vwf_draw (gbe_vwf.c): OR one glyph (16 bytes in vb_glyph) into 1 or 2 strip
; tiles: x = (byte << vb_first) & 0xFF; dst0 |= x >> vb_sh; dst1 (if not 0) |= x << (8 - vb_sh).
; As one shift: (byte & (0xFF >> first)) << (8 + first - sh), high byte to dst0, low byte to dst1,
; done by jumping into a chain of add hl,hl (8 T per bit). Zero bytes are skipped and a byte equal to
; the previous one reuses its result (2bpp fonts: both planes alike).
; Measured: C ~20k T per glyph; the first asm (bit loops per byte) 8k; this ~3k (happyvalley's
; commentary letter frames went over 154 lines with 8k).
; void vwf_blit(void)   reads vb_glyph[16], vb_first, vb_sh, vb_dst0, vb_dst1
    .module gbe_vwf_blit
    .globl _vwf_blit, _vb_glyph, _vb_first, _vb_sh, _vb_dst0, _vb_dst1

    .area _DATA
_vb_glyph:: .ds 16
_vb_first:: .ds 1
_vb_sh::    .ds 1
_vb_dst0::  .ds 2
_vb_dst1::  .ds 2
vb_k:       .ds 1
vb_mask:    .ds 1
vb_entry:   .ds 2
vb_prev:    .ds 1
vb_b:       .ds 1
vb_c:       .ds 1

    .area _CODE

_vwf_blit::
    ld  a, (_vb_first)          ; mask = 0xFF >> first
    ld  b, a
    ld  c, #0xFF
    inc b
1$:
    dec b
    jr  z, 2$
    srl c
    jr  1$
2$:
    ld  a, c
    ld  (vb_mask), a
    ld  a, (_vb_sh)             ; s = 8 + first - sh (1..15): entry = chain_end - s
    ld  b, a
    ld  a, (_vb_first)
    add a, #8
    sub a, b
    ld  c, a
    ld  hl, #chain_end
    ld  a, l
    sub a, c
    ld  l, a
    ld  a, h
    sbc a, #0
    ld  (vb_entry + 1), a
    ld  a, l
    ld  (vb_entry), a
    xor a, a
    ld  (vb_k), a
    ld  (vb_prev), a
10$:
    ld  a, (vb_k)
    ld  e, a
    ld  d, #0
    ld  hl, #_vb_glyph
    add hl, de
    ld  a, (hl)
    or  a, a
    jr  z, 20$                  ; nothing to OR
    ld  hl, #vb_prev
    cp  a, (hl)
    jr  z, 12$                  ; same byte as the last one shifted: reuse vb_b / vb_c
    ld  (hl), a
    ld  hl, #vb_mask
    and a, (hl)
    ld  l, a
    ld  h, #0
    ld  bc, #11$                ; call the chain at its entry: push the return, push the entry, ret
    push bc
    ld  a, (vb_entry)
    ld  c, a
    ld  a, (vb_entry + 1)
    ld  b, a
    push bc
    ret
11$:
    ld  a, h
    ld  (vb_b), a
    ld  a, l
    ld  (vb_c), a
12$:
    ld  hl, #_vb_dst0           ; dst0[k] |= B (DE = k)
    ld  a, (hl+)
    ld  h, (hl)
    ld  l, a
    add hl, de
    ld  a, (vb_b)
    or  a, (hl)
    ld  (hl), a
    ld  hl, #_vb_dst1           ; dst1[k] |= C (if dst1)
    ld  a, (hl+)
    ld  h, (hl)
    ld  l, a
    or  a, h
    jr  z, 20$
    add hl, de
    ld  a, (vb_c)
    or  a, (hl)
    ld  (hl), a
20$:
    ld  hl, #vb_k
    inc (hl)
    ld  a, (hl)
    cp  a, #16
    jr  c, 10$
    ret

chain:                          ; 15 x add hl,hl (1 byte each), entered s from the end
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
chain_end:
    ret
