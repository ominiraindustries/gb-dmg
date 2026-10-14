# CABALLERITO - UI spec (para el programador)

Autor: ui-designer · 2026-10-14 · Fuente: `design/gdd.md` v1.0 (§4, §5).
Maquetas: `design/screens/*.screen` → `python harness/gb.py preview platformer` →
`build/preview/screen_*.png`. Coordenadas siempre en **(fila, columna) de tiles 8x8**, fila 0-17,
columna 0-19, salvo que diga "px".

Textos: español, mayúsculas, sin tildes. Fuente compartida `harness/common/font.tiles`
(DIGIT0..9, LETTER_A..Z, DASH, EXCLAM, DOT, COLON, QUESTION). No hace falta añadir nada a la fuente.

---

## 0. Tiles de UI (`res/ui.tiles`, 67 tiles)

| Índice | Etiqueta | Grupo | Uso |
|---|---|---|---|
| 0 | `BLANK` | HUD | blanco (espacio). Si el tile de cielo del tileset es blanco puro se puede usar ese en su lugar |
| 1 | `ICON_COIN` | HUD | moneda (HUD fila 0) |
| 2 | `ICON_HEAD` | HUD | cabeza de Teo = vidas (HUD fila 1, INTRO) |
| 3 | `ICON_TIME` | HUD | reloj de arena = tiempo |
| 4 | `ICON_TIMES` | HUD | signo "x" pequeño apoyado en la línea base de la fuente (no es la letra X) |
| 5-12 | `FRAME_TL, FRAME_T, FRAME_TR, FRAME_L, FRAME_R, FRAME_BL, FRAME_B, FRAME_BR` | SCREEN | marco de caja (CLEAR, GAMEOVER) |
| 13-14 | `WALL_TOP, WALL_BRICK` | SCREEN | muralla con almenas (TITLE, CLEAR, GAMEOVER), se repiten cada 8 px |
| 15-18 | `SWORD_HILT, SWORD_GUARD, SWORD_BLADE, SWORD_TIP` | SCREEN | espada bajo el logo (TITLE) |
| 19-66 | `LOGO_00 .. LOGO_47` | LOGO | logo CABALLERITO, 3 filas x 18 columnas (solo TITLE) |

Carga en VRAM (zona BG):
- **Siempre residentes en INTRO/PLAY/PAUSE/DYING/GOAL:** fuente (41) + grupo HUD (5, o 4 si se usa el
  cielo como blanco). El GDD presupuestaba 37 + 3: son **+6 tiles** (puntuación de la fuente ya
  existente + `BLANK` + `ICON_TIMES`). Total zona BG en juego: 41 + 5 + tileset 89 = 135 → 7 tiles
  en la zona compartida (el GDD ya contaba con 1; quedan ~100 libres allí).
- **Grupos SCREEN + LOGO (62 tiles)** solo se usan en TITLE / CLEAR / GAMEOVER, que se dibujan con
  LCD apagado: cárguelos **encima del tileset del nivel** (el nivel no está en pantalla y INTRO
  vuelve a cargar el tileset con LCD apagado). No cuentan para el presupuesto de juego.
- Las runs `FRAME_*` y `LOGO_*` son consecutivas: el código puede usar `UI_LOGO_00 + n`.

---

## 1. Registros, capas y fundidos (común)

### 1.1 Mapas
- BG map `$9800` (LCDC bit 3 = 0), window map `$9C00` (LCDC bit 6 = 1). Dirección de un tile:
  `base + fila*32 + col`.
- TITLE, CLEAR, GAMEOVER: todo en el **BG** (`$9800`), `SCX = SCY = 0`, ventana apagada, sprites
  apagados (LCDC bit 1 = 0).
- INTRO, PLAY, PAUSE, DYING, GOAL: nivel en BG filas 0-15, HUD (e INTRO) en la **ventana**.

### 1.2 Paleta y fundidos (blanco)
- Normal: `BGP = 0xE4`, OBP0/OBP1 los que decida el arte (GDD: OBP1 = armadura encantada).
- Función de fundido: a cada campo de 2 bits `c` de la paleta se le aplica `max(c - k, 0)`.
  Para `0xE4`: k=0 `0xE4`, k=1 `0x90`, k=2 `0x40`, k=3 `0x00`. Precalcular la tabla de 4 valores
  para BGP, OBP0 y OBP1 (para OBP con color 0 transparente da igual el campo 0).
