# GRIFO - UI spec (para el programador)

Autor: ui-designer · 2026-10-14 · Fuente: `design/gdd.md` v1.0 (§3, §4, §5, §12).
Maquetas: `design/screens/*.screen` → `python harness/gb.py preview shmup` →
`build/preview/screen_*.png`. Coordenadas en **(fila, columna) de tiles 8x8**, fila 0-17,
columna 0-19, salvo que diga "px". Mismo lenguaje visual que CABALLERITO (cajas con marco doble
sobre la muralla, logo de tiles con sombra, espada bajo el logo, HUD arriba sin línea separadora).

Textos: español, mayúsculas, sin tildes ni Ñ. Fuente compartida `harness/common/font.tiles`
(DIGIT0..9, LETTER_A..Z, DASH, EXCLAM, DOT, COLON, QUESTION): no hace falta añadir nada.

---

## 0. Tiles y VRAM

### 0.1 Ficheros (dos, para que la VRAM cuadre)
`res/ui.tiles` (24 tiles, **residentes en juego**):

| Índice | Etiqueta | Uso |
|---|---|---|
| 0 | `BLANK` | blanco; **es el tile 0 de VRAM**, así que limpiar un mapa con 0 = blanco |
| 1 | `ICON_LIFE` | vidas: casco del caballero con penacho (el mismo de CABALLERITO) |
| 2 | `ICON_BOMB` | bombas: cuerno de guerra (como el ítem B), campana oscura arriba a la derecha |
| 3 | `ICON_POWER` | nivel de arma: pluma de fuego (como el ítem P) |
| 4 | `ICON_BOSS` | cabeza de dragón de frente (simétrica): flanquea "PELIGRO" |
| 5-13 | `BAR_0 .. BAR_8` | barra del jefe: tubo negro (filas 1 y 6) con `n` px rellenos (gris oscuro, filas 2-5) desde la izquierda. Run consecutiva: `UI_BAR_0 + n` |
| 14 | `BAR_CAP_L` | extremo izquierdo de la barra (línea en el px 7) |
| 15 | `BAR_CAP_R` | extremo derecho de la barra (línea en el px 0) |
| 16-23 | `FRAME_TL, FRAME_T, FRAME_TR, FRAME_L, FRAME_R, FRAME_BL, FRAME_B, FRAME_BR` | marco de caja (CONTINUAR en juego; CLEAR, GAMEOVER) |

`res/uiscreens.tiles` (43 tiles, **solo TITLE / CLEAR / GAMEOVER**, cargados con el LCD apagado):

| Índice | Etiqueta | Uso |
|---|---|---|
| 0 | `ICON_TIMES` | signo "x" de multiplicar sobre la línea base de la fuente (CLEAR) |
| 1-2 | `WALL_TOP, WALL_BRICK` | muralla con almenas (TITLE, CLEAR, GAMEOVER) |
| 3-6 | `SWORD_HILT, SWORD_GUARD, SWORD_BLADE, SWORD_TIP` | espada bajo el logo (TITLE) |
| 7-8 | `CLOUD_L, CLOUD_R` | nubecita del cielo del título (decorativa, gris) |
| 9-42 | `LOGO_00 .. LOGO_33` | logo GRIFO, 3 filas x 14 columnas (run consecutiva) |

### 0.2 Distribución de tiles de BG (LCDC bit 4 = 0, GDD §7.2)
El mismo orden en juego y en pantallas, para que los índices de la fuente y del HUD no cambien:

| Tiles BG | En juego (PLAY/PAUSE/CONTINUAR) | En TITLE / CLEAR / GAMEOVER |
|---|---|---|
| 0-23 | `ui` | `ui` |
| 24-64 | `font` (DIGIT0 = 24, LETTER_A = 34, DASH 60, EXCLAM 61, DOT 62, COLON 63, QUESTION 64) | `font` |
| 65-236 | `bg` (172 tiles hoy; caben hasta 191 → `BG_BASE = 65`) | `uiscreens` en 65-107 (sobre los slots del bg) |

