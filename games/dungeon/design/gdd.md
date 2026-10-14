# TORRE HUNDIDA — Documento de diseño

Estado: aprobado (2026-10-14)    Versión: 1.0    Autor: game-designer

> Carpeta `games/dungeon`. Dungeon crawler en primera persona por casillas para DMG (mover una
> casilla, girar 90°, vista pseudo-3D compuesta con piezas). **Doble objetivo:** un juego pequeño y
> pulido, y **ampliar el arnés** con lo que aún le falta: **bancos de ROM** (ya en el arnés para assets;
> aquí se usan a fondo), **vista en primera persona con doble búfer de mapa**, **texto y menús**, **guardado en
> SRAM**, y **niveles en rejilla con su lint y su vista previa**.
> Tema y decisiones aprobados por el usuario (§12): **TORRE HUNDIDA**, la torre de un mago que se tragó
> la tierra boca abajo. En código y tests se usan **nombres técnicos neutros** (HERO, FAST, GUARD, SLOW,
> KEY, POTION, STAFF, AMULET...); entre paréntesis, el nombre del tema.
> Mecánicas clásicas del género (crawlers de rejilla en tiempo real); nada de nombres, gráficos,
> textos ni mapas de juegos existentes.
> `harness/physics.py` no aplica (no hay saltos): aquí ese papel lo hacen el lint del nivel y el
> compositor de referencia en Python (§9.8 E11), que los tests usan como verdad.

---

## 1. Pitch

- **Género:** dungeon crawler en primera persona, por casillas, combate en tiempo real lento.
- **Fantasía:** "eres el aprendiz del mago. Una noche la tierra se tragó su torre entera, **boca abajo**,
  con el maestro dentro. Bajas por el hueco con una daga y una poción y recorres los pisos invertidos
  —baldosas en el techo, bóvedas bajo los pies, ventanas llenas de tierra— hacia el que fue el piso más
  alto, el estudio del mago. Abres puertas, le quitas la llave a una armadura viva y encuentras la
  escalera que, en la torre del revés, ahora baja."
- **Ambientación:** la escalera de bajada de cada piso es la antigua escalera de subida; los pisos se
  cuentan hacia abajo (PISO 1 = el que era el último). Las criaturas son las del laboratorio del mago,
  sueltas: diablillos, armaduras animadas, ojos flotantes.
- **Bucle principal:** explorar casilla a casilla → ver algo en el pasillo (ojos en la oscuridad,
  una puerta, un objeto) → luchar de frente (atacar, apartarse cuando el monstruo se prepara) →
  recoger llave/poción/arma → abrir la puerta cerrada → bajar la escalera.
- **Qué lo hace distinto:** en un DMG, una vista de 160x96 que cambia en cada paso **sin parpadeos ni
  desgarros** (doble búfer con los dos mapas de fondo, §9.2), con balanceo al andar y barrido al girar
  gracias a que el HUD vive en la ventana. Monstruos que **se ven acercarse por profundidades** (ojos →
  figura pequeña → figura grande) y que **avisan antes de golpear**. Dificultad suave, guardado en
  cualquier momento.
- **Duración:** el piso de M1 se explora en **8-15 min**; se puede guardar en cualquier momento desde la
  pausa (sesiones de autobús de 2-5 min).
- **Referencias (solo mecánicas):**
  - Crawlers de rejilla en tiempo real de PC (movimiento por casillas, giro de 90°, piezas por
    profundidad, monstruos de frente, llaves y puertas).
  - Crawlers por casillas de Game Boy en general: vista arriba, texto abajo, pocos colores con
    sombreado por distancia.
  - `games/shmup` (este repo): cómo planificar trabajo de motor (E1-E11), bots que deben avanzar,
    comprobación VRAM == modelo en cada frame, lint del nivel en Python.
  - `games/tetris`: auto-repetición de menús (16/6 f), copia asm de filas, `vram_late`.

---

## 2. Mecánicas

### 2.0 Convenciones (obligatorias para programador y tests)

- **Unidades:** frames (59.73 fps) y casillas. No hay física continua ni 8.8: todo es entero.
- **Mapa:** rejilla de **16x16 casillas** en WRAM, `dmap[256]`, índice `(y << 4) | x`. `x` crece hacia
  el este, `y` hacia el sur. Fuera del mapa (`(x | y) & 0xF0`, que también atrapa −1 = 0xFF) = muro.
- **Orientación** `pf`: `0 = N (dy −1)`, `1 = E (dx +1)`, `2 = S (dy +1)`, `3 = O (dx −1)`.
  Derecha = `(pf + 1) & 3`. Tablas `dir_dx[4]`, `dir_dy[4]` (int8).
- **Celdas de la vista:** `(d, l)` = d casillas al frente, l a la derecha (negativo = izquierda).
  Casilla del mundo: `x = px + d·dx[pf] + l·dx[(pf+1)&3]`, igual en y.
- **Tipos de celda** (`dmap`, 1 byte): `0 FLOOR`, `1 WALL`, `2 DOOR` (cerrada), `3 LOCKED` (con
  cerradura), `4 DOOR_OPEN`, `5 UP` (escalera de entrada, sellada), `6 DOWN` (escalera de bajada).
  - **Sólida para la vista** (se pinta como bloque): WALL, DOOR, LOCKED, UP, DOWN.
  - **Transitable:** FLOOR, DOOR_OPEN (y DOWN solo para el héroe: entrar = bajar).
- **Aleatoriedad:** un único generador `rng_next()` (xorshift de 16 bits, devuelve 8 bits) con estado
  global `rng_state`; se siembra con `DIV` + contador de frames al pulsar en TITLE. Los tests escriben
  `rng_state` y predicen los resultados con una copia del algoritmo en Python.
- **Pausa total:** con cualquier menú o el mapa abiertos, todos los temporizadores del juego se paran.
- **Globales legibles por tests** (no `static`): §9.7.

### 2.1 Movimiento y giro

| Parámetro | Valor | Unidad | Notas |
|---|---|---|---|
| ↑ / ↓ | avanzar / retroceder 1 casilla sin cambiar `pf` | | |
| ← / → | girar 90° izquierda / derecha | | |
| B + ← / → | paso lateral (izquierda / derecha) | | B pulsado **antes** que la dirección |
| B + ↓ | media vuelta (180°) | | huida rápida |
| Latencia entrada → vista nueva | **3 f** | f | componer en el frame de la entrada, copiar en 3 VBlanks, cambio de mapa al final del 3º (§9.2) |
| Repetición manteniendo ↑/↓/lateral | 1 paso cada **12 f** (5 pasos/s) | f | ajustar en playtest |
| Repetición manteniendo ←/→ | 1 giro cada **12 f** | f | ajustar en playtest |
| Búfer de entrada | 1 acción pulsada en los últimos 6 f del enfriamiento se ejecuta al acabar | f | como el búfer de tetris |
| Chocar (muro, puerta cerrada, monstruo, UP) | no se mueve; SFX `BUMP`; `shake_y` 1 px durante 4 f; enfriamiento 12 f | | contra UP además "EL HUECO SE CERRO" |
| Entrar en DOWN | solo de frente (↑) desde su única casilla vecina | | → CLEAR (§2.8) |
| Coger objeto | automático al entrar en su casilla | | §2.7 |

**Efectos (baratos: solo registros, el HUD está en la ventana y no se mueve):**

| Efecto | Cómo | Duración |
|---|---|---|
| Balanceo al andar | tras el cambio de mapa de un paso: `scy` = base + 2, +1, 0 | 3 f |
| Barrido al girar | durante los 3 frames de copia, el mapa visible se desplaza `scx` = ±8, ±16, ±24 (derecha: positivo); con el cambio de mapa vuelve a 0 | 3 f |
| Temblor al recibir daño | `shake_x` ±2 alternando cada 2 f | 8 f |

- Las columnas 20-31 y las filas de margen (7 y 20) de ambos mapas llevan el fondo de cada fila (techo /
  oscuridad / suelo, §2.3), así el barrido y el balanceo enseñan fondo coherente.
- Los sprites (monstruo, objeto) se desplazan con el mismo `scx`/`shake_x` (x de sprite −= desplazamiento);
  durante el barrido de giro se ocultan (3 f).
- Balanceo y barrido aprobados (§12, decisión 9); quedan en constantes `STEP_BOB` y `TURN_SLIDE` para el playtest.

### 2.2 Vista: lo que se ve

La vista ocupa las **filas 0-11 de la pantalla (160x96 px, 20x12 tiles)**. Alcance: **3 casillas** al
frente; más allá, oscuridad. Se ve un "cono" de 15 celdas además de la propia:

```
 d=3:  (3,-2) (3,-1) (3,0) (3,1) (3,2)     solo caras frontales
 d=2:  (2,-2) (2,-1) (2,0) (2,1) (2,2)     frontales de -1..1; laterales de ±1 y ±2
 d=1:         (1,-1) (1,0) (1,1)           frontales y laterales de ±1
 d=0:         (0,-1)  HERO (0,1)           solo laterales
```

### 2.3 Geometría de la vista y piezas

