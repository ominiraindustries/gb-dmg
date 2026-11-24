# GBDMG: juegos de Game Boy DMG, instrucciones de trabajo

Juegos en C con GBDK-2020 (SDCC 4.5) sobre la biblioteca de motor **gbe** (`harness/common`), probados en PyBoy.
Las partes críticas pasan a ensamblador sólo cuando el profiling lo justifica y con prueba de equivalencia contra C.
Cliente: Claude Code. El usuario habla español: responde en español. Código, comentarios e identificadores en inglés.

## Inicio de una tarea

1. Ejecuta una sola vez: `python -I harness/scripts/kb.py brief --role <rol> --task "<tarea>"`.
2. Lee sólo las rutas y secciones que indique el brief. Para técnicas, cifras, hardware o API usa
   `kb.py query "..." [--kind api|ref|tecnica|game]` antes de buscar por todo el repositorio.
3. Carga sólo la skill necesaria. No leas todas las skills, toda la documentación ni ficheros enteros si basta una sección.
4. Resume logs y resultados; nunca vuelques al contexto logs grandes, transcritos, JSONL, binarios ni árboles completos.

Mapa de la documentación: `docs/INDEX.md`. Qué usar para cada necesidad: `docs/guias/que-usar.md`. API de gbe:
`docs/api/` (generada desde `harness/common/src/gbe.h` con `python -I harness/scripts/apidoc.py`; `--check` comprueba
que está al día). Referencias de hardware: `docs/ref/` (regenerables con `docs/ref/mkref.py`). Convenciones para que
`kb.py` encuentre lo que se escribe: `docs/harness/kb.md`.

Trabajo pendiente: Beads, mediante `python -I harness/scripts/beads.py` (`prime`, `ready --json`, `show ID`). Estados
verificables: `open` → `confirmed` (evidencia fechada) → `in_progress` (`--claim`) → `resolved` (hecho, sin validar)
→ `closed` (prueba y fecha, o descarte razonado). Toda tarea lleva `--acceptance` y una etiqueta `area:`
(`gbe`, `harness`, `docs`, `juego:<nombre>`); no se cierra sólo con un commit. Flujo: `docs/harness/beads.md`.

## Mapa mínimo

- `harness/`: herramientas comunes (no meter código de un juego): `gb.py` (CLI: `setup`, `new`, `build`, `run`,
  `test`, `preview`), `gbtest.py` (driver PyBoy de los tests), `gbrun.py` (Mesen), conversores (`screens.py`,
  `levels.py`, `world.py`, `tables.py`, `script.py`, `metatiles.py`, `vwf.py`), `templates/`.
- `harness/common/`: **gbe**, la biblioteca de motor (`src/gbe*.c/.s`, `gbe.h`, `README.md`) y los recursos comunes
  (fuentes `font*.tiles`, `greybox.tiles`). Un juego nuevo parte de ella en vez de reescribirla.
- `harness/scripts/`: arnés de trabajo (`kb.py`, `beads.py`, `lessons.py`, `board.py`, `worktree.py`, `bgwatch.py`,
  hooks). Python siempre con `-I`.
- `games/<juego>/`: `src/`, `res/`, `tests/`, `design/` (GDD, ui, maquetas), `game.json`. `games/urbe` es trabajo del
  usuario sin versionar: no se toca, no se commitea, no se borra.
- `docs/`: guías, técnicas, estudios, API, referencias, datos (lecciones, buzón) y arnés.
- `tools/` (GBDK, `python harness/gb.py setup`) y `reference/` no se versionan.

Formatos de `res/` (`.tiles`, `.screen`, `.lvl`, `.map`, `.tbl`, `.evs`, `metatiles.mt`) y claves de `game.json`
(`common_src`, `common_res`, `screens`, `vram_order`, `vram_scenes`, `banked_res`, `levels`): `docs/harness/estructura.md`.

## Commits

Commit automático (sin preguntar) al terminar cada cosa: un juego o hito, cambios en skills/agentes/CLAUDE.md, mejoras
del arnés. Mensajes en español, agrupados por tema. Sólo tus rutas: `git add <rutas>` y commit en el mismo paso, nunca
`git add -A` (te llevarías el trabajo de otros agentes y `games/urbe`).

## Estudio (diseño + programación)

