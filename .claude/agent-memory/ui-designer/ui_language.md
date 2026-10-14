---
name: ui-language
description: The user's preferred UI look for studio games (frames, logo, HUD), confirmed on CABALLERITO/GRIFO and requested again for TORRE HUNDIDA (dungeon)
metadata:
  type: feedback
---

The user liked the CABALLERITO/GRIFO UI language and asked to reuse it in TORRE HUNDIDA (games/dungeon,
2026-10-14): framed boxes (thick black line + thin dark gray inner line, white outer pixel),
a tile logo with a drop shadow, no separator line on the HUD. Each game keeps its own theme
(dungeon: earth band with roots + upside-down battlements instead of the castle wall).

**Why:** consistency of the studio's look; the user explicitly called it out as liked.
**How to apply:** start new games from this frame/logo style, re-theme the decoration bands;
never add a HUD separator row (use a blank row). See [[screen-gotchas]].

**Text case (2026-10-14, dungeon):** the user asked that games stop writing everything in capitals:
in-game text is Spanish sentence case ("Nueva partida", "Pulsa Start"), lowercase from
`harness/common/font_lower.tiles`. Capitals only at the start of labels/lines, acronyms (PV, EQ),
button names, compass letters, and title logos. Apply to every new game's mockups and ui.md.
