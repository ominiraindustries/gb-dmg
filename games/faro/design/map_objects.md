# FARO M1b - objetos de los mapas (para el game-designer y el programador)

Mapas en `res/maps/*.map` (fuente de verdad; coordenadas = casillas absolutas del mapa). Vista previa:
`python harness/gb.py preview faro` -> `build/preview/map_<nombre>.png` (objetos en rojo).
Todos los guiones citados existen como STUB en `res/scripts/stubs.evs` (una linea `say` con la
intencion): al escribir el guion de verdad en su `.evs`, borrar el stub.

## Mapas

| Mapa | Tileset (`@ metatiles`) | Tamano | Contenido |
|---|---|---|---|
| `ISLA` | `metatiles` (exterior) | 12x8 sectores (192x128) | la isla entera de GDD 6.1; M1b usa 6 sectores, el resto es mar (deduplicado: 18 sectores unicos) |
| `CASA_INES` | `metatiles_interior` | 1x1 | casa de Ines (donde vive Leo) |
| `POSADA` | `metatiles_interior` | 1x1 | casa/cocina de Tomasa con posada |
| `TIENDA` | `metatiles_interior` | 1x1 | tienda de Varadero |
| `ENFERMERIA` | `metatiles_interior` | 1x1 | enfermeria |
| `FARO_PB` | `metatiles_faro` | 1x1 | faro, planta baja |
| `FARO_LENTE` | `metatiles_faro` | 1x1 | Sala de la Lente |

Sectores de `ISLA` usados (coordenadas de sector = las de GDD 6.1):
- (2,4) **Claro** tras las zarzas (machete). (3,4), (2,3), (3,3): bosque de relleno (sin acceso).
- (2,5)-(3,5) **Varadero** (casillas x 32-63, y 80-95). (4,4)-(4,5): sector de bruma (muro, sin acceso).
- (2,6) mar con el **muelle** (sale de Varadero hacia el sur).
- (3,6) **Sendero del Cabo**; (3,7) **Cabo** con el faro, acantilado y playa de rocas abajo.

Las salas interiores ocupan las casillas 3..12 x 3..11 de su sector (10x9 utiles); fuera, `VOID`.
Puerta interior: `DOORMAT` en (7,11); se llega desde fuera a (7,10) mirando arriba.

## Grafo de warps (llegada = casilla al otro lado de la puerta; el lint del build lo comprueba)

| Desde | Casilla | Hacia | Llegada |
|---|---|---|---|
| ISLA puerta casa de Ines | (36,82) | CASA_INES | (7,10) UP |
| ISLA puerta posada | (46,82) | POSADA | (7,10) UP |
| ISLA puerta tienda | (54,82) | TIENDA | (7,10) UP |
| ISLA puerta enfermeria | (60,82) | ENFERMERIA | (7,10) UP |
| ISLA delante de la puerta del faro | (53,120) | FARO_PB | (7,10) UP |
| CASA_INES / POSADA / TIENDA / ENFERMERIA felpudo | (7,11) | ISLA | debajo de su puerta: (36,83) (46,83) (54,83) (60,83) DOWN |
| FARO_PB felpudo | (7,11) | ISLA | (53,121) DOWN |
| FARO_PB escalera (pared) | (11,3) | FARO_LENTE | (11,4) DOWN |
| FARO_LENTE escalera (pared) | (11,3) | FARO_PB | (11,4) DOWN |

Nota para el programador: el warp del faro esta en la casilla de camino DELANTE de la puerta (las
piezas `LIGHTHOUSE_*` son solidas); se entra pisandola. Las escaleras `STAIRS_UP/DOWN` estan en la fila
de la pared (K_WARP, no solidas): se entra andando hacia arriba.

## Puertas y cambios permanentes

| Puerta | Como | Objetos |
|---|---|---|
| Zarzas del claro | 2 `BRAMBLE` en (40,78) (41,78): solo con habilidad CUT (Machete) | sin evento (lo hace el kind) |
| Puerta del faro | triggers `faro_cerrado` en (53,121) y (54,121) con `once=F_FARO_ABIERTO`: mientras no este puesta, el guion dice "cerrada" y hace `pwalk` de vuelta 1 casilla abajo. El trozo de camino de la puerta solo se alcanza por esas 2 casillas (lados: cartel y arbusto) | `K` |
| Muro de bruma al este de Varadero | 2 `FOG` en (63,83) (63,84) + `patch flag=F_BRUMA_1` -> `PATH_N` (mt 7) / `PATH_S` (mt 8). Detras sigue el sector de bruma (4,5): en M1b el anillo 1 termina la demo; en M2 ahi van las Marismas | `f`, `g`, cartel `M` |
| Lente encendida | 8 `patch flag=F_ANILLO_1` en FARO_LENTE: `LENS_rc` -> `LENSLIT_rc` (mt 23-26, 28-31; el centro no cambia) | `1`..`8` |

