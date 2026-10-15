---
name: project-happyvalley
description: games/happyvalley HAPPY VALLEY - HK horse racing stable sim (Derby Stallion-like), GDD v0.1 2026-10-15, greybox M1, race model prototype in design/race_proto.py
metadata:
  type: project
---

User's idea (fixed by him): stable management + breeding, Hong Kong racing, two tracks (Happy Valley night
tight oval where the draw matters; Sha Tin big turf/dirt with cups), races must be SEEN (side scroll +
commentary), game must be DEEP. GDD v0.1 written 2026-10-15 (`games/happyvalley/design/gdd.md`).

Key decisions I made: side-on race view, one 8 px row per runner (row = rank by lane then gate, so <= 6
sprites/line), 1 tick = 1 frame = 0.04 s race time (x2.4 TV pace), 1 px = 0.5 m; 44-week season;
money s32 in k HK$; ratings/classes HK-style table; genetics = midparent + 1/8 regression to 50 + noise ±8.
The race model was calibrated with a Python prototype (`design/race_proto.py`, the executable spec;
tests port it to `tests/hv_model.py`). Calibration lesson: bend loss must be ~1 %/lane, and lane
changes need an asymmetric "free" window or the draw bias becomes absurd (outer third won 5 %).

Pending for the user: race view (side vs oval vs side+minimap), race pace (x2.4 vs x4), season length
(44 vs 22 turns).

**Why:** future sessions on this game (M1a race, M1b management, M2 depth list) need these anchors.
**How to apply:** keep GDD and race_proto.py in sync; balance changes go to tables + bots, not C.
Related: [[feedback-greybox-first]], [[user-taste]].
