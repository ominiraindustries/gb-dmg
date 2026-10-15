# MADRIGUERA — especificación de interfaz (ui-designer)

Fuente de las posiciones: las maquetas `design/screens/*.screen`. El build convierte cada texto en
`SCREEN_<PANTALLA>_AT_<TEXTO>` (= `fila * 32 + col`) y `SCREEN_<PANTALLA>_LEN_<TEXTO>`
(`harness/screens.py`), y con texto proporcional además `SCREEN_<PANTALLA>_TILE_<TEXTO>` (primer tile
del texto en VRAM) y `_TILES_<TEXTO>` (celdas que ocupa). **El código usa esos defines, nunca
coordenadas ni tiles a mano.** `fila = AT >> 5`, `col = AT & 31`. Lo que no es texto (iconos, marcos,
cursor, mapa) se da aquí, en filas/columnas de pantalla, o relativo a un define.

- Las maquetas se regeneran con `python games/mazmorra/design/gen_screens.py` (todas menos el título)
  y `python games/mazmorra/design/paint_title.py` (título: también escribe `res/title.tiles`). Editar
  allí, no los `.screen` a mano. Vista previa: `python harness/gb.py preview mazmorra`.
- **Texto proporcional** (fuente B, `font_mini*`, §1.3): todo texto de una maqueta se dibuja al compilar
  con su ancho real en tiles propios del hueco `text`. Alineado a la izquierda en sus celdas salvo los
  de la línea `center:` de la maqueta. Un texto ocupa tantas celdas como letras tiene en la maqueta
  (una letra por celda), aunque su tinta ocupe ~70 %: por eso los textos centrados se eligieron con un
  número **par** de letras alrededor de la col. 10 (centrados de verdad en la pantalla), y las líneas
  dinámicas de ejemplo tienen 18 letras (reservan los 18 tiles de una línea entera).
- **Para borrar o reescribir un texto usar `_TILES_`**, no `_LEN_`: `LEN` se corta en el punto
  (`"Has caido."` → `LEN_HAS_CAIDO` 9, `TILES_HAS_CAIDO` 10). Reescribir = `vwf_clear` + `vwf_draw` en
  `_TILES_` tiles + `tiles_push` a `_TILE_` (gbe_vwf), preparado en `update()` y copiado por `gbe_vq`.
- **Textos que aparecen, cambian o parpadean** están en la maqueta; para ocultarlos el código escribe
  `UI_BLANK` en las `_TILES_` celdas del mapa (los tiles del texto se quedan cargados).
- **Ventana**: `WX = 7`, `WY = 0` siempre en juego; mapa de la ventana `$9C00` (LCDC bit 6 = 1), fondo
  `$9800`. Como WY = 0, **fila de pantalla = fila del mapa de la ventana**: los defines de las maquetas
  de ventana valen tal cual sobre `$9C00`.
- Texto en mayúscula inicial, sin tildes ni eñe; `¿ ¡ , '` de `font_mini_es`. El punto se escribe con
  la leyenda `·` (`font_mini:DOT`): en las maquetas `.` es blanco.

## 1. Tiles y VRAM

### 1.1 Juegos de tiles de fondo
| Juego | Fichero | Tiles | VRAM | Quién lo carga |
|---|---|---|---|---|
| title | `res/title.tiles` (lo genera `paint_title.py`) | **101** | 0-100, hueco compartido con `dungeon` | `screen_build(TITULO)` |
| ui | `res/ui.tiles` | **21** (presupuesto 24) | `VRAM_UI` (101) | todos los `screen_build` |
| texto | hueco reservado `{"text": 90}` | **90** | `VRAM_TEXT` 122-211 | cada pantalla carga su `screen_<n>_text` |

Las fuentes ya **no están en VRAM**: `font_mini*` viven en ROM (banco) y solo las lee gbe_vwf. Total
`101 + 21 + 90 = 212`: llega justo al límite del jefe (212); ya no queda margen 200-211. Si el jefe
necesita más, el hueco de texto puede bajar a 72 (la pantalla que más gasta usa 71, §1.3).

