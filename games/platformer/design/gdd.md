# PLATFORMER (título provisional) — Documento de diseño

Estado: borrador (2026-10-14)    Versión: 0.1    Autor: game-designer

> Nombre de carpeta `games/platformer`. Título, protagonista, enemigos y objetos definitivos: ver
> §12 "Decisiones pendientes". En este documento se usan **nombres técnicos neutros**
> (PLAYER, WALKER, SHELL, ITEM_GROW...) y, entre paréntesis, los del concepto recomendado (A, "BROTE").
> Copiamos **mecánicas** de Super Mario Bros / Super Mario Land; nada de nombres, personajes, gráficos
> ni música de Nintendo.

---

## 1. Pitch

- **Género:** plataformas de scroll horizontal (side-scroller) para DMG.
- **Fantasía:** "eres un pequeño héroe que cruza un mundo corriendo, saltando sobre enemigos, rompiendo
  bloques y creciendo con power-ups hasta llegar a la meta antes de que se acabe el tiempo."
- **Bucle principal:** correr hacia la derecha → leer el siguiente obstáculo (hoyo, enemigo, bloque) →
  saltar en el momento justo → recoger monedas/power-ups → llegar a la meta y sumar puntos por tiempo.
- **Qué lo hace distinto:** es el primer juego con scroll del estudio; la novedad para el jugador es el
  tema y los personajes originales (ver §12); la mecánica es la clásica, bien afinada y fluida en DMG.
- **Duración de partida objetivo:** nivel de 90-150 s; partida M1 completa 2-5 min; juego final (4
  niveles) 10-15 min.
- **Referencias:**
  - *Super Mario Bros.* (NES): física de carrera y salto variable, bloques ?, ladrillos, cadena de
    pisotones, caparazón, asta de meta, tiempo, 100 monedas = vida, cámara que no vuelve atrás.
  - *Super Mario Land* (GB): niveles de solo 1 pantalla de alto, HUD de 2 filas arriba, ritmo en
    pantalla pequeña, enemigos de 16x16.
  - `games/tetris` (este repo): bucle `vsync → draw_vram → update`, colas de VRAM con presupuesto fijo,
    copia asm, `vram_late`, `max_frame_lines`, BCD de la puntuación (`bcd.s`).

---

## 2. Mecánicas

### 2.0 Convenciones (obligatorias para programador y tests)

- **Unidades:** píxeles y frames (59.73 fps). Velocidades y aceleraciones en **8.8 con signo**
  (`int16_t`, `0x0100` = 1 px/frame).
- **Coordenadas de mundo:**
  - `x`: `uint16_t` píxeles (0..4095) + `uint8_t` subpíxel. Nivel máx. 256 columnas de metatile = 4096 px.
  - `y`: `uint8_t` píxeles con **sesgo `Y_BIAS = 32`** (la fila 0 del nivel empieza en y=32; así
    caben saltos por encima del borde superior sin números negativos) + `uint8_t` subpíxel.
  - La posición de un actor es la esquina **superior izquierda** de su caja de 16 px de ancho.
- **Nivel:** 8 filas de metatiles de 16x16 (128 px = 16 filas de tiles) x N columnas (M1: N = 200).
  - Fila 0 = arriba, fila 7 = abajo (suelo normal). Suelo del jugador en el nivel 1-1: pies en
    y = 32 + 112 = 144.
  - Fuera del mapa: filas < 0 = vacío; filas >= 8 = vacío (hoyo). Columnas < 0 o >= N = sólido
    (paredes invisibles).
- **Mapa en RAM:** al cargar el nivel se copia/descomprime de ROM a `level[]` en WRAM,
  **column-major**, índice `(col << 3) | fila` (máx. 2048 bytes). Colisión, streaming y cambios de
  bloques leen y escriben **solo** esta copia.
- **Globales legibles por tests** (no `static`): ver §9.4.

### 2.1 Movimiento horizontal del jugador

| Parámetro | Valor | Unidad | Notas |
|---|---|---|---|
| Velocidad máx. andando | 0x0140 (1.25) | px/f | ajustar en playtest |
| Velocidad máx. corriendo (B mantenido) | 0x0200 (2.0) | px/f | ajustar en playtest; **es también la velocidad máx. de scroll** |
| Aceleración (suelo) | 0x0020 | /f | 0 → andar en 10 f, 0 → correr en 16 f |
| Deceleración sin dirección (suelo) | 0x0030 | /f | de correr a 0 en ~11 f |
| Derrape (dirección contraria en suelo) | 0x0060 | /f | animación SKID mientras el signo de vx ≠ dirección pulsada |
| Aceleración en el aire | 0x0018 | /f | |
| Límite de velocidad en el aire | el de despegue | | si saltó corriendo (|vx| > 0x0140), conserva el máx. de correr aunque suelte B |
| Deceleración en el aire sin dirección | 0 | | conserva la inercia (como SMB) |
| Agachado (solo grande, en suelo) | decel 0x0020 | /f | se desliza hasta parar; no puede acelerar |

Reglas:
- Soltar B mientras corre en el suelo: el máximo baja a 1.25 y vx decelera con 0x0030 hasta ese máximo.
- El jugador no puede salir por la izquierda de la cámara: `x >= camera_x` (si choca con el borde, vx = 0).
- Al final del nivel la pared invisible es la columna N.

### 2.2 Salto

Se usan **dos gravedades** (estilo SMB): baja mientras sube con A mantenido, alta en el resto. Así
el salto es variable sin "cortes" bruscos.

| Parámetro | Valor | Unidad | Notas |
|---|---|---|---|
| vy inicial (|vx| <= 0x0180) | -0x0380 (-3.5) | px/f | altura con A mantenido ≈ 49 px (3 metatiles) |
| vy inicial (|vx| > 0x0180, carrerilla) | -0x0400 (-4.0) | px/f | altura ≈ 64 px (4 metatiles) |
| Gravedad subiendo con A mantenido | 0x0020 | /f | |
| Gravedad normal (A suelto, o vy >= 0) | 0x0050 | /f | salto con toque mínimo ≈ 20 px |
| Velocidad máx. de caída | 0x0400 (4.0) | px/f | < 8 px/f: sin tunneling |
| Coyote time | 5 | f | puede saltar 5 f después de dejar un borde |
| Jump buffer | 5 | f | A pulsado ≤ 5 f antes de aterrizar salta al tocar suelo |
| Choque de cabeza | vy = 0 | | empieza a caer con gravedad normal |
| Corrección de esquina (cabeza) | 4 | px | si la cabeza solapa un bloque ≤ 4 px en horizontal, se empuja al jugador fuera en vez de chocar |
| Rebote al pisar enemigo, A mantenido | -0x0380 | px/f | con gravedad baja: rebote alto (~49 px) |
| Rebote al pisar enemigo, A suelto | -0x0280 | px/f | ≈ 10 px |

