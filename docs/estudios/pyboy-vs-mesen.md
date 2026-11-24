# PyBoy frente a Mesen 2 en un juego real (2026-11-24)

Pregunta: ¿los dos ejecutores headless del arnés (`harness/gbtest.py` con PyBoy y `harness/gbrun.py` con Mesen 2) dan los
mismos números en un juego con HUD por corte LYC, scroll y presupuesto de frame? Si sí, PyBoy sirve para los tests
rápidos y Mesen solo hace falta para lo que depende del timing fino.

## Método

ROM: `games/platformer/build/platformer.gb` (gbe_video con `hud_cut`, gbe_map, actores). Mismo guion en los dos: START
en el frame 60, DERECHA desde el 120 hasta el 900, A en 150-160, 300-310, 450-460, 600-610 y 750-760. Frame 1 = primer
frame tras el arranque en los dos (PyBoy sin boot ROM; `gbrun` se salta los 84 frames de la boot ROM de Mesen).

```sh
python -I harness/gbrun.py platformer --frames 900 \
    --input "60:start;120-900:right;150-160:a;300-310:a;450-460:a;600-610:a;750-760:a" \
    --shot 100,400,900 --check "vram_late==0,max_frame_lines<154" --watch "max_frame_lines,camera_x.w" --every 150
```

PyBoy: el mismo guion frame a frame con `pyboy.button_press/release` y `gb.frames(1)`, leyendo `gb.u8`/`gb.u16`.

## Resultado

| Frame | `max_frame_lines` PyBoy | Mesen | `camera_x` PyBoy | Mesen | `vram_late` (los dos) |
|---|---|---|---|---|---|
| 150 | 24 | 24 | 0 | 0 | 0 |
| 300 | 64 | 64 | 19 | 22 | 0 |
| 450 | 78 | 78 | 207 | 209 | 0 |
| 600 | 78 | 78 | 249 | 249 | 0 |
| 750 | 78 | 78 | 0 | 0 | 0 |
| 900 | 78 | 78 | 132 | 135 | 0 |

- **El presupuesto de frame coincide exactamente** (líneas por frame: 24, 64, 78) y ninguno de los dos ve copias fuera
  del VBlank. Las cifras de rendimiento medidas con PyBoy en los tests valen.
- **La posición difiere 2-3 px** desde el primer tramo de carrera: el mismo guion llega con un desfase de 1-3 frames
  (latencia de entrada distinta: PyBoy procesa un botón pulsado antes de `frames(1)` en la lógica que acaba en el frame
  siguiente, CLAUDE.md). Los tests que comparan posiciones entre ejecutores deben anclarse a un contador del juego, no
  al número de frame (lección tick-anchored-tests de `docs/guias/lecciones-snes.md`).
- La captura de Mesen muestra el HUD de 2 filas fijo y el nivel desplazado (el corte LYC funciona en un emulador
  exacto). En hello, 20 frames de DERECHA dan exactamente +20 px en los dos (`harness/tests/test_gbrun.py`).

## Sin medir

- Casos donde los dos deberían discrepar (escrituras a VRAM en el modo 3, STAT bloqueado, efectos de raster de varias
  bandas): falta una ROM de prueba propia que los provoque a propósito.
- Coste de `gbrun` frente a PyBoy por frame en juegos largos (Mesen: ~1 s de arranque; los 900 frames tardaron unos
  segundos).