- **Los índices de `bg` llevan `+65`** en `mt_tiles`, `row_buf`, NIEBLA, etc. (`BG_BASE`). Es el
  precio de que el tile 0 sea blanco y de poder convertir las pantallas con `screens.py`
  (un solo `vram_order`). Con `bg` en 0 el logo y la muralla no cabrían en ninguna parte.
- Al volver de TITLE/CLEAR/GAMEOVER a PLAY la carga con LCD apagado reescribe el `bg` (65-236).
- Índices ≥ 128 van a `$8800-$8FFF` (los sprites usan 0-127 en `$8000`), como dice el GDD.

### 0.3 Pantallas convertibles con `harness/screens.py`
`game.json`:
```json
"screens": ["title", "continuar", "clear", "gameover"],
"vram_order": ["ui", "font", "uiscreens"]
```
- `title`, `clear`, `gameover`: mapa de 18x20 completo para el BG `$9800` (LCD apagado).
- `continuar`: mapa para la **ventana** `$9C00`; usar las filas 1-17 (la fila 0 es el HUD vivo,
  sale de `hud_buf`). Solo usa tiles residentes (máx. índice 64).
- No convertir `play_hud`, `play_boss`, `pause`, `msg_fase`, `msg_peligro`: solo importa su fila 0
  (20 bytes), mejor como tablas de 20 bytes en el código (§2.4). Ahorra 5 x 360 B de ROM.
- `screen_title_spr` trae 4 entradas 8x8 del grifo (tiles `PLAYER`..`PLAYER+3`, sin offset);
  en modo 8x16 usar solo las de tile par (0 y 2): `PLAYER` en x 72, `PLAYER+2` en x 80, y 56 px de
  pantalla (OAM: +8, +16). Si el pixel-artist renombra `PLAYER`, hay que cambiar `title.screen`.

---

## 1. Registros, capas y fundidos (común)

### 1.1 Mapas y capas
- BG map `$9800` (anillo de 32 filas del scroll), window map `$9C00` (LCDC bit 6 = 1),
  dirección = `base + fila*32 + col`. Sprites 8x16 (LCDC bit 2 = 1).
- TITLE, CLEAR, GAMEOVER: todo en el **BG**, `SCX = SCY = 0` (`scx_shadow`, `scy_shadow`), ventana
  apagada, `hud_cut = 0`. Sprites: solo TITLE (el grifo); CLEAR/GAMEOVER OBJ off.
- PLAY, PAUSE: fase en el BG, HUD en la fila 0 de la ventana (§2), `hud_cut = 1`.
- CONTINUAR: ventana a pantalla completa (`hud_cut = 0`, `WY = 0`), OBJ off; el BG no se toca.

### 1.2 Paletas y fundidos (a blanco)
- Normal: `video_init(7, 0xE4, 0xE4, 0xD8)` → BGP `0xE4`, OBP0 `0xE4`, OBP1 `0xD8` (destello).
- `set_fade(k)` (gbe_video) ya hace `max(c - k, 0)` por campo: BGP k=0..3 = `0xE4, 0x90, 0x40,
  0x00`; OBP1 `0xD8, 0x84, 0x40, 0x00`.
- **Fundido de salida (16 f):** k = 1, 2, 3, 3 en los frames 0, 4, 8, 12. **De entrada (16 f):**
  k = 3, 2, 1, 0 en los frames 0, 4, 8, 12 (`gbe_screen`). La lógica está congelada y el mando se
  ignora durante los fundidos.
- El rugido (bomba) hace `set_fade(1)` 4 f: el HUD también se aclara (aceptado en el GDD).

### 1.3 Redibujado con LCD apagado (patrón único)
Fundido de salida → `DISPLAY_OFF` (en VBlank) → cargar tiles/mapas → registros (SCX/SCY/WX/WY/LCDC,
`hud_cut`) → `set_fade(3)` → `DISPLAY_ON` → `skip_measure = 1` ese frame → fundido de entrada.
Puntos: BOOT→TITLE, TITLE→PLAY, PLAY→CLEAR, PLAY/CONTINUAR→GAMEOVER, CLEAR→TITLE,
GAMEOVER→TITLE. **Sin LCD apagado:** PLAY→CONTINUAR→PLAY (§5) y PLAY↔PAUSE.

