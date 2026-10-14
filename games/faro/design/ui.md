# FARO — especificación de interfaz (ui-designer)

Fuente de las posiciones: las maquetas `design/screens/*.screen`. El build convierte cada texto en
`SCREEN_<PANTALLA>_AT_<TEXTO>` (= `fila * 32 + col`) y `SCREEN_<PANTALLA>_LEN_<TEXTO>`
(`harness/screens.py`). **El código usa esos defines, nunca coordenadas a mano.** `fila = AT >> 5`,
`col = AT & 31`. Lo que no es texto (iconos, marcos, cursor, barras) se da aquí relativo a un define.

- **Números dinámicos**: en la maqueta, el valor de ejemplo está alineado a la derecha en su campo.
  El código escribe el valor real **alineado a la derecha terminando en la última celda del ejemplo**
  (`AT + LEN - 1`), en blanco por la izquierda hasta el ancho máximo que da esta especificación.
- **Listas**: la maqueta lleva el primer elemento con su define; el elemento `i` va en `AT + 32 * i`
  (paso de 1 fila salvo que se diga otra cosa) y el cursor en la columna indicada de esa fila.
- **Textos que aparecen o parpadean** (Continuar, ¡Nueva receta!, Pulsa Start...) están en la
  maqueta; el código los borra (escribe `UI_BLANK` en `LEN` celdas) cuando no tocan.
- **Ventana**: los defines de las maquetas de ventana están en coordenadas de pantalla. Cuadro de texto
  (WY = 96): fila de la ventana = fila − 12. Panel (WX = 87): columna de la ventana = columna − 10.
- **Superposiciones** (`*_accion`, `*_cantidad`, `cocina_plato`, `combate_atacar`...): la maqueta
  muestra la pantalla de fondo tapada; las posiciones del fondo se toman de su maqueta base.
- Las maquetas se regeneran con `python games/faro/design/gen_screens.py` (y el título con
  `paint_title.py`): editar allí, no los `.screen` a mano. Cuando el pixel-artist añada a la fuente
  los glifos `¡ ¿ , '` (E14), volver a ejecutar `gen_screens.py`: hoy se dibujan como blanco (los textos
  de ejemplo ya los llevan; las celdas existen).
- Vista previa: `python harness/gb.py preview faro` → `build/preview/screen_*.png`. Los sprites 8x16 se
  listan en las maquetas como sus dos mitades 8x8 (la vista previa dibuja sprites 8x8).

## 1. Tiles y VRAM

### 1.1 Juegos de tiles de UI

| Juego | Fichero | Tiles | Dónde y cuándo |
|---|---|---|---|
| ui | `res/ui.tiles` | **12** | BG 0-11 (`$9000`), arranque, con el LCD apagado; no cambia nunca |
| font + font_lower | `harness/common/` | 46 + 26 | BG 12-83 (46 con los 4 glifos E14) |
| uimenu | `res/uimenu.tiles` | **42** | BG 84-125, en el hueco de la parte A del tileset del mundo: combate y todas las pantallas completas |
| title | `res/title.tiles` | **92** | hueco del tileset (BG 84-175), solo TITLE y FIN DE LA DEMO |
| uispr | `res/uispr.tiles` | 34 (ROM) | sprites: 7 iconos de HUD (14 tiles, solo 4 en VRAM) + haz del faro (20, solo en TITLE) |

`"vram_order": ["ui", "font", "font_lower", ["overworld", "uimenu", "title", ...]]` (los otros
tilesets de mapa, `faro`, `interior`..., en el mismo grupo). El tileset del mundo empieza en 84, como ya
supone `overworld.tiles` (`@ base 84`). En combate y pantallas completas el bloque `$8800-$8FFF`
(BG 128-255) queda libre para imágenes: criatura 7x7 (49), espalda de Leo (30), franja del bioma
(≤ 32), icono de objeto 2x2 (4), imagen 7x7 del Cuaderno, escena del campamento.
Añadir `ui`, `uimenu`, `title`, `uispr` y cada `screen_*` a `"banked_res"`.

### 1.2 ui.tiles (12, residente)

| Índice | Etiqueta | Uso |
|---|---|---|
| 0 | `BLANK` | relleno de cuadros, hueco de las pestañas, celdas vacías |
| 1-8 | `FRAME_TL FRAME_T FRAME_TR FRAME_L FRAME_R FRAME_BL FRAME_B FRAME_BR` | marco de 9 piezas (la 9ª es BLANK). Orden fijo |
| 9 | `CURSOR` | cursor de menú (tile de fondo a la izquierda de la opción) |
| 10 | `ARROW_DOWN` | "hay más": sustituye un `FRAME_B` del borde inferior (texto, listas) |
| 11 | `COIN` | concha (dinero) |

Marco: línea negra gruesa + línea gris oscuro fina + margen blanco de 1 px (lenguaje del estudio), esquinas
redondeadas y un remache gris claro. **Pestaña de título**: el título de un cuadro va sobre su borde
superior: `FRAME_TL`, `FRAME_T`, `BLANK`, texto (desde la col. +3), `BLANK`, `FRAME_T`... (cuadro de
texto con nombre, Atacar, Cocina, Recetas...). Una línea interior de separación = fila de `FRAME_T`
entre dos `FRAME_L/FRAME_R` (EQUIPO fila 8).

### 1.3 uimenu.tiles (42)

| Etiquetas (en orden) | Uso |
|---|---|
| `BAR_L BAR_0..BAR_8 BAR_R` | barra de 64 px = `BAR_L` + 8 tiles + `BAR_R`; tile `k` = `BAR_0 + clamp(px − 8k, 0, 8)` |
| `BOWL_FULL BOWL_MID BOWL_LOW BOWL_EMPTY` | saciedad por banda (≥ 60, 25-59, 1-24, 0) |
| `ST_NET ST_CALM ST_LIT ST_FLY` | banderas de la criatura: ENREDADO, CALMADO, ILUMINADO, VOLANDO |
| `CURSOR_IDLE` | cursor hueco: marca la opción madre mientras hay un submenú/popup |
| `ARROW_UP` | "hay más arriba": sustituye un `FRAME_T` del borde superior |
| `PLUS` | `+` (subida de nivel, ropa +3; la fuente no lo tiene) |
| `POCKET_ITEMS POCKET_FOOD POCKET_GADGETS POCKET_LANTERNS` | bolsillos de MOCHILA; el farolillo es también el icono de "Luces" |
| `FAM_BICHO FAM_BESTIA FAM_AVE FAM_PEZ FAM_REPTIL FAM_FLORA FAM_BRUMA` | familias (orden del GDD 3.4) |
| `DMG_CORTE DMG_GOLPE DMG_PUNTA DMG_FUEGO` | tipos de daño 0-3; el 4 (LUZ) usa `ST_LIT` |
| `MARK_CAUGHT MARK_SEEN` | ● capturada / ○ vista; huecos lleno/vacío de COCINA |
| `POT` | olla (Cocina, notas de cocina, plato activo) |
| `ARROW_LEFT ARROW_RIGHT` | cambio de bolsillo / página / valor (◀ ▶) |

