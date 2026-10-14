# GRIFO (título provisional) — Documento de diseño

Estado: borrador (2026-10-14)    Versión: 0.1    Autor: game-designer

> Carpeta `games/shmup`. Shoot'em up de scroll vertical para DMG. **Doble objetivo:** un juego pequeño
> y pulido, y **estresar y ampliar el arnés** (`harness/common`, gbe): scroll vertical con streaming de
> filas, piscinas de muchos objetos en 8 bits, multiplexado/parpadeo de sprites, patrones de balas,
> colisión rápida en asm, guiones de oleadas y un jefe dibujado en el fondo.
> Tema y título pendientes (§12); este documento usa el concepto recomendado **GRIFO**. En el código y
> los tests se usan **nombres técnicos neutros** (PLAYER, DART, WAVE, SWOOP, CARRIER, TURRET, BOSS);
> entre paréntesis, el nombre del tema.
> Mecánicas clásicas del género (Solar Striker, 1942, Twinbee); nada de nombres, gráficos ni música ajenos.

---

## 1. Pitch

- **Género:** shmup vertical (scroll de abajo arriba), una fase + jefe en M1.
- **Fantasía:** "eres un joven caballero a lomos de un grifo que sobrevuela el reino —bosque, río,
  murallas y torres— disparando a las criaturas del dragón hasta enfrentarte a él en la niebla."
- **Bucle principal:** esquivar balas legibles moviéndote en 8 direcciones → mantener A para disparar
  y barrer oleadas → coger plumas (arma) y cuernos (bombas) de los portadores → usar la bomba cuando
  la pantalla se llena → derrotar al jefe.
- **Qué lo hace distinto:** jefe grande (64x48) **dibujado en el fondo** y movido con SCX/SCY, torretas
  de tierra también en el fondo (0 sprites), y un gestor de sprites con prioridades que hace que lo que
  parpadea sea siempre lo menos peligroso. Para el jugador: tema de fantasía original, dificultad suave.
- **Duración:** fase de **~107 s** de scroll + jefe **~30-45 s** → partida M1 de **2.5-4 min**.
- **Referencias:**
  - *Solar Striker* (GB): ritmo, escala de enemigos 16x16, pocas balas pero claras, jefe al final.
  - *1942 / Twinbee*: oleadas con trayectorias fijas, portadores que sueltan power-ups, bomba.
  - `games/platformer` (este repo): HUD arriba con corte LYC (`gbe_video`), regla de cámara en 8 bits,
    colas de VRAM, bots que deben avanzar, `act_move` asm (aquí, versión de 8 bits).
  - `games/tetris`: copia de fila asm a 20 T/tile, BCD de la puntuación (`bcd.s`).

---

## 2. Mecánicas

### 2.0 Convenciones (obligatorias para programador y tests)

- **Unidades:** píxeles y frames (59.73 fps). Velocidades en **8.8 con signo** (`int16_t`, `0x0100` =
  1 px/f); posiciones `uint8_t` píxel + `uint8_t` subpíxel.
- **Todo vive en espacio de pantalla, en 8 bits.** No hay coordenada de mundo para los objetos
  voladores: el scroll solo afecta al fondo y a los objetos de tierra (§2.8). Esto es lo que hace
  posible el presupuesto de CPU (§9.3).
- **Coordenadas = coordenadas OAM** de la esquina superior izquierda: `X = x_pantalla + 8`,
  `Y = y_pantalla + 16`. Dibujar es copiar sin sumar.
  - Vivo si `X < 168` y `Y < 176`. Un objeto que sale por la izquierda o por arriba pasa de 0 a
    0xF8-0xFF y la **misma comparación** lo mata (ninguna velocidad supera 8 px/f, así que nunca salta
    el hueco 168-255 / 176-255 de golpe).
  - Los enemigos aparecen con `Y` 0..15 (pantalla −16..−1): entran **por debajo del HUD**, donde los
    sprites están apagados (líneas 0-7), y "salen" de él suavemente.
- **Cajas de colisión** como centro + semitamaño en 8 bits: solape si
  `GBE_WITHIN(cxa - cxb, hwa + hwb) && GBE_WITHIN(cya - cyb, hha + hhb)` (macro simétrica de `gbe.h`).
- **Pantalla de juego:** líneas 8-143 (136 px de alto x 160 de ancho). Línea 0-7: HUD (ventana).
- **Globales legibles por tests** (no `static`): §9.5.

### 2.1 Jugador (PLAYER, "Grifo")

| Parámetro | Valor | Unidad | Notas |
|---|---|---|---|
| Sprite | 16x16 | px | 2 sprites 8x16; frames NORMAL, BANK_L, BANK_R (ladeado al moverse en x) |
| Velocidad recta | 0x0180 (1.5) | px/f | ajustar en playtest |
| Velocidad diagonal | 0x0110 (1.06) por eje | px/f | ≈ 1.5 / √2; diagonal no más rápida |
| Aceleración | instantánea | | shmup: respuesta directa, sin inercia |
| Límites X (OAM) | 8 .. 152 | | pantalla x 0..144 |
| Límites Y (OAM) | 32 .. 144 | | pantalla y 16..128: no puede meterse pegado al HUD (los enemigos entran ahí) |
| Frame ladeado | tras 6 f pulsando izq./der.; vuelve a NORMAL 6 f después de soltar | f | solo visual |
| **Hitbox de daño (núcleo)** | 4x4 en (6,6) del sprite → centro (X+8, Y+8), semitamaño 2x2 | px | el jinete; el resto del grifo no recibe daño |
| Hitbox de recogida (ítems) | 12x12 en (2,2), semitamaño 6x6 | px | generosa |
| Posición inicial / reaparición | X = 80, Y = 136 (pantalla 72, 120) | | |

### 2.2 Disparo y niveles de arma

A mantenido = **autodisparo**. Al pulsar A (flanco), si el enfriamiento ya llegó a 0, dispara en ese
mismo frame; mantenido, repite cada `FIRE_RATE`.

| Parámetro | Valor | Unidad | Notas |
|---|---|---|---|
| `FIRE_RATE` | 8 | f | 7.5 ráfagas/s; ajustar en playtest |
| Velocidad del disparo central | vy = −0x0500 (−5.0) | px/f | rayo de 12 px de alto, se lee bien a esa velocidad |
| Disparos laterales (nivel 3) | vx = ±0x0140, vy = −0x04C0 | px/f | ≈ ±15° |
| Aparición | X = jugador X + 4, Y = jugador Y − 12 (central); laterales en X ± 6 | px | |
| Piscina de disparos | **8** | ranuras | si no hay hueco, esa parte de la ráfaga no sale |
| Hitbox central | nivel 1: 4x12 (semi 2x6); nivel 2: 8x12 (semi 4x6) | px | centro (X+4, Y+8) |
| Hitbox lateral | 4x8 (semi 2x4) | px | |
| Daño | central nivel 1: 1; central nivel 2-3: 2; lateral: 1 | HP | |

| Nivel | Ráfaga cada 8 f | Sprites por ráfaga | Vivos (aprox.) |
|---|---|---|---|
| 1 | 1 rayo central (tile de 1 rayo) | 1 | 136/5 = 27 f de vida → ~4 |
| 2 | 1 rayo doble central (mismo sprite, tile de 2 rayos separados 4 px) | 1 | ~4 |
| 3 | rayo doble + **2 laterales en ráfagas alternas** (cada 16 f) | 1 / 3 | ~4 + ~4 = 8 (= piscina) |