Cálculos de referencia (para diseño de niveles, comprobados por el lint de niveles §11):
- Salto andando: 28 f subiendo + ~18 f bajando ≈ 46 f x 1.25 = **~57 px de alcance** → hoyos de
  hasta **3 metatiles** sin correr.
- Salto corriendo: 32 f + ~20 f ≈ 52 f x 2.0 = **~104 px** → hoyos de hasta **5 metatiles** con carrerilla.
- Altura: andando ~49 px (sube a una plataforma de 3 metatiles), corriendo ~64 px (4 metatiles).

### 2.3 Formas del jugador (power-ups) y daño

| Forma | Tamaño sprite | Hitbox (offset x,y / ancho x alto) | Sprites OAM | Notas |
|---|---|---|---|---|
| SMALL (pequeño) | 16x16 | (3,2) / 10x14 | 2 (8x16) | no rompe ladrillos |
| BIG (grande, ITEM_GROW "Abono") | 16x32 | (3,4) / 10x28 | 4 (2 por línea) | rompe ladrillos; puede agacharse |
| BIG agachado | 16x16 (frame CROUCH) | (3,18) / 10x14 | 2 | |
| SHOT (disparo, ITEM_SHOT "Girasol") | 16x32 | igual que BIG | 4 | mismos tiles que BIG con **paleta OBP1**; B lanza proyectiles |

Transiciones:
- SMALL + ITEM_GROW → BIG. Animación de crecer: **48 f**, alterna frame pequeño/grande cada 4 f,
  **lógica congelada** (enemigos y tiempo parados).
- BIG + ITEM_SHOT → SHOT. Animación: 32 f alternando OBP0/OBP1 cada 4 f, lógica congelada.
- SMALL + ITEM_SHOT (si cogió uno que ya estaba en pantalla) → BIG.
- ITEM_GROW cogido siendo BIG/SHOT → solo 1000 puntos.
- **Daño:** SHOT → (regla pendiente §12, recomendado BIG); BIG → SMALL; SMALL → muerte.
  Encoger: 48 f congelado alternando grande/pequeño, luego **invulnerabilidad 90 f** (parpadeo:
  2 f visible / 2 f oculto). Durante la invulnerabilidad el contacto lateral con enemigos se ignora;
  pisar sigue funcionando.
- **Atascado tras crecer** (techo de 1 metatile encima): si la hitbox grande solapa sólido, el
  jugador se empuja 1 px/f hacia donde mira hasta quedar libre; sin daño.

### 2.4 Proyectil (forma SHOT, "pipas")

| Parámetro | Valor | Unidad | Notas |
|---|---|---|---|
| Disparo | flanco de B | | B sigue sirviendo para correr mientras se mantiene |
| Máx. en pantalla | 2 | | si hay 2, B no dispara |
| Cadencia mínima | 8 | f | entre disparos |
| Aparición | x = frente del jugador (±12 px), y = jugador + 8 (BIG) | px | |
| vx | ±0x0300 (3.0) | px/f | |
| vy inicial | +0x0100 | px/f | |
| Gravedad | 0x0060 | /f | |
| Rebote en suelo | vy = -0x0200 | px/f | rebota a altura fija (~8 px) |
| Hitbox | 6x6 | px | sprite 8x8 visual |
| Destrucción | choca con pared, sale de cámara, toca enemigo | | al chocar: "puf" 8 f (1 sprite) |

### 2.5 Cámara y scroll (recomendación: sin volver atrás, como SMB — ver §12)

| Parámetro | Valor | Notas |
|---|---|---|
| Umbral derecho | `player_x - camera_x > 64` → `camera_x = player_x - 64` | ajustar en playtest; deja 80 px de vista por delante (5 metatiles, 40 f corriendo) |
| Retroceso | **nunca** (`camera_x` solo crece) | el jugador choca con el borde izquierdo de pantalla |
| Máximo | `camera_x <= N*16 - 160` (1-1: 3040) | |
| Velocidad máx. de cámara | = vx máx. del jugador (2 px/f); **garantía de diseño: ≤ 8 px/f** | ≤ 8 px/f asegura como mucho 1 columna nueva por frame |
| Vertical | ninguna | el nivel mide exactamente la zona de juego (16 filas de tiles) |

Hardware:
- Nivel dibujado en las filas 0-15 del mapa BG ($9800). HUD en la **ventana** (recomendado arriba,
  §5). Con HUD arriba: `SCY = 0xF0` (-16) para que la fila 0 del BG aparezca en la línea 16.
- `SCX = camera_x & 0xFF`. El valor se calcula en `update()` en `scx_shadow` y se escribe al
  **principio** de `draw_vram()`, en el mismo VBlank en el que el DMA de GBDK copia el shadow OAM
  calculado con la misma cámara → fondo y sprites se mueven juntos (sin temblor de 1 frame).

**Streaming de columnas** (el punto crítico del juego):
- El mapa BG es un anillo de 32 columnas de tiles. Visibles: de `cam_tile = camera_x >> 3` a
  `cam_tile + 20` (21 columnas si SCX no está alineado).
- Cuando `cam_tile` cambia (cruza múltiplo de 8 px), `update()` prepara la columna de tiles
  `cam_tile + 21` en `col_buf[16]`: para cada fila de metatile r (0..7),
  `mt = level[((c>>1) << 3) | r]`, mitad `h = c & 1` → `col_buf[2r] = mt_tiles[mt][h]`,
  `col_buf[2r+1] = mt_tiles[mt][2+h]`. `draw_vram()` copia los 16 tiles a la columna
  `(cam_tile + 21) & 31` del BG (stride 32 bytes) en el siguiente VBlank.
- La columna +21 se escribe con 1 frame de margen (la +20 ya se escribió al cruzar el tile anterior).
- Carga inicial / respawn: columnas 0..21 con la pantalla apagada (`DISPLAY_OFF`, `skip_measure = 1`).
- **Cambios de bloque** (ladrillo roto, ? usado, moneda cogida): se modifica `level[]` y, si la
  columna del metatile está dentro del rango ya escrito en VRAM (`cam_tile - 1 .. cam_tile + 21`),
  se encola el redibujado de sus 4 tiles (cola FIFO de metatiles, máx. **4 por frame**). Si aún no se
  ha escrito, no hace falta: el streaming leerá `level[]` ya cambiado.

### 2.6 Colisión contra el mapa

- Ejes separados: primero mover x y resolver, luego mover y y resolver.
- Horizontal: puntos del borde izquierdo/derecho de la hitbox a y = arriba+1, abajo-1 (y medio si BIG).
- Vertical (pies/cabeza): puntos x = izquierda+1 y derecha-2 de la hitbox.
- Al chocar se ajusta la posición al borde del metatile (múltiplo de 16) y la velocidad de ese eje a 0.
- **Bloque golpeado con la cabeza:** el de la columna que contiene el centro x del jugador; si el centro
  está sobre vacío, el del punto que tocó. Un solo bloque por salto y frame.