- **Fundido de salida (16 f):** escribir k = 1, 2, 3, 3 en los frames 0, 4, 8, 12 (cada valor dura
  4 f; el último paso es blanco sostenido). **Fundido de entrada (16 f):** k = 3, 2, 1, 0 en los
  frames 0, 4, 8, 12. Los registros se escriben al principio de `draw_vram()` (VBlank).
- Durante los fundidos no se lee el mando (salvo lo indicado en cada pantalla) y la lógica de juego
  está congelada.

### 1.3 Redibujado con LCD apagado (patrón único)
Fundido de salida hasta blanco → en el frame siguiente: `DISPLAY_OFF` (GBDK espera a VBlank: nunca
apagar fuera de VBlank) → cargar tiles y mapas → registros (SCX/SCY/WX/WY/LCDC/LYC) → `BGP = 0x00`,
`OBP* = 0x00` → `DISPLAY_ON` → `skip_measure = 1` en ese frame → fundido de entrada.
Puntos de redibujado: BOOT→TITLE, TITLE→INTRO, (DYING→INTRO), DYING→GAMEOVER, GOAL→CLEAR,
CLEAR→TITLE (M2: CLEAR→INTRO), GAMEOVER→TITLE. INTRO→PLAY **no** apaga el LCD (§3).

### 1.4 Presupuesto de tiles por frame fuera de los redibujados
| Situación | Tiles en ese frame |
|---|---|
| TITLE, parpadeo de "PULSA START" | 11 (cada 30 f; cada 4 f tras pulsar Start) |
| PLAY, peor caso HUD | **14** (puntos 6 + monedas 2 + vidas 2 + tiempo 3 + icono reloj 1) |
| GOAL, cuenta de tiempo | 9 por frame (tiempo 3 + puntos 6) |
| Entrar / salir de PAUSE | 20 (fila 0 del HUD; ese frame no hay streaming ni cola de metatiles) |
| PAUSE, parpadeo "PAUSA" | 5 (cada 30 f) |
| CLEAR, parpadeo "NUEVO RECORD!" | 13 (cada 30 f) |

Todo se compone en buffers en `update()` y solo se copia en `draw_vram()`.

---

## 2. HUD (ventana, 2 filas arriba)

Maqueta: `screens/play_hud.screen`.

```
col  01234567890123456789
r0   .PUNTOS...ox00..1-1.     o = ICON_COIN, x = ICON_TIMES
r1   .000000...vx03.t300.     v = ICON_HEAD, t = ICON_TIME
```

| Elemento | Fila | Columnas | Dirección window | Formato |
|---|---|---|---|---|
| "PUNTOS" | 0 | 1-6 | `$9C01-$9C06` | fijo |
| `ICON_COIN`, `ICON_TIMES` | 0 | 10, 11 | `$9C0A-$9C0B` | fijo |
| monedas | 0 | 12-13 | `$9C0C-$9C0D` | 2 dígitos con cero (00-99) |
| mundo "1-1" | 0 | 16-18 | `$9C10-$9C12` | dígito, `DASH`, dígito; cambia solo en INTRO |
| puntos | 1 | 1-6 | `$9C21-$9C26` | 6 dígitos con ceros (BCD, tope 999999) |
| `ICON_HEAD`, `ICON_TIMES` | 1 | 10, 11 | `$9C2A-$9C2B` | fijo |
| vidas | 1 | 12-13 | `$9C2C-$9C2D` | 2 dígitos con cero (01-99) |
| `ICON_TIME` | 1 | 15 | `$9C2F` | fijo (parpadea con poco tiempo, ver abajo) |
| tiempo | 1 | 16-18 | `$9C30-$9C32` | 3 dígitos con ceros (300 … 099 … 000) |

Resto de celdas de las filas 0-1: `BLANK`. Columna 0 y 19 vacías (margen).

**Hardware (GDD §5, con dos detalles añadidos):**
- `WX = 7`, `WY = 0`. Ventana visible en las líneas 0-15 (filas 0-1 del mapa de ventana).
- `LYC = 15`, interrupción STAT por LYC. La ISR espera a modo 0 (`(STAT & 3) == 0`) de la línea 15 y
  en **una sola escritura** hace `LCDC = (LCDC & ~0x20) | 0x02`: ventana fuera **y sprites dentro**.
  En VBlank (inicio de `draw_vram()`): `LCDC = (LCDC | 0x20) & ~0x02`.
  *Propuesta UI:* con los sprites apagados en las líneas 0-15, Teo (o un ítem/trozo) que salte por
  encima de la fila 0 del nivel queda recortado limpiamente en la línea 16 en vez de pintarse sobre
  el HUD. Coste: 0 (misma escritura). Si el programador lo descarta, mantener solo el bit 5.
