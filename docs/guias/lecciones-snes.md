# Lecciones del proyecto SNES que valen aquí

El proyecto SNES (`C:/Users/David/Desktop/SNES`, mismo usuario, octubre-noviembre de 2026, pausado el 2026-11-23) acumuló
~780 lecciones en `docs/datos/lessons.jsonl`. Esta página recoge las que no dependen del 65816 ni del PPU de la SNES y
las traduce a la Game Boy. Entre corchetes, el id de la lección original (buscar con
`grep '"id": "<id>"' C:/Users/David/Desktop/SNES/docs/datos/lessons.jsonl`). Las técnicas medidas de aquí están en
`docs/tecnicas/`; esto es método.

## Pruebas

1. **Los checks de estado no ven la pantalla.** Un test pasó con la pantalla llena de basura y otro con la pantalla
   negra [mtest-golden, mtest-nonblank]. Aquí: cada escenario mira la captura (Read), usa `gb.vram_errors()` /
   `mockup_errors()` en PyBoy o `--nonblank` / `--golden` en `gbrun`. Es la misma regla que ya aprendió `games/faro`.
2. **Asertar los estados intermedios**, no solo el final: un estado final puede cumplirse sin haber pasado por el medio
   [intermediate-states]. `gbrun --check-at "F:..."` y `--expect "x==0@F1-F2"`; en PyBoy, asserts tras cada tramo.
3. **El valor esperado sale de un modelo, no de copiar una ejecución** [model-derived-expect, module-python-model]: aquí
   `harness/physics.py`, `harness/vwf.py`, `gb.rng_next()`, `tables.py` cargado en Python. Si el esperado solo cuadra con
   el comportamiento roto, el test está mal [test-matches-bug].
4. **Comprobar que la suite corre de verdad** (contar los PASS, no solo "no falló") [suite-really-ran]; un test xfail
   estricto es la forma de dejar un bug conocido a la vista (CLAUDE.md).
5. **Anclar entradas y capturas a un contador del juego, no al número de frame**, cuando el arranque puede cambiar de
   duración [tick-anchored-tests, tests-by-tick-not-frame]. `gbrun` ya cuenta desde el final de la boot ROM para que
   PyBoy y Mesen coincidan, pero un título que tarda más rompe los frames fijos.
6. **Probar los extremos** (velocidad máxima, más objetos, contadores al límite): los desbordamientos de 8/16 bits son
   silenciosos [test-extremes-overflow]. Aquí además el sesgo de `y` en u8 (CLAUDE.md, platformer).
7. **Un bot debe demostrar que avanza** y que el jefe recorre todos sus estados [boss-bot-pattern-coverage,
   stall-metric-per-level]; un bot atascado da números de rendimiento falsos (lección propia de platformer).
8. **Mutar para validar un test**: quitar a propósito cada protección (cada invalidación de caché, cada condición del
   camino rápido) y ver que el test falla [cache-invalidation-mutation, mutation-hit-the-hazard, fast-path-kill-switch].
   Aplica a cada rutina asm de gbe con su referencia C.
9. **Comparar byte a byte tras reescribir en asm** (OAM, VRAM, WRAM con la build anterior) [byte-compare-after-asm-rewrite];
   `gbe_selftest` lo hace para gbe; para un juego, `--dump` de `gbrun` en las dos builds.

## Mesen headless

10. Capturas con `emu.getScreenBuffer()` en el `startFrame` siguiente; `takeScreenshot` puede devolver un frame viejo
    [snesrun-sync-capture]. `gbrun` lo hace así.
11. Mesen guarda el `.sav` del cartucho entre ejecuciones: con batería, `--sram-in fresh|FICHERO` siempre
    [battery-srm-between-runs, battery-sram].
12. Un error de Lua en `--testrunner` puede colgar Mesen hasta el timeout sin log: probar primero con pocos frames
    [mesen-lua-globals-probe, study-lua-no-literal-newline]. `gbrun` valida los argumentos antes (código 3).
13. **Nunca** `taskkill /IM Mesen.exe`: otros agentes tienen Mesen en marcha; matar solo por PID [never-kill-all-mesen].
14. `emu.getState()` en un callback por instrucción es carísimo; leer el estado solo en momentos marcados
    [mesen-exec-cb-slow].
15. La configuración de Mesen del usuario no debe cambiar los resultados (filtro de vídeo, modelo, RAM, mezcla de
    frames): `gbrun` fuerza todo en la línea de órdenes.