Clases de colisión de metatile (byte de atributos en la tabla de metatiles):

| Clase | Sólido | Al golpear desde abajo | Al tocar |
|---|---|---|---|
| EMPTY (cielo, decorado) | no | — | — |
| SOLID (suelo, bloque duro, tubería, usado) | sí | sonido BUMP | — |
| BRICK (ladrillo) | sí | SMALL: rebota (BUMP, mata enemigos encima); BIG/SHOT: **se rompe** | — |
| Q_COIN (? con moneda) | sí | moneda + pasa a USED | — |
| Q_POWER (? con power-up) | sí | ITEM_GROW si SMALL, ITEM_SHOT si BIG/SHOT; pasa a USED | — |
| HIDDEN_1UP (invisible) | **solo desde abajo** con vy < 0 | aparece como USED y suelta ITEM_1UP | — |
| BRICK_COIN (M2: ladrillo multi-moneda) | sí | moneda por golpe durante 180 f (máx. 10), luego USED | — |
| BRICK_STAR (M2) | sí | ITEM_STAR, pasa a USED | — |
| COIN (moneda suelta) | no | — | +1 moneda, +200; metatile → EMPTY |
| POLE (asta de meta) | no | — | inicia secuencia de meta (§2.11) |

- Golpear desde abajo cualquier bloque que tenga un **enemigo o ítem encima** (la caja del enemigo
  toca la parte superior del bloque) lo mata "volteado" (enemigo) o lo hace saltar e invertir
  dirección (ítem: vy = -0x0300).
- M1 sin animación visual de "bote" del bloque (llega en M4 como sprite 16x16 que sube 4 px y baja en 8 f).

### 2.7 Ladrillos rotos y partículas

| Parámetro | Valor |
|---|---|
| Trozos | 4 sprites 8x8 (en ranura 8x16 con tile inferior vacío) |
| Velocidades iniciales | arriba: (±0x0100, -0x0400); abajo: (±0x0100, -0x0280) |
| Gravedad | 0x0040 /f |
| Vida | hasta salir por abajo o 64 f |
| Efecto en el jugador | vy = 0 (deja de subir) |
| Puntos | 50 |

Moneda que sale de un bloque ?: sprite 8x16 que sube con vy -0x0400 y gravedad 0x0040, desaparece a
los 24 f (≈ 32 px de subida). La moneda se suma en el momento del golpe. Máx. 2 simultáneas.

### 2.8 Enemigos

Reglas comunes:
- **Aparición:** lista de objetos del nivel ordenada por columna; un objeto aparece cuando
  `obj_x < camera_x + 160 + 16`. Puntero de lista solo hacia delante (la cámara no retrocede).
- **Desaparición:** `x + 16 < camera_x - 16`, o caer por debajo del nivel (fila >= 9). No vuelven.
- **Máximo 5 enemigos activos.** Si no hay hueco, el objeto espera (el puntero no avanza) hasta que
  se libere uno.
- Gravedad 0x0040, caída máx. 0x0300. Caminan sobre el mapa con la misma colisión que el jugador.
- Dos enemigos que se tocan **se dan la vuelta ambos** (excepto caparazón en movimiento, que mata).
- **Pisotón:** el jugador cae (vy > 0) y su borde inferior está por encima del centro vertical del
  enemigo en el momento del solape. Si no, es daño.
- **Muerte "volteada"** (proyectil, caparazón, estrella, bloque golpeado debajo): sprite con flip Y,
  vy = -0x0200, cae sin colisión hasta salir de pantalla.

| Enemigo | Hito | Tamaño / hitbox | Comportamiento | Al pisarlo | Otras muertes |
|---|---|---|---|---|---|
| **WALKER** ("Escarabajo") | M1 | 16x16 / (2,4) 12x12 | Anda a ±0x0080 (0.5 px/f), empieza hacia la izquierda; se da la vuelta en paredes; **cae** por los bordes. Animación: flip X cada 8 f | Aplastado: frame SQUASH 30 f y desaparece | volteado |
| **SHELL** ("Caracol") | M1 | 16x16 / (2,2) 12x14 | Igual que WALKER al andar (cae por bordes). Animación 2 frames cada 8 f | Se mete en la concha (quieto) | volteado |
| SHELL quieto | M1 | (2,4) 12x12 | Quieto 300 f; luego tiembla 60 f (frame PEEK alternando cada 4 f); después vuelve a andar hacia el jugador | **Patada** | volteado |
| SHELL pateado | M1 | (2,4) 12x12 | vx ±0x0300 (3 px/f) alejándose del jugador; rebota en paredes; cae por bordes; mata a todo enemigo que toca (cadena de puntos); **daña al jugador** por contacto lateral salvo 8 f de gracia tras la patada | Se detiene (vuelve a SHELL quieto) | volteado |
| PLANT ("Carnívora") | M2 | 16x16 / (3,2) 10x12 | Sale de una tubería: escondida 90 f, sube 16 px en 32 f, arriba 60 f, baja 32 f. No sale si el centro del jugador está a ≤ 24 px del centro de la tubería. Sprite con prioridad "detrás del BG" (bit 7 OAM) para que la tubería la tape | **Daña** (no se puede pisar) | proyectil, caparazón, estrella |
| HOPPER ("Caracol alado") | M2 | 16x16 / (2,2) 12x14 | SHELL que, al aterrizar, salta con vy -0x0380 (≈ 24 px); avanza ±0x0080 | Pierde las alas → SHELL andando | volteado |

Patada de caparazón quieto: al tocarlo de lado, o pisándolo. Dirección = signo de
(centro caparazón - centro jugador); si es 0, la dirección hacia la que mira el jugador.

### 2.9 Ítems

| Ítem | Hito | Sale del bloque | Movimiento | Efecto |
|---|---|---|---|---|
| ITEM_GROW ("Abono") | M1 | sube 16 px en 32 f (0x0080), sin colisión | vx +0x0100 (hacia la derecha), gravedad 0x0040, gira en paredes, cae por bordes | SMALL → BIG; +1000 |
| ITEM_SHOT ("Girasol") | M1 | igual | quieto | BIG → SHOT (SMALL → BIG); +1000 |
| ITEM_1UP | M1 | igual | como ITEM_GROW (mismos tiles, paleta OBP1) | +1 vida |
| ITEM_STAR ("Mariquita dorada") | M2 (opcional, §12) | igual | vx ±0x0100, gravedad 0x0030, al tocar suelo vy = -0x0300 (bota siempre) | Invencible 600 f: mata por contacto (cadena), parpadeo de paleta OBP0/OBP1 cada 4 f (cada 8 f los últimos 120 f), música propia |