### 1.4 Sprites de UI (uispr.tiles, modo 8x16)

- **HUD**: 2 huecos en VRAM, `HUD_SLOT_HEART` y `HUD_SLOT_BOWL` (2 pares = 4 tiles). Al cambiar de
  banda, el código pone en la cola de tiles (`gbe_tiles`, 32 B, 1 frame) los 2 tiles del estado nuevo:
  `HEART_FULL HEART_HALF HEART_EMPTY`, `BOWL_FULL BOWL_HALF BOWL_EMPTY BOWL_ZERO` (pares consecutivos).
  **Dónde viven en VRAM**: el presupuesto de sprites 0-127 está lleno (Leo 32, NPC 48, criaturas 32,
  efectos 16 de `fx.tiles`, que deja fuera estos iconos). Propuesta: tiles de sprite **252-255**
  (= BG 252-255 de `$8800`), libres porque `overworld.tiles` tiene 166 tiles (84-249). Eso fija el
  tileset del mundo en **≤ 168 tiles** (no 172). Ver preguntas abiertas.
- **Haz del faro** (TITLE): `BEAM_0..BEAM_7` (8 pares) + `BEAM_FLASH` (2 pares, izquierda y derecha).

### 1.5 Presupuestos que cumplen las pantallas
- Campo: BG 0-127 = ui 12 + fuentes 72 + tileset A 44 = 128 (GDD 7.2). La ventana solo usa ui + fuentes.
- Combate: BG 0-127 = 12 + 72 + uimenu 42 = 126. `$8800`: criatura 49 + espalda 30 + bioma ≤ 32 = 111.
- Pantallas completas: igual que combate; `$8800` para la imagen de la pantalla.
- Sprites por línea: campo = HUD 2 (y 4-10) + jugador 2 + actores; los iconos del HUD solo comparten
  línea con actores en la fila de pantalla 0, y el peor caso del GDD 7.3 (8) + 2 = 10. Título: haz 8
  sprites en y 52-67, Leo 2 en y 95-110: ≤ 8 por línea. Combate ≤ 6 (efectos).

---

## 2. TITLE (`title.screen`, `title_menu.screen`) — M1b

**Dibujo**: LCD apagado, `screen_title_map` en el BG `$9800`, SCX = SCY = 0, ventana apagada. Logo FARO
(la O es la lente del faro con sus anillos) filas 1-4, subtítulo `SCREEN_TITLE_AT_LA_ISLA_EN_LA_BRUMA`,
faro cols 15-18 filas 5-13, rocas y mar filas 13-17. BGP 0xE4, OBP0 0xE4.

**Sprites** (lista de la maqueta, en orden): Leo mirando al faro (`mar:SIDE_A`, OAM 0-1, en (112, 95))
y un fotograma del haz (OAM 2-9). El haz lleva **prioridad de fondo (bit 7 de OAM)**: solo se ve sobre el
blanco y pasa por detrás del logo, del texto y de la torre.

**Haz (ciclo de 240 f, sprites a y 52)**: el haz apunta a la izquierda: `BEAM_k` en x = 128 − 8k.
- f 0-119: largo, k = 0..7 visibles (8 sprites).
- f 120-151: se acorta (gira hacia ti): cada 4 f se oculta el sprite más lejano (k = 7, 6, ... 0).
- f 152-167: destello: `BEAM_FLASH` (2 sprites, x 128 y 136, y 52) + BGP 0xE4 → 0x94 (blanco más
  amplio) 8 f y vuelta.
- f 168-199: el haz sale por la derecha (fuera de pantalla): nada.
- f 200-239: vuelve por detrás: aparece de cerca a lejos, un sprite cada 5 f (k = 0..7).

**Estado 1 (Pulsa Start)**: `SCREEN_TITLE_AT_PULSA_START` parpadea 30 f visible / 30 f borrado.
Start o A: SFX `MENU_OK`, semilla del RNG (DIV + frames, GDD 2.0), pasa al estado 2.
**Estado 2 (menú)**: copiar de `screen_title_menu_map` el bloque filas 8-12, cols 2-15 (70 tiles, en 4
frames por la cola) y borrar Pulsa Start. Opciones en `SCREEN_TITLE_MENU_AT_CONTINUAR`,
`..._AT_NUEVA_PARTIDA`, `..._AT_OPCIONES` (paso de 2 filas), cursor `CURSOR` en la columna AT − 1.
- **Continuar** solo con partida válida (`gbe_save`): si no, se borra (`LEN_CONTINUAR`) y el cursor
  empieza en Nueva partida; arriba/abajo la saltan. Con partida, el cursor empieza en Continuar.
- Arriba/abajo con repetición 16/6 f y vuelta al otro extremo; A confirma (SFX `MENU_OK`); B vuelve al
  estado 1. Nueva partida con partida existente: pregunta en el cuadro de texto (BG, fila 12-17 como
  `dialogo_sino`): "¿Borrar la partida?" con el cursor en **No**.
- Salida: fundido a blanco 16 f (BGP 0xE4 → 0x90 → 0x40 → 0x00, 4 f cada paso), LCD apagado.

---

## 3. HUD de campo (`campo_hud.screen`) — M1b

Sin tiles de HUD: dos sprites 8x16. OAM 0 corazón en (4, 4), OAM 1 cuenco en (14, 4).
| Icono | Estado (tiles copiados al hueco) | Cuándo se ve |
|---|---|---|
| Corazón | `HEART_FULL` PV ≥ 50 %, `HEART_HALF` < 50 %, `HEART_EMPTY` < 25 % | oculto (y = 0) si PV ≥ 50 %; medio siempre; vacío parpadeando 16/16 f |
| Cuenco | `BOWL_FULL` sac ≥ 60, `BOWL_HALF` 25-59, `BOWL_EMPTY` 1-24, `BOWL_ZERO` 0 | oculto si ≥ 60; medio siempre; vacío parpadeando 16/16 f; cero parpadeando 8/8 f |

- Al cambiar de banda (en cualquier sentido) el icono se muestra **180 f** con el estado nuevo aunque
  sea "bien" (así se ve que el corazón se llenó). La copia de tiles va por la cola en el frame del cambio.
- Con el panel abierto se **mueven** al panel como etiquetas (§5). Con el cuadro de texto se quedan
  como están (arriba, no estorban).
- Mensajes de umbral la primera vez (guion): "Te suenan las tripas." etc.

---

## 4. Cuadro de texto (ventana) — M1b

`dialogo.screen`, `dialogo_sino.screen`, `dialogo_elige.screen`, `dialogo_cartel.screen`.
Ventana WY = 96, WX = 7: filas de pantalla 12-17 = filas 0-5 del mapa de la ventana.

