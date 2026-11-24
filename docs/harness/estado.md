# Estado del arnés de trabajo (handoff)

## 2026-11-24: puesta en marcha (portado del workspace de SNES)

Hecho:

- Beads inicializado (Dolt embebido, base `GB`, prefijo `GB-`, estados extra `confirmed,resolved`, exportación a
  `.beads/issues.jsonl`). Adaptador `harness/scripts/beads.py` con las reglas de `docs/harness/beads.md`.
- Backlog sembrado desde los hitos de cada GDD y los `xfail` estrictos: 6 epics (CABALLERITO, GRIFO, TORRE HUNDIDA,
  FARO, MADRIGUERA, HAPPYVALLEY), los 7 bugs de QA de MADRIGUERA, 2 de GRIFO, el reproductor de música de gbe
  (bloquea la música de GRIFO) y 4 huecos del arnés/docs (gb.py mesen, fichas que faltan, ROM de timing, .bat).
  Todas las tareas están en `open`: nadie ha confirmado todavía con evidencia de hoy.
- `kb.py` (brief, query, card, sql, inbox, check, test) sobre docs, gbe.h, docs/api, Pan Docs, GDD, lecciones y
  Beads; convenciones en `docs/harness/kb.md`; `kb_tests.json` con 19 consultas (19/19 en el top 3).
- `lessons.py` con 33 lecciones agnósticas de consola traídas de SNES (arnés, agentes, coste, worktrees, Beads,
  Python en Windows); sin lecciones de hardware del SNES.
- `board.py` (módulos = `gbe_<m>`, juegos = `common_src` de `game.json`), `worktree.py` (checkout completo + junctions
  a `tools/` y `reference/`, borrado seguro), `bgwatch.py`, `inbox_hook.py` (SubagentStop) y `session_start.py`
  (SessionStart) en `.claude/settings.json`.
- Agentes nuevos `gb-sdk-dev`, `gb-game-dev`, `gb-reviewer`, `gb-docs-writer`; los cinco del estudio y las skills con
  el flujo nuevo; skill `kb`. CLAUDE.md reescrito al estilo SNES, con el detalle técnico en `docs/guias/*` y
  `docs/harness/estructura.md`.
- Pruebas: `python -m pytest harness/scripts/tests -q` (27).

Pendiente / riesgos:

- Los hooks de `.claude/settings.json` se activan en la próxima sesión de Claude Code (revisar con `/hooks`).
- Sin remoto Dolt: Beads sólo vive en esta máquina (`bd dolt remote add` cuando haya remoto).
- `board.py busy` y `doctor` probados sólo con el tablero vacío; `worktree.py prune` sin probar en real.
- Las tareas de juego se sembraron del GDD: al retomar cada juego, confirmar (o descartar) con evidencia actual.
- `kb.py` no tiene todavía `GAMES` (juegos comerciales citados en estudios) para etiquetar fichas: rellenarlo cuando
  haya estudios en `docs/estudios/`.
