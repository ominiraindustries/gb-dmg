# VBlank y copias a VRAM

Qué cabe en el VBlank, cómo preparar fuera y copiar dentro, y cómo copiar cuando no cabe. Fuentes: Pan Docs
(`docs/ref/pandocs/17_Rendering.md`, `67_Accessing_VRAM_and_OAM.md`, `13_LCDC.md`), `docs/guias/rendimiento-vram.md`
(lo medido en tetris, platformer, faro, dungeon), `harness/common/README.md`.

---

## VB1 · El presupuesto del VBlank con GBDK
<!-- tags: vblank, vram, presupuesto -->

**Problema** · La VRAM no se puede escribir en el modo 3; lo que se escriba entonces se pierde **en silencio**. El sitio
seguro para escribir mucho es el VBlank, que es corto.

**Cómo lo resolvían** · Pan Docs: VBlank = líneas 144-153 = 10 × 456 = **4560 T** por frame. La VRAM también se puede
escribir en los modos 0 y 2 de cada línea, pero son ventanas de decenas de ciclos.

**En gbe** · Bucle fijo: `vsync()` → copias (solo copiar) → `frame_vram_check()` → lógica → sprites → `frame_end()`. Con
GBDK `vsync()` vuelve en LY ≈ 146 después de su ISR (~1100 T: DMA de OAM incluida): quedan **~3400-3600 T** para copias
propias. Decidir el presupuesto de copia antes de empezar a copiar (dungeon: el texto se decidía después y se pasaba).

**Medido en nuestros juegos** · Coste por tile de mapa: `set_bkg_tiles` ~520 T (y espera a STAT fuera de VBlank), bucle C
~76 T, asm desenrollado **20 T** (`games/tetris/src/vram.s`); cola `gbe_vq` ~20 T/tile + ~90 T por entrada; datos de tile
(16 B) con `tile_copy16` ~330 T; `memcpy` de GBDK ~30 T/byte en copias cortas.

**Estado** · patrón (bucle de `gbe_frame`)

---

## VB2 · Preparar fuera del VBlank, copiar dentro con colas
<!-- tags: vblank, colas, vram -->

**Problema** · Convertir un número o un texto a tiles, o buscar qué hay que redibujar, gasta el VBlank en algo que no es
copiar.

**Cómo lo resolvían** · Separar productor y consumidor: la lógica deja en WRAM los bytes listos y su destino; el VBlank
solo los copia, con un tope por frame, en orden FIFO. Nada de recorrer arrays buscando trabajo (recorrer 18 filas
costaba más que copiarlas, tetris).

**En gbe** · `gbe_vq` (`vq_push()`, `vq_push_fill()`, `vq_draw_vram()`, `vq_budget`), `gbe_tiles` (datos de tile desde
cualquier banco, `tiles_budget` = 2 por VBlank), `gbe_map`/`gbe_vmap`/`gbe_world` con su propia cola de columnas o filas,
`vram_mt4_list` (metatiles 2x2).

**Medido en nuestros juegos** · faro: 18 entradas de 1 tile por frame perdían tiles → filas enteras, nunca columnas de 1
tile; la cola para en LY 150 (con 152, 32 tiles acababan en la línea 1). world_lab: 4 tiles con `memcpy` de GBDK se
pasaban del VBlank (lo cazó `vram_late`).

**Estado** · hecho

---

## VB3 · Copiar tiles fuera del VBlank
<!-- tags: vram, lcd-off, hblank, doble-buffer -->

**Problema** · Cargas grandes (una pantalla nueva, un tileset, una vista 3D) no caben en 3400 T.

**Cómo lo resolvían** · Tres salidas (Pan Docs, "Accessing VRAM and OAM"): **apagar el LCD** (la VRAM es libre; solo se
puede apagar dentro del VBlank, apagarlo fuera puede dañar la pantalla real); **repartir en varios frames** dibujando en
lo que no se ve (el otro mapa de fondo y cambiar el bit 3 de LCDC, o filas fuera de la ventana de scroll); **escribir en
el HBlank** (modo 0, 87-204 T por línea, comprobando STAT antes de cada escritura: es lo que hace `set_bkg_tiles` de
GBDK, por eso cuesta ~520 T/tile). GBDK trae además `hblank_copy_vram()` (`gb/hblankcpy.h`).

**En gbe** · LCD apagado: `gbe_screen` (`screen_build()` con fundido) y `lcd_off_redraw_begin()`. Varios frames:
`gbe_bgbuf` (lienzo de 20 de ancho copiado N filas por VBlank al mapa oculto y cambio de mapa). HBlank: no hay módulo
propio (sin medir `hblank_copy_vram`).

**Medido en nuestros juegos** · dungeon: 4 filas por VBlank = 2,6k T, cambio de mapa tras 3 VBlanks.

**Estado** · hecho (LCD apagado y doble búfer); copia en HBlank: sin medir

---

## VB4 · Guardia: las copias que se salen del VBlank se cuentan
<!-- tags: vblank, tests, vram_late -->

**Problema** · Un tile escrito en el modo 3 se pierde sin error, y basta con que un frame largo retrase el `vsync()`.

**Cómo lo resolvían** · Medir LY al acabar las copias y contar las veces que ya era < 144 (la pantalla visible había
empezado).

**En gbe** · `gbe_frame`: `frame_vram_check()` incrementa `vram_late` y guarda `vram_late_ly0` (dónde empezaron) y
`vram_late_ly` (dónde acabaron); el juego pone `frame_vsync_ly = LY_REG` tras `vsync()`. Todo test de juego exige
`vram_late == 0` (y en Mesen: `--check vram_late==0`). Tras un frame largo, `if (LY_REG < 144) vsync();` pierde un frame
pero ninguna copia sale fuera.

**Medido en nuestros juegos** · Lo cazó en world_lab (memcpy de GBDK) y en faro (colas de 1 tile).

**Estado** · hecho (`gbe_frame`)
