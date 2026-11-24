# HUD, ventana y efectos de raster

Cambios de registros a mitad de frame: el HUD fijo sobre un fondo que se desplaza, paralaje con un solo fondo y
fundidos con las paletas. Fuentes: Pan Docs (`docs/ref/pandocs/12_Window.md`, `14_STAT.md`, `15_Scrolling.md`,
`16_Palettes.md`, `17_Rendering.md`, `26_Interrupt_Sources.md`), `harness/common/src/gbe_video.c`, `gbe_raster.c/.s`,
juegos `platformer`, `shmup`. **Todo lo de este capítulo se confirma en Mesen** (`docs/guias/pruebas.md`): PyBoy no
reproduce el timing a mitad de frame.

---

## HR1 · Corte LYC/STAT a mitad de frame para el HUD
<!-- tags: raster, lyc, stat, hud, interrupciones -->

**Problema** · La DMG tiene un solo fondo: si se desplaza, el HUD se desplaza con él. Hace falta que una parte de la
pantalla use otros registros (ventana encendida, sprites apagados, otro SCX).

**Cómo lo resolvían** · Pan Docs (STAT, Interrupt Sources): con `LYC = línea` y el bit 6 de STAT, la interrupción LCD
salta cuando LY == LYC. El modo 3 dura entre 172 y 289 T según los sprites y el SCX, así que el cambio se escribe en el
**HBlank** de la línea anterior al corte: interrupción en LYC = línea − 1, esperar al modo 0 y escribir. Cuidado con el
"bloqueo de STAT": si otra fuente de STAT ya tiene la señal alta, el flanco de LYC no genera interrupción. GBDK
instala manejadores con `add_LCD()` y su cadena termina con `nowait_int_handler` (sin esperar a STAT).

**En gbe** · `gbe_video`: `video_init(cut_line, bgp, obp0, obp1)` instala las ISR; con `hud_cut = 1` la ventana se ve
por encima de `cut_line` y los sprites solo por debajo; `bgp_below`/`bgp_below_on` cambian la paleta del fondo bajo el
corte (destellar el campo, no el HUD). Los registros se escriben a través de sombras (`scx_shadow`...): el build para si
un juego con gbe_video escribe `SCX_REG`/`BGP_REG` directamente.

**Medido en nuestros juegos** · platformer: HUD de 2 filas arriba y nivel con scroll horizontal, `max_frame_lines` 78
en Mesen tras 900 frames de juego (captura correcta, 2026-11-24); shmup: el mismo corte con scroll vertical.

**Estado** · hecho (`gbe_video`)

---

## HR2 · La ventana como HUD
<!-- tags: window, hud -->

**Problema** · Un marcador o una caja de diálogo que no se mueva con el fondo y no gaste sprites.

**Cómo lo resolvían** · Pan Docs (Window): la ventana es una segunda capa de mapa que tapa el fondo desde (WX − 7, WY)
**hasta la esquina inferior derecha**: un HUD **abajo** sale gratis (`WY = 144 − alto`); un HUD **arriba** necesita
apagar la ventana en la línea del corte (HR1). La ventana tiene su propio contador de líneas (si se apaga y se vuelve a
encender sigue donde iba). Los sprites se dibujan sobre la ventana salvo que se apaguen en esa franja.

**En gbe** · HUD arriba: `gbe_video` con `hud_cut` (HR1). Diálogos: `gbe_tbox` dibuja en la ventana y el juego la
muestra mientras `tbox_visible`. Texto del HUD: `gbe_text` + `gbe_vq` (solo cambian los números: lección
hud-fields-not-strings de `docs/guias/lecciones-snes.md`).

**Medido en nuestros juegos** · platformer (arriba, 2 filas), faro y world_lab (caja de diálogo abajo).

**Estado** · hecho

---

## HR3 · Fundidos con las paletas (BGP/OBP0/OBP1)
<!-- tags: palette, fade, bgp -->

**Problema** · Fundir a blanco o a negro sin color: la DMG solo tiene 4 tonos.

**Cómo lo resolvían** · Pan Docs (Palettes): `BGP`, `OBP0`, `OBP1` asignan un tono (2 bits) a cada uno de los 4 colores.
Un fundido son 3-4 pasos cambiando esa tabla (p. ej. cada tono c → min(c + k, 3) para negro, o hacia 0 para blanco),
escritos en VBlank. OBP0/OBP1 no se inicializan al arrancar: fijarlas siempre (OBP1 arranca a 0x1B en GBDK).

**En gbe** · `set_fade(k)` (0 normal … 3 blanco) y `set_fade_dark(k)` (0 … 3 negro) sobre las sombras de `gbe_video`;
`gbe_screen` hace la transición completa: fundido de 16 frames, `screen_build()` con el LCD apagado, fundido de entrada.
Destellos de daño: cambiar `obp0_shadow`/`bgp_below` unos frames.

**Medido en nuestros juegos** · transiciones de 16 frames en platformer, shmup, dungeon, faro, happyvalley, mazmorra.

**Estado** · hecho (`gbe_video`, `gbe_screen`)

---

## HR4 · Paralaje y curvas cambiando SCX por líneas
<!-- tags: raster, parallax, scx -->

**Problema** · Con un solo fondo no hay capas: el cielo, las montañas y el suelo se mueven a la vez.

**Cómo lo resolvían** · Dividir la pantalla en bandas horizontales y cambiar SCX en el HBlank anterior a cada banda
(interrupción LYC encadenada: cada manejador escribe el SCX y programa el LYC de la siguiente banda). Así cada banda se
desplaza a su velocidad (paralaje por bandas) o se curva una pista. Límite práctico: el coste de cada interrupción
(entrar, esperar al modo 0, salir) y que dos bandas no pueden estar a menos de ~1 línea.

**En gbe** · `gbe_raster`: hasta `RASTER_MAX` (10) cambios de SCX por frame; llenar `raster_line[]` (ascendente, ≥ 1),
`raster_scx[]`, `raster_n` y `raster_commit()`, que se aplica en el VBlank siguiente; la línea 0 usa `scx_shadow`.
`raster_init()` después de `video_init()`; **no** a la vez que el `hud_cut` de gbe_video.

**Medido en nuestros juegos** · sin medir: ningún juego versionado lo usa todavía (commit 1461fa3 lo añadió a gbe).
Al usarlo, confirmar con `gbrun` capturas fila a fila.

**Estado** · hecho (`gbe_raster`); sin juego que lo use