Máx. 1 ítem en pantalla (si sale otro, sustituye al anterior). Desaparece al salir por la izquierda o caer.

### 2.10 Puntuación, monedas, vidas y tiempo

| Evento | Puntos |
|---|---|
| Pisotón en cadena (sin tocar suelo) | 100, 200, 400, 500, 800, 1000, 2000, 4000, 5000, 8000, luego 1UP cada uno |
| Caparazón pateado: enemigos que mata en cadena | 500, 800, 1000, 2000, 4000, 5000, 8000, luego 1UP |
| Patear caparazón quieto | 400 |
| Proyectil / estrella / bloque golpeado debajo | 100 (WALKER), 200 (SHELL, PLANT, HOPPER) |
| Moneda | 200 |
| Ladrillo roto | 50 |
| Power-up recogido | 1000 |
| Asta de meta (fila de los pies al tocarla) | filas 0-1: 5000; 2: 2000; 3: 800; 4: 400; 5-6: 100 |
| Tiempo restante al acabar | 50 por unidad |

- La cadena de pisotón se reinicia al tocar el suelo; la del caparazón, al detenerlo o desaparecer.
- **Monedas:** 100 → +1 vida y el contador vuelve a 0. **Vidas:** empiezan en 3, máx. 99.
- **Puntuación:** 6 dígitos BCD (reutilizar `games/tetris/src/bcd.s`), tope 999999.
- **Tiempo:** empieza en **300 unidades**; 1 unidad = **24 f** (300 = 120 s). A 100 unidades: aviso
  sonoro (M3: música acelerada). A 0: muerte.
- **Récord:** en RAM en M1; guardado en SRAM en M4 si se aprueba (§12).

### 2.11 Muerte, checkpoint y meta

- **Muerte** por daño siendo SMALL o por tiempo: lógica congelada 30 f, sprite DEATH con vy = -0x0400,
  gravedad 0x0040, sin colisión, cae fuera de pantalla (~90 f). Música/SFX de vida perdida.
- **Hoyo:** cuando el borde superior del jugador pasa la fila 8 del nivel (y >= 32 + 128) → muerte
  directa sin animación, espera 60 f.
- Después: fundido → pantalla INTRO (con vidas - 1) o GAME OVER si llega a 0.
- **Checkpoint** invisible (objeto `k`, 1-1: columna 100): si el jugador lo ha pasado, reaparece allí.
  Al reaparecer: forma SMALL, tiempo 300, **mapa recargado desde ROM** (bloques restaurados),
  puntuación y monedas se conservan.
- **Meta (asta):** al tocar la columna POLE (hitbox del asta: 4 px de ancho centrados en el metatile):
  1. Puntos por altura (tabla §2.10); control bloqueado; x del jugador pegado al asta.
  2. El jugador y la bandera (sprite 16x16) bajan a 2 px/f hasta la base.
  3. El jugador camina a la derecha a 1.0 px/f hasta la puerta del castillo y se oculta.
  4. Cuenta de tiempo: −1 unidad/frame, +50 puntos cada una, tic de sonido cada 4 f.
  5. Espera 60 f → LEVEL CLEAR.

---

## 3. Controles

| Botón | En juego | En menús / pantallas |
|---|---|---|
| Izquierda / Derecha | mover | — (no hay menús con opciones en M1) |
| Abajo | agacharse (BIG/SHOT en suelo) | — |
| Arriba | nada (reservado: tuberías con warp, §12) | — |
| A | saltar (mantener = más alto) | confirmar |
| B | mantener = correr; pulsar = disparar (forma SHOT) | — |
| Start | pausa / reanudar | empezar en TITLE; saltar espera en GAME OVER / CLEAR |
| Select | nada | nada |

Sin combinaciones de 3 botones. A y B a la vez (correr + saltar) es el uso normal.

---

## 4. Pantallas y flujo

```
BOOT -> TITLE --Start--> INTRO (120 f) -> PLAY <--Start--> PAUSE
                                          |
             +----------------------------+-------------------+
             | muerte                     | meta              |
             v                            v                   |
         DYING (anim)                  GOAL (asta, cuenta)    |
             |                            |                   |
     vidas>0 | vidas=0                    v                   |
       INTRO   GAMEOVER (180 f o Start)  CLEAR (180 f o Start) |
                   |                      |  M1: -> TITLE     |
                   v                      |  M2: -> INTRO del nivel siguiente
                 TITLE                    v
```

`state` (global u8): `TITLE=0, INTRO=1, PLAY=2, PAUSE=3, DYING=4, GOAL=5, CLEAR=6, GAMEOVER=7`.

| Pantalla | Contenido | Notas |
|---|---|---|
| TITLE | Logo (≤ 60 tiles, M2; en M1 texto con la fuente), "PULSA START" parpadeando 30/30 f, "RECORD 000000" | dibujada con LCD apagado |
| INTRO | Fondo liso, "MUNDO 1-1", icono de cabeza + "X 03" | 120 f; mientras, con LCD apagado al principio, se carga el tileset y el nivel |
| PLAY | Nivel + HUD en la ventana | |
| PAUSE | El juego se congela; la fila de etiquetas del HUD se sustituye por "PAUSA" centrado; música en pausa | al reanudar se restaura la fila (20 tiles por la cola del HUD) |
| DYING | animación de muerte (§2.11) | |
| GOAL | secuencia de meta (§2.11) | |
| CLEAR | "NIVEL COMPLETADO" + puntuación | M1: vuelve a TITLE y actualiza récord |
| GAMEOVER | "FIN DEL JUEGO" | 180 f o Start → TITLE |

Transiciones: fundido con BGP en 4 pasos x 4 f (16 f) → redibujado con LCD apagado
(`skip_measure = 1`) → fundido de entrada. Maquetas `.screen`: las hace el ui-designer (en este
momento no hay tileset del juego que referenciar); los layouts de texto de este GDD son la guía.

Textos: solo mayúsculas y dígitos (fuente compartida). Hace falta añadir **"-"** a
`harness/common/font.tiles` para "1-1" (o escribir "1 1"); decisión del ui-designer.

---

## 5. HUD e interfaz

HUD de **2 filas en la ventana**, fijo mientras el BG hace scroll. Propuesta (el ui-designer la refina):

```
col: 0         1
     01234567890123456789
r0:  PUNTOS   oX00  1-1      o = icono moneda
r1:  000000   vX03  t300     v = icono cabeza (vidas), t = icono reloj
```