- `SCY = 0xF0`: las líneas 0-15 muestran las filas **30-31** del mapa BG detrás de la ventana.
  Rellenarlas con `BLANK` al cargar el nivel (el streaming solo escribe filas 0-15); así, si la ISR
  llega una línea tarde/temprano, lo que asoma es cielo blanco y no basura.
- Variable `hud_cut` (u8): 1 en PLAY/PAUSE/DYING/GOAL (la ISR corta), 0 en INTRO (ventana a pantalla
  completa; la ISR no toca nada). En TITLE/CLEAR/GAMEOVER la ventana está apagada y la ISR no hace nada.

**Actualización:** `hud_buf[2][20]` refleja las filas 0-1. Cuando cambia un valor, `update()`
escribe sus dígitos en `hud_buf` y marca el campo sucio (bits: SCORE, COINS, LIVES, TIME, TIMEICON,
ROW0_ALL). `draw_vram()` copia los campos sucios (máx. 14 tiles; ROW0_ALL = 20 solo en PAUSE).
- Tiempo: cambia cada 24 f → 3 tiles. Moneda: monedas 2 + puntos 6. 100 monedas: monedas 2 + vidas 2
  + puntos 6. Pisotón/bloque: puntos 6.
- **Poco tiempo (propuesta, complementa el aviso sonoro del GDD):** con `time_units <= 100`,
  `ICON_TIME` alterna `ICON_TIME`/`BLANK` cada **16 f** (1 tile). Se detiene (visible) en GOAL,
  DYING y PAUSE.

---

## 3. INTRO (tarjeta de nivel, 120 f)

Maqueta: `screens/intro.screen`. Todo en el **mapa de ventana** (`$9C00`), ventana a pantalla
completa (`WY = 0`, `hud_cut = 0`), sprites apagados.

| Elemento | Fila | Columnas | Texto |
|---|---|---|---|
| HUD filas 0-1 | 0-1 | §2 | valores actuales (puntos, monedas, vidas, tiempo 300 del nivel, mundo) |
| mundo | 6 | 5-13 | `MUNDO 1-1` (MUNDO 5-9, `1` 11, `DASH` 12, `1` 13) |
| nombre del nivel | 8 | `(20 - len) / 2` | `PRADERA` (col 6), `MAZMORRA` (col 6), `ALMENAS` (col 6), `TORRE` (col 7) |
| vidas | 11 | 7, 9, 11-12 | `ICON_HEAD` col 7, `ICON_TIMES` col 9, 2 dígitos cols 11-12 |
| resto filas 2-17 | | | `BLANK` |

Secuencia (frames desde que entra en INTRO):
1. f0: LCD apagado (`skip_measure`): carga tileset del nivel, `level[]`, columnas BG 0-21 filas
   0-15, filas BG 30-31 a `BLANK`, mapa de ventana filas 0-17 (HUD + tarjeta). `SCX = 0`,
   `SCY = 0xF0`, `WX = 7`, `WY = 0`, `hud_cut = 0`, LCDC: BG on, ventana on, OBJ off. `BGP = 0`.
2. f1-16: fundido de entrada. f17-103: espera. f104-119: fundido de salida. (Total 120 f.)
3. Con la pantalla en blanco: `hud_cut = 1`, colocar los sprites del jugador, OBJ los activa la ISR.
   **No se apaga el LCD:** el nivel ya está en el BG, la tarjeta de las filas 2-17 del mapa de
   ventana queda oculta porque la ventana se corta en la línea 15.
4. Fundido de entrada de 16 f con la lógica congelada → estado PLAY (empieza a correr el tiempo).
- Botones: ninguno (Start no salta la tarjeta).

---

## 4. PLAY

Maqueta: `screens/play_hud.screen` (filas 2-17 en blanco; el nivel lo dibuja el pixel-artist en
`art_*.screen`). HUD según §2. Fila de pantalla `r` (2-17) = fila `r-2` del nivel.
- Botones (GDD §3): Izq/Der mover, Abajo agacharse, A saltar, B correr/disparar, **Start = pausa**
  (solo en PLAY, no durante GOAL, DYING ni fundidos), Select nada.
- Sprites en las líneas 0-15: ninguno visible (recorte por LCDC bit 1, §2).

## 5. PAUSE

