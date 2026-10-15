; gbe: the raster LCD handler (see gbe_raster.c). Called at LYC = line - 1 of the next split: waits
; for that line's HBlank, writes SCX (taking effect on `line`), arms the next split.
    .module gbe_raster
    .globl _raster_isr, _rs_n, _rs_line, _rs_scx, _rs_i

    .area _CODE

_raster_isr::
    ld  a, (_rs_i)
    ld  hl, #_rs_n
    cp  a, (hl)
    ret nc                      ; no split left this frame
    ld  e, a
    ld  d, #0
    ld  hl, #_rs_scx
    add hl, de
    ld  b, (hl)                 ; B = SCX of the next band
1$:
    ldh a, (0x41)               ; STAT: wait for mode 0 (HBlank) of line - 1
    and a, #3
    jr  nz, 1$
    ld  a, b
    ldh (0x43), a               ; SCX
    ld  a, e                    ; next split
    inc a
    ld  (_rs_i), a
    ld  hl, #_rs_n
    cp  a, (hl)
    jr  nc, 2$
    ld  e, a
    ld  hl, #_rs_line
    add hl, de
    ld  a, (hl)
    dec a
    ldh (0x45), a               ; LYC
    ret
2$:
    ld  a, #0xFF
    ldh (0x45), a
    ret
