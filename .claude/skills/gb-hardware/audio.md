# Audio (APU)

## Channels

| Ch | Type | Registers | Sweep | Volume control | Length max |
|---|---|---|---|---|---|
| CH1 | Pulse + period sweep | NR10-NR14 ($FF10-$FF14) | yes | 4-bit + envelope | 64 ticks |
| CH2 | Pulse | NR21-NR24 ($FF16-$FF19) | no | 4-bit + envelope | 64 ticks |
| CH3 | Wave (32 x 4-bit samples) | NR30-NR34 ($FF1A-$FF1E), wave RAM $FF30-$FF3F | no | 0/25/50/100% | 256 ticks |
| CH4 | Noise (LFSR) | NR41-NR44 ($FF20-$FF23) | no | 4-bit + envelope | 64 ticks |

Frame sequencer ("DIV-APU") ticks at 512 Hz from DIV bit 4 falling edge: envelope 64 Hz, length
256 Hz, CH1 sweep 128 Hz. **Writing DIV disturbs these** (can clock them early).

Source: reference/pandocs/src/Audio.md, reference/pandocs/src/Audio_details.md

## Global registers

| Reg | Bits | Meaning |
|---|---|---|
| NR52 $FF26 | 7 | APU power (R/W). 0 = all APU regs cleared and read-only (except NR52; on DMG also length timers in NRx1 stay writable); wave RAM unaffected. ~16% power saving |
| | 3-0 | CH4..CH1 active (read-only; writing does NOT start/stop channels) |
| NR51 $FF25 | 7-4 | CH4, CH3, CH2, CH1 -> left |
| | 3-0 | CH4, CH3, CH2, CH1 -> right |
| NR50 $FF24 | 7 / 3 | VIN left / right (keep 0) |
| | 6-4 / 2-0 | left / right master volume 0-7 (= x1..x8; never mutes) |

Init: `NR52 = $80` first, then `NR50 = $77`, `NR51 = $FF`, then channel registers. (Boot leaves
NR52=$F1, NR50=$77, NR51=$F3.) Speaker is mono (L+R merged); stereo only on headphones.

A channel turns off when: its length timer expires (if enabled), CH1 sweep overflows, or its DAC
is turned off. Envelope reaching 0 does NOT turn it off.

Source: reference/pandocs/src/Audio_Registers.md

## DACs and pops

- DAC of CH1/2/4 is on iff `NRx2 & $F8 != 0` (i.e. initial volume > 0 or envelope up). CH3 DAC =
  NR30 bit 7. Triggering with DAC off does nothing.
- Turning a DAC on/off, changing NR51 routing, or changing NR50 causes a pop (DC offset change).
- Silence a channel without a pop: write `$08` to NRx2 (volume 0, envelope up -> DAC stays on), then
  `$80` to NRx4 (retrigger to reload).

Source: reference/pandocs/src/Audio_details.md

## CH1 / CH2 (pulse)

| Reg | Bits | Meaning |
|---|---|---|
| NR10 $FF10 (CH1 only) | 6-4 | Sweep pace, in 128 Hz ticks (7.8 ms); 0 = no iterations |
| | 3 | Direction: 0 = add (pitch up), 1 = subtract (pitch down) |
| | 2-0 | Step: each iteration `P = P +/- (P >> step)` |
| NR11 / NR21 | 7-6 | Duty: 00 = 12.5%, 01 = 25%, 10 = 50%, 11 = 75% (25% and 75% sound the same) |
| | 5-0 | Initial length L (write-only); duration = (64 - L)/256 s if length enabled |
| NR12 / NR22 | 7-4 | Initial volume 0-15 |
| | 3 | Envelope direction: 0 = down, 1 = up |
| | 2-0 | Envelope pace: one volume step every pace/64 s; 0 = no envelope |
| NR13 / NR23 | 7-0 | Period low 8 bits (write-only) |
| NR14 / NR24 | 7 | Trigger (write-only) |
| | 6 | Length enable (R/W) |
| | 2-0 | Period high 3 bits (write-only) |

