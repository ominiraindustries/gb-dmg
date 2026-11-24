# Rendimiento y VRAM (medido en los juegos)

Cómo cabe un juego en 70224 T por frame y en ~3400 T de VBlank libres con GBDK. Todo lo que hay aquí se midió en un
juego del repositorio (`games/tetris`, `platformer`, `shmup`, `faro`, `dungeon`); las técnicas por problema están en
`docs/tecnicas/` (VBlank: [vblank.md](../tecnicas/vblank.md); sprites: [sprites.md](../tecnicas/sprites.md)) y
las piezas ya hechas en `docs/guias/que-usar.md`.

- Bucle: `vsync()` → `draw_vram()` (solo copiar a VRAM) → input → `update()` → sprites → `measure_frame()`.
  `vsync()` vuelve en LY≈146: quedan ~3600 T de VBlank para `draw_vram()`.
- **Preparar tiles fuera del VBlank, dentro solo copiar**: convertir números/textos a tiles en `update()`
  (buffers), y en `draw_vram()` copiar con un presupuesto fijo por frame (colas FIFO, nada de recorrer
  arrays buscando trabajo: recorrer 18 filas costaba más que copiarlas).
- `set_bkg_tiles` es lento (~520 T/tile y espera STAT fuera de VBlank); en VBlank escribir directo a
  VRAM. Bucle C de copia ~76 T/tile; asm desenrollado 20 T/tile (`games/tetris/src/vram.s`).
- Guardia obligatoria: contador `vram_late` (LY < 144 al acabar `draw_vram()`) y un test que exige 0;
  los tiles escritos fuera de VBlank se pierden en silencio. Para saber por qué: el juego pone
  `frame_vsync_ly = LY_REG` tras `vsync()` y gbe guarda `vram_late_ly0` (dónde empezaron las copias) y
  `vram_late_ly` (dónde acabaron). Instrumentar con más código cambia el timing y el fallo desaparece.
- Cola de VRAM (`vq`): cada entrada cuesta ~90 T además de ~20 T/tile: filas enteras, nunca columnas
  de 1 tile (faro: 18 entradas por frame perdían tiles). Para en LY 150 (con 152, 32 tiles acababan en
  la línea 1).
- Herramientas del arnés para tests: `gb.run_bot(step, progress, frames, on_stuck)` (bot que debe
  avanzar; devuelve peor frame y vram_late), `gb.selftest()` (asm de gbe == referencias C),
  `python harness/physics.py --game <juego>` (saltos/fosos/escalones exactos en 8.8, verificado
  contra la ROM: el diseño y el lint de niveles salen de ahí).
- Medir antes de optimizar: `p = gb.profile(["update", "draw_vram", ...])` en un test/script y
  `print(p.report())` da T-cycles máximos/medios por función (1 frame = 70224 T, 1 línea = 456 T).
  `gb.worst_frames(funcs, frames, step)` desglosa los peores frames: en games/shmup el pico eran 4
  costes medianos a la vez, no una función caliente. Regla propia < 120 líneas; el límite real es
  154 (por encima se pierde un frame).
- Librería de GBDK: `memcpy`/`memset` son asm (~10 T/byte en copias largas, pero ~30 T/byte en copias cortas
  o con banco: 16 B por tile ~480 T, 128 B con `bank_memcpy` 4.2k; en VBlank usar copias asm desenrolladas como
  `tile_copy16` de gbe_tiles.s, ~20 T/byte); `memmove` (~190 T/byte) y `strncpy`
  (~290 T/byte) son C: evitarlos en el juego (games/dungeon: 11k T por un scroll de 60 bytes).
- SDCC 4.5 compila mal `(uint16_t)y << 4` si `y` es un `uint8_t` local cuya dirección se pasó a una
  función (`get(&x, &y)`): lo hace en 8 bits. Copiar antes a un u16 (`v = y; v <<= 4;`); detalle en gbdk
  `gotchas.md`.
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
  (`jp`) se atribuye a la llamada. Para perfilar el interior de un módulo, quitar `static`. Entiende
  código en bancos (empareja la vuelta por SP: todas las BANKED vuelven por el mismo trampolín).
  Ante cifras raras, la verdad son las **líneas reales con y sin cada parte** (bits de depuración que
  apagan módulos, A/B de `frame_lines`): en games/faro el profiler viejo culpaba a quien no era.
- Lo medido en games/faro (campo con 16 actores): un bucle de SDCC sobre 16 huecos cuesta 150-300 T por
  vuelta **aunque el hueco esté vacío** → listas compactas de los activos (`cr_ids`), no recorrer todos;
  una consulta a una tabla en banco por llamada BANKED ~500 T → copiar a WRAM lo que se lee cada frame;
  un objeto que aparece y desaparece en bucle (aparición más lejos que la distancia de borrado) o dos
  especies robándose un hueco de sprites se comen 25 líneas sin que nada se vea: comprobar que lo
  que se crea **se crea** (contadores) antes de optimizar.
- WRAM: la pila crece desde $E000 hacia los globales; el build para si quedan < 512 bytes. Búferes
  grandes que solo usa una cosa (autoprueba, guardado) → zona compartida o lectura a trozos.
- `vsync()` tras un frame largo vuelve en mitad de la pantalla: `if (LY_REG < 144) vsync();` justo
  después (pierde un frame pero ninguna copia a VRAM sale fuera de VBlank).

Origen: sección de `CLAUDE.md` movida aquí el 2026-11-24 (CLAUDE.md enlaza esta guía). Las cifras son medidas en los juegos citados.