### 1.2 ui.tiles (21, mismo orden en todas las escenas)
| Índice | Etiqueta | Uso |
|---|---|---|
| 0 | `BLANK` | relleno de cajas, fila 1 de la ventana, celdas vacías del HUD, huecos de pestaña |
| 1-8 | `FRAME_TL FRAME_T FRAME_TR FRAME_L FRAME_R FRAME_BL FRAME_B FRAME_BR` | marco de 9 piezas (la 9ª es `BLANK`); también las salas del mapa de pausa |
| 9 | `ARROW_DOWN` | "hay más": sustituye el `FRAME_B` de la col. 17 de la fila inferior de la caja |
| 10 | `CURSOR` | cursor de menú (tile de fondo a la izquierda de la opción) |
| 11-13 | `HEART_FULL HEART_HALF HEART_EMPTY` | corazones del HUD: `tile = HEART_FULL + estado` (0 lleno, 1 medio, 2 vacío) |
| 14 | `BOMB` | icono de bombas |
| 15 | `KEY` | icono de llave pequeña |
| 16 | `BOSS_KEY` | Llave del Rey (llave con corona) |
| 17 | `SOLID` | negro: fondo de FIN |
| 18-20 | `MAP_DOOR_V MAP_DOOR_H_T MAP_DOOR_H_B` | uniones del mapa de pausa |

Marco: línea negra de 2 px + costura gris oscuro discontinua (periodo 4, simétrica) + margen blanco de
3 px hasta el texto (a la izquierda) y 4 px (arriba, contando la fila vacía de la fuente).
**Sin línea separadora en el HUD** (preferencia del usuario): la fila 1 de la ventana es `BLANK`.

### 1.3 Hueco de texto: desplazamientos y tiles por pantalla
Tile = `VRAM_TEXT + desplazamiento`. Cada pantalla carga `screen_<n>_text` (`_TEXT_COUNT` tiles) en
`SCREEN_<N>_TEXT_FIRST` al construirse (o al abrirse, si es un panel de la ventana). Lo que se ve a la
vez no se pisa; lo que nunca coincide comparte rango.

| Escena | Pantalla | `text:` | Tiles | Rango | Contenido |
|---|---|---|---|---|---|
| title | `title` | 0 | 11 | 0-10 | `PULSA_START` |
| title | `title_menu` | 11 | 22 | 11-32 | `CONTINUAR` 9, `NUEVA_PARTIDA` 13 |
| title | `title_borrar` | 33 | 38 | 33-70 | `EMPEZAR_DE_NUEVO` 18, `SE_BORRARA_TODO` 16, `SI` 2, `NO` 2 |
| play | `play` | 0 | 0 | — | (M1: el HUD no tiene cifras) |
| play | `hud_full` | 0 | 3 | 0-2 | `10` (bombas, 2), `1` (llaves, 1): **del HUD, siempre cargados** |
| play | `dialogo` | 3 | 64 | 3-66 | pestaña `DON_TERRON` 3-12; líneas 13-30, 31-48, 49-66 |
| play | `dialogo_cartel` | 13 | 54 | 13-66 | las 3 líneas (mismos tiles que en `dialogo`) |
| play | `dialogo_sino` | 3 | 50 | 3-52 | pestaña 3-12, líneas 1-2 13-48, `SI` 49-50, `NO` 51-52 |
| play | `objeto` | 13 | 18 | 13-30 | el mensaje (línea 1) |
| play | `pausa` / `pausa_base` | 3 | 12 / 4 | 3-14 | `MAPA` 3-6, nombre de sala `ANTESALA` 7-14 |
| gameover | `fin` | 0 | 24 | 0-23 | `HAS_CAIDO` 10, `CONTINUAR` 9, `SALIR` 5 |
| ending | `final` | 0 | 65 | 0-64 | ver §8 |

- Escena título: se cargan las tres (0-70) con el LCD apagado al construir TITULO; pasar de "Pulsa
  Start" al menú o a la confirmación solo copia filas del mapa, nunca tiles de texto.
- Escena juego: tiles 0-2 = cifras del HUD (las redibuja `hud_update`). Diálogo, objeto y pausa
  empiezan en 3 y se excluyen entre sí. Las maquetas de esos paneles llevan el HUD **sin cifras**
  (si las llevaran, sus tiles se asignarían dentro del rango del panel).
- Máximo por escena: título 71, juego 67, fin 24, final 65 (de 90).

## 2. TITULO (escena `title`) — `title.screen`, `title_menu.screen`, `title_borrar.screen`
Residente: `title` (hueco), `ui`, texto 0-70. Sin sprites (`vram_scenes.title.spr = []`). Ventana
apagada, `hud_cut = 0`, `SCX = SCY = 0`.
- Construcción: `gbe_screen`: fundido 16 f → LCD apagado, cargar `title` + `ui` + los tres
  `screen_title*_text`, copiar `screen_title_map` (`skip_measure`) → fundido de entrada 16 f.