- Pluma (ítem P): nivel +1 (máx. 3); con nivel 3 da 1000 puntos.
- **Al morir: nivel −1** (mínimo 1) — propuesta de dificultad suave, ver §12.
- Disparos por línea: el central como mucho 1 por línea (separación 40 px > 16 px del sprite);
  laterales ≤ 2. **Total ≤ 3 por línea.**

### 2.3 Bomba ("Rugido" del grifo)

| Parámetro | Valor | Notas |
|---|---|---|
| Botón | B (flanco) | no se puede lanzar otra mientras dura (90 f) |
| Bombas al empezar / al reaparecer | 2 / se rellena hasta 2 si tenía menos | dificultad suave |
| Máximo | 4 | cuerno (ítem B) +1; con 4 da 1000 puntos |
| Efecto inmediato | **borra todas las balas enemigas** (+10 puntos cada una); 8 de daño a todo enemigo visible (voladores, torretas, jefe) | se aplica en 1 frame |
| Invulnerabilidad | 90 f | sin parpadeo (el jugador sabe que la lanzó) |
| Efecto visual | temblor SCY ±2 px alternando cada 2 f durante 16 f + `set_fade(1)` 4 f y vuelta | sin inversión de paleta (ghosting/epilepsia); el HUD también se aclara (comparte BGP, aceptado) |
| Bala nueva durante el rugido | los enemigos **no disparan** durante los 90 f | evita que la pantalla se rellene al instante |

### 2.4 Daño, vidas, reaparición y continuaciones

| Parámetro | Valor | Notas |
|---|---|---|
| Vidas al empezar | 3 | máx. 9 |
| Vidas extra | a los 20 000 y 50 000 puntos | una vez cada una |
| Muerte | núcleo del jugador toca bala enemiga, cuerpo de enemigo volador o cuerpo del jefe | las torretas de tierra no se tocan (se vuela por encima) |
| Animación de muerte | explosión 32 f (3 frames de 16x16) + temblor ±2 px 12 f; **el scroll sigue** | |
| Al morir | se borran todas las balas enemigas (sin puntos); los enemigos no disparan durante 60 f tras reaparecer | |
| Reaparición | **en el sitio** (sin retroceder), en X=80 Y=136, entrando desde abajo (Y 176 → 136 en 20 f, sin control) | |
| Invulnerabilidad tras reaparecer | 120 f, parpadeo 4 f visible / 4 f oculto | |
| Game over | vidas = 0 → pantalla CONTINUAR (§4) | |
| Continuaciones | 3; continúa **en el sitio** con 3 vidas, arma 1, 2 bombas y **puntuación a 0** | propuesta, ver §12 |

### 2.5 Balas enemigas (EBULLET)

Legibilidad en el LCD borroso es la prioridad:

| Parámetro | Valor | Notas |
|---|---|---|
| Gráfico | círculo de **6x6** dentro de 8x8: contorno color 3, relleno color 1 | se ve sobre fondo claro (contorno) y oscuro (relleno). Forma distinta de los disparos del jugador (rayos verticales) |
| Variante del jefe | rombo 6x6 con el mismo contraste | |
| En modo 8x16 | tile superior = bala, inferior = tile vacío compartido | **ocupa 16 líneas** para el límite de 10 por línea (§7.3) |
| Hitbox | 4x4 centrado (semitamaño 2x2) → choque si los centros están a < 4 px en ambos ejes | generosa con el jugador |
| Velocidades | lenta 1.0 (0x0100), normal 1.25 (0x0140), rápida 1.5 (0x0180), máx. 2.0 (0x0200) | nunca > 2 px/f |
| Direcciones | **32** (11.25°). `dir 0` = abajo, sentido horario en pantalla: 8 = izquierda, 16 = arriba, 24 = derecha | `vx = −v·sin θ`, `vy = v·cos θ`, θ = dir·11.25° |
| Tabla | `dir_vx[32]`, `dir_vy[32]` (8.8, v = 1.0); 1.25 = v + v>>2, 1.5 = v + v>>1, 2.0 = v<<1 | 128 bytes |
| Apuntado | `aim_dir(dx, dy)` con dx, dy con signo (8 bits) del centro del emisor al centro del jugador → dir 0..31; error ≤ 1 dir respecto a atan2 | tabla 16x16 de primer cuadrante + simetrías (§9.6) |
| Piscina | **12** | si está llena, la bala no sale (el patrón se degrada, no se rompe) |
| Apariciones por frame | máx. 7 | un abanico de 7 cabe en 1 frame |

**Patrones** (funciones del motor, §9.6):
- `AIMED(v)`: 1 bala hacia el jugador.
- `FAN(n, step, v)`: n balas en `aim ± step·(k − (n−1)/2)`, k = 0..n−1. Ej.: FAN(3, 2, 1.25) = −22.5°, 0, +22.5°.
- `SPIRAL(step, v, cada f)`: 1 bala cada `f` frames con `dir += step` (estado en el emisor).
- `RING(n, v)`: n balas repartidas en 32/n (solo M2; el tope de 12 lo limita).

### 2.6 Enemigos voladores

Reglas comunes:
- **Piscina de 6** enemigos voladores (2 sprites 8x16 cada uno, 16x16).
- Movimiento por **rutas de datos** (no código por enemigo): segmentos `(frames, vx, vy)` en 8.8, o
  "desplazamiento por tabla" (`x = x0 + tabla[t]`). El motor mueve todos en asm (§9.6).
- **Golpe:** el disparo desaparece, HP −daño, el enemigo usa la paleta OBP1 ("destello", siluetas
  claras) 2 f, SFX `HIT` (prioridad baja).
- **Muerte:** la ranura pasa a EXPLOSIÓN en el sitio 16 f (2 frames de 8 f), sin colisión; misma ranura
  y mismos 2 sprites → la explosión no gasta sprites extra. Puntos al morir.
- "Pensar" (decidir disparos, cambiar segmento) se hace en frames alternos por enemigo
  (`(i + frame) & 1`); moverse y chocar, todos los frames.
- Nunca disparan si están a menos de 32 px por encima del jugador en vertical (`Y_jug − Y_ene < 32`)
  ni en los 90 f del rugido / 60 f tras reaparecer (justicia).

| Tipo (tema) | Hitbox (semi) | HP | Puntos | Ruta | Disparo |
|---|---|---|---|---|---|
| **DART** ("Murciélago") | 12x12 (6x6) | 1 | 100 | recto hacia abajo a vy 0x0180; desde pantalla y 32, si el centro del jugador está a > 8 px en x, vx = ±0x0040 hacia él (persigue un poco) | no |
| **WAVE** ("Fuego fatuo") | 12x12 (6x6) | 1 | 150 | baja a vy 0x00C0; x = x0 + `wave_ofs[t & 127]` (seno de amplitud 24 px, periodo 128 f) | variante `f`: 1 AIMED(1.0) cuando t = 48 |
| **SWOOP** ("Gárgola") | 14x14 (7x7) | 4 | 400 | baja a vy 0x0180 hasta pantalla y ≥ 40; para 40 f; sale con vx ±0x0100 (hacia el borde más cercano), vy −0x0100 | `s`: FAN(3, 2, 1.25) a los 20 f de parar. `g`: además otra FAN(3,2,1.5) a los 36 f |
| **CARRIER** ("Globo goblin") | 14x14 (7x7) | 10 | 800 | baja a vy 0x00C0; x = x0 + `wave_ofs[(t>>1) & 127] >> 2` (balanceo ±6 px) | no; al morir suelta un ítem (P o B según el objeto del nivel) |

