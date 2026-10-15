# MADRIGUERA — especificación de interfaz (ui-designer)

Fuente de las posiciones: las maquetas `design/screens/*.screen`. El build convierte cada texto en
`SCREEN_<PANTALLA>_AT_<TEXTO>` (= `fila * 32 + col`) y `SCREEN_<PANTALLA>_LEN_<TEXTO>`
(`harness/screens.py`). **El código usa esos defines, nunca coordenadas a mano.** `fila = AT >> 5`,
`col = AT & 31`. Lo que no es texto (iconos, marcos, cursor, mapa) se da aquí, en filas/columnas de
pantalla, o relativo a un define.

- Las maquetas se regeneran con `python games/mazmorra/design/gen_screens.py` (todas menos el título)
  y `python games/mazmorra/design/paint_title.py` (título: también escribe `res/title.tiles`). Editar
  allí, no los `.screen` a mano. Vista previa: `python harness/gb.py preview mazmorra`.
- **Números dinámicos**: el valor de ejemplo de la maqueta ocupa el ancho máximo del campo; el código
  escribe el valor real alineado a la derecha terminando en `AT + LEN - 1`, con blancos a la izquierda.
- **Textos que aparecen, cambian o parpadean** están en la maqueta; el código escribe `UI_BLANK` en
  `LEN` celdas cuando no tocan.
- **Ventana**: `WX = 7`, `WY = 0` siempre en juego; mapa de la ventana `$9C00` (LCDC bit 6 = 1), fondo
  `$9800`. Como WY = 0, **fila de pantalla = fila del mapa de la ventana**: los defines de las maquetas
  de ventana valen tal cual sobre `$9C00`.
- Fuente: hoy `font` + `font_lower` + `font_es` (72 tiles). Cuando se adopte `font_mini` (E3, M2) se
  cambia el nombre en `tilesets:` de los generadores; posiciones y textos no cambian.
- Texto en mayúscula inicial, sin tildes ni eñe; `¿ ¡ , '` de `font_es`. El punto se escribe con la
  leyenda `·` (`font:DOT`): en las maquetas `.` es blanco. Ojo: `screens.text_runs` corta un texto en
  el punto (`"de Robledo."` → define `DE_ROBLEDO`, LEN 10 sin el punto).

## 1. Tiles y VRAM

### 1.1 Juegos de tiles de UI
| Juego | Fichero | Tiles | Hueco | Quién lo carga |
|---|---|---|---|---|
| title | `res/title.tiles` (lo genera `paint_title.py`) | **106** | hueco compartido con `dungeon` | `screen_build(TITULO)` |
| ui | `res/ui.tiles` | **21** (presupuesto 24) | detrás del hueco | todos los `screen_build` |
| font + font_lower + font_es | `harness/common/` | 42 + 26 + 4 | detrás de ui | todos los `screen_build` |

`"vram_order": [["dungeon", "title"], "ui", "font", "font_lower", "font_es"]` (con `font_mini` más
tarde). `title` mide 106 (> 104 del GDD) a cambio de que `ui` mide 21 (< 24): el total sigue siendo
**200** (`106 + 21 + 72 = 199`), el margen 200-211 queda libre y el límite del jefe (212) no se toca.
Si `dungeon` acaba en ≤ 104, el hueco mide 106 por el título. `paint_title.py` para si pasa de 107.
`"common_res": ["font", "font_lower", "font_es"]`; `title`, `ui` y cada `screen_*` a `"banked_res"`.
`"screens"`: `title title_menu title_borrar play hud_full dialogo dialogo_cartel dialogo_sino objeto
pausa pausa_base fin final` (las de M3 pueden añadirse cuando toquen; no cuestan nada si no se usan).

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
1 px, esquinas redondeadas (lenguaje del estudio; tema: saco cosido de la despensa del topo).
**Sin línea separadora en el HUD** (preferencia del usuario): el GDD §5.1 y §7.1 la tenían; la fila 1 de
la ventana es `BLANK` y el tile "línea del HUD" no existe. Iconos y corazones usan las filas 0-6 del
tile, como la fuente (misma línea base).