**Semantica de `trigger ... once=F_X` que necesitan estos mapas:** el trigger NO se dispara si
F_X esta puesta, y **el motor no la pone solo**: la pone el guion (asi `faro_cerrado` sigue
bloqueando hasta que otro guion ponga F_FARO_ABIERTO). Los guiones de un solo uso
(`intro_muelle`, `aviso_sendero`, `claro_entrada`, `lente_vista`) deben hacer `set` de su bandera.

Los `mt=` de los patch son ids numericos (orden de lineas del `.mt`): si se reordena un `.mt`, hay
que regenerarlos.

## Especies por ventana de 3x3 sectores (lint GDD 10.4) - CONFLICTO con `spawns.tbl`

La geometria de GDD 6.1 pone el claro en la fila 4, Varadero en la 5, el sendero en la 6 y el cabo
en la 7: las ventanas de filas 4-6 y 5-7 comparten Varadero + Sendero, asi que Varadero+Sendero
pueden tener como mucho 2 especies. Con la tabla actual salen 5 en cada ventana
(filas 4-6: Polifaro, Dunejo, Sapoyo, Pinzarro, Gavirata; filas 5-7: Pinzarro, Gavirata, Dunejo,
Sapoyo, Erizal). Propuesta que cumple <= 4:

| Tabla | Especies | Donde |
|---|---|---|
| `SPAWN_PLAYA_VAR` | Pinzarro (solo) | playa de Varadero |
| `SPAWN_SENDERO` | Dunejo, Pinzarro | Sendero |
| `SPAWN_CLARO` / `SPAWN_CHARCA` | Polifaro, Sapoyo (+ Dunejo/Pinzarro) | Claro (fila 4) |
| `SPAWN_CABO` | Gavirata, Erizal (+ Dunejo/Pinzarro) | Cabo (fila 7) |

Resultado: filas 4-6 = Pinzarro, Dunejo, Polifaro, Sapoyo; filas 5-7 = Pinzarro, Dunejo, Gavirata,
Erizal. Consecuencia buena para el diseno: para el anillo 1 (5 especies) hace falta el claro
(Polifaro o Sapoyo), es decir, el Machete del encargo del pescador: la puerta por habilidad es
obligatoria.

## Objetos por mapa

Recuento por sector (limites: <= 12 objetos, <= 6 NPC): Claro 7 (0 NPC), Varadero oeste 10 (2),
Varadero este 9 (1), muelle 1 (1), Sendero 6 (0), Cabo 8 (0); interiores 3-11. NPC: 3 aspectos en
total (ABUELA, PESCADOR, VECINA).

### ISLA - Varadero (2,5)-(3,5)
| Ch | Casilla | Tipo | Datos | Que debe hacer |
|---|---|---|---|---|
| i p t e | (36,82) (46,82) (54,82) (60,82) | warp | ver grafo | puertas de casa de Ines, posada, tienda, enfermeria |
| V | (42,85) | sign | cartel_varadero | "Varadero, puerto de Albor". Lore: antes salian barcos cada dia; desde la bruma, nadie |
| M | (62,85) | sign | cartel_bruma | camino de las Marismas cerrado por la bruma (pista: el faro la aparta) |
| f g | (63,83) (63,84) | patch | F_BRUMA_1 | ver Puertas |
| A | (35,86) | npc ABUELA LOOK | vecina_rosa | vecina mayor junto al jardin de Ines: recuerdos de Ines y del faro encendido; cuando falta el diario, "ve a ver a Tomasa" |
| C | (50,87) | npc VECINA WANDER | vecina_plaza | vecina en la plaza: tienda (lena, cebos, farolillos) y enfermeria gratis |
| N | (41,90) | npc PESCADOR LOOK | pescador_redes | pescador remendando redes en la playa: tutorial suave "los Pinzarro de la arena; acercate por detras" |
| B | (38,86) | forage | FORAGE_BAYAS | zarzamora del jardin de Ines (primera recoleccion, cerca de casa) |
| s S | (35,90) (49,90) | spawn | SPAWN_PLAYA_VAR r3 | playa: Pinzarro (tutorial de caza) |
| u | (34,89) | item | CONCHAS_50, F_PICK_VAR_1 | junto a la barca varada |
| v | (34,87) | item | POCION, F_PICK_VAR_2 | rincon del jardin de Ines |
| w | (56,92) (57,92) | trigger | aviso_sendero, once F_AVISO_SENDERO | al salir hacia el Sendero: "el faro esta al sur, cuidado con la hierba alta" (o retener a Leo si no tiene farolillos: entonces sin set hasta F_DIARIO) |
| I | (44,92) | trigger | intro_muelle, once F_INTRO | primer paso en el muelle: escena de los barcos parados por la bruma |
| F | (44,101) | npc PESCADOR STILL | pescador_muelle | al final del muelle: da la Honda (F_HONDA) y el encargo de 3 Plumas (F_ENCARGO_ON/OK) -> Machete |