- Tone frequency: **f = 131072 / (2048 - P)** Hz (P = 11-bit period, 0-2047). Range 64 Hz up.
- Writing NRx2 while the channel plays requires a retrigger to take effect cleanly ("zombie mode"
  writes are model-dependent; only "$V8 then repeated $08 = +1 volume" is consistent).
- Period writes apply after the current sample ends; no retrigger needed for pitch slides/vibrato.
- Sweep: addition overflow (> $7FF) turns CH1 off, even with pace 0 (if step != 0 at trigger, an
  immediate overflow check runs). Subtraction never turns it off. Writing NR13/14 during an active
  sweep is overwritten at the next sweep step (shadow register) unless you retrigger. Clearing the
  direction bit after a subtract-mode calculation disables the channel.
- Retriggering does not reset the duty phase (only APU power-off does).

Source: reference/pandocs/src/Audio_Registers.md, reference/pandocs/src/Audio_details.md

## CH3 (wave)

| Reg | Bits | Meaning |
|---|---|---|
| NR30 $FF1A | 7 | DAC on/off (off = channel off) |
| NR31 $FF1B | 7-0 | Initial length L; duration = (256 - L)/256 s |
| NR32 $FF1C | 6-5 | Level: 00 mute, 01 100%, 10 50%, 11 25% |
| NR33 $FF1D | 7-0 | Period low |
| NR34 $FF1E | 7 / 6 / 2-0 | Trigger / length enable / period high |
| $FF30-$FF3F | | 16 bytes = 32 samples, upper nibble first |

- Tone frequency: **f = 65536 / (2048 - P)** (one octave below a pulse channel with the same P).
- Wave RAM access while CH3 is **active** on DMG: reads give $FF and writes are ignored except on the
  exact cycle CH3 reads it -> effectively unusable. Procedure: `NR30 = $00` (DAC off -> channel
  off), write $FF30-$FF3F, `NR30 = $80`, then trigger NR34.
- DMG: retriggering CH3 while it is reading wave RAM **corrupts wave RAM** (first byte, or first 4
  bytes, overwritten). Avoid by writing NR30 = $00 then $80 before retriggering.
- After trigger the first sample read is index 1 (low nibble of $FF30); sample 0 plays only after
  wrapping. Until the first read the last-ever sample is output.
- Changing NR32 mid-note shifts the digital value -> DC bias (minor click).

Source: reference/pandocs/src/Audio_Registers.md, reference/pandocs/src/Audio_details.md

## CH4 (noise)

| Reg | Bits | Meaning |
|---|---|---|
| NR41 $FF20 | 5-0 | Initial length L; duration = (64 - L)/256 s |
| NR42 $FF21 | | Same as NR12 (volume/envelope; DAC rule) |
| NR43 $FF22 | 7-4 | Clock shift s |
| | 3 | LFSR width: 0 = 15-bit (noise), 1 = 7-bit (buzzy, more tonal) |
| | 2-0 | Divider r (r = 0 treated as 0.5) |
| NR44 $FF23 | 7 / 6 | Trigger (resets LFSR) / length enable |

- LFSR clock = **262144 / (r x 2^s)** Hz; s = 14 or 15 stops clocking. Higher s / r = lower,
  rumblier noise. Examples: $20 -> 131072 Hz (hiss), $50 -> 16384 Hz, $71 -> 2048 Hz, $74 -> 512 Hz.
- Switching 15->7-bit mid-sound can lock up the LFSR (silence); retrigger fixes it.

Source: reference/pandocs/src/Audio_Registers.md, reference/pandocs/src/Audio_details.md

## Note -> period table (A4 = 440 Hz, equal temperament)

P = round(2048 - 131072/f) (pulse) or round(2048 - 65536/f) (wave). Write `NRx3 = P & $FF`, `NRx4 = $80 | (P >> 8)` to trigger.
Computed values; error vs. ideal pitch is < 3 cents through octave 4, up to ~11 cents in octave 6.
For CH3 use the value from one octave higher (wave P for C4 = pulse P for C5).

