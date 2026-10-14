# GBDMG — harness para juegos de Game Boy DMG

Juegos en C con GBDK-2020 (SDCC). Las partes críticas se pasan a ensamblador solo cuando
el profiling lo justifica y con una prueba de equivalencia contra la versión C.

## Estructura
- `harness/` — herramientas comunes a todos los juegos (no meter código de un juego aquí)
  - `gb.py` — CLI: `setup`, `new`, `build`, `run`, `test`
  - `gbtest.py` — driver headless (PyBoy) para tests: botones, frames, leer variables, capturas
  - `templates/<tipo>/` — plantillas de `gb.py new <juego> [tipo]` (hoy: `basic`, sobre gbe)
- `games/<juego>/` — `src/` (.c/.s), `res/` (assets), `tests/` (pytest), `game.json` (título, flags de lcc)
  - `res/*.tiles`: tiles en arte ASCII 8x8 (`.` `-` `+` `#` = colores 0-3, `@ NOMBRE` etiqueta el
    siguiente tile). Se convierten al compilar a `build/gen/<nombre>.c/.h` (`#include "bg.h"`).
  - Assets compartidos en `harness/common/*.tiles` (p. ej. la fuente): `"common_res": ["font"]` en game.json.
    Texto en mayúscula y minúscula: `font_lower` (a..z) + `txt_lower`; en tests `GB.tile_text(tiles, font, lower)`.
  - Pantallas fijas (título, resultados...): las maquetas `design/screens/<nombre>.screen` del
    ui-designer se convierten al compilar en mapas de tiles (`screen_<nombre>_map[360]` + sprites) con
    `"screens": [...]` y `"vram_order": ["bg", "font", "ui"]` (bases de VRAM; `["a", "b"]` = dos tilesets
    que se turnan en el mismo hueco) en game.json. El build genera `vram.h` (`VRAM_<TILESET>`) y
    `@ base auto` en `metatiles.mt`/`view.pcs`: nada de bases escritas a mano
    (`harness/screens.py`). Lo que diseña el agente es exactamente lo que sale en el juego.
  - **Librería de motor `gbe`** (`harness/common/src/gbe*.c/.s`, ver `harness/common/README.md`):
    bucle de frame y medición, OAM directo, fundidos/transiciones, HUD con corte LYC, actores con
    `act_move` asm, mapa con scroll y consultas asm, SFX con prioridad, autoprueba asm-vs-C
    (`gb.selftest()`). Juegos nuevos parten de ella en vez de reescribirla.
  - Código compartido en `harness/common/src/` (p. ej. `bcd.s` + `bcd.h`, suma BCD con `daa`):
    `"common_src": ["bcd.s"]` en game.json; sus headers están en el include path.
  - `res/*.lvl`: niveles en ASCII (rejilla + `@ clave valor`), convertidos a `build/gen/<nivel>.c/.h`
    (mapa por columnas + lista de objetos). Qué significa cada carácter va en game.json `"levels"`
    con nombres simbólicos que define el C del juego (formato al principio de `harness/levels.py`;
    `levels.parse()` sirve para tests de lint en Python puro). Niveles verticales (shmup):
    `"order": "rows"` + capa de objetos al lado de la rejilla (games/shmup/res/stage1.lvl).
  - `res/maps/*.map`: mundos con scroll en 4 direcciones (sectores de 16x16 casillas, `harness/world.py`)
    para `gbe_world`; banco de pruebas `games/world_lab` (pantalla == modelo en cada frame).
  - `res/data/*.tbl`: tablas de datos (columnas con tipo: texto, enum, flags, ref a otra tabla) →
    `tbl_<nombre>[]` en un banco + ids `<PREFIJO>_<ID>` para guiones y mapas (`harness/tables.py`, con
    cargador Python para tests y bots). Los números de equilibrio van ahí, no en C.
  - `res/scripts/*.evs`: guiones y diálogos (`harness/script.py`: texto partido en líneas/páginas al compilar,
    lint de banderas/etiquetas/longitudes) para `gbe_script` + `gbe_tbox`.
  - `res/metatiles.mt`: tabla de metatiles como datos (nombre, 4 tiles, atributos) → `build/gen/metatiles.c/.h`
    (`harness/metatiles.py`); la usan el ROM, la vista previa del nivel y los tests en Python.