Maqueta: `screens/pause.screen`.
- Al pulsar Start en PLAY: SFX de pausa; el mismo frame se reescribe la **fila 0 del HUD entera**
  (20 tiles): todo `BLANK` salvo `PAUSA` en las columnas **7-11**. La fila 1 no cambia.
- `PAUSA` parpadea **30 f visible / 30 f oculto** (5 tiles por cambio), empezando visible.
- El nivel y los sprites quedan congelados y visibles; la paleta no cambia; el tiempo no corre.
- Start otra vez: se restaura la fila 0 desde `hud_buf` (20 tiles) en ese frame, todavía en PAUSE;
  la lógica de PLAY se reanuda en el frame siguiente. A, B, Select, cruceta: ignorados.

## 6. DYING (sin pantalla propia)

Es la pantalla de juego con la animación de muerte del GDD §2.11; el HUD sigue visible y quieto
(el icono de reloj deja de parpadear). Al terminar (animación ~90 f, o 60 f tras caer a un hoyo):
fundido de salida 16 f → LCD apagado → INTRO (con vidas ya descontadas) o GAMEOVER si `lives == 0`.
Sin botones.

## 7. GOAL (cuenta de tiempo en el HUD)

Sin pantalla propia: es PLAY con control bloqueado (GDD §2.11). Durante el paso 4 (cuenta), cada
frame: `time_units -= 1`, puntos `+= 50` → HUD tiempo (3) + puntos (6) = **9 tiles/frame**. Tic de
sonido cada 4 f. Al llegar a 000: espera 60 f → fundido de salida → LCD apagado → CLEAR. Sin botones.

---

## 8. TITLE

Maqueta: `screens/title.screen`. BG `$9800`, `SCX = SCY = 0`, ventana y sprites apagados.

| Elemento | Fila | Columnas | Contenido |
|---|---|---|---|
| logo | 2-4 | 1-18 | tabla de abajo (`LOGO_nn`, `--` = `BLANK`) |
| espada | 5 | 1 / 2 / 3-17 / 18 | `SWORD_HILT` / `SWORD_GUARD` / `SWORD_BLADE` x15 / `SWORD_TIP` |
| "PULSA START" | 10 | 4-14 | parpadea |
| "RECORD 000000" | 12 | 3-15 | "RECORD" 3-8, récord 6 dígitos 10-15 |
| muralla | 15 / 16-17 | 0-19 | `WALL_TOP` / `WALL_BRICK` |
| resto | | | `BLANK` |

Logo (índice n de `LOGO_nn`; columnas 1 a 18):
```
fila 2: -- 00 01 02 03 04 05 06 07 08 -- 09 10 11 12 13 14 15 16 --
fila 3: -- 17 18 19 20 21 22 23 17 24 -- 25 26 27 28 29 30 31 31 --
fila 4: -- 32 33 34 35 36 37 37 38 39 40 38 41 42 43 44 45 46 47 --
```
(la primera y última entrada son las columnas 0 y 19; dibujadas: x 8-151 px, y 17-38 px.)

- **M1 sin logo** (GDD: logo en M2): poner `CABALLERITO` con la fuente en la fila 3, columnas 4-14;
  el resto igual (espada y muralla son 6 tiles, se pueden usar ya en M1).
- Parpadeo: "PULSA START" **30 f visible / 30 f oculto** (11 tiles por cambio), empieza visible.
- **Start o A**: SFX; el texto parpadea rápido **4 f / 4 f durante 32 f** (feedback), luego fundido
  de salida 16 f → LCD apagado → INTRO del 1-1 (puntos 0, monedas 0, vidas 3). Select y el resto:
  nada. Ignorar Start durante el fundido de entrada.
- Entrada: desde BOOT (LCD apagado, cargar fuente + grupos HUD/SCREEN/LOGO) con fundido de entrada.
- Opcional (en la maqueta): Teo SMALL `TEO_SMALL_IDLE` de `spr.tiles` (2 sprites 8x16: tile N en
  x = 24, tile N+2 en x = 32; y = 105 px de pantalla, pies en la línea 120 sobre las almenas). Si se
  usa, en TITLE se activan los sprites (OBJ on, OBP0 en el fundido). 2 sprites por línea.

## 9. CLEAR (nivel completado)

Maqueta: `screens/clear.screen`. BG `$9800`, `SCX = SCY = 0`, ventana y sprites apagados.