- Arte: logo "MADRIGUERA" filas 1-3, subtítulo "La campana del alba" **pintado** en la fila 5 (arte de
  `title.tiles` con la fuente gruesa antigua, no es texto proporcional), cerro con la puerta, cartel
  "no-topos", Tilo; filas 14-17 blancas: textos.
- **M1**: `PULSA_START` (centrado en sus 11 celdas, cols 4-14) parpadea **30 f visible / 30 f
  borrado** (`UI_BLANK` en `TILES_PULSA_START` celdas ↔ `TILE_PULSA_START + k`). Start **o** A:
  sonido "confirmar", fundido a blanco → JUEGO.
- **M3**, con partida válida: Start/A cambia las filas 14-17 por las de `screen_title_menu_map`
  (80 tiles por `gbe_vq`, 2 frames). Cursor `CURSOR` en la col. 4, opciones alineadas a la izquierda en
  la col. 5, paso de 2 filas: `SCREEN_TITLE_MENU_AT_CONTINUAR` (fila 14) y `..._AT_NUEVA_PARTIDA`
  (fila 16). Empieza en Continuar. Arriba/abajo cambian (con vuelta), A/Start confirma, B vuelve a
  "Pulsa Start". Sin partida, Start va directo a la INTRO.
- **M3**, Nueva partida con partida guardada: copiar las filas 11-17 de `screen_title_borrar_map`
  (140 tiles, 4 frames). Pregunta centrada: `SCREEN_TITLE_BORRAR_AT_EMPEZAR_DE_NUEVO` ("¿Empezar de
  nuevo?") y `_AT_SE_BORRARA_TODO` ("Se borrara todo."); respuestas `_AT_SI` (cursor en la col.
  `(AT_SI & 31) − 1` = 5) y `_AT_NO` (cursor col. 11). **Empieza en No.** Izquierda/derecha cambian;
  A confirma; B = No. No → restaurar filas 11-17 de `screen_title_menu_map` (140 tiles, 4 frames).
- Dinámicos (QA): `title`: `PULSA_START`. `title_menu`/`title_borrar`: ninguno (comparar con el cursor
  en su posición inicial).

## 3. JUEGO: HUD (escena `play`) — `play.screen` (M1), `hud_full.screen` (M2+)
Residente: `dungeon` (hueco), `ui`, texto 0-2 (+ el panel abierto); sprites del juego.
- **Cómo se muestra**: ventana encendida (LCDC bit 5) con `WY = 0`, `WX = 7`; `gbe_video` con
  `video_init(16, ...)` y `hud_cut = 1`: en VBlank ventana ON + OBJ OFF, en LYC 16 ventana OFF + OBJ ON.
- **Al construir la escena** (LCD apagado): copiar las filas 0-1 de `screen_play_map` a `$9C00`
  filas 0-1 (40 tiles), y luego escribir el estado real del HUD.
- Para usar los defines del HUD completo hay que añadir `hud_full` a `"screens"` de game.json (hoy
  solo `title play fin`); lo mismo para `dialogo*`, `objeto`, `pausa*`, `final` cuando toquen.
- Fila 0 de la ventana (fila 1 = `BLANK`):

| Elemento | Columnas | Cuándo se ve | Contenido |
|---|---|---|---|
| Corazones | 1-5 | siempre | `hp_max / 2` contenedores; contenedor `i`: lleno si `hp >= 2i+2`, medio si `hp == 2i+1`, vacío si no; columnas sin contenedor `BLANK` |
| Bombas | icono col. 11; cifras en `SCREEN_HUD_FULL_AT_10` (cols 12-13), tiles `TILE_10` (2) | desde `F_BOMBAS` | 0-10 en cifras proporcionales **alineadas a la izquierda**, pegadas al icono |
| Llaves | icono col. 15; cifra en `SCREEN_HUD_FULL_AT_1` (col. 16), tile `TILE_1` (1) | `keys >= 1` | una cifra (la llave más ancha, "8", mide 7 px) |
| Llave del Rey | col. 18 | `F_LLAVE_REY` | `BOSS_KEY` |