### 1.4 Tiles escritos por frame fuera de los redibujados
| Situación | Tiles en ese frame |
|---|---|
| PLAY, HUD peor caso | **12** (puntos 6 + vidas 1 + bombas 1 + arma 1 + barra 3) |
| PLAY, poner/quitar un aviso (FASE 1, PELIGRO, restaurar) | **20** (fila entera; ese frame ningún otro campo del HUD) |
| PELIGRO parpadeando | 11 cada 30 f |
| Entrar / salir de PAUSE | 20; "PAUSA" parpadeando: 5 cada 30 f |
| Barra del jefe al aparecer | 5 (tapas + 3) el primer frame, luego ≤ 3/f |
| CONTINUAR | cuenta 1 cada 60 f; "PULSA START" 11 cada 30 f |
| TITLE "PULSA START" | 11 cada 30 f (cada 4 f tras pulsar) |
| CLEAR, cuenta de bonos | ≤ 12/f (TOTAL 6 + bono 5 + dígito de bombas 1); al acabar RECORD 6 |
| CLEAR / GAMEOVER "NUEVO RECORD!" | 13 cada 30 f |

Todo se compone en buffers en `update()` y `draw_vram()` solo copia (GDD §9.2: HUD ≤ 20).

---

## 2. HUD (ventana, 1 fila arriba)

Maquetas: `screens/play_hud.screen`, `screens/play_boss.screen`.

```
col  01234567890123456789
r0   000000.v3.b2.p1.....      normal          v ICON_LIFE  b ICON_BOMB  p ICON_POWER
r0   045670.v2.b1.p3<##.>      con jefe        < BAR_CAP_L  # BAR_n x3  > BAR_CAP_R
```

| Elemento | Col | Dirección | Formato |
|---|---|---|---|
| puntos | 0-5 | `$9C00-$9C05` | 6 dígitos BCD **con ceros** (tope 999999); tile = 24 + dígito |
| `ICON_LIFE` | 7 | `$9C07` | fijo |
| vidas | 8 | `$9C08` | 1 dígito 0-9 |
| `ICON_BOMB` | 10 | `$9C0A` | fijo |
| bombas | 11 | `$9C0B` | 1 dígito 0-4 |
| `ICON_POWER` | 13 | `$9C0D` | fijo |
| arma | 14 | `$9C0E` | 1 dígito 1-3 |
| barra del jefe | 15-19 | `$9C0F-$9C13` | solo en BOSS / BOSS_DEAD; si no, `BLANK` |
| huecos | 6, 9, 12 | | `BLANK` |

Prioridad: caben **todos** los contadores del GDD (puntos, vidas, bombas, arma) y la barra, sin
recortar nada. Cols 15-19 quedan libres fuera del jefe (sitio para un aviso futuro).

### 2.1 Hardware: ventana y corte LYC
- `WX = 7`, `WY = 0`, ventana encendida en VBlank. `video_init(7, …)`: **LYC = 7**. La ISR espera
  al HBlank de la línea 7 y, en una sola escritura, apaga la ventana y enciende los sprites; la ISR
  de VBlank los vuelve a poner (ventana on, OBJ off). Ya lo hace `gbe_video` con `hud_cut = 1`.
- Resultado: líneas 0-7 = fila 0 de la ventana (HUD); líneas 8-143 = BG (136 px de juego). Los
  sprites no se dibujan en 0-7: los enemigos que aparecen con pantalla y −16..−1 salen de debajo del
  HUD sin pintarse encima.
- **Qué hay detrás del HUD:** las líneas 0-7 del BG son las líneas `SCY .. SCY+7` del anillo, es
  decir la fila de tiles que está entrando por arriba (la que el streaming acaba de escribir). Queda
  tapada por la ventana; por eso el streaming puede escribir esa fila sin que se vea. La primera línea
  de juego visible (pantalla y = 8) es la línea `(SCY + 8) & 255` del BG.
- Si la ISR llegara una línea tarde, la línea 8 mostraría la fila 1 de la ventana: debe ser blanca.
  Las filas 1-2 de la ventana son `BLANK` también con el panel de CONTINUAR cargado (§5).