- `tools/gbdk/` — SDK, no versionado (`python harness/gb.py setup`)

## Commits
Hacer commit automáticamente (sin preguntar) al terminar cada cosa: un juego o hito, cambios en
skills/agentes/CLAUDE.md, mejoras del arnés. Mensajes en español, agrupados por tema.

## Estudio (diseño + programación)
Para juegos nuevos o partes grandes: skill `/game-studio <idea>` (fases autónomas: tema, tono, nombres y
detalles los decido yo; solo pregunto lo caro de cambiar, como la mecánica central o la vista, y paro en la prueba
del usuario al final).
Roles (subagentes en `.claude/agents/`, cada uno con memoria propia):
- `game-designer` → `design/gdd.md` (mecánicas con números, controles, pantallas, presupuestos, hitos, plan de pruebas)
- `pixel-artist` → `res/*.tiles` + maquetas; revisa sus PNG de preview
- `ui-designer` → `design/screens/*.screen`, `design/ui.md`, `res/ui.tiles`
- `qa-tester` → tests que faltan, rendimiento/VRAM, revisión visual y de código, informe de bugs
- `playtester` → bots con reflejos humanos (`GB.human`, experto/medio/novato) → `design/playtest.md`:
  dificultad por tramo, ritmo, atascos, trucos, números de feel y ajustes propuestos con cifras
- La sesión principal hace de productor y programador (skills `gbdk`, `gb-asm`).
Skills de diseño: `gb-game-design` (GDD, feel, UI, presupuestos, géneros), `gb-pixel-art`.
Vista previa sin compilar el juego: `python harness/gb.py preview <juego>` → `build/preview/*.png`
(hojas de tiles, maquetas `design/screens/*.screen` y, con `metatiles.mt`, el nivel vertical entero
`level_<nivel>.png` con los objetos marcados; formato al principio de `harness/preview.py`).

## Flujo de trabajo
- Compilar: `python harness/gb.py build <juego>` (muestra uso de ROM/RAM). El build se para a propósito
  si hay funciones sin declarar (dice qué `#include` falta), prototipos dentro de bloques, o si un juego
  con `gbe_video` escribe `SCX/SCY/BGP/OBP*_REG` sin su sombra (la ISR de VBlank lo pisaría).
- Helpers de tests en `games/<juego>/tests/<nombre>.py` (p. ej. `stage_model.py`): importables desde los
  tests (conftest añade la carpeta); el nombre debe ser único entre juegos.
- Tests: `python harness/gb.py test <juego>`. Ejecutarlos tras cada cambio de lógica.
- Jugar: `python harness/gb.py run <juego>` (ventana PyBoy)
- Las capturas de los tests van a `games/<juego>/build/shots/*.png`: mirarlas con Read
  para comprobar visualmente los cambios, no fiarse solo de los asserts.
- Presupuesto de frame: el juego expone `max_frame_lines` (scanlines usadas tras `vsync()`) y un
  test con bot juega miles de frames y comprueba que no se pasa (ver `games/breakout`, `games/tetris`).
- Cada mecánica nueva lleva un test: estado inicial → entrada → assert sobre variables.
  Los tests leen globales **no static** por nombre (`gb.u8("player_x")`), vía el fichero .noi.
- Lecturas coherentes en tests: el tick de PyBoy acaba en LY 0, a mitad del `update()` del juego.
  `gbtest` lo resuelve con un hook en `vsync()` que fotografía la WRAM en el último frame de cada
  `frames()`: `gb.u8/u16/bytes` leen esa foto (estado completo del frame). Leer WRAM con
  `gb.pyboy.memory` directamente salta esa protección. Hay 1 frame de latencia de entrada: un botón
  pulsado antes de `frames(1)` se procesa en la lógica que termina en el frame siguiente.
