---
name: proportional-text-mockups
description: User picked proportional font B (font_mini*) for mazmorra; how to lay out mockups when the build draws every text proportionally (vwf)
metadata:
  type: feedback
---

The user chose the proportional font B (`harness/common/font_mini*.tiles`) for games/mazmorra
(2026-10-15); the harness draws every mockup text proportionally into a reserved `text` VRAM slot.

**Why:** the user found monospace text airy; proportional text is ~70% as wide (≈5.7 px per letter).

**How to apply:**
- `tilesets:` lists `font_mini font_mini_lower font_mini_es`; legend punctuation refs are
  `font_mini:DOT` / `font_mini_es:EXCL_OPEN` etc.
- One letter still takes one grid cell, so a centred text (`center:`) is only truly centred on the
  screen when its cell count is even and symmetric about column 10: pick wording with an even letter
  count (e.g. "Has caido.", "Gracias por jugar.").
- Dynamic lines: sample text exactly as long as the reserved tiles (18-letter dialogue lines).
- Overlays shown with another screen's texts get `text: <offset>`; overlay mockups must not include
  HUD digits (they would be allocated inside the overlay's range). Same-shape boxes without a tab
  get offset + tab size so their lines share tiles.
- Use `_TILES_` (not `_LEN_`) for blanking: LEN stops at a DOT legend char.
