# Pruebas: PyBoy para lo rápido, Mesen 2 para el día a día, SameBoy para la firma, Emulicious para depurar

Cuatro emuladores, cada uno para una cosa:

| Nivel | Emulador | Para qué | Comando |
|---|---|---|---|
| 1. Tests y bots | PyBoy (`harness/gbtest.py`) | toda la lógica con pytest, bots de miles de frames, perfil por función | `python -I harness/gb.py test <juego>` |
| 2. Timing diario | Mesen 2 (`harness/gbrun.py`) | confirmar raster, LYC/STAT, presupuesto de VBlank, OAM DMA mientras se trabaja | `python -I harness/gbrun.py <juego> ...` |
| 3. Firma de exactitud | SameBoy (`harness/sbrun.py`) | **antes de dar algo por hecho** (`resolved`): la misma ejecución que en gbrun, en el emulador más exacto | `python -I harness/sbrun.py <juego> ...` |
| 4. Depurar a mano | Emulicious (`gb.py debug`) | puntos de ruptura, VRAM/OAM, paso a paso en C desde VS Code (sólo el usuario: abre ventana) | `python -I harness/gb.py debug <juego> [--source]`, guía [depurar-emulicious.md](depurar-emulicious.md) |

Regla: un hito, un efecto de raster o un cambio de timing no se marca `resolved` sin una ejecución de `sbrun` con sus
checks y capturas (además de los tests de PyBoy). Si SameBoy y Mesen discrepan, manda SameBoy (tabla de exactitud más
abajo) y se anota como lección.

Los ejecutores headless leen las globales del juego por nombre (las no `static`, vía el
`.noi` del enlazador) y cuentan el frame 1 desde el mismo punto (el primer frame tras el arranque: PyBoy no
ejecuta boot ROM, `gbrun` se salta la de Mesen, unos 84 frames con el logo, y `sbrun` la boot ROM libre de SameBoy, 85).
Ojo con la excepción de `sbrun` en "Diferencias medidas".

| | PyBoy (`harness/gbtest.py`) | Mesen 2 (`harness/gbrun.py`) |
|---|---|---|
| Para qué | tests de lógica con pytest, bots de miles de frames, perfil por función, lecturas coherentes de WRAM | confirmar lo que depende del timing: cortes LYC/STAT, cambios de registro a mitad de frame, si las copias a VRAM caben en el VBlank, DMA de OAM, sonido |
| Cómo | `python -I harness/gb.py test <juego>` (tests en `games/<juego>/tests/`) | `python -I harness/gbrun.py <juego> [opciones]` |
| Velocidad | muy rápido, en proceso | ~1 s de arranque + ~1000 frames/s; un proceso por ejecución |
| Exactitud | buena para la CPU y el PPU por línea; **no** detecta fallos de timing a mitad de frame ni de hardware real | Mesen 2 emula ciclo a ciclo; modelo DMG forzado. Pasa 63/66 de Mooneye y dmg-acid2 (PyBoy 60/66 y falla dmg-acid2): tabla de exactitud más abajo |
| Entrada | `gb.hold("right", 20)`, `gb.tap("a")`, bots `GB.human` | guion `--input "30-40:start;60-90:right+a"` |
| Estado | `gb.u8("player_x")` (foto de la WRAM en el último `vsync()` del tramo) | `--check`, `--check-at`, `--expect` (cada frame de un rango), `--watch` a CSV, `--dump` |
| Pantalla | `gb.screenshot()`, `gb.vram_errors()`, `gb.mockup_errors()`, `gb.screen_tiles()` | `shot_NNNN.png` (160×144), `--nonblank`, `--golden DIR` píxel a píxel |
| SRAM | `ram = gb.power_off(); GB(rom, ram=ram)` | `--sram-out f.sav` y en la siguiente ejecución `--sram-in f.sav` (o `fresh`) |

