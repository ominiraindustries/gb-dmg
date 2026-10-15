# MADRIGUERA — Documento de diseño

Estado: borrador (2026-10-15)    Versión: 0.1    Carpeta: `games/mazmorra`

> Aventura de acción cenital tipo Zelda con **una sola mazmorra** de 9 salas, pantalla a pantalla
> (al salir por un borde la cámara se desliza a la sala vecina, como en Link's Awakening).
> Tema, tono, nombres, historia y dificultad los decide el diseñador (el usuario lo pidió así).
> Lo caro de cambiar está en §12 "Decisiones pendientes".

---

## 1. Pitch

- **Género:** acción-aventura cenital en tiempo real, una mazmorra, pantalla a pantalla.
- **Fantasía:** eres **Tilo**, el nieto del campanero de Robledo, y bajas con la espada de madera de tu
  abuelo a la madriguera del **Rey Topo**, que ha robado la **Campana del Alba**. Sin su tañido la niebla
  no se va del valle.
- **Bucle principal:** entra en una sala, lee el peligro, limpia o esquiva, encuentra la llave o el
  camino, abre la puerta siguiente.
- **Qué lo hace distinto:** tono cálido y con humor (una madriguera con "palacio" de topo, carteles de
  "prohibido el paso a no-topos", un topo viejo que critica a su rey), una mazmorra corta y densa que
  se juega de una sentada, y un jefe que se esconde bajo tierra y se combate leyendo temblores.
- **Duración objetivo:** 20-30 min la primera vez (desglose en §6). Guardado automático al entrar en
  cada sala: se puede dejar en cualquier momento (sesión de autobús).
- **Referencias:**
  - *Link's Awakening* (GB): salas de 10x8 metatiles, transición deslizada, llaves pequeñas, llave del
    jefe, bombas que abren grietas, cofres que aparecen al limpiar la sala, levantar el objeto.
  - *The Legend of Zelda* (NES): estocada de espada en 4 direcciones, enemigos que se mueven por
    casillas, retroceso al recibir golpes.
  - Estudio: `games/world_lab` (mundo + actores + diálogo), `games/dungeon` (bancos, guardado),
    `games/shmup` (pools de proyectiles con `gbe_aim`), `games/platformer` (HUD arriba con corte LYC).

### Historia (corta, se cuenta en 2 páginas al empezar y 1 al final)
El Rey Topo odia el ruido. Una noche se llevó la Campana del Alba de Robledo a su madriguera, bajo el
cerro. Desde entonces la niebla no se levanta. Tilo baja a buscarla. Dentro se encuentra con los
súbditos del rey (babosas, topillos y escupidores) y con **Don Terrón**, un topo viejo que piensa que
su rey se ha vuelto un cascarrabias. Al vencer al Rey Topo, Tilo toca la campana y la niebla se va.

Tono: aventura amable, frases cortas con un punto de humor. Dificultad: **suave** (preferencia del
usuario): 3 corazones, enemigos que quitan medio corazón, continuar en la sala con la vida llena,
las bombas no hieren a Tilo.

---

## 2. Mecánicas

Convenciones: 59.73 fps; velocidades en 8.8 (`0x0100` = 1 px/f); coordenadas de mundo en px
(u16, el mapa mide 512x512 px); celdas de 16x16 (u8). **Todos los números de equilibrio van en
`res/data/rules.tbl` y `res/data/enemies.tbl` (§2.12), no en C.** Los valores marcados (*) son de
partida: ajustar en playtest.

Sin saltos ni gravedad: `harness/physics.py` no aplica. El movimiento es a velocidad constante y
entera en 8.8, así que las distancias son exactas (p. ej. 0x0140 x 60 f = 75 px justos) y los tests
las comprueban al píxel.

### 2.1 Sala y cámara
- Una sala = **10x8 celdas de 16 px = 160x128 px**, exactamente la pantalla bajo el HUD de 2 filas.
- El borde de la sala (fila 0, fila 7, col 0, col 9) es pared. Las puertas son bloques de 2x2 celdas
  que cruzan la frontera entre dos salas (2 celdas de la pared de cada sala), centrados:
  puertas arriba/abajo en las columnas 4-5, puertas a los lados en las filas 3-4. El hueco
  transitable de una puerta abierta mide **16 px** (las mitades exteriores de las dos celdas
  son jamba de pared, como en LA).
- Cámara fija en la sala: `cam_x = sala_col * 160`, `cam_y = sala_fila * 128 - 16` (la fila 0 de la
  sala sale en la línea 16 de pantalla, justo bajo el HUD).
- Todas las colisiones y el dibujado de objetos dentro de una sala se hacen en **coordenadas de
  pantalla de 8 bits** (la sala cabe entera en pantalla; regla de CLAUDE.md).

### 2.2 Transición entre salas (deslizado)
- Disparo: el centro de la caja de pies de Tilo entra en una celda de pared de la propia sala por un
  hueco de puerta (es decir, cruza la fila/columna de borde andando hacia fuera).
- Durante la transición la lógica del juego se congela (enemigos, proyectiles, temporizadores).
- La cámara se desliza **4 px/f**: 160 px en **40 f** (horizontal), 128 px en **32 f** (vertical).
- Tilo avanza **1 px/f durante los primeros 32 f** en la dirección de salida (32 px = las dos celdas de
  pared de la puerta) y termina en la primera celda interior de la sala nueva, mirando hacia dentro.
- Proyectiles, bombas, recogibles, "pufs" y enemigos de la sala vieja se borran en el primer frame
  (liberar es barato). Los de la nueva se crean **1 por frame** durante el deslizado (nunca más de 1
  aparición por frame: regla de CLAUDE.md), ya en su sitio, y entran en pantalla con el deslizado; no
  piensan hasta que acaba. Huecos de gact: 4 enemigos + Don Terrón + 1 libre (`GBE_GACT_MAX 6`).
- Al terminar: se guarda la partida (§2.11), se aplican puertas/cofres según banderas, y si la sala
  tiene compuertas (§2.8) se cierran 16 f después.
- `gbe_world`: la cámara se mueve ≤ 16 px/f (requisito del módulo). Con `world_edge_budget = 4`
  (máximo del módulo, `PREP_N`) entran 16 metatiles por cada 16 px de deslizado; una línea nueva
  necesita 12-13. Ajustado: el test de transición comprueba `world_lost == 0` y pantalla == mapa en
  **cada frame** del deslizado (riesgo R2).

### 2.3 Tilo: movimiento
| Parámetro | Valor | Unidad | Notas |
|---|---|---|---|
| Velocidad | 0x0140 (*) | 8.8 px/f | 1.25 px/f; 102 f para cruzar el interior de 128 px |
| Aceleración / frenada | instantánea | | estilo Zelda: arranca y para en seco |
| Diagonal | misma velocidad por eje | | más rápida en diagonal (aceptable en GB, feel.md) |
| Caja de pies (paredes) | x+3..x+12, y+8..y+15 | px | 10x8: la cabeza puede tapar la pared de arriba |
| Caja de daño (recibir) | x+2..x+13, y+4..y+15 | px | 12x12 |
| Empujón en esquinas | 1 px/f lateral | | si al avanzar choca solo una de las 2 sondas y el lado libre está a ≤ 6 px, Tilo se desliza hacia el hueco (cruzar puertas de 16 px sin precisión) |
| Orientación | último eje pulsado | | en diagonal se conserva la orientación si es una de las dos; si no, la horizontal |
| Animación andar | 2 frames, cambio cada 8 f | | abajo/arriba/lado (izquierda = lado con flip X) |
- Colisión: 2 sondas por el borde que avanza (`wattr_at(celda)` y bit SOLID), eje X y eje Y por
  separado. Los enemigos **no** bloquean a Tilo (tocar = daño).
- Casos límite: pulsar contra una pared no cambia la posición ni un subpíxel; en una puerta cerrada
  (llave/compuerta/grieta/jefe) se comporta como pared.

### 2.4 Espada (A)
| Parámetro | Valor | Unidad | Notas |
|---|---|---|---|
| Duración del golpe | 14 (*) | f | Tilo no se mueve durante el golpe |
| Caja activa | f 2..9 | f | estocada; el sprite de la espada se dibuja f 0..11 |
| Búfer | A en f 8..13 encadena otro golpe al acabar | | nunca exigir frame perfecto |
| Caja derecha | x+12..x+27, y+6..y+13 | px | 16x8 (incluye la parte pegada a Tilo) |
| Caja izquierda | x-12..x+3, y+6..y+13 | px | |
| Caja arriba | x+4..x+11, y-12..y+3 | px | 8x16 |
| Caja abajo | x+4..x+11, y+12..y+27 | px | |
| Daño | 1 | PV | |
| Golpes por enemigo y estocada | 1 | | el enemigo queda invulnerable 20 f tras el golpe |
| Hit-stop | 2 (*) | f | se congela todo salvo el sonido |
- La espada destruye las semillas de los escupidores (§2.6) y las rocas del jefe (§2.9).
- Con A junto a un cartel, un PNJ o un cofre (Tilo mirándolo y su caja de pies a ≤ 4 px) A **lee /
  habla / abre** en vez de golpear.
- Sprites: espada vertical = 1 sprite 8x16; horizontal = 2 sprites (16x8 dentro de dos 8x16).

### 2.5 Vida, daño y muerte
| Parámetro | Valor | Unidad | Notas |
|---|---|---|---|
| Corazones al empezar | 3 (= 6 medios) | | `hp` en medios corazones |
| Máximo | 4 (con el contenedor de R8); el HUD admite 5 | | |
| Retroceso al recibir daño | 2 px/f durante 8 f (16 px) | | dirección: eje dominante del vector atacante→Tilo; se para en paredes; sin control |
| Invulnerabilidad | 60 (*) | f | parpadeo: sprite oculto 4 f / visible 4 f |
| Temblor de pantalla | ±1 px, 6 f | | `shake_x/y` de gbe_video |
| Corazón recogido | +2 medios | | hasta el máximo |
| Muerte (`hp == 0`) | congelar 30 f, fundido a negro 16 f, pantalla FIN | | |
| Continuar | en la sala donde murió, en la posición en que entró, vida **llena** | | llaves, bombas, puertas y cofres se conservan; enemigos reaparecen |
- Contador `deaths` (u16) para la pantalla final.

### 2.6 Enemigos (`gbe_gact`: actores por casillas)
Los enemigos andan de celda en celda (estilo Zelda NES) con `gbe_gact`. Tilo es libre al píxel.
El juego pone `gact_px/py = 0xFF` (sin jugador para gact) para que los enemigos **puedan** entrar en
la casilla de Tilo, y dirige las persecuciones con `gact_step_toward`. `gact_terrain_ok` solo admite
celdas de suelo de la sala actual (nunca puertas ni paredes). Caja de colisión enemiga 12x12
(px+2..px+13). Destello al recibir golpe: `prop` con OBP1 (paleta invertida) 2 f sí / 2 f no
durante los 20 f de invulnerabilidad. Al morir: "puf" de 16 f (2 frames de 8 f) y posible
recogible (§2.10).

**E1 Babosa** (M1) — vaga sin rumbo.
| Parámetro | Valor |
|---|---|
| Comportamiento | `GACT_WANDER`, 24 f por celda (0.67 px/f) (*) |
| PV / daño por contacto | 2 / 1 medio |
| Retroceso al recibir golpe | 1 celda alejándose de Tilo a 6 f/celda (`gact_speed` + `gact_try_move`); si la celda no está libre, no retrocede |
| Animación | 2 frames, cada 12 f, mirando a la derecha + flip X (`GACT_ANIM2`) |

**E2 Topillo** (M2) — se esconde y asoma; se aprende leyendo el temblor.
| Estado | Duración | Qué hace |
|---|---|---|
| BAJO | hasta estar a ≤ 2 celdas (Manhattan) de Tilo | montículo; persigue con `gact_step_toward` a 20 f/celda; intangible e inofensivo |
| AVISO | 20 f (*) | quieto, el montículo tiembla ±1 px, sonido de tierra (telegrafía ≥ 12 f) |
| FUERA | 60 f (*) | asomado, vulnerable, daño por contacto 1 medio; no se mueve |
| CAVA | 12 f | baja; ya inofensivo e intangible |
| ESPERA | 90 f | montículo quieto antes de poder perseguir otra vez |
PV 1.

**E3 Escupidor** (M2) — bulbo-raíz fijo que escupe semillas.
| Parámetro | Valor |
|---|---|
| Comportamiento | `GACT_STILL`; mira a Tilo (eje dominante, 4 direcciones) |
| Ciclo | REPOSO 90 f → CARGA 20 f (sprite hinchado, sonido) → dispara 1 semilla → REPOSO |
| Semilla | 8x8 (caja 6x6), 0x0180 = 1.5 px/f en la dirección mirada, daño 1 medio; se rompe en paredes o con la espada |
| PV / contacto | 3 / 1 medio |
| Límite | 1 semilla en vuelo por escupidor |

### 2.7 Llaves y puertas
| Puerta | Cómo se abre | Persistencia |
|---|---|---|
| Abierta | siempre | - |
| Cerrojo (llave pequeña) | Tilo empuja contra ella 8 f con `keys ≥ 1`: `keys--`, se abre (4 celdas), sonido | bandera de la puerta |
| Jefe (Llave del Rey) | igual con `F_LLAVE_REY`; la llave no se gasta | bandera |
| Grieta (pared agrietada) | explosión de bomba que toque cualquiera de sus celdas | bandera |
| Compuerta | se cierra al entrar en la sala si no está limpia; se abre al morir el último enemigo | bandera "sala limpia" |
- Abrir = `world_set_cell` de las celdas del bloque 2x2 a los metatiles "abierta" de su lado. Las
  compuertas solo cambian las 2 celdas de su lado. Se reaplican desde las banderas al entrar en cada
  sala y al cargar partida (el mapa cabe entero en la caché de gbe_world, §9.2, así que los parches no
  se pierden mientras se juega).
- Sin llave: Tilo choca como con una pared; la primera vez sale el texto "Esta cerrada con llave." (M3).

### 2.8 Salas que se cierran y cofres que aparecen
- Sala con compuerta (R6) o cofre oculto (R3, R6): al limpiar todos sus enemigos suena el jingle de
  secreto, se abre la compuerta y aparece el cofre (`world_set_cell` a CHEST) y se pone la bandera
  `F_Rn_LIMPIA`. Con la bandera puesta, la sala ya no tiene enemigos al volver.
- El resto de salas: los enemigos reaparecen cada vez que se entra (estilo Zelda).

### 2.9 Bombas (objeto que abre camino, B) — recomendado frente al gancho (§12)
| Parámetro | Valor |
|---|---|
| Se consiguen | cofre de R6: 8 bombas; máximo 10 |
| Colocar | B con `bombs ≥ 1` y ninguna bomba activa (máx. 1): centro de la bomba = centro de los pies de Tilo + 10 px en la dirección mirada; si ese punto es sólido, en el centro de los pies |
| Mecha | 90 f; los últimos 30 f parpadea (tile alterno cada 4 f) |
| Explosión | 16 f, 2 frames 16x16; caja de efecto 40x40 centrada en la bomba |
| Efecto | 2 de daño a enemigos (y al jefe, §2.10); abre grietas y rompe rocas agrietadas cuyas celdas toque la caja; **no** hiere a Tilo (dificultad suave) |
| Alcance práctico | Tilo pegado a una pared agrietada (pies a ≤ 12 px de la celda) la abre siempre: con la regla del punto sólido la caja llega 16 px dentro de la pared |
| Anti-atasco | si `bombs < 2` y ya tienes bombas, cada enemigo muerto suelta bombas (+2) con 1/3 de probabilidad (tabla); nunca te quedas sin poder abrir una grieta |

### 2.10 Jefe: el Rey Topo (M3)
Objeto propio en C (no gact), 32x32 = 8 sprites 8x16 (dibujado simétrico: 4 tiles + flip X por
frame). Arena = interior de R9, 128x96 px.
| Estado | Fase 1 (PV 8..5) | Fase 2 (PV 4..1) | Qué pasa |
|---|---|---|---|
| BAJO | 120 f, 0x0080 px/f | 90 f, 0x00C0 px/f | montículo 16x16 sigue a Tilo en línea recta (8 direcciones de `aim_dir`); intangible e inofensivo |
| TEMBLOR | 30 f | 24 f | se para; temblor de pantalla ±1 px y ruido (telegrafía ≥ 12 f) |
| SALE | 16 f | 16 f | emerge en el sitio del montículo; contacto 2 medios desde aquí hasta que cava |
| LANZA | 3 rocas sueltas apuntadas, una cada 20 f, 0x0140 px/f | 2 abanicos de 3 rocas (dirección ±3 de 32), cada 24 f, 0x0140 px/f | rocas 8x8, daño 1 medio, la espada las rompe |
| MAREADO | 90 f | 70 f | vulnerable: 1 PV por estocada (invulnerable 20 f entre golpes); a los 3 golpes cava ya |
| CAVA | 16 f | 16 f | vuelve a BAJO |
- Bomba que explota sobre el montículo en BAJO o TEMBLOR: sale aturdido directamente a MAREADO
  durante 120 f y recibe 2 de daño (atajo para quien piense).
- PV 8. Muerte: 90 f de destellos con 4 "pufs" escalonados, temblor, luego aparece la **Campana del
  Alba** en el centro de la arena. Tocarla: Tilo la levanta (48 f), bandera `F_JEFE`, pantalla final.
- La puerta del jefe se cierra detrás de Tilo al entrar en R9 (vuelve a los metatiles "jefe cerrada")
  y se abre al vencerlo.

### 2.11 Guardado (M3)
- `gbe_save` (dos ranuras alternas, firma + checksum). Se guarda **automáticamente al terminar cada
  transición de sala** y al coger un objeto de cofre. Coste estimado < 5k T (40 bytes), en el último
  frame de la transición.
- Contenido (versión 1, 40 bytes): `flags[4]` (32 banderas), `keys`, `bombs`, `hp_max`, sala actual,
  posición de entrada (x, y en celdas + orientación), `deaths` (u16), tiempo de juego (u32 en frames),
  reserva.
- Título: "Continuar" solo si hay partida válida; "Nueva partida" pide confirmación si la hay
  ("Se borrara la partida. Seguro?" Si/No).
- Tras el final se conserva la partida con `F_JEFE`: "Continuar" lleva a R1 con todo abierto.

### 2.12 Datos (tablas, `harness/tables.py`)
`res/data/rules.tbl` (una fila por constante, `RULE_<ID>`, columna `v u16`):

| ID | Valor | | ID | Valor |
|---|---|---|---|---|
| LINK_SPEED | 0x0140 | | BOMB_FUSE | 90 |
| SWORD_FRAMES | 14 | | BOMB_BLINK | 30 |
| SWORD_ACTIVE_FROM / TO | 2 / 9 | | BOMB_BLAST | 16 |
| SWORD_BUFFER_FROM | 8 | | BOMB_BOX | 40 |
| HITSTOP | 2 | | BOMB_MAX | 10 |
| HURT_INVULN | 60 | | BOMB_CHEST | 8 |
| KNOCK_FRAMES / KNOCK_SPEED | 8 / 0x0200 | | DROP_BOMBS | 2 |
| HP_START | 6 | | PICKUP_LIFE | 300 (parpadea los últimos 60) |
| SCROLL_SPEED | 4 | | ENEMY_INVULN | 20 |
| SHUTTER_DELAY | 16 | | ITEM_HOLD | 48 |

`res/data/enemies.tbl`:
```
@ table enemies
@ prefix EN
@ col hp     u8
@ col dmg    u8          ; medios corazones por contacto
@ col fpc    u8          ; frames por celda
@ col t1     u8          ; BABOSA -, TOPILLO aviso, ESCUPIDOR reposo
@ col t2     u8          ; TOPILLO fuera, ESCUPIDOR carga
@ col t3     u8          ; TOPILLO espera
@ col shot   u16         ; velocidad de proyectil 8.8 (0 = no dispara)
@ col heart  u8          ; corazon al morir: 1 de cada N (0 = nunca)
@ col bombs  u8          ; bombas al morir si bombs < 2: 1 de cada N
BABOSA     2  1  24   0   0   0  0x0000  4  3
TOPILLO    1  1  20  20  60  90  0x0000  3  3
ESCUPIDOR  3  1   0  90  20   0  0x0180  4  3
```
`res/data/rooms.tbl`: ENTRADA, VESTIBULO, RAICES, CHARCOS, GALERIA, ALMACEN, POZO, ANTESALA,
TRONO con `name text 10` (para el mapa de pausa), `col u8`, `row u8`, `kind enum NORMAL CLEAR BOSS`.

Banderas (`res/scripts/flags.txt`, solo se añaden al final): `F_INTRO, F_L1, F_L2, F_LLAVE_REY,
F_BOMBAS, F_CORAZON, F_D1, F_D2, F_PUERTA_JEFE, F_GRIETA_R5, F_ROCAS_R4, F_R3_LIMPIA, F_R6_LIMPIA,
F_JEFE, F_CAMPANA, F_TERRON, F_CERROJO_VISTO` (17; `GBE_FLAG_BYTES 4`).

---

## 3. Controles

| Botón | En juego | En menús |
|---|---|---|
| Cruceta | mover en 8 direcciones | mover cursor (repetición 16/6 f, `gbe_menu`) |
| A | espada; leer / hablar / abrir cofre si estás delante | confirmar / pasar página del diálogo |
| B | poner bomba (cuando las tienes) | atrás |
| Start | pausa (mapa + inventario) | confirmar en el título; salir de la pausa |
| Select | sin uso | sin uso |

Sin acordes de botones. Durante el diálogo solo responde A (y la cruceta en Si/No).

---

## 4. Pantallas y flujo

```
TITULO --Start/A--> (Nueva partida: INTRO) --> JUEGO
   ^                (Continuar)            --> JUEGO (sala guardada)
   |
JUEGO = { SALA <-> DESLIZADO, SALA -> DIALOGO -> SALA, SALA -> OBJETO -> SALA,
          SALA <-Start-> PAUSA }
JUEGO --hp 0--> FIN ("Has caido") --Continuar--> JUEGO (misma sala)
                                  --Salir-----> TITULO
JUEGO --campana--> FINAL (texto + tiempo + caidas) --A--> TITULO
```
| Pantalla | Cómo se construye | Maqueta (`design/screens/`, la refina ui-designer) |
|---|---|---|
| TITULO | `transition()`: LCD apagado, carga `title` en el hueco compartido | `title.screen`: logo "Madriguera", subtítulo "La campana del alba", menú (M3) / "Pulsa Start" (M1) |
| JUEGO | `screen_build(JUEGO)`: carga `dungeon`, `ui`, todos los sprites, `world_load` | `play.screen` (HUD + sala R1) |
| DESLIZADO | en juego, sin apagar el LCD (§2.2) | - |
| DIALOGO | ventana: caja en las filas 2-6 bajo el HUD, corte LYC a la línea 56 | `dialogo.screen` |
| OBJETO | Tilo levanta el objeto 48 f + mensaje de 1 línea en la caja | - |
| PAUSA | ventana a pantalla completa (corte a 144: los sprites se ocultan solos) dibujada por `gbe_vq` antes de mostrarse | `pausa.screen` |
| FIN | `screen_build(FIN)`: solo `ui` + fuentes (no toca sprites) | `fin.screen` |
| FINAL | `screen_build(FINAL)`: `ui` + fuentes + sprite de la campana | `final.screen` |
Todas las transiciones de pantalla: fundido 16 f → construir con LCD apagado (`skip_measure`) →
fundido 16 f (`gbe_screen`). **Regla de VRAM: cada `screen_build` carga todos los huecos que usa su
escena**, sin suponer lo que dejó la anterior (lección de faro).

---

## 5. HUD e interfaz

### 5.1 HUD (ventana, filas 0-1, corte LYC en la línea 16 con `gbe_video` `hud_cut`)
```
col: 0         1         2
     01234567890123456789
f0:   ♥♥♥♥♥   b10  k2  K       ♥ corazones (lleno/medio/vacío), b icono bomba + 2 cifras,
f1:  ────────────────────      k icono llave + 1 cifra, K Llave del Rey; f1 línea separadora
```
- Corazones cols 1-5 (los que no tienes no se dibujan). Bombas cols 9-11 (ocultas hasta
  `F_BOMBAS`), llaves cols 13-14 (ocultas con 0 llaves), Llave del Rey col 16.
- Los tiles del HUD se preparan en `update()` cuando cambia un valor y se copian por `gbe_vq` (≤ 8
  tiles por cambio).
- Los sprites nunca tapan el HUD (gbe_video apaga OBJ por encima del corte).

### 5.2 Caja de diálogo (M3)
- Ventana filas 2-6 (5 filas): marco + **3 líneas de 18 caracteres** a 8 px de interlineado. Mientras
  está abierta el corte LYC baja a la línea 56; el juego está congelado.
- Escritura 1 carácter/f, A completa la página, flecha parpadeante (30 f) al esperar.
- Requiere dos cambios pequeños de motor (E5, E6): `gbe_tbox` con 3 líneas seguidas en vez de 2 a
  doble espacio, y `script.py` con líneas por página configurables por juego.

### 5.3 Fuente compacta (pedido del usuario)
- La fuente compartida es grande y espaciada. Nueva fuente compartida **`font_mini`** (+
  `font_mini_lower`, `font_mini_es`) en `harness/common/`, mismas etiquetas que `font`
  (`DIGIT0..`, `LETTER_A..`, `LOWER_A..`, `COMMA`...) para que `gbe_text`/`gbe_tbox` funcionen
  cambiando solo la base.
- Glifos: trazo de 1 px, mayúsculas de 6 px de alto (filas 1-6), altura x de 4 px (filas 3-6),
  descendentes en la fila 7, ancho 5 px en las columnas 1-5 (M, W, m, w hasta 6-7 px). Permite
  interlineado de 8 px (cajas de 3 líneas).
- Proceso: el pixel-artist hace una **imagen comparativa** (frase de diálogo y HUD con la fuente vieja
  y la nueva) antes de adoptarla; hasta entonces el juego usa `font`/`font_lower`/`font_es` con las
  mismas bases (mismo número de tiles: 72).
- Textos en mayúscula inicial ("Pulsa Start", "Coges una llave."), sin tildes ni eñe.

---

## 6. Progresión y dificultad

### 6.1 La mazmorra (rejilla de 3x4 salas; el mapa mide 32x32 celdas = 2x2 sectores)
```
          col 0             col 1                 col 2
fila 0   (roca)          R8 Antesala ==J== R9 Trono (jefe)
                             ||L2
fila 1   R6 Almacen ==S== R5 Galeria ==X== R7 Pozo
                             ||L1
fila 2   R3 Raices ------ R2 Vestibulo ------ R4 Charcos
                             ||
fila 3   (roca)          R1 Entrada
```
`--` puerta abierta, `L1/L2` cerrojo, `S` compuerta, `X` grieta (bomba), `J` puerta del jefe.

### 6.2 Recorrido previsto y tiempos
| Paso | Sala | Qué pasa | Min. aprox. |
|---|---|---|---|
| 1 | R1 Entrada | intro, cartel, 2 babosas: aprender espada | 1.5 |
| 2 | R2 Vestibulo | 3 babosas; cerrojo al norte (no hay llave) | 1.5 |
| 3 | R4 Charcos (opcional ahora) | ve el cofre tras rocas agrietadas; cartel "suenan huecas" | 1.5 |
| 4 | R3 Raices | babosas + topillos; al limpiar aparece cofre: **L1** | 2.5 |
| 5 | R2 → cerrojo D1 → R5 Galeria | topillos + escupidor; ve la grieta al este y el cerrojo D2 | 2.5 |
| 6 | R6 Almacen | compuerta se cierra; oleada mixta; cofre: **Bombas** | 3 |
| 7 | R5 → bomba en la grieta → R7 Pozo | escupidores + babosas; cofre: **Llave del Rey** | 3 |
| 8 | R5 → R2 → R4 | bomba en las rocas: cofre **L2** | 3 |
| 9 | R4 → R2 → R5 → cerrojo D2 → R8 | Don Terrón (consejo), topillos, cofre **Corazón** (4.º corazón) | 2.5 |
| 10 | R8 → puerta del jefe → R9 | Rey Topo | 3-4 |
| | | muertes, dudas, vueltas | 2-4 |
| | | **Total** | **24-30** |
Sin bloqueos posibles: los dos cerrojos solo se alcanzan en orden (L1 solo puede gastarse en D1) y
las bombas se reponen (§2.9). Un test de progresión en Python lo comprueba sobre el `.map` (§11).

### 6.3 Las salas (10x8 celdas; fila 0 arriba)
Leyenda: `#` pared, `.` suelo, `D` puerta abierta, `L` cerrojo, `S` compuerta, `X` grieta, `J` jefe,
`E` escalera de entrada (decorado sólido), `R` pilar/estatua (sólido), `~` charco (sólido), `o` roca
agrietada (sólida, se rompe con bomba), `C` cofre, `c` cofre oculto (aparece al limpiar), `T` cartel,
`N` Don Terrón, `@` inicio de Tilo, `b` babosa, `t` topillo, `e` escupidor, `B` Rey Topo.
Las puertas laterales ocupan la columna de pared en las filas 3-4; las de arriba/abajo las columnas
4-5 de la fila de pared. Ningún enemigo empieza a menos de 3 celdas de una puerta de entrada (lint).

```
R1 Entrada (1,3)   R2 Vestibulo (1,2)  R3 Raices (0,2)    R4 Charcos (2,2)
####DD####         ####LL####          ##########         ##########
#........#         #........#          #.t....~~#         #e......e#
#.R....R.#         #.b....b.#          #..R..b~~#         #.~~..~~.#
#..b.....#         D...RR...D          #........D         D........#
#......b.#         D...RR...D          #..b.R...D         D...b....#
#.R....R.#         #.....b..#          #~~....t.#         #.~~ooo~~#
#.T..@...#         #........#          #~~..c...#         #T..oCo..#
####EE####         ####DD####          ##########         ##########

R5 Galeria (1,1)   R6 Almacen (0,1)    R7 Pozo (2,1)      R8 Antesala (1,0)  R9 Trono (2,0)
####LL####         ##########          ##########         ##########         ##########
#.t......#         #R......R#          #e......e#         #N.......#         #R......R#
#.R..e.R.#         #..b..e..#          #..~~~~..#         #..R..R..#         #........#
D........X         #........S          X..~.C~..#         #........J         J...B....#
D..t..t..X         #.t......S          X..~..~..#         #..t..t..J         J........#
#.R....R.#         #..b.....#          #..b..b..#         #..R..R..#         #........#
#........#         #R...c..R#          #R......R#         #....C...#         #R......R#
####LL####         ##########          ##########         ####LL####         ##########
```
Contenido de cofres: R3 `c` = L1; R4 `C` = L2 (tras 5 rocas, una bandera para todas); R6 `c` = Bombas;
R7 `C` = Llave del Rey; R8 `C` = Corazón. Carteles: R1 "Madriguera del Rey Topo. Prohibido el paso a
quien no sea topo." / R4 "Estas rocas suenan huecas...". Don Terrón (R8): pregunta "Quieres un
consejo?" Si → "Cuando tiembla el suelo, el rey va a salir. Y una bomba en su monticulo le deja
tonto." No → "Pues suerte, chaval."

Objetos por sector del mapa (límite de world.py: 16): sector (0,0) 14 (R6 entero + parte de R5 y R8:
el más justo), (1,0) 10, (0,1) 9, (1,1) 13.

### 6.4 Dificultad
Sube por contenido, no por parámetros: R1-R2 solo babosas; R3 añade topillos; R4-R5 escupidores;
R6 oleada mixta (4 enemigos, el máximo de una sala); jefe con 2 fases. Máximo **4 enemigos vivos por
sala** (presupuesto de sprites por línea, §7). M1 usa como mucho 3.

---

## 7. Contenido y assets

### 7.1 Tilesets
| Asset (`res/*.tiles`) | Tipo | Tiles | Notas |
|---|---|---|---|
| `dungeon` | bg | ≤ 104 | ~41 metatiles (`res/metatiles.mt`, lista abajo). Tierra prensada con raíces y tablones; suelo claro y poco contrastado, actores oscuros |
| `title` | bg | ≤ 104 | logo + ilustración; comparte hueco con `dungeon` |
| `ui` | bg | 24 | corazón lleno/medio/vacío, iconos bomba/llave/Llave del Rey, línea del HUD, marco de caja (8), flecha, cursor, `UI_BLANK`, 5 tiles del mapa de pausa |
| `font_mini` + `_lower` + `_es` | bg | 42 + 26 + 4 = 72 | compartidas (harness/common); hasta adoptarla, `font` + `font_lower` + `font_es` (72) |
| `link` | sprite | 46 | Tilo 16x16: andar abajo/arriba/lado x2, golpe abajo/arriba/lado, levantar objeto (10 frames x 4) + espada 6 |
| `enemies` | sprite | 30 | babosa 8, topillo 12 (montículo + 2 asomado), escupidor 8 (normal/hinchado), semilla 2 |
| `fx` | sprite | 22 | bomba 4 (2 frames), explosión 8, puf 8, roca del jefe 2 |
| `items` | sprite | 16 | corazón 2, llave 2, Llave del Rey 2, bombas 2, contenedor 4, campana 4 |
| `npc` | sprite | 8 | Don Terrón 2 frames |
| `boss` | sprite | ≤ 36 | Rey Topo 32x32 simétrico: normal, lanzando, mareado (8 tiles cada uno) + montículo 4 |

Metatiles (`res/metatiles.mt`, `@ attr SOLID 0x80`; `GBE_WORLD_MT 64`):
FLOOR, FLOOR2, WALL_T/B/L/R, WALL_TL/TR/BL/BR (10) · puertas abiertas DOOR_T_L/R, DOOR_B_L/R,
DOOR_L_U/D, DOOR_R_U/D (8) · LOCK_T_L/R, LOCK_B_L/R (4) · SHUT_R_U/D (2) · CRACK_R_U/D,
CRACK_L_U/D (4) · BOSS_R_U/D, BOSS_L_U/D (4) · STAIRS_L/R, BLOCK, ROCK_CRACKED, WATER, CHEST,
CHEST_OPEN, SIGN (8) = **40 metatiles**. Solo existen las orientaciones que la mazmorra usa (sin flip
de fondo en DMG cada orientación cuesta tiles). Estimación de tiles únicos: suelo 6, paredes y
esquinas 26, puertas abiertas 16, cerrojos 8, compuerta 4, grietas 8, jefe 8, resto 28 = **104**.

### 7.2 Casas de VRAM (se convierte en `vram_order` + `vram_scenes` de game.json)
LCDC bit 4 = 0 (por defecto en GBDK): fondo 0-127 en $9000, 128-255 en $8800 = tiles de sprite 128-255.
Sprites 8x16 (bases pares). Las bases de fondo las calcula el build (`vram.h`, `VRAM_*`); las de
abajo son las previstas.

| Tileset | Capa | Tiles | Hueco previsto | Comparte con | Quién lo (re)carga |
|---|---|---|---|---|---|
| `dungeon` / `title` | BG | ≤ 104 | 0-103 | entre ellos | `screen_build(TITULO)` carga `title`; `screen_build(JUEGO)` carga `dungeon` siempre (también al volver de FIN). La pausa y el diálogo no tocan tiles |
| `ui` | BG | 24 | 104-127 | - | todos los `screen_build` |
| `font_mini` | BG | 42 | 128-169 | - (ocupa tiles de sprite 128-169) | todos los `screen_build` |
| `font_mini_lower` | BG | 26 | 170-195 | - | todos |
| `font_mini_es` | BG | 4 | 196-199 | - | todos |
| (libre) | | | 200-211 | margen para que `dungeon` crezca | - |
| `link` | SPR | 46 | 0-45 | - | `screen_build(JUEGO)` y `(FINAL)` |
| `enemies` | SPR | 30 | 46-75 | - | `screen_build(JUEGO)` |
| `fx` | SPR | 22 | 76-97 | - | `screen_build(JUEGO)` |
| `items` | SPR | 16 | 98-113 | - | `screen_build(JUEGO)` y `(FINAL)` |
| `npc` | SPR | 8 | 114-121 | - | `screen_build(JUEGO)` |
| `boss` | SPR | ≤ 36 | **212**-247 | - | `screen_build(JUEGO)` (residente: R9 se entra deslizando) |
- **Ningún hueco de sprites se comparte**: todo cabe residente. El único hueco compartido es
  `dungeon`/`title`, y lo recarga cada `screen_build` que lo usa.
- Límite duro: el fondo acaba antes de 212 (test: `VRAM_FONT_MINI_ES + 4 <= 212`).
- Mapa de la ventana ($9C00): filas 0-1 HUD, filas 2-6 caja de diálogo, filas 2-17 panel de pausa
  (al abrir la pausa se dibuja encima; la caja se redibuja entera al abrirse).

Borrador de game.json:
```json
"vram_order": [["dungeon", "title"], "ui", "font_mini", "font_mini_lower", "font_mini_es"],
"vram_scenes": {
  "title":   { "spr": [] },
  "play":    { "spr": [[0, "link"], [46, "enemies"], [76, "fx"], [98, "items"], [114, "npc"], [212, "boss"]] },
  "pause":   { "spr": [] },
  "gameover":{ "spr": [] },
  "ending":  { "spr": [[0, "link"], [98, "items"]] }
}
```

### 7.3 Sprites y OAM
Reparto fijo de OAM (lo más bajo = más prioridad): 0-1 Tilo, 2-3 espada, 4-5 bomba/explosión,
6-15 actores gact (5 x 2: 4 enemigos + Don Terrón), 16-19 proyectiles (pool), 20-23 recogibles,
24-25 puf, 26-33 Rey Topo (8), 34-39 libres.

| Momento | Sprites en pantalla | Peor línea |
|---|---|---|
| M1, R2 con 3 babosas | Tilo 2 + espada 2 + 6 + recogible 1 + puf 2 = 13/40 | 2 + 2 + 3x2 = **10/10** (3 babosas alineadas con Tilo golpeando de lado) |
| R6 oleada: 4 enemigos + 2 semillas + bomba | 2 + 2 + 8 + 2 + 2 + 2 = 18/40 | 4 enemigos alineados + Tilo + espada = 12 → se rota el orden de dibujo de gact cada frame (E4): parpadeo de 1 frame, nunca un enemigo invisible |
| Jefe: Rey Topo + 3 rocas + Tilo + bomba | 8 + 3 + 4 + 2 = 17/40 | 4 (jefe) + 3 rocas recién lanzadas + 2 + espada 2 = 11 en el frame del abanico → las 3 rocas salen con 0, 6 y 12 f de desfase (en M3 se mide; si parpadea, aceptable) |

### 7.4 Totales
Fondo en juego: 104 + 24 + 72 = **200 tiles** (128 propios + 72 compartidos). Sprites: 122 + 36 =
**158 tiles**. Sprites en pantalla peor caso **18/40**; por línea **10/10** sin rotación en M1, 12 con
rotación en M2 (R6, rara).

---

## 8. Sonido
Sin música en M1-M3: el arnés no tiene reproductor de música (ver §9.5). Efectos con `gbe_sfx`
(prioridad por canal):
| Efecto | Canal | Prioridad | Hito |
|---|---|---|---|
| Espadazo (siseo corto) | 4 | 1 | M1 |
| Golpe a enemigo | 1 | 2 | M1 |
| Enemigo muere | 4 | 2 | M1 |
| Tilo herido (grave) | 1 | 3 | M1 |
| Recoger corazón | 2 | 1 | M1 |
| Pasos de transición (ninguno) / puerta deslizando | - | - | - |
| Cerrojo abierto / compuerta | 4 | 2 | M2 |
| Bomba colocada (clic) / explosión (larga) | 1 / 4 | 1 / 3 | M2 |
| Secreto (arpegio ascendente) | 1 | 3 | M2 |
| Cofre / objeto levantado (fanfarria corta) | 1+2 | 3 | M2 |
| Topillo tiembla / escupidor carga | 4 / 2 | 1 | M2 |
| Letra del diálogo (blip) | 2 | 0 | M3 |
| Jefe: temblor, rugido, golpe, muerte | 4 / 4 / 1 / 4 | 2-3 | M3 |
| Menú: mover / confirmar | 2 | 1 | M1 (título) |

---

## 9. Técnica

### 9.1 Cartucho
**MBC5 + RAM + batería, 64 KB (4 bancos)**: `["-autobank", "-Wm-yt0x1B", "-Wm-yo4", "-Wm-ya1"]`.
`GBE_BANKED` y `GBE_SELFTEST_BANKED` desde M1 (lección de faro: el banco 0 se llenó con el motor).
Si en M3 hace falta, subir a 128 KB (`-Wm-yo8`) sin otros cambios.

### 9.2 Cómo se hacen las salas con el motor existente (decisión §12.2)
- La mazmorra entera es **un solo `res/maps/mazmorra.map`** de `harness/world.py`: `@ size 2 2`
  (32x32 celdas), salas en bloques de 10x8 (`sala (c, f)` = celdas x 10c..10c+9, y 8f..8f+7), columnas
  30-31 y huecos sin sala rellenos de pared, `@ border WALL`.
- Con 2x2 sectores, la caché 3x3 de `gbe_world` contiene **siempre el mapa entero** tras
  `world_load`: no hay cargas de sector durante el juego y los parches `world_set_cell` (puertas,
  cofres, rocas) no se pierden. Se reaplican desde banderas al entrar en cada sala por robustez.
- El "pantalla a pantalla" es solo la cámara: fija en la sala, deslizada a 4 px/f entre salas
  (`world_update(celda de Tilo, cámara)`); el anillo del BG y la cola de bordes de `gbe_world` ya
  dibujan lo que entra.
- Objetos del mapa (`world_objects` en game.json):
  `"enemy": ["kind enum BABOSA TOPILLO ESCUPIDOR"]`,
  `"door": ["kind enum LOCKED SHUTTER BOSS CRACKED", "side enum UP DOWN LEFT RIGHT", "flag flag"]`
  (1 registro en la celda superior izquierda del bloque 2x2),
  `"chest": ["item enum LLAVE LLAVE_REY BOMBAS CORAZON", "flag flag", "hidden bool"]`,
  `"rock": ["flag flag"]`, `"sign": ["script script"]`, `"npc": ["script script"]`, `"start": []`,
  `"boss": []`. Al entrar en una sala el juego recoge los objetos de los sectores que la tocan
  (hasta 4 llamadas a `world_events`, una por frame durante el deslizado) y filtra por rectángulo.
- Vista previa: `python harness/gb.py preview mazmorra` (mapa + objetos) para revisar las salas como imagen.

### 9.3 Módulos de gbe que usa
| Módulo | Para qué | Hito |
|---|---|---|
| `gbe_frame`, `gbe_oam`, `gbe_sfx`(+asm) | bucle, medición, OAM directo, efectos | M1 |
| `gbe_video` | sombras, fundidos, temblor, **HUD arriba con corte LYC** (`hud_cut`, línea 16) | M1 |
| `gbe_screen` | transiciones con fundido y LCD apagado | M1 |
| `gbe_bank`, `gbe_vram.s` | assets en bancos, metatiles a VRAM | M1 |
| `gbe_world` (+asm) | mapa, colisión `wattr_at`, cámara deslizada, parches | M1 |
| `gbe_gact` (+asm) | enemigos y PNJ por casillas, dibujo 16x16 | M1 |
| `gbe_vq`, `gbe_text` | HUD, textos de pantallas | M1 |
| `gbe_rng` | soltar objetos, deambular | M1 |
| `gbe_selftest` | asm == C de world/gact (`gb.selftest()`) | M1 |
| `gbe_pool`, `gbe_aim` (+asm) | semillas y rocas del jefe (`fire`, `aim_dir`) | M2 |
| `gbe_flags` | banderas de puertas/cofres/salas | M2 |
| `gbe_tbox`, `gbe_script` | carteles, Don Terrón, intro, mensajes de objeto | M3 |
| `gbe_menu` | menú del título, Si/No, pausa | M3 |
| `gbe_save` | guardado automático | M3 |

### 9.4 Trabajo de motor nuevo (riesgos)
| Id | Qué | Hito | Tamaño |
|---|---|---|---|
| E1 | Cámara de sala sobre `gbe_world`: fija + deslizado 4 px/f con `world_edge_budget = 4`; test pantalla == mapa en cada frame del deslizado | M1 | pequeño (código de juego) |
| E2 | Uso de gact para combate: `gact_px = 0xFF`, retroceso de 1 celda (`gact_speed` + `gact_try_move` mientras otro comportamiento manda), destello por `prop`. Si gact no deja forzar el paso, pequeña extensión `gact_push(i, dir, fpc)` | M1 | pequeño |
| E3 | Fuente `font_mini` compartida y soporte de nombre de fuente en `screens.py`/`preview.py`/`GB.tile_text` (hoy asumen `font`/`font_lower`) | M1 (arte) / M2 (adopción) | pequeño |
| E4 | Rotación del orden de dibujo en `gact_draw` (empezar en un actor distinto cada frame) para > 10 sprites por línea | M2 | pequeño (asm) |
| E5 | `gbe_tbox`: 3 líneas a 8 px (`tbox_line_step`), caja de 5 filas | M3 | pequeño |
| E6 | `script.py`: líneas por página configurables por juego (game.json) | M3 | pequeño |
| E7 | Cambiar la línea del corte LYC en tiempo de juego (16 / 56 / 144) desde VBlank (`video_set_cut`) | M3 | pequeño |

### 9.5 Lo que es demasiado grande para el arnés hoy (fuera de alcance)
Música (no hay reproductor: integrar hUGEDriver sería un hito de motor propio, M4 opcional), un mundo
exterior, varias mazmorras, gancho/pozos/bloques empujables, fuente de ancho variable, intercambio de
objetos en A/B.

### 9.6 Presupuesto de CPU (objetivo: peor frame < 100 de 154 líneas)
Con costes medidos de `budgets.md` y world_lab (gact: mover 4 actores ~1k, dibujar ~950 T cada uno,
pensar hasta 6k):

| Trabajo (frame pico: R6, 4 enemigos, 2 semillas, explosión, Tilo golpeando) | T |
|---|---|
| frame/vídeo/sonido | 1.0k |
| Tilo (entrada, 4 sondas `wattr_at`, empujón, animación) | 3.0k |
| Espada vs 4 enemigos + 2 semillas (cajas de 8 bits) | 2.4k |
| Contacto enemigos/proyectiles vs Tilo | 2.4k |
| `gact_update` (mover + 1 pensador) | 6.0k |
| Lógica C por enemigo (estados) 4 x 800 | 3.2k |
| `gact_draw` 4 x 950 | 3.8k |
| Semillas (`pool_move` + paredes) | 1.0k |
| Explosión: celdas tocadas + enemigos (1 frame) | 4.0k |
| OAM Tilo/espada/fx/recogibles (6 x 300) | 1.8k |
| HUD, RNG, `world_update` quieto | 3.0k |
| **Total estimado** | **~31.6k T ≈ 69 líneas** |
Margen: las estimaciones de GDD han salido 1.5-2.5x bajas (shmup); con 1.5x serían ~104 líneas. Por
eso: máximo 4 enemigos por sala, y si el bot mide > 90 líneas, lógica de enemigos en frames alternos
(mitad cada frame) antes de añadir contenido. Deslizado: `world_update` con bordes ~5k + dibujo de
hasta 5 actores 4.8k + 1 aparición ~2k + Tilo ~1k ≈ 13k T (28 líneas). Jefe: ~13k T.
VBlank (~3600 T útiles): bordes del mundo 4 x 100 T + `gbe_vq` ≤ 40 tiles x 20 T (pausa) o ≤ 8
(HUD/texto) → < 1.5k T.

### 9.7 ROM, RAM y bancos
- Banco 0 (≤ 14 KB): gbe hot (frame, oam, video, screen, bank, vram, world, gact asm, vq, text, sfx,
  flags, rng, pool/aim asm) ~8 KB + juego en caliente (Tilo, combate, enemigos, sala) ~5 KB.
- Banco 1 (código frío, `BANKED`): pantallas (título, pausa, fin, final), entrar/salir de sala,
  puertas y cofres, jefe, operaciones de guion, glue del guardado; gbe tbox/menu/save/gact C y la
  autoprueba (`GBE_BANKED`, `GBE_SELFTEST_BANKED`).
- Bancos 2-3: tiles (~(104+104+24+72+158) x 16 B ≈ 7.4 KB), mapa (4 sectores 1 KB + objetos ~0.6 KB),
  guiones ~1.5 KB, tablas < 0.5 KB. Total ROM ~35-40 KB de 64.
- WRAM (8 KB): caché de gbe_world 2304 + rejilla/gslot 512 + metatiles (64) 320 + gact (8 x 24) 192 +
  pool 128 + tbox/script ~400 + juego ~400 + pila ≥ 512 → ~4.8 KB (~60 %).
- SRAM: 2 ranuras de 40 B (gbe_save).

---

## 10. Hitos

### M1 — rebanada vertical (lo más pequeño, pulido)
- Título ("Madriguera", "Pulsa Start") → juego.
- **3 salas: R1, R2, R3** del mapa final (las salidas de R2 hacia R4 y R5 son pared en M1; el resto
  de salas, roca).
- Tilo: movimiento, colisión, empujón en esquinas, espada, daño, retroceso, invulnerabilidad, muerte →
  FIN ("Has caido" / "Continuar") → misma sala con la vida llena.
- **1 enemigo: la babosa** (≤ 3 por sala), con retroceso, destello, puf y corazones que suelta.
- HUD de corazones (ventana arriba con corte LYC).
- Transiciones deslizadas entre las 3 salas.
- Efectos de sonido de M1 (§8).
- Arte definitivo de Tilo, babosa, dungeon (los metatiles de R1-R3), ui (corazones, línea) y título;
  **comparativa de fuente** del pixel-artist (se adopta en M2 si el usuario la aprueba).
- Medido: peor frame < 100 líneas con bot, `vram_late == 0`, `world_lost == 0`, `vram_errors` limpio.

### M2 — contenido
Las 9 salas (sin el jefe: R9 vacía con la campana de prueba), llaves pequeñas y cerrojos, compuerta,
cofres (visibles y ocultos), bombas, grietas y rocas, topillo y escupidor, recogibles de bombas,
rotación de dibujo gact (E4), adopción de `font_mini` (E3), test de progresión del mapa, bots de
playtest de las 9 salas.

### M3 — jefe, guardado, texto, pulido
Rey Topo, Campana y pantalla final; guardado automático + Continuar; carteles, Don Terrón, intro y
mensajes de objeto (E5-E7); pausa con mapa e inventario; jingles y efectos que faltan; ajuste de
números con los informes del playtester.

### M4 — prueba en hardware real
Flashcart en DMG: corte LYC, deslizado, guardado tras apagar; (opcional) música si se añade un
reproductor al arnés.

---

## 11. Plan de pruebas
| Qué | Cómo |
|---|---|
| Movimiento | test: mantener derecha 60 f desde el centro de R1 → `link_x` +75 px exactos; diagonal +75/+75 |
| Paredes | test: andar 120 f contra cada pared de R1 → se para en el borde exacto de la caja de pies (x+3/x+12, y+8) |
| Empujón en esquinas | test: Tilo 5 px desalineado bajo la puerta norte, mantener arriba → cruza la puerta en ≤ 40 f; 7 px desalineado → no cruza |
| Espada | test: babosa quieta (WANDER off) a 4 px a la derecha; A → en f 2 `en_hp` baja a 1, retrocede 1 celda; segundo golpe tras 20 f → muere, puf |
| Búfer y bloqueo | test: A en el f 10 del golpe encadena otro; Tilo no se mueve durante los 14 f |
| Daño | test: babosa encima → `hp` 6→5, retroceso 16 px (menos si hay pared), `invuln` 60, sin segundo daño dentro de los 60 f |
| Muerte y continuar | test: `hp = 1` + golpe → estado FIN; Continuar → misma sala, posición de entrada, `hp == hp_max`, `deaths == 1` |
| Recogibles | test con semilla de RNG fija (`gb.rng_next`): la babosa suelta corazón cuando toca; recogerlo suma 2 medios sin pasar del máximo; desaparece a los 300 f |
| Transición | test: subir por la puerta de R1 → tras 32 f `room == VESTIBULO`, `cam_y` −128, Tilo en la fila 6 de R2; **en cada frame** pantalla == modelo de `world.py` (como world_lab), `world_lost == 0`, `vram_late == 0`; después `gb.vram_errors("play") == []` |
| Enemigos en la transición | test: tras entrar, nº de actores == objetos `enemy` de la sala; los de la sala vieja liberados; nunca 2 apariciones en un frame (contador) |
| HUD | test: con `hp` 0..10 los tiles de las cols 1-5 de la ventana son lleno/medio/vacío correctos (`gb.tile_text`/tiles de `ui`) |
| Pantallas fijas | `gb.mockup_errors("title")`, `("fin")`, `("final")`, `("pausa")` tras cada transición, y `gb.vram_errors(escena)` |
| Autoprueba | `gb.selftest()` (world + gact asm == C) |
| Presupuesto de frame | bot que recorre R1→R2→R3→R2→R1 golpeando a lo que tenga cerca durante 6000 f; **debe avanzar** (salas visitadas, `run_bot` con `progress`); `max_frame_lines < 100`, `vram_late == 0`; `gb.worst_frames` en el informe |
| Lint del mapa (Python, sin ROM) | `world.parse` del `.map`: cada sala 10x8 con paredes en el borde, puertas simétricas en las dos salas, ningún enemigo a < 3 celdas de una puerta, ≤ 4 enemigos por sala, ≤ 16 objetos por sector |
| Progresión (M2) | BFS en Python sobre el `.map` con estado (llaves, bombas, banderas): la campana es alcanzable, ningún orden de juego gasta una llave en la puerta equivocada, sin salas sin salida |
| Llaves/puertas/bombas/compuertas (M2) | test por mecánica: estado inicial → acción → asserts sobre `keys`, banderas, metatile de la celda (`wmt_at`) y pantalla |
| Topillo / escupidor (M2) | tests de tiempos: aviso ≥ 20 f antes de ser peligroso; la semilla sale a 1.5 px/f en la dirección de Tilo; espada la rompe |
| Jefe (M3) | tests de fases y PV (8 golpes, bomba en el montículo = 2 y mareado 120 f); bot que lo vence |
| Guardado (M3) | `ram = gb.power_off(); GB(rom, ram=ram)` a mitad de mazmorra → Continuar restaura sala, llaves, bombas, puertas, cofres; ranura corrupta → la anterior |
| Diálogo (M3) | `script.py` lint (longitudes, banderas); test: A en el cartel → `tbox_visible`, corte en 56, `vram_errors` limpio |
| Playtest con bots (`GB.human`) | novato / medio / experto: tiempo hasta la campana (objetivo medio 20-30 min), muertes por sala, atascos |
| Humano | feel de la espada y el retroceso, legibilidad de la fuente nueva, dificultad, si las salas se entienden sin texto |

---

## 12. Decisiones pendientes (para el usuario)
Solo lo caro de cambiar una vez construido; el resto (tema, nombres, historia, dificultad, números)
está decidido arriba y se cambia barato.

- [ ] **Objeto que abre camino: bombas (recomendado) / gancho.** Bombas: reutilizan temporizador +
  caja de efecto contra metatiles agrietados y sirven contra el jefe; ningún motor nuevo y nada de
  sprites en fila. Gancho: cadena de 3-4 sprites en una línea (con Tilo, espada y 2 enemigos pasa de
  10 por línea), estado de "volar sobre pozos" con pozos en el mapa y blancos enganchables: más motor
  y más riesgo.
- [ ] **Formato de las salas: un mapa de `gbe_world` con cámara por sala (recomendado) / motor de
  salas propio.** El mapa de world.py reutiliza la caché, el anillo del BG, la cola de bordes, los
  objetos, la vista previa y `gbe_gact` (que depende de gbe_world), a cambio de ~3.2 KB de WRAM y de
  que las salas no coinciden con los sectores. Un motor propio (`gbe_room`: sala de 80 bytes, volcado
  por columnas al deslizar) gastaría menos WRAM pero obliga a reescribir los actores y la vista previa.
- [ ] **Enemigos por casillas con Tilo libre (recomendado) / todo libre al píxel.** Por casillas =
  `gbe_gact` tal cual (medido, con asm) y un combate legible estilo Zelda NES; libre al píxel daría
  enemigos más fluidos (murciélagos en diagonal) pero pide un módulo de actores libres con colisión
  contra el mapa que hoy no existe.

---

## 13. Riesgos
| Riesgo | Mitigación |
|---|---|
| R1 Coste de frame con 4 enemigos (faro acabó en 119/120 con 16 actores) | máx. 4 enemigos por sala, bot de presupuesto desde M1, lógica a medias en frames alternos si > 90 líneas |
| R2 La cola de bordes de gbe_world va justa a 4 px/f (13 metatiles por línea, 16 por cada 16 px) | `world_edge_budget = 4`, test pantalla == mapa en cada frame del deslizado; si falla, deslizar a 3 px/f (53 f / 43 f) |
| R3 gact no pensado para combate (casilla del jugador reservada, sin retroceso, sin parpadeo) | E2: `gact_px = 0xFF`, retroceso con `gact_try_move`, destello por `prop`; extensión mínima si hace falta |
| R4 > 10 sprites por línea en R6 y en el abanico del jefe | E4 (rotación), desfase de las rocas; medir con `gb.vram_errors` y capturas |
| R5 Objetos por sector: el sector (0,0) lleva 14 de 16 | lint en el test del mapa; si se pasa, mover un enemigo de R6 o el cofre a otra celda del sector vecino |
| R6 VRAM de fondo justa (200 de 212 antes de chocar con el jefe) | presupuesto de 104 tiles para `dungeon` desde el primer arte; test de límite |
| R7 Banco 0 (motor grande) | `GBE_BANKED` y código frío en banco 1 desde M1; el build avisa |
| R8 La fuente nueva no gusta o pide cambios en la herramienta | comparativa antes de adoptarla; el juego funciona con la fuente vieja (mismas bases) |
| R9 Diálogo en la ventana bajo el HUD (corte LYC variable) | E7 pequeño; test de `tbox_visible` + `vram_errors` + captura |
| R10 Sin música el juego se siente vacío | efectos cuidados en M1-M3; música como hito de motor aparte (M4) |
