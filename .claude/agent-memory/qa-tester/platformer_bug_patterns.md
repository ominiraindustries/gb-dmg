---
name: platformer-bug-patterns
description: Recurring bug patterns found in side-scroller QA (CABALLERITO M1, 2026-10-14) - check these first in any scrolling/platformer game
metadata:
  type: project
---

Patterns found in games/platformer M1 review (2026-10-14). Check these first on any platformer.

- **u8 world y with a bias wraps above the screen top**: Y_BIAS=32 is not enough when a level has
  standable blocks in row 1; a jump from there takes y below 0 -> ~224-239 and the "fell in a pit"
  check (`y >= PIT_Y`) fires. Test jumps (small running, big walking) from the highest platforms.
- **GDD numbers are approximations; level geometry is not**: GDD said running jump ~64 px, real sum
  is 62 px; the 4-high turrets needed 63 -> level unbeatable. The level lint trusted the GDD number.
  Always brute-force reachability (savestate + every take-off frame) for the tallest obstacles.
- **Existing "bot" tests may be stuck**: the step-3 bot sat against a wall at x=723 for 6000 frames
  and still "passed" the frame budget. Before trusting a bot's worst frame, check it reached the goal
  and saw the heaviest event (enemy groups, not just one enemy).
- **Per-enemy CPU in C is ~15-20 scanlines**; design max (5 enemies) blew the frame. Always run a
  test with the design maximum of actors on screen while the camera streams.
- **State change on contact re-triggered next frame**: stomping a moving ball stops it, but the
  overlap persists one frame and the "touch stopped ball = kick" rule re-kicks it. Look for
  contact handlers that change state without a grace timer.
- **Cutscene movement without physics**: the goal walk moved x only, so Teo floated 16 px after
  leaving the pole's base block. Check scripted sequences against the terrain they cross.
- Spec features silently missing: enum/flag defined but never used (HUD_TIMEICON) -> grep for
  unused dirty flags/constants vs ui.md.

**How to apply:** start platformer reviews with these tests; they are in
games/platformer/tests/test_qa.py (play_level bot, brute-force jump, 5-enemy budget).
Related: [[qa-harness-notes]]