## 2. TITULO (escena `title`) — `title.screen`, `title_menu.screen`, `title_borrar.screen`
Residente: `title` (hueco), `ui`, fuentes. Sin sprites (`vram_scenes.title.spr = []`). Ventana apagada,
`hud_cut = 0`, `SCX = SCY = 0`.
- Construcción: `gbe_screen`: fundido 16 f → LCD apagado, cargar `title` + `ui` + fuentes, copiar
  `screen_title_map` (`skip_measure`) → fundido de entrada 16 f.
- Arte: logo "MADRIGUERA" filas 1-3, subtítulo "La campana del alba" pintado con espaciado
  proporcional en la fila 5 (no es texto de fuente: 19 letras no se centran en celdas de 8 px), cerro
  con la puerta de la madriguera, cartel "no-topos", Tilo mirando la puerta y niebla, filas 7-13.
  Filas 14-17 blancas: textos.
- **M1**: `SCREEN_TITLE_AT_PULSA_START` parpadea **30 f visible / 30 f borrado** (11 tiles cada 30 f).
  Start **o** A: sonido "confirmar", (M1) fundido a blanco → JUEGO (nueva partida en R1).
- **M3**, con partida válida: Start/A cambia las filas 14-17 por las de `screen_title_menu_map`
  (80 tiles por `gbe_vq`, 2 frames). Cursor `CURSOR` en la col. 4, opciones en la col. 5, paso de 2
  filas: `SCREEN_TITLE_MENU_AT_CONTINUAR` (fila 14) y `..._AT_NUEVA_PARTIDA` (fila 16). Empieza en
  Continuar. Arriba/abajo cambian (con vuelta), A/Start confirma, B vuelve a "Pulsa Start". Sin
  partida, Start va directo a la INTRO (no hay menú).
- **M3**, Nueva partida con partida guardada: copiar las filas 11-17 de `screen_title_borrar_map`
  (140 tiles, 4 frames: la caja se "despliega" de arriba abajo, aceptado). Pregunta en
  `SCREEN_TITLE_BORRAR_AT_SE_BORRARA_LA` / `_AT_PARTIDA` / `_AT_SEGURO`; respuestas
  `SCREEN_TITLE_BORRAR_AT_SI` (cursor en la col. `AT_SI & 31` − 1) y `_AT_NO` (cursor col. − 1).
  **Empieza en No.** Izquierda/derecha cambian; A confirma; B = No. No → restaurar filas 11-17 de
  `screen_title_menu_map` (el cerro vuelve; 140 tiles, 4 frames).
- Dinámicos (QA): `title`: `PULSA_START`. `title_menu`/`title_borrar`: ninguno (comparar con el cursor
  en su posición inicial).

## 3. JUEGO: HUD (escena `play`) — `play.screen` (M1), `hud_full.screen` (M2+)
Residente: `dungeon` (hueco), `ui`, fuentes; sprites del juego.
- **Cómo se muestra**: ventana encendida (LCDC bit 5) con `WY = 0`, `WX = 7`; `gbe_video` con
  `video_init(16, ...)` y `hud_cut = 1`: en VBlank ventana ON + OBJ OFF, en LYC 16 ventana OFF + OBJ ON.
  Los sprites nunca tapan el HUD; la sala (fondo) empieza en la línea 16.
- **Al construir la escena** (LCD apagado): copiar las filas 0-1 de `screen_play_map` a `$9C00`
  filas 0-1 (40 tiles), y luego escribir el estado real del HUD (abajo).
- Fila 0 de la ventana (fila 1 = `BLANK`):

