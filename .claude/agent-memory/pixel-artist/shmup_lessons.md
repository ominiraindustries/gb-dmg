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
**Why:** found by judging mockups, saves iterations next time.
**How to apply:** any top-down/shmup art; also re-check with zoomed crops (preview at 3x is small).