- Oleadas (formaciones) en §6.2: DART en columna de 3 (intervalo 13 f ≈ 20 px), WAVE en fila de 4
  por la misma ruta (intervalo 16 f), SWOOP solos o en pareja (si son 2, el segundo dispara **12 f
  después** para que sus abanicos no coincidan en las mismas líneas, §7.3), CARRIER solo.
- Vida aproximada en pantalla: DART ~100 f, WAVE ~200 f, SWOOP ~130 f, CARRIER ~200 f (lint §11).

### 2.7 Ítems

| Ítem (tema) | Origen | Movimiento | Efecto |
|---|---|---|---|
| **P** ("Pluma de fuego") | CARRIER con objeto `c` | vy 0x0080 (cae más lento que nada), x con balanceo ±8 px (tabla, periodo 64 f); se pierde por abajo | arma +1 (máx. 3); a tope 1000 pts |
| **B** ("Cuerno") | CARRIER con objeto `e` | igual | bomba +1 (máx. 4); a tope 1000 pts |

Máx. 1 ítem en pantalla (si sale otro, sustituye al anterior). Sprite 16x16 (2 sprites), parpadeo de
paleta OBP0/OBP1 cada 8 f para que destaque. Recogida: caja 12x12 del jugador contra 12x12 del ítem.

### 2.8 Torretas de tierra (TURRET, "Balista")

Dibujadas **en el fondo** (metatile 16x16), con un actor lógico invisible: **0 sprites**.

| Parámetro | Valor | Notas |
|---|---|---|
| Posición | (columna c, fila de mapa r) del `.lvl` | `X = c·16 + 8`; `Y = (uint8_t)(16 + 128 + scroll_y − r·16)` en 8 bits (válido mientras esté cerca de la pantalla) |
| Piscina | 4 lógicas | aparece al escribirse su fila en VRAM; se libera al salir por abajo (pantalla y ≥ 144) |
| HP / puntos | 6 / 500 | solo la tocan los disparos y la bomba |
| Hitbox | 14x14 (semi 7x7) | |
| Disparo | AIMED cada 96 f; el primero 40 f después de entrar | solo si pantalla y ∈ [16, 96] (no dispara desde abajo del jugador) |
| Velocidad bala | según zona: 1.0 (río), 1.25 (murallas, torres) | tabla §6.1 |
| Orientación | 3 metatiles: apuntando izq. (dir 4-11), abajo (resto), der. (dir 21-28) | cambio = redibujar 4 tiles por la cola de metatiles; como mucho 1 cambio por torreta cada 16 f |
| Golpe | SFX `HIT`; sin destello (sería redibujar tiles) | |
| Destruida | metatile → **cráter** (cola de metatiles), explosión de sprite 16 f en una de las 2 ranuras de explosión libres (si no hay, sin explosión) | |

### 2.9 Scroll y mapa vertical

| Parámetro | Valor | Notas |
|---|---|---|
| Velocidad | **0x0080 (0.5 px/f)** constante en la fase | ajustar en playtest; tabla por fase en M2 |
| Longitud | **200 filas de metatile** (3200 px) → 6400 f ≈ **107 s** | |
| Ancho | 10 metatiles = 20 tiles = 160 px; **sin scroll horizontal** (SCX = 0 salvo jefe) | |
| `scroll_y` | `uint16_t` px recorridos + subpíxel `uint8_t` | |
| SCY | `scy_shadow = (uint8_t)(SCY_BASE − scroll_y)`, escrito en el VBlank (junto al DMA de OAM) | fondo y torretas se mueven a la vez que los sprites |
| Anillo de BG | 32 filas de tiles ($9800); visibles 17 (+1 parcial) | |
| Streaming | al cruzar cada múltiplo de 8 px se prepara en `update()` la fila de tiles que entra por arriba (+1 de margen) en `row_buf[20]`; `draw_vram()` la copia en el siguiente VBlank | a 0.5 px/f: 1 fila cada 16 f |
| Garantía | scroll ≤ 8 px/f → ≤ 1 fila por frame | test de estrés a 8 px/f |
| Mapa en WRAM | anillo de **16 filas de metatile** (160 bytes) con las filas visibles, copiadas de ROM al entrar | `map_set()` (cráter, orientación de torreta) modifica el anillo y encola el redibujado si la fila está en VRAM |
| Carga inicial | 18 filas con el LCD apagado (`skip_measure = 1`); columnas 20-31 de **todas** las filas del BG a tile NIEBLA | necesario para el jefe (§2.10) |
| Objetos del nivel | lista ordenada por fila: aparecen cuando su fila entra por arriba | puntero solo hacia delante |

### 2.10 Jefe (BOSS, "Dragón de la torre")

**Dibujado en el fondo** (64x48 px = 8x6 tiles = 4x3 metatiles, 48 tiles únicos; el BG no tiene flip
en DMG). Llega con el scroll como parte del mapa, el scroll se detiene y a partir de ahí **se mueve con
SCX/SCY**: como todo lo visible del fondo es niebla lisa (color 0), mover el fondo = mover al jefe.
El HUD está en la ventana y no se mueve.

Llegada:
1. Filas 176-187 del mapa: **niebla lisa** (tile NIEBLA, color 0 uniforme; 192 px > 136 visibles).
   En la fila 180 el HUD muestra "PELIGRO" parpadeando (30/30 f) 3 s con SFX `WARN`.
2. Filas 188-193: el jefe (metatiles 4x3 en columnas 3-6 de las filas 189-191, resto niebla).
3. Cuando el borde superior del jefe llega a pantalla y = 16 (`@ stop_row` del `.lvl`), velocidad de
   scroll = 0. Desde entonces `SCY = scy_parada + boss_dy`, `SCX = (uint8_t)(−boss_dx)`.
4. Barra de vida del jefe aparece en el HUD (§5).

Posición en pantalla para colisiones (8 bits): `boss_X = BOSS_X0 + boss_dx`, `boss_Y = BOSS_Y0 + boss_dy`
(BOSS_X0 = 48 + 8, BOSS_Y0 = 16 + 16 en coordenadas OAM).

| Parámetro | Valor | Notas |
|---|---|---|
| HP | **200** | nivel 2 de arma ≈ 15 HP/s → ~14 s de impactos puros, ~30-45 s reales; ajustar en playtest |
| Hitbox (cuerpo, recibe disparos y mata por contacto) | 56x32 en (4,8) del jefe (semi 28x16) | |
| Emisores (relativos a la esquina del jefe) | boca (32, 40), cañón izq. (8, 36), cañón der. (56, 36) | |
| Golpe | disparo desaparece; SFX `BOSS_HIT` como mucho cada 8 f; destello: paleta del BG **por debajo de la línea de corte** a "clara" 2 f, como mucho cada 8 f | requiere `bgp_below` en gbe_video (§9.6) |
| `boss_dx` | −40..+40 | `boss_dx = sin_tab[t·k]` amplitud 40 |
| `boss_dy` | 0..+24 | solo en la embestida |

Fases (por tabla, `boss_phase` global):