- No dar algo por "fino" sin que el usuario lo haya probado (el feel y el hardware real no se testean aquí).
- Bugs conocidos que aún no se arreglan: test con `@pytest.mark.xfail(strict=True, reason="BUG: ...")`
  (al arreglarlo pasa a XPASS y falla, así se quita la marca). Un juego que arranca en el título
  puede sobreescribir el fixture `gb` en su `tests/conftest.py` (ver games/shmup).

## Rendimiento y VRAM (aprendido en games/tetris, medido)
- Bucle: `vsync()` → `draw_vram()` (solo copiar a VRAM) → input → `update()` → sprites → `measure_frame()`.
  `vsync()` vuelve en LY≈146: quedan ~3600 T de VBlank para `draw_vram()`.
- **Preparar tiles fuera del VBlank, dentro solo copiar**: convertir números/textos a tiles en `update()`
  (buffers), y en `draw_vram()` copiar con un presupuesto fijo por frame (colas FIFO, nada de recorrer
  arrays buscando trabajo: recorrer 18 filas costaba más que copiarlas).
- `set_bkg_tiles` es lento (~520 T/tile y espera STAT fuera de VBlank); en VBlank escribir directo a
  VRAM. Bucle C de copia ~76 T/tile; asm desenrollado 20 T/tile (`games/tetris/src/vram.s`).
- Guardia obligatoria: contador `vram_late` (LY < 144 al acabar `draw_vram()`) y un test que exige 0;
  los tiles escritos fuera de VBlank se pierden en silencio.
- Herramientas del arnés para tests: `gb.run_bot(step, progress, frames, on_stuck)` (bot que debe
  avanzar; devuelve peor frame y vram_late), `gb.selftest()` (asm de gbe == referencias C),
  `python harness/physics.py --game <juego>` (saltos/fosos/escalones exactos en 8.8, verificado
  contra la ROM: el diseño y el lint de niveles salen de ahí).
- Medir antes de optimizar: `p = gb.profile(["update", "draw_vram", ...])` en un test/script y
  `print(p.report())` da T-cycles máximos/medios por función (1 frame = 70224 T, 1 línea = 456 T).
  `gb.worst_frames(funcs, frames, step)` desglosa los peores frames: en games/shmup el pico eran 4
  costes medianos a la vez, no una función caliente. Regla propia < 120 líneas; el límite real es
  154 (por encima se pierde un frame).
- Librería de GBDK: `memcpy`/`memset` son asm (~10 T/byte); `memmove` (~190 T/byte) y `strncpy`
  (~290 T/byte) son C: evitarlos en el juego (games/dungeon: 11k T por un scroll de 60 bytes).
- Trampas medidas de SDCC: indexar con `int8_t` (`board[row_off[r] + i]`) ~466 T por acceso → usar
  punteros/`memcpy`; recalcular datos de una forma en cada llamada → cachear; `memcpy`/`memset` de
  GBDK son asm y rápidos.
- Objetos con arrays (struct of arrays), medido en games/platformer:
  - `arr[i]` con `i` variable recalcula la dirección en cada acceso (16 bits); con índice constante
    es una dirección fija. Bucles cortos sobre huecos fijos → desenrollar (spawn de 4 trozos: 8900 → 5300 T).
  - La suma posición += velocidad 8.8 en C cuesta ~1500 T; en asm ~240 T (`act_move` en
    `games/platformer/src/vram.s`, reutilizable). Igual para consultas al mapa (`mt_at`/`solid_at`).
  - Enemigos lentos: física a medio ritmo (mitad de ellos cada frame, paso doble); colisiones con el
    jugador sí cada frame. Como mucho 1 aparición de enemigo por frame (evita picos al reaparecer).
  - Sprites: escribir directo en `shadow_OAM` (`oam16`) y vaciar rangos con `memset`, no
    `set_sprite_tile/prop + move_sprite` por sprite.