Regla: **todo test va en PyBoy**; se añade una ejecución de Mesen cuando el cambio toca timing (ISR de LCD, raster,
presupuesto de VBlank, colas de VRAM, OAM DMA) o cuando PyBoy y lo que ve el usuario no coinciden. No se dan por buenos
efectos de raster solo con PyBoy.

## gbrun.py

```text
python -I harness/gbrun.py <juego | ruta.gb> [--frames N] [--shot F,F] [--input SPEC] [--check SPEC,...]
       [--check-at "F:SPEC;F2:SPEC"] [--expect "LOC OP V@F1-F2"] [--watch LOC,... --every N]
       [--dump wram|vram|oam|hram|sram|rom|bus[:start:len]] [--nonblank] [--golden DIR [--update-golden]]
       [--ram zeros|ones|random] [--model dmg|cgb|sgb] [--boot] [--sram-in F|fresh] [--sram-out F] [--out DIR]
```

- `LOC` = símbolo del `.noi` (con o sin `_`), con `+n`/`-n` y `.w` para 16 bits, o `mem:dirección`
  (`bus:0xFF40` = LCDC por el bus de la CPU, `hram:0`, `oam:4`). Operadores `== != <= >= < >`.
- Sale con 0 si todo pasa, 1 si falla un check/expect/golden/captura en blanco, 2 si Mesen no produjo resultado,
  3 si los argumentos están mal (se avisa antes de arrancar Mesen).
- Salida en `games/<juego>/build/mesen/` (o `--out`): capturas, `result.json`, `watch.csv`, `*.bin`.
- Fuerza siempre el modelo DMG, sin mezcla de frames, RAM a ceros y sin filtro de vídeo: la configuración de Mesen del
  usuario (que prefiere GBC, mezcla frames y RAM aleatoria) no cambia el resultado. `--ram random` imita la DMG real.
- Mesen: `tools/mesen/Mesen.exe` (ignorado; se puede copiar ahí) o, si no está, la copia del proyecto SNES
  (`Desktop/SNES/tools/mesen/Mesen.exe`); `--mesen` o `GBRUN_MESEN` para otra. Comparte con `snesrun` el cerrojo de
  ejecución (una ejecución de Mesen a la vez en la máquina).
- Pruebas del propio ejecutor: `python -I -m pytest harness/tests -q` (parseo, códigos de salida, golden y que cuenta los
  frames igual que PyBoy).

### Ejemplos comprobados (2026-11-24)

```sh
# hello: 20 frames de DERECHA mueven el sprite 20 px (igual que en PyBoy)
python -I harness/gbrun.py hello --frames 60 --input "10-29:right" --check "player_x==96,player_y==68" \
    --check-at "9:player_x==76" --watch player_x --every 10 --nonblank

# platformer: título, START, 13 s corriendo y saltando; el HUD con corte LYC se ve bien en Mesen,
# max_frame_lines = 78 y vram_late = 0 (el mismo presupuesto que miden los tests de PyBoy)
python -I harness/gbrun.py platformer --frames 900 \
    --input "60:start;120-900:right;150-160:a;300-310:a;450-460:a;600-610:a;750-760:a" \
    --shot 100,400,900 --check "vram_late==0,max_frame_lines<154" --watch "max_frame_lines,camera_x.w" --every 150
```

## sbrun.py (SameBoy)

Misma interfaz y mismos códigos de salida que `gbrun.py` (0 pasa, 1 falla un check/expect/golden/captura en blanco,
2 SameBoy no dio resultado, 3 argumentos mal, antes de arrancar). Reutiliza los parsers de `gbrun` (`LOC`, checks,
guion de entrada, golden), así que una línea de `gbrun` vale tal cual cambiando el nombre del script.

```text
python -I harness/sbrun.py <juego | ruta.gb> [--frames N] [--shot F,F] [--input SPEC] [--check SPEC,...]
       [--check-at "F:SPEC;F2:SPEC"] [--expect "LOC OP V@F1-F2"] [--watch LOC,... --every N]
       [--dump wram|vram|oam|hram|sram|rom|bus[:start:len]] [--nonblank] [--golden DIR [--update-golden]]
       [--ram zeros|ones|random] [--model dmg|cgb|sgb] [--boot] [--sram-in F|fresh] [--sram-out F] [--out DIR]
       [--regs "b==3,c==5,..."] [--rebuild]
```

