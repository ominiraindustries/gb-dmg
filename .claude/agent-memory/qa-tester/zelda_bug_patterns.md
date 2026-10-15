---
name: zelda-bug-patterns
description: Bug patterns found in the top-down room-slide action game QA (MADRIGUERA M1, 2026-10-15) - check first in any gbe_world/gbe_gact room game
metadata:
  type: project
---

Found in games/mazmorra M1 (tests in games/mazmorra/tests/test_qa.py, strict xfails until fixed).

- **Room-exit trigger one cell late**: slide fired when the feet centre had LEFT the room instead of
  entering its border row (GDD). Effects: Tilo lands 1 cell too deep (next to enemies) and, with a
  TOP HUD, walks fully hidden under the window cut for ~8 frames before the slide. Measure landing
  cell per direction and sprite lines visible below the cut.
- **Knockback skips the room-exit check**: forced movement (knockback) can push the player through a
  doorway out of the room; the exit check only ran while a direction was held -> player off-screen,
  pressing UP slides DOWN. Test knockback in every doorway.
- **gact_try_move on a moving actor still changes a->dir** (gbe_gact.c): drawn offset along the new
  axis -> 16-30 px sprite jump, no knockback. Any "force a step" on gact must check `moving`.
- **Static timers not reset on death/new game** (shake_t set by the fatal hit, never decremented while
  dead): effects replay after Continuar AND after Salir -> new game. Grep link/player statics.
- **Fade colour vs spec**: gbe `transition()` always fades to white; specs asking for black (death)
  need set_fade_dark.
- **BANKED engine getters in per-frame loops** (gact_wx/gact_wy ~350 T each, called per enemy in both
  contact and sword loops) -> bot worst 97/100 lines with only 3 enemies.
- gb.selftest() must run in a scene with the world loaded (at the title: 67/200 false mismatches).
- view model mid-slide: SCX/SCY in the snapshot are one frame behind cam_x/cam_y (ISR writes them):
  derive the displayed camera from SCX/SCY high bits from cam.

**How to apply:** start room/slide games with these tests (walk_out per direction, knockback in
doorways, mid-step hit, shake after continue, fighting bot in maz_bot.py).
Related: [[platformer-bug-patterns]], [[shmup-bug-patterns]], [[qa-harness-notes]]