| Elemento | Posición | Comportamiento |
|---|---|---|
| Marco | filas 12-17, cols 0-19 | se escribe al abrir (120 tiles en 6 frames de ≤ 20, con la ventana aún escondida: `WY = 144` hasta que esté) |
| Nombre (pestaña) | `SCREEN_DIALOGO_AT_TOMASA` (fila 12, col 3), ≤ 12 car. | `BLANK` antes (col 2) y después; sin hablante: borde liso (`dialogo_cartel`) |
| Línea 1 | `SCREEN_DIALOGO_AT_DEJO_ESTO_PARA_TI` − 64 → fila 14, col 1 | 18 car.; la maqueta empieza en col 2 porque el `¡` aún no existe |
| Línea 2 | `SCREEN_DIALOGO_AT_DEJO_ESTO_PARA_TI` (fila 16, col 1) | 18 car. |
| Flecha "más" | fila 17, col 17 (`ARROW_DOWN` en vez de `FRAME_B`) | parpadea 16/16 f mientras espera A/B; no sale en la última página |

- Máquina de escribir: lenta 1 car./2 f, normal 1/f, rápida 2/f; A mantenido ×2; ≤ 4 tiles/f (GDD 4.5).
  SFX `TEXT_BLIP` cada 2 caracteres. A o B con la línea a medias: se completa al instante.
- Página nueva: borrar filas 14 y 16 (36 tiles, 2 frames por la cola) y empezar a escribir.
- Abrir/cerrar: sin animación (aparece al estar escrito el marco: 6 frames ≈ 0.1 s); al cerrar
  `WY = 144` y se devuelve el control en el frame siguiente (así un A no se encadena con otro NPC).
- **ASK (Sí/No)**: la pregunta es **una línea** (fila 14). Fila 16: `SCREEN_DIALOGO_SINO_AT_SI` y
  `..._AT_NO`; cursor en `AT_SI − 1` o `AT_NO − 1`. Empieza en Sí (el guion puede pedir No para
  preguntas peligrosas: borrar partida, soltar). Cruceta alterna, A confirma, B = No.
- **CHOICE (3-4)**: la pregunta va en la página anterior; el cuadro muestra 2x2 opciones:
  `SCREEN_DIALOGO_ELIGE_AT_COMPRAR` (izq.-arriba), `..._AT_VENDER` (der.-arriba), `..._AT_HABLAR`,
  `..._AT_SALIR`; ≤ 8 car.; cursor en AT − 1. Orden de lectura izq.-der., arriba-abajo. B = la última.
- Lint de textos (script.py): líneas ≤ 18 car., pregunta de ASK ≤ 18, opciones ≤ 8, nombres ≤ 12.
- Noche (M2, BGP 0xF9): el cuadro se ve gris claro con tinta negra (legible). Mejora propuesta: corte LYC
  en la línea 96 con BGP 0xE4 para la ventana (gbe ya tiene corte LYC).

---

## 5. Panel de Start (ventana) — M1b

`panel.screen`, `panel_guardar.screen`, `panel_aviso.screen`. Ventana WY = 0, WX = 87 (cols 10-19).
Es un **cajón**: borde izquierdo (col 10), bordes superior e inferior hasta el borde de la pantalla, sin
borde derecho.

**Entrada**: Start en WALK. El panel entra deslizando **8 px/f durante 10 f** (WX 167 → 87): en el
frame n se escribe la columna n de la ventana (18 tiles) y WX = 167 − 8n, así nunca se ve una columna sin
escribir (≤ 18 tiles/frame). Salida: WX += 8 por frame sin escribir nada. SFX `MENU_OK` / `MENU_BACK`.

| Elemento | Posición | Notas |
|---|---|---|
| Entradas | `SCREEN_PANEL_AT_CUADERNO` + 32·i, i = 0..7 | Cuaderno, Mochila, Equipo, Acampar, Mapa (M2), Guardar, Opciones, Salir. **M1**: sin Mapa, 7 entradas seguidas |
| Cursor | col 11 de la fila de la entrada | arriba/abajo con vuelta; recuerda la última entrada mientras dure la partida |
| Nombre | `SCREEN_PANEL_AT_MAR` | ≤ 5 car. |
| Nivel | `SCREEN_PANEL_AT_NV`; valor terminado en `AT_12 + LEN − 1` (col 19) | 1-2 cifras |
| PV | valor terminado en `SCREEN_PANEL_AT_32_38` + 4 (col 19), ≤ 7 car. ("178/178") | etiqueta = **sprite del corazón** (OAM 0) en (88, 96) |
| EN | `SCREEN_PANEL_AT_EN`; valor terminado en col 19 (`AT_9_13 + LEN − 1`), ≤ 5 car. | |
| Saciedad | palabra en `SCREEN_PANEL_AT_NORMAL` (≤ 6): Llena / Normal / Hambre / Debil | etiqueta = **sprite del cuenco** (OAM 1) en (88, 112) |
| Dinero | `COIN` en fila 15 col 11; valor terminado en `AT_1250 + LEN − 1` (col 19) | ≤ 4 cifras |
| Fase (M2) | `SCREEN_PANEL_AT_DIA`: "Dia" / "Noche" | en M1 en blanco |

- Mientras el panel está abierto, OAM 0-1 (HUD) se colocan como etiquetas en esas posiciones y se ven
  siempre (estado actual de la banda); al cerrar vuelven a (4, 4) / (14, 4) con su regla de visibilidad.
- A: Cuaderno / Mochila / Equipo / Opciones → pantalla completa (§7-§9, §14) con fundido rápido.
  Acampar → si se puede, CAMP (§12); si no, **aviso** (`panel_aviso`). Guardar → `panel_guardar`.
  Salir, B o Start → cerrar.
- **Aviso** (`panel_aviso`): filas 10-16, cols 11-19, 9 car. por línea, paso de 1 fila, desde
  `SCREEN_PANEL_AVISO_AT_NO_ES`: "No es / seguro: / hay algo / cerca." (criatura alerta a ≤ 5),
  "Aqui no / se puede / acampar." (pueblo o sin casilla CAMP), "Te falta / madera." (sin leña).
  90 f o A/B y vuelven las estadísticas. El cursor queda en `CURSOR_IDLE` durante el aviso.
- **Guardar** (`panel_guardar`): las filas 10-16 pasan a ser el cuadro de guardado: nombre
  `SCREEN_PANEL_GUARDAR_AT_MAR`, "Luces" (`AT_LUCES`, valor terminado en col 19), "Tiempo"
  (`AT_TIEMPO`, valor h:mm terminado en col 19 en la fila siguiente, hasta 99:59), pregunta
  `AT_GUARDAR_2` (fila 15, col 11 con el `¿`), `AT_SI` / `AT_NO` con cursor en AT − 1 (empieza en Sí).
  A en Sí: la fila 15 dice "Guardando" (sin cursor), se guarda (~60k T, `skip_measure`), SFX `SAVE`,
  "Guardado" 60 f y vuelven las estadísticas. B / No: vuelven las estadísticas.

