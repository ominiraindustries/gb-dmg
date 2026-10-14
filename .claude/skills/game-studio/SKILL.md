---
name: game-studio
description: Run the studio pipeline to make a Game Boy DMG game from an idea - design (game-designer), art and UI (pixel-artist, ui-designer), implementation, QA (qa-tester) and playtest - with the user approving each phase. Use when the user wants to start a new game or a major new part of a game, e.g. "/game-studio un plataformas de un ninja".
---

# Studio pipeline

You (the main session) are the producer and the programmer. The studio roles are subagents in
`.claude/agents/`: **game-designer**, **pixel-artist**, **ui-designer**, **qa-tester**. Delegate
with the Agent tool (`subagent_type` = the agent name); give each a self-contained brief (they do
not see this conversation): game folder, what to deliver, decisions already taken by the user.

Talk to the user in Spanish. Each phase ends with a short report to the user and **their
approval** before the next phase. Commit after each phase (CLAUDE.md rule).

## Phase 0 - Setup
- Pick a folder name (lowercase, no spaces). New game: `python harness/gb.py new <game>`.
- Write down the user's idea and any constraints they gave (genre, references, length).

## Phase 1 - Design
- Delegate to **game-designer**: idea + constraints -> `games/<game>/design/gdd.md`.
- Show the user: pitch, core loop, controls, screens, M1 scope, budget verdict.
- Resolve "Decisiones pendientes" with the user (AskUserQuestion, 2-3 options + recommendation).
  Send answers back to the designer (SendMessage) to update the GDD, or edit it yourself if tiny.
- Mark the GDD "aprobado" with the date. Commit.

## Phase 2 - Art and UI (in parallel, one message with two Agent calls)
- **pixel-artist**: asset list from the GDD -> `res/*.tiles` (+ mockups showing art in context).
- **ui-designer**: every screen of the flow -> `design/screens/*.screen`, `design/ui.md`, `res/ui.tiles`.
- They must not edit the same files (artist: game tilesets; ui: `ui.tiles` + screens).
- Run `python harness/gb.py preview <game>` yourself and look at the PNGs; give the user the paths
  of the key previews and collect feedback. Route feedback back to the right agent. Commit.

## Phase 3 - Build (you, with the gbdk / gb-asm skills)
- Implement milestone by milestone (M1 first). Follow CLAUDE.md: loop structure, VRAM rules,
  `max_frame_lines` / `vram_late` / `skip_measure`, non-static globals for tests.
- Tests for each mechanic as you go (`games/<game>/tests/`). Keep `python harness/gb.py test <game>` green.
- Measure with `gb.profile([...])` before optimizing; asm only for measured hot spots, with tests.
- Commit at each milestone.

## Phase 4 - QA
- Delegate to **qa-tester** after each milestone: it runs everything, writes missing tests, profiles,
  reviews screenshots and code, reports bugs. Fix the bugs (you), re-run QA if fixes were large. Commit.

## Phase 5 - Playtest (the user)
- Ask the user to play: `python harness/gb.py run <game>` (controls: arrows, A = a, B = s,
  Start = Enter, Select = Backspace).
- Route feedback: feel/difficulty -> parameters in the GDD + code; looks -> pixel-artist;
  layout/menus -> ui-designer; bugs -> you + a regression test. Iterate.

## Phase 6 - Wrap up
- Update the GDD to match what was built. Add reusable lessons to CLAUDE.md or the skills
  (new gotchas, measured costs, feel values that worked). Commit.