| Elemento | Columnas | Cuándo se ve | Contenido |
|---|---|---|---|
| Corazones | 1-5 | siempre | `hp_max / 2` contenedores; contenedor `i`: lleno si `hp >= 2i+2`, medio si `hp == 2i+1`, vacío si no; columnas sin contenedor `BLANK` |
| Bombas | icono col. 11, cifras = `SCREEN_HUD_FULL_AT_10` (cols 12-13) | desde `F_BOMBAS` | `BOMB` + 0-10 alineado a la derecha, decena en blanco si `< 10` |
| Llaves | icono col. 15, cifra = `SCREEN_HUD_FULL_AT_1` (col. 16) | `keys >= 1` | `KEY` + cifra |
| Llave del Rey | col. 18 | `F_LLAVE_REY` | `BOSS_KEY` |

- **Qué cambia y cuándo**: al cambiar `hp`, `hp_max`, `bombs`, `keys` o la bandera, `update()` prepara
  el grupo afectado en un búfer y lo encola en `gbe_vq` (corazones 5 tiles, bombas 3, llaves 2,
  Llave del Rey 1; ≤ 11 por frame en el peor caso). Nunca se escribe el HUD en `draw_vram` a mano.
- **Vida baja** (`hp <= 2`): el último corazón no vacío parpadea con `HEART_EMPTY`, 16 f / 16 f (1 tile
  cada 16 f). Se para al recuperar vida o morir.
- Dinámicos (QA): `play` → `gb.mockup_errors("play", (0, 0, 20, 2), ignore=[(0, 1, 5)])` tras empezar
  partida (corazones con `hp` 6 de 6 deben coincidir sin ignorar: 3 llenos). Las cols 6-19 de la fila 0
  y toda la fila 1 son `BLANK` en M1. `hud_full`: `["10", "1", (0, 1, 5)]`.

## 4. FIN (escena `gameover`, M1) — `fin.screen`
Residente: `ui` + fuentes (el hueco no se usa; no toca sprites). Ventana apagada, `hud_cut = 0`,
sprites ocultos.
- Entrada: `hp == 0` → congelar 30 f → fundido a negro 16 f (`set_fade_dark`) → LCD apagado: copiar
  `screen_fin_map` (`skip_measure`) → fundido desde negro 16 f.
- Caja de las filas 4-13, cols 3-16 sobre `SOLID`. `SCREEN_FIN_AT_HAS_CAIDO` (fila 6).
  Opciones `SCREEN_FIN_AT_CONTINUAR` (fila 9) y `SCREEN_FIN_AT_SALIR` (fila 11); cursor en la col.
  `(AT & 31) − 1` (= 5) de la opción elegida, la otra con `BLANK`. Empieza en Continuar.
- Arriba/abajo cambian (con vuelta), sonido "mover"; A o Start confirman, sonido "confirmar"; B nada.
- Continuar → fundido a negro → `screen_build(JUEGO)` (recarga `dungeon`, `ui`, fuentes, sprites, HUD)
  en la sala y posición de entrada, vida llena → fundido de entrada. Salir → fundido a blanco → TITULO.
- Dinámicos (QA): ninguno; `gb.mockup_errors("fin")` entero en cuanto acaba el fundido.

## 5. DIALOGO (escena `play`, M3) — `dialogo.screen`, `dialogo_cartel.screen`, `dialogo_sino.screen`
- **Cómo se muestra**: la caja vive en la ventana, filas 2-6 (ya visible por WY = 0). Al abrir:
  `gbe_tbox` encola el marco (5 filas x 20 = 100 tiles por `gbe_vq`, ≤ 40/frame → 3 frames) y **solo
  cuando la cola está vacía** se baja el corte a la línea **56** (E7, `video_set_cut(56)`): ventana hasta
  la fila 6, sprites ocultos encima de la línea 56. Al cerrar: corte a 16 en el VBlank siguiente (la
  caja queda escrita pero oculta: no hace falta borrarla). El juego está congelado mientras.