---

## 6. COMBATE — M1b

`combate.screen` (menú), `combate_msg.screen`, `combate_atacar.screen`, `combate_tecnica.screen`,
`combate_objeto.screen`, `combate_nivel.screen`. Todo en el BG `$9800`, ventana apagada, SCX = SCY = 0
salvo las sacudidas.

**Entrada** (GDD 3.1): "!" si estaba alerta → 3 destellos BGP invertido (0x1B) 4 f → fundido a negro
12 f (BGP 0xE4 → 0xF9 → 0xFE → 0xFF, 4 f) → LCD apagado: cargar uimenu + imágenes, escribir el mapa
(`skip_measure`) → fundido de entrada 12 f. Primer mensaje: "¡Un Pinzarro!" / "¡Te ataca un Erizal!"
(emboscada) / "Lo pillas por sorpresa." (Ventaja).

### 6.1 Disposición
| Bloque | Posición | Contenido |
|---|---|---|
| Criatura | cols 13-19, filas 0-6 | imagen 7x7 (mapa secuencial, tiles en `$8800`); las de 40x40 centradas (cols 14-18, filas 1-5) |
| Bloque enemigo | medio marco: `FRAME_L` col 0 filas 1-3, `FRAME_BL` (4, 0), `FRAME_B` fila 4 cols 1-12 | |
| — nombre | `SCREEN_COMBATE_AT_PINZARRO` | ≤ 10 |
| — nivel | `SCREEN_COMBATE_AT_NV3` | "Nv" + 1-2 cifras, a la izquierda |
| — estado | `SCREEN_COMBATE_AT_DOR` | 3 letras: DOR ATU CEG VEN QUE REN (blanco si ninguno) |
| — banderas | fila 2, cols 10, 11, 12 | `ST_NET`/`ST_FLY` (excluyentes), `ST_CALM`, `ST_LIT`, de izquierda a derecha sin huecos |
| — PV | etiqueta `SCREEN_COMBATE_AT_PV`; barra en fila 3, cols 3-12 | la criatura **no** muestra números (salvo tras Ojo de farero: el mensaje los dice) |
| Espalda de Leo | cols 1-5, filas 7-12 | imagen 5x6 |
| Bloque de Leo | medio marco: `FRAME_R` col 19 filas 7-10, `FRAME_BR` (11, 19), `FRAME_B` fila 11 cols 6-18 | |
| — nombre / nivel | `SCREEN_COMBATE_AT_MAR`; nivel terminado en `AT_NV5 + LEN − 1` (col 18) | "Nv" + cifras |
| — PV | etiqueta `SCREEN_COMBATE_AT_PV_2`, barra fila 8 cols 9-18; números terminados en `AT_32_38 + 4` (col 18), ≤ 7 car. | |
| — estado | `SCREEN_COMBATE_AT_VEN` (3 letras) | |
| — EN | `SCREEN_COMBATE_AT_EN`; valor terminado en `AT_9_13 + 3` (col 14), ≤ 5 car. | |
| — saciedad | fila 10, col 18 | `BOWL_FULL + banda` |
| Cuadro inferior | filas 13-17, cols 0-19 | menú / mensajes / listas |

**Barras**: `px = (pv × BARK[pvmax]) >> 8` (GDD 3.1); tile k = `BAR_0 + clamp(px − 8k, 0, 8)`. Al bajar
o subir, el valor mostrado se mueve 1 px cada 2 f hacia el real: como mucho 1 tile cambia por paso. La
barra de Leo y los números se actualizan juntos (los números cuentan hacia el valor real a la vez).
Golpe a la criatura: parpadeo de sus 49 celdas (BLANK y vuelta, 4 f cada fase, 3 veces) + `shake_x` ±2
6 f. Golpe a Leo: `shake_y` ±2 8 f.

### 6.2 Menú de órdenes (`combate.screen`)
3 filas x 2 columnas: `SCREEN_COMBATE_AT_ATACAR`, `..._AT_TECNICA`, `..._AT_OBJETO`, `..._AT_ARTILUGIO`,
`..._AT_HUIR`, `..._AT_CAPTURAR`. Cursor en AT − 1 (cols 1 y 9). Cruceta mueve en la rejilla (sin
vuelta), A abre, B no hace nada en el menú raíz. Al volver de un submenú, el cursor está en la orden de
la que se salió. Capturar con la bolsa sin farolillos: SFX `MENU_BACK` y mensaje "No te quedan farolillos.".

### 6.3 Mensajes (`combate_msg.screen`)
Líneas en filas 14 y 16, cols 1-18 (`SCREEN_COMBATE_MSG_AT_QUEDAN_3_PV` = fila 16; fila 14 = esa − 64).
2 car./f. `ARROW_DOWN` en (17, 17) parpadeando 16/16 f en los mensajes que esperan A (resultado de
captura, botín, subida de nivel, técnica aprendida); el resto avanza solo a los 40 f de completarse
(A lo adelanta). Mensajes típicos (≤ 18 por línea): "Leo usa el Remo.", "¡Critico!", "No le afecta.",
"Pinzarro se duerme.", "Lanzas el farolillo.", "¡Pinzarro capturado!", "¡Nueva luz para el faro!",
"Ganas 24 PX.", "Consigues: / Carne cangrejo x2".

### 6.4 Submenús (Atacar, Técnica, Objeto, Artilugio, Capturar)
- El cuadro inferior lleva **pestaña** con el nombre de la orden (`SCREEN_COMBATE_ATACAR_AT_ATACAR`) y
  muestra 3 elementos en las filas 14-16: nombre desde `..._AT_CUCHILLO` (col 2, ≤ 14), cursor col 1,
  valor a la derecha terminado en col 18 (coste EN en Técnica, cantidad en Objeto/Artilugio/Capturar;
  nada en Atacar ni en artilugios llave). Más de 3: se desplaza de uno en uno; `ARROW_UP` en (13, 17) si
  hay más arriba, `ARROW_DOWN` en (17, 17) si hay más abajo.