- El destello del jefe (`bgp_below`, GDD §2.10) cambia la paleta solo por debajo del corte: el HUD
  no destella.

### 2.2 Actualización
`hud_buf[20]` = fila 0 con los contadores. `update()` escribe los dígitos que cambian y marca campos
sucios: `SCORE` (6), `LIVES` (1), `BOMBS` (1), `POWER` (1), `BAR` (3, o 5 con las tapas), `ROW` (20).
`draw_vram()` copia solo lo sucio. Mientras haya un aviso (§2.4), `hud_buf` se sigue actualizando
pero no se copia; al quitarlo se copia la fila entera.

### 2.3 Barra del jefe
- 24 px en las cols 16-18, cerrada por `BAR_CAP_L` (col 15) y `BAR_CAP_R` (col 19).
- `px = (boss_hp * 31) >> 8` (200 → 24); si `boss_hp > 0` y `px == 0`, `px = 1` (nunca vacía con el
  jefe vivo). Tile de la col `16 + i` (i = 0..2): `UI_BAR_0 + clamp(px − 8·i, 0, 8)`.
- Aparece al pasar a `play_sub = BOSS` (scroll parado): tapas + 3 tiles. **Propuesta:** se llena de
  0 a 24 px a 1 px/f (24 f, ≤ 1 tile/f) mientras el jefe entra en su vaivén; después sigue a
  `boss_hp`. Solo se reescriben los tiles cuyo valor cambia.
- En BOSS_DEAD se queda vacía (`BAR_0` x3). Al empezar OUTRO: cols 15-19 a `BLANK` (5 tiles).
- Este cambio de GDD §5 (4 tiles/32 px sin tapas → 3 tiles/24 px con tapas) se ve mucho mejor: un
  tubo cerrado se lee como barra de vida; abierto contra el borde de la pantalla no.

### 2.4 Avisos en la fila del HUD (sustituyen la fila entera, 20 tiles)
| Aviso | Fila 0 (20 tiles) | Cuándo | Parpadeo | Maqueta |
|---|---|---|---|---|
| `FASE 1` | `BLANK` x7, `FASE` (7-10), `BLANK`, `1` (12), `BLANK` x7 | desde el frame 0 de PLAY (ya escrito al construir con LCD apagado) durante 120 f | no | `msg_fase.screen` |
| `PELIGRO` | `ICON_BOSS` (4), `PELIGRO` (6-12), `ICON_BOSS` (14), resto `BLANK` | cuando la fila 180 del mapa entra por arriba, 180 f | **30 f visible / 30 f oculto** (oculto = 20 `BLANK`), empieza visible; 3 ciclos | `msg_peligro.screen` |
| `PAUSA` | `PAUSA` (7-11), resto `BLANK` | mientras dura la pausa | 30/30 f, empieza visible | `pause.screen` |

- Prioridad: PAUSA > PELIGRO > FASE 1 > contadores. Si se pausa durante un aviso, su temporizador se
  congela; al reanudar se redibuja el aviso (20 tiles) y sigue donde iba.
- Al acabar un aviso: copiar `hud_buf` entero (20 tiles) ese frame.
- El cambio entre visible y oculto de PELIGRO toca solo las cols 4-14 (11 tiles); de PAUSA, 7-11 (5).

---

## 3. PLAY

Maqueta: `screens/play_hud.screen` (filas 1-17 en blanco; la fase la dibuja el pixel-artist en
`art_*.screen`). Construcción (TITLE→PLAY, LCD apagado): tiles §0.2, 18 filas del mapa, columnas
20-31 a NIEBLA, ventana fila 0 = aviso FASE 1, **ventana filas 1-17 = panel de CONTINUAR**
(`screen_continuar_map` filas 1-17, oculto por el corte; ver §5), `hud_cut = 1`, `WX = 7`,
`WY = 0`. Fundido de entrada.
- Botones (GDD §3): cruceta mover, A mantenido autodisparo, B bomba (flanco), **Start pausa**,
  Select nada.
