---
name: happyvalley-view-and-data-prefs
description: User preferences from HAPPY VALLEY v1.1 - side-on TV race camera with strong ambience (no pure top view), data-driven systems, fictional names instead of real trademarks
metadata:
  type: feedback
---

For race/sports presentation the user wants a side-on, slightly tilted TV-style camera (Derby Stallion)
with lots of ambience (crowd, city skyline, parallax, visible bends) plus a mini-map; he rejected the
pure top-down view after seeing it implemented.
**Why:** he played the top-down greybox and did not like it; ambience is "very important" to him.
**How to apply:** propose presentation with depth and atmosphere early; budget raster/parallax in the GDD.

He wants content systems to be data-only (e.g. tracks as tables: code knows no concrete track).
**Why:** new content should be a data change, not code.
**How to apply:** design formats + a generic builder + a lint and a "synthetic content" test.

Avoid real organisation/venue names with trademark risk (e.g. Hong Kong Jockey Club venues): use
fictional names with the right flavour; the game title can keep the brand vibe.