- **Posición recomendada: arriba** (como SMB/SML; los hoyos se pierden por abajo de forma natural).
  - Ventana en `WY = 0`, `WX = 7`. Interrupción STAT por LYC con `LYC = 15`: la ISR espera a modo 0
    (HBlank) de la línea 15 y apaga la ventana (`LCDC` bit 5 = 0); se vuelve a encender en VBlank.
    Coste ~100-150 T por frame.
  - `SCY = 0xF0` para que la fila 0 del nivel se vea en la línea 16.
  - Alternativa (§12): HUD abajo, `WY = 128`, sin interrupciones, `SCY = 0`. El nivel ocupa las
    mismas 16 filas, así que cambiar de una a otra es tocar 3 registros y la ISR.
- Actualización: cuando cambia un valor, `update()` lo convierte a tiles en un buffer (`hud_buf`) y
  marca la zona sucia; `draw_vram()` copia como mucho **14 tiles de HUD por frame** (puntos 6, monedas 2,
  vidas 2, tiempo 3 + margen).
- Vidas también se muestran en INTRO.

---

## 6. Progresión y dificultad

Dificultad por **tablas de parámetros por nivel**, no por código especial:

| Nivel | Hito | Tileset | Columnas | Tiempo | Hoyo máx. | Enemigos | Novedad |
|---|---|---|---|---|---|---|---|
| 1-1 "Huerto" | M1 | exterior | 200 | 300 | 3 | WALKER, SHELL | todo lo básico |
| 1-2 "Raíces" | M2 | subterráneo | 220 | 300 | 3 | + PLANT | techo de ladrillos, tuberías con plantas |
| 1-3 "Copas" | M2 | exterior (variante) | 200 | 250 | 5 | + HOPPER | plataformas altas, hoyos largos con carrerilla |
| 1-4 "Invernadero" | M2 | interior | 180 | 300 | 4 | todos | final de mundo; ¿jefe? (§12) |

Parámetros por nivel en tabla: velocidad WALKER/SHELL (0x0080 en 1-1, 0x0090 en 1-3/1-4), tiempo
inicial, tileset, música, columna de checkpoint.

### 6.1 Nivel 1-1 (M1): estructura por columnas (N = 200, 3200 px)

| Columnas | Contenido | Qué enseña |
|---|---|---|
| 0-15 | Inicio llano, decorado; jugador en col 2 | moverse, correr |
| 16-24 | ? moneda (c16 f4); fila B P B ? B (c20-24 f4, P = power-up); ? arriba (c22 f1); WALKER c22 | golpear bloques, primer power-up, pisar |
| 28-49 | Tuberías de alto 2 (c28), 3 (c38), 4 (c46); WALKER en c41 y par en c51-53 | saltar obstáculos |
| 56-66 | Tubería 4 (c57); bloque oculto 1UP (c64 f3) | secreto |
| 69-70 | Hoyo de 2 | hoyos |
| 76-88 | B P B (c77-79 f4); fila alta de ladrillos c80-87 f1 con 2 WALKER encima | plataformas altas |
| 88-90 | Hoyo de 3 | |
| 92-103 | Ladrillos y ? de monedas; **checkpoint k en c100** | |
| 104-115 | ? en triángulo (c106, c109, c112 en f4; c109 en f1, uno P); SHELL en c107 | caparazón y patada |
| 118-131 | Ladrillos sueltos y fila alta; **grupo de 3 WALKER** (c122-126) | cadena de pisotones |
| 134-155 | Escalera sube 4 (c134-137) y baja (c140-143); escalera doble alto 4 con hoyo de 2 entre medias (c146-155) | escaleras |
| 160-170 | Tubería 2 (c160); B B ? B (c164-167 f4); tubería 2 (c170); 2 WALKER | |
| 172-180 | Escalera final de alto 6 (bloques duros) | salto a la meta |
| 189 | Asta: bola en f0, palo f1-f5, bloque duro de base en f6 | puntos por altura |
| 193-199 | Castillo decorativo, puerta en c196 | fin |

### 6.2 Formato de nivel (fuente ASCII → C al compilar)

Texto de **8 líneas x N caracteres** (`res/level1_1.lvl`); el conversor (extensión del harness, M1)
genera `level1_1.c/.h` con el mapa de metatiles (column-major, 8 bytes/columna) y la lista de objetos.
Mayúsculas/símbolos = metatiles; minúsculas = objetos (la celda debajo cuenta como cielo).

| Car. | Significado | Car. | Significado |
|---|---|---|---|
| `.` | cielo | `#` | suelo |
| `B` | ladrillo | `H` | bloque duro |
| `?` | ? moneda | `P` | ? power-up |
| `U` | oculto 1UP | `$` | moneda suelta |
| `[` `]` | boca de tubería izq./der. | `{` `}` | cuerpo de tubería izq./der. |
| `\|` | asta | `x` | inicio del jugador |
| `w` | WALKER | `s` | SHELL |
| `k` | checkpoint | `p` / `h` | PLANT / HOPPER (M2) |

Decorado (nubes, arbustos, colinas, castillo): caracteres que define el pixel-artist con su tileset.
Ejemplo (columnas 0-47 del 1-1):

```
................................................
......................?.........................
..................................$$............
..............................................[]
................?...BPB?B.............[]......{}
............................[]........{}......{}
..x...................w.....{}........{}.w....{}
################################################
```

---

## 7. Contenido y assets

Modo de sprites **8x16** (LCDC bit 2 = 1): cada sprite usa un par de tiles (par/impar). Objetos de 8x8
(trozos, proyectil) ocupan un par con el tile de abajo vacío. Flip X en vez de frames a la izquierda.

### 7.1 Tiles de sprite

| Asset | Hito | Tiles | Frames | Notas |
|---|---|---|---|---|
| PLAYER pequeño | M1 | 24 | IDLE, WALK1, WALK2, JUMP, SKID, DEATH (6 x 4) | |
| PLAYER grande | M1 | 40 | mitades sup.: NORMAL, JUMP, SKID, THROW (4 x 4); inf.: IDLE, WALK1, WALK2, JUMP, SKID (5 x 4); CROUCH 16x16 (4) | mitades combinables; SHOT = misma gráfica con OBP1 |
| WALKER | M1 | 8 | WALK (anim por flip), SQUASH | |
| SHELL | M1 | 16 | WALK1, WALK2, SHELL, PEEK | |
| Ítems GROW/SHOT/STAR | M1 (STAR M2) | 12 | 1 c/u | 1UP = GROW con OBP1 |
| Moneda que salta | M1 | 6 | 3 frames 8x16 | |
| Trozo de ladrillo | M1 | 2 | 1 (rotación por flip) | |
| Proyectil + puf | M1 | 4 | 1 + 1 | |
| Bandera | M1 | 4 | 1 | |
| PLANT | M2 | 8 | 2 | |
| HOPPER (alas) | M2 | 8 | 2 | |
| Números de puntos flotantes | M4 | 16 | | "100", "200"... "1UP" |
| **Total** | | **M1: 116 · M2: 132 · M4: 148** | | sprite privados 0-127 + resto en los compartidos 128-255 |

