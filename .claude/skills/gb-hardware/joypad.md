# Joypad (P1/JOYP, $FF00)

## Register

| Bit | Name | R/W | Meaning |
|---|---|---|---|
| 7-6 | - | - | unused (read 1; boot value $CF) |
| 5 | Select buttons | R/W | 0 = action buttons (Start, Select, B, A) appear in bits 3-0 |
| 4 | Select d-pad | R/W | 0 = directions appear in bits 3-0 |
| 3 | Start / Down | R | **0 = pressed** |
| 2 | Select / Up | R | 0 = pressed |
| 1 | B / Left | R | 0 = pressed |
| 0 | A / Right | R | 0 = pressed |

- The 8 buttons form a 2x4 matrix: select a row by writing bit 4 or 5 low, then read bits 3-0.
- Write $20 -> d-pad selected (bit 4 = 0). Write $10 -> buttons selected (bit 5 = 0).
  Write $30 -> nothing selected; low nibble reads $F.
- Active low: pressed = 0. Invert (`~x & $0F`) to get active-high bits.
- Selecting both rows ($00) ORs the rows together (a held line hides presses on the other row);
  only useful for STOP wake-up / joypad interrupt.

Source: reference/pandocs/src/Joypad_Input.md

## Reading procedure

Pan Docs: most programs read the port several times in a row after selecting a row; the extra
reads are a delay so the inputs stabilize, and only the last value is used. (The exact number of
reads is not specified by Pan Docs; common practice in Nintendo-style routines is a couple of reads
for the d-pad and more (~6) for buttons - treat as convention, not a measured requirement.)

```
read_joypad:            ; result in A: bit7..0 = Down Up Left Right Start Select B A, 1 = pressed
    ld   a, $20         ; select d-pad
    ldh  [$FF00], a
    ldh  a, [$FF00]
    ldh  a, [$FF00]     ; settle
    cpl
    and  $0F
    swap a
    ld   b, a           ; d-pad in high nibble
    ld   a, $10         ; select buttons
    ldh  [$FF00], a
    ldh  a, [$FF00]
    ldh  a, [$FF00]
    ldh  a, [$FF00]
    ldh  a, [$FF00]
    ldh  a, [$FF00]
    ldh  a, [$FF00]     ; settle
    cpl
    and  $0F
    or   b
    ld   b, a
    ld   a, $30         ; deselect both rows
    ldh  [$FF00], a
    ld   a, b
    ret
```

Note: that nibble order (buttons low, d-pad high) is the hardware.inc/RGBDS convention. GBDK's
`joypad()` uses a different layout: `J_RIGHT $01, J_LEFT $02, J_UP $04, J_DOWN $08, J_A $10,
J_B $20, J_SELECT $40, J_START $80` (active high, "follows Nintendo's guidelines"). Read it **once
per frame** into a variable and test bits from that variable.

## Edge detection (once per frame)

```c
static uint8_t keys, prev_keys, pressed, released;
void input_update(void) {
    prev_keys = keys;
    keys      = joypad();
    pressed   = keys & ~prev_keys;   // went down this frame
    released  = ~keys & prev_keys;   // went up this frame
}
```

- Use `pressed` for menu actions, jump start, shots; use `keys` for held actions (walk, variable
  jump height while A held).
- Auto-repeat for menus: counter reset on `pressed`, re-fire every N frames after an initial delay.
- Do not call `joypad()` multiple times per frame from different places; inconsistent snapshots
  break edge detection. `waitpad()` busy-loops without HALT (burns battery).

## Bounce

- Pan Docs (joypad interrupt section): pressing a button usually produces one or more high->low
  transitions due to switch bounce (GBA SP reportedly does not bounce). This matters for the
  joypad interrupt and for sampling faster than the bounce settles.
- Polling once per frame (~16.7 ms) usually rides over bounce, so frame-based edge detection
  needs no extra debounce in practice (engineering judgment, not a Pan Docs measurement). If a
  physical unit shows double presses, require the state to be stable for 2 consecutive frames.
- Pressing opposite directions simultaneously (Left+Right, Up+Down) is possible on worn pads or
  emulators; game logic should handle or mask it (convention).

Source: reference/pandocs/src/Interrupt_Sources.md, reference/pandocs/src/Joypad_Input.md

## Soft reset convention

Many games reset on A+B+Select+Start held together (convention, not hardware). Debounce it with
the frame snapshot and require release before acting again.