- **Cuadro de detalle**: mientras hay una lista abierta, el bloque de Leo (cols 6-19, filas 6-12) se
  sustituye por un cuadro con marco completo (filas 6-12, cols 6-19; interior filas 7-11, cols 7-18,
  12 car.). Al cerrar la lista se vuelve a dibujar el bloque de Leo.
  - Atacar: fila 7 icono de tipo (`DMG_*`, `ST_LIT` para LUZ) col 7 + nombre del tipo
    (`SCREEN_COMBATE_ATACAR_AT_CORTE`); fila 8 "Poder" (`AT_PODER`) y el valor terminado en col 15
    (`AT_8`); fila 9 eficacia (`AT_POCO_EFICAZ`): "Eficaz" / "Poco eficaz" / "No le afecta", en blanco si
    no se conoce (sin Ojo de farero ni captura) o si es normal.
  - Técnica: fila 7 "Coste" + "n EN" (`SCREEN_COMBATE_TECNICA_AT_COSTE`, `AT_2_EN`), fila 8 "Tienes" +
    EN actual/máx (`AT_TIENES`, `AT_9_13`), filas 9-10 descripción corta (2 x 12). Sin EN suficiente: el
    coste de la lista parpadea 8/8 f y A da SFX `MENU_BACK`.
  - Objeto / Artilugio / Capturar: fila 7 "Tienes" + cantidad (`SCREEN_COMBATE_OBJETO_AT_TIENES`,
    `AT_3`), filas 8-10 descripción corta (3 x 12).
- A: elige (y gasta el turno salvo Atacar → arma, que lo gasta al atacar). B: vuelve al menú.
- Coste de VBlank al abrir: cuadro inferior 54 tiles + detalle 98 tiles → por la cola en 8 frames
  (≤ 20 por frame); el cursor no se mueve hasta que acaba (≈ 0.13 s).

### 6.5 Subida de nivel (`combate_nivel.screen`)
Tras los mensajes de victoria: la zona del enemigo se borra y aparece un cuadro cols 8-19 filas 0-6 con
pestaña "Nv6" (`SCREEN_COMBATE_NIVEL_AT_NV6`, el código escribe el nivel nuevo). Filas 1-5: PV EN ATQ
DEF AGI (`AT_PV`, `AT_EN`, `AT_ATQ`, `AT_DEF`, `AT_AGI`) con `PLUS` en col 17 y la subida (1 cifra) en
col 18; con 2 cifras, `PLUS` en col 16. Mensaje "¡Leo sube al Nv6!" con flecha. A cierra; luego
"Aprende Golpe suave." si toca.

### 6.6 Salida
Victoria / captura / huida: fundido a negro 12 f, reconstrucción del campo con el LCD apagado, fundido de
entrada 12 f. PV 0: "Leo se desmaya..." → DESMAYO (§15).

---

## 7. MOCHILA — M1b (`mochila.screen`, `mochila_accion.screen`)

Pantalla completa (fundido rápido: BGP a blanco en 8 f, LCD apagado, `skip_measure`, fundido de entrada 8 f).
| Elemento | Posición |
|---|---|
| Cabecera | cuadro filas 0-2; `ARROW_LEFT` (1, 1), icono del bolsillo `POCKET_*` (1, 3), nombre `SCREEN_MOCHILA_AT_COMIDA` (≤ 10: Objetos, Comida, Artilugios, Farolillos), `ARROW_RIGHT` (1, 18) |
| Lista | cuadro filas 3-12; 8 visibles, filas 4-11: nombre desde `SCREEN_MOCHILA_AT_CARNE_CANGREJO` (col 2, ≤ 14), cantidad terminada en col 18 (`AT_2`), cursor col 1 |
| Flechas | `ARROW_UP` en (3, 17) / `ARROW_DOWN` en (12, 17) si hay más arriba / abajo |
| Info | cuadro filas 13-17: icono 16x16 del objeto en cols 1-2 filas 14-15 (4 tiles del pixel-artist en `$8800`), descripción desde `SCREEN_MOCHILA_AT_CARNE_FRESCA` (fila 14, col 4) y `AT_SE_ESTROPEA` (fila 16, col 4), 2 x 15 car. |

- Izquierda/derecha: cambia de bolsillo (redibuja cabecera + lista + info: ~170 tiles, por la cola en
  9 frames, o con el LCD apagado si se prefiere; recomendado: cola, sin parpadeo). Arriba/abajo con
  repetición 16/6 f; la lista se desplaza cuando el cursor pasa de la fila 4 u 11 (redibujar 8 filas = 128
  tiles en 7 frames; el cursor sigue moviéndose: los números se escriben en el orden en que se ven).
- Columna de cantidad: número (1-2 cifras); "Sel" en el artilugio registrado en Select; vacío en objetos
  llave; en Farolillos llenos (si se listan aquí): "Nv" + nivel.
- Start: ordena el bolsillo (tipo y luego nombre). B: vuelve al panel (fundido rápido).
- **Popup de acción** (`mochila_accion`): cuadro cols 8-19, filas 6-12; opciones desde
  `SCREEN_MOCHILA_ACCION_AT_USAR` (col 10, paso 1, ≤ 9), cursor col 9. El cursor de la lista queda
  como `CURSOR_IDLE`. Opciones por bolsillo: Objetos "Usar Tirar Salir", Comida "Comer Tirar Salir",
  Artilugios "Usar Registrar Tirar Salir" (Tirar solo en gastables; Usar solo si sirve en el campo),
  Farolillos "Tirar Salir". B = Salir. Al cerrar se redibujan las filas 6-12 de la lista.
- Tirar: cuadro de cantidad (§11.3, sin moneda ni total) y "¿Seguro?" en la info con Sí/No.
- Comer / Usar: el efecto se dice en la info ("+20 PV", "Ya estas llena."), SFX `EAT`.

---

## 8. CUADERNO — M1b (`cuaderno.screen`, `cuaderno_ficha.screen`)

### 8.1 Lista
| Elemento | Posición |
|---|---|
| Cabecera | `SCREEN_CUADERNO_AT_CUADERNO`; `POCKET_LANTERNS` en (1, 13); capturadas/total terminado en col 18 (`AT_5_48`) |
| Lista | filas 4-13 (10 visibles): número `SCREEN_CUADERNO_AT_01` (2 cifras), marca en col 5 (`MARK_CAUGHT` / `MARK_SEEN` / blanco), nombre `SCREEN_CUADERNO_AT_PINZARRO` (col 7, ≤ 10) o "-----" si no se conoce; cursor col 1 |
| Flechas | (3, 17) / (14, 17) |
| Pie | familia: `FAM_*` en (16, 1) + nombre `SCREEN_CUADERNO_AT_BICHO` (≤ 6); "Cazas" `AT_CAZAS` + número terminado en col 18 (`AT_3`). En blanco para especies desconocidas |

Lista de las 48 (M1b: el código lista hasta la última especie conocida + 3 desconocidas, mínimo 10).
A: ficha (solo vistas). B: panel. Izquierda/derecha: página de 10.