### 7.2 Tiles de fondo/ventana

| Asset | Tiles | Notas |
|---|---|---|
| Fuente (dígitos + A-Z) + "-" | 37 | compartida |
| Iconos HUD (moneda, cabeza, reloj) | 3 | |
| Tileset exterior 1-1: cielo 1, suelo 4, ladrillo 4, ? 4, usado 4, duro 4, boca tubería 8, cuerpo tubería 4, moneda 4, nube 8, arbusto 8, colina 10, asta (bola 4 + palo 2), castillo 12 | 81 | el BG no tiene flip en DMG: cada mitad asimétrica es un tile propio |
| Animación del bloque ? (M4) | 8 | se anima reescribiendo 1 tile (16 bytes) por frame |
| **Total BG** | **~129** | 128 privados ($9000) + 1 en compartidos |

**Total VRAM:** BG ~129 + sprites 148 (M4) = **277 / 384** tiles; zona compartida usada ~21/128.
Margen para que el pixel-artist crezca ~100 tiles. Cada tileset de nivel se carga en INTRO con LCD apagado.
Metatiles por tileset: ≤ 64 (tabla `mt_tiles[64][4]` + `mt_attr[64]` = 320 bytes).

### 7.3 Sprites en pantalla (OAM 40)

| Ranuras OAM | Uso | Sprites |
|---|---|---|
| 0-3 | jugador (2 si SMALL) | 4 |
| 4-13 | 5 enemigos x 2 | 10 |
| 14-15 | ítem | 2 |
| 16-17 | 2 proyectiles | 2 |
| 18-21 | 4 trozos de ladrillo | 4 |
| 22-23 | 2 monedas que saltan | 2 |
| 24-25 | bandera de meta | 2 |
| 26-31 | puntos flotantes (M4, 3 x 2) | 6 |
| **Total peor caso** | | **32 / 40** |

**Sprites por línea, peor caso** (banda de 16 px a ras de suelo): jugador 2 + 3 enemigos 6 + 2
proyectiles 2 = **10 / 10**. Para que se cumpla:
- **Regla de diseño de niveles:** como mucho **3 enemigos** en la misma banda de 16 px dentro de una
  ventana de 176 px (comprobado por el lint de niveles). SMB pone grupos de 4: aquí grupos de 3.
- Trozos de ladrillo y monedas que saltan cruzan bandas unos pocos frames: se acepta parpadeo.
- **Seguridad:** el bloque de enemigos (ranuras 4-13) se **rota** cada frame (el enemigo que va
  primero en OAM cambia), así que si una línea pasa de 10 los sprites parpadean en vez de desaparecer
  siempre los mismos.
- Sprites ocultos con Y = 0, nunca con X fuera de pantalla.

---

## 8. Sonido

M1: **solo efectos**, escritos directamente en registros (sin driver). M3: integración de hUGEDriver
(hito propio) con música y efectos que roban canal.

### 8.1 Efectos

| Efecto | Canal | Prioridad (3 = máx.) | Notas |
|---|---|---|---|
| Salto (SMALL / BIG distinto tono) | 1 (pulso, sweep subida) | 1 | |
| Moneda | 1 | 2 | dos notas agudas |
| Pisotón | 4 (ruido) | 2 | corto |
| Golpe de bloque (bump) | 4 | 1 | |
| Ladrillo roto | 4 | 2 | |
| Aparece power-up | 1 | 2 | arpegio subiendo |
| Coger power-up | 1 | 3 | |
| Disparo | 4 | 1 | |
| Patada de caparazón | 4 | 2 | |
| Daño / encoger | 1 | 3 | sweep bajada |
| 1UP | 1 | 3 | |
| Asta / bandera bajando | 1 | 3 | |
| Tic de cuenta de tiempo | 1 | 1 | cada 4 f |
| Pausa | 1 | 3 | |
| Aviso de tiempo (100) | 1 | 3 | |

Un efecto de igual o mayor prioridad corta al que suena en ese canal; uno menor se descarta.
Con hUGEDriver: la música usa los 4 canales; un efecto silencia la voz de música de su canal mientras dura.

### 8.2 Música (M3, hUGEDriver)

| Pista | Duración | Bucle | Canales |
|---|---|---|---|
| Título | 30-40 s | sí | 1-4 |
| Exterior (1-1, 1-3) | 30-45 s | sí | 1-4 (ruido = percusión) |
| Subterráneo (1-2) | 20-30 s | sí | 1-4 |
| Interior (1-4) | 20-30 s | sí | 1-4 |
| Invencible (estrella) | 6-8 s | sí | 1-4 |
| Nivel completado | 4 s | no | 1-4 |
| Vida perdida | 3 s | no | 1-3 |
| Fin del juego | 5 s | no | 1-3 |
| "Prisa" (tiempo ≤ 100) | jingle 2 s + pista de nivel a tempo +25 % | — | |

Presupuesto: driver ~2.5 KB + ~12 KB de canciones; llamada de 1 vez/frame (~1000-2000 T, medir) desde
el bucle principal fuera de VBlank, con su banco seleccionado.

---

## 9. Técnica

### 9.1 Cartucho: **MBC5 + RAM + batería (0x1B), 64 KB de ROM, 8 KB de SRAM, desde M1**

Estimación de ROM:

| Parte | M1 | Juego completo (M4) |
|---|---|---|
| Código C (+ asm de copia) | 16-22 KB | 20-26 KB |
| Tiles de sprite | 1.9 KB | 2.4 KB |
| Tiles BG + fuente | 2.1 KB | 3 tilesets ≈ 5 KB |
| Niveles (1.6 KB/nivel sin comprimir + objetos) | 1.8 KB | 4 niveles ≈ 7.2 KB |
| Pantalla de título (logo + mapa) | — | 1.4 KB |
| hUGEDriver + música | — | ~14.5 KB |
| Efectos | 0.3 KB | 0.5 KB |
| **Total** | **~22-28 KB** | **~50-57 KB** |

Por qué MBC5 ya en M1: M1 queda rozando los 32 KB y el juego completo los dobla; meter banking
después obliga a reorganizar datos. Con el mapa del nivel copiado a WRAM al cargar, **solo el
cargador de nivel/tileset y la llamada al driver de música cambian de banco**: el banking es casi gratis
si se diseña así desde el principio. Sobre MBC1: MBC5 es el recomendado del estudio (CLAUDE.md).
Batería: solo hace falta si se aprueba guardar el récord (§12); si no, tipo 0x19 (MBC5 sin RAM).
Flags previstas: `["-autobank", "-Wm-yt0x1B", "-Wm-yo4", "-Wm-ya1"]` (si crece de 64 KB: `-Wm-yo8`).

RAM (WRAM 8 KB):