Proyección exacta con cámara 1.5 casillas detrás del centro de la casilla del héroe: los planos de
profundidad están a z = 2, 3, 4 (semiancho = 96/z px, semialto 64/z redondeado a 8). **Todos los
bordes caen en múltiplos de 8 px**, así cada pieza es un rectángulo de tiles y las piezas se pintan
de lejos a cerca sin mezclar píxeles de dos piezas en un tile.

| Plano | x (px) | y (px) | Columnas de tile | Filas de tile |
|---|---|---|---|---|
| P0 (pantalla) | 0-159 | 0-95 | 0-19 | 0-11 |
| P1 (borde lejano de la casilla del héroe) | 32-127 | 16-79 | 4-15 | 2-9 |
| P2 | 48-111 | 24-71 | 6-13 | 3-8 |
| P3 | 56-103 | 32-63 | 7-12 | 4-7 |

**Fondo (pieza BG):** filas 0-3 techo, 4-7 oscuridad (la franja de P3: todo lo que está a más de 3
casillas), 8-11 suelo. Cada fila es **un patrón de 2 tiles alternos** (24 bytes de tabla), para que
`view_clear` rellene a ~8 T por tile y las columnas 20-31 se puedan rellenar con lo mismo.
En la torre del revés el **techo son las antiguas baldosas** (losas con juntas) y el **suelo es la antigua
bóveda** (nervios de piedra, tierra en las grietas): el contraste techo oscuro / suelo de trama media se
mantiene.

**Piezas** (rectángulos con filas contiguas; los lados son trapecios: cada fila es un tramo contiguo):

| Pieza | Celda | Cara | Columnas | Filas | Entradas |
|---|---|---|---|---|---|
| F3L2 / F3R2 | (3,∓2) | frontal | 0 / 19 | 4-7 | 4 c/u |
| F3L1 / F3R1 | (3,∓1) | frontal | 1-6 / 13-18 | 4-7 | 24 c/u |
| F3C (D3, E3) | (3,0) | frontal (puerta, escalera) | 7-12 | 4-7 | 24 |
| S2L2 / S2R2 | (2,∓2) | lateral (hacia el centro) | 0 / 19 | 3-8 | 6 c/u |
| S2L1 / S2R1 | (2,∓1) | lateral | 6 / 13 | 3-8 | 6 c/u |
| F2L1 / F2R1 | (2,∓1) | frontal | 0-5 / 14-19 | 3-8 | 36 c/u |
| F2C (D2, E2) | (2,0) | frontal | 6-13 | 3-8 | 48 |
| S1L1 / S1R1 | (1,∓1) | lateral | 4-5 / 14-15 | 2-9 | 16 c/u |
| F1L1 / F1R1 | (1,∓1) | frontal | 0-3 / 16-19 | 2-9 | 32 c/u |
| F1C (D1, E1) | (1,0) | frontal | 4-15 | 2-9 | 96 |
| S0L / S0R | (0,∓1) | lateral | 0-3 / 16-19 | 0-11 | 48 c/u |
| LK1 / LK2 / LK3 | (d,0) LOCKED o UP | cerradura/sello sobre la puerta | centro | — | 4 / 2 / 1 |

- La cara frontal de (2,±2) y las laterales de profundidad 3 caen fuera de pantalla o en la oscuridad:
  no existen.
- **Puertas y escaleras solo tienen pieza propia en la columna central** (D1-D3, E1-E3). En las
  columnas laterales se pintan como muro (en M1 una puerta lateral parece muro hasta que la miras de
  frente; piezas laterales en M2, §10). Sus caras laterales son las del muro (el marco de piedra).
- LOCKED = pieza de puerta + LK*. UP = pieza de puerta + LK* (el hueco de entrada, tapado de tierra; no hay escalera de
  subida en M1).
- DOOR_OPEN se pinta como FLOOR (sin marco en M1).
- **El DMG no puede voltear tiles de fondo**: las piezas derechas (R) tienen tiles propios.

**Orden de pintado** (`view_compose`, de lejos a cerca; dentro de una capa los tramos no se solapan):

1. BG
2. Frontales de d=3: (3,−2) (3,−1) (3,0) (3,1) (3,2)
3. Laterales de d=2: (2,−2) (2,−1) (2,1) (2,2)
4. Frontales de d=2: (2,−1) (2,0) (2,1)
5. Laterales de d=1: (1,−1) (1,1)
6. Frontales de d=1: (1,−1) (1,0) (1,1)
7. Laterales de d=0: (0,−1) (0,1)

Se pinta una pieza si su celda es sólida (§2.0). La celda central usa D*/E* según el tipo, y LK* encima
si es LOCKED/UP. Culling opcional (saltarse celdas tapadas) **solo si no cambia el resultado**: el test
compara con el compositor de referencia (§11).

**Monstruos y objetos** (sprites, modo 8x16): solo en la **columna central**, el más cercano, si todas
las celdas (k,0) con k < d son transitables.

| Qué | d | Tamaño (px) | Posición en pantalla (x, y esquina) | Sprites | Por línea |
|---|---|---|---|---|---|
| Monstruo | 1 | 32x48 | (64, 30), pies en y 77 | 4x3 = 12 | 4 |
| Monstruo | 2 | 16x32 | (72, 38), pies en y 69 | 2x2 = 4 | 2 |
| Monstruo | 3 | ojos 16x8 en la oscuridad | (72, 44) | 2 (ojo der. = flip X) | 2 |
| Objeto en el suelo | 1 | 16x16 (báculo, amuleto) / 8x16 (llave, poción) | (72, 64) / (76, 64) | 2 / 1 | 2 |
| Objeto en el suelo | 2 | saco genérico 8x8 | (76, 62) | 1 | 1 |

- Respiración del monstruo (sin tiles extra): la fila superior de sprites sube 1 px cada 32 f.
- Un objeto bajo un monstruo se ve a sus pies (va antes en OAM: se dibuja delante). Un objeto más lejos
  que el monstruo no se ve.
- Los sprites representan **la vista que se está mostrando** (`shown_x/y/f`, que se actualizan cuando se
  programa el cambio de mapa), no la posición lógica: así sprite y fondo cambian en el mismo frame.

### 2.4 Héroe (HERO, "Aprendiz")

| Parámetro | Valor | Notas |
|---|---|---|
| PV al empezar / máximo | 20 / 20 | M2: subir de nivel (+5) |
| Arma inicial | DAGA | siempre la tiene |
| Pociones al empezar | 1 | dificultad suave |
| Precisión | 208 / 256 | menos la esquiva del monstruo |
| Defensa | 0; **1 con AMULETO** | cada punto resta 32 a la precisión del monstruo |
| Regeneración | +1 PV cada **300 f** si ningún monstruo está alerta (`aware_count == 0`) | suave; ajustar |
| Llaves / pociones | máx. 9 / 9 | contadores |

| Arma | Daño | Enfriamiento | Notas |
|---|---|---|---|
| DAGA | 1-2 | 20 f | |
| BACULO (STAFF) | 2-4 | 28 f | bastón de combate del mago; se equipa solo al cogerlo; se puede volver a la daga en OBJETOS |

### 2.5 Combate (tiempo real lento con aviso, §12)

**Atacar (A):** si `atk_cd == 0`: `atk_cd = enfriamiento del arma`, efecto de tajo 8 f, SFX `SWING`, y en
el mismo frame se resuelve contra la celda (1,0):
- **Monstruo:** acierta si `rng_next() < 208 − esquiva`. Daño = `min + rng_next() % (max − min + 1)`
  − armadura del monstruo, **mínimo 1**. Acierto: destello (OBP1 = paleta clara) 6 f, retroceso y −2 px
  6 f, SFX `HIT`, mensaje "GOLPE: 3". Fallo: SFX `MISS`, "FALLAS".
- PV ≤ 0: parpadeo (visible en frames alternos) 24 f, SFX `KILL`, "DIABLILLO CAE"; si llevaba objeto lo deja
  en su celda ("SUELTA UNA LLAVE"); `kills + 1`.
- **Puerta / cerradura:** ver §2.8 (abrir no gasta enfriamiento).
- **Nada / muro:** solo el tajo y `SWING`.

**Ataque de monstruo:** si está alerta, adyacente en ortogonal (cualquier lado) y su `atk_timer == 0`:
1. **Preparación** (`windup` f): de frente, el monstruo baja 2 px y usa OBP1 oscuro; si está a un lado o
   detrás, **flecha** en el borde de la vista (izq. x 4, der. x 148, ambas en y 44; detrás x 76 / y 80) parpadeando
   8/8 f y SFX `GROWL`. El héroe puede apartarse.
2. Al acabar, si sigue adyacente: acierta si `rng_next() < precisión − 32·defensa`. Daño = rango del
   monstruo (sin armadura del héroe en M1). Acierto: zarpazo 8 f (si es de frente), temblor (§2.1),
   SFX `HURT`, "TE HIERE: 2". Fallo: "ESQUIVAS".
3. `atk_timer = periodo de ataque`, `move_timer = periodo de movimiento` (no se mueve justo después).

**Daño esperado por combate** (primer orden, para orientar el playtest; la verdad es el ROM):