- Sprites en líneas 0-7: ninguno (corte LYC). Peor caso por línea: GDD §7.3 (la UI no añade sprites).

## 4. PAUSE

Maqueta: `screens/pause.screen`.
- Start (flanco) en PLAY con `play_sub` NORMAL, RESPAWN, BOSS_INTRO o BOSS (no en DYING, BOSS_DEAD,
  OUTRO ni durante fundidos): SFX `PAUSE`, después sonido silenciado; ese frame la fila 0 pasa a
  PAUSA (20 tiles). Todo congelado y visible (paleta normal, sprites quietos, scroll parado).
- Start otra vez: se restaura la fila (contadores o el aviso activo, 20 tiles) en ese frame, todavía
  en PAUSE; la lógica se reanuda en el frame siguiente. A, B, Select, cruceta: ignorados.

## 5. CONTINUAR

Maqueta: `screens/continuar.screen`. Todo en la **ventana**, que pasa a pantalla completa; la fase
sigue intacta en el BG (y su estado en WRAM), así que no hay que reconstruir nada para continuar.

| Elemento | Fila | Columnas | Dirección | Contenido |
|---|---|---|---|---|
| HUD | 0 | 0-19 | `$9C00` | `hud_buf` (vidas 0) |
| marco | 3-14 | 1-18 | | `FRAME_TL` (3,1) … `FRAME_BR` (14,18) |
| `CONTINUAR?` | 5 | 5-14 | `$9CA5` | fijo (`?` = `QUESTION`) |
| caja de la cuenta | 7-9 | 8-10 | | marco 3x3 con `FRAME_*` |
| cuenta | 8 | 9 | `$9D09` | dígito 9 → 0 |
| `QUEDAN n` | 11 | 6-13 | `$9D66`; dígito `$9D6D` | n = continuaciones que quedan (3, 2, 1) |
| `PULSA START` | 13 | 4-14 | `$9DA4` | parpadea 30/30 f |

Secuencia:
1. Fin de la animación de muerte con `lives == 0`: si `continues == 0` → GAMEOVER directamente.
2. `hiscore = max(hiscore, score)` **ya aquí** (continuar pone la puntuación a 0) y anotar
   `new_record` si se superó.
3. Fundido de salida 16 f. Con la pantalla en blanco: dígito de la cuenta = 9, dígito de QUEDAN,
   `PULSA START` visible (3 cosas, ≤ 13 tiles), `hud_cut = 0`, LCDC: ventana on, OBJ off. **Sin LCD
   apagado** (el panel ya está en las filas 1-17 desde que se construyó PLAY).
4. Fundido de entrada 16 f. La cuenta: cada 60 f el dígito baja 1 (1 tile) con SFX `TICK`; el 9 y
   el 0 también duran 60 f (10 s en total). Al acabar el 0 → fundido de salida → LCD apagado →
   GAMEOVER.
5. **Start** (flanco) a partir del frame 30 tras el fundido de entrada: SFX `START`,
   `continues − 1`, `score = 0`, `lives = 3`, `power = 1`, `bombs = 2`, borrar balas;
   fundido de salida; con la pantalla en blanco `hud_cut = 1` y copiar `hud_buf` (20 tiles);
   fundido de entrada; `play_sub = RESPAWN`.
- **A no hace nada** aquí (el jugador suele venir con A mantenido del autodisparo: no debe gastar una
  continuación sin querer). B, Select, cruceta: nada.

## 6. GAMEOVER

Maqueta: `screens/gameover.screen`. BG `$9800`, LCD apagado, `uiscreens` cargado.

| Elemento | Fila | Columnas | Contenido |
|---|---|---|---|
| marco | 3-13 | 1-18 | esquinas (3,1) (3,18) (13,1) (13,18) |
| `FIN DEL JUEGO` | 5 | 3-15 | fijo |
| `PUNTOS` + puntos | 7 | 3-8 / 11-16 | puntuación de la última partida |
| `RECORD` + récord | 9 | 3-8 / 11-16 | récord **ya actualizado** (también se actualiza aquí) |
| `NUEVO RECORD!` | 11 | 3-15 | solo si `new_record` (se batió en esta partida, en cualquier tramo); parpadea 30/30 f; si no, `BLANK` |
| muralla | 15 / 16-17 | 0-19 | `WALL_TOP` / `WALL_BRICK` |

