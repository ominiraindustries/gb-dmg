---
name: qa-harness-notes
description: Non-obvious PyBoy/harness behaviours that make QA tests flaky or wrong (screenshots, mid-update writes, WRAM snapshot)
metadata:
  type: reference
---

- **First rendered frame shows the window 1 line too high** (PyBoy LCD renderer starts
  `ly_window = 0` instead of -1, and tests tick with rendering off). `gb.screenshot()` twice and
  use the second image before judging HUD alignment. Not a game bug.
- **Test writes land mid-update()**: PyBoy ticks end at LY 0, while the game's update runs from
  LY ~146 into the next frame, so writing a velocity (`player_vx`) can be overwritten by the game's
  own store. Teleport straight into the trigger instead of writing speeds.
- `gb.pyboy.memory[...] = v` bypasses the WRAM snapshot: a later `gb.u8` returns the old value
  until the next `frames()`. Use `gb._write(addr, v)` (wrapped as `poke()` in test_qa.py).
- `load_state()` leaves the snapshot stale too: always `frames()` before reading.
- Savestates (`gb.pyboy.save_state(io.BytesIO())`) make brute-force searches cheap (~40 trials/s).
- The profiler `_bank()` assumes no banking; fine while code is flat in 0x0000-0x7FFF.

Related: [[platformer-bug-patterns]]