| Fase | HP | Movimiento | Ataques |
|---|---|---|---|
| A | 200-101 | vaivén en x, periodo 256 f | cada 72 f: FAN(5, 2, 1.25) desde la boca, apuntado. Cada 128 f (desfase 36 f): AIMED(1.5) desde cada cañón |
| Transición | al bajar de 101 | quieto 32 f, destello cada 4 f, rugido SFX; borra balas | |
| B | 100-1 | vaivén periodo 160 f; ciclo de 240 f | f 0-95: SPIRAL(step 5, 1.0, cada 8 f) desde la boca (12 balas). f 96-143: descanso. f 144-167: embestida `boss_dy` 0→24 (1 px/f) con FAN(7, 2, 1.25) al llegar abajo; f 168-215: vuelve `boss_dy` 24→0 (0.5 px/f) |
| Muerte | 0 | parado, temblor | 150 f: explosión de sprite cada 8 f en puntos pseudoaleatorios del cuerpo (2 ranuras de explosión); destello cada 16 f; borra balas. Después: 6 filas del jefe → niebla (1 fila de 20 tiles por frame, 6 f), 60 f, el jugador sube solo a 1.5 px/f hasta salir → CLEAR |

### 2.11 Puntuación

| Evento | Puntos |
|---|---|
| DART / WAVE / SWOOP / CARRIER | 100 / 150 / 400 / 800 |
| TURRET | 500 |
| Jefe | 20 000 |
| Bala borrada por bomba | 10 |
| Ítem con el contador al máximo | 1000 |
| Al acabar la fase: bombas restantes | 2000 cada una |
| Al acabar la fase sin morir | 10 000 |

- 6 dígitos BCD (`bcd.s`, `bcd_add3`), tope 999999. Récord en RAM en M1 (SRAM: §12).
- Sin cadenas ni multiplicadores en M1 (opción de M3, §12).

---

## 3. Controles

| Botón | En juego | En menús / pantallas |
|---|---|---|
| Cruceta | mover en 8 direcciones | — (sin menús con opciones en M1) |
| A | mantener = autodisparo cada 8 f | confirmar / empezar |
| B | bomba (flanco) | — |
| Start | pausa / reanudar | empezar en TITLE; continuar en CONTINUAR; saltar espera en CLEAR |
| Select | nada | nada |

Sin combinaciones de 3 botones. A mantenido + B (bomba mientras disparas) es el uso normal.

---

## 4. Pantallas y flujo

```
BOOT -> TITLE --Start/A--> PLAY (banner "FASE 1" 120 f en el HUD) <--Start--> PAUSE
                             |                       |
                       vidas = 0                 jefe muerto
                             v                       v
                         CONTINUAR (10 s)         CLEAR (bonos; 300 f o Start)
                        Start |    tiempo 0           |
                         PLAY  v                      v
                            GAMEOVER (180 f) -> TITLE  TITLE (M1; M2: fase 2)
```

`state` (global u8): `TITLE=0, PLAY=1, PAUSE=2, CONTINUE=3, GAMEOVER=4, CLEAR=5`. Dentro de PLAY,
`play_sub`: `0 NORMAL, 1 DYING, 2 RESPAWN, 3 BOSS_INTRO, 4 BOSS, 5 BOSS_DEAD, 6 OUTRO`.

| Pantalla | Contenido | Notas |
|---|---|---|
| TITLE | Logo GRIFO (M1: texto grande con la fuente; logo de tiles en M3), "PULSA START" parpadeando 30/30 f, "RECORD 000000" | `.screen`, LCD apagado |
| PLAY | Mapa + HUD en ventana | al empezar, la fila del HUD muestra "FASE 1" 120 f y luego los contadores |
| PAUSE | todo congelado; la fila del HUD muestra "PAUSA" centrado; sonido silenciado | al reanudar se restaura el HUD (≤ 20 tiles por la cola del HUD) |
| CONTINUAR | "CONTINUAR" + cuenta 9→0 (1 cada 60 f) + "QUEDAN 3" | Start continúa en el sitio (§2.4) |
| GAMEOVER | "FIN DEL JUEGO" + puntuación | 180 f o Start → TITLE; actualiza récord |
| CLEAR | "FASE COMPLETADA", "BOMBAS 2 X 2000", "SIN MORIR 10000", total | cuenta animada de bonos (+100/f, tic cada 4 f); actualiza récord |

Transiciones: fundido BGP 4 pasos x 4 f → `screen_build` con LCD apagado → fundido de entrada
(`gbe_screen`, ya existe). Textos en español sin tildes ni Ñ (todos los de arriba lo cumplen). Las
maquetas `.screen` las hace el ui-designer a partir de este documento.

---

## 5. HUD e interfaz

**Propuesta (recomendada): 1 fila arriba en la ventana**, cortada con la interrupción LYC que ya hace
`gbe_video` (`video_init(7, ...)`): el usuario prefirió el HUD arriba en CABALLERITO. Ventaja extra en un
shmup: los sprites están apagados en las líneas 0-7, así que los enemigos **salen de debajo del HUD**
sin que haga falta recortarlos. Deja 136 px de alto de juego (2 filas de HUD dejarían 128).

```
col: 0         1
     01234567890123456789
r0:  000000 v3 b2 P1 ....     v = icono vidas, b = icono bomba, P = icono pluma (nivel de arma)
                              cols 16-19: barra de vida del jefe (solo en BOSS)
```

- Ventana: mapa en **$9C00** (el BG usa las 32 filas de $9800 como anillo), `WY = 0`, `WX = 7`.
- Barra del jefe: 4 tiles = 32 px; 9 tiles de relleno (0..8 px). 200 HP / 32 px → 1 px = 6.25 HP
  (`px = (hp·41) >> 8`, sin divisiones).
- Textos de la fila: "FASE 1", "PELIGRO" (parpadeo 30/30 f), "PAUSA" sustituyen la fila entera y se
  restauran después.
- Actualización: `update()` convierte a tiles en `hud_buf[20]` y marca columnas sucias; `draw_vram()`
  copia **≤ 20 tiles por frame** (normalmente 1-6).
- Alternativas (§12): 2 filas arriba como CABALLERITO, o panel lateral derecho de 4 columnas (ventana
  desde WX = 135 sin interrupción, juego de 128x144, pero los sprites se dibujan **encima** de la
  ventana: obligaría a no dejar entrar objetos en x ≥ 128).

---

## 6. Progresión y dificultad

### 6.1 Zonas de la fase 1 (parámetros en tabla, no código especial)

| Filas | Zona | Tiempo (s) | Bala torreta | Bala SWOOP | Densidad | Novedad |
|---|---|---|---|---|---|---|
| 0-11 | Pradera | 0-2 | — | — | nada | "FASE 1"; moverse |
| 12-40 | Bosque | 2-17 | — | — | 1 oleada / ~3 s, sin balas | DART, WAVE, primer CARRIER (P) |
| 41-80 | Río | 17-39 | 1.0 | 1.25 | + torretas en las orillas | balas apuntadas, WAVE `f`, SWOOP |
| 81-130 | Murallas | 39-66 | 1.25 | 1.25 | torretas en almenas, 2 oleadas solapadas | parejas de SWOOP, CARRIER (B) |
| 131-175 | Torres | 66-90 | 1.25 | 1.5 | **pico**: 6 voladores + 4 torretas | SWOOP `g`, prueba de estrés (§11) |
| 176-187 | Niebla | 90-97 | — | — | 2 columnas de DART | "PELIGRO" en fila 180 |
| 188-199 | Jefe | 97- | — | — | jefe | scroll se para en `stop_row` |