Juegos nuevos o partes grandes: skill `/game-studio <idea>`. Decido yo lo barato de cambiar (tema, tono, nombres,
detalles); sólo pregunto lo caro (mecánica central, vista) y paro en la prueba del usuario al final. **Primero el juego
con cuadros** (`harness/common/greybox.tiles`, toda la lógica, sin agentes de arte); arte y UI al final, cuando el
usuario ya lo ha jugado. Roles en `.claude/agents/`: `game-designer` (`design/gdd.md`), `pixel-artist` (`res/*.tiles`),
`ui-designer` (`design/screens/*.screen`, `ui.md`), `qa-tester`, `playtester` (bots con `GB.human`); la sesión principal
hace de productor y programador. Vista previa sin compilar: `python harness/gb.py preview <juego>` → `build/preview/`.

## Reglas de implementación

- **Lib primero**: antes de escribir a mano física, menús, input, texto, guardado, scroll, actores, HUD, colas de VRAM o
  sonido, consulta `docs/guias/que-usar.md` y `kb.py query --kind api`, y anota en el README del juego una tabla
  "Lib check" (necesidad, API revisada, por qué no basta). Si gbe cubre casi todo, úsala y pide sólo el hueco. Si
  falta de verdad, NO lo resuelvas en el juego: abre una tarea `area:gbe` con `--acceptance`, hazla en un worktree con
  su prueba (`gb.selftest()`, `games/gbe_lab`) y migra el juego después.
- **Texto y fuentes**: ningún juego dibuja texto con una fuente hecha a mano ni con un motor de texto propio. Todo el
  texto usa las fuentes del arnés (`harness/common/font*.tiles`, `font_lower`, `font_mini*`, `font_es`) con `gbe_text`
  o `gbe_vwf`. Se decide al crear el armazón, antes de la primera pantalla, y el encargo de cualquier agente de interfaz
  lo dice. Un glifo nuevo va a la fuente común, para todos los juegos.
- **Arte editable**: los fuentes de arte (`res/*.tiles`, `design/screens/*.screen`) son la fuente de verdad que lee el
  build; los scripts generadores sólo los siembran y nunca los sobrescriben al compilar. Cada juego lleva
  `compilar.bat` y `compilar_y_jugar.bat` para recompilar con doble clic (tarea pendiente en Beads para los existentes).
- **Diseño primero**: todo agente que diseñe juego, niveles, enemigos o jefes lee antes `docs/guias/diseno-juegos.md`
  y cita qué reglas aplica; un nivel no se da por bueno sin pasar su checklist.
- Los cambios de diseño visual, controles, dificultad o dirección artística son decisiones del usuario.
- PixelLab y otras APIs de pago requieren permiso previo del usuario.
- Un cambio en `harness/common` o `harness/*.py` tiene rigor alto y se hace en un worktree
  (`python -I harness/scripts/worktree.py add NOMBRE --base RAMA`; se quita con `worktree.py remove`, nunca a mano).
  Un cambio dentro de `games/<juego>` tiene rigor medio.
- Respeta la propiedad de archivos que indique el coordinador; no edites archivos compartidos fuera del encargo.
- Lecciones del workspace de SNES aplicables aquí: `docs/guias/lecciones-snes.md`.

## Reglas técnicas imprescindibles (detalle en las guías)

- **Rendimiento y VRAM** (`docs/guias/rendimiento-vram.md`): bucle `vsync()` → `draw_vram()` (sólo copiar) → input →
  `update()` → sprites → `measure_frame()`; preparar tiles fuera del VBlank y dentro sólo copiar con presupuesto fijo;
  `vram_late` debe ser 0 en los tests; regla propia < 120 líneas de 154; medir con `gb.profile` antes de optimizar.
- **Bancos de ROM** (`docs/guias/bancos.md`): `banked_res` + `-autobank` con MBC5; un fichero con `#pragma bank N`
  no llama a `SWITCH_ROM`; el banco 0 no pasa de 0x4000; saves con firma + checksum (`gbe_save.c`).
- **Hardware DMG** (`docs/guias/hardware-dmg.md`, skill `gb-hardware`): 70224 T por frame (17556 M-cycles), VRAM
  inaccesible en modo 3, OAM en modos 2 y 3; nunca escribir OAM desde C; apagar el LCD sólo en VBlank; 10 sprites por
  línea (ocultar con Y, no con X); fijar siempre BGP/OBP0/OBP1; WRAM y SRAM arrancan con basura.
