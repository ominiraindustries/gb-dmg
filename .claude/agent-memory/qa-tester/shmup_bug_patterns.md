---
name: shmup-bug-patterns
description: Recurring bug patterns found in the GRIFO shmup M1b QA (2026-10-14) - check first in any pool/flicker/screen-flow game
metadata:
  type: project
---

Found in games/shmup M1b (tests in games/shmup/tests/test_qa.py, strict xfails until fixed).

- **u8 screen timers on screens longer than 255 f**: CONTINUAR count (632 f) used `++screen_timer`
  with `(t - 16) % 60` and `t >= 46`; after the wrap, digits last 60/136 f and Start is ignored
  46 f out of every 256. Grep every `% 60`/`t >= N` on a u8 timer and ask how long that screen lasts.
- **Pause drops the active HUD message** (PELIGRO/FASE): the message system has one slot, PAUSA
  overwrites it and resuming calls message_end. Test pause during every timed message.
- **Effects gated on `timer & 7 == 0` + work split by frame parity**: shots checked on even frames
  only, flash only when boss_t % 8 == 0 -> with an odd boss_t - frame the flash never fires. Test
  both parities (shift the timer by 1).
- **Rotation by 1 slot per frame with >1 object dropped per line** keeps one object hidden 2+
  frames. Union-of-2-frames tests catch it.
- **"All in one frame" bursts**: bomb (12 x add_score + 6 kills + 4 turret kills) and CLEAR skip
  (180 x add_score) -> frame_lines 255. add_score did bcd_tiles every call (~700 T).
- **Lint lifetimes from GDD approximations** (DART 100, WAVE 200) vs the real route (176/vy = 117,
  235): the 6-slot pool overflows and `spawn_enemy` silently drops spawns. Recompute lifetimes from
  the route and run a no-shooting bot that counts dropped spawns.
- Skipped-count bonus: "finish at once" re-adds the item being counted (overpay).

**How to apply:** for screen flows, test durations > 256 f; for pools, run a bot that never kills.
Related: [[platformer-bug-patterns]], [[qa-harness-notes]]
