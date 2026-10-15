---
name: game-studio
description: Run the studio pipeline to make a Game Boy DMG game from an idea - design (game-designer), art and UI (pixel-artist, ui-designer), implementation, QA (qa-tester), bot playtest (playtester) and the user's playtest - deciding cheap-to-change things itself and stopping only for expensive choices and the user's playtest. Use when the user wants to start a new game or a major new part of a game, e.g. "/game-studio un plataformas de un ninja".
---

# Studio pipeline

You (the main session) are the producer and the programmer. The studio roles are subagents in
`.claude/agents/`: **game-designer**, **pixel-artist**, **ui-designer**, **qa-tester**, **playtester**. Delegate
with the Agent tool (`subagent_type` = the agent name); give each a self-contained brief (they do
not see this conversation): game folder, what to deliver, decisions already taken by the user.

Talk to the user in Spanish. Commit after each phase (CLAUDE.md rule).

## Autonomy: when to stop for the user
The user prefers seeing a working game early over being asked: "las cositas se pueden cambiar
luego". The pipeline runs on its own from the idea to a playable, QA'd, bot-playtested milestone.
- **Decide yourself** everything that is cheap to change later: theme, tone, names, story, texts,
  difficulty numbers, art details, UI layout, every technical choice. Take the designer's/artist's
  recommendation and list what you chose in the phase note.
- **Ask** (AskUserQuestion, 2-3 options + your recommendation first, all in one round) only for
  what is expensive to change once built: the core mechanic or camera/view (e.g. turn-based vs
  real time, first-person vs top-down), and a scope cut that changes what the game is. A visual
  question that really decides the look goes with a comparison image (Phase 2). If unsure, decide.
- Each phase ends with a short note to the user (what was done, key image paths, decisions you
  took) and you continue without waiting. The user's playtest (Phase 6) is the one real stop.
- Feedback can arrive at any time: route it (Phase 6 rules) and keep going.

## Phase 0 - Setup
- Pick a folder name (lowercase, no spaces). New game: `python harness/gb.py new <game>`.
- Write down the user's idea and any constraints they gave (genre, references, length).

## Phase 1 - Design
- Delegate to **game-designer**: idea + constraints -> `games/<game>/design/gdd.md`.
- Show the user: pitch, core loop, controls, screens, M1 scope, budget verdict.
- Resolve "Decisiones pendientes" with the user (AskUserQuestion, 2-3 options + recommendation).
  Send answers back to the designer (SendMessage) to update the GDD, or edit it yourself if tiny.
- "Decisiones pendientes": decide them with the designer's recommendation; ask only the expensive
  ones (core mechanic, view, scope), batched. Mark the GDD "aprobado" with the date. Commit.
- **M1 is the smallest vertical slice, polished**: one map/level, one enemy type, one of each screen
  kind. Size the game against what the engine can carry today (games/faro, an open-world RPG,
  was at 119 of 120 frame lines, 96 % WRAM and full ROM banks halfway through M1b, with visual bugs
  everywhere: the user closed it). If the idea is bigger, say so and propose the slice to start with.

## Phase 2 - Art and UI (in parallel, one message with two Agent calls)
- **pixel-artist**: asset list from the GDD -> `res/*.tiles` (+ mockups showing art in context).
- **ui-designer**: every screen of the flow -> `design/screens/*.screen`, `design/ui.md`, `res/ui.tiles`.
- They must not edit the same files (artist: game tilesets; ui: `ui.tiles` + screens).
- Run `python harness/gb.py preview <game>` yourself and look at the PNGs against the skill
  checklists; send problems back to the right agent yourself. Give the user the paths of the key
  previews in the phase note (feedback can arrive any time later). Commit.
- Art details ("windows on the walls or not?") you decide from the previews. A visual question that
  really sets the game's look goes to the user WITH a comparison image: the artist renders the
  variants side by side in the same scenes (games/dungeon: `variant_windows.png`); the user could
  not choose from text alone.

## Phase 3 - Build (you, with the gbdk / gb-asm skills)
- Implement milestone by milestone (M1 first). Follow CLAUDE.md: loop structure, VRAM rules,
  `max_frame_lines` / `vram_late` / `skip_measure`, non-static globals for tests.
- Tests for each mechanic as you go (`games/<game>/tests/`). Keep `python harness/gb.py test <game>` green.
- Measure with `gb.profile([...])` before optimizing; asm only for measured hot spots, with tests.
- Declare game.json `vram_scenes` (harness/vramcheck.py) from the first scene, and for every scene
  and screen a test with `gb.vram_errors(scene)` (also after each transition into it) and
  `gb.mockup_errors(screen, ...)`. Text through `gb.screen_tiles()`, never the VRAM maps.
- **Look at the game yourself after every visible feature**: screenshots of the feature in action
  (NPCs turning, menus opening, after transitions), Read them. Green tests are not "it works": in
  games/faro the dialogue box was never on screen and NPCs wore the title's tiles, all tests green.
- Small visible increments, each with a one-line checkpoint to the user ("pruébalo: Start abre el
  panel") so they can follow the game as it grows; for a big game, stop for their look every few
  features instead of only at the end ("hay que hacerle más seguimiento").
- Commit at each milestone.

## Phase 4 - QA
- Delegate to **qa-tester** after each milestone: it runs everything, writes missing tests, profiles,
  reviews screenshots and code, reports bugs. Fix the bugs (you), re-run QA if fixes were large. Commit.
- QA's known bugs arrive as strict xfail tests: fix, remove the mark, keep the test.
- QA's readability findings (things vanishing over a background) go straight to the **pixel-artist**
  in parallel with your fixes (games/shmup: bullets over the boss wings, bat over the forest).

## Phase 5 - Bot playtest
- Delegate to **playtester** once the milestone is playable end to end and QA is green: bots with
  human-like reaction times (expert/average/novice, several seeds) measure difficulty per section,
  pacing, stuck points, exploits and feel numbers, and it proposes tuning with numbers in
  `design/playtest.md`.
- Apply the proposals that are measured and inside the GDD's intent (update the GDD numbers too);
  re-run the playtester if the changes were large. Proposals that change the game's character
  (a new mechanic, a different camera) are expensive: batch them for the user. Commit.

## Phase 6 - Playtest (the user)
- Ask the user to play: `python harness/gb.py run <game>` (controls: arrows, A = a, B = s,
  Start = Enter, Select = Backspace). Tell them what the bots found and what to try first
  (from `design/playtest.md`): fun, feel and looks are what only they can judge.
- Route feedback: feel/difficulty -> parameters in the GDD + code; looks -> pixel-artist;
  layout/menus -> ui-designer; bugs -> you + a regression test. Iterate.

## Phase 7 - Retrospective (always, before the next milestone or game)
The games exist to improve the harness. Go through `retro.md` in this skill's folder: what was
learned, what moves into `harness/common/` (engine code, assets), which mistakes become automatic
checks (build checks, lint rules, tests), what changes in skills/agents/templates. Update the GDD
to match what was built. Commit each part.