## Rendimiento

16. **Contrastar cada medida con dos métodos** [bench-two-methods, hv-frame-wrap]: aquí `gb.profile()` y las líneas
    reales con y sin la parte (lo que ya aprendió faro con el profiler viejo). Un contador que da la vuelta hace que una
    medida larga salga corta.
17. **No componer texto cada frame**: imprimir etiquetas una vez y actualizar solo los números que cambian
    [hud-fields-not-strings]. Coincide con "preparar fuera del VBlank, copiar dentro".
18. **No acotar una carga contando VBlanks**, medir líneas [vblank-count-bounds].
19. **Los autotests largos dentro de la ROM van troceados** con presupuesto de líneas [selftest-jobs].
20. **Encender la pantalla solo en VBlank** y con la OAM ya lista: encenderla a mitad de frame da un frame de basura
    [screen-on-in-vblank]. En DMG apagarla fuera de VBlank además puede dañar la pantalla real.

## Diseño

21. **Diseñar contra la cabecera real** (`docs/api/`, `gbe.h`), no contra el documento de diseño de un módulo
    [design-from-headers, generated-docs-no-hand-edit].
22. **Derivar las reglas de nivel de la física exacta** (foso máximo andando y corriendo, escalón máximo) y medirlas
    antes de dibujar niveles [design-derive-level-rules, exec-window-per-speed, jump-meter-takeoff: el despegue es el
    último frame en el suelo]. Aquí: `harness/physics.py`.
23. **Distancias en píxeles**; si se dice "tile", decir si es de 8 o de 16 [design-units-px].
24. **La dificultad se mide como ventana de ejecución** (frames de margen por pulsación crítica), nunca 1 frame en el
    camino principal [design-exec-window].
25. **Todo diseño lista los huecos de la biblioteca que necesita** y termina con las decisiones del usuario como
    preguntas con recomendación [game-doc-gaps-questions].
26. Bits altos para decidir eventos aleatorios: en un LCG los bajos repiten con periodo corto [lcg-low-bits]
    (gbe usa xorshift16, pero la regla vale para cualquier generador casero).

## Scripts, git y agentes

27. **Una edición por script falla si no encuentra el patrón** [scripted-edits-assert]; Python en Windows lee en cp1252
    sin `encoding='utf-8'` [python-utf8-edits]; conservar los finales de línea del fichero [keep-line-endings]. Los textos
    con barras invertidas van con la herramienta Write, no en un heredoc [bash-heredoc-backslash].
28. **`git add` de rutas concretas y commit en el mismo paso**: el commit de otro agente se lleva lo que haya en el
    índice [stage-then-commit-at-once, coord-add-only-own-files].
29. **No medir contra un módulo que otro agente está cambiando**; reservar rutas antes de trabajar en paralelo
    [dont-measure-moving-module].
30. **No ampliar el encargo de un agente en marcha**: lo nuevo va al backlog y a otro agente [no-scope-creep].
31. Cada agente trabaja en su propia subcarpeta del scratchpad [scratchpad-own-subdir].
32. Los worktrees que no se borran llenan el disco (el SNES llegó a ~107 y a disco lleno); nunca crear junctions a
    carpetas versionadas dentro de un worktree (git borró los ficheros reales). Memoria del usuario, 2026-11-21/23.

## Preferencias del usuario aprendidas en SNES

- **Fidelidad antes que optimización** cuando se clona un original; optimizar después.
- **No preguntar para seguir**: los bloques planificados se hacen; solo se preguntan las decisiones reales (mecánica
  central, vista, dirección artística).
- **Las limitaciones de VRAM o sprites se resuelven con ingeniería**, no se aceptan como excusa para desviarse.
- **Diseño antes que código** (`docs/guias/diseno-juegos.md`) y preguntas de aspecto/jugabilidad a un agente
  diseñador, no al usuario.
- **Nada de fuentes hechas a mano por juego**: texto con la fuente común de la biblioteca (aquí `font*.tiles` +
  `gbe_text`/`gbe_vwf`).
- **El arte que el usuario pueda editar** vive en ficheros fuente del juego que el build lee (aquí `res/*.tiles` y las
  maquetas `.screen`), y los generadores nunca los sobrescriben.
- Las baterías completas, una vez al día; cada agente corre solo las pruebas de su bloque.