| Elemento | Fila | Columnas | Contenido |
|---|---|---|---|
| marco | 2-13 | 1-18 | `FRAME_TL` (2,1), `FRAME_T` (2, 2-17), `FRAME_TR` (2,18), `FRAME_L` (3-12, 1), `FRAME_R` (3-12, 18), `FRAME_BL` (13,1), `FRAME_B` (13, 2-17), `FRAME_BR` (13,18) |
| "NIVEL COMPLETADO" | 4 | 2-17 | fijo |
| "MUNDO 1-1" | 6 | 6-14 | número del nivel terminado |
| "PUNTOS" + puntos | 8 | 3-8 / 11-16 | puntuación final (con bonus de tiempo y asta ya sumados) |
| "RECORD" + récord | 10 | 3-8 / 11-16 | récord **ya actualizado** |
| "NUEVO RECORD!" | 12 | 4-16 | solo si la puntuación superó el récord anterior; parpadea 30/30 f (13 tiles) |
| muralla | 15 / 16-17 | 0-19 | `WALL_TOP` / `WALL_BRICK` |

- Duración: 180 f, o Start/A a partir del frame 30 (para que una pulsación previa no la salte) →
  fundido de salida → M1: TITLE (récord actualizado); M2: INTRO del nivel siguiente (tras el 1-4,
  TITLE).

## 10. GAMEOVER

Maqueta: `screens/gameover.screen`. BG `$9800`, `SCX = SCY = 0`, ventana y sprites apagados.

| Elemento | Fila | Columnas | Contenido |
|---|---|---|---|
| marco | 5-12 | 1-18 | igual que CLEAR: esquinas (5,1) (5,18) (12,1) (12,18), lados filas 6-11 |
| "FIN DEL JUEGO" | 7 | 3-15 | fijo |
| "PUNTOS" + puntos | 10 | 3-8 / 11-16 | puntuación final |
| muralla | 15 / 16-17 | 0-19 | `WALL_TOP` / `WALL_BRICK` |

- Duración: 180 f, o Start/A a partir del frame 30 → fundido de salida → TITLE.
- Propuesta: actualizar también aquí el récord (ver preguntas abiertas).

---

## 11. Botones por pantalla

| Pantalla | Start | A | B | Select | Cruceta |
|---|---|---|---|---|---|
| TITLE | empezar | empezar | — | — | — |
| INTRO | — | — | — | — | — |
| PLAY | pausa | saltar | correr / disparar | — | mover / agacharse |
| PAUSE | reanudar | — | — | — | — |
| DYING, GOAL | — | — | — | — | — |
| CLEAR, GAMEOVER | saltar espera (desde f30) | igual que Start | — | — | — |

Flancos de pulsación (no niveles) para Start y A en pantallas.

## 12. Cadenas exactas

| Cadena | Tiles | Dónde |
|---|---|---|
| `PULSA START` | 11 | TITLE fila 10 col 4 |
| `RECORD` | 6 | TITLE fila 12 col 3; CLEAR fila 10 col 3 |
| `PUNTOS` | 6 | HUD (0,1); CLEAR fila 8 col 3; GAMEOVER fila 10 col 3 |
| `MUNDO 1-1` | 9 | INTRO fila 6 col 5; CLEAR fila 6 col 6 |
| `PRADERA` / `MAZMORRA` / `ALMENAS` / `TORRE` | 7/8/7/5 | INTRO fila 8 |
| `PAUSA` | 5 | HUD fila 0 col 7 |
| `NIVEL COMPLETADO` | 16 | CLEAR fila 4 col 2 |
| `NUEVO RECORD!` | 13 | CLEAR fila 12 col 4 (`!` = `EXCLAM`) |
| `FIN DEL JUEGO` | 13 | GAMEOVER fila 7 col 3 |
| `CABALLERITO` (M1 sin logo) | 11 | TITLE fila 3 col 4 |

## 13. Comprobaciones (checklist)
- Legibilidad: texto negro sobre blanco; iconos con contorno negro, nada importante en gris claro
  sobre blanco (la moneda es gris claro **dentro** de contorno negro).
- HUD fuera de la acción (líneas 0-15, el nivel empieza en la 16); números alineados a la derecha
  con ceros; "1-1" alineado encima del tiempo (cols 16-18).
- Sprites por línea: ninguna pantalla de UI usa sprites (Teo opcional en TITLE: 2).
- Cambios de pantalla completa siempre con LCD apagado y `skip_measure`; en juego ≤ 14 tiles de HUD.
- Test sugerido: leer `$9C00-$9C33` en PLAY y comparar con `score`/`coins`/`lives`/`time_units`.
