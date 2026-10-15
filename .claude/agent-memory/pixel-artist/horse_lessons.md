---
name: horse-lessons
description: Racehorse sprite lessons for games/happyvalley - user rejected childish 16x16 horses, gave a 30x22 stretched-gallop reference; what made the redraw work (2026-10-15)
metadata:
  type: feedback
---

User verdict on the concept horses (16x16, 1-px legs, procedural): "parecen hechos por un crío". Horses are
THE key art of happyvalley. The user then gave a reference: colour pixel racehorse ~30x22 px in full stretch (long low body,
neck thrown forward, small head, tail streaming back, crouched jockey with cap, saddlecloth).

**Why:** small horses fail on legs and head; procedural primitives (ellipses + joint-angle lines) gave goats/sausages.
**How to apply:**
- What worked: fill masks as span lists + auto 4-neighbour outline for body/neck/head, jockey as its own blob,
  legs HAND-PLACED per pose from a small pose library (reach, reachhi, vert, back, lift, fold / push, trail,
  land, mid, under, swing), with an 8-frame Muybridge table picking poses. Near legs 2 px ('+' coat + black back
  edge), far legs 1 px black; bay coat = dark gray + black points. Head LOW and neck stretched forward
  (a high head reads as a goat/cat at 16-24 px).
- Judge in the night-straight scene (scratchpad concept.py screen_night + compose) at 1x and 3x.
- 24x16 and 32x24 hold the reference look; 16x16 can't (suspension frames look like a bird).
- Scripts: scratchpad L16.py/L24.py/L32.py, pnt.py, cost.py, study.py (may be gone between sessions).
See [[feedback-style-happyvalley]].