| Arma | Amuleto | DIABLILLO (golpes / f / PV perdidos) | ARMADURA | OJO |
|---|---|---|---|---|
| DAGA | no | 3.2 / 64 / 1.5 | 11.1 / 223 / 4.8 | 9.8 / 197 / 4.6 |
| DAGA | sí | 3.2 / 64 / 1.2 | 11.1 / 223 / 3.9 | 9.8 / 197 / 3.7 |
| BACULO | no | 1.6 / 45 / 1.1 | 5.6 / 156 / 3.3 | 4.9 / 138 / 3.2 |
| BACULO | sí | 1.6 / 45 / 0.9 | 5.6 / 156 / 2.7 | 4.9 / 138 / 2.6 |

Piso completo (4 diablillos, 3 armaduras, 1 ojo) con daga: ~25 PV; con báculo y amuleto: ~16 PV. Con 20 PV,
3 pociones en el mapa + 1 inicial (+10 c/u) y regeneración, un jugador medio no debería morir más de una
vez (objetivo de dificultad suave).

### 2.6 Monstruos

Hasta **12 por piso** (lint). Una celda = un monstruo. Siempre miran al héroe (solo hay arte de frente).

| Código (tema) | PV | Daño | Precisión | Esquiva | Armadura | Mover cada | Atacar cada | Preparación | Detecta (Manhattan) | Olvida (>) | Sin alerta |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FAST ("Diablillo": rápido, deambula) | 3 | 1-2 | 192 | 48 | 0 | 24 f | 48 f | 12 f | 4 | 7 | deambula: paso aleatorio cada 72 f |
| GUARD ("Armadura viva": armadura 1, guarda salas) | 8 | 1-3 | 176 | 24 | 1 | 40 f | 64 f | 16 f | 5 | 8 | quieto |
| SLOW ("Ojo flotante": lento, aguanta mucho) | 12 | 2-4 | 160 | 0 | 0 | 64 f | 80 f | 20 f | 3 | 6 | quieto |

Todos los valores: ajustar en playtest (están en una tabla `mon_stats[]`, nada de código por tipo).

**IA (C, barata):**
- **Activo** = a distancia de Chebyshev ≤ 8 del héroe. Solo los activos cuentan temporizadores.
- **Alerta** si distancia Manhattan ≤ detecta; deja de estarlo si > olvida.
- **Planificador:** cada frame piensa **como mucho 1 monstruo** cuyo temporizador llegó a 0 (turno
  rotativo), regla de games/platformer: nada de picos por pensar todos a la vez.
- **Moverse (alerta):** voraz: eje con mayor |delta| primero (empate: x); si la celda no está libre,
  el otro eje si su delta ≠ 0; si no, espera. Libre = FLOOR o DOOR_OPEN, sin monstruo, sin héroe.
  Los monstruos **no abren puertas** ni pisan escaleras. (Campo de distancias BFS en asm: M2.)
- Monstruo con objeto: `K` en el nivel = armadura viva que lleva la llave.

### 2.7 Objetos e inventario

| Objeto (código) | Sprite en el suelo | Efecto al cogerlo | Uso |
|---|---|---|---|
| KEY ("Llave") | 8x16 | `keys + 1`, "COGES UNA LLAVE" | se gasta al abrir una LOCKED |
| POTION ("Poción") | 8x16 | `potions + 1`, "COGES UNA POCION" | OBJETOS → A: +10 PV (tope máx.), "RECUPERAS 10 PV"; con PV llenos "YA ESTAS SANO" y no se gasta |
| STAFF ("Báculo") | 16x16 | `weapon = 1`, "COGES EL BACULO" | se equipa solo |
| AMULET ("Amuleto") | 16x16 | `amulet = 1`, "COGES EL AMULETO" | defensa 1, siempre puesto |

- Máx. 1 objeto por celda (lint), máx. 24 objetos por piso. Si un contador está a 9, el objeto se queda
  en el suelo ("NO PUEDES LLEVAR MAS").
- Inventario = contadores + arma/amuleto (no hay ranuras): la pantalla OBJETOS es una lista fija (§4).

### 2.8 Puertas, llaves y escaleras

| Situación (A con la celda (1,0)) | Resultado |
|---|---|
| DOOR | → DOOR_OPEN, recomponer vista (mismo camino de 3 f), SFX `DOOR`, "ABRES LA PUERTA" |
| LOCKED con `keys > 0` | `keys − 1`, → DOOR_OPEN, SFX `UNLOCK`, "USAS LA LLAVE" |
| LOCKED sin llaves | SFX `LOCKED`, "ESTA CERRADA" |
| UP | SFX `LOCKED`, "EL HUECO SE CERRO" (por donde entró el aprendiz: tierra) |

- Las puertas no se vuelven a cerrar en M1 (cerrar para cortar el paso a monstruos: M2).
- Animación de apertura: ninguna en M1 (cambio instantáneo); puerta que sube en 2 pasos: M3 (más piezas).
- **DOWN:** avanzar contra ella = "BAJAS LA ESCALERA", fundido → CLEAR.

### 2.9 Muerte

PV = 0 → `play_sub = DYING`: entrada bloqueada, la pantalla se funde a negro en 32 f (BGP hacia 0xFF en
4 pasos de 8 f; `set_fade` solo aclara: fundido a negro nuevo en E2), SFX `DEATH` → GAMEOVER ("HAS CAIDO": CONTINUAR = cargar la última
partida guardada; si no hay, empezar el piso desde el principio; TITULO).

### 2.10 Automapa (§12)

- Select en PLAY abre el mapa (pausa total); Select o B lo cierra.
- Pantalla completa: la ventana se oculta y el búfer trasero se dibuja con 18 filas (filas 8-25 del mapa
  de fondo). Fila 0 "MAPA - PISO 1", celdas 16x16 a 1 tile por celda en columnas 2-17, filas 1-16,
  fila 17 "B: VOLVER".
- Tiles: muro, suelo, puerta, cerradura, escalera abajo, escalera sellada (6); no vista = blanco. Héroe =
  sprite flecha según `pf` (flecha arriba/abajo con flip Y, derecha/izquierda con flip X).
- **Celdas vistas** (`seen[32]`, 1 bit por celda), marcadas al componer cada vista: (d,l) se marca si
  todas las (k,0) con 1 ≤ k < d son transitables y, si |l| = 2, (d,±1) es transitable. Siempre (0,±1) y
  (1,0). El test usa la misma regla en Python.
- Construcción: 4 filas de mapa por frame en C (~64 celdas x ~300 T ≈ 19k T) + copia de 4 filas por
  VBlank → 5 frames hasta el cambio de mapa. Al cerrar se rellenan de nuevo las filas 20-25 (margen).

### 2.11 Mensajes

Línea ≤ 18 caracteres, mayúsculas, sin tildes ni Ñ, solo los glifos de la fuente (dígitos, A-Z,
`- ! . : ?` y `/` nuevo, E14). Tabla de cadenas en un banco (§9.1, `#pragma bank 255`), con `#` = número.

`PISO 1` · `GOLPE: #` · `FALLAS` · `<NOMBRE> CAE` (DIABLILLO, ARMADURA, OJO) · `SUELTA UNA LLAVE` ·
`TE HIERE: #` · `ESQUIVAS` · `COGES UNA LLAVE` · `COGES UNA POCION` · `COGES EL BACULO` ·
`COGES EL AMULETO` · `NO PUEDES LLEVAR MAS` (20: se parte en 2 líneas "NO PUEDES" / "LLEVAR MAS") ·
`RECUPERAS # PV` · `YA ESTAS SANO` · `ABRES LA PUERTA` · `USAS LA LLAVE` · `ESTA CERRADA` ·
`EL HUECO SE CERRO` · `BAJAS LA ESCALERA` · `PARTIDA GUARDADA` · `ERROR AL GUARDAR`.

---

## 3. Controles

| Botón | En juego | En menús / pantallas |
|---|---|---|
| ↑ / ↓ | avanzar / retroceder | mover cursor (auto-repetición 16 f / 6 f, como tetris) |
| ← / → | girar 90° | — (cambiar valor en M2) |
| A | atacar / abrir puerta | confirmar / usar |
| B | modificador: B+←/→ paso lateral, B+↓ media vuelta | atrás |
| Start | menú de pausa | cerrar todos los menús; empezar en TITLE |
| Select | automapa | cerrar automapa |

Sin combinaciones de 3 botones. B solo no hace nada en juego (evita acciones accidentales).

---

## 4. Pantallas y flujo

```
BOOT -> TITLE --NUEVA PARTIDA--> carga del piso (fundido, LCD apagado) -> PLAY
          |  --CONTINUAR (si hay partida válida)--------------------------^
          v                                                               |
PLAY <--Start--> MENU (pausa): OBJETOS | ESTADO | MAPA | GUARDAR | VOLVER |
PLAY <--Select-> MAP                                                      |
PLAY --PV 0--> DYING (32 f) -> GAMEOVER: CONTINUAR (cargar) | TITULO      |
PLAY --entra en DOWN--> CLEAR (resumen) --Start--> TITLE (M1: "FIN DE LA DEMO")
```

`state` (u8 global): `TITLE=0, PLAY=1, MENU=2, MAP=3, GAMEOVER=4, CLEAR=5`. `play_sub`: `0 IDLE,
1 BUSY (copia de vista en curso), 2 DYING`. `menu_page`: `0 PAUSA, 1 OBJETOS, 2 ESTADO, 3 CONFIRMAR`.

