; gbe: small helpers SDCC gets wrong. SDCC 4.5 sometimes compiles (uint16_t)r << 5 (r an u8 local) in
; 8 bits (swap / rlca / and 0xE0: rows >= 8 of a BG map wrap onto rows 0-7; seen in happyvalley's
; race view and mazmorra, see the gbdk skill gotchas). Use these for map row offsets.
; uint16_t gbe_row32(uint8_t r)   BC = r * 32
    .module gbe_util
    .globl _gbe_row32

    .area _CODE

_gbe_row32::
    ld  c, a
    ld  b, #0
    sla c
    rl  b
    sla c
    rl  b
    sla c
    rl  b
    sla c
    rl  b
    sla c
    rl  b
    ret
