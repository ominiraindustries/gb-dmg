# Pruebas: PyBoy para lo rápido, Mesen 2 para lo exacto

El repositorio tiene dos ejecutores headless. Los dos leen las globales del juego por nombre (las no `static`, vía el
`.noi` del enlazador) y los dos cuentan el frame 1 desde el mismo punto (el primer frame tras el arranque: PyBoy no
ejecuta boot ROM y `gbrun` se salta la de Mesen, unos 84 frames con el logo).

| | PyBoy (`harness/gbtest.py`) | Mesen 2 (`harness/gbrun.py`) |
|---|---|---|
| Para qué | tests de lógica con pytest, bots de miles de frames, perfil por función, lecturas coherentes de WRAM | confirmar lo que depende del timing: cortes LYC/STAT, cambios de registro a mitad de frame, si las copias a VRAM caben en el VBlank, DMA de OAM, sonido |
| Cómo | `python -I harness/gb.py test <juego>` (tests en `games/<juego>/tests/`) | `python -I harness/gbrun.py <juego> [opciones]` |
| Velocidad | muy rápido, en proceso | ~1 s de arranque + ~1000 frames/s; un proceso por ejecución |
| Exactitud | buena para la CPU y el PPU por línea; **no** detecta fallos de timing a mitad de frame ni de hardware real | Mesen 2 emula ciclo a ciclo y está pensado para la exactitud (PyBoy prioriza la velocidad); modelo DMG forzado. Sin medir aún con ROM de prueba de timing qué casos separan a los dos |
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

## Qué mirar después de una ejecución

1. El código de salida y las líneas `FAIL:`.
2. Las capturas con Read (no basta con los asserts: CLAUDE.md, "los tests comprueban lo que se ve").
3. Si PyBoy y Mesen discrepan en algo de timing, manda Mesen; anótalo como lección (el fallo es real en hardware).
