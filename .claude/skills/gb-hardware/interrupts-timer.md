# Interrupts, HALT/STOP, timer and DIV

## IME, IE, IF

| Item | Where | Notes |
|---|---|---|
| IME | CPU-internal flag, not readable | `ei` sets (delayed by one instruction), `di` clears, `reti` = `ei`+`ret` (no delay issue), cleared automatically when an ISR is dispatched. 0 when the game starts |
| IE ($FFFF) | bits 4-0 enable Joypad, Serial, Timer, LCD, VBlank | R/W |
| IF ($FF0F) | bits 4-0 request flags | R/W; set by hardware on rising edge of each request line; writable to request/discard manually. Boot value $E1 (unused bits 7-5 read 1) |

An interrupt is serviced only if IME = 1 and (IE & IF) bit set. Otherwise the IF bit stays set and
the request waits. **Clear stale IF bits before enabling an interrupt** (e.g. `IF = 0` before
`ei`) if you do not want an immediately pending one.

`ei` delay: `ei` immediately followed by `di` allows no interrupt in between.

Source: reference/pandocs/src/Interrupts.md

## Sources, vectors, priority

| Bit | Source | Vector | Raised when |
|---|---|---|---|
| 0 | VBlank | $40 | PPU enters mode 1 (LY=144), ~59.7 times/s; VBlank lasts ~1.1 ms |
| 1 | STAT | $48 | rising edge of OR of enabled STAT sources (LYC=LY, mode 0, 1, 2) |
| 2 | Timer | $50 | TIMA overflows (reloaded from TMA) |
| 3 | Serial | $58 | 8 serial clocks after a transfer starts |
| 4 | Joypad | $60 | any P1 bit 0-3 goes high->low (with its row selected); bouncy |

Priority when several are pending and allowed: bit 0 (VBlank) first ... bit 4 (Joypad) last.

STAT blocking: a source going high while the STAT line is already high produces no interrupt.

Joypad interrupt is mostly useful to wake from STOP; with both rows selected a press on the other
row that shares a held line is not detected.

Source: reference/pandocs/src/Interrupt_Sources.md

## Dispatch and ISR timing

1. IF bit for the serviced interrupt and IME are cleared.
2. 2 wait M-cycles, PC pushed (2 M-cycles), PC = vector (1 M-cycle): **5 M-cycles** total, after the
   current instruction completes.
3. Handler typically pushes registers, does work, pops, `reti`.

Nested interrupts: execute `ei` inside a handler to allow others (any priority) to interrupt it.
Keep handlers short; long VBlank handlers eat the 1140 M-cycle VBlank budget.

GBDK: `add_VBL(fn)`, `add_LCD(fn)`, `add_TIM(fn)`, then `set_interrupts(VBL_IFLAG | LCD_IFLAG | ...)`
inside `CRITICAL { }` / `disable_interrupts()`...`enable_interrupts()`. `vsync()` (alias
`wait_vbl_done()`) halts until the next VBlank.

Source: reference/pandocs/src/Interrupts.md

## HALT

- Stops the CPU until (IE & IF) != 0. Saves power (Pan Docs: 5-50%+ battery). Preferred way to wait
  for VBlank instead of polling LY.
- IME = 1: wake, service ISR, continue after `halt`.
- IME = 0, nothing pending at `halt`: wake when something becomes pending; no ISR is called; execution
  continues after `halt` (use this for "di + halt" sync to a STAT mode).
- IME = 0 and something already pending: **HALT bug** - `halt` exits immediately and PC fails to
  increment, so the byte after `halt` is executed twice. Special cases: `ei` ; `halt` with a pending
  interrupt -> ISR runs, returns to the `halt`, which then waits again. `halt` followed by `rst` ->
  the rst return address points to the rst itself.
- Idiom (Pan Docs): VBlank ISR sets `vblank_flag`; main loop does `halt`, then checks the flag and
  loops if zero (other enabled interrupts also wake `halt`). Caveat from the source: a VBlank landing
  between the flag test and the jump goes unnoticed and costs one extra frame. If only VBlank is
  enabled, a bare `halt` suffices. ISRs must return with `reti` (or `ei`) or halt-waiting deadlocks.

Source: reference/pandocs/src/halt.md, reference/pandocs/src/Reducing_Power_Consumption.md

## STOP

- Very low power standby; terminated by a P10-P13 line going low -> select rows via P1 ($00, $10
  or $20) beforehand.
- DMG: **turn the LCD off (in VBlank) before STOP**; Pan Docs warns that otherwise the LCD may be
  damaged / show a black line (the source sentence is garbled: "disabling the LCD before invoking
  STOP leaves the LCD enabled" - the intended rule is: never STOP with the LCD on).
- STOP behaviour is complex (can act as NOP, HALT, or eat the next byte depending on state);
  no licensed DMG game uses it. DIV is reset by STOP. Avoid unless needed (auto-sleep feature).

Source: reference/pandocs/src/Reducing_Power_Consumption.md, reference/pandocs/src/Timer_and_Divider_Registers.md

## Timer registers

| Reg | Addr | Function |
|---|---|---|
| DIV | $FF04 | Upper 8 bits of the 16-bit system counter (which increments every M-cycle). Increments at 16384 Hz. Any write -> 0. Reset by STOP |
| TIMA | $FF05 | Incremented at TAC rate when enabled; on overflow reloaded from TMA and timer IRQ requested |
| TMA | $FF06 | Reload value. IRQ period = (256 - TMA) TIMA ticks |
| TAC | $FF07 | bit 2 = enable TIMA (DIV always counts); bits 1-0 = clock select |

| TAC 1-0 | Increment every | Frequency (DMG) |
|---|---|---|
| 00 | 256 M-cycles | 4096 Hz |
| 01 | 4 M-cycles | 262144 Hz |
| 10 | 16 M-cycles | 65536 Hz |
| 11 | 64 M-cycles | 16384 Hz |

Example: TAC = %100 (4096 Hz), TMA = 256 - 64 = 192 -> 64 Hz timer interrupt.
Timer IRQ is not synced to the LCD: it jitters raster effects and must not fire during OAM DMA.
A common use: driving a music driver at a rate independent of VBlank.

Source: reference/pandocs/src/Timer_and_Divider_Registers.md

## Obscure timer behaviour (summary)

- TIMA ticks on a falling edge of a selected system-counter bit (via a multiplexer), so:
  - Writing DIV can produce an extra TIMA tick (and an early DIV-APU tick -> audio envelope/length/
    sweep timing shifts) if the selected bit was 1.
  - Changing TAC clock select from a bit that is 1 to one that is 0 sends a tick.
  - DMG only: disabling the timer while the selected bit is 1 sends one tick.
- On overflow TIMA reads $00 for one M-cycle; TMA is copied and IF.2 set one M-cycle later.
  Writing TIMA during that cycle cancels the reload and the IRQ; writing TIMA on the next cycle is
  ignored; writing TMA on that next cycle loads the new TMA value.
- TMA write on the same M-cycle as a reload: Timer_and_Divider_Registers.md says the old value is
  loaded, Timer_Obscure_Behaviour.md says a TMA write in the reload cycle is copied too. The two
  pages disagree - never depend on it.
- Practical rule: configure TMA/TAC once with the timer stopped, reset DIV only at init, never
  rely on DIV for timing after writing it. DIV is fine as a cheap entropy source for RNG seeding
  when sampled at a human input event.

Source: reference/pandocs/src/Timer_Obscure_Behaviour.md
