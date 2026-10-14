---
name: font-lessons
description: Shared font redesign (2026-10-14) - user called the thin 5x7 font "basura"; bold 7x7 rules that replaced it
metadata:
  type: feedback
---

The user rejected the original thin 1 px-stroke 5x7 font in harness/common/font.tiles as junk and
asked for "algo decente" for all games. Replaced (2026-10-14) with a bold font:
2 px vertical stems, 1 px horizontals, cap height 7 (rows 0-6), glyphs from column 0, letters 7 px,
digits/I/T/Y 6 px, punctuation on cols 2-3. 0 vs O told apart by width (6 px oval vs 7 px), not
a slash: a slashed zero looked noisy in "000000" scores.

**Why:** thin strokes with 3 px gaps looked spindly and sparse on the DMG; bold stems read at 1x.
**How to apply:** new text art (logos, UI labels) should match this weight. Known trade-off:
stacked lines (dungeon log, stat panels) only have 1 px leading and look dense; if the user
complains, propose a 6 px cap height variant or spacing lines in the layout. Generator approach:
glyph dict in a scratchpad script + a sample sheet old-vs-new at 1x/3x
(games/dungeon/build/preview/font_sample.png).

Lowercase (2026-10-14, user wants mixed case): separate harness/common/font_lower.tiles (LOWER_A..Z,
macro FONT_LOWER_LOWER_A) so uppercase-only games stay untouched. x-height 5 (rows 2-6), letters 6 px,
i/l centred. Descenders g j p q y drop 1 px into row 7: compared side by side, keeping them inside
rows 2-6 made p/q read as small caps P/Q and g as 9. Trade-off: in 8 px stacked lines a tail can
touch a cap below; suggest a blank pixel row/line gap in layouts.