Tiempo ≈ fila × 0.536 s (16 px por fila a 0.5 px/f) menos ~4.5 s (la fila aparece por arriba).

### 6.2 Guion de oleadas (M1, primera versión; el `.lvl` es la fuente de verdad)

Letras de objeto en el `.lvl`: `d` DART x3 · `w` WAVE x4 sin disparo · `f` WAVE x4 con disparo ·
`s` SWOOP · `g` SWOOP doble ráfaga · `c` CARRIER con P · `e` CARRIER con B · `t` TURRET.
WAVE en columna ≤ 4 entra por la izquierda de su seno, ≥ 5 por la derecha (fase del seno invertida).

| Fila | Objetos (columna) | Fila | Objetos (columna) |
|---|---|---|---|
| 12 | d(2) | 100 | t(0) t(9) |
| 18 | d(7) | 104 | f(1) |
| 22 | w(1) | 110 | c(4) |
| 29 | w(8) | 116 | t(2) t(7) |
| 36 | d(2) d(7) | 118 | d(3) |
| 40 | c(4) | 124 | f(8) |
| 48 | t(1) | 132 | d(2) |
| 52 | t(8) f(2) | 136 | t(1) t(8) g(4) |
| 60 | t(2) t(7) | 142 | f(1) |
| 66 | s(5) | 148 | t(0) t(9) |
| 72 | d(1) d(8) | 150 | g(2) g(7) f(8) (pico) |
| 78 | e(4) | 160 | c(3) |
| 84 | t(1) t(8) w(5) | 164 | e(6) |
| 92 | t(4) f(1) | 168 | t(2) t(7) s(5) |
| 96 | g(2) g(7) | 180, 184 | d(2), d(7) |

Comprobado a mano con las vidas de §2.6 (1 fila = 32 f): nunca más de 6 voladores ni 4 torretas
(una torreta vive ~9.5 filas en pantalla). Si al implementar se cambia una vida o una ruta, el lint lo
vuelve a comprobar.

Reglas de diseño de oleadas (las comprueba el lint, §11):
- ≤ 6 voladores vivos a la vez y ≤ 4 torretas (simulación con las vidas de §2.6).
- ≤ 3 voladores en la misma banda de 16 px en el momento de aparecer; formaciones horizontales ≤ 3.
- Dos SWOOP de la misma fila disparan con 12 f de desfase.
- ≥ 9 filas de niebla lisa antes del jefe; columnas del jefe dentro de 3-6.
- Toda torreta sobre un metatile de suelo válido (no agua, no niebla).

### 6.3 M2 en adelante
Vuelta 2 (al acabar la fase, si se aprueba): balas +0.25 px/f, intervalos de disparo ×0.75, DART
disparan. O fases nuevas con tilesets propios (decidir tras el playtest de M1).

---

## 7. Contenido y assets

Modo de sprites **8x16** (LCDC bit 2 = 1). Objetos de 8x8 (balas) usan un par con el tile inferior vacío.

### 7.1 Tiles de sprite

| Asset | Tiles | Frames | Notas |
|---|---|---|---|
| Jugador | 12 | NORMAL, BANK_L, BANK_R | BANK_R podría ser flip de BANK_L si el diseño es simétrico (−4) |
| Explosión del jugador | 12 | 3 | |
| Disparos del jugador | 6 | rayo, rayo doble, lateral (par 8x16 con mitad vacía) | lateral derecho = flip X |
| Balas enemigas | 4 | círculo, rombo + tile vacío compartido | |
| DART, WAVE, SWOOP, CARRIER | 32 | 2 c/u (aleteo cada 8 f) | |
| Explosión 16x16 | 8 | 2 | voladores, torretas y jefe |
| Ítems P, B | 8 | 1 c/u | |
| **Total** | **82** | | privados $8000-$87FF (0-127) |

### 7.2 Tiles de fondo / ventana

| Asset | Tiles | Notas |
|---|---|---|
| Fuente compartida | 37 | `harness/common/font.tiles` |
| Iconos HUD (vida, bomba, pluma) + barra (9) | 12 | |
| Tileset de la fase (pradera, bosque, río, murallas, torres, transiciones) | ≤ 110 | colores 0-2 sobre todo; color 3 escaso (que actores y balas destaquen) |
| Torreta (3 orientaciones) + cráter | 16 | 4 metatiles |
| NIEBLA (color 0 liso) | 1 | |
| Jefe | 48 | 8x6 únicos |
| **Total BG** | **~224** | BG direccionado a $8800 (LCDC bit 4 = 0): 0-127 en $9000 + 128-255 en $8800 |

**Total VRAM:** 82 + ~224 = **~306 / 384**. Los tiles 128-255 de $8800 los usa solo el fondo (los
sprites caben en 0-127). Metatiles: ≤ 64 (`mt_tiles[64][4]` + `mt_attr[64]`).

### 7.3 Sprites: OAM y gestor de parpadeo

OAM se reconstruye entero cada frame en **grupos por prioridad**. El DMG dibuja en cada línea los 10
primeros sprites **por orden de OAM**: el orden de los grupos es la prioridad, y dentro de cada grupo
el orden **rota** cada frame (`spr_rot`), así que si una línea se pasa de 10, lo que se pierde es lo
menos importante y nunca lo mismo dos frames seguidos.

| OAM | Grupo | Sprites | Parpadeo |
|---|---|---|---|
| 0-1 | Jugador | 2 | **nunca** (siempre primero) |
| 2-13 | Balas enemigas | 12 | rotan entre sí (lo último que debe perderse: una bala invisible mata) |
| 14-25 | Enemigos voladores (y sus explosiones) | 6 x 2 | rotan por enemigo (los 2 sprites juntos) |
| 26-27 | Ítem | 2 | |
| 28-35 | Disparos del jugador | 8 | rotan; son lo primero que se pierde (el jugador apenas lo nota) |
| 36-39 | Explosiones extra (torretas, jefe) | 2 x 2 | las últimas |
| **Total** | | **40 / 40** | ranuras libres con Y = 0 |

**Sprites por línea (líneas 8-143).** Cada sprite 8x16 cuenta en 16 líneas, **también las balas**
(su mitad inferior es transparente pero ocupa). Peores casos de diseño:

| Momento | Jugador | Disparos | Enemigos | Balas | Total | Qué parpadea |
|---|---|---|---|---|---|---|
| Normal (bosque/río) | 2 | ≤ 3 | ≤ 2 x 2 | ≤ 2 | ≤ 11 | a veces 1 disparo |
| Pico Torres (fila 150): 2 SWOOP parados en la misma banda disparando FAN(3) | 0-2 | ≤ 3 | 4 + 1 WAVE 2 | 3 (+3 del segundo, 12 f después y ya 15 px más abajo) | 12-14 | disparos del jugador; con jugador en la banda, también 1 enemigo |
| Jefe, FAN(7) saliendo de la boca | 0-2 | ≤ 3 | 0 (jefe en BG) | 7 | ≤ 12 | disparos; balas nunca (2 + 7 < 10) |
| Bomba / muerte | — | — | — | 0 | — | — |

Objetivo medido (§11): jugador nunca perdido; balas enemigas nunca ocultas 2 frames seguidos;
líneas > 10 en ≤ 25 % de los frames del bot de la fase completa.

---

## 8. Sonido

M1: **solo efectos** por registros (`gbe_sfx`, prioridad por canal). Música en M2 (hUGEDriver, requiere
bancos).