- **Qué cambia y cuándo**: al cambiar `bombs`/`keys`, `update()` redibuja con gbe_vwf los 2 o 1 tiles
  del número (`vwf_clear` + `vwf_draw` desde x = 0) y los encola (32 o 16 bytes); los corazones y los
  iconos son entradas del mapa (corazones 5, iconos 1). Mapa: las celdas del número apuntan siempre a
  `TILE_10 + 0/1` y `TILE_1` mientras se ven; `BLANK` si no.
- **Vida baja** (`hp <= 2`): el último corazón no vacío parpadea con `HEART_EMPTY`, 16 f / 16 f.
- Dinámicos (QA): `play` → `gb.mockup_errors("play", (0, 0, 20, 2), ignore=[(0, 1, 5)])`.
  `hud_full`: `["10", "1", (0, 1, 5)]`.

## 4. FIN (escena `gameover`, M1) — `fin.screen`
Residente: `ui` + texto 0-23. Ventana apagada, `hud_cut = 0`, sprites ocultos.
- Entrada: `hp == 0` → congelar 30 f → fundido a negro 16 f → LCD apagado: copiar `screen_fin_map` y
  `screen_fin_text` (`skip_measure`) → fundido desde negro 16 f.
- Caja de las filas 4-13, **cols 3-16** sobre `SOLID`. `SCREEN_FIN_AT_HAS_CAIDO` ("Has caido.",
  fila 6, centrado en las cols 5-14). Opciones alineadas a la izquierda `SCREEN_FIN_AT_CONTINUAR`
  (fila 9) y `SCREEN_FIN_AT_SALIR` (fila 11), col. 7; cursor en la col. `(AT & 31) − 1` (= 6) de la
  opción elegida, la otra con `BLANK`. Empieza en Continuar. (El bloque cursor + "Continuar" queda
  centrado en la caja.)
- Arriba/abajo cambian (con vuelta), sonido "mover"; A o Start confirman; B nada.
- Continuar → fundido a negro → `screen_build(JUEGO)` en la sala y posición de entrada, vida llena.
  Salir → fundido a blanco → TITULO.
- Dinámicos (QA): ninguno; `gb.mockup_errors("fin")` entero en cuanto acaba el fundido.

## 5. DIALOGO (escena `play`, M3) — `dialogo.screen`, `dialogo_cartel.screen`, `dialogo_sino.screen`
- **Cómo se muestra**: la caja vive en la ventana, filas 2-6. Al abrir: `gbe_tbox` encola el marco
  (5 filas x 20 = 100 tiles por `gbe_vq`, ≤ 40/frame → 3 frames) y **solo cuando la cola está vacía**
  se baja el corte a la línea **56** (`video_set_cut(56)`). Al cerrar: corte a 16 en el VBlank
  siguiente (la caja queda escrita pero oculta). El juego está congelado mientras.
- Configuración de `gbe_tbox`: `tbox_row = 2`; `tbox_frame = { FRAME_TL, FRAME_T, FRAME_TR,
  FRAME_L, BLANK, FRAME_R, FRAME_BL, FRAME_B, FRAME_BR }`; `tbox_arrow = ARROW_DOWN`;
  `tbox_cursor = CURSOR`; `tbox_yes_col = 3`, `tbox_no_col = 9`. 3 líneas en las filas 3-5 desde la
  col. 1; flecha en la fila 6, col. 17.
- **Texto proporcional**: cada línea es una tira de **18 tiles = 144 px** (cols 1-18), dibujada desde
  x = 0 (como la maqueta) y alineada a la izquierda. Tiles: línea 1 = `SCREEN_DIALOGO_TILE_SI_TIEMBLA_EL_REY`
  (VRAM_TEXT + 13), línea 2 = `_TILE_TOPO_SALE_YA_DE_SU` (+31), línea 3 = `_TILE_CUEVA_MUCHO_OJO` (+49);
  el mapa de las filas 3-5 apunta siempre a esas tiras (se escribe una vez al abrir). Una línea admite
  ~25 letras (el texto medio mide ~5,7 px por letra). Las 3 líneas apiladas a 8 px ya no se tocan
  (`font_mini`: la fila 7 solo tiene descendentes).
- **Corte de líneas**: debe ser por píxeles (≤ 144 px con `vwf.width`), no por 18 caracteres:
  `harness/script.py` corta hoy por `TEXT_W = 18` letras y `TEXT_LINES = 2` (el diálogo tiene 3).
  Propuesto al productor; mientras tanto las líneas salen más cortas de lo que caben.
- Escritura 1 carácter/f (2 con A mantenido): cada letra redibuja 1-2 tiles de la tira (32 bytes por
  `gbe_vq`); A completa la página (54 tiles, 2 frames). Flecha **16/16 f** con `FRAME_B` mientras
  espera.
