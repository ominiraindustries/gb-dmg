# Retrospective checklist (end of every milestone / game)

Goal: the next game must start better than this one did. For each item, do it or write why not.

## 1. Collect
- [ ] Read the git log of the game, the QA reports and the agents' memories (`.claude/agent-memory/`).
- [ ] List every bug that reached QA or the user, every performance problem and every time a tool
      or document was wrong or missing.
- [ ] For every bug the USER saw (they play, tests do not): which check would have caught it, and
      why did ours pass? (games/faro: tests read VRAM maps and tile numbers, never what was drawn ->
      `gb.vram_errors`, `gb.mockup_errors`, `gb.screen_tiles`.)

## 2. Turn mistakes into checks (best: impossible to repeat)
- [ ] Build check (`harness/gb.py check_warnings`) for compiler-detectable mistakes.
- [ ] Lint rule (level/asset lints) for content mistakes, using measured data (physics.py), not
      hand numbers.
- [ ] Test or harness assertion for runtime mistakes (VRAM guard, budget bot that must progress,
      selftest for asm).
- [ ] Only if none of the above is possible: a rule in CLAUDE.md / a skill's gotchas.

## 3. Move reusable code into the harness
- [ ] Engine code used and tested by this game that another game would rewrite -> `harness/common/src`
      (gbe), with a C reference + selftest for any asm, and a line in `harness/common/README.md`.
- [ ] Shared assets (font glyphs, UI pieces) -> `harness/common/*.tiles`.
- [ ] Converters/tools the game needed -> `harness/` (+ docs at the top of the file).
- [ ] Re-run the game's whole suite on the extracted code (the game is the library's test).

## 4. Improve the studio
- [ ] Agents: what did each role get wrong or miss? Change its instructions or tools.
- [ ] Skills: new measured costs, patterns, gotchas (with numbers and where they were measured).
- [ ] Templates (`harness/templates/<type>`): would a new game of this type start from this game's
      skeleton? Add/update the template.
- [ ] Save durable user preferences in the agents' memories.

## 5. Close
- [ ] All game suites green (`python harness/gb.py test <game>` for every game).
- [ ] CLAUDE.md still short and true (move details into skills).
- [ ] Commit per topic; report to the user what changed in the harness and why.