| Efecto | Canal | Prioridad | Notas |
|---|---|---|---|
| `SHOT` disparo | 2 | 0 | 4 f, pulso agudo corto; se repite cada 8 f, no debe cansar (volumen bajo) |
| `HIT` impacto en enemigo/torreta | 4 | 1 | ruido muy corto |
| `BOOM` enemigo destruido | 4 | 2 | |
| `BIG_BOOM` torreta/jefe/jugador | 4 | 3 | largo |
| `ITEM` coger P/B | 1 | 2 | arpegio subiendo |
| `POWER` arma +1 | 1 | 3 | |
| `BOMB` rugido | 1 + 4 | 3 | sweep bajando + ruido |
| `DEATH` | 1 | 3 | sweep bajando largo |
| `EXTEND` vida extra | 1 | 3 | |
| `WARN` "PELIGRO" | 2 | 3 | dos tonos alternos cada 15 f, 3 s |
| `BOSS_HIT` | 4 | 1 | máx. 1 cada 8 f |
| `PAUSE`, `START`, `TICK` (cuenta de bonos) | 1 | 3 / 3 / 1 | |

Con música (M2): `SHOT` en el canal 2 robaría la melodía cada 8 f → pasar `SHOT` al canal 4 o
silenciarlo con música (decidir en M2).

---

## 9. Técnica

### 9.1 Cartucho

| Parte | M1 |
|---|---|
| Código C + asm (motor gbe + juego) | 16-20 KB |
| Tiles (82 + 224) x 16 B | 4.9 KB |
| Mapa de la fase (200 filas x 10) + objetos | 2.2 KB |
| Tablas (velocidades por dirección 128 B, atan 256 B, senos 256 B, rutas ~300 B) | ~1 KB |
| Pantallas (`.screen` 360 B c/u x 4) | 1.4 KB |
| Efectos | 0.3 KB |
| **Total** | **~26-30 KB** |

**MBC5 + RAM + batería (0x1B) desde M1**, enlazado plano < 32 KB (sin `SWITCH_ROM`), igual que
CABALLERITO: `["-Wm-yt0x1B", "-Wm-yo4", "-Wm-ya1"]`. M1 roza los 32 KB y la música no cabe: la tarea
pendiente de bancos (CLAUDE.md) es **bloqueante para M2**. Batería: récord en SRAM si se aprueba (§12);
si no, MBC5 sin RAM (0x19).

RAM (WRAM 8 KB): piscinas (8 disparos + 12 balas + 6 enemigos + 4 torretas + 1 ítem + 2 explosiones =
33 objetos x ~10 B) ~330 B; anillo del mapa 160 B; `row_buf` 20 + `hud_buf` 20 + cola de metatiles
4 x 6; shadow OAM 160; estado ~200 → **~1 KB / 8 KB**. HRAM: punteros del bucle asm si el perfil lo pide.

### 9.2 Presupuesto de VBlank (peor frame)

`vsync()` vuelve en LY ≈ 146 → **~3600 T** para `draw_vram()`.

| Trabajo | Tiles | Coste |
|---|---|---|
| SCX/SCY/BGP/OBP (ISR de VBlank de gbe_video) | — | ~60 T |
| Fila de streaming: 20 tiles **contiguos** en el mapa (stride 1): `ld a,(hl+) / ld (de),a / inc e` desenrollado = 20 T/tile | 20 | ~500 T con llamada |
| Cola de metatiles (torretas/cráteres): máx. 2 x 4 tiles, ~40 T/tile | 8 | ~450 T |
| HUD: máx. 20 tiles (normal 1-6), copia asm 20 T/tile | 20 | ~500 T |
| Borrado del jefe (6 filas, 1 por frame; sin streaming porque el scroll está parado) | (20) | (excluyente con la fila) |
| **Total peor caso** | **48** | **~1500 T (42 % de 3600)** |

- A 0.5 px/f: 1 fila cada 16 f. A 8 px/f (test de estrés): 1 fila por frame, sigue cabiendo.
- Todo se prepara en `update()`; en VBlank solo se copia. Prohibido `set_bkg_tiles` en juego.
- `vram_late` debe ser 0 en todos los tests.

### 9.3 Presupuesto de CPU (fuera de VBlank), momento pico (Torres, piscinas llenas)

| Trabajo | Cómo | Coste |
|---|---|---|
| Input, jugador, disparo | C, 8 bits | ~1500 T |
| Mover 26 objetos (8 disparos + 12 balas + 6 enemigos) + matar al salir | **asm** `pool_move` ~120 T/objeto | ~3100 T |
| IA de 6 voladores (rutas, disparo) | C, medio ritmo para "pensar" | ~5400 T |
| 4 torretas (y desde el scroll, apuntar, disparar) | C | ~2400 T |
| Colisiones: disparos x enemigos (8x6), disparos x torretas (8x4), balas x jugador (12), enemigos x jugador (6), ítem | **asm** `hit_first` ~40 T por par, salida temprana por y | ~4000 T |
| Crear balas (abanico de 7 con `aim_dir`) | asm `aim_dir` + C | ~1500 T |
| Construir OAM (40 sprites, grupos + rotación) | **asm** `spr_build` | ~2500 T |
| Preparar fila (10 metatiles → 20 tiles), cada 16 f | asm | ~600 T |
| HUD a tiles (solo si cambia), oleadas, SFX | C | ~1200 T |
| **Total** | | **~22 000 T ≈ 49 líneas** |

Objetivo de test: **`max_frame_lines < 120`** (CLAUDE.md). En C puro (sin `pool_move`, `hit_first`,
`spr_build` en asm) saldrían ~26 x 1500 T de movimiento + ~15 000 T de colisiones: **no cabe**. Por eso
esas tres rutinas son trabajo de motor **antes** de la lógica del juego (§10), cada una con su
referencia en C y su caso en `gbe_selftest`. La regla de 8 bits en espacio de pantalla viene de
games/platformer (5 enemigos: de 150 a ~100 líneas solo por eso).

### 9.4 Riesgos técnicos y mitigación

| Riesgo | Mitigación |
|---|---|
| CPU con 33 objetos | 8 bits en pantalla; asm para mover, chocar y OAM; "pensar" a medio ritmo; perfil `gb.profile` por función |
| Parpadeo ilegible en el LCD borroso | prioridades (§7.3), reglas de oleadas en el lint, tope de 12 balas, desfase de abanicos; playtest en hardware |
| Balas 8x16 ocupan 16 líneas | contado en el presupuesto; si molesta, M3: balas dobles (2 balas en un sprite) en patrones fijos |
| Jefe en BG: cualquier detalle del fondo visible se movería con él | niebla lisa ≥ 9 filas + columnas 20-31 a niebla (lint); el temblor de la bomba lo mueve también (aceptado) |
| Destello del jefe cambiando BGP a mitad de frame (en la ISR de la línea 7) | PyBoy no prueba timing real → hardware (M4); plan B: destellar solo con sprites de explosión |
| Errores de anillo/filas (fila equivocada, desfase de 1) | test VRAM == mapa en cada frame del recorrido entero y a 8 px/f |
| Torretas desincronizadas del fondo | `Y` calculada desde `scroll_y` cada frame (no acumulada); test que compara su `Y` con la fila en VRAM |
| ROM al límite de 32 KB plano | MBC5 en cabecera desde M1; bancos antes de M2 (tarea del arnés) |
| ISR LYC en hardware real | ya probada en CABALLERITO; plan B HUD sin ISR (§12) |