- 180 f, o Start/A a partir del frame 30 → fundido de salida → LCD apagado → TITLE.

## 7. CLEAR (fase completada)

Maqueta: `screens/clear.screen`. BG `$9800`, LCD apagado, `uiscreens` cargado. Caja a todo el ancho
(cols 0-19) para centrar las líneas de 15 caracteres.

| Elemento | Fila | Columnas | Contenido |
|---|---|---|---|
| marco | 0-14 | 0-19 | esquinas (0,0) (0,19) (14,0) (14,19) |
| `FASE COMPLETADA` | 2 | 2-16 | fijo |
| `BOMBAS n x 2000` | 4 | 2-7 / 9 / 11 / 13-16 | `n` = bombas restantes (col 9); `ICON_TIMES` col 11; `2000` fijo |
| `SIN MORIR` + bono | 6 | 2-10 / 12-16 | `10000`, o `00000` si murió en la fase |
| `TOTAL` + puntos | 8 | 2-6 / 11-16 | puntuación (sube con la cuenta) |
| `RECORD` + récord | 10 | 2-7 / 11-16 | récord anterior; se actualiza al acabar la cuenta |
| `NUEVO RECORD!` | 12 | 3-15 | solo si se bate; parpadea 30/30 f |
| muralla | 15 / 16-17 | 0-19 | `WALL_TOP` / `WALL_BRICK` |

Cuenta animada (GDD §4: +100/f, tic cada 4 f), desde el frame 30 tras el fundido de entrada:
1. Bombas: cada frame `score += 100`; cada 20 f (= 2000) `n − 1` (1 tile). Hasta `n = 0`.
2. Sin morir: cada frame bono `− 100` (5 tiles) y `score += 100`, hasta `00000` (100 f).
3. SFX `TICK` cada 4 f mientras cuenta. `score` se satura en 999999.
4. Al acabar: si `score > hiscore` → `hiscore = score`, RECORD (6 tiles), `NUEVO RECORD!` parpadea.
- Start/A durante la cuenta: la termina de golpe (valores finales, ≤ 18 tiles ese frame).
- Duración: 300 f desde el final del fundido de entrada (la cuenta máxima son 80 + 100 f), o Start/A
  ≥ 30 f después de acabar la cuenta → fundido de salida → TITLE (M2: fase 2).

## 8. TITLE

Maqueta: `screens/title.screen`. BG `$9800`, LCD apagado, `uiscreens` cargado, ventana off.

| Elemento | Fila | Columnas | Contenido |
|---|---|---|---|
| logo | 2-4 | 3-16 | tabla de abajo |
| espada | 5 | 3 / 4 / 5-15 / 16 | `SWORD_HILT` / `SWORD_GUARD` / `SWORD_BLADE` x11 / `SWORD_TIP` |
| nubes | 7 / 8 | 2-3 / 15-16 | `CLOUD_L CLOUD_R` |
| grifo (sprites) | — | — | `PLAYER` 16x16 en x 72, y 56 px de pantalla (2 sprites 8x16, OBP0) |
| `PULSA START` | 10 | 4-14 | parpadea |
| `RECORD 000000` | 12 | 3-8 / 10-15 | récord (RAM en M1, SRAM en M2) |
| muralla | 15 / 16-17 | 0-19 | `WALL_TOP` / `WALL_BRICK` |

Logo (índice n de `LOGO_nn`, columnas 3 a 16; `--` = `BLANK`):
```
fila 2: 00 01 02 03 01 04 05 06 07 08 09 03 01 04
fila 3: 10 11 12 13 14 15 16 17 18 19 20 21 -- 21
fila 4: 22 23 24 25 26 27 28 29 30 31 -- 32 23 33
```
(Letras negras de trazo 5 px con sombra gris oscura de 1 px abajo/derecha, 22 px de alto.)