- Configuración de `gbe_tbox`: `tbox_row = 2`; `tbox_frame = { FRAME_TL, FRAME_T, FRAME_TR,
  FRAME_L, BLANK, FRAME_R, FRAME_BL, FRAME_B, FRAME_BR }`; `tbox_arrow = ARROW_DOWN`;
  `tbox_cursor = CURSOR`; `tbox_yes_col = 3`, `tbox_no_col = 9`. **E5**: 3 líneas en las filas +1, +2,
  +3 (filas 3-5 de pantalla) desde la col. 1, 18 caracteres; flecha en la fila +4 (fila 6), col. 17.
- Pestaña del hablante (`SCREEN_DIALOGO_AT_DON_TERRON`, fila 2 desde la col. 3, blanco antes y
  después): solo Don Terrón. Carteles y mensajes: borde liso (`dialogo_cartel`).
- Escritura 1 carácter/f (2 con A mantenido); A completa la página (8 tiles/f). Flecha **16/16 f** con
  `FRAME_B` mientras espera (el GDD decía 30 f; 16 f se lee mejor como "pulsa").
- Sí/No (`dialogo_sino`): pregunta en las líneas 1-2, `SCREEN_DIALOGO_SINO_AT_SI` / `_AT_NO` en la
  fila 5, cursor una columna a la izquierda. Empieza en Sí; izquierda/derecha cambian; A confirma.
  Sin flecha mientras elige.
- Con la fuente actual (descendentes en la fila 7) las líneas a 8 px se tocan (p, g, y sobre la
  línea de abajo); aceptado hasta `font_mini`, que lo resuelve.
- Dinámicos (QA): todos los textos de las líneas; comparar región `(0, 2, 20, 7)` ignorando
  `["CUANDO_TIEMBLA_EL", "SUELO_EL_REY_VA_A", "SALIR", (5, 6, 1), (6, 17, 1)]` (el punto y la flecha).
  `dialogo_sino`: ignorar `["QUIERES_UN", "CONSEJO"]`.

## 6. OBJETO (escena `play`, M2/M3) — `objeto.screen`
- Tilo levanta el objeto 48 f (sprite del objeto sobre su cabeza, OAM 20); a la vez se abre la caja
  (§5) con **una línea** en la fila 3. Tras los 48 f aparece la flecha; A cierra y devuelve el control.
- Textos (≤ 18): "¡Coges una llave!", "¡La Llave del Rey!", "¡Coges 8 bombas!", "¡Un corazon mas!",
  "¡La Campana del Alba!" (21: dos líneas: "¡La Campana" / "del Alba!").
- Dinámicos (QA): `["COGES_UNA_LLAVE", (6, 17, 1)]`.

## 7. PAUSA (escena `play`, M3) — `pausa.screen` (ejemplo), `pausa_base.screen` (copia)
- **Cómo se muestra**: Start en una sala (no durante deslizado, diálogo ni golpe). El juego se congela;
  con el corte aún en 16 (la ventana bajo la línea 16 no se ve) se encola: filas 2-17 de
  `screen_pausa_base_map` → `$9C00` filas 2-17 (320 tiles, 8 frames a 40/frame), luego salas,
  uniones y nombre (≤ 80 tiles, 2 frames). Cuando la cola está vacía: **ventana a pantalla completa**.
  **No usar un corte en la línea 144**: en la 144 coinciden LYC y VBlank; la ISR de VBlank va primero
  y la de LYC dejaría la ventana apagada y los sprites encendidos para el frame siguiente. En su lugar
  (E7): `hud_cut = 0` + LCDC ventana ON + OBJ OFF (escritos en VBlank). Al salir (Start o B): `hud_cut = 1`
  con LYC 16 en el VBlank siguiente; no hay que restaurar nada (la ventana bajo el HUD vuelve a no verse).
  Filas 0-1 (HUD) no se tocan.