### 8.2 Ficha
| Elemento | Posición |
|---|---|
| Imagen | marco cols 0-8, filas 0-8; imagen 7x7 en cols 1-7, filas 1-7 (`$8800`, carga con el LCD apagado al entrar; al cambiar de especie: 49 tiles por la cola en 4 frames con la imagen en BLANK mientras tanto) |
| Nombre | `SCREEN_CUADERNO_FICHA_AT_PINZARRO` (≤ 10) |
| Número + marca | `AT_01`; marca en (2, 13) |
| Familia | `FAM_*` en (3, 10), nombre `AT_BICHO` |
| Débil | `AT_DEBIL`; iconos de tipo alineados a la derecha terminando en col 19 (≤ 2) |
| Resiste | `AT_RESISTE` (para BRUMA "Inmune", 6 car.); iconos terminando en col 19 (≤ 3) |
| Iconos desconocidos | `QUESTION` de la fuente en lugar del icono hasta Ojo de farero o captura |
| Cazas | `AT_CAZAS`, número terminado en col 18 (`AT_3`) |
| Zona / Cebo | `AT_ZONA` + valor `AT_PLAYA` (col 7, ≤ 12); `AT_CEBO` + valor `AT_PESCADO` (≤ 12) |
| Descripción | 3 líneas de 18 en filas 13-15 desde `AT_ANDA_DE_LADO_Y` (col 1) |
| Nota de cocina | `POT` en (16, 1), texto desde `AT_CON_SAL` (col 3, ≤ 16) |

Vistas sin capturar: descripción y nota = "???" (fila 13). Arriba/abajo: especie vista anterior /
siguiente. B: lista con el cursor en esta especie.

---

## 9. EQUIPO — M1b (`equipo.screen`, `equipo_tecnicas.screen`)

Cabecera común (filas 0-2): flechas de página (1, 1) / (1, 18), nombre `SCREEN_EQUIPO_AT_MAR` (≤ 5),
estado `AT_VEN` (3 letras o blanco), nivel terminado en `AT_NV3 + LEN − 1` (col 17). Izquierda/derecha
cambia de página (Estado ↔ Técnicas).

**Página Estado** (`equipo.screen`):
| Elemento | Posición |
|---|---|
| PV / EN | `AT_PV`, `AT_EN`; valores terminados en col 10 (`AT_26_30`, `AT_11_11`), ≤ 7 / ≤ 5 car. |
| ATQ / DEF / AGI | `AT_ATQ`, `AT_DEF`, `AT_AGI`; valores (≤ 2 cifras, con el plato aplicado) terminados en col 18 |
| Saciedad | `BOWL_*` en (6, 1) + palabra `AT_NORMAL` (Llena / Normal / Hambre / Debil) |
| PX | `AT_PX` + barra fila 7 cols 3-12: progreso hacia el nivel siguiente (`px = (xp − base) × 64 / tramo`, tabla) |
| Armas | filas 9-11: `AT_CUCHILLO` + 32·i (col 2, ≤ 14, "-" si el hueco está vacío), icono de tipo en col 18; cursor col 1 |
| Ropa | `AT_CHUBASQUERO` (fila 12); `PLUS` + DEF terminado en col 18 (1-2 cifras; con 2, `PLUS` en col 16) |
| Detalle | fila 15: del elemento señalado: arma "Corte  Poder  8" (`AT_CORTE`, `AT_PODER`, valor `AT_8`); ropa "Defensa" + valor |
| Plato activo | `POT` en (16, 1), mejora `AT_CORAZA` (≤ 10: Fuerza, Coraza, Agil, Vigor, Sigilo, Cazador, Mano firme, Olfato), pasos que quedan terminados en col 18 (`AT_384`); sin plato: "Sin plato" y nada a la derecha |

A en un hueco de arma o ropa: popup (estilo `mochila_accion`, cols 4-19) con las armas/ropas que se
tienen; A equipa, B cancela. B: vuelve al panel.

**Página Técnicas** (`equipo_tecnicas.screen`): lista con pestaña "Tecnicas", filas 4-12 (9 visibles),
nombre `SCREEN_EQUIPO_TECNICAS_AT_CONCENTRAR` + 32·i, coste terminado en col 18; descripción filas 15 y
16 (`AT_ATAQUE_QUE_NUNCA`, `AT_DEJA_A_0_PV`, 18 car.). A en una técnica usable fuera de combate
(Concentrar, Primeros auxilios, Respiro): se usa y el efecto sale en la descripción.

---

## 10. COCINA — M1b (`cocina.screen`, `cocina_plato.screen`, `recetas.screen`)

En el campamento, la cocina de la posada y la casa de Tomasa.
| Elemento | Posición |
|---|---|
| Huecos | cuadro filas 0-5, pestaña "Cocina"; filas 1-3: `MARK_CAUGHT` (lleno) / `MARK_SEEN` (vacío) en col 1, ingrediente desde `SCREEN_COCINA_AT_CARNE_CANGREJO` + 32·i (col 3, ≤ 14) o `DASH` si está vacío |
| Receta prevista | fila 4: `ARROW_RIGHT` en col 1 + nombre `AT_CANGREJO_Y_SAL` (col 3, ≤ 14) si los huecos forman una receta **conocida**; "???" si no es conocida (puede ser nueva o Mejunje); blanco con los huecos vacíos |
| Lista | cuadro filas 6-13, pestaña "Ingredientes"; filas 7-12 (6 visibles): nombre `AT_CARNE_CANGREJO_2` (col 2), cantidad terminada en col 18 (lo que queda tras lo puesto en los huecos); flechas (6, 17) / (13, 17) |
| Ayudas | filas 15-16: `AT_SELECT` + `AT_RECETAS`, `AT_START` + `AT_COCINAR` |

- A: el ingrediente va al siguiente hueco libre (SFX `MENU_OK`; con los 3 llenos, SFX `MENU_BACK`).
  B: saca el último hueco; con los huecos vacíos, sale. Start: cocina (con ≥ 1 hueco). Si se puede
  más de una vez: cuadro de cantidad (§11.3, "x N" sin moneda). SFX `COOK_SIZZLE` 40 f.
- **Resultado** (`cocina_plato`): cuadro cols 2-17, filas 3-12 sobre la cocina. `¡Nueva receta!`
  (`SCREEN_COCINA_PLATO_AT_NUEVA_RECETA`, fila 4) solo si es nueva (jingle; si no, borrado). Icono del
  plato 16x16 en cols 9-10, filas 6-7. Nombre centrado en la fila 9 (`AT_CANGREJO_Y_SAL`, ≤ 14: col =
  3 + (14 − len) / 2). Efecto centrado en la fila 11 (≤ 14: "+25 PV  Coraza", el `+` es `PLUS`).
  Mejunje: "Mejunje" / "+10 saciedad"... ≤ 14. A: cierra (redibuja filas 3-12).
