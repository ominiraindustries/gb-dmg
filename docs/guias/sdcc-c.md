# C rápido con SDCC y gotchas de GBDK

Reglas para que el C de SDCC 4.5 (GBDK-2020 4.5.0) sea rápido y no falle. Detalle y mediciones: skill `gbdk`
(`performance.md`, `gotchas.md`); API de GBDK: `docs/ref/gbdk/api/`; asm: skill `gb-asm` y `docs/ref/sm83-opcodes.md`.

## Reglas de C con SDCC
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

Origen: sección de `CLAUDE.md` movida aquí el 2026-11-24 (CLAUDE.md enlaza esta guía). Las cifras son medidas en los juegos citados.