| Pantalla | Cómo se dibuja | Contenido |
|---|---|---|
| TITLE | `.screen`, LCD apagado (`gbe_screen`) | "TORRE HUNDIDA" con la fuente (logo de tiles en M3: la torre del revés), menú NUEVA PARTIDA / CONTINUAR (solo si hay partida válida; el cursor empieza en CONTINUAR), "2026" |
| PLAY | vista (BG, doble búfer) + HUD (ventana) | §2.2, §5 |
| MENU pausa | **superposición en el búfer trasero**: la vista actual + caja con marco en columnas 5-14, filas 2-9 | OBJETOS, ESTADO, MAPA, GUARDAR, VOLVER; cursor = sprite flecha |
| OBJETOS | caja columnas 1-18, filas 1-10 sobre la vista | "POCION   X3", "LLAVE    X1", "DAGA", "BACULO  EQ", "AMULETO  EQ" (las que se tengan); A sobre POCION bebe, sobre un arma la equipa |
| ESTADO | igual | "APRENDIZ", "PV      18/20", "ATAQUE   2-4", "DEFENSA  1", "DERROTADOS 3", "TIEMPO 04:12", "PISO 1" |
| GUARDAR | mensaje en el log | escribe la partida (§9.5); "PARTIDA GUARDADA" |
| MAP | búfer trasero a pantalla completa, ventana oculta | §2.10 |
| GAMEOVER | `.screen`, LCD apagado | "HAS CAIDO", CONTINUAR / TITULO |
| CLEAR | `.screen` + números | "PISO 1 SUPERADO", "TIEMPO 04:12", "DERROTADOS 6 DE 8", "OBJETOS 5 DE 6", "FIN DE LA DEMO" (M1) |

- Las superposiciones (pausa, OBJETOS, ESTADO, MAPA) **reutilizan el doble búfer**: se componen en el
  lienzo de WRAM y se copian como una vista más (3-5 frames); al cerrar se recompone la vista.
- Transiciones entre pantallas completas: fundido BGP 16 f → `screen_build` con LCD apagado → fundido
  de entrada (`gbe_screen`, existe). La carga del piso (tiles desde bancos) va dentro de `screen_build`.
- Las maquetas `.screen` las hace el ui-designer. `design/screens/geom_play.screen` es solo un boceto
  de distribución (vista con letras = piezas, HUD con textos de ejemplo).

---

## 5. HUD e interfaz

**Vista arriba (filas 0-11) + HUD de 6 filas abajo en la VENTANA** (`WY = 96`, `WX = 7`,
mapa de ventana en `$9C00` filas 0-5). Sin interrupción LYC: la ventana tapa por sí sola de la línea 96
hacia abajo. El HUD no se mueve con SCX/SCY (balanceo, barrido, temblor) y existe una sola copia
(no hay que escribirlo en los dos mapas del doble búfer).

```
col: 01234567890123456789
w0:  V18/20 ES K1 O3   RN     V corazón, E icono de arma (daga/báculo), S amuleto (o vacío),
w1:  ====================     K llave + cuenta, O poción + cuenta, R rosa + letra N/E/S/O
w2:   PISO 1                  separador (1 tile)
w3:   ABRES LA PUERTA         registro de mensajes: 4 líneas x 18 (columnas 1-18),
w4:   GOLPE: 3                el más nuevo abajo
w5:   DIABLILLO CAE
```

- PV: dos dígitos con espacio a la izquierda (" 8/20"). La brújula usa O = Oeste.
- **Estado (w0):** `update()` lo convierte a `hud_buf[20]` cuando cambia algo (bandera sucia) y la cola
  de VRAM lo copia (20 tiles, una vez).
- **Registro:** mensaje nuevo → las 3 líneas de abajo suben (se re-encolan, 54 tiles en 2-3 frames por el
  presupuesto de la cola) y la nueva se escribe **2 caracteres por frame**. Hasta 4 mensajes pendientes
  en FIFO (si se llena se descarta el más antiguo pendiente). A no acelera (A es atacar).
- **Menús:** caja con marco de 9 piezas (4 esquinas, 4 bordes, relleno), texto a 1 tile del borde,
  cursor sprite (flecha derecha) a la izquierda de la opción, con vuelta de abajo a arriba. Auto-
  repetición 16/6 f. El menú es un módulo genérico (§9.8 E7).
- Disposición aprobada (§12, decisión 4).

---

## 6. Progresión y dificultad

### 6.1 Piso 1 (M1) — borrador; el `.lvl` es la fuente de verdad

Comprobado con un prototipo del lint (§11): bordes cerrados, puertas entre dos muros, escaleras con
una sola vecina, llave alcanzable antes de su cerradura, DOWN alcanzable, 102 celdas transitables,
ningún monstruo a menos de 4 casillas (Manhattan) del inicio.

```
     celdas            objetos            leyenda celdas: # muro  . suelo  D puerta  L cerradura
     0123456789012345  0123456789012345                   U entrada sellada  X escalera abajo
  0  ################  ................   objetos: @ inicio (@ facing S)  r FAST  k GUARD
  1  #####U##########  ................            K GUARD con llave  m SLOW  p POTION
  2  #...#.##...#...#  .p...@....w...h.            w STAFF  h AMULET  l KEY suelta (no hay en M1)
  3  #...D..D...#...#  ..r.............
  4  #...#.##...#...#  .........r...k..   Recorrido previsto: despensa oeste (diablillo,
  5  ##.##.#######.##  ................   poción) -> almacén tras D (7,3) (diablillo, BACULO)
  6  ##.##.#######.##  ................   -> sala NE (armadura, AMULETO) -> pasillo central
  7  ##.##.#######.##  ................   -> biblioteca tras D (8,9) (2 armaduras, una con la
  8  #..............#  ................   LLAVE, poción) -> L (12,11) -> antesala con el OJO
  9  ##D#####D###.###  ................   delante de X (14,13). Sala SO (2 diablillos, poción)
 10  #...###....#.###  ................   opcional.
 11  #...###....#L###  .r..............
 12  #...###....#..##  ...r...k........
 13  #...###....#..X#  .........K...m..
 14  #...###....#..##  .p........p.....
 15  ################  ................
```

Contenido: 8 monstruos (4 FAST, 3 GUARD, 1 SLOW), 3 pociones, báculo, amuleto, 1 llave (en un GUARD),
4 puertas, 1 cerradura. El pixel-artist y el diseñador de niveles pueden retocarlo; el lint manda.

### 6.2 Reglas del nivel (las comprueba el lint, §11)

- Rejilla exactamente 16x16 (M2: hasta 32x32), borde exterior de muro.
- 1 inicio (`@`) con `@ facing` válido y celda de frente transitable; 1 DOWN; UP opcional junto al inicio.
- DOOR/LOCKED: muro a ambos lados en un eje y transitable en el otro (la puerta "está en un muro").
- UP/DOWN: exactamente una vecina transitable (el arco se mira de frente).
- Objetos y monstruos solo sobre FLOOR, máx. 1 por celda; ≤ 12 monstruos, ≤ 24 objetos.
- **Llaves:** nº de llaves (sueltas + `K`) ≥ nº de LOCKED (con llaves genéricas, así nunca hay bloqueo
  por gastar una llave en la puerta "equivocada"), y simulación iterativa (BFS sin cerraduras → recoger
  llaves alcanzables → abrir una cerradura de la frontera → repetir) que llega a DOWN.
- Ningún monstruo a distancia Manhattan < 4 del inicio.
- Todas las celdas transitables alcanzables (sin zonas muertas) salvo las marcadas `@ secret` (M2).

### 6.3 M2 en adelante
Pisos 2-3 (con sus tilesets y 3 tipos de monstruo cada uno), subir de nivel con experiencia, monstruos
laterales, palancas y paredes falsas. Decidir tras el playtest de M1.

---

## 7. Contenido y assets

### 7.1 Tiles de fondo (BG + ventana), máx. 256 índices

Modo LCDC.4 = 0: índices 0-127 en `$9000`, 128-255 en `$8800` (compartidos con sprites 128-255).
`"vram_order": ["ui", "font", "walls"]`.

| Asset | Índices | Tiles | Notas |
|---|---|---|---|
| UI: marco de menú (9), iconos HUD (corazón, daga, báculo, amuleto, llave, poción, rosa: 7), separador (1), automapa (6), BLANK (1) | 0-23 | 24 | `res/ui.tiles` (ui-designer) |
| Fuente compartida + `/` (E14) | 24-65 | 42 | `harness/common/font.tiles` |
| **Juego de paredes "torre"** | 66-231 | **166** | `res/walls.tiles` + `res/view.pcs` (pixel-artist) |
| Libres (los pueden usar sprites 232-255) | 232-255 | 24 | margen |

Reparto del juego de paredes (presupuesto por pieza; si el arte no cabe, simplificar texturas):