### 9.5 Globales para tests (no `static`)

`state`, `play_sub`, `scroll_y` (u16), `scroll_speed` (u16 8.8), `scy_shadow`, `scx_shadow`,
`rows_written`, `player_x`, `player_y`, `player_inv`, `power` (1-3), `bombs`, `lives`, `continues`,
`score` (BCD 3 B), `hiscore`, `shot_x[]`, `shot_y[]`, `shot_t[]`, `eb_x[]`, `eb_y[]`, `eb_vx[]`,
`eb_vy[]`, `eb_t[]`, `en_type[]`, `en_x[]`, `en_y[]`, `en_hp[]`, `en_state[]`, `gt_x[]`, `gt_y[]`,
`gt_hp[]` (torretas), `item_type`, `item_x`, `item_y`, `boss_hp`, `boss_phase`, `boss_dx`, `boss_dy`,
`obj_ptr` (puntero de objetos del nivel), `spr_rot`, `map_ring[]`, `vram_late`, `max_frame_lines`,
`skip_measure`, `cheat_flags` (bit 0 invencible, bit 1 bombas infinitas, bit 2 congelar objetos
—solo se reconstruye OAM—, bit 3 velocidad de scroll forzada a `cheat_scroll`; solo los escriben los tests).

### 9.6 Qué reutiliza de gbe y qué le falta (trabajo de motor en `harness/common`)

**Reutiliza tal cual:** `gbe_frame` (bucle, input, `max_frame_lines`, `vram_late`), `gbe_video` (corte
LYC del HUD en la línea 7, fundidos), `gbe_screen` (transiciones), `gbe_sfx`, `bcd.s`, fuente
compartida, `harness/screens.py`. **No usa** `gbe_map` (horizontal) ni `gbe_actors` (x de 16 bits):
quedan como están; las piezas nuevas son sus equivalentes verticales / de 8 bits.

Piezas nuevas, genéricas (cada asm con referencia C + caso en `gbe_selftest`):

| # | Pieza | Qué hace | Por qué |
|---|---|---|---|
| E1 | `gbe_vmap` (+ `.s`) | mapa vertical de metatiles: filas de ancho fijo (10) en ROM, anillo de N filas en WRAM, `vmap_load`, `vmap_scroll(speed)` con `scroll_y` 16 bits, preparación de fila (10 mt → 20 tiles, asm), copia `vram_row20` contigua, `vmap_set(col,row,mt)` con cola de redibujado, aviso de "fila nueva" para aparecer objetos, parada de scroll | el motor solo tiene scroll horizontal por columnas |
| E2 | `gbe_video`: `scy_shadow`, `bgp_below` y temblor | SCY escrito en el VBlank con SCX; paleta BG distinta por debajo de la línea de corte (la ISR LYC la escribe); `shake_x/shake_y` sumados a los shadows | scroll vertical, destello del jefe sin destellar el HUD, temblor sin tocar la lógica |
| E3 | `gbe_pool` (+ `.s`) | piscinas de objetos en 8 bits (struct of arrays: X, Xs, Y, Ys, vx, vy, tipo, estado, timer), `pool_alloc(first, n)`, `pool_move(first, n)` asm que suma 8.8 y libera al salir (`X ≥ 168 || Y ≥ 176`) | `gbe_actors` usa x de 16 bits y 240 T por objeto |
| E4 | `gbe_spr` (+ `.s`) | gestor de OAM: grupos con rango fijo y prioridad, rotación por grupo (`spr_rot`), objetos de 1 sprite (8x8 en 8x16) y 2 sprites (16x16), ocultos con Y = 0, `spr_build()` asm desde las piscinas | más de 10 sprites por línea con parpadeo controlado |
| E5 | `gbe_hit` (+ `.s`) | `hit_first(cx, cy, hw, hh, first, n)` → índice del primer objeto de la piscina que solapa (o 0xFF), con salida temprana por y; variante caja-contra-piscina para disparos x enemigos | colisión de muchos pares en < 50 T por par |
| E6 | `gbe_aim` (+ `.s`) | `aim_dir(dx, dy)` → 0..31, `dir_vx/dir_vy`, escalado de velocidad por desplazamientos, patrones `fire_aimed`, `fire_fan`, `fire_spiral` (estado en el emisor), `fire_ring` (M2) sobre la piscina de balas | patrones de balas |
| E7 | `gbe_wave` | oleadas: objetos del nivel por fila → formaciones (cuántos, intervalo en f, desfases x, ruta); intérprete de rutas por segmentos `(f, vx, vy)` y por tabla `x0 + tab[t]`; máx. 1 aparición por frame (regla de games/platformer) | aparición de enemigos guionizada y testeable |
| E8 | `harness/levels.py` | `"order": "rows"` (fila-mayor, de abajo arriba, objetos ordenados por fila) y `object_cell` **por objeto** (la `t` deja una torreta en el mapa) | el formato actual es por columnas con celda de objeto única |
| E9 | `harness/gbtest.py` | `gb.oam()` (40 entradas), `gb.line_sprites(first=8, last=143)` → por línea: sprites pedidos y cuáles **dibuja de verdad** el DMG (10 primeros por orden OAM, alto 8/16 según LCDC), `gb.bg_rows()` para comparar el anillo de VRAM | medir parpadeo y streaming desde los tests |
| E10 | `gbe_tiles` (M3, opcional) | cola de tiles de 16 B copiados en VBlank con presupuesto (p. ej. 4 tiles/frame) | cargar tiles del jefe durante la niebla en fases futuras; en M1 todo cabe precargado |
| E11 | Banking (tarea ya pendiente) | código fijo en banco 0, datos en bancos | bloqueante para la música (M2) |

---

## 10. Hitos

- **M1a — motor (antes de la lógica del juego):** E1-E9 con referencias C, `gbe_selftest` ampliado,
  README de `harness/common` actualizado; demo mínima en `games/shmup`: scroll vertical del mapa de
  prueba + 33 objetos moviéndose y chocando + OAM con rotación, midiendo `max_frame_lines`.
- **M1b — slice jugable (fase 1 completa, arte provisional):** jugador, 3 niveles de arma, bomba,
  vidas/reaparición/continuaciones, DART/WAVE/SWOOP/CARRIER, torretas en BG, ítems, guion de oleadas
  de §6.2, jefe en BG con 2 fases y muerte, HUD de 1 fila, TITLE/PAUSE/CONTINUAR/GAMEOVER/CLEAR,
  efectos de sonido, récord en RAM, tests de §11.
- **Antes de M2 — bancos de ROM** (tarea del arnés, E11).
- **M2 — música y guardado:** hUGEDriver (título, fase, jefe, clear, game over), récord en SRAM si se
  aprueba, `SHOT` sin pisar la melodía.
- **M3 — contenido y pulido:** vuelta 2 o fase 2 (tileset propio, `gbe_tiles` para su jefe), logo de
  título, cadenas de puntuación (si se aprueban), opciones/satélites (si se aprueban), explosiones más
  ricas.
- **M4 — hardware real:** flash cart; parpadeo y ghosting de balas, ISR LYC con `bgp_below`, audio.

---

## 11. Plan de pruebas

Todos los bots usan `gb.run_bot` con **progreso** = `scroll_y + (200 − boss_hp)` (crece en la fase y
en el jefe) y `done` = `state == CLEAR`; un bot que no avanza no vale como medida.