- Pestaña del hablante: `SCREEN_DIALOGO_AT_DON_TERRON` (fila 2, cols 3-12, centrado; blanco en las
  cols 2 y 13). Solo Don Terrón. Carteles y mensajes: borde liso (`dialogo_cartel`, `text: 13`: mismas
  tiras de línea que `dialogo`).
- Sí/No (`dialogo_sino`): pregunta en las líneas 1-2, `SCREEN_DIALOGO_SINO_AT_SI` / `_AT_NO` en la
  fila 5 (tiles 49-52, dentro del rango de la línea 3: al pasar de una página normal a la pregunta se
  reescribe la fila 5 del mapa), cursor una columna a la izquierda. Empieza en Sí; izquierda/derecha;
  A confirma. Sin flecha mientras elige.
- Dinámicos (QA): región `(0, 2, 20, 7)` ignorando `["SI_TIEMBLA_EL_REY", "TOPO_SALE_YA_DE_SU",
  "CUEVA_MUCHO_OJO", (6, 17, 1)]` (la flecha). `dialogo_cartel`: `["MADRIGUERA_DEL_REY",
  "TOPO_PROHIBIDO_EL", "PASO_A_QUIEN_NO_ES", (6, 17, 1)]`. `dialogo_sino`: `["QUIERES_QUE_TE_DE",
  "UN_CONSEJO_GRATIS"]`.

## 6. OBJETO (escena `play`, M2/M3) — `objeto.screen`
- Tilo levanta el objeto 48 f (sprite sobre su cabeza, OAM 20); a la vez se abre la caja (§5) con
  **una línea centrada** en la fila 3 (`SCREEN_OBJETO_TILE_LA_LLAVE_DEL_REY`, 18 tiles, `text: 13`):
  el código dibuja el mensaje en x = `(144 − vwf.width) / 2`. Tras los 48 f aparece la flecha; A cierra.
- Textos (todos caben en una línea de 144 px): "¡Coges una llave!" (97 px), "¡La Llave del Rey!"
  (100), "¡Coges 8 bombas!" (97), "¡Un corazon mas!" (96), "¡La Campana del Alba!" (122: ahora en
  **una** línea, antes dos).
- Dinámicos (QA): `["LA_LLAVE_DEL_REY", (6, 17, 1)]`.

## 7. PAUSA (escena `play`, M3) — `pausa.screen` (ejemplo), `pausa_base.screen` (copia)
- **Cómo se muestra**: Start en una sala (no durante deslizado, diálogo ni golpe). El juego se congela;
  con el corte aún en 16 se encola: filas 2-17 de `screen_pausa_base_map` → `$9C00` filas 2-17 (320
  tiles, 8 frames a 40/frame) y el texto de `pausa` (12 tiles: `MAPA` + nombre), luego salas, uniones
  y nombre (≤ 80 tiles, 2 frames). Cuando la cola está vacía: **ventana a pantalla completa** con
  `hud_cut = 0` + LCDC ventana ON + OBJ OFF (escritos en VBlank); no usar un corte en la línea 144. Al
  salir (Start o B): `hud_cut = 1` con LYC 16 en el VBlank siguiente. Filas 0-1 (HUD) no se tocan.
- Panel: caja filas 2-17 con pestaña `SCREEN_PAUSA_AT_MAPA` (centrado en sus 4 celdas). Mapa de la
  rejilla 3x4 (`rooms.tbl` `col`, `row`): sala (c, r) = caja 3x2 (`FRAME_TL FRAME_T FRAME_TR` /
  `FRAME_BL FRAME_B FRAME_BR`) con esquina en **fila 4 + 3r, col. 4 + 4c**. Uniones: entre (c, r) y
  (c, r+1) `MAP_DOOR_V` en (fila 4 + 3r + 2, col. 4 + 4c + 1); entre (c, r) y (c+1, r) `MAP_DOOR_H_T`
  en (fila 4 + 3r, col. 4 + 4c + 3) y `MAP_DOOR_H_B` debajo.
- Solo **salas visitadas** y la unión entre dos salas visitadas que comparten puerta. La sala actual
  parpadea caja ↔ `BLANK`, 16/16 f (6 tiles cada 16 f), empezando visible.