- **C con SDCC, GBDK y asm** (`docs/guias/sdcc-c.md`, skills `gbdk`, `gb-asm`): `uint8_t` por defecto, shifts a mano,
  nada de `int8_t` como índice ni `/` por variable; el bug de `(uint16_t)y << 4`; convención `__sdcccall(1)`; asm
  `sdasgb` sólo tras medir y con test de equivalencia C vs asm.

## Verificación

- Compilar: `python harness/gb.py build <juego>` (el build se para con funciones sin declarar, prototipos en bloques o
  registros escritos sin su sombra). Probar: `python harness/gb.py test <juego>` tras cada cambio de lógica.
  Jugar (ventana, sólo el usuario): `python harness/gb.py run <juego>`. Mesen headless: `harness/gbrun.py`
  (PyBoy frente a Mesen: `docs/guias/pruebas.md`).
- Mira las capturas (`games/<juego>/build/shots/*.png`) antes de afirmar que algo funciona. Los tests comprueban **lo
  que se ve** (`gb.vram_errors`, `gb.mockup_errors`, `gb.screen_tiles`), no variables ni mapas de VRAM.
- Cada mecánica nueva lleva su test (estado → entrada → assert sobre globales **no static**, `gb.u8("x")`). Las
  lecturas usan la foto de WRAM del último frame (no `gb.pyboy.memory`); hay 1 frame de latencia de entrada. Helpers
  en `games/<juego>/tests/<nombre>.py` con nombre único entre juegos. Bugs conocidos: `xfail(strict=True)` + tarea. Un juego que arranca en el
  título puede sobreescribir el fixture `gb` en su `tests/conftest.py` (games/shmup).
- Prueba proporcional al cambio: el implementador ejecuta la suite de su juego (y `gb.selftest()` si tocó asm de
  gbe). La batería de todos los juegos, una vez al día o al integrar cambios de gbe; nunca un bucle de suites.
- No dar algo por "fino" sin que el usuario lo haya probado: el feel y el hardware real no se testean aquí.
- Un script de reemplazo comprueba que encontró el patrón esperado.

## Agentes y presupuesto de contexto

Trabaja directamente en búsquedas, cambios de un fichero, tareas secuenciales y pruebas rutinarias. Usa subagentes sólo
con líneas de trabajo independientes, aislamiento necesario o una especialidad clara.

Agentes de ingeniería: `gb-sdk-dev` (gbe y arnés, en worktree), `gb-game-dev` (un bloque de un juego), `gb-reviewer`
(revisión independiente) y `gb-docs-writer` (documentación y triaje); los del estudio, arriba. Reparto de modelos y
reglas de coste: `docs/harness/coste-tokens.md`.

- Objetivo 80–120 llamadas por agente; máximo 150. A las ~130 se termina el bloque y se escribe un handoff corto
  (README del juego, notas de la tarea o `docs/harness/estado.md`). Una fase nueva la empieza otro agente con el handoff.
- Máximo 2–3 agentes simultáneos, con rutas no solapadas. Antes de lanzarlos:
  `python -I harness/scripts/board.py claim NOMBRE --bead ID --task "..." --owns RUTAS --uses MODULOS`;
  al integrar, `board.py release NOMBRE [--remove-worktree]`. `board.py doctor` revisa reservas y worktrees.
- Mensajes a agentes en marcha: pocos y agrupados. Si esperas a un agente, avanza trabajo que no se solape.
- Todo bucle de espera lleva límite (`timeout 1800 bash -c ...`). Procesos colgados: `python -I harness/scripts/bgwatch.py`.

## Hallazgos y cierre

Los informes finales de los subagentes pueden llevar `## Lecciones para mi rol`, `## Huecos de gbe` y
`## Bugs encontrados`; son opcionales y sólo con evidencia nueva y reutilizable (compruébalo antes con `kb.py query`).
El hook `SubagentStop` los archiva en `docs/datos/inbox.jsonl`; el aviso de inicio de sesión pide cribar con 20 o más
o más de 2 días (`kb.py inbox apply FICHERO`). Lo vigente va a Beads o a lecciones (`lessons.py add`).

Antes del informe final ejecuta las comprobaciones de las rutas modificadas (`kb.py check` si tocaste docs, lecciones
o Beads). Informa de archivos cambiados, pruebas realizadas, resultado y riesgos pendientes; sin logs completos.