- Panel: caja filas 2-17 con pestaña `SCREEN_PAUSA_AT_MAPA`. Mapa de la rejilla 3x4 de salas
  (`rooms.tbl` `col`, `row`): sala (c, r) = caja 3x2 (`FRAME_TL FRAME_T FRAME_TR` / `FRAME_BL FRAME_B
  FRAME_BR`) con esquina en **fila 4 + 3r, col. 4 + 4c**. Uniones: entre (c, r) y (c, r+1)
  `MAP_DOOR_V` en (fila 4 + 3r + 2, col. 4 + 4c + 1); entre (c, r) y (c+1, r) `MAP_DOOR_H_T` en
  (fila 4 + 3r, col. 4 + 4c + 3) y `MAP_DOOR_H_B` debajo.
- Solo se dibujan las **salas visitadas** y la unión entre dos salas visitadas que comparten puerta
  (con la mazmorra del GDD, haber visitado las dos implica haber abierto la puerta). La sala actual
  parpadea caja ↔ `BLANK`, 16/16 f (6 tiles cada 16 f), empezando visible.
- Nombre de la sala (`rooms.tbl` `name`, ≤ 10) centrado en la fila 16 entre las cols 1-18:
  col. = `1 + (18 - len) / 2`; antes, `BLANK` en las 18 celdas. Ejemplo `SCREEN_PAUSA_AT_GALERIA`.
- **Falta en el GDD**: guardar qué salas se han visitado (`visited`, 2 bytes de la reserva del guardado,
  bit = id de sala). Sin eso el mapa no puede saber qué dibujar tras cargar.
- Dinámicos (QA): el estado de `pausa.screen` se reproduce en un test (R1-R6 visitadas, en R5, `hp` 5
  de 6, 3 bombas, sin llaves): `gb.mockup_errors("pausa", ignore=["3", (0, 1, 5)])` en un frame con la
  sala actual visible (el parpadeo: filas 7-8, cols 8-10). Para otros estados, comparar el marco con
  `pausa_base` (región filas 2-17, ignorando el interior `(r, 1, 18)` de las filas 3-16) y el mapa
  contra el modelo de salas visitadas.

## 8. FINAL (escena `ending`, M3) — `final.screen`
Residente: `ui` + fuentes; sprites `link` e `items`. Ventana apagada, `hud_cut = 0`.
- Tras levantar la campana (48 f): fundido a blanco 16 f → LCD apagado: `screen_final_map` → fundido
  de entrada. Fondo blanco (el alba), caja filas 1-16 cols 0-19.
- Campana: sprite de `items` 16x16 (2 sprites 8x16) en x 72, y 32 (filas 4-5, dentro de la caja),
  OBP0; se balancea 1 px a cada lado cada 16 f (meter en la maqueta cuando exista `items.tiles`).
- Textos fijos: `¡Dong!`, `La niebla se va` / `de Robledo.`, `Gracias`. Etiquetas `SCREEN_FINAL_AT_TIEMPO`
  y `_AT_CAIDAS`; valores alineados a la derecha terminando en la col. 16: tiempo `SCREEN_FINAL_AT_24_31`
  (`m:ss` hasta 9:59, `mm:ss` hasta 59:59, `h:mm` más allá; 5 celdas), caídas `SCREEN_FINAL_AT_3`
  (hasta 3 cifras: empezar 2 columnas a la izquierda del ejemplo).
- A → fundido a blanco → TITULO.
- Dinámicos (QA): `["24_31", "3"]`.

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
- Tiles por frame: HUD ≤ 11 (vq); diálogo 40/frame al abrir y 1-8 al escribir; pausa 40/frame; título
  ≤ 11 (parpadeo) o 40 (menú). Pantallas completas con LCD apagado.
- Legibilidad: actores oscuros sobre la sala clara (lo vigila el pixel-artist); HUD en negro/gris
  oscuro sobre blanco, separado de la sala por la fila blanca 1; nada importante en gris claro sobre
  blanco (solo la costura del marco y la niebla del título, decorativas).
- Escenas y tilesets: cada maqueta usa solo `ui` + fuentes (y `title` las de título), residentes en su
  escena según §1. Ninguna maqueta usa `dungeon` ni sprites: la sala de `play` es el mundo.