| Grupo | Tiles | Detalle |
|---|---|---|
| Fondo | ≤ 10 | techo 4 filas, oscuridad 1, suelo 4 filas (patrón de 2 por fila) |
| Frontales P1 / P2 / P3 | ≤ 16 / 12 / 8 | textura que se repite + bordes; cuanto más lejos, más oscuro |
| Laterales S0 (L+R) | ≤ 36 | 18 c/u: diagonales arriba/abajo + interior por columna |
| Laterales S1 (L+R) | ≤ 20 | 10 c/u |
| Laterales S2 (L1, R1, L2, R2) | ≤ 20 | 5 c/u |
| Puertas D1 / D2 / D3 + cerradura LK (3) | ≤ 12 / 6 / 3 / 3 | |
| Escalera E1 / E2 / E3 | ≤ 11 / 6 / 3 | arco con peldaños hacia la oscuridad |
| **Total** | **≤ 166** | |

Tema del juego de paredes "torre": sillares de torre redonda, ventanas ojivales **tapiadas de tierra** y
raíces asomando en algún frontal (variante de textura dentro del presupuesto), puertas de madera con
herrajes, escalera de caracol del revés que "baja". Legibilidad en el LCD borroso: **sombreado por distancia** (P1 colores 0-1 con contorno 3, P2 1-2, P3 2-3,
oscuridad 3), techo oscuro y suelo de trama media; las aristas de las esquinas en color 3.

### 7.2 Tiles de sprite (modo 8x16, `$8000-$87FF`, índices 0-127)

| Asset | Tiles | Notas |
|---|---|---|
| FAST (diablillo), GUARD (armadura viva), SLOW (ojo flotante): d1 32x48 (24) + d2 16x32 (8) | 96 | 32 por tipo; ataque = lunge + zarpazo, sin frame extra |
| Ojos (d3) | 2 | compartidos; ojo derecho = flip X |
| Objetos d1: llave 2, poción 2, báculo 4, amuleto 4 | 12 | |
| Saco genérico d2 | 2 | |
| Tajo 16x16 / zarpazo 16x16 | 4 / 4 | |
| Flechas (arriba, derecha; flip para abajo/izquierda) | 4 | indicador de ataque lateral, héroe del automapa, cursor de menús |
| **Total** | **124 / 128** | |

**Total VRAM:** 232 BG + 124 sprites = **356 / 384**. Todo se carga con el LCD apagado al entrar en el
piso; en juego **no se escriben datos de tiles** (solo mapas). Regla para M2: ≤ 3 tipos de monstruo por
piso (o E15 `gbe_tiles`).

### 7.3 Sprites: OAM y límite por línea

| OAM | Qué | Sprites |
|---|---|---|
| 0 | flecha (indicador lateral / cursor de menú / héroe en el mapa) | 1 |
| 1-2 | tajo | 2 |
| 3-4 | zarpazo | 2 |
| 5-6 | objeto en el suelo | 2 |
| 7-18 | monstruo | 12 |
| 19-39 | libres (Y = 0) | — |

Peor línea: líneas 56-59 con monstruo d1 (4) + tajo (2) + zarpazo (2) + flecha (1) = **9 / 10**; líneas
64-79: monstruo (4) + objeto (2) + zarpazo (2) = 8. **Nunca hay parpadeo** (no hace falta `gbe_spr`).

---

## 8. Sonido

M1: **solo efectos** (`gbe_sfx`). Música en M2 (hUGEDriver en su banco, E16).

| Efecto | Canal | Prioridad | Notas |
|---|---|---|---|
| `STEP` | 4 | 0 | ruido muy corto y bajo; cada paso |
| `BUMP` | 4 | 1 | golpe sordo |
| `SWING` / `MISS` | 4 / 4 | 1 / 1 | |
| `HIT` / `KILL` | 4 / 4 | 2 / 3 | |
| `GROWL` (preparación) | 2 | 2 | **aviso**: debe oírse siempre |
| `HURT` | 1 | 3 | sweep bajando corto |
| `DOOR` / `UNLOCK` / `LOCKED` | 1 / 1 / 2 | 2 / 2 / 2 | |
| `PICKUP` / `DRINK` | 1 / 1 | 2 / 2 | arpegio subiendo |
| `MENU_MOVE` / `MENU_OK` / `MENU_BACK` | 2 | 1 / 2 / 2 | |
| `SAVE` | 1 | 3 | |
| `DEATH` / `CLEAR` | 1 | 3 | |

---

## 9. Técnica

### 9.1 Cartucho y bancos (E1: base ya hecha, queda ampliarla)

**MBC5 + RAM + batería (0x1B), 64 KB en M1 (4 bancos), 8 KB de SRAM:**
`["-autobank", "-Wm-yt0x1B", "-Wm-yo4", "-Wm-ya1"]` (receta de CLAUDE.md; M2: `-Wm-yo8`, 128 KB).

| Parte | M1 |
|---|---|
| Código motor gbe (frame, video, oam, sfx, screen, text, menu, save, view, bgbuf, vq, rng, bancos) | ~8-9 KB |
| Código del juego (estados, IA, combate, menús, carga) | ~10-12 KB |
| Tiles: paredes 166 + UI 24 + fuente 42 + sprites 124 = 356 x 16 B | 5.7 KB |
| Piezas de la vista (tramos) | ~1.2 KB |
| Piso 1 (256 B + objetos ~60 B) + tablas de monstruos/objetos | ~0.4 KB |
| Textos (~25 mensajes + menús) | ~0.8 KB |
| Pantallas `.screen` (title, gameover, clear: 360 B c/u) | 1.1 KB |
| **Total** | **~28-31 KB** de código + datos → **no cabe plano junto a GBDK (~3 KB)**: hacen falta bancos ya en M1 |

**Lo que ya da el arnés (probado en games/gbe_lab):** `game.json` `"banked_res": [stems]` mete los assets
generados (tilesets, niveles, `screen_<nombre>`) en bancos con `#pragma bank 255` + `BANKREF(stem)`, y
bankpack (`-autobank`) elige el banco. Helpers en `harness/common/src/gbe_bank.c` (banco 0, restauran el
banco): `bank_set_bkg_data(bank, first, n, data)`, `bank_set_sprite_data(...)`,
`bank_memcpy(bank, dst, src, n)`, `bank_read8(bank, p)`. El build se para si algo fijo pasa de `0x4000`
cuando hay bancos.

**Disposición de bancos** (los números de banco de datos los decide bankpack; el código no los supone,
usa `BANK(stem)`):

| Zona | Contenido | Quién la mapea |
|---|---|---|
| Banco 0 (fijo, `$0000-$3FFF`) | crt de GBDK, ISRs (VBlank de gbe_video), todo gbe (incl. `gbe_bank`, `gbe_view`, `gbe_bgbuf`), bucle principal, código del juego **mientras quepa** | siempre |
| Banco 1 (solo si el banco 0 se llena) | código C del juego con `#pragma bank 1` y entradas `BANKED` llamadas desde `main()` | trampolín de GBDK (cambia y restaura; medir su coste, se esperan ~100-150 T, pocas llamadas por frame) |
| Bancos autobank | `"banked_res": ["walls", "view", "ui", "font", "spr", "floor1", "screen_title", "screen_gameover", "screen_clear"]` + textos y tablas grandes del juego en un `.c` con `#pragma bank 255` | helpers de `gbe_bank` / `SWITCH_ROM` dentro de gbe_view |
| M2 | música (hUGEDriver + canciones), juegos de paredes y pisos nuevos | helpers / ISR de música |

Reglas (para la sección "Bancos de ROM" de CLAUDE.md):
1. **Solo código del banco 0 cambia de banco** (`SWITCH_ROM`), guardando `_current_bank` y restaurándolo
   antes de volver. Si existe código en banco 1, nunca cambia de banco (lint nuevo del build, E1).
2. Datos con banco: tiles con `bank_set_bkg_data`/`bank_set_sprite_data` (LCD apagado), nivel y textos con
   `bank_memcpy` a WRAM (un mensaje ≤ 18 B, ~300 T), y el compositor de la vista cambia al banco de las
   piezas (`BANK(view)`) durante la composición (1 cambio por paso, ~50 T).
3. Las ISRs del banco 0 no leen datos con banco; la de música (M2) guarda/restaura el banco.
4. `view.pcs` (E11) genera un `.c` que debe poder ir en `"banked_res"` como los tilesets.

**Carga de datos:** al entrar en un piso, con el LCD apagado dentro de `screen_build`: tiles (356 x 16 B),
mapa a `dmap`, objetos y monstruos a sus tablas, relleno de los dos mapas de fondo (filas 7-20, columnas
0-31) y del HUD. En juego: textos (1 cadena por mensaje, ~300 T) y piezas (al componer). Nada se
"streamea" a VRAM salvo mapas.

### 9.2 Cómo se dibuja la vista: comparación y elección

La vista es un **mosaico de índices de tile**: las piezas (§2.3) son tramos de índices que se copian en un
lienzo de WRAM `view_buf[240]` (20x12) de lejos a cerca; ningún tile se genera en tiempo de ejecución.
Lo que cambia por paso es el **mapa de fondo de la vista: hasta 240 entradas (todas en giros y pasos)**.
Se copian siempre las 240 (coste constante, sin buscar diferencias).

Costes medidos de referencia: copia asm de 20 entradas contiguas `vram_row20` ~24 T/tile (shmup), copia
asm de 10 tiles ~228 T (budgets.md), VBlank útil tras `vsync()` ~3600 T.