| Qué | Cómo |
|---|---|
| Autoprueba del motor | `gb.selftest()` → 0 discrepancias en `pool_move`, `hit_first`, `aim_dir`, fila 10→20, `spr_build`, `vram_row20` |
| Movimiento 8 direcciones y límites | test: mantener cada dirección N f → desplazamiento = N·1.5 (recto) / N·1.06 (diagonal) ±1; contra los bordes no pasa de 8..152 / 32..144 |
| Autodisparo y niveles | test: A mantenido 64 f → 8 ráfagas; `power` 1/2/3 → sprites por ráfaga 1/1/3 (laterales cada 16 f); piscina llena no crea más |
| Núcleo del jugador | test con `write_u8`: bala a dx = 3 → muere; dx = 4 → no (ambos ejes) |
| Bomba | test: 12 balas en pantalla, B → `eb_t[]` todas libres, score +120, enemigos −8 HP, `player_inv = 90`, `bombs − 1`; segunda B durante 90 f no hace nada |
| Muerte, reaparición, continuaciones | test: forzar choque → `play_sub` DYING → RESPAWN; `power − 1`, `bombs ≥ 2`, `player_inv = 120`; con `lives = 1` → CONTINUE; Start → 3 vidas y `score = 0` |
| Vidas extra | test: `score` = 19 990, matar DART → `lives + 1`; no se repite |
| `aim_dir` | test Python: para dx, dy en −64..64 (paso 4) leer el resultado de la ROM (vía selftest o variable de depuración) y comparar con `round(atan2)` → error ≤ 1 dir |
| Patrones | test: FAN(5,2) → 5 balas nuevas con dirs `d−4, d−2, d, d+2, d+4`; SPIRAL suma `step` por bala; piscina llena → no crea y no corrompe |
| Enemigos | tests por tipo con el nivel congelado: ruta (posición tras N f), HP, puntos, ítem del CARRIER según `c`/`e`, SWOOP dispara a los 20 f de parar, no disparan a < 32 px del jugador |
| Torretas | test: su `Y` = fórmula de §2.8 en cada frame y coincide con la fila de VRAM donde está su metatile; al morir el anillo y la VRAM tienen el cráter |
| **Streaming vertical correcto** | bot a velocidad normal y test con `cheat_scroll` a 4 y 8 px/f: cada frame, las 18 filas visibles del BG ($9800, vía `gb.bg_rows()`) == mapa ROM / anillo + `mt_tiles`; columnas 20-31 = NIEBLA; `vram_late == 0` |
| **Sprites por línea y parpadeo** | bot de la fase completa: cada frame `gb.line_sprites()` → (a) los 2 sprites del jugador se dibujan siempre; (b) ninguna bala enemiga sin dibujar 2 frames seguidos; (c) frames con alguna línea > 10 ≤ 25 %. Test determinista: `cheat_flags` congelar + 14 balas en la misma línea → la unión de 2 frames consecutivos contiene las 14 |
| Jefe | test: forzar `scroll_y` a la parada → velocidad 0, `SCX = −boss_dx`, `SCY` según `boss_dy`; hitbox en pantalla = BOSS_X0 + boss_dx; `boss_hp` 101 → 100 cambia `boss_phase`; muerte → filas del jefe = NIEBLA en VRAM y `state` CLEAR tras el outro |
| **Presupuesto de frame** | bot de fase completa (+ jefe, ~10 000 f) con `cheat_flags` invencible, autodisparo y vaivén horizontal: `max_frame_lines < 120`, `vram_late == 0`; perfil (`gb.profile`) de `pool_move`, `hit_first`, `spr_build`, `update`, `draw_vram` en la fila 150 (pico) |
| Bot "justo" (informativo) | sin trampas, esquiva la bala más cercana por encima: muertes y fila alcanzada se imprimen (guía para el playtest, no assert) |
| Lint del nivel (Python puro) | sobre `res/stage1.lvl`: 10 de ancho, ≤ 6 voladores / ≤ 4 torretas simultáneos (simulación con vidas de §2.6), ≤ 3 en una banda al aparecer, ≥ 9 filas de niebla lisa antes del jefe, jefe en columnas 3-6, torretas sobre suelo, `stop_row` coherente |
| Flujo de pantallas | test: TITLE → PLAY → PAUSE (HUD "PAUSA", lógica congelada) → GAMEOVER/CLEAR → TITLE; récord actualizado |
| Capturas | `gb.screenshot` en inicio, pico de Torres, jefe fase B, rugido → revisión visual con Read |
| **Playtest humano** | sensación de velocidad del jugador y del scroll, legibilidad de las balas en LCD borroso, cuánto molesta el parpadeo, dificultad (objetivo: un jugador medio llega al jefe con 1-2 vidas perdidas), duración del jefe, volumen de `SHOT` |

---

## 12. Decisiones pendientes (para el usuario)

1. **Tema y título**
   - a) **GRIFO** — caballero a lomos de un grifo contra las criaturas de un dragón (murciélagos,
     fuegos fatuos, gárgolas, globos goblin, balistas; jefe: dragón de la torre). Sigue el mundo de
     fantasía de CABALLERITO y da terreno variado (bosque, río, murallas) que estresa el streaming.
   - b) **ESTELA** — caza espacial sobre una luna minera (drones, minas, torretas; jefe: nave nodriza).
     El clásico del género, siluetas muy legibles, pero fondo más vacío.
   - c) **AVISPA** — una avispa defiende un jardín (moscas, escarabajos, flores-torreta; jefe: araña).
     Tono simpático.
   - **Recomendación: a) GRIFO.**
2. **HUD**: a) **1 fila arriba con el corte LYC** (recomendado: 136 px de juego, enemigos que salen de
   debajo del HUD, reutiliza gbe_video); b) 2 filas arriba como CABALLERITO (128 px de juego);
   c) panel lateral derecho sin interrupción (128x144, pero hay que impedir que los sprites entren en él).
3. **Al morir, el arma**: a) **baja 1 nivel** (recomendado, suave); b) vuelve a nivel 1 (clásico duro);
   c) se conserva.
4. **Continuaciones**: a) **3, en el sitio, puntuación a 0** (recomendado); b) infinitas; c) ninguna
   (arcade puro: game over = título).
5. **Bomba**: a) **sí, 2 por vida, máx. 4** (recomendado); b) sin bomba, con escudo de 1 golpe al coger
   un ítem; c) bomba que se recarga sola cada 30 s.
6. **Récord guardado en SRAM** (M2): a) **sí** (recomendado; MBC5 + RAM + batería desde M1);
   b) no (MBC5 sin RAM).
7. **Puntuación con cadena** (M3): a) **no, puntuación simple** (recomendado para M1); b) bonus por
   destruir una oleada entera (x2 al último); c) multiplicador que sube matando sin fallar disparos.
8. **Velocidad de scroll**: a) **0.5 px/f** (recomendado, terreno legible, fase de 107 s);
   b) 0.75 px/f (fase de 300 filas para la misma duración: más mapa y ROM); c) 1.0 px/f (más
   sensación de velocidad, 400 filas).
9. **Después de M1**: a) vuelta 2 más difícil (barato); b) **fase 2 nueva** con tileset y jefe propios
   (recomendado si el motor sale bien: es lo que más estresa el arnés: `gbe_tiles`, bancos);
   c) satélites/opciones para el jugador.