- **Recetas** (`recetas.screen`, Select): pestaña "Recetas" + conocidas/32 (`AT_RECETAS`, `AT_8_32`).
  Lista filas 1-11 (11 visibles): cursor col 1, `MARK_CAUGHT` en col 3 si tienes los ingredientes /
  `MARK_SEEN` si falta alguno, nombre `AT_ASADO_SIMPLE` (col 5, ≤ 14). Pie filas 14-16: los 1-3
  ingredientes (marca col 1, nombre col 3, "tienes" terminado en col 18). A: llena los huecos con esa
  receta y vuelve a COCINA (= "Repetir receta": la lista se abre en la última receta cocinada, así
  repetir es Select, A, Start). Si faltan ingredientes, A da SFX `MENU_BACK`. B: vuelve sin cambios.

---

## 11. TIENDA — M1b (`tienda.screen`, `tienda_cantidad.screen`, `tienda_vender.screen`)

Desde el guion (CHOICE "Comprar / Vender / Hablar / Salir"). Pantalla completa con fundido rápido.
| Elemento | Posición |
|---|---|
| Cabecera | modo `SCREEN_TIENDA_AT_COMPRAR` ("Comprar" / "Vender"), `COIN` (1, 13), dinero terminado en col 18 (`AT_1250`) |
| Lista | cuadro filas 3-12, **paso de 2 filas**, 4 visibles: fila del nombre (`AT_POCION`, col 2, ≤ 14; cursor col 1), fila del precio (`COIN` en col 14, precio terminado en col 18, ≤ 4 cifras). Vender: "x" + cantidad que tienes terminada en col 18 en la fila del nombre (la x distingue cantidades de precios) |
| Flechas | (3, 17) / (12, 17) |
| Pie | descripción 2 líneas en filas 14-15 (`AT_CURA_30_PV_DE_UNA`, 18 car., paso 1), "Tienes" (`AT_TIENES`) + cantidad terminada en col 9 |

### 11.3 Cuadro de cantidad (también MOCHILA Tirar y COCINA x N)
Cuadro cols 8-19, filas 9-11. "x" `SCREEN_TIENDA_CANTIDAD_AT_X_3` (col 10), cantidad terminada en
col 12 (1-2 cifras), `COIN` en col 14, total terminado en col 18 (`AT_60`); sin moneda ni total en Tirar
y Cocinar. `ARROW_UP` en (9, 12) y `ARROW_DOWN` en (11, 12). Arriba/abajo ±1, izquierda/derecha ±10,
con vuelta 1 ↔ máximo (lo que puedes pagar y llevar). A: compra (SFX, dinero y "Tienes" se actualizan,
el pie dice "¡Gracias!" 60 f). B: cancela. Sin dinero o sin sitio: A con SFX `MENU_BACK` y el pie dice
"No te llega." / "No te cabe.".

---

## 12. CAMPAMENTO — M1b (`campamento.screen`, `capturas.screen`)

| Elemento | Posición |
|---|---|
| Escena | filas 0-9, 20x10: imagen del pixel-artist (Leo, hoguera, olla, noche); la hoguera se anima con parches de tiles (3 fotogramas, 8 f) o con los sprites `FIRE_0..2` de `fx.tiles` |
| Estado | cuadro cols 0-7, filas 10-17: PV `SCREEN_CAMPAMENTO_AT_PV` + valor actual terminado en col 6 (`AT_32`, ≤ 3 cifras); EN `AT_EN` + valor en col 6; `BOWL_*` en (13, 1) + saciedad 0-100 terminada en col 6 (`AT_41`); `POCKET_LANTERNS` en (15, 1) + farolillos llenos/tope terminado en col 6 (`AT_3_12`); fase `AT_NOCHE` (M2; en M1 en blanco) |
| Menú | cuadro cols 8-19, filas 10-17: `AT_COCINAR` + 32·i (col 10): Cocinar, Descansar, Salar, Capturas, Guardar, Recoger; cursor col 9 |

- Cocinar → COCINA. Descansar → pregunta Sí/No en un cuadro de texto dibujado en el BG (filas 12-17, como
  `dialogo_sino`, sin pestaña): "¿Descansar hasta el dia?" (M2: elegir día/noche); Sí: fundido a negro
  32 f, efecto (GDD 2.7), fundido de entrada, el estado se actualiza. Salar → lista de perecederos con el
  formato de MOCHILA (pestaña "Salar"), A sala 1 (necesita Sal: si no, "No tienes sal."). Capturas →
  `capturas`. Guardar → cuadro de guardado igual que `panel_guardar` dibujado en el BG sobre el menú
  (cols 8-19, filas 10-17). Recoger / B → vuelve al mapa (la hoguera desaparece).
- **Capturas** (`capturas.screen`): pestaña "Capturas" + llenos/tope (`AT_CAPTURAS`, `AT_3_12`); lista
  filas 1-12: cursor col 1, `POCKET_LANTERNS` col 2, especie `AT_PINZARRO` (col 4, ≤ 10), nivel terminado
  en col 18 (`AT_NV3`). Pie filas 15-16: "Cocinar da:" + botín principal (`AT_COCINAR_DA`,
  `AT_CARNE_CANGREJO_X2`). A: popup "Cocinar / Soltar / Salir" (estilo `mochila_accion`); Soltar pide
  confirmación con el cursor en No.

---

## 13. ANILLO DEL FARO (LAMP) — M1b (`faro_anillo.screen`)

Escena con guion en el mapa de la Sala de la Lente (tileset del pixel-artist), entrada bloqueada:
1. Fundido a blanco 16 f desde el Vivero/escalera, cámara en la lente, fundido de entrada.
2. Leo delante de la lente; "!" sobre él; 60 f de espera (música se calla).
3. Destellos: BGP 0xE4 → 0x90 → 0x40 → 0x00 → 0x40 → 0x90 → 0xE4 (3 f cada paso), 3 veces, SFX en cada pico.
4. En el blanco del tercer destello se escribe el parche del anillo n encendido (metatiles del pixel-artist,
   ≤ 2 por VBlank) y se queda encendido.