| Enfoque | Números | Veredicto |
|---|---|---|
| A. Redibujar el mapa de la vista en 1 VBlank, un solo búfer | 240 x 24 T + 12 filas x ~60 T ≈ **6500 T > 3600** | no cabe. En 2 VBlanks: 1 frame con media vista vieja y media nueva en cada paso (desgarro visible). Con vista de 12x10 (120 tiles ≈ 3000 T) cabría, pero la vista sería de 96x80 y no quedaría VBlank para el texto |
| **B. Doble búfer con los dos mapas de fondo (LCDC.3)** | copiar al mapa oculto 4 filas por VBlank: 4 x (20 x 24 + ~60) ≈ **2200 T**, 3 VBlanks, y cambiar LCDC.3 (1 escritura) al final del 3º | **elegido**: sin desgarro, latencia 3 f (50 ms), queda ~1000 T de VBlank para texto/HUD en esos frames. El HUD va en la ventana (`$9C00` filas 0-5) y la vista en las filas 8-19 de ambos mapas (`SCY` base = 64), así no se pisan |
| C. Doble búfer en un solo mapa, cambiando SCY | mismo coste que B | equivalente, pero gasta SCY en elegir búfer (el balanceo y el barrido se complican) y no deja libre un mapa para la ventana; B es 1 bit |
| D. Redibujar con el LCD apagado | 1 frame en blanco por paso a 5 pasos/s = estroboscopio; además apagar solo en VBlank | **prohibido** en pasos normales; solo al cargar el piso (con fundido) |
| E. Generar datos de tile (vista en mapa de bits) | 240 tiles x 16 B = 3840 B por vista: a ~20 T/byte ≈ 77k T de VBlank = **22 VBlanks** por paso, más rasterizar en la CPU | rechazado para la vista. La cola de datos de tile (E15, ~8 tiles por VBlank ≈ 2600 T) queda para M2: cambiar sets de monstruos o decoraciones sin apagar el LCD |

**Secuencia de un paso** (frame N = el que lee la entrada):
1. Frame N, `update()`: mover el héroe en el modelo, `view_compose()` en `view_buf` (§9.4), marcar `seen`,
   `bgbuf_start()`: `bgbuf_rows_left = 12`, búfer trasero = el que no se ve.
2. VBlank N+1, N+2, N+3: `bgbuf_draw_vram()` copia 4 filas cada uno a las filas 8+r del mapa trasero.
3. Al final del VBlank N+3 (aún en VBlank; la guardia `vram_late` lo vigila): LCDC.3 cambia →
   el frame N+3 ya se ve con la vista nueva. En el `update()` de N+2 se fijan `shown_x/y/f` para que los
   sprites del frame N+3 correspondan.
4. Mientras `play_sub == BUSY` las acciones nuevas van al búfer de entrada.

`ROWS_PER_VBLANK = 4` es una constante: si la medida deja margen, 6 (2 VBlanks); si no, 3 (4 VBlanks).

### 9.3 Presupuesto de VBlank (peor frame)

| Trabajo | Tiles | Coste |
|---|---|---|
| Sombras de la ISR (SCX, SCY, BGP, OBP0/1, bit 3 de LCDC) | — | ~80 T |
| Copia de vista: 4 filas x 20 (`vram_row20`) | 80 | ~2200 T |
| Cola de VRAM (HUD, registro): presupuesto **16 tiles** si hay copia de vista, **48** si no | 16 | ~500 T |
| Cambio de mapa (LCDC.3) | — | ~20 T |
| **Total peor caso (frame de copia)** | **96** | **~2800 T (78 % de 3600)** |

- Frames sin copia de vista: cola de hasta 48 tiles ≈ 1400 T.
- Superposiciones de 18 filas (automapa): mismas 4 filas por VBlank, 5 VBlanks.
- Todo se prepara en `update()`; en VBlank solo se copia. Prohibido `set_bkg_tiles` en juego.
- `vram_late == 0` en todos los tests. **El 78 % es una estimación: medir en M1a** (`gb.profile` de
  `bgbuf_draw_vram`, `vq_draw_vram`) antes de la lógica del juego.

### 9.4 Presupuesto de CPU (fuera de VBlank)

| Trabajo | Cómo | Coste |
|---|---|---|
| Entrada, estado, héroe | C | ~1500 T |
| **Componer la vista** (frame de la entrada): `view_clear` 240 x ~8 T; tramos de piezas, peor caso teórico 512 entradas x 24 T (`ld a,(de) / inc de / ld (hl+),a`) + ~70 tramos x ~60 T; 15 consultas de celda en C x ~400 T | asm + C | ≈ 2k + 12k + 4k + 6k ≈ **24-30k T** |
| Marcar `seen` | C | ~1000 T |
| IA: 1 monstruo piensa por frame; temporizadores de ≤ 12 activos | C | ~1500 + 600 T |
| Sprites: monstruo 12 + objeto 2 + efectos 5, directos a `shadow_OAM` (presupuesto de shmup: ~300 T por sprite) | C/asm | ~5500 T |
| Texto: mensaje a tiles, HUD (solo si cambia) | C | ~1500 T |
| SFX | asm | ~300 T |
| **Total frame de paso** | | **~36-42k T ≈ 80-92 líneas** |
| Frame normal (sin paso) | | ~11k T ≈ 25 líneas |

Objetivo de test: **`max_frame_lines < 120`**. Las estimaciones de shmup salieron 3-5x bajas en C por
objeto; aquí lo caro (composición, copia) es asm medible desde M1a. Si la composición pasa de 35k T:
culling de celdas tapadas (con el test de equivalencia) y consultas de celda en asm.
Pantallas de menú: componer una caja con 6 líneas de texto ≈ 20k T (C). Guardar: ~60k T (se marca
`skip_measure`, es una acción de menú).

### 9.5 RAM, VRAM y guardado

**WRAM (8 KB):** `dmap` 256, `seen` 32, `view_buf` 240 (lienzo de 360 para pantallas de 18 filas),
monstruos 12 x 10 = 120, objetos 24 x 3 = 72, registro 4 x 18 + 4 pendientes = 80, `hud_buf` 20, cola de
VRAM 16 x 4 = 64, shadow OAM 160, estado ~200 → **~1.4 KB**.

**Mapas de VRAM:**

| Zona | Uso |
|---|---|
| `$9800` filas 7-20 (columnas 0-31) | búfer de vista A (filas 8-19 = vista, 7 y 20 = margen de balanceo, columnas 20-31 = fondo para el barrido); filas 8-25 en el automapa |
| `$9C00` filas 0-5 | ventana: HUD |
| `$9C00` filas 7-20 (8-25 en el automapa) | búfer de vista B |
| LCDC | bit 3 = búfer visible, bit 6 = 1 (ventana en `$9C00`), bit 5 ventana on (off en MAP), bit 4 = 0, bit 2 = 1 (8x16) |

**SRAM (8 KB, `gbe_save`, ya existe):** hoy un bloque en `$A000`: `'G' 'B' versión len_lo len_hi
datos[len] suma1 suma2` (Fletcher-16, la firma se escribe la última, SRAM habilitada solo dentro de las
funciones). API: `save_load(dst, len, version)` → 1 si es válido, `save_store(src, len, version)`,
`save_erase()`. El juego usa `version = 1` (cambiarla invalida partidas de un formato viejo).

**Ampliación E8 (dos ranuras):** ranuras en `$A000` y `$B000` escritas en alternancia, con un byte de
secuencia (u8, comparación módulo 256) tras la versión; `save_load` elige la ranura válida con la
secuencia más alta, así un corte de corriente a mitad de guardado deja la partida anterior. Misma API
(compatible con GRIFO); `save_erase()` borra las dos.

Carga del juego (~360 B): piso 1, `px py pf` 3, `hp hp_max` 2, `keys potions weapon amulet` 4, `kills` 1,
`play_secs` 2, `rng_state` 2, `dmap` 256 (puertas abiertas incluidas), `seen` 32, objetos cogidos (bits,
24) 3, monstruos 12 x 4 (vivo/PV, x, y, estado) 48.

### 9.6 Riesgos técnicos y mitigación

| Riesgo | Mitigación |
|---|---|
| Composición de la vista más cara de lo estimado (24-30k T) | medir en M1a con un mapa de prueba y el peor caso; culling con test de equivalencia; consultas de celda en asm |
| VBlank del frame de copia al 78 % (estimado) | medir; `ROWS_PER_VBLANK` a 3; presupuesto de la cola de VRAM bajo mientras se copia |
| El arte no cabe en 166 tiles de paredes | presupuesto por pieza (§7.1); el pixel-artist revisa con el compositor de referencia (E11); simplificar texturas antes que pedir streaming |
| Errores de bancos (cuelgue al cambiar de banco, código con banco cambiando banco) | reglas de §9.1, lint del build (E1), test que lee datos de cada banco por los helpers y los compara con los ficheros fuente; uso por banco en el build (E1) |
| Ventana y búfer B comparten `$9C00` | regiones disjuntas (§9.5); test: tras cada copia, las filas 0-5 de `$9C00` == HUD esperado |
| Desfase sprites/fondo al cambiar de vista | `shown_x/y/f` fijados el frame antes del cambio; test que en cada frame compara sprites con la vista visible |
| Guardado cortado a mitad (corriente) | firma escrita la última (ya en `gbe_save`) + dos ranuras (E8); test con `gb.power_off()` |
| Monstruos que atacan sin verse (lados, detrás) | flecha + `GROWL` en la preparación + mensaje; dibujo lateral en M2 |
| Puertas laterales que parecen muro | aceptado en M1; piezas laterales de puerta en M2 si sobra presupuesto de tiles |
| Hardware real: escribir LCDC.3 en VBlank, ventana con WY fijo | sencillo, sin ISR a mitad de frame; probar en M4 |