### ISLA - Claro (2,4), tras las zarzas
| Ch | Casilla | Tipo | Datos | Que debe hacer |
|---|---|---|---|---|
| r | (40,76) (41,76) | trigger | claro_entrada, once F_CLARO_VISTO | primer paso tras las zarzas: luces de Polifaro entre la hierba |
| c | (43,68) | sign | cartel_claro | cartel viejo junto al campamento: "Aqui acampaba Ines" (pista para el diario) |
| q | (37,71) | spawn | SPAWN_CLARO r3 | hierba alta: Polifaro |
| Q | (40,74) | spawn | SPAWN_CHARCA r3 | orilla de la charca: Sapoyo |
| b | (37,74) | forage | FORAGE_BAYAS | zarzamora |
| o | (44,75) | item | FAROLILLO_FINO, F_PICK_CLARO_1 | premio por abrir el claro |
Hay un `CAMPSITE` en (42,69) (campamento seguro antes de cazar Polifaro).

### ISLA - Sendero del Cabo (3,6) y Cabo (3,7)
| Ch | Casilla | Tipo | Datos | Que debe hacer |
|---|---|---|---|---|
| d D | (59,99) (58,105) | spawn | SPAWN_SENDERO r3 | hierba alta: Dunejo |
| y | (55,104) | forage | FORAGE_BAYAS | zarzamora junto al campamento |
| m | (58,103) | item | MADERA, F_PICK_SEN_2 | lena al lado del `CAMPSITE` (56,102): ensena a acampar |
| j | (50,110) | item | POCION, F_PICK_SEN_1 | escondida en la hierba |
| h | (57,109) | sign | cartel_sendero | "Sendero del Cabo - Faro de Albor al sur" |
| L | (53,120) | warp | FARO_PB | puerta del faro |
| k | (52,120) | sign | cartel_faro | placa del faro: "Faro de Albor. Su luz guia a los barcos" (y quizas el ano de Ines) |
| K | (53,121) (54,121) | trigger | faro_cerrado, once F_FARO_ABIERTO | puerta cerrada hasta que alguien (Tomasa?) de la llave |
| x X | (60,114) (54,125) | spawn | SPAWN_CABO r3 | rocas del cabo / playa de rocas: Erizal, Gavirata |
| z | (57,126) | item | POCION, F_PICK_CABO_1 | playa de rocas (se baja por la escalera del acantilado (59,123)) |
| Z | (51,113) | item | CEBO_DULCE, F_PICK_CABO_2 | en la hierba del cabo |
Otro `CAMPSITE` en (55,118), junto al faro.

### Interiores
| Mapa | Ch | Casilla | Tipo | Datos | Que debe hacer |
|---|---|---|---|---|---|
| CASA_INES | b | (8,4) | sign | ines_estanteria | libros de Ines: criaturas, faros, recetas (lore) |
| CASA_INES | c | (6,3) | sign | ines_cuadro | cuadro del faro encendido (se lee mirando a la pared) |
| CASA_INES | o | (12,5) | item | REMO, F_REMO | el Remo viejo (primera arma) |
| POSADA | T | (6,4) | npc ABUELA STILL | tomasa | tras el mostrador (se le habla por el COUNTER (6,5)): diario y farolillos (F_DIARIO), cocina (`cook`), posada (`inn`) |
| POSADA | P | (7,8) | npc PESCADOR STILL LEFT | huesped_pescador | huesped: la bruma no deja faenar; rumor del faro |
| POSADA | H | (11,6) | npc VECINA STILL LEFT | huesped_vecina | huesped: pista de recetas (bayas + ...) |
| TIENDA | T | (8,4) | npc VECINA STILL | tendera | tras el mostrador (COUNTER (8,5)): `shop SHOP_VARADERO` |
| TIENDA | C | (10,7) | npc PESCADOR WANDER | cliente_tienda | pista: cebos y lena para acampar |
| ENFERMERIA | N | (9,4) | npc VECINA STILL | enfermera | tras el mostrador (COUNTER (9,5)): `heal` + F_ENFERMERIA |
| ENFERMERIA | P | (4,5) | npc PESCADOR STILL LEFT | paciente | se perdio en la bruma: aviso de peligro |
| FARO_PB | b | (6,4) | sign | faro_bitacora | bitacora de Ines: pagina 1 del diario (F_DIARIO_1, receta) |
| FARO_PB | o | (12,6) | item | TONICO, F_PICK_FARO_1 | objeto del faro |
| FARO_LENTE | V | (7,8) | trigger | lente_vista, once F_LENTE_VISTA | delante de la lente, primera vez: "seis anillos negros" |
| FARO_LENTE | L | (9,8) | sign | faro_lente | mesa del farero: con 5 especies (`reg_count 5`) -> `lamp_ring 1`, `set F_ANILLO_1`, `set F_BRUMA_1`, `demo_end` |
| FARO_LENTE | 1-8 | lente | patch | F_ANILLO_1 | ver Puertas |

## Pendiente (propuestas)
- Recoleccion de RAMAS: no hay metatile de "arbusto seco" con kind FORAGE (solo `BERRY`): todas las
  recolecciones del slice son BAYAS; la lena sale de la tienda y del objeto `m`. Si se quiere
  `FORAGE_RAMAS`, el pixel-artist dibuja un metatile `DRYBUSH`.
- La puerta del faro podria abrirse con la escena de Tomasa (F_DIARIO) para no anadir otro paso.