5. Jingle "Anillo encendido" (≈ 180 f) y cuadro de texto con pestaña "Faro":
   `SCREEN_FARO_ANILLO_AT_ANILLO_1_DE_6` ("Anillo n de 6") + línea 2 de recuerdo / pista ("La luz llega
   lejos."), luego las páginas del recuerdo de Ines.
6. Fundido a blanco, cámara en el muro de Bruma de la región (warp de cámara con LCD apagado), fundido de
   entrada; la Bruma se disuelve: BGP 0xE4 ↔ 0x90 alternando cada 4 f mientras se cambian sus celdas de 2
   en 2 a suelo (orden de fuera hacia dentro); texto "La bruma se retira del camino de las Marismas.".
7. Vuelta a Leo. En M1b, después: FIN DE LA DEMO.

---

## 14. OPCIONES, NOMBRE, MAPA, FINAL

**OPCIONES** (`opciones.screen`, M1b): desde TITLE y el panel. Cuadro filas 2-12 con pestaña. Filas 4/6/8:
cursor col 2, etiqueta `SCREEN_OPCIONES_AT_TEXTO` / `AT_SONIDO` / `AT_SALIR`, valor entre `ARROW_LEFT`
(col 10) y `ARROW_RIGHT` (col 18), valor desde col 11 (≤ 7): Texto Lento / Normal / Rapido; Sonido
Estereo / Mono. Izquierda/derecha cambian al momento; con Texto, la muestra de las filas 14-16 se vuelve a
escribir a la velocidad nueva. B o Salir: vuelve (se guarda en `options` con la partida).

**NOMBRE** (`nombre.screen`, M2): nombre en `SCREEN_NOMBRE_AT_MAR` (5 huecos, `DASH` = vacío; el hueco
siguiente parpadea 16/16 f). Letras A-Z en la rejilla (filas 5/7/9, cols 2, 4, ... 18; cursor a su
izquierda); Select cambia a minúsculas (solo se ven minúsculas a partir de la 2ª letra si se elige
mayúscula inicial automática: recomendado). "Borrar" (`AT_BORRAR`) y "Fin" (`AT_FIN`). B borra, Start
salta a Fin. Por defecto "Leo".

**MAPA** (M2) y **FINAL / CRÉDITOS** (M4): sin maqueta todavía (el mapa depende del PNG del mundo de
`world.py`; el final son imágenes del pixel-artist). Usarán el mismo marco y pestañas.

---

## 15. DESMAYO y FIN DE LA DEMO — M1b

**DESMAYO** (`desmayo.screen`): tras "Leo se desmaya..." en combate, fundido a negro 12 f; con el LCD
apagado se carga este mapa y se muestra con **BGP = 0x1B** (invertido: texto blanco sobre negro; la vista
previa lo enseña normal). `SCREEN_DESMAYO_AT_MAR_SE_DESMAYA` se escribe a 1 car. / 4 f (los puntos van
después del run, son `DOT`), 90 f, fundido a negro, despertar en la enfermería (guion: enfermera +
"Has perdido 150 C.").

**FIN DE LA DEMO** (`fin_demo.screen`): LCD apagado; filas 0-5 = logo del título (mismos tiles).
Cuadro filas 7-16 con pestaña "Fin de la demo": Luces (`AT_LUCES`, valor terminado en col 17), Cazas,
Nivel, Tiempo (h:mm), "Gracias por / jugar!" (filas 14-15). Se guarda antes de mostrarlo; A vuelve a TITLE.

---

## 16. Transiciones (BGP; OBP0/OBP1 siguen la misma rampa)

| Paso | Rampa | Duración |
|---|---|---|
| Campo ↔ pantalla completa (Mochila, Cuaderno, Equipo, Opciones, Tienda, Campamento) | a blanco: 0xE4, 0x90, 0x40, 0x00 | 2 f por paso (8 f), LCD apagado, redibujo `skip_measure`, entrada igual al revés |
| Entre pantallas completas (Cocina ↔ Recetas, Cuaderno ↔ ficha) | sin fundido: redibujo por la cola | ≤ 20 tiles/frame |
| Campo → combate | 3 destellos 0x1B 4 f, a negro 0xE4, 0xF9, 0xFE, 0xFF 4 f por paso | GDD 3.1 |
| Título → juego, desmayo, descansar | a negro 0xE4, 0xF9, 0xFE, 0xFF | 4 f por paso |
| Warps | a negro 2 f por paso | |

Cualquier cambio de pantalla entera = LCD apagado dentro del fundido. En juego, la cola de VRAM nunca pasa
de 20 tiles por frame (texto, listas, popups).

---

## 17. Textos y longitudes

Reglas (lint en `script.py` / `tables.py`): tipo frase, sin tildes ni ñ (fuente). Nombres de especie
≤ 10, objetos/platos/armas/ropa/técnicas ≤ 14 (columna de lista cols 2-15), descripción de objeto 2 x 15
(MOCHILA) y 3 x 12 (detalle de combate), descripción de técnica 2 x 12 y 2 x 18, líneas de diálogo 18,
pregunta ASK 18, opciones CHOICE 8, nombres de hablante 12, zona/cebo 12, nota de cocina 16, descripción
de ficha 3 x 18, mejora de plato ≤ 10.

**Nombres del GDD que no caben** (proponer al game-designer; las maquetas usan versiones cortas):
| GDD | Car. | Propuesta |
|---|---|---|
| Cuchillo de pesca | 17 | Cuchillo |
| Sable del farero | 16 | Sable farero |
| Martillo de faro | 16 | Martillo faro |
| Farol de guerra | 15 | Farol guerra |
| Farolillo de plata / de bruma / maestro | 18 / 18 / 17 | Farol de plata / Farol de bruma / Farol maestro |
| Galleta marinera | 16 | Galleta |
| Dardo somnifero | 15 | Somnifero |
| Cebo de pescado | 15 | Cebo pescado |
| Pimienta de roca | 16 | Pimienta |
| Silbato de gaviota | 18 | Silbato |
| Primeros auxilios | 17 | Vendaje |
| Carne de cangrejo / Filete de anguila / Huevo de gaviota / Muslo de conejo / Huevas de erizo | 15-17 | Carne cangrejo / Filete anguila / Huevo gaviota / Muslo conejo / Huevas erizo |
| Platos: Pescado a la brasa, Cangrejo con sal, Ancas con bayas, Tortilla marinera, Estofado de cabo, Mermelada de duna, Anguila ahumada, Guiso del cazador, Empanada de mar | 15-18 | Pescado asado, Cangrejo y sal, Ancas y bayas, Tortilla mar, Estofado, Mermelada, Anguila curada, Guiso cazador, Empanada |
| Leña (ñ) | — | "Madera" (o unificar con Ramas secas) |
| Estado ENV (envenenado) | — | **VEN**: "ENV" junto a la etiqueta EN se confunde |

---

## 18. Escritura de tiles por frame (resumen para el programador)

| Momento | Tiles | Cómo |
|---|---|---|
| Abrir cuadro de texto | 120 (marco) | cola, 6 frames, ventana escondida hasta acabar |
| Escribir texto | ≤ 4 por frame | cola (gbe_tbox) |
| Abrir panel | 180 | 1 columna (18) por frame durante el deslizamiento |
| Estadísticas del panel / aviso / guardar | ≤ 63 | cola, 4 frames |
| Submenú de combate | 152 | cola, 8 frames |
| Barra de combate | 1 por paso | directo en VBlank |
| Parpadeo de criatura | 49 | por fase (GDD 8.3) |
| Lista que se desplaza (Mochila, Cuaderno) | 8-10 filas x 18 | cola, ≤ 20 por frame |
| Popup (acción, cantidad, plato) | 30-160 | cola; al cerrar se redibuja lo tapado |
| Pantalla completa | entera | LCD apagado, `skip_measure` |
| HUD (cambio de banda) | 2 tiles de sprite (32 B) | cola de tiles, 1 frame |