- Salida en `games/<juego>/build/sameboy/` (o `--out`): `shot_NNNN.png`, `result.json` (con `regs`), `watch.csv`, `*.bin`.
- Las capturas salen con **la misma paleta gris que Mesen** (00/6B/B5/FF), así que un diff entre los dos es de
  emulación o de frame, no de paleta. Pero la captura `N` de sbrun es la imagen que el LCD acaba de pintar al cerrar el
  frame `N`, y la de gbrun es la del frame anterior: **`sbrun shot N` = `gbrun shot N+1`** (medido en hello: 0 píxeles
  de diferencia con ese desfase, 38 sin él). Las lecturas de memoria sí coinciden en el mismo `N`. Cada emulador lleva
  su carpeta golden.
- Sólo en sbrun: `--regs` comprueba registros de la CPU al final (`a f b c d e h l af bc de hl sp pc`), p. ej. la firma
  de éxito de Mooneye `b==3,c==5,d==8,e==13,h==21,l==34`.
- Le falta respecto a gbrun: `--mesen` (no aplica) y el cerrojo entre procesos (no hace falta: SameBoy no comparte
  configuración, se pueden lanzar varios a la vez). `--model dmg` es DMG-B con la boot ROM libre de SameBoy.
- Cómo funciona: `harness/sameboy/sbheadless.c` es un driver de C mínimo sobre el núcleo de SameBoy (lee un plan de
  frames: teclas, capturas, lecturas de memoria, volcados, SRAM). `sbrun` lo compila solo la primera vez con el `gcc`
  de MinGW contra `tools/sameboy/src` (~30 s) y lo deja en `tools/sameboy/build/sbheadless.exe`; `--rebuild` lo
  fuerza tras actualizar SameBoy. Velocidad: 3000 frames de platformer en 3,3 s con Python incluido (~1000 frames/s;
  el driver activa el modo turbo de SameBoy, que si no duerme para ir a 60 fps).
- El `sameboy_tester` oficial también está compilado (`tools/sameboy/build/sameboy_tester.exe`, con las boot ROMs
  al lado), pero sólo sabe correr N segundos y guardar un BMP: no tiene guion de entrada ni lectura de memoria.
- Pruebas del ejecutor: `python -I -m pytest harness/tests/test_sbrun.py -q`.

Instalar SameBoy (si falta `tools/sameboy`): bajar de https://github.com/LIJI32/SameBoy/releases el
`sameboy_winsdl_vX.zip` (descomprimir en `tools/sameboy/bin/`) y el tarball del tag (en `tools/sameboy/src/`);
comprobar el SHA-256 con `SHA2-256SUMS`. Versión y licencia: `docs/ref/README.md`.

### Ejemplos comprobados (2026-11-24)

```sh
python -I harness/sbrun.py hello --frames 60 --input "10-29:right" --check "player_x==96,player_y==68" \
    --check-at "9:player_x==76" --watch player_x --every 10 --nonblank
python -I harness/sbrun.py platformer --frames 900 \
    --input "60:start;120-900:right;150-160:a;300-310:a;450-460:a;600-610:a;750-760:a" \
    --shot 100,400,900 --check "vram_late==0,max_frame_lines<154" --watch "max_frame_lines,camera_x.w" --every 150
```

Resultados frente a Mesen: hello da los mismos valores en cada frame (`player_x` 76 → 96) y las mismas capturas con el
desfase de un frame de arriba. platformer: los mismos checks (`vram_late = 0`, `max_frame_lines = 78`), capturas 100 y
400 iguales (pantallas quietas); la del 900 difiere en 662 píxeles porque la cámara va 2 px por detrás (siguiente
apartado).

### Diferencias medidas: el número de frame tras apagar el LCD