| Uso | Bytes |
|---|---|
| `level[]` (256 col x 8 máx.) | 2048 |
| Actores (≈ 14 x ~16 bytes, struct of arrays) | ~230 |
| Lista de objetos: índice, flags | ~40 |
| Buffers VRAM: `col_buf` 16, cola de metatiles 4 x 6, `hud_buf` 40 | ~80 |
| Shadow OAM (GBDK) | 160 |
| Resto (estado, música) | ~300 |
| **Total** | **~2.9 KB / 8 KB** |

### 9.2 Presupuesto de VBlank (peor frame)

`vsync()` vuelve en LY≈146 → **~3600 T** para `draw_vram()` (CLAUDE.md).

| Trabajo en `draw_vram()` | Tiles | Coste estimado |
|---|---|---|
| Escribir `SCX` (+ `SCY`) | — | ~30 T |
| Columna de streaming (asm desenrollado, stride 32: `ld a,(de) / inc de / ld (hl),a / add hl,bc` ≈ 32 T/tile) | 16 | ~600 T con llamada |
| Cola de metatiles (máx. 4 x 4 tiles, ~40 T/tile con dirección calculada en `update()`) | 16 | ~700 T |
| HUD (máx. 14 tiles, rutinas de copia de fila asm 20 T/tile) | 14 | ~400 T |
| Animación de tile del bloque ? (M4, 16 bytes) | 1 tile | ~400 T |
| **Total peor caso** | **47 tiles** | **~2100 T (58 % de 3600)** |

- A 2 px/f entra una columna cada 4 frames; con la garantía de ≤ 8 px/f, nunca más de 1 por frame.
- Todo se prepara en `update()` (direcciones de VRAM, tiles a copiar); en VBlank solo se copia (lección de tetris).
- Prohibido `set_bkg_tiles`/`set_win_tiles` durante el juego (≈ 520 T/tile).
- Guardia `vram_late` (LY < 144 al acabar `draw_vram()`) debe ser 0 en todos los tests.
- Si en la medición se pasa, la cola de metatiles baja a 2 por frame (el resto espera al siguiente).

### 9.3 Presupuesto de CPU (fuera de VBlank)

| Trabajo | Estimación |
|---|---|
| Jugador: física + colisión con mapa | ~3000-5000 T |
| 5 enemigos (física + mapa) + pares enemigo-enemigo (10) + contra jugador | ~8000 T |
| Ítems, proyectiles, partículas | ~2000 T |
| Preparar columna, HUD, aparición de objetos | ~1500 T |
| Componer shadow OAM (≤ 32 sprites) | ~3500 T |
| Música hUGEDriver (M3) | ~1500 T (medir) |
| **Total** | **~20000-22000 T ≈ 45-50 líneas de 154** |

Objetivo del test: `max_frame_lines ≤ 120` en el bot de 10 000 frames (deja > 20 % libre). Si se pasa:
perfilar (`gb.profile`) y llevar a asm la colisión de actores contra el mapa.

### 9.4 Globales para tests (no `static`)

`state`, `level_num`, `player_x` (u16), `player_y`, `player_vx`, `player_vy` (s16), `player_form`
(0 SMALL, 1 BIG, 2 SHOT), `player_inv` (frames de invulnerabilidad), `player_on_ground`, `camera_x`
(u16), `scx_shadow`, `cols_written` (última columna de tiles escrita), `level[]`, `mt_tiles[]`,
`act_type[]`, `act_x[]`, `act_y[]`, `act_state[]`, `coins`, `lives`, `score` (BCD 3 bytes),
`time_units`, `checkpoint`, `vram_late`, `max_frame_lines`, `skip_measure`, `max_line_sprites`
(máximo de sprites en una línea calculado por el test desde OAM, no por el juego),
`cheat_flags` (bit 0: invencible, bit 1: tiempo infinito; solo los escriben los tests).

### 9.5 Riesgos técnicos y mitigación

| Riesgo | Mitigación |
|---|---|
| VBlank desbordado (columna + bloques + HUD) | copia asm, colas con presupuesto fijo, `vram_late == 0` en tests, test de estrés de cámara a 4 y 8 px/f |
| Columnas mal escritas (tiles equivocados al hacer scroll) | test que compara el mapa BG de VRAM con `level[]` + `mt_tiles` en todas las columnas visibles, cada frame, durante un recorrido entero |
| Más de 10 sprites por línea | regla de 3 enemigos por banda (lint), rotación de OAM |
| ISR de LYC a mitad de frame (HUD arriba) | esperar a HBlank antes de tocar LCDC; PyBoy no garantiza timing de hardware real → probar en hardware (M5); alternativa HUD abajo sin ISR |
| CPU con 5 enemigos en C | struct of arrays, sin indexar con `int8_t`, perfilar; colisión a asm si hace falta |
| Banking (datos en bancos leídos con el banco equivocado) | solo el cargador y la música cambian de banco; test que carga cada nivel y compara `level[]` con el fuente |
| Bugs de colisión en esquinas (cabeza entre dos bloques, atascado al crecer, borde izquierdo de cámara) | tests deterministas con posiciones fijadas por `write_u16` |

---

## 10. Hitos

- **M1 — slice jugable (nivel 1-1 entero, arte provisional):**
  MBC5 configurado; conversor `.lvl` → C; carga del nivel a WRAM; streaming de columnas y cámara sin
  retroceso; HUD en ventana (arriba con ISR LYC, o abajo si se decide así); física SMALL/BIG/SHOT con
  agacharse; WALKER y SHELL (con patada y cadena); bloques ?, ladrillos (rebote/rotura), oculto 1UP,
  monedas; proyectil; hoyos, tiempo, vidas, puntuación, 100 monedas = vida; checkpoint; asta y cuenta
  de tiempo; pantallas TITLE (solo texto), INTRO, PAUSE, DYING, GAMEOVER, CLEAR (→ TITLE); efectos de
  sonido básicos por registros; tests de §11.
- **M2 — contenido:** niveles 1-2, 1-3, 1-4 (2 tilesets más); PLANT, HOPPER; ITEM_STAR y ladrillo
  multi-moneda (si se aprueban); logo de título; flujo CLEAR → siguiente nivel; final del mundo.
- **M3 — música:** integración de hUGEDriver (banco propio), 9 pistas de §8.2, efectos con prioridad
  y robo de canal, "prisa".
- **M4 — pulido:** bote visual de bloques, puntos flotantes, bloque ? animado, fundidos, polvo al
  derrapar, guardado del récord en SRAM (firma + checksum) si se aprueba.
- **M5 — hardware real:** flash cart; revisar ISR de LYC, parpadeos, LCD borroso con objetos rápidos
  (caparazón a 3 px/f), audio.

---

## 11. Plan de pruebas