### 9.7 Globales para tests (no `static`)

`state`, `play_sub`, `menu_page`, `menu_sel`, `px`, `py`, `pf`, `hp`, `hp_max`, `keys`, `potions`,
`weapon`, `amulet`, `atk_cd`, `move_cd`, `kills`, `play_secs`, `dmap[256]`, `seen[32]`, `mon_type[]`,
`mon_x[]`, `mon_y[]`, `mon_hp[]`, `mon_state[]` (bit 0 alerta, bit 1 preparando, bit 2 muriendo),
`mon_move_t[]`, `mon_atk_t[]`, `mon_item[]`, `mon_count`, `aware_count`, `item_type[]`, `item_x[]`,
`item_y[]`, `item_count`, `view_buf[240]`, `view_flips` (u8, +1 en cada cambio de mapa), `bg_front`
(0/1), `bgbuf_rows_left`, `shown_x`, `shown_y`, `shown_f`, `scx_shadow`, `scy_shadow`, `log_lines[]`,
`log_pending`, `rng_state` (u16), `save_status`, `vram_late`, `max_frame_lines`, `skip_measure`,
`cheat_flags` (bit 0 invencible, bit 1 monstruos congelados, bit 2 un golpe mata, bit 3 mapa entero
visto; solo los escriben los tests).

### 9.8 Qué reutiliza de gbe y qué le falta (trabajo de motor en `harness/common`)

**Reutiliza tal cual:** `gbe_frame` (bucle, entrada, `max_frame_lines`, `vram_late`), `gbe_oam`
(`oam16/oam8`), `gbe_screen` (transiciones con LCD apagado), `gbe_sfx`, `gbe_vram.s` (`vram_row20` para la
copia de filas), fuente compartida, `harness/screens.py`, `gb.run_bot`, `gb.profile`, `gb.selftest`,
`gb.worst_frames`, **`gbe_bank`** (`"banked_res"` + helpers, §9.1), **`gbe_save`** (un bloque con
Fletcher-16; se amplía en E8), `gb.power_off()` / `GB(rom, ram=...)` (apagar y encender conservando la
SRAM), `gb.bg_map(window=True)`, `gb.io()`. `gbe_video` con cambios (E2). **No usa** `gbe_map`, `gbe_vmap`, `gbe_actors`, `gbe_pool`, `gbe_spr`,
`gbe_aim` (no hay scroll ni muchos objetos).

Piezas nuevas, genéricas (cada asm con referencia C + caso en `gbe_selftest`), en el orden de M1a:

| # | Pieza | Qué hace | Por qué / para quién más |
|---|---|---|---|
| E1 | **Bancos de ROM: ampliar** (la base `"banked_res"` + `gbe_bank` ya existe) | (a) código del juego en `#pragma bank 1` con entradas `BANKED` si el banco 0 se llena (receta y coste medido del trampolín); (b) lint del build: `SWITCH_ROM`/`SWITCH_ROM_MBC5` solo en código del banco 0; (c) informe de uso por banco en `gb.py build`; (d) el `.c` de `view.pcs` (E11) y los textos admitidos en `"banked_res"`; (e) CLAUDE.md "Bancos de ROM" al día | primer juego que llena el banco 0 de código; música y pisos nuevos de todos los juegos |
| E2 | `gbe_video`: doble mapa y ventana abajo | sombra del bit 3 de LCDC aplicada en VBlank + `video_bgmap_now(sel)` (escritura inmediata en VBlank), `video_window(wy)` (ventana fija sin ISR), base de `scy`/`scx`, fundido a negro `set_fade_dark(k)` | doble búfer; HUD inferior sin interrupción |
| E3 | `gbe_view` (+ `.s`) | compositor de vista en primera persona: formato de piezas por tramos, `view_clear(bg)` asm, `view_blit(piece)` asm (+ C), `view_compose(x, y, f)` con la tabla de las 15 celdas y el orden de §2.3; el juego da `view_cell_class(x, y)` → MURO/PUERTA/CERRADURA/ESCALERA/LIBRE y las tablas de piezas | núcleo del género; reutilizable por otro crawler o por vistas de "ventana" en un RPG |
| E4 | `gbe_bgbuf` | doble búfer de mapa: lienzo de WRAM (20x12 o 20x18) → mapa oculto, N filas por VBlank con `vram_row20`, cambio de LCDC.3 al acabar, `bgbuf_busy()`, relleno de márgenes | vista, menús superpuestos, automapa; cualquier juego que redibuje pantallas grandes sin apagar el LCD |
| E5 | `gbe_vq` | cola FIFO de escrituras de mapa `(dst, src, len)` con presupuesto de tiles por frame, ajustable (`vq_budget`) | generaliza las colas de HUD hechas a mano en platformer/shmup |
| E6 | `gbe_text` | tabla carácter → tile de la fuente, `txt_put(buf, str)`, números con anchura y ceros, registro de N líneas con escritura de K caracteres/frame en la ventana, cadenas en banco (copiadas a WRAM con `bank_memcpy`) | textos de todos los juegos; base de un futuro RPG |
| E7 | `gbe_menu` | menú vertical: caja de 9 piezas en un lienzo, opciones, cursor sprite, auto-repetición 16/6 f, A/B/Start, devuelve la opción; opciones desactivables (CONTINUAR sin partida) | pausa/título/opciones de cualquier juego |
| E8 | `gbe_save`: **ampliar** (ya hay 1 bloque con firma `'G''B'`, versión, longitud y Fletcher-16; firma escrita la última) | 2 ranuras alternas (`$A000`/`$B000`) + byte de secuencia; `save_load` elige la válida más nueva; misma API `save_load/save_store/save_erase` | partida a salvo si se corta la corriente al guardar; récord de GRIFO |
| E9 | `gbe_rng` | xorshift de 16 bits, `rng_next()` 8 bits, `rng_state` global; copia del algoritmo en `harness/gbtest.py` para predecir en tests | todos los juegos con azar |
| E10 | `harness/levels.py` `"order": "grid"` | rejilla W x H (≤ 32x32) fila-mayor de arriba abajo (`map[y*W + x]`), capa de objetos como los niveles verticales, `@ facing`; `levels.parse()` para el lint | niveles de crawler, puzles, RPG |
| E11 | `harness/fpview.py` + formato `res/view.pcs` | piezas de la vista en ASCII (leyenda de tiles + rejilla por pieza, `.` transparente, cada fila un tramo contiguo: lo valida); genera las tablas C (con banco); **compositor de referencia en Python** que da las 240 entradas para (mapa, x, y, f) y PNG de vistas canónicas (pasillo, cruce, puerta delante, sala) y de cualquier posición de un nivel | arte de piezas revisable sin compilar; verdad de los tests VRAM == modelo |
| E12 | `harness/preview.py`: niveles de rejilla | `level_<nombre>.png` en vista cenital con leyenda (colores por tipo de celda y letras de objetos) | revisar niveles sin jugar |
| E13 | `harness/gbtest.py`: **ampliar** (ya hay `gb.power_off()` + `GB(rom, ram=...)`, `gb.bg_map(window=True)` = `$9C00`, `gb.io()`) | `gb.bg_map(map=0/1)` explícito y `gb.active_bg()` (según LCDC.3 vía `gb.io(0xFF40)`), corromper bytes de la SRAM devuelta por `power_off()` antes de encender, `gb.rng_next(state)` | tests de doble búfer y de ranuras corruptas |
| E14 | `harness/common/font.tiles` | glifo `SLASH` (`/`) (y su mapeo en `screens.py`/`preview.py`) | "18/20" en el HUD; útil para todos |
| E15 | `gbe_tiles` (M2, opcional) | cola de datos de tile (16 B) copiados en VBlank con presupuesto (~8 tiles/frame cuando no hay copia de vista) | > 3 tipos de monstruo por piso, decoraciones; la E10 de shmup |
| E16 | Música (M2) | hUGEDriver en su banco, llamado desde la ISR con guardar/restaurar banco | primera música del estudio |

---

## 10. Hitos

- **M1a — arnés y motor (antes de la lógica del juego):** E1-E14 (E1, E8 y E13 son ampliaciones de lo que ya existe) con referencias C y
  `gbe_selftest` ampliado, README de `harness/common` y CLAUDE.md (bancos) actualizados. Demo en `games/dungeon`: piezas
  provisionales (rectángulos con números de pieza), un mapa de prueba, andar y girar con el doble búfer,
  menú de pausa de prueba, guardar/cargar, y **medidas reales** de `view_compose`, `bgbuf_draw_vram` y la
  cola (§9.3, §9.4) apuntadas en budgets.md.
- **M1b — slice jugable (piso 1, arte provisional del pixel-artist):** movimiento/giro con balanceo y
  barrido, vista con muros de torre/puertas/escalera, 3 monstruos con IA y combate, objetos, puertas y llave,
  automapa, HUD y registro, TITLE / MENU (OBJETOS, ESTADO, MAPA, GUARDAR) / GAMEOVER / CLEAR, guardado en
  SRAM y CONTINUAR, efectos de sonido, tests de §11.