SameBoy y Mesen numeran distinto los frames **mientras el LCD está apagado**: cada vez que el juego apaga y enciende el
LCD (carga de pantalla), SameBoy puede contar un frame más. En platformer, `sys_time` (contador de VBlank) va 2 frames
por detrás en SameBoy desde el arranque y 3 desde la pantalla de título (medido frame a frame con `--watch sys_time.w
--every 1` en los dos). No es un fallo del juego ni de exactitud de la CPU: es la definición de "frame" sin LCD. Por eso:

- Dentro de un tramo con el LCD encendido, los dos coinciden frame a frame.
- Para comparar ejecuciones entre emuladores, comparar estados del juego (`sys_time`, posiciones) o capturas tras un
  tramo estable, no el mismo número de frame después de cambios de pantalla; y la entrada por frame se desplaza igual.
- Las carpetas golden se crean por emulador si la ejecución cruza cambios de pantalla.

### Exactitud de los tres emuladores (ROMs de prueba libres, 2026-11-24)

Mooneye Test Suite `mts-20260714-0944-31510e1` (MIT, Gekkio): las 66 ROMs de `acceptance/` que valen para DMG
(se excluyen las de dmg0, mgb, sgb y `-S`), 1200 frames cada una, éxito = registros B C D E H L = 3 5 8 13 21 34.
dmg-acid2 v1.0 (MIT, Matt Currie): PPU (prioridades, ventana, sprites de 8×16, límite de 10), comparado por tonos con
`img/reference-dmg.png`. ROMs en `tools/testroms/` (ignorado). Las de Blargg no se usan: no tienen licencia explícita.

| Prueba | PyBoy | Mesen 2 | SameBoy |
|---|---|---|---|
| Mooneye acceptance (66) | 60 | **63** | **63** |
| Fallan | `boot_regs-dmgABC`, `bits/unused_hwio-GS`, `ppu/intr_2_mode0_timing_sprites` y las 3 de abajo | `boot_div-dmgABCmgb`, `boot_hwio-dmgABCmgb`, `serial/boot_sclk_align-dmgABCmgb` | las mismas 3 que Mesen |
| dmg-acid2 (píxeles distintos de la referencia) | 130 (ojo derecho y una línea: prioridad de sprites) | **0** | **0** |

- Las 3 que fallan en todos miden el estado exacto del DIV/serie al salir de la boot ROM **de Nintendo**; Mesen y
  SameBoy usan su propia boot ROM (libre) y PyBoy ninguna. No afectan a nuestros juegos (no dependen de la fase del DIV
  al arrancar). Pasarían con la boot ROM oficial, que no se baja (copyright de Nintendo).
- `ppu/intr_2_mode0_timing_sprites` necesita más de 300 frames: con 300 fallaba también en SameBoy.
- Con estas ROMs **Mesen y SameBoy empatan**; PyBoy falla en el timing de modo 0 con sprites (la duración del modo 3
  según los sprites de la línea) y en la prioridad de sprites de dmg-acid2: justo lo que afecta a rasters con sprites.
  SameBoy queda como firma porque su README declara que pasa todas las de Blargg, todas las de Mooneye ("algunas
  necesitan la boot ROM original", justo las 3 de arriba) y las de Wilbert Pol, emula el LCD al T-ciclo (demos como
  Prehistorik Man), y es libre y compilable aquí; Mesen es más cómodo para el día a día (Lua, depurador).
- Medido el 2026-11-24 con un script de un solo uso (PyBoy en proceso con `register_file`; Mesen con un Lua propio que
  lee `emu.getState()["cpu.b"]`…; SameBoy con `sbrun --regs`).

## Qué mirar después de una ejecución

1. El código de salida y las líneas `FAIL:`.
2. Las capturas con Read (no basta con los asserts: CLAUDE.md, "los tests comprueban lo que se ve").
3. Si PyBoy y Mesen discrepan en algo de timing, se repite en SameBoy (`sbrun`) y manda SameBoy; anótalo como lección
   (el fallo es real en hardware).