- Nombre de la sala (`rooms.tbl` `name`): `SCREEN_PAUSA_AT_ANTESALA`, fila 16, **cols 6-13 (8 tiles,
  `TILE_ANTESALA`)**, centrado: el código lo dibuja en x = `(64 − vwf.width) / 2`. Todos caben: el más
  ancho, "Vestibulo", mide 54 px. El mapa de esas 8 celdas no cambia.
- **Falta en el GDD**: guardar qué salas se han visitado (`visited`, 2 bytes de la reserva del guardado).
- Dinámicos (QA): el ejemplo es todas las salas menos R9 visitadas, en R8 Antesala, `hp` 5 de 6;
  `gb.mockup_errors("pausa", (0, 2, 20, 18))` con la sala actual visible (filas 4-5, cols 8-10). El
  HUD del ejemplo no lleva cifras: comparar la fila 0 aparte. Otros estados: marco contra `pausa_base`
  y el mapa contra el modelo de salas visitadas; ignorar `ANTESALA`.

## 8. FINAL (escena `ending`, M3) — `final.screen`
Residente: `ui` + texto 0-64; sprites `link` e `items`. Ventana apagada, `hud_cut = 0`.
- Tras levantar la campana (48 f): fundido a blanco 16 f → LCD apagado: `screen_final_map` +
  `screen_final_text` → fundido de entrada. Fondo blanco, caja filas 1-16 cols 0-19.
- Campana: sprite de `items` 16x16 (2 sprites 8x16) en x 72, y 32 (filas 4-5), OBP0; se balancea 1 px
  a cada lado cada 16 f (meter en la maqueta cuando exista en `items.tiles`).
- Textos fijos centrados: `¡Dong!`, `La niebla deja` / `Robledo.`, `Gracias por jugar.` (cambiados para
  tener un número par de letras: centrados exactos). Etiquetas `SCREEN_FINAL_AT_TIEMPO` y `_AT_CAIDAS`
  en la col. 4; valores **alineados a la izquierda en la col. 12**: tiempo `SCREEN_FINAL_TILE_24_31`
  (5 tiles: `m:ss` hasta 9:59, `mm:ss` hasta 59:59, `h:mm` más allá; "59:59" mide 31 px) y caídas
  `_TILE_12` (2 tiles; mostrar como máximo 99).
- A → fundido a blanco → TITULO.
- Dinámicos (QA): `["24_31", "12"]`.

## 9. Transiciones (todas con `gbe_screen`)
| De → a | Salida | Construcción | Entrada |
|---|---|---|---|
| TITULO → JUEGO | fundido a blanco 16 f | LCD apagado (`skip_measure`) | desde blanco 16 f |
| JUEGO → FIN | congelar 30 f + a negro 16 f | LCD apagado | desde negro 16 f |
| FIN → JUEGO | a negro 16 f | LCD apagado | desde negro 16 f |
| FIN → TITULO, FINAL → TITULO | a blanco 16 f | LCD apagado | desde blanco 16 f |
| JUEGO → FINAL | a blanco 16 f | LCD apagado | desde blanco 16 f |
| Pausa, diálogo, objeto | sin fundido | tiles por `gbe_vq` con la ventana oculta | cambio de corte en VBlank |
| Deslizado entre salas | — | `gbe_world` | — (el HUD de la ventana no se mueve) |

## 10. Comprobaciones
- Sprites por línea: la UI no usa sprites (cursores y flechas son tiles de fondo); en pausa, diálogo
  y pantallas fijas los sprites están ocultos o no existen. Solo FINAL: campana 2 + Tilo 2.
- Tiles por frame: HUD ≤ 3 tiles de texto (48 bytes) + 6 de mapa; diálogo 40 de mapa/frame al abrir,
  1-2 tiles de texto por letra; pausa 40/frame; título ≤ 11 de mapa (parpadeo) o 40 (menú). Pantallas
  completas y sus tiles de texto con LCD apagado.
- Hueco de texto: ninguna pantalla pasa de 71 de 90 (§1.3); el build para si alguna no cabe.
- Legibilidad: HUD negro/gris oscuro sobre blanco, separado de la sala por la fila blanca 1; nada
  importante en gris claro sobre blanco. Con `font_mini` el `¡` se parece a una `i` ("iLa Llave",
  "iDong!"): pedido al pixel-artist (no edito fuentes compartidas).
- Escenas y tilesets: cada maqueta usa solo `ui` + las fuentes de texto (y `title` las de título).
  Ninguna maqueta usa `dungeon` ni sprites: la sala de `play` es el mundo.