- Interacciones entre muchos objetos (games/platformer, 5 enemigos de 150 → ~100 líneas): una vez por
  frame calcular la x **relativa a la cámara en 8 bits** (`x - camera_x + 32`; los objetos solo existen
  cerca de la pantalla) y hacer todas las colisiones y el dibujado en 8 bits. Solape simétrico
  |d| < N: `(uint8_t)(d + N - 1) < 2N - 1` (con `+N < 2N` el lado negativo choca y el positivo no).
  Pares una sola vez (`j > i`) y en frames alternos si los objetos son lentos.
- Bots de rendimiento: deben **comprobar que avanzan** (un bot atascado en la columna 45 dio un "85
  líneas" falso). El peor caso real está en las zonas con más enemigos y al cargar columnas.
- Números de diseño vs. realidad: medir la física (altura real de salto 62 px, no los 64 del GDD) y que
  el lint de niveles use lo medido; si no, el nivel puede ser imposible de terminar.
- `y` en u8 con sesgo: un salto alto puede pasar por debajo de 0 (0xC0-0xFF = encima de la pantalla);
  ninguna comprobación (fosos, filas) debe interpretar eso como "abajo".
- Profiler (`gb.profile`): solo ve funciones **no static**; una función que acaba con llamada final
  (`jp`) se atribuye a la llamada. Para perfilar el interior de un módulo, quitar `static`.

## Bancos de ROM
- `"banked_res": ["walls", "level1", "screen_title"]` en game.json mete esos assets generados en bancos
  conmutables (`#pragma bank 255` + `BANKREF(<stem>)`); con flags MBC5 + `-autobank`
  (`["-autobank", "-Wm-yt0x1B", "-Wm-yo8", "-Wm-ya1"]`). Se leen con `gbe_bank.c`
  (`bank_set_bkg_data(BANK(walls), ...)`, `bank_memcpy`), que vive en el banco 0. Probado en games/gbe_lab.
- El build **para** si un fichero con `#pragma bank N` llama a `SWITCH_ROM` (se desmapearía a sí mismo),
  y si con bancos algo del banco 0 (código, `_HOME`, `_GSINIT`...) pasa de 0x4000
  (SWITCH_ROM lo desmapearía), y **avisa** de las builds planas que lo pasan sin bancos
  (platformer y shmup hoy: funcionan mientras no se conmute). Código grande: funciones `BANKED`.
  Detalle: skill `gbdk` `banking.md`.

## Reglas de hardware DMG
Detalle completo: skill `gb-hardware`. Lo imprescindible:
- 70224 dots (T-cycles) por frame = **17556 M-cycles** (las tablas de instrucciones van en M-cycles).
  59.73 Hz, 154 líneas (144 visibles + 10 de VBlank), 456 dots por línea.
- VRAM inaccesible solo en modo 3; OAM inaccesible en modos 2 y 3 (usar DMA desde HRAM).
  Con GBDK: escribir tiles/mapas grandes con la pantalla apagada (`DISPLAY_OFF`) o
  repartir en varios frames; `move_sprite` escribe en shadow OAM (seguro en cualquier momento).
- Nunca escribir OAM directamente desde C (bug de corrupción de OAM en DMG).
- Apagar el LCD solo en VBlank (`DISPLAY_OFF` lo hace bien; escribir `LCDC_REG` a pelo no).
- 40 sprites, máx. 10 por línea. Ocultar sprites con Y=0 / Y≥160, **no** con X fuera de pantalla
  (siguen contando para el límite de 10). Sprites 8x8 u 8x16.
- 384 tiles en VRAM. Con LCDC bit4=1 fondo y sprites comparten los 256 de $8000-$8FFF;
  con bit4=0 el fondo usa $8800-$97FF y comparte 128 con los sprites.
- Mapa de fondo 32x32 tiles, pantalla 20x18. Una paleta de fondo, dos de sprites (color 0 transparente).
  OBP0/OBP1 no se inicializan al arrancar: fijarlas siempre. WRAM y SRAM arrancan con basura.
- WRAM 8 KB, HRAM 127 bytes. ROM 32 KB sin MBC; más con MBC5 (preferible a MBC1).
- Saves: habilitar SRAM solo durante el acceso y validar con firma + checksum: `gbe_save.c` ya lo hace;
  los tests apagan y encienden con la SRAM (`ram = gb.power_off(); GB(rom, ram=ram)`).
- Los tests en PyBoy no detectan bugs exclusivos del hardware real ni de timing a mitad de frame.

## Reglas de C con SDCC (para que sea rápido)
Detalle y mediciones: skill `gbdk` (`performance.md`). Lo imprescindible:
- `uint8_t` por defecto; 16 bits solo cuando haga falta. Evitar `int` (16 bits con signo).
- División por potencia de 2: escribir el shift a mano (`x >> 3`); `x / 8` genera un bucle de 16 bits
  aunque sea `uint8_t`. `% 8` y multiplicar por constante sí salen bien. Nada de mul/div por variable en el bucle.
- Acceso más barato: global/struct global fijo (13 instr.) < puntero a struct (21) < array de structs por índice (34).
- Evitar recursión, `printf` en el juego, floats, y funciones con muchos parámetros.
- Datos constantes como `const` (van a ROM, no gastan RAM).
- Ante la duda, **medir**: mirar el asm generado (`.lst` con ciclos) en vez de suponer.

## Gotchas de GBDK
- Al entrar en `main()` el LCD ya está encendido pero BG y sprites apagados (`SHOW_BKG`/`SHOW_SPRITES`).
- `OBP1_REG` arranca a 0x1B (sombras invertidas): fijar paletas siempre.
- `gb/gb.h` no incluye `gb/metasprites.h`.
- png2asset: sprites 8x16 por defecto (`-spr8x8` si no); usar PNG indexado + `-keep_palette_order`
  para controlar qué color es cada índice.
- Banking: `-autobank` exige `-Wm-yt<tipo>`; sin `-Wm-ya<N>` la cabecera dice "sin RAM".
  Receta 64 KB MBC1 + save: `["-autobank", "-Wm-yt0x03", "-Wm-yo4", "-Wm-ya1"]`.

## Ensamblador
Detalle: skill `gb-asm` (opcodes con ciclos, sintaxis, convención de llamada verificada, optimización,
test de equivalencia C vs asm, medición exacta de ciclos con PyBoy). Lo imprescindible:
- GBDK usa sintaxis `sdasgb` (no RGBDS): `#` delante de inmediatos, símbolos C con `_` (`_player_x`),
  `ld a,(hl+)`, `ldh`, `ldhl sp,#n`. El apéndice ASGB del asmlnk manual está desfasado (`ldi`/`ldd` no existen).
- Ficheros `.s` en `src/` se compilan automáticamente.
- Convención `__sdcccall(1)` (verificada en GBDK 4.5.0, el manual de SDCC se equivoca en parte):
  1er arg en A (8 bits) o DE (16 bits), 2º en E o DE; retorno 8 bits en A, 16 bits en BC.
  Ningún registro se preserva; los args en pila los retira el callee.
- `.bndry` se pierde al enlazar: tablas alineadas a 256 necesitan su propia área con `-Wl-b_AREA=0x..00`.
- Ciclos estáticos: `lcc -Wa-l` genera `.lst` con ciclos por instrucción.
- Antes de portar a asm: medir, y tener un test que compare salida C vs asm con las mismas entradas.
- Presupuesto VBlank: ~4560 T totales, GBDK usa ~1136 en su ISR → ~3400 T para código propio.
