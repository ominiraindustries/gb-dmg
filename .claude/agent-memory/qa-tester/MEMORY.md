# QA tester memory

## Recurring bug patterns (check these first)
- Lock/timer resets that can be refreshed forever by an action that briefly changes state (tetris:
  a floor kick lifting the piece reset the lock delay without spending a reset).
- Fixed-size FIFOs/queues that silently drop when full (tetris text queue lost a "clear" -> stray
  tile on screen). Look for `if (count == MAX) return;` and count the worst-case burst.
- Per-level loops in scoring/difficulty (`for i <= level`) that blow the frame budget at high
  levels; test the maximum reachable level, not just 20.
- HUD fields with fewer digits than the value can reach (level 100 rendered as 'A0').
- Auto-repeat (DAS) using a fixed priority instead of the last pressed direction.
- Off-by-one in "N per frame" loops (rows per VBlank was 3 instead of 4).
- [Platformer patterns](platformer_bug_patterns.md) - u8 y wrap above top = pit death, GDD jump
  height vs level, stuck bots, 5-actor CPU budget, contact re-trigger, cutscenes without physics.

- [Shmup patterns](shmup_bug_patterns.md) - u8 timers on >255 f screens, pause eats HUD message,
  `t&7` gates vs parity-split work, rotate-by-1 flicker, one-frame bomb bursts, lint lifetimes.

## Harness notes
- PyBoy tick returns at LY 0, possibly mid-update(); allow ±1 frame or require a condition for
  2 consecutive frames.
- Bot tests must include the heaviest events (line clears, refills, transitions); a random bot
  that never clears lines does not test the worst frame.
- [Harness gotchas](qa_harness_notes.md) - screenshot twice (window 1 line off on first render),
  writes land mid-update, pyboy.memory writes bypass the WRAM snapshot.