- **Logo de tiles ya en M1** (el GDD lo dejaba para M3; en CABALLERITO el usuario lo quiso en M1).
  Si falta ROM: `GRIFO` con la fuente en la fila 3, cols 7-11, y quitar los 34 `LOGO_*` (544 B).
- Parpadeo: `PULSA START` 30 f visible / 30 f oculto (11 tiles), empieza visible.
- **Propuesta:** el grifo sube y baja 1 px cada 16 f (y = 56, 55, 56, 57…) y alterna NORMAL/BANK
  si el pixel-artist añade un aleteo; coste 0 tiles. Sprites por línea: 2.
- **Start o A**: SFX `START`; el texto parpadea 4 f / 4 f durante 32 f, fundido de salida 16 f →
  LCD apagado → PLAY (puntos 0, vidas 3, bombas 2, arma 1, continuaciones 3, `new_record = 0`).
  Ignorar el mando durante el fundido de entrada.

---

## 9. Botones por pantalla

| Pantalla | Start | A | B | Select | Cruceta |
|---|---|---|---|---|---|
| TITLE | empezar | empezar | — | — | — |
| PLAY | pausa | autodisparo (mantener) | bomba | — | mover 8 dir. |
| PAUSE | reanudar | — | — | — | — |
| CONTINUAR | continuar (desde f30) | — (a propósito) | — | — | — |
| GAMEOVER | saltar espera (desde f30) | igual que Start | — | — | — |
| CLEAR | terminar cuenta / salir (§7) | igual que Start | — | — | — |

Flancos de pulsación para Start/A en pantallas; A en juego es nivel (mantener).

## 10. Cadenas exactas

| Cadena | Tiles | Dónde |
|---|---|---|
| `PULSA START` | 11 | TITLE (10,4); CONTINUAR (13,4) |
| `RECORD` | 6 | TITLE (12,3); GAMEOVER (9,3); CLEAR (10,2) |
| `FASE 1` | 6 | HUD (0,7) |
| `PELIGRO` | 7 | HUD (0,6), con `ICON_BOSS` en (0,4) y (0,14) |
| `PAUSA` | 5 | HUD (0,7) |
| `CONTINUAR?` | 10 | CONTINUAR (5,5) |
| `QUEDAN n` | 8 | CONTINUAR (11,6) |
| `FIN DEL JUEGO` | 13 | GAMEOVER (5,3) |
| `PUNTOS` | 6 | GAMEOVER (7,3) |
| `NUEVO RECORD!` | 13 | GAMEOVER (11,3); CLEAR (12,3) |
| `FASE COMPLETADA` | 15 | CLEAR (2,2) |
| `BOMBAS n x 2000` | 15 | CLEAR (4,2) (`x` = `ICON_TIMES`) |
| `SIN MORIR 10000` | 15 | CLEAR (6,2) |
| `TOTAL` | 5 | CLEAR (8,2) |

## 11. Comprobaciones (checklist)
- Legibilidad: texto negro sobre blanco; iconos con contorno negro y relleno gris claro/oscuro
  dentro (nada importante en gris claro sobre blanco). Las nubes del título son gris claro a
  propósito (decorado). Probado encima de `art_stage` (HUD sobre murallas): se lee.
- HUD fuera de la acción (líneas 0-7, el juego empieza en la 8); números con ceros y anchos fijos;
  sin línea separadora (preferencia del usuario en CABALLERITO).
- Sprites por línea: la UI solo usa 2 (grifo en TITLE). El HUD apaga los sprites en 0-7.
- Cambios de pantalla completa con LCD apagado y `skip_measure`; en juego ≤ 12 tiles de HUD por
  frame, 20 en los frames de aviso (GDD §9.2 presupuesta 20).
- Tests sugeridos: en PLAY leer `$9C00-$9C13` y comparar con `score` (tiles 24+d), `lives`, `bombs`,
  `power` (`$9C08/$9C0B/$9C0E`) y la barra (`$9C10-$9C12` = 5 + n); en PAUSE, `$9C07-$9C0B` =
  `PAUSA` (tiles 34+15, 34+0, 34+20, 34+18, 34+0) en la fase visible del parpadeo; en CONTINUAR,
  `$9D09` = 24 + cuenta.
