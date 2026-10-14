---
name: screen-gotchas
description: Pitfalls met while writing .screen mockups (text-run define names, 20-char rows, missing glyphs)
metadata:
  type: feedback
---

- A single blank between two texts merges them into one `SCREEN_*_AT_` run; use 2+ blanks between a
  label and its value. Repeated texts get `_2`, `_3` names: pick distinct sample values or give the
  programmer label-row + fixed right column instead.
- Rows longer than 20 chars are silently cut: a 19-char box row shifted the frame. Generate box
  overlays with a small script that asserts widths, and print `screens.text_runs()` to check.
- Glyphs missing from the shared font (e.g. '/' before E14): map the char to DASH in the legend
  and note it; never edit `harness/common/font.tiles` myself.

**Why:** found on games/dungeon (2026-10-14); defines are the code's positions, so a wrong run
name or shifted row becomes a bug.
**How to apply:** every new mockup: check runs and row widths before writing ui.md. See [[ui-language]].
- Lowercase letters are text now (font_lower): legend keys must never be letters (a legend `u`
  turned the `u` of "puerta" into a map tile). Use symbols or Greek/Cyrillic chars, and add
  `font_lower` to the `tilesets:` line or lowercase renders as uppercase in the preview.
- Descenders (g j p q y) touch whatever is in the row below: check titles sitting right on a dark
  area (dungeon "Mapa" over the automap).
