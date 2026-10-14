---
name: shmup-lessons
description: Art lessons from GRIFO (games/shmup, 2026-10-14) - bullet readability, sprite transparency, canopy/turret pitfalls
metadata:
  type: feedback
---
Lessons from my own review rounds on GRIFO M1 art (not yet user-approved at time of writing):
- Enemy bullets = black ring + light-gray fill read over white, light-gray water and textured
  forest; they get lost over dense dark mortar lines -> keep wall faces light (white mortar on `-`).
- In sprites `.` is transparent: never use it for eyes/cores (WAVE core showed the BG through).
- A mostly light-gray player vanishes over light-gray water: give it some `+` mass (wing coverts).
- Circle canopy clumps read as cobblestones; scalloped radius + leaf ticks reads as foliage.
- Ballista turrets: diagonal bow arms read as an "X", hollow hub as a magnifier; a T-shaped
  crossbow (arc + 2-px stock + arrowhead) rotated 90 deg for left/right reads best.
- QA round (2026-10-14): sprites have NO white (shade 0 = transparent, OBP0 0xE4) - "white core"
  requests are impossible; instead use a light-gray 1-px halo outside the black outline + a
  heavy black body (2-px ring, light core). Reads over white, light membrane and dark bones.
- Thin-outline sprites with light fill vanish over light textured BG (canopy); a dark mass
  (black body, dark membrane) + light rim reads better than "light membrane" bats.
- Blinking items via OBP0 0xE4 / OBP1 0xD8 swap shades 1<->2: give each item a big area of
  one shade (dark badge + light icon) so the blink inverts visibly.
- Judge with real ROM screenshots: composite new sprites onto build/shots/*.png with a scratch
  PIL script (before vs after side by side) - faster and truer than .screen mockups.
**Why:** found by judging mockups, saves iterations next time.
**How to apply:** any top-down/shmup art; also re-check with zoomed crops (preview at 3x is small).
