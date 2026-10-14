---
name: project-shmup
description: games/shmup exists to stress-test and grow the gbe engine (harness/common) as well as be a small polished vertical shmup; GDD v0.1 drafted 2026-10-14
metadata:
  type: project
---

games/shmup (vertical shoot'em up, working title GRIFO, GDD v0.1 2026-10-14, pending user decisions).
The user's explicit goal: the game must also **stress-test and extend the studio harness** — exercise
what gbe lacks (vertical row streaming, 8-bit object pools, sprite multiplexing/flicker priority,
bullet patterns/aim, asm collision, wave scripting, BG-drawn boss) inside a small M1 scope.

**Why:** the studio builds each game to grow reusable engine pieces in harness/common (gbe), extracted only after a game uses and tests them.

**How to apply:** for this and future designs, list precisely which gbe modules are reused and which
new generic engine items (with C references + selftest) the design needs, and schedule engine work
(M1a) before game logic (M1b). Related: [[user-taste]].