| Note | Oct 3 | Oct 4 | Oct 5 | Oct 6 |
|---|---|---|---|---|
| C | $416 | $60B | $706 | $783 |
| C# | $44E | $627 | $714 | $78A |
| D | $483 | $642 | $721 | $790 |
| D# | $4B5 | $65B | $72D | $797 |
| E | $4E5 | $672 | $739 | $79D |
| F | $511 | $689 | $744 | $7A2 |
| F# | $53B | $69E | $74F | $7A7 |
| G | $563 | $6B2 | $759 | $7AC |
| G# | $589 | $6C4 | $762 | $7B1 |
| A | $5AC | $6D6 | $76B | $7B6 |
| A# | $5CE | $6E7 | $773 | $7BA |
| B | $5ED | $6F7 | $77B | $7BE |

Sanity checks from Pan Docs: P = $500 -> 170.67 Hz, P = $740 -> 682.67 Hz (pulse).

## SFX recipes (starting points - tune by ear on hardware)

Values derived from the formulas above; durations computed, sound character not measured.

| SFX | Channel | Writes (in order) | Behaviour |
|---|---|---|---|
| Jump | CH1 | NR10=$24, NR11=$80, NR12=$F1, NR13=$00, NR14=$85 | 50% duty from 171 Hz (P=$500), sweep up P += P/16 every 15.6 ms; overflow auto-stops the channel after ~7 steps (~110 ms, ending ~1.4 kHz) |
| Coin | CH2 | frame 0: NR21=$80, NR22=$F0, NR23=$7B, NR24=$87 (B5). ~4 frames later: NR22=$F2, NR23=$9D, NR24=$87 (E6, retrigger) | two-tone "ding"; second note decays 15 steps x 2/64 s ~ 0.47 s |
| Explosion | CH4 | NR41=$00, NR42=$F3, NR43=$71, NR44=$80 | 15-bit noise, LFSR 2048 Hz, decays over 15 x 3/64 s ~ 0.70 s. Deeper: NR43=$74; optionally raise NR43 shift each frame for a falling rumble |
| Shot / hit | CH4 | NR41=$30, NR42=$A1, NR43=$20, NR44=$C0 | bright hiss, length-cut after (64-48)/256 s = 62.5 ms |
| Laser | CH1 | NR10=$1E, NR11=$66, NR12=$F2, NR13=$C0, NR14=$C7 | 25% duty, P=$7C0 (2048 Hz) sweeping down P -= P/64 every 7.8 ms (~1050 Hz after 2 steps, ~440 Hz after 8). Subtract sweep never self-stops, so length L=38 cuts it after (64-38)/256 s ~ 102 ms. Note: sweep is linear in P, not in pitch - near P=$7FF small P changes are big pitch jumps |

General SFX engine shape (per frame, from VBlank or main loop): a table of {frame delay, register,
value} steps per SFX; a priority byte so a weak SFX does not cut a strong one; when finished,
silence with NRx2=$08 + NRx4=$80 (no pop) and hand the channel back to music.

## Music driver + SFX coexistence (hUGEDriver)

- hUGEDriver (tracker-based, common with GBDK) is ticked once per frame (or from the timer IRQ)
  via `hUGE_dosound()` after `hUGE_init(&song)`. It writes all four channels.
- To play an SFX on a channel, mute it in the driver first (`hUGE_mute_channel(HT_CH<n>,
  HT_CH_MUTE)`), write the SFX registers, and when the SFX ends unmute (`HT_CH_PLAY`). The driver
  then resumes writing the channel; it may stay silent until the next note triggers it. Verify
  names against the hUGEDriver.h actually vendored into the project (not part of Pan Docs).
- Conventional channel use: SFX on CH4 (noise: hits, explosions) and CH2 or CH1 (tones), so the
  melody survives; CH3 SFX need wave RAM rewrites (stop CH3 first, see above) - avoid.
- Do not touch NR50/NR51/NR52 per SFX (pops, and it affects the music). If SFX pan, restore NR51.
- Keep driver tick and SFX updates in the same context (both in VBlank or both in main loop) to
  avoid register write races.

Source: reference/pandocs/src/Audio.md, reference/pandocs/src/Audio_Registers.md, reference/pandocs/src/Audio_details.md