- **M2 — contenido:** pisos 2-3 (`-Wm-yo8`, un juego de paredes por piso), música (E16), experiencia y
  niveles, monstruos en columnas laterales, piezas laterales de puerta, cerrar puertas, palancas y paredes
  falsas, campo de distancias BFS (asm) para la IA, `gbe_tiles` si hacen falta más monstruos.
- **M3 — pulido:** puerta que sube en 2 pasos, logo de título, más animación de monstruos, grupo o magia
  (solo si se piden más adelante).
- **M4 — hardware real:** flash cart; legibilidad de la profundidad en el LCD, ghosting de los sprites
  grandes, SRAM con batería real (cortar la corriente al guardar).

---

## 11. Plan de pruebas

Bots con `gb.run_bot` y **progreso** = celdas vistas (`popcount(seen)`) + 20 x `kills` + 500 si
`state == CLEAR`; `done` = CLEAR. Un bot que no avanza no vale como medida. El bot de exploración lee
`dmap`, `seen`, `px/py/pf` y la lista de monstruos, calcula en Python un BFS hasta la celda no vista más
cercana (o hasta la llave/cerradura/escalera cuando ya no quedan) y lo traduce a giros y pasos; ataca a lo
que tenga delante y bebe poción con PV < 8 (por el menú).

| Qué | Cómo |
|---|---|
| Autoprueba del motor | `gb.selftest()` → 0 discrepancias en `view_clear`, `view_blit`, `vram_row20`, `rng_next` |
| Bancos | test: cada recurso con banco leído por `bank_memcpy`/`bank_read8` desde la ROM == fichero fuente (tiles, piezas, nivel, textos); build: lint de `SWITCH_ROM` y nada fijo por encima de `0x4000`; tras 10 000 f de bot, `_current_bank` en cada `vsync` es el del código (ningún helper deja un banco de datos mapeado) |
| Pasos, giros, choques | test por acción: estado → botón → `px/py/pf` en el frame de la entrada; `view_flips + 1` exactamente 3 f después; contra muro/puerta/monstruo/UP no se mueve y no hay cambio de mapa; mantener ↑ 120 f en un pasillo largo → 10 pasos; búfer: pulsar → en el enfriamiento se ejecuta al acabar |
| **Vista == modelo** | en cada cambio de mapa (bot de exploración entero + 4 giros en cada celda de un mapa de prueba): las filas 8-19 x columnas 0-19 del mapa visible (`gb.active_bg()`) == `fpview.compose(dmap, px, py, pf)` de E11 (mismas piezas, mismo orden). Columnas 20-31 y filas 7/20 == fondo de su fila |
| **Sin desgarro** | durante cada copia, el mapa visible no cambia ni un byte hasta el cambio de LCDC.3; el cambio ocurre con LY ≥ 144 (`vram_late == 0`) |
| Ventana intacta | tras cada copia de vista y cada superposición, `$9C00` filas 0-5 == HUD esperado (texto del estado y del registro reconstruido en Python) |
| Sprites == vista visible | cada frame: monstruo/objeto dibujados según `shown_x/y/f` y la regla de §2.3 (profundidad, tamaño, OAM 7-18), nunca más de 10 por línea (`gb.max_line_sprites()`), ninguno en líneas ≥ 96 salvo en menús |
| Efectos | balanceo: `scy_shadow` = 66, 65, 64 tras un paso; barrido: `scx_shadow` 8/16/24 durante un giro a la derecha y 0 tras el cambio |
| Combate (determinista) | con `rng_state` fijado y copia Python de `rng_next`: A con monstruo delante → `mon_hp` según la fórmula de §2.5 (acierto y fallo); enfriamiento de daga 20 f / espada 28 f; muerte → `kills + 1`, objeto soltado en la celda |
| Ataque de monstruo | test: monstruo adyacente al lado → flecha en OAM 0 durante la preparación (12/16/20 f según tipo); apartarse antes → sin daño; quedarse → daño según la fórmula y `atk_timer` reiniciado; escudo resta 32 a la precisión |
| IA | tests con monstruos congelados salvo uno: se mueve cada periodo hacia el héroe por la regla voraz, no entra en muros/puertas/escaleras/celdas ocupadas, deja de perseguir más allá de "olvida"; como mucho 1 monstruo piensa por frame |
| Puertas y llaves | A ante DOOR → DOOR_OPEN + vista nueva; LOCKED sin llave → igual y mensaje; con llave → `keys − 1` y abierta; UP → mensaje |
| Objetos | entrar en la celda → contador + mensaje + objeto desaparece; contador a 9 → se queda; poción con PV llenos no se gasta |
| Regeneración y muerte | sin monstruos alerta, +1 PV cada 300 f; `hp = 1` + golpe → DYING → GAMEOVER; CONTINUAR carga la partida |
| **Guardado** | GUARDAR → SRAM con firma y suma válidas; `ram = gb.power_off(); GB(rom, ram=ram)` → TITLE con CONTINUAR → todo el estado (§9.5) igual al guardado; alternancia de ranuras (2 guardados → 2 secuencias); corromper 1 byte de la ranura nueva en `ram` → carga la vieja; corromper las dos → no hay CONTINUAR; SRAM deshabilitada fuera del acceso |
| Menús y texto | Start → MENU con 5 opciones, auto-repetición 16/6 f, vuelta de abajo a arriba, B atrás, Start cierra; OBJETOS/ESTADO muestran los valores reales (tiles del mapa visible == texto esperado); registro: 2 caracteres/frame, sube al llegar un mensaje, FIFO de 4 |
| Automapa | Select → ventana oculta, celdas del mapa == `seen` + `dmap` (tiles del automapa), flecha según `pf`; se cierra con B/Select y la vista vuelve igual |
| **Presupuesto de frame** | bot de exploración con `cheat_flags` invencible hasta CLEAR (~20 000 f) + bot de "giros sin parar" 5000 f: `max_frame_lines < 120`, `vram_late == 0`; perfil (`gb.profile`) de `view_compose`, `view_blit`, `bgbuf_draw_vram`, `vq_draw_vram`, IA; `gb.worst_frames()` del peor frame |
| Bot justo (informativo) | sin trampas: muertes, pociones usadas, PV al llegar a la escalera y tiempo → guía para el playtest, no assert |
| **Lint del nivel** (Python puro) | `levels.parse` sobre `res/floor1.lvl`: todas las reglas de §6.2 |
| Flujo de pantallas | TITLE (CONTINUAR solo con partida válida) → PLAY → MENU → PLAY → GAMEOVER → TITLE; CLEAR al entrar en DOWN |
| Capturas | pasillo, cruce, puerta y cerradura delante, monstruo a d1/d2/d3, objeto en el suelo, menú de pausa, OBJETOS, automapa, título → revisión visual con Read; además los PNG de vistas canónicas de E11 |
| **Playtest humano** | sensación del paso (3 f + balanceo) y del giro (barrido), legibilidad de la profundidad y de los monstruos en LCD borroso, justicia del aviso de ataque, si uno se pierde (¿hace falta el automapa?), dificultad (objetivo: llegar a la escalera con ≤ 1 muerte), duración del piso |

---

## 12. Decisiones tomadas (2026-10-14)

El usuario eligió:
1. **Tema y título:** **TORRE HUNDIDA** (no la recomendación CRIPTA): la torre de un mago tragada por la
   tierra boca abajo; el aprendiz baja por sus pisos invertidos. Monstruos con las mismas mecánicas,
   re-temáticos: FAST = diablillo, GUARD = armadura viva (de ahí su armadura 1), SLOW = ojo flotante.
   Objetos: ESPADA → BÁCULO (STAFF), ESCUDO → AMULETO (AMULET).
2. **Un héroe** (el aprendiz).
3. **Combate en tiempo real lento con aviso** (preparación de 12-20 f, pausa en menús).
4. **Vista 160x96 arriba + HUD de 6 filas abajo en la ventana.**
5. **Automapa** a pantalla completa con Select, solo celdas vistas, en M1.
6. **Guardar en cualquier momento** desde la pausa (+ automático al bajar escaleras en M2).
7. **Al morir:** cargar la última partida guardada.
8. **Progresión:** solo por objetos en M1; experiencia y niveles en M2.
9. **Paso:** cambio instantáneo + balanceo de 3 f al andar y barrido de 3 f al girar.
10. **Pisos de M2:** 16x16 como M1.

(Opciones descartadas: ver historial de git, versión 0.1.)

### Arte y UI (fase 2, 2026-10-14)
- Paredes: ventanas tapiadas solo en los frentes laterales (variante a, elegida viendo
  `build/preview/variant_windows.png`); suelo de rombos de nervios; halo claro en todos los monstruos.
- UI: cursor de menú como tile de fondo; logo "TORRE" de tiles ya en M1; corazón parpadeando con vida
  <= 25 %; guardar sin confirmación; el cursor de la pausa **recuerda la última opción**; automapa solo
  con orientación; global `staff_owned`; mensajes PARTIDA CARGADA / EQUIPAS LA DAGA / EQUIPAS EL BACULO.