| Qué | Cómo |
|---|---|
| Aceleración / velocidad máx. andando y corriendo | test: mantener Derecha (y B) N frames → `player_vx` llega a 0x0140 / 0x0200 en 10 / 16 f (±1) |
| Deceleración y derrape | test: soltar / pulsar contrario → frames hasta vx = 0 |
| Altura de salto (toque, andando, corriendo) | test: registrar `player_y` mínimo → ≈ 20 / 49 / 64 px (±2) |
| Coyote time y jump buffer | test: posicionar en borde con `write_u16`, pulsar A en f 4 (salta) y f 7 (no salta); A 5 f antes de aterrizar |
| Choque de cabeza y corrección de esquina | test: jugador bajo bloque con desplazamiento 3 px (se corrige) y 6 px (choca) |
| Bloques: ? moneda / power-up / ladrillo SMALL / ladrillo BIG / oculto | test: golpear desde abajo → `level[]` cambia a USED/EMPTY, `coins`, `score`, ítem creado según forma |
| Moneda suelta, 100 monedas → vida | test: fijar `coins = 99`, coger una → `coins == 0`, `lives + 1` |
| Pisotón vs daño; cadena de puntos | test: enemigo colocado debajo con vy > 0 → muere y score +100; segundo sin tocar suelo +200; contacto lateral → `player_form` baja |
| Caparazón: meterse, patear, rebotar en pared, matar en cadena, gracia 8 f | test con posiciones fijadas |
| Formas: crecer, disparo, encoger, invulnerabilidad 90 f | test de transiciones y temporizadores (`player_inv`) |
| Proyectil: máx. 2, cadencia 8 f, rebote, muere en pared | test |
| Hoyo y tiempo 0 → muerte; checkpoint | test: `state` pasa a DYING; reaparición en col 100 si `checkpoint` |
| Meta: puntos por altura y cuenta de tiempo | test: tocar asta a distintas filas → score esperado; `time_units` baja a 0 y suma 50/u |
| Cámara: nunca retrocede, umbral 64, tope final | test: andar a la izquierda → `camera_x` no baja; jugador no sale por la izquierda |
| **Streaming correcto (VRAM == mapa)** | test/bot: recorrer el nivel corriendo; cada frame leer el mapa BG ($9800) con `gb.pyboy.memory` y comparar las 21 columnas visibles con `level[]` + `mt_tiles`; también tras romper ladrillos y coger monedas |
| Estrés de streaming | test con `camera_x` forzada a avanzar 4 y 8 px/f (cheat de tests) → misma comparación y `vram_late == 0` |
| Presupuesto de frame | bot 10 000 frames (correr, saltar, disparar, con `cheat_flags` invencible) → `max_frame_lines ≤ 120`, `vram_late == 0`; perfil de `draw_vram ≤ 3000 T` |
| Sprites por línea | bot: cada frame contar sprites visibles por línea desde OAM → ≤ 10 salvo frames con trozos de ladrillo |
| Lint de niveles (Python puro, sin emulador) | sobre `res/*.lvl`: ancho/alto, hoyos ≤ máximo de la tabla §6, ≤ 3 enemigos por banda en ventana de 176 px, asta y `x` presentes, tuberías bien cerradas, obstáculos ≤ altura de salto |
| Banking | test: cargar cada nivel → `level[]` igual al generado desde el `.lvl` |
| Capturas | `gb.screenshot` en inicio, bloque roto, BIG, meta → revisión visual (Read del PNG) |
| **Playtest humano** | feel del salto y la carrera, umbral de cámara, dificultad del 1-1, legibilidad en LCD borroso (caparazón rápido), si el HUD arriba molesta, sonido |

---

## 12. Decisiones pendientes (para el usuario)

- [ ] **1. Título, protagonista y tema** (nada de IP de Nintendo):
  - **A) "BROTE"** (recomendado): un brote/semilla con patas en un huerto invadido por bichos.
    Crecer = "Abono", disparo = "Girasol" (escupe pipas), estrella = "Mariquita dorada", monedas =
    gotas de agua (100 gotas = vida), WALKER = escarabajo, SHELL = **caracol** (la concha encaja de forma
    natural con la mecánica de patear), PLANT = planta carnívora en tubos de riego, meta = verja del huerto
    con bandera. Siluetas muy legibles en DMG y tono simpático y original.
  - B) "BOLT": un robot pequeño. Crecer = "Batería" (armadura), disparo = "Chispa", monedas = tornillos,
    enemigos = droide andante, armadillo-bot (bola), torreta en conductos.
  - C) "TINY KNIGHT" / "PEQUEÑO CABALLERO": caballerito. Crecer = "Yelmo", disparo = "Hacha" arrojadiza,
    enemigos = slime, tortuga acorazada, planta en macetas; meta = estandarte del castillo.
- [ ] **2. Posición del HUD:** A) **arriba con ventana + interrupción LYC** (recomendado: aspecto SMB/SML,
  los hoyos se ven caer por abajo; además prueba una técnica útil para el arnés); B) abajo con la
  ventana sin interrupciones (más simple y robusto, estilo Kirby, pero el jugador "cae dentro del HUD").
- [ ] **3. Cámara:** A) **sin volver atrás, como SMB** (recomendado: streaming en un solo sentido,
  enemigos que no reaparecen, más simple y probado); B) cámara libre en ambos sentidos (streaming por
  los dos lados, reaparición de enemigos, más RAM de estado y más casos de test).
- [ ] **4. Idioma de los textos:** A) **español** (recomendado: "PULSA START", "PAUSA", "FIN DEL JUEGO",
  "MUNDO"; no hacen falta tildes ni Ñ); B) inglés arcade ("PUSH START", "GAME OVER").
- [ ] **5. Dificultad / regla de daño:** A) clásica SMB: SHOT recibe daño → SMALL, 3 vidas;
  B) **suave**: SHOT → BIG, 3 vidas (recomendado para sesiones cortas en GB); C) muy suave: además 5 vidas.
- [ ] **6. Guardar récord en SRAM (batería):** A) **sí, en M4** (recomendado; MBC5+RAM+batería ya
  reservado, coste pequeño); B) no (cartucho 0x19 sin RAM).
- [ ] **7. Tamaño del juego final:** A) **4 niveles (un mundo) en M2** y decidir más tras el playtest
  (recomendado); B) 8 niveles (dos mundos, ROM 128 KB); C) solo el 1-1 pulido.
- [ ] **8. Estrella de invencibilidad (y ladrillo multi-moneda):** A) **sí, en M2** (recomendado:
  momento de euforia barato); B) no.
- [ ] **9. Jefe en el 1-4:** A) **sin jefe, final por asta** (recomendado para no ampliar alcance);
  B) jefe sencillo estilo SMB (puente que se rompe con un interruptor), hito aparte.
- [ ] **10. Tuberías con warp / salas de bonus (Abajo sobre la boca):** A) **no hasta después de M4**
  (recomendado); B) sí en M2 (sala de monedas por nivel).
