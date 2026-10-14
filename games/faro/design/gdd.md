# FARO: la isla en la bruma — Documento de diseño

Estado: aprobado (2026-10-14)    Versión: 1.1 (datos M1b en `res/data/*.tbl`)    Autor: game-designer    Fecha: 2026-10-14

> Carpeta `games/faro`. RPG de captura y supervivencia para DMG, de calidad comercial, 10-15 h.
> El jugador **lucha él mismo** contra criaturas visibles en el mapa, las caza para comer o las captura
> para registrarlas, y con cada especie registrada el faro de la isla brilla más y la Bruma retrocede.
> **Requisito de ingeniería:** las reglas son código y el contenido son datos. Criaturas, objetos,
> recetas, técnicas, mapas, NPC, diálogos y eventos viven en `res/` como tablas y guiones que se
> compilan; cambiar la historia o el escenario no toca `src/` (§10.2, con un test que lo comprueba).
> Nada de nombres, gráficos, textos ni mapas de juegos existentes ("Cuaderno", no "Pokédex").
> En código y tests: nombres técnicos neutros (FIELD, BATTLE, SPECIES, ITEM, RECIPE...); los nombres
> del tema solo salen de los datos.
> `harness/physics.py` no aplica (no hay saltos con física): aquí hacen ese papel el **modelo de combate
> en Python** (§12, verificado contra el ROM con `rng_state` fijo) y el **lint del mundo** (§10.4).

---

## 1. Pitch

- **Género:** RPG de captura y supervivencia, combate por turnos 1 contra 1, mundo continuo por casillas.
- **Fantasía:** "eres Leo, el nieto de la farera. Hace siete años el faro de Albor se apagó, la abuela
  desapareció y la Bruma cerró el mar: no llegan barcos y la isla vive de lo que caza y pesca. El
  faro no quemaba aceite: concentraba la luz que llevan dentro todas las criaturas de la isla. Con el
  cuaderno de tu abuela, un cuchillo de pesca y cinco farolillos sales a cazar para comer y a capturar
  para encender el faro, especie a especie, hasta llegar al corazón de la Bruma."
- **Tono:** cuento costero, cálido y algo melancólico; humor en la cocina; la Bruma inquietante, no gore.
- **Bucle en una frase:** ves una criatura en el mapa → te acercas con sigilo (o la atraes con cebo) →
  luchas tú → la debilitas sin matarla para capturarla, o la cazas para comer → cocinas en el
  campamento → con lo registrado el faro abre la isla.
- **Duración:** historia principal 12-13 h; registro completo (48/48) 14-15 h. Sesiones de 5-20 min:
  guardar en cualquier momento fuera de combate.
- **Dificultad objetivo:** suave-clásica de GB (la del usuario, ver memoria): el hambre no mata, morir
  cuesta media bolsa de dinero, ningún bloqueo permanente.

### 1.1 Pilares
1. **Cazar es jugar en el mapa:** criaturas visibles con comportamiento propio (huyen, persiguen,
   duermen, van en manada, emboscan, vuelan, nadan); sigilo, cebos y honda. Cero encuentros aleatorios.
2. **Tú eres el arma:** eliges tipo de daño (corte, golpe, punta, fuego, luz), técnicas y artilugios
   para cada especie. Capturar exige **dosificar**: debilitar sin matar.
3. **Comer lo que cazas:** hambre, campamento, cocina con recetas que se descubren y platos que dan
   ventajas reales. Comer bien es la forma más barata de curarse y de capturar mejor.
4. **La luz como progresión:** el registro enciende anillos del faro; cada anillo aparta la Bruma de
   una región. Los artilugios (machete, farol, garfio, bote...) abren el resto (Metroidvania ligero).
5. **Producto pulido:** scroll suave en 4 direcciones, 60 fps, sin parpadeos, textos limpios, música
   en todas las zonas, guardado robusto.

### 1.2 Qué lo hace distinto (no es un clon)
| Pokémon | FARO |
|---|---|
| Tus criaturas luchan | Luchas tú: armas por tipo de daño, técnicas con energía, artilugios |
| Encuentros aleatorios en la hierba | Criaturas visibles con 9 comportamientos; sigilo (B), cebos, honda |
| Capturar = bajar PV | Capturar = dosificar daño + estados + cebo favorito + condición de especie |
| Las criaturas sobrantes van a una caja | Sobrantes: soltarlas o abrir el farolillo y cocinarlas |
| Sin supervivencia | Saciedad, campamento, cocina con descubrimiento, carne que se estropea, sal |
| Medallas abren el mapa | El faro (registro) aparta la Bruma; artilugios abren pasos |

### 1.3 Referencias (solo mecánicas)
- RPG de captura de GB: mundo por casillas de 16x16, pueblos con tienda y enfermería, cuaderno de especies.
- *Dungeon Meshi* (tono): cocinar lo que se caza, recetas con criaturas, la cocina como corazón del grupo.
- Juegos de supervivencia ligera: hambre con efectos graduales, campamento como punto de descanso.
- Este repo: `games/dungeon` (bancos, texto, menús, guardado con 2 ranuras, plan E1-E16),
  `games/platformer` (regla de cámara en 8 bits, streaming, `act_move`), `games/shmup` (gestor de
  sprites con rotación, presupuestos medidos, bots que deben avanzar).

---

## 2. Mecánicas de campo (mapa)

### 2.0 Convenciones (obligatorias para programador y tests)
- **Unidades:** frames (59.73 fps), píxeles, **casillas de 16x16 px** (metatiles). Posiciones de casilla
  `u8` (mundo ≤ 256x256 casillas); desplazamiento dentro de la casilla en píxeles `u8` (0-15).
- **Mapa:** sectores de **16x16 casillas** (256 bytes, 1 byte = metatile). Un mapa es una rejilla de
  sectores (el exterior: 12x8 sectores = 192x128 casillas). Fuera del mapa = metatile de borde del mapa.
- **Dirección** `dir`: `0 abajo, 1 arriba, 2 izquierda, 3 derecha` (tablas `dir_dx[4]`, `dir_dy[4]`).
- **Pasos** (`steps`, u16 que da la vuelta): +1 al completar cada casilla andando, en bici o en bote.
  Hambre, regeneración, estropeado, día/noche y reaparición de recursos cuentan pasos, no tiempo:
  quedarse quieto no castiga.
- **Aleatoriedad:** `gbe_rng` (`rng_next()`, `rng_state`), sembrado con DIV + frames al pulsar en TITLE.
  Los tests fijan `rng_state` y predicen con `gb.rng_next()`.
- **Pausa total:** con texto, menú o pantalla abierta no corren los relojes de pasos ni la IA.
- **Datos:** todo número de equilibrio de este documento vive en `res/data/*.tbl` (§10.3); el C no
  tiene ninguno. "Ajustar en playtest" = cambiar la tabla.

### 2.1 Movimiento por casillas y cámara
| Parámetro | Valor | Notas |
|---|---|---|
| Andar | 1 px/f → **16 f por casilla** (3.7 casillas/s) | animación: cambia de pie cada 8 px |
| Sigilo (mantener B) | 0.5 px/f → 32 f por casilla | las criaturas te ven a la mitad de distancia (§2.4) |
| Bici (artilugio) | 2 px/f → 8 f por casilla | no en interiores ni cuevas (bandera del mapa); despierta a los dormilones |
| Bote | 1.33 px/f (patrón 1,1,2) → 12 f por casilla | solo agua profunda (`DEEP`) |
| Girar sin andar | toque < 6 f en una dirección distinta de `dir` | como los RPG de GB tardíos |
| Encadenar pasos | dirección mantenida al acabar el paso → el siguiente empieza en el mismo frame | sin frames muertos |
| Chocar | animación de andar sin moverse 16 f + SFX `BUMP` (máx. 1 cada 16 f) | |
| Saltar un bordillo (`LEDGE_*`) | 2 casillas en **24 f**, arco y = 0,-3,-5,-7,-8,-8,-7,-5,-3,0 (cada 2-3 f), sombra | solo en el sentido del bordillo |
| Cámara | el jugador siempre en la casilla de pantalla (4, 4) → píxel (64, 64); el mapa se desplaza | sin zona muerta: es la cámara clásica del género |
| Bordes | más allá del mapa se ve el metatile de borde (mar, roca, negro en interiores) | la cámara nunca se para |

- **Solo un eje por paso:** el movimiento por casillas nunca mueve en diagonal. El streaming lo
  aprovecha (§10.6): por paso entra **una** columna o **una** fila de casillas, nunca las dos.
- Entrada durante un paso: la nueva dirección se guarda y se aplica al acabar (búfer de 1 paso).

### 2.2 Tipos de casilla (atributos de metatile, datos de `res/metatiles_*.mt`)
`attr` = `SOLID 0x80 | CAMP 0x40 | PRIO 0x20 | kind (5 bits)`. `PRIO` = el fondo tapa la mitad inferior
del sprite (hierba alta: bit 7 de OAM, coste 0; los tiles de hierba dejan la mitad superior en color 0).

| kind | Nombre | Regla |
|---|---|---|
| 0 | NONE | suelo normal |
| 1 | GRASS | hierba alta (PRIO); ahí viven las emboscadas |
| 2 | WATER | agua somera: no se pisa; con caña se pesca mirándola |
| 3 | DEEP | mar: solo en bote (habilidad BOAT) |
| 4-6 | LEDGE_D / L / R | bordillo: se salta en ese sentido, sólido en el resto |
| 7 | BRAMBLE | zarza: sólida; A con habilidad CUT la corta (vuelve al recargar el sector) |
| 8 | GAP | grieta: A frente a un `HOOKPOST` al otro lado con HOOK = cruzar (anim 32 f) |
| 9 | HOOKPOST | poste de garfio (sólido) |
| 10 | SLOPE | cuesta: andando 32 f por casilla, en bici normal |
| 11 | DARKDOOR | entrada de cueva oscura: sin LIGHT, texto "Esta muy oscuro" y no entras |
| 12 | BRUMA | muro de bruma: sólido mientras `lamp_ring` < el anillo del evento de esa casilla |
| 13 | COUNTER | mostrador: se habla con el NPC de la casilla de detrás |
| 14 | FORAGE | arbusto/árbol con recolección (tabla en el evento) |
| 15 | WARP | puerta/escalera: el evento WARP de la casilla |
| 16 | FISHSPOT | agua con más peces (tabla de pesca propia) |

### 2.3 Interacción y artilugios de campo
| Entrada | Efecto |
|---|---|
| A frente a NPC / cartel / mural / libro | guion del evento (el NPC se gira hacia ti) |
| A frente a objeto en el suelo (destello) | lo coges (bandera de recogida, no reaparece) |
| A frente a FORAGE listo | recolección: tabla (`forage.tbl`: p. ej. BAYAS → Bayas x1-2, RAMAS → Madera x1); reaparece a los **512 pasos** |
| A frente a BRAMBLE (con CUT) | corta (anim 12 f, SFX `CUT`) |
| A frente a WATER/FISHSPOT (con FISH) | pesca (§2.6) |
| A frente a GAP con poste (con HOOK) | cruza con garfio |
| Select | usa el **artilugio registrado** (Mochila → Registrar): honda, cebo, bici, silbato, caña |
| Start | panel de menú (§4) |

**Habilidades:** los objetos llave dan bits de habilidad (datos `items.tbl`, columna `ability`):
`CUT` (Machete), `LIGHT` (Farol de mano), `FISH` (Vara de pesca), `SLING` (Honda), `HOOK` (Garfio),
`BIKE` (Bicicleta), `BOAT` (Bote), `FLY` (Silbato: viaje rápido a pueblos visitados).
El código solo pregunta por bits (`has_ability(CUT)`), nunca por un objeto concreto.

**Honda (Select):** piedra en línea recta 4 casillas (sprite 8x8 a 4 px/f). Si da a una criatura: combate
con **Ventaja** y la criatura ATURDIDA; si es voladora, además DERRIBADA. Enfriamiento 30 f.
**Cebo (Select):** se deja en la casilla de delante 600 f; las especies a las que les gusta ese cebo y
están a ≤ 6 casillas van a comérselo y quedan **comiendo** 240 f (como dormidas, §2.4). Gasta 1.

### 2.4 Criaturas en el mapa: comportamientos
Cada especie tiene en `species.tbl`: `beh` (comportamiento), `beh2` (comportamiento al despertar /
alertarse), `spd` (frames por casilla: 8/12/16/24/32), `vis` (vista en casillas, Manhattan), horario
(`DIA`, `NOCHE`, `SIEMPRE`) y cebo favorito.

**Alerta:** cada criatura activa "piensa" cuando su temporizador llega a 0 (como mucho **1 criatura
piensa por frame**, turno rotativo, regla de games/dungeon). Ve al jugador si distancia Manhattan ≤ vista
efectiva: `vis` andando, `vis >> 1` con sigilo, `vis + 2` en bici, `vis - 1` con el plato SIGILO.
Al verte: emoticono "!" sobre ella **24 f** (aviso: siempre hay tiempo de reaccionar) y pasa a `beh2`.

| Comportamiento | Regla | Cómo se captura/caza |
|---|---|---|
| ERRANTE | paso aleatorio cada 48-96 f dentro de radio 4 de su punto de aparición | acercarse y tocarla |
| ASUSTADIZO | al verte huye a velocidad `spd` (eje que más aleja; si no puede, el otro; acorralada tiembla) 160 f; si sale del área activa desaparece | sigilo, cebo, honda, acorralar |
| PERSEGUIDOR | al verte, tras el "!" te persigue hasta 8 s o > 8 casillas; luego vuelve a casa | si te toca, ella ataca primero; huyes en bici o con sigilo |
| DORMILON | en su horario duerme ("Zz"); por cada paso tuyo a ≤ 3 casillas: despierta con 32/256 andando, 0 con sigilo, 256/256 en bici. Despierta → `beh2` | tocarla dormida: combate con ella DORMIDA y Ventaja |
| MANADA | líder ERRANTE + 2-3 seguidores que pisan sus casillas anteriores; al verte, todos `beh2` | combate con la tocada; al acabar, el resto se dispersa (desaparece) |
| EMBOSCADA | invisible en GRASS/arena/agua; si estás a ≤ 5 casillas la casilla "tiembla" cada 96 f (aviso); al acabar un paso adyacente a ella salta ("!", 12 f) | si salta, ella primero; honda a la casilla que tiembla = Ventaja |
| VOLADOR | vuela a `spd` 8-12 ignorando WATER/GAP; huye a ≤ 3 casillas; en combate tiene VOLANDO | honda o cebo; en combate red/garfio la DERRIBAN |
| NADADOR | sombra en agua; no se toca | caña (§2.6) o bote |
| GUARDIAN | fija, bloquea un paso; A = combate (guion); no huye | jefe; a 0 PV se RINDE (§3.6) |

**Contacto:** combate si el jugador intenta entrar en la casilla de una criatura (la iniciativa es del
jugador: **Ventaja** si la criatura no estaba alerta), o si una criatura alerta intenta entrar en la del
jugador (ella actúa primero). Tras huir de un combate, esa criatura queda **aturdida 120 f** en el mapa.

**Aparición (spawns):** eventos SPAWN con tabla (hasta 4 entradas: especie, nivel mín-máx, peso,
horario, condición `lamp_ring ≥ n` / bandera). Reglas:
| Parámetro | Valor |
|---|---|
| Criaturas activas a la vez | máx. **6** (de 12 huecos de actor; el resto NPC) |
| Un spawn crea criatura si | su sector está en la caché, su criatura no existe y su casilla queda fuera de la pantalla + 1 casilla |
| Desaparece si | > 14 casillas (Chebyshev) del jugador o su sector sale de la caché → reaparece a los 600 f |
| Cazada/capturada | su spawn reaparece a los **1024 pasos** o al descansar |
| Apariciones por frame | máx. 1 (regla de platformer: sin picos) |

### 2.5 Saciedad, energía y salud en el campo (supervivencia)
| Parámetro | Valor | Notas |
|---|---|---|
| Saciedad `sac` | 0-100 (empieza en 80) | icono de estómago de 5 estados |
| Gasto | −1 cada **32 pasos**; −1 por combate; −8 al dormir | de lleno a vacío: 3200 pasos ≈ **14 min** andando |
| Lleno (`sac` ≥ 60) | +1 PV cada 12 pasos | comer bien cura |
| Normal (25-59) | sin efectos | |
| Hambriento (1-24) | ATQ −25 % en combate, sin regenerar EN; aviso una vez al entrar | |
| Desfallecido (0) | ATQ −50 %, AGI −50 %; −1 PV cada 16 pasos **sin bajar de 1** | el hambre nunca mata |
| Energía `en` | +1 cada 24 pasos si `sac` ≥ 25 | para técnicas |
| Veneno en el campo | −1 PV cada 8 pasos (mínimo 1), hasta curarlo | |

**Mejoras de plato (`buff`)**: 1 activa a la vez (un plato nuevo la sustituye), dura N pasos.
| buff | Efecto |
|---|---|
| FUERZA | ATQ +25 % (`a + (a >> 2)`) |
| CORAZA | DEF +25 % |
| AGIL | AGI +25 % (huir, iniciativa, esquiva) |
| VIGOR | +1 PV cada 6 pasos (sustituye a "Lleno") |
| SIGILO | vista de las criaturas −1 más |
| CAZADOR | al cazar, +1 del ingrediente principal |
| MANO_FIRME | captura: `Q_tool + 2` (§3.6) |
| OLFATO | peso ×2 de las entradas raras de los spawns |

**Estropeado** (solo ingredientes con bandera `PERECE`: carne, pescado, marisco, huevo):
- Cada objeto perecedero tiene `age` (u8): +1 cada 64 pasos mientras haya alguno; 0 cuando la
  cuenta llega a 0. Al llegar a **40** (2560 pasos ≈ 11 min): **la mitad redondeada hacia arriba** pasa a
  su versión "pasada" (Carne pasada / Pescado pasado) y `age = 20`. Aviso en el texto.
- Lo pasado no se pierde: comido da +8 de saciedad con 50 % de ENVENENADO, y **sirve de cebo de carne**.
- **Salar** en el campamento (1 Sal + 1 perecedero → Cecina/Salazón): nunca se estropea y cuenta como
  CARNE/PESCADO en recetas.

**Cómo se evita el tedio:** el hambre no mata; avisos claros solo al cruzar umbrales; comer es 1 acción
de menú; en cada pueblo hay comida barata (Pan, Galleta); cocinar tiene "Repetir receta" y
"Cocinar x N"; los platos dan ventajas que merecen la pena; la cuenta es por pasos (pensar o leer no
gasta); un plato medio (40-60) cubre 9-14 min.

### 2.6 Pesca (artilugio Vara de pesca, `FISH`)
- A frente a WATER/FISHSPOT: lanzas (anim 16 f). Si hay un NADADOR a ≤ 3 casillas, se acerca (1 casilla
  cada 24 f) y muerde; si no, con 50 % muerde un pez pequeño de la tabla de pesca del mapa a los
  60-180 f.
- Mordida: "!" y **ventana de 24 f** para pulsar A. Acierto: combate (NADADOR) o ingrediente (pez pequeño).
  Fallo: se escapa. Sin coste.

### 2.7 Campamento
| Regla | Valor |
|---|---|
| Dónde | mapa con bandera `OUTDOOR` + casilla con `CAMP` bajo el jugador + casilla de delante libre (ahí va la hoguera) |
| Cuándo no | ninguna criatura alerta a ≤ 5 casillas ("No es seguro"); nunca en pueblos |
| Coste | **1 Madera** (objeto con rol `LENA`; máx. 9; 4 C en tiendas o en las ramas secas: recolección RAMAS) |
| Pantalla | escena de campamento (§4): Leo, hoguera animada, olla, mochila |
| Cocinar | gratis mientras dure el campamento |
| Descansar | PV +50 % del máximo, EN al máximo, cura todos los estados; `sac −8`; pasa a la siguiente fase (día ↔ noche, M2); reinicia todos los spawns y recolecciones |
| Salar | 1 Sal + 1 perecedero → conserva |
| Farolillos | abrir sobrantes: **Cocinar** (da los mismos ingredientes que cazarla) o **Soltar** |
| Guardar | sí |
| Recoger | vuelta al mapa; la hoguera desaparece |

### 2.8 Día y noche (M2)
- Fase cada **1536 pasos** (≈ 7 min) o al descansar (campamento/posada: eliges "hasta el día" / "hasta
  la noche"). Noche: `BGP` un tono más oscuro (0xF9 en vez de 0xE4; el texto sigue legible: fondo
  gris claro, tinta negra), sprites con paleta normal (resaltan).
- Afecta a: entradas de spawn con horario, quién duerme (DORMILON diurno/nocturno), especies BRUMA.

### 2.9 Muerte y enfermería
- PV 0 en combate → "Leo se desmaya..." → fundido a negro → despiertas en la **última enfermería
  visitada** con PV llenos, **mitad del dinero** (redondeo abajo), sin perder objetos ni registro.
- Enfermería: cura PV, EN y estados **gratis** (jingle de 90 f). Fija el punto de despertar.
- Posada (cada pueblo): 15-40 C, curación completa + elegir fase + cocina de la posada.

---

## 3. Combate

### 3.1 Presentación y flujo
Pantalla aparte 1 contra 1. Contacto en el mapa → "!" (si la criatura estaba alerta) → 3 destellos de
`BGP` invertido (4 f cada uno) → fundido a negro 12 f → pantalla construida con el LCD apagado
(1-2 frames, `skip_measure`) → fundido de entrada 12 f. Al acabar, vuelta al mapa con el mismo esquema.

```
col: 01234567890123456789
r0:  Pinzarro              ######   criatura 56x56 (7x7 tiles) en cols 12-18, filas 0-6 (BG)
r1:  Nv 3 [========  ]     ######   nombre (≤ 10), nivel, barra de PV (8 tiles = 64 px)
r2:  DOR                   ######   estado (3 letras) / iconos ENR CAL ILU
r3-5:                      ######
r6:   ####                          jugador de espaldas 40x48 (5x6 tiles) cols 1-5, filas 6-11
r7:   ####       Leo   Nv 5
r8:   ####       PV  32/38
r9:   ####       [========]          barra 8 tiles
r10:  ####       EN   9/13  (o)      (o) = icono de saciedad
r11:  ####   ________________        línea de suelo del fondo del bioma
r12: +------------------+
r13: | >Atacar  Artilug.|           menú 2x3 en las filas 13-15
r14: |  Tecnica Objeto  |           mensajes: 2 líneas (filas 14 y 16), 2 caracteres/f
r15: |  Capturar Huir   |
r16: |                  |
r17: +------------------+
```
- Todo en el fondo (la ventana no se usa en combate). Golpe a la criatura: parpadea 3 veces (se
  reescriben sus 49 entradas de mapa con el tile vacío y de vuelta, 4 f cada fase) + `shake_x` ±2 6 f.
  Golpe al jugador: `shake_y` ±2 8 f. Efectos (tajo, impacto, red, llama, rayo de luz, Zz, estrellas) con sprites.
- Barras: se vacían 1 px cada 2 f. Píxeles de barra = `(pv × BARK[pvmax]) >> 8`, `BARK[m] = 16384 / m`
  en tabla (u16; `pv ≤ pvmax ≤ 255` → producto ≤ 16384, sin división en tiempo de juego).

**Orden del turno:** el jugador elige → se calcula quién va primero → acción 1 → acción 2 → fin de
turno (estados, contadores). Iniciativa: jugador primero si `AGI_j + rng(0-7) ≥ AGI_c + rng(0-7)`.
**Ventaja** (tú la tocaste sin que estuviera alerta, o con honda): tu primer turno es gratis.
**Emboscada/persecución** (ella te tocó): su primer turno es gratis.

### 3.2 Estadísticas del jugador (tabla `player.tbl`, generada con estas fórmulas)
| Stat | Fórmula (L = nivel 1-40) | L1 | L5 | L10 | L20 | L30 | L40 |
|---|---|---|---|---|---|---|---|
| PV máx | `18 + 4L` | 22 | 38 | 58 | 98 | 138 | 178 |
| EN máx | `8 + L` | 9 | 13 | 18 | 28 | 38 | 48 |
| ATQ | `4 + L + (L >> 1)` | 5 | 11 | 19 | 34 | 49 | 64 |
| DEF (sin ropa) | `3 + L + (L >> 2)` | 4 | 9 | 15 | 28 | 40 | 53 |
| AGI | `5 + L` | 6 | 10 | 15 | 25 | 35 | 45 |
| PX para subir | `8 + 4L + L²` | 13 | 53 | 148 | 488 | 1028 | — |

PX acumulados hasta L35: 16 337 (u16). Al subir: PV y EN suben lo mismo que el máximo (no se llenan).
Leo empieza en **Nv 2** (`RULE_START_LEVEL`): Golpe suave (Nv 3) llega tras 2-3 combates.

### 3.3 Estadísticas de las criaturas
Cada especie tiene niveles (tiers) 1-15 de PV/AT/DF/AG. Con nivel L:
| Stat | Fórmula | Ejemplo tiers 8, L20 |
|---|---|---|
| PV | `10 + ((tPV × L × 3) >> 3)` (≤ 255) | 70 |
| ATQ | `4 + ((tAT × L × 3) >> 4)` | 34 |
| DEF | `3 + ((tDF × L × 3) >> 4)` | 33 |
| AGI | `2 + ((tAG × L × 3) >> 4)` | 32 |
Productos ≤ 15 × 40 × 3 = 1800 (u16). Todos los PV caben en u8.

### 3.4 Daño (enteros, sin divisiones en tiempo de juego)
```
DEF' = max(4, DEF)                         ; RECIP[d] = 1024 / d en tabla u16 (d = 4..255, ≤ 256)
R16  = clamp((ATQ × RECIP[DEF']) >> 6, 2, 64)   ; ATQ/DEF en 1/16 (16 = iguales). ATQ ≤ 255 → ≤ 65280
d    = (POT × R16) >> 4                    ; POT ≤ 60 → ≤ 240
tipo : débil d << 1 · resiste d >> 1 · inmune 0      (2 bits por tipo de daño en la especie)
crít : 1/16 (1/2 con Puntería) → d + (d >> 1)
mods : Hambriento d − (d >> 2) · Desfallecido d >> 1 · FUERZA d + (d >> 2) · QUEMADO (atacante) d − (d >> 2)
téc  : d = (d × mul) >> 3                 ; mul de la técnica en octavos (skills.tbl): Golpe suave 6, Tajo doble 5, Embestida 16
azar : d − ((d × rng(0..31)) >> 8)         ; 88-100 %
mín. 1 (salvo inmune); Golpe suave: si d ≥ PV → d = PV − 1
```
**Acierto:** `acc` (arma 242 ≈ 95 %; movimientos según tabla) `− 2 × max(0, AGI_def − AGI_atk)`, mínimo
128; CEGADO: `acc >> 1`; objetivo VOLANDO (no DERRIBADO/ENREDADO): `− 64`. Acierta si `rng_next() < acc`.

**Tipos de daño (5):** CORTE, GOLPE, PUNTA, FUEGO, LUZ. **Familias** (resistencias por defecto; la
especie puede cambiarlas):
| Familia | Débil a | Resiste | Notas |
|---|---|---|---|
| BICHO (insectos, crustáceos) | GOLPE | CORTE | |
| BESTIA | CORTE | — | |
| AVE | PUNTA | GOLPE | suele VOLAR |
| PEZ (peces, moluscos) | PUNTA | FUEGO | |
| REPTIL (y anfibios) | FUEGO | CORTE | |
| FLORA (plantas, setas) | FUEGO, CORTE | GOLPE, PUNTA | |
| BRUMA | LUZ | inmune a CORTE/GOLPE/PUNTA si no está ILUMINADA | se capturan solo ILUMINADAS |

### 3.5 Acciones del jugador
| Acción | Detalle |
|---|---|
| **Atacar** | submenú con las **hasta 3 armas** de la bolsa de armas (Equipo); elegir cualquiera no cuesta turno extra. Daño por fórmula con el POT y tipo del arma |
| **Técnica** | lista de técnicas aprendidas con su coste de EN |
| **Artilugio** | red, cebos, bengala, dardo, honda, farol, garfio (los que tengas) |
| **Objeto** | pociones, tónicos, antídotos, comida (comer en combate gasta el turno y aplica el plato) |
| **Capturar** | elegir tipo de farolillo → lanzamiento (24 f) → 0-3 sacudidas (32 f c/u) → resultado |
| **Huir** | `p = clamp(128 + 8 × (AGI_j − AGI_c) + 64 × intentos, 16, 255)`; éxito si `rng_next() < p`; criatura ENREDADA = siempre; GUARDIAN = nunca |

**Armas** (`weapons` en `items.tbl`):
| Arma | Tipo | POT | Extra | Dónde / precio |
|---|---|---|---|---|
| Cuchillo | CORTE | 8 | — | inicial |
| Remo viejo | GOLPE | 7 | ATURDIDO 10 % | Varadero (casa) |
| Machete | CORTE | 13 | habilidad CUT | Acto 1 (encargo en Salinas) |
| Arpón corto | PUNTA | 12 | — | tienda Salinas 240 |
| Antorcha | FUEGO | 14 | QUEMADO 20 % | Robledo 450 |
| Maza de raíz | GOLPE | 17 | ATURDIDO 15 % | Robledo 600 |
| Arpón de hueso | PUNTA | 22 | — | Hondura 1100 |
| Farol guerra | LUZ | 24 | ILUMINADO 50 % | Altamar 1800 |
| Martillo faro | GOLPE | 30 | ATURDIDO 20 % | Altamar 2400 |
| Sable farero | CORTE | 36 | crít 1/8 | Acto 5 (historia) |

**Ropa** (DEF): Ropa de faena +1 (inicial), Chubasquero +3 (60), Chaleco corcho +6 (300), Capa de
lona +9 (700), Coraza concha +13 (1500), Abrigo farero +18 (historia).

**Técnicas** (16; `skills.tbl`):
| Técnica | EN | Efecto | Se aprende |
|---|---|---|---|
| Concentrar | 0 | recupera 3 EN, pierdes el turno | L1 |
| Ojo de farero | 1 | muestra PV exactos y debilidades; anota datos en el Cuaderno | L2 |
| Golpe suave | 2 | arma elegida ×0.75 (`(d × 6) >> 3`), **nunca mata** | L3 |
| Aturdir | 3 | GOLPE POT 6, ATURDIDO 60 % | L6 |
| Vendaje | 5 | +25 % PV máx | L8 |
| Silbido | 3 | DORMIDO 45 % a BESTIA/AVE, 15 % al resto | libro, Acto 1 |
| Tajo doble | 4 | 2 golpes ×5/8 (`(d × 5) >> 3`) con arma de CORTE | L11 |
| Puntería | 2 | el siguiente ataque acierta seguro y crítico 1/2 | L14 |
| Grito | 3 | ATQ de la criatura −25 % 3 turnos | L17 |
| Calma | 4 | CALMADO 60 % (3 turnos) | Tomasa, Acto 2 |
| Ráfaga de luz | 8 | LUZ POT 18 + ILUMINADO; requiere LIGHT | Acto 2 |
| Embestida | 6 | arma ×2 (`mul` 16), recibes 1/8 del daño | L21 |
| Red rápida | 5 | ENREDADO 50 % sin gastar red | L25 |
| Respiro | 10 | +50 % PV, cura estados | L29 |
| Golpe certero | 6 | usa `DEF >> 1` | L33 |
| Canto de faro | 12 | a criaturas BRUMA: ILUMINADO + CALMADO seguros | historia, final |

**Artilugios de combate:**
| Artilugio | Efecto | Precio |
|---|---|---|
| Red | ENREDADO 3 turnos (90 %); a una VOLANDO la DERRIBA | 12 |
| Cebo dulce / Cebo de carne / Cebo pescado | si le gusta: CALMADO 2 turnos y `Q_bait` 6 si es su favorito, 5 si no; si no come nada, turno perdido | 8 |
| Bengala | FUEGO POT 18, CEGADO 30 % | 25 |
| Somnifero (dardo) | DORMIDO 70 % (2-4 turnos) | 30 |
| Honda (llave) | PUNTA POT 6, ATURDIDO 25 %; VOLANDO → DERRIBADO 50 % | — |
| Farol de mano (llave) | ILUMINADO 4 turnos; CEGADO 40 % a especies nocturnas | — |
| Garfio (llave) | VOLANDO → DERRIBADO 100 % | — |

### 3.6 Captura
```
v = catch[especie]                         (0-255, datos)
v = (v × Q_hp)   >> 2    Q_hp:   PV > 50 % → 2 · ≤ 50 % → 4 · ≤ 25 % → 6 · ≤ 12.5 % → 8
                                  (pv×2 ≤ max, pv×4 ≤ max, pv×8 ≤ max: solo desplazamientos)
v = (v × Q_st)   >> 2    Q_st:   ninguno 4 · CALMADO 5 · ENREDADO/ATURDIDO/DERRIBADO 6 · DORMIDO 8 · RENDIDO 12 (el mejor)
v = (v × Q_tool) >> 2    Q_tool: Farolillo 4 · Farolillo fino 6 · Farol de plata 8 · Farol de bruma 12 (BRUMA) / 4 (resto)
                                 (+2 con MANO_FIRME) · Farol maestro → v = 255
v = (v × Q_bait) >> 2    Q_bait: cebo favorito comido en este combate 6 · otro cebo comido 5 · ninguno 4
condición de especie no cumplida → v = 0 ("La luz se escapa")
v ≥ 255 → seguro; si no, capturada si rng_next() < v            (u16 en los pasos; ≤ 255 × 12)
sacudidas al fallar: 2 si roll < 2v, 1 si roll < 4v, si no 0 (solo animación)
```
- **Condiciones** (`cond` + `cond_arg` en `species.tbl`): `NONE`, `STATUS x` (debe estar DORMIDA, p. ej.
  Salitorta), `LIT` (ILUMINADA: BRUMA), `GROUNDED` (DERRIBADA o ENREDADA: voladoras raras), `TOOL x`
  (solo con ese farolillo).
- **Tras un fallo**, ASUSTADIZO / VOLADOR escapan con 25 % (fin del combate, sin PX).
- **Primera captura de una especie:** se registra al instante, la luz vuela al faro (animación del
  farolillo hacia arriba 32 f + jingle) y da PX ×2. **Capturas repetidas:** van a la lista de farolillos
  llenos (máx. 12; 24 con Zurrón) para soltar o cocinar en el campamento.
- **GUARDIAN:** a 0 PV no muere: queda **RENDIDO** (`Q_st` 12). Si huyes o fallas hasta que acabe el
  combate, vuelve a estar en su sitio con PV llenos. Así ninguna especie se pierde para siempre.
- **Cazar (PV 0, no guardián):** PX + botín (§5.4), contador `kills[especie] + 1`. Nunca registra.

### 3.7 IA de las criaturas
- Hasta 4 movimientos por especie (`moves.tbl` global de ~48) con peso 0-15. Elección: aleatoria
  ponderada, con estas reglas en orden: (1) PV ≤ 25 % y tiene `HUIR` o curarse → 50 % de usarlo
  (`HUIR` falla si está ENREDADA o DERRIBADA); (2) movimiento de estado y el jugador sin estado → peso ×2;
  (3) CALMADO → solo movimientos sin daño o nada ("observa"); (4) mismo movimiento de defensa 2 veces
  seguidas → peso 0.
- Jefes: 2 juegos de movimientos y umbral de PV (p. ej. ≤ 50 % cambia al juego 2 con mensaje).
- **Movimientos de ejemplo:** Pinza (CORTE 6), Picotazo (PUNTA 7), Topetazo (GOLPE 10), Carga (GOLPE 14), Mordisco
  (CORTE 12), Aguijón (PUNTA 8, ENVENENADO 30 %), Esporas (DORMIDO 40 %), Tinta (CEGADO 60 %),
  Coraza (DEF +25 % 3 turnos), Robar (quita 1 comida de la mochila; Gavirata), Llamarada (FUEGO 16,
  QUEMADO 20 %), Niebla (CEGADO 50 %), Huir (escapa con 50 %).

### 3.8 Estados
Un estado principal (`st`, `st_turns`) + banderas con su contador. Abreviaturas de 3 letras (combate, Equipo; `statuses.tbl`):
DOR ATU CEG VEN QUE REN.
| Estado | Efecto | Duración | Fin |
|---|---|---|---|
| DORMIDO | pierde el turno; al recibir daño 50 % despierta | 2-4 turnos | |
| ATURDIDO | pierde el siguiente turno | 1 | |
| CEGADO | acierto `>> 1` | 3 | |
| ENVENENADO | −PV máx `>> 3` por turno (jugador: también en el campo) | hasta curar (criatura: 5) | Antídoto, enfermería, campamento |
| QUEMADO | −PV máx `>> 4` por turno, daño −25 % | 4 | Ungüento |
| ENREDADO (bandera) | no huye ni vuela; AGI `>> 1` | 3 | |
| CALMADO (bandera) | sin movimientos de daño | 2-3 | |
| ILUMINADO (bandera) | BRUMA pierde su inmunidad y puede capturarse | 4 | |
| VOLANDO / DERRIBADO | innato de voladoras / anulado por red, garfio, honda | combate | |
| RENDIDO | solo guardianes a 0 PV: no actúa | combate | |

### 3.9 Experiencia
`px = ((xp_base × L_criatura) >> 3) + 2` al cazar o capturar (×2 si es especie nueva); huir 0.
`xp_base` 10-40 en la tabla. Batallas para subir de nivel (criatura del nivel del jugador, `xp_base`
20): L5 ≈ 4, L10 ≈ 6, L20 ≈ 9, L30 ≈ 13 → **≈ 300 combates** hasta L35 en la historia (objetivo del
bot de equilibrio: L33-36 al llegar al final).

### 3.10 Ejemplos resueltos (los tests los reproducen con `rng_state` fijado)
**A. Principio: Leo L3 contra Pinzarro L3** (tiers 6/5/7/3; BICHO: débil GOLPE, resiste CORTE).
Pinzarro: PV `10 + (54 >> 3)` = 16, ATQ `4 + (45 >> 4)` = 6, DEF `3 + (63 >> 4)` = 6, AGI 3. Leo: PV 30,
ATQ 8, DEF 6 + 1 = 7, AGI 8.
- Cuchillo (CORTE 8): `R16 = (8 × 170) >> 6 = 21`, `d = (8 × 21) >> 4 = 10`, resiste → **5** (4 golpes).
- Remo (GOLPE 7): `d = (7 × 21) >> 4 = 9`, débil → **18 ≥ 16: lo mata de un golpe** (caza, no captura).
- Golpe suave con remo: `(18 × 6) >> 3 = 13`, con el azar 12-13 → quedan **3-4 PV** (4 × 4 = 16 ≤ 16 → banda
  ≤ 25 %, `Q_hp` 6, con cualquier tirada).
  Captura con Farolillo: `v = 150 × 6 >> 2 = 225` → **88 %**.
- Pinza (CORTE 6) contra Leo: `R16 = (6 × 146) >> 6 = 13`, `d = (6 × 13) >> 4 = 4` → **4** por golpe (el azar no baja un daño < 9).
**B. Mitad: Leo L20 (ATQ 34, DEF 28 + 9 Capa de lona, AGI 25) contra Musgali L20** (tiers 9/9/7/6; BESTIA, débil CORTE).
Musgali: PV 77, ATQ 37, DEF 29, AGI 24.
- Machete (CORTE 13): `R16 = (34 × 35) >> 6 = 18`, `d = (13 × 18) >> 4 = 14`, ×2 = **28** → 2 golpes: 21 PV
  (21 × 2 = 42 ≤ 77 → banda ≤ 50 %).
- Carga de Musgali (GOLPE 14): `R16 = (37 × 27) >> 6 = 15`, `d = (14 × 15) >> 4 = 13` → Leo aguanta 7-8.
- Captura `catch` 80, ≤ 50 %, DORMIDO (dardo), Farolillo fino: `80 → 80 → 160 → 240` = **94 %**; sin dardo **47 %**.
- Huir: `128 + 8 × (25 − 24) = 136` → 53 %. Acierto del jugador: 242 (95 %).

---

## 4. Controles, pantallas y flujo

### 4.1 Controles
| Botón | Campo | Combate / menús | Texto |
|---|---|---|---|
| Cruceta | andar (toque = girar) | cursor (repetición 16/6 f) | — |
| A | hablar, leer, coger, recolectar, cortar, pescar, cruzar | confirmar | avanzar; mantener = texto ×2 |
| B | **mantener = sigilo** | atrás | avanzar |
| Start | panel de menú | — (en listas: ordenar) | — |
| Select | artilugio registrado | — | — |
Sin combinaciones de 3 botones. En la bici, B mantenido no hace nada (no hay sigilo en bici).

### 4.2 Flujo (máquina de estados `state`)
```
BOOT -> TITLE: Continuar (si hay partida) | Nueva partida -> NAME (M2) -> INTRO (guion) -> FIELD
FIELD.WALK <-> FIELD.SCRIPT (texto/eventos; guion del VM)       FIELD.WALK <-> FIELD.PANEL (Start)
FIELD.PANEL -> SCREEN: CUADERNO | MOCHILA | EQUIPO | MAPA (M2) | OPCIONES   (fundido rápido 8 f + LCD off)
FIELD.PANEL -> CAMP (si se puede) -> SCREEN.COCINA / farolillos / dormir
FIELD.SCRIPT -> SHOP | COCINA (posada) | ENFERMERIA (guion) | SAVE (confirmación)
FIELD (contacto) -> BATTLE -> (victoria/captura/huida) FIELD | (PV 0) FAINT -> FIELD en la enfermería
FIELD.SCRIPT (anillo del faro) -> LAMP (escena) -> FIELD ... -> ENDING -> CREDITS -> TITLE (posjuego)
```
`state`: `TITLE 0, FIELD 1, BATTLE 2, SCREEN 3, CAMP 4, SHOP 5, FAINT 6, LAMP 7, ENDING 8`.
`field_sub`: `WALK 0, SCRIPT 1, PANEL 2`. `screen_id`: `CUADERNO, MOCHILA, EQUIPO, COCINA, MAPA, OPCIONES`.

### 4.3 Pantallas
| Pantalla | Capa / cómo | Contenido |
|---|---|---|
| TITLE | BG, LCD apagado | logo "FARO" (imagen) con el haz girando (sprites), "Pulsa Start" 30/30 f, Continuar / Nueva partida / Opciones |
| FIELD | BG con scroll + sprites | mapa, actores, HUD discreto (§4.4) |
| Texto | **ventana** WY = 96 (filas 12-17), WX = 7 | marco + 2 líneas de 18 car. (filas 14 y 16), flecha ▼ parpadeando 16/16 f; Sí/No dentro del cuadro a la derecha |
| Panel (Start) | **ventana** WX = 87 (cols 10-19), WY = 0; entra deslizando WX 167→87 en 8 f | Cuaderno, Mochila, Equipo, Acampar, Mapa (M2), Guardar, Opciones, Salir; abajo: "Leo Nv12", PV, EN, estómago, fase (sol/luna), dinero |
| CUADERNO | pantalla completa (LCD off) | lista 48 (Nº, nombre o "-----", ● capturada / ○ vista), contador "Luces 23/48"; ficha: imagen 56x56, familia, hábitat, cebo favorito, debilidades (si se usó Ojo de farero o capturada), texto (3 líneas), "Notas de cocina" |
| MOCHILA | pantalla completa | 4 bolsillos (←/→): Objetos, Comida, Artilugios, Farolillos; lista con cuenta; icono 16x16 del seleccionado; A: Usar/Comer/Registrar/Tirar |
| EQUIPO | pantalla completa | stats, ropa, bolsa de 3 armas, técnicas, plato activo y pasos que le quedan, estado |
| CAMP | pantalla completa | escena (Leo, hoguera animada 3 frames, olla); menú: Cocinar, Descansar, Salar, Farolillos, Guardar, Recoger |
| COCINA | pantalla completa | 3 huecos de ingrediente + lista de Comida; "Cocinar", "Repetir receta", "Recetas" (conocidas con sus ingredientes); resultado con icono |
| SHOP | pantalla completa | Comprar / Vender; lista con precio; cantidad con ↑↓ (×1, ←/→ ×10); dinero |
| BATTLE | BG | §3.1 |
| FAINT | BG negro + texto | "Leo se desmaya..." |
| LAMP | escena en la Sala de la Lente | el anillo se enciende (parches de mapa + destellos de paleta), texto, la Bruma de la región se disuelve |
| ENDING / CREDITS | imágenes + texto | §6.5 |

### 4.4 HUD de campo (discreto, con sprites)
No hay HUD fijo: el mapa se ve entero. Dos iconos 8x16 en x 4 y x 14, y 4 (OAM 0-1):
- **Corazón:** oculto si PV ≥ 50 %; medio < 50 %; vacío parpadeando 16/16 f < 25 %.
- **Estómago:** oculto si `sac` ≥ 60; medio 25-59; vacío parpadeando 1-24; con aspa a 0.
- Ambos se muestran 180 f cuando cambian de banda aunque estén "bien". Mensajes de umbral en el
  cuadro de texto la primera vez ("Te suenan las tripas").

### 4.5 Texto
- Tipo frase (mayúscula inicial), fuentes compartidas (68 tiles) + **4 glifos nuevos compartidos**:
  coma, apóstrofo, ¡ y ¿ (E14). Sin tildes ni ñ en pantalla: en los datos se escribe "Pocion", "Arpon",
  "Unguento"; las palabras con ñ se cambian por otras ("temporada", no "año"). Este documento usa
  tildes solo para leerse mejor.
- Velocidad (Opciones): lenta 1 car./2 f, normal 1 car./f, rápida 2 car./f; A mantenido ×2. Máx. 4 tiles/f.
- Variables en el texto: `{N}` nombre, `{I}` objeto, `{S}` especie, `{#}` número.
- Longitudes: nombres de especie ≤ 10, objetos ≤ 14, líneas 18.

---

## 5. Supervivencia, cocina y economía

### 5.1 Ingredientes (categorías en `items.tbl`, máscara de bits)
`CARNE, PESCADO, MARISCO, HUEVO, VERDURA, FRUTA, HONGO, GRANO, ESPECIA, DULCE`. Un ingrediente puede
tener varias. Fuentes: criaturas (cazar / abrir farolillo), recolección, pesca, tiendas (Sal, Harina,
Aceite, Miel, Pimienta), encargos. M1b: Bayas, Algas, Hinojo y Madera salen de la recolección.

### 5.2 Cocina
- **Dónde:** campamento, cocina de posada, casa de Tomasa.
- **Cómo:** eliges 1-3 ingredientes → se buscan las recetas (gana la de más huecos de objeto concreto y, a
  igualdad, la de fila menor de `recipes.tbl`); cada receta tiene 1-3 huecos (objeto concreto o categoría) y casa sin importar
  el orden (como mucho 3! = 6 permutaciones x 32 recetas: se calcula una vez al pulsar Cocinar).
- **Receta conocida:** sale el plato. **Desconocida pero válida:** sale el plato y "¡Nueva receta!"
  (jingle, bandera `recipe_known`). **Ninguna:** "Mejunje" (+10 saciedad). Los ingredientes se gastan.
- **Cómo se descubren:** experimentando; 12 páginas del diario de Ines (dan receta + pista de captura);
  Tomasa y los cocineros de cada pueblo (guion `LEARN_RECIPE`); la línea "Notas de cocina" de cada ficha
  del Cuaderno ("Su carne con sal es otra cosa").
- **Repetir receta** (1 pulsación si tienes los ingredientes) y **Cocinar x N** (hasta el mínimo
  disponible).

**Primeras 16 recetas** (32 en total; `recipes.tbl`):
| # | Plato | Ingredientes | Sac. | Efecto | Se conoce |
|---|---|---|---|---|---|
| 1 | Asado simple | CARNE | 20 | +10 PV | inicio |
| 2 | Pescado asado | PESCADO | 18 | +12 PV | inicio |
| 3 | Cangrejo y sal | Carne cangrejo + Sal | 30 | +25 PV, CORAZA 384 pasos | Tomasa (M1) |
| 4 | Ancas y bayas | Ancas de sapo + FRUTA | 30 | +15 PV, FUERZA 384 | experimentar (pista en Sapoyo) |
| 5 | Tortilla mar | HUEVO + HUEVO + Aceite | 40 | +20 PV, AGIL 384 | diario 1 (M1) |
| 6 | Estofado | CARNE + VERDURA + VERDURA | 55 | +30 PV, VIGOR 512 | experimentar |
| 7 | Mermelada | FRUTA + FRUTA + Miel | 20 | +20 EN, SIGILO 384 | Tomasa (M1) |
| 8 | Caldo de algas | VERDURA + Sal | 15 | +10 EN, cura veneno | inicio |
| 9 | Anguila curada | Filete anguila + ESPECIA | 35 | +25 PV, MANO_FIRME 384 | Salinas |
| 10 | Pan de algas | GRANO + VERDURA | 35 | +10 PV | Salinas |
| 11 | Sopa de setas | HONGO + HONGO + ESPECIA | 30 | EN llena, OLFATO 512 | Robledo |
| 12 | Guiso cazador | CARNE + HONGO + ESPECIA | 60 | +40 PV, CAZADOR 512 | diario 4 |
| 13 | Empanada | GRANO + MARISCO + Aceite | 50 | +30 PV, CORAZA 512 | Hondura |
| 14 | Queso de cabra | Leche de cabra + Sal | 25 | +20 PV, cura quemado | Hondura |
| 15 | Lomo a la miel | Lomo de jabali + Miel + ESPECIA | 70 | PV llenos, FUERZA 768 | Altamar |
| 16 | Caldo de luz | Medusa de luz + VERDURA + Sal | 25 | EN llena, MANO_FIRME 768 | diario 9 |

### 5.3 Inventario
Cuenta por objeto (u8, 128 ids) con tope por categoría (`caps.tbl`):
| Categoría | Tope | Con Zurrón (500 C, Acto 2) |
|---|---|---|
| Ingredientes, platos | 9 por objeto | 19 |
| Medicinas, artilugios gastables | 9 | 19 |
| Farolillos vacíos (por tipo) | 20 | 40 |
| Farolillos llenos (lista especie + nivel) | 12 | 24 |
| Objetos llave, armas, ropa | 1 | 1 |
| Dinero (Conchas, C) | 9999 | |
Al pasar del tope: "No te cabe" y se queda en el suelo / no se recoge del botín (aviso).

### 5.4 Botín al cazar
`drops` de la especie: principal (siempre, 1-2), material (50 %), raro (1/16). Ej.: Pinzarro → Carne de
cangrejo 1-2, Concha 50 %, Perla 1/16. BRUMA no da carne (Esencia de bruma, material).

### 5.5 Economía
| Fuente | Valor |
|---|---|
| Dinero inicial | 300 C + 5 Farolillos |
| Materiales (solo se venden) | Concha 12, Pluma 14, Piel 16, Escama 18, Aguijón 12, Púa 12, Cuarzo 45, Polvo de luz 30, Perla 100, Ámbar 150 |
| Venta de cualquier otro objeto | mitad del precio de compra (llaves no) |
| Encargos (tablón en cada pueblo, guiones) | 100-800 C + receta/objeto |
| Dinero en el mapa | 50-300 C (objetos de suelo) |
| Ingreso medio por caza | ~15 C (Prólogo), ~35 (Acto 2), ~70 (Acto 5) |

| Precio | C | | Precio | C |
|---|---|---|---|---|
| Poción (+30 PV) | 20 | | Farolillo | 15 |
| Poción fuerte (+80) | 60 | | Farolillo fino | 40 |
| Elixir (todo) | 200 | | Farol de plata | 90 |
| Tónico (+15 EN) | 30 | | Farol de bruma (tras anillo 5) | 120 |
| Antídoto / Ungüento | 10 | | Red / Cebo | 12 / 8 |
| Pan (+15 sac.) / Galleta (+20, no perece) | 8 / 12 | | Bengala / Somnifero | 25 / 30 |
| Sal / Harina / Aceite / Miel / Pimienta | 6 / 5 / 10 / 12 / 8 | | Madera | 4 |
| Enfermería | gratis | | Posada | 15 (Varadero) - 40 (Altamar) |
Objetivo del bot de economía: terminar cada acto con 100-600 C tras comprar lo necesario (no hay que
"farmear" para avanzar; sí para comprar el arma opcional del pueblo).

---

## 6. Mundo, criaturas e historia

### 6.1 La isla de Albor (exterior continuo: 12x8 sectores = 192x128 casillas)
Cada carácter = 1 sector de 16x16 casillas. `~` = mar (3 sectores de mar compartidos, sin datos repetidos).
```
        0  1  2  3  4  5  6  7  8  9  10 11
   0    ~  ~  T  T  A  A  A  A  ~  ~  ~  ~      T Altamar (ciudad)      A Acantilados (garfio)
   1    ~  U  T  a  a  D  D  D  ~  ~  C  C      a Acantilados bajos     D Desfiladero   H Hondura
   2    ~  U  B  B  B  D  H  D  ~  ~  C  C      U Ruinas Hundidas (marea)   C Islote Cenizal (bote)
   3    ~  ~  B  R  B  B  d  d  ~  ~  ~  ~      B Bosque Viejo   R Robledo   d salida de la Cueva del Eco
   4    ~  ~  b  b  M  M  M  S  S  ~  ~  X      b linde del bosque (zarzas: machete)   X Ojo de la Bruma
   5    ~  ~  V  V  M  M  S  S  ~  ~  ~  ~      M Marismas   S Salinas
   6    ~  ~  V  F  ~  ~  ~  ~  ~  ~  ~  ~      V Varadero (inicio)
   7    ~  ~  ~  F  ~  ~  ~  ~  ~  ~  ~  ~      F Cabo y Sendero del Faro (el faro en la punta)
```
- 47 sectores de tierra/islote ≈ 12 000 casillas (la escala de un RPG de GB completo).
- Muros de BRUMA entre regiones (se disuelven por anillo): Varadero→Marismas (anillo 1), linde del
  bosque se abre además con machete, Cueva→Desfiladero (anillo 3), Desfiladero→Acantilados (anillo 4),
  mar abierto hacia Cenizal (anillo 5), Ojo de la Bruma (anillo 6).

**Mapas interiores** (warps; cada uno su mapa y tileset):
| Mapa | Tamaño (sectores) | Puerta |
|---|---|---|
| Faro (4 plantas + Sala de la Lente + Vivero) | 6 x 1x1 | Cabo |
| Cueva del Eco | 3x2 | Bosque (LIGHT) |
| Minas de Hondura | 3 plantas x 2x2 | Hondura (HOOK dentro) |
| Ruinas Hundidas | 2 plantas x 2x2 | marea baja (BOAT para la planta 2) |
| Almacén del Gremio | 1x2 | Altamar (guion) |
| Volcán de Cenizal | 2 plantas x 2x2 | Cenizal |
| Corazón de la Bruma | 3x3 | Ojo de la Bruma (anillo 6) |
| Casas, tiendas, enfermerías, posadas | ~45 x 1x1 (≤ 10x9 útiles) | pueblos |

### 6.2 Avance y ritmo (10-15 h)
| Parte | Zonas | Especies nuevas (acum.) | Anillo (capturas) | Artilugio / hito | Niveles | Tiempo (acum.) |
|---|---|---|---|---|---|---|
| Prólogo | Varadero, Sendero, Faro | 6 (6) | 1 (5) | Cuchillo, Remo, Honda | 2-6 | 0.75 h (0.75) |
| Acto 1 | Marismas, Salinas | 7 (13) | 2 (11) | Machete, Vara de pesca, Sal | 5-11 | 2 h (2.75) |
| Acto 2 | Bosque Viejo, Robledo, Cueva del Eco | 9 (22) | 3 (19) | Farol, Bici, Zurrón | 10-17 | 2.25 h (5) |
| Acto 3 | Desfiladero, Hondura, Minas | 8 (30) | 4 (26) | Garfio | 16-24 | 2.25 h (7.25) |
| Acto 4 | Acantilados, Altamar, Ruinas | 8 (38) | 5 (33) | Silbato (viaje), Bote | 22-30 | 2.5 h (9.75) |
| Acto 5 | Mar, Cenizal, Volcán | 6 (44) | 6 (39) | Farol maestro | 29-34 | 2 h (11.75) |
| Final | Corazón de la Bruma | 1 (45) | — | Canto de faro | 33-38 | 0.75 h (12.5) |
| Posjuego | Bruma nocturna en toda la isla | 3 (48) | luz completa | final verdadero | 35-40 | 1.5-2.5 h (14-15) |
Holgura: al acabar cada acto hay ≥ 2 especies más de las que pide el anillo (no hay que capturarlo todo).

### 6.3 Las 48 especies
Tiers PV/AT/DF/AG (1-15). `catch` 0-255. Comportamiento → al alertarse. Hor.: D día, N noche, S siempre.
| # | Nombre | Familia | Zona | Comport. | Nv | Tiers | catch | Hor. | Cond. | Botín principal |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Pinzarro | BICHO | playa Varadero | ERRANTE | 2-5 | 6/5/7/3 | 150 | S | — | Carne cangrejo |
| 2 | Dunejo | BESTIA | Sendero | ASUSTADIZO | 2-5 | 5/4/4/9 | 140 | D | — | Muslo conejo |
| 3 | Gavirata | AVE | costa | VOLADOR | 3-6 | 5/6/4/8 | 120 | D | — | Huevo gaviota |
| 4 | Sapoyo | REPTIL | charcas | DORMILON → ERRANTE | 3-6 | 8/5/5/3 | 140 | D duerme | — | Ancas de sapo |
| 5 | Erizal | BICHO | rocas | PERSEGUIDOR lento (24) | 3-6 | 6/6/9/2 | 120 | S | — | Huevas erizo |
| 6 | Polifaro | BICHO | claro tras zarzas | ERRANTE | 5-6 | 5/5/4/8 | 70 | S | — | Polvo de luz |
| 7 | Zancuda | AVE | marisma | ASUSTADIZO | 5-9 | 6/7/5/9 | 100 | D | — | Huevo de garza |
| 8 | Fangila | PEZ | canales | NADADOR | 6-10 | 7/7/5/7 | 110 | S | — | Filete anguila |
| 9 | Tabarro | BICHO | juncal | MANADA → PERSEGUIDOR | 6-10 | 4/6/4/9 | 140 | D | — | Aguijón |
| 10 | Salitorta | REPTIL | salinas | DORMILON | 7-11 | 12/5/13/2 | 90 | S | DORMIDA | Caparazón |
| 11 | Juncabato | BESTIA | juncal | PERSEGUIDOR | 7-11 | 8/9/6/6 | 110 | S | — | Lomo de jabato |
| 12 | Cristacan | BICHO | salinas | EMBOSCADA | 8-11 | 6/8/9/5 | 100 | S | — | Sal fina |
| 13 | Garzareal | AVE | marisma (jefe) | GUARDIAN | 12 | 10/9/7/10 | 25 | — | — | Pluma real |
| 14 | Bellotin | BESTIA | bosque | ASUSTADIZO | 10-14 | 6/6/5/12 | 120 | D | — | Nueces |
| 15 | Musgali | BESTIA | bosque | PERSEGUIDOR | 11-15 | 9/9/7/6 | 80 | S | — | Lomo de jabali |
| 16 | Setilla | FLORA | sotobosque | DORMILON → EMBOSCADA | 10-14 | 8/6/7/3 | 130 | S | — | Seta |
| 17 | Buhorno | AVE | bosque | DORMILON (día) / VOLADOR (noche) | 12-16 | 7/8/6/9 | 70 | N | — | Pluma de buho |
| 18 | Cortezo | BESTIA | claros | MANADA → ASUSTADIZO | 12-16 | 8/7/7/10 | 60 | D | — | Venado |
| 19 | Murcieco | BESTIA | Cueva del Eco | VOLADOR | 13-17 | 5/8/5/12 | 110 | S | — | Ala de murcielago |
| 20 | Lumbrigo | BICHO | Cueva del Eco | ERRANTE | 13-17 | 7/6/8/4 | 120 | S | — | Gelatina de luz |
| 21 | Zorrebla | BESTIA | bosque | PERSEGUIDOR | 13-17 | 7/10/6/11 | 70 | N | — | Piel de zorro |
| 22 | Osoroble | BESTIA | Robledo (jefe) | GUARDIAN | 18 | 14/11/10/5 | 20 | — | — | Miel salvaje |
| 23 | Risquera | BESTIA | desfiladero | MANADA → ASUSTADIZO | 16-21 | 8/8/8/11 | 90 | D | — | Leche de cabra |
| 24 | Lagartiz | REPTIL | desfiladero | ERRANTE | 16-21 | 8/9/9/7 | 100 | D | — | Cola de lagarto |
| 25 | Escorojo | BICHO | desfiladero | EMBOSCADA | 17-22 | 7/11/9/7 | 80 | S | — | Aguijón rojo |
| 26 | Topero | BESTIA | Minas | EMBOSCADA | 18-23 | 9/8/8/6 | 110 | S | — | Carne de topo |
| 27 | Cuarzol | BICHO | Minas | DORMILON | 19-23 | 9/5/15/1 | 90 | S | — | Cuarzo |
| 28 | Halconte | AVE | riscos | VOLADOR (12) | 19-24 | 7/11/6/14 | 50 | D | DERRIBADA | Pluma de halcon |
| 29 | Salamina | REPTIL | Minas | ERRANTE | 20-24 | 8/10/8/8 | 70 | S | — | Cola de salamandra |
| 30 | Ciempiedra | BICHO | Minas (jefe) | GUARDIAN | 25 | 15/12/13/6 | 20 | — | — | Coraza de ciempies |
| 31 | Frailin | AVE | acantilados | MANADA → ASUSTADIZO | 22-27 | 7/8/7/10 | 110 | D | — | Huevo de frailecillo |
| 32 | Pulporo | PEZ | pozas | EMBOSCADA | 23-28 | 9/10/8/8 | 80 | S | — | Pulpo |
| 33 | Focalma | BESTIA | rocas | DORMILON | 23-28 | 13/9/10/4 | 70 | D | — | Grasa de foca |
| 34 | Medulux | PEZ | bahía | NADADOR | 24-29 | 6/9/6/9 | 90 | N | — | Medusa de luz |
| 35 | Conchudo | BICHO | Ruinas | ERRANTE (32) | 25-30 | 11/10/14/3 | 60 | S | — | Concha gigante |
| 36 | Gatruina | BESTIA | Ruinas | ASUSTADIZO | 25-30 | 7/10/7/13 | 70 | N | — | Piel de gato |
| 37 | Sierpedra | REPTIL | Ruinas | EMBOSCADA | 26-30 | 9/12/9/10 | 60 | S | — | Carne de sierpe |
| 38 | Rayarena | PEZ | aguas someras | EMBOSCADA | 26-30 | 9/10/9/9 | 70 | S | — | Aleta de raya |
| 39 | Aletazo | PEZ | mar (bote) | NADADOR | 29-33 | 10/11/8/11 | 80 | S | — | Ventresca |
| 40 | Cormonte | AVE | Cenizal | VOLADOR | 29-33 | 8/11/7/13 | 70 | D | — | Pluma negra |
| 41 | Iguanalava | REPTIL | volcán | DORMILON | 30-34 | 11/10/12/6 | 60 | D | — | Cola de iguana |
| 42 | Escarbrasa | BICHO | volcán | MANADA → PERSEGUIDOR | 30-34 | 8/12/10/9 | 90 | S | — | Caparazón ígneo |
| 43 | Carnerojo | BESTIA | Cenizal | PERSEGUIDOR | 31-35 | 11/13/10/8 | 50 | S | — | Cordero |
| 44 | Serpemar | PEZ | mar de Cenizal (jefe) | GUARDIAN | 36 | 15/14/12/11 | 15 | — | — | Escama de sierpe |
| 45 | Madrebruma | BRUMA | Corazón (jefa final) | GUARDIAN | 40 | 15/14/14/10 | 3 | — | ILUMINADA | — |
| 46 | Fatuo | BRUMA | toda la isla (bruma) | VOLADOR | 35-40 | 7/12/8/14 | 60 | N | ILUMINADA | Esencia de bruma |
| 47 | Velamar | BRUMA | Ruinas / costa | ERRANTE | 35-40 | 10/13/11/9 | 40 | N | ILUMINADA | Esencia de bruma |
| 48 | Ballenebla | BRUMA | mar abierto | GUARDIAN | 40 | 15/15/14/8 | 5 | N | ILUMINADA | Esencia de bruma |
Especies 46-48 solo existen con `lamp_ring = 6`. Las 4 especies GUARDIAN-jefe y 45/48 se rinden (§3.6).

### 6.4 Historia (actos), personajes y lore
**Personajes:** **Leo** (14, protagonista, nombre cambiable en M2); **Ines** (la farera desaparecida;
se la conoce por su diario); **Tomasa** (cocinera de Varadero, mentora, enseña a cocinar y a respetar
lo que se come); **Bruno** (cazador de Salinas, rival: no cree en el faro, vende carne y pieles; compite
contigo en encargos y al final ayuda); **Celso** (bibliotecario de Altamar, historia de los fareros);
**Ofelia** (patrona del Gremio de Farolas de Altamar: vende farolas con luz de criaturas encerradas;
vaciar la isla de luces es lo que alimenta la Bruma).

| Parte | Resumen |
|---|---|
| Prólogo | Tomasa te da el diario y los farolillos de Ines. Cazas un Pinzarro (tutorial de caza), cocinas con ella, capturas tu primer Dunejo (tutorial de Golpe suave). En el faro apagado, la Sala de la Lente tiene seis anillos negros. 5 especies → **anillo 1**: el haz aparta la Bruma del camino de las Marismas |
| Acto 1 | Salinas lleva años aislada. Bruno caza para vender. Encargo de la salinera: el Machete; aprendes a salar. La Garzareal vigila el juncal. Diario: Ines siguió a la Bruma hacia el norte. **Anillo 2**: se abre el Bosque |
| Acto 2 | Robledo, pueblo de carpinteros: arreglan la bici de Ines con 3 piezas (encargo). El Farol en la Cueva del Eco; el Osoroble protege a sus crías. **Anillo 3** |
| Acto 3 | Hondura: el Gremio compra "piedra-luz" a los mineros; en las Minas, el Ciempiedra. El Garfio. **Anillo 4** |
| Acto 4 | Altamar: Celso y la biblioteca (por qué el faro necesita criaturas *libres* en el Vivero); el almacén de Ofelia con cientos de farolillos llenos: los liberas (escena). Silbato de gaviota y Bote. Ruinas Hundidas: murales de los primeros fareros. **Anillo 5** |
| Acto 5 | Cenizal, el islote del volcán donde Ines acampó; la Serpemar. Farol maestro (de Ines). **Anillo 6**: el haz atraviesa el mar hasta el Ojo de la Bruma |
| Final | En el Corazón de la Bruma está Ines, mayor, calmando sola a la Madrebruma. Combate que solo se gana capturando (Canto de faro + ILUMINADA). La Bruma se levanta, vuelven los barcos, Ines vuelve a casa. Créditos |
| Posjuego | De noche aparecen las 3 últimas criaturas de bruma. **48/48**: final verdadero, el Vivero lleno y el faro "a plena luz" |

**Lore:** carteles (~80), NPC (~180), 12 páginas del diario de Ines (coleccionables: receta + pista),
8 libros en Altamar, murales en las Ruinas, la ficha de cada especie, y la Sala de la Lente (cada anillo,
un recuerdo de Ines).

### 6.5 Final
Escena de 6 imágenes (fundidos): el haz sobre el mar, barcos en Varadero, Ines y Leo en la cocina de
Tomasa, el Vivero, créditos con las especies capturadas desfilando (sus sprites de campo), "Fin". Tras
los créditos, vuelta al mapa en Varadero (posjuego) con la partida marcada `game_clear`.

---

## 7. Presentación

### 7.1 Dirección de arte
- Mundo legible en 4 tonos: suelo claro (colores 0-1), obstáculos con contorno 3, agua con 2 frames de
  animación, hierba alta con briznas en la mitad inferior (PRIO). Personajes 16x16 con contorno negro y
  halo claro (regla de dungeon: resaltan sobre cualquier fondo).
- Criaturas de combate 56x56 (máx.; las pequeñas 40x40 centradas), estilo grabado/acuarela con
  tramas; el jugador de espaldas 40x48.
- Interfaz: marcos de 9 piezas, iconos de objeto 16x16.

### 7.2 VRAM por escena (LCDC.4 = 0: BG 0-127 en `$9000`, 128-255 compartidos `$8800`; sprites 8x16 en `$8000`)
**Campo:**
| Zona | Contenido | Tiles |
|---|---|---|
| BG 0-127 | fuentes 72 (42 + 26 + 4 nuevos), UI 12 (marco 8, vacío, cursor, flecha ▼, moneda), **tileset parte A 44** | 128 |
| BG/spr 128-255 | **tileset parte B 128** (incl. 8 tiles de animación de agua/flores) | 128 |
| Sprites 0-127 | jugador 32 (andar 24: abajo/arriba/lado x 2 frames x 4; acciones 8: pescar, lanzar), NPC 3 tipos x 16 (abajo, arriba, lado, lado-paso; andar abajo/arriba = espejo X), criaturas **4 especies x 8** (2 frames, espejo X), efectos 16 (! ? Zz, destello, sombra, piedra, cebo, corcho, iconos corazón/estómago) | 128 |
Tileset exterior: **172 tiles** (≈ 70-90 metatiles). Al montar en bici, sus 24 tiles sustituyen a los
de andar (cola de tiles, 6 frames, durante una animación de 12 f). Una especie que aparece y no está
cargada ocupa un hueco libre de los 4 (carga de 8 tiles en 2 frames; aparece fuera de pantalla).
**Lint del mundo:** en cualquier ventana de 3x3 sectores, ≤ 4 especies en spawns y ≤ 3 aspectos de NPC.

**Combate:** BG 0-127: fuentes 72 + UI 12 + barras/estados 20 = 104 (24 libres); 128-255: criatura ≤ 49 +
jugador 30 + fondo del bioma ≤ 32 = 111; sprites: efectos y farolillo ≤ 72.
**Cuaderno:** fuentes + UI + marco de ficha + imagen ≤ 49 + iconos de familia. **Título:** logo ≤ 150 + fuentes.
Todas las cargas grandes con el LCD apagado dentro de un fundido. En juego solo se escriben datos de
tile por la cola (animación, bici, especies, iconos).

### 7.3 Sprites
| OAM | Campo | Sprites |
|---|---|---|
| 0-1 | iconos HUD | 2 |
| 2-3 | jugador | 2 |
| 4 | sombra / piedra de honda / corcho | 1 |
| 5-7 | emoticonos | 3 |
| 8-31 | 12 actores x 2 | 24 |
| 32-39 | libres | — |
**Por línea:** jugador 2 + 4 actores en la misma franja = 10. Si una franja pasa de 10 (manadas), los
actores rotan su orden de OAM cada frame (`gbe_spr`: lo que parpadea nunca es el jugador). Peor caso
esperado en mapas reales (lint de spawns): 8.
**Combate:** ≤ 16 sprites, ≤ 6 por línea, sin parpadeo.

### 7.4 Música y efectos (la música es trabajo del arnés: E8)
**Música** (hUGEDriver, banco propio; se reservan **4000 T/frame** y **48 KB** de ROM): Título, Varadero,
Ruta de día, Ruta de noche, Marismas/Salinas, Bosque, Cueva, Desfiladero/Minas, Altamar, Mar, Cenizal,
Faro, Bruma, Combate, Combate de jefe, Final/créditos; jingles: Victoria, Captura, Nueva receta,
Subir nivel, Enfermería, Anillo encendido, Desmayo (16 pistas + 7 jingles).
**SFX** (`gbe_sfx`, canal 4 ruido / 1 pulso; la música cede el canal mientras suenan):
| Efecto | Canal | Prio | | Efecto | Canal | Prio |
|---|---|---|---|---|---|---|
| STEP_GRASS | 4 | 0 | | CAPTURE_SHAKE | 4 | 2 |
| BUMP | 4 | 1 | | CAPTURE_OK / FAIL | 1 | 3 |
| CUT / FORAGE / PICKUP | 4 / 1 / 1 | 2 | | MENU_MOVE / OK / BACK | 2 | 1 / 2 / 2 |
| ALERT ("!") | 2 | 3 | | TEXT_BLIP (cada 2 car.) | 2 | 0 |
| SWING / HIT / CRIT / MISS | 4 / 4 / 4 / 4 | 1 / 2 / 3 / 1 | | COOK_SIZZLE | 4 | 1 |
| HURT | 1 | 3 | | EAT | 4 | 1 |
| THROW | 4 | 1 | | SAVE | 1 | 3 |
| STATUS_ON | 2 | 2 | | FISH_BITE | 2 | 3 |

---

## 8. Técnica

### 8.1 Cartucho
**MBC5 + RAM + batería (0x1B), 512 KB (32 bancos), 8 KB de SRAM:**
`["-autobank", "-Wm-yt0x1B", "-Wm-yo32", "-Wm-ya1"]` (M1: `-Wm-yo8`, 128 KB).

| Parte | Estimación |
|---|---|
| Código del motor (gbe existente usado ~6 KB + nuevo ~14 KB) | 20 KB |
| Código del kit RPG (combate 8, campo 4, comportamientos 3, menús/pantallas 8, cocina/campamento 3.5, inventario/registro/tienda 4, guardado 1, resto 6.5) | 38 KB |
| Librería GBDK | 3 KB |
| Tiles: 6 tilesets (exterior 172, interior, cueva, ruinas, volcán, faro: ~130 c/u) ≈ 820 tiles | 13 KB |
| Imágenes de combate: 48 x ~40 tiles (tras quitar repetidos) + mapas 7x7 | 33 KB |
| Sprites de campo: 48 especies x 8 + 24 NPC x 16 + jugador/bici/espaldas 90 tiles | 13.5 KB |
| UI, iconos de objeto (110 x 4 tiles), efectos | 9 KB |
| Imágenes de título y final (~4 x 150 tiles) | 10 KB |
| Mapas: ~141 sectores x 256 B (exterior 47 + mazmorras 49 + interiores 45) | 36 KB |
| Eventos de mapa (NPC, carteles, warps, spawns, parches) | 8 KB |
| Guiones (bytecode) | 20 KB |
| Texto: ~63 KB en bruto → **~40 KB** con diccionario (§8.4) | 40 KB |
| Tablas (especies, movimientos, objetos, recetas, técnicas, tiendas, spawns, jugador) | 6 KB |
| Música y SFX | 48 KB |
| **Total** | **~298 KB de 512** (58 %; los bancos de 16 KB desperdician ~10 %) |

**SRAM:** `gbe_save` con 2 ranuras alternas (`$A000` / `$B000`), partida ≈ **1.0 KB** (§8.7) ≤ 4000 B.

### 8.2 Banco 0 (16 KB, se llenó en dungeon con 13.6 KB)
- **Va en el banco 0** (presupuesto **≤ 14 KB**, el build avisa a 13): crt + librería GBDK (~3 KB), ISRs,
  `gbe_frame/video/oam/vram/vq/tiles/bank/sfx/spr/flags`, el núcleo de `gbe_world` (streaming + consultas
  asm), `gbe_gact` (mover/dibujar), el intérprete del VM de guiones (lee bytecode de cualquier banco:
  es código de banco 0 y puede cambiar de banco), el bucle principal y el paso del jugador.
- **Va en bancos (`BANKED`)**: combate, IA, captura, menús y pantallas, cocina, campamento, tienda,
  registro, guardado/carga, construcción de pantallas, operaciones de juego del VM, comportamientos
  de criaturas (1 llamada por frame: ~150 T de trampolín, aceptable), música (banco propio con
  guardar/restaurar banco en la llamada).
- **Regla de datos con banco:** el código en bancos lee datos de otros bancos **solo** con los helpers de
  `gbe_bank` (`bank_memcpy` a WRAM al empezar un combate/pantalla: especie, movimientos, textos).

### 8.3 Presupuesto de VBlank (≈ 3600 T útiles tras `vsync()`)
| Trabajo (campo, peor frame) | Cuánto | Coste |
|---|---|---|
| Sombras de registros (SCX/SCY/BGP/WX/WY/LCDC) | — | ~100 T |
| **Borde del streaming**: ≤ 2 metatiles por VBlank (`vram_mt4_list`, 100 T c/u + llamada) | 8 tiles | ~350 T |
| Cola de tiles (animación de agua **o** bici/especie/icono; nunca dos en el mismo frame) | 4 tiles = 64 B | ~800 T |
| Cola de VRAM de texto/ventana (`gbe_vq`) | ≤ 20 tiles | ~500 T |
| Celdas cambiadas (zarza cortada, parche) | ≤ 2 metatiles | ~250 T |
| **Total** | | **~2000 T (56 %)** |
- **Una fila Y una columna en el mismo frame no ocurre** (pasos de un solo eje). Peor caso teórico si un
  guion forzara las dos (giro de cámara en diagonal, que los guiones no permiten): fila 12 + columna 11 =
  23 metatiles ≈ 2.4k T → cabría en un VBlank sin nada más; se reparte igualmente a 2 por frame.
- Teletransporte, warp, vuelta de combate o de pantalla: reconstrucción con LCD apagado en un fundido.
- Combate: barras (≤ 2 tiles), texto (≤ 20), parpadeo de criatura 49 tiles (~1000 T) → ≤ 1600 T.

### 8.4 Presupuesto de CPU (fuera de VBlank), campo en el peor frame
Costes medidos de `budgets.md`: C ~800 T por objeto, OAM ~300 T por objeto dibujado.
| Trabajo | Cómo | Coste |
|---|---|---|
| Entrada, estado, paso del jugador, consultas de casilla (asm ~100 T) | C + asm | ~2000 T |
| 12 actores: mover/animar (C) | 12 x 800 | ~9600 T |
| IA: 1 criatura piensa por frame (BANKED) | C | ~1800 T |
| Sprites: 13 objetos 16x16 + HUD/emoticonos | 15 x 300 | ~4500 T |
| Preparar el borde al empezar un paso (12 metatiles a la lista) | asm + C | ~2000 T |
| Caché de sectores al cruzar un límite: 1 sector por frame (`bank_memcpy` 256 B) | asm | ~2800 T |
| Activar eventos/spawns del sector nuevo (1 sector por frame) | C | ~2000 T |
| VM de guiones / cuadro de texto | C | ~1500 T |
| Supervivencia (por paso) + SFX | C + asm | ~600 T |
| Música (reserva) | asm | ~4000 T |
| **Total peor frame** | | **~30 800 T ≈ 68 líneas** (x1.5 de margen por las sorpresas de shmup: ~100) |
Objetivo de test: **`max_frame_lines < 120`**, `vram_late == 0`. Construir una pantalla de menú (lista de
8 filas de texto) ~15k T; guardar ~60k T (`skip_measure`, acción de menú). Calcular un turno de combate
~5-10k T (no es crítico: pasa entre animaciones).

### 8.5 RAM (WRAM 8 KB)
| Bloque | Bytes |
|---|---|
| Caché de sectores 3x3 x 256 | 2304 |
| Actores 12 x ~20 (struct of arrays) + ocupación | 260 |
| Eventos de los sectores cargados (índice) + parches temporales (8) | 450 |
| VM: registros, pila de llamadas (8), temporizadores | 64 |
| Cuadro de texto: búferes de línea y de página | 170 |
| Unión por estado: combate (~300) / pantallas (listas, cocina, tienda ~512) | 512 |
| **Estado de partida** (lo que se guarda, §8.7) | ~1000 |
| Colas: borde 2 x 48, `gbe_vq` 64, tiles 64 | 224 |
| shadow OAM | 160 |
| Pila | 512 |
| **Total** | **~5.7 KB de 8** (si falta: caché 2x2 sectores = −1280, con radio de actividad 8) |

### 8.6 Riesgos técnicos y mitigación
| Riesgo | Mitigación |
|---|---|
| Banco 0 se llena (dungeon: 13.6 KB con un piso) | presupuesto ≤ 14 KB desde M1a, aviso del build a 13 KB; todo lo no caliente `BANKED` desde el principio |
| CPU de 12 actores en C (~800 T c/u) más de lo estimado | `gbe_gact` con movimiento/dibujo en asm (como `act_move`/`spr_group`); IA a 1 por frame; medir en M1a con 12 actores sintéticos (`games/gbe_lab`) |
| Cambiar de banco en sitios prohibidos (cuelgues) | reglas de §8.2; lint del build existente; test de 20 000 f con `_current_bank` coherente |
| Streaming 4 direcciones (nuevo) con huecos o tiles tarde | margen de 1 casilla en los 4 lados; test VRAM == modelo de la ventana visible en cada paso (bot), `vram_late == 0` |
| Volumen de contenido (48 especies, 141 sectores, ~60 KB de texto) | todo con conversores y lint; vista previa del mundo entero en PNG; M1 pequeño; el artista trabaja por actos |
| Equilibrio (formulas, economía, hambre) | modelo de combate en Python verificado contra el ROM; bots de equilibrio por acto (§12) |
| Música: no existe aún en el arnés | E8 en M2; 4000 T y 48 KB reservados desde M1 |
| Guardado grande cortado a mitad | `gbe_save` ya escribe la firma la última y alterna ranuras; test con `gb.power_off()` |
| Sprites > 10 por línea con manadas | lint de spawns (≤ 4 especies/3x3 sectores, manadas de ≤ 3) + rotación de OAM |

### 8.7 Partida guardada (versión 1)
`map_id, x, y, dir, last_clinic, phase, steps(2), play_secs(3)` · jugador `name[5], level, xp(2), pv, en,
sac, buff, buff_steps(2), st, money(2), weapons[3], armor, skills(2 bits→2 B)` · `items[128]` · `age[16]`
(perecederos) · `full_lanterns[24][2]` · `registry_seen[6], registry_caught[6]` · `kills[48]` ·
`recipe_known[4]` · `flags[128]` (1024 banderas de historia, recogidas, encargos) · `vars[16]` ·
`lamp_ring` · `visited_towns` · `registered_gadget` · `options` → **≈ 1000 B**.

### 8.8 Globales para tests (no `static`)
`state, field_sub, screen_id, map_id, px, py, pdir, pstep_px, cam_x, cam_y, steps, sac, buff, buff_steps,
pv, pv_max, en, en_max, level, xp, money, items[], age[], weapons[], armor, lamp_ring, flags[], vars[],
registry_seen[], registry_caught[], kills[], recipe_known[], full_lanterns[], phase, act_type[], act_x[],
act_y[], act_state[], act_species[], spawn_timer[], b_turn, b_cpv, b_cpv_max, b_species, b_level, b_st,
b_flags, b_result, cook_result, last_recipe, script_pc, script_trace[16], tbox_busy, wcache_sector[9],
edge_pending, max_frame_lines, vram_late, skip_measure, rng_state, cheat_flags` (bit 0 invencible, 1
criaturas congeladas, 2 captura segura, 3 sin hambre; solo los escriben los tests).

---

## 9. Hitos

| Hito | Alcance | Criterios de salida |
|---|---|---|
| **M1a — motor** | E1-E7, E9-E12, E14-E16 (§10.5) con referencias C y `gbe_selftest`; demo en `games/gbe_lab` o `faro`: mapa de prueba 4x4 sectores, andar/bici con streaming, 12 actores errantes, cuadro de texto con un guion, panel deslizante, guardar/cargar | selftest 0 fallos; VRAM visible == modelo tras 2000 pasos de bot; `max_frame_lines` y costes **medidos** apuntados en `budgets.md`; banco 0 ≤ 14 KB |
| **M1b — slice jugable** | Varadero (2x1 sectores: casa de Ines, casa/cocina de Tomasa con posada, tienda, enfermería), Sendero del Cabo (1x2), cabo con el Faro (planta baja + Sala de la Lente), claro tras zarzas (1x1); especies 1-6 (5 comportamientos: errante, asustadizo, volador, dormilón, perseguidor); combate completo (3 armas, 4 técnicas, red/cebo/honda, pociones, comida, 2 tipos de farolillo, huir); cazar + botín; PX hasta ~L8; saciedad, estropeado y sal; campamento; cocina (recetas 1-8, 2 por descubrir); Cuaderno (6 fichas); anillo 1 (escena) y "Fin de la demo"; machete como recompensa de un encargo (el pescador pide 3 Plumas; prueba de puertas por habilidad); guardar/continuar; desmayo; título; SFX; día fijo | bot completa el slice (≥ 5 capturas → anillo 1) en 25-45 min de juego simulado; tests de §11 verdes; el usuario lo juega |
| **M2 — Acto 1 + sistemas** | Marismas, Salinas, Garzareal; pesca, día/noche, bordillos, emboscadas, manadas; música (E8) con 5 pistas; nombre del jugador; texto con diccionario si hace falta; **paquete de contenido alternativo** de prueba (§10.2) | bot de equilibrio del Acto 1 dentro de objetivos; test de contenido alternativo verde |
| **M3 — Actos 2-3** | Bosque, Robledo, Cueva, Desfiladero, Hondura, Minas; bici, farol, garfio, zurrón; 17 especies | tiempos por región del bot en ±25 % de §6.2 |
| **M4 — Actos 4-5 + final** | Acantilados, Altamar, Ruinas, mar, Cenizal, Corazón; silbato, bote; final y créditos; posjuego | bot completa la historia con trampas de tiempo; 48/48 alcanzable (lint) |
| **M5 — pulido** | entrada de la criatura deslizándose (corte LYC), animaciones de reposo, Vivero con criaturas registradas, todas las pistas, equilibrio final con bots y playtest | playtest humano del juego completo |
| **M6 — hardware** | flash cart, SRAM con batería real (cortar la corriente al guardar), legibilidad en LCD, 10 h de partida real | sin bugs bloqueantes; lista de errores cerrada |

---

## 10. Arquitectura: motor, kit RPG, contenido

### 10.1 Capas
| Capa | Dónde | Qué contiene | Regla |
|---|---|---|---|
| Motor genérico | `harness/common/src/gbe_*` | scroll, actores, texto, VM, menús, colas, guardado, música | sin nada de RPG; vale para cualquier juego |
| Kit RPG | `games/faro/src/rpg/*.c` | reglas del género: combate, captura, IA, supervivencia, cocina, inventario, registro, tienda, campo, pantallas | **sin contenido**: ni nombres, ni ids concretos, ni números de equilibrio; candidato a `harness/common` cuando lo use un segundo juego |
| Contenido | `games/faro/res/` | tablas, mapas, guiones, textos, tiles, imágenes, música | solo datos |
| Pegamento | `games/faro/src/main.c` | bucle, estados, `screen_build` | mínimo |
Ganchos del sistema (dinero, farolillo maestro, habilidades) se marcan en los datos con un `role` o
`ability`; el kit pregunta por el rol, nunca por un objeto.

### 10.2 Cómo se comprueba que el contenido es intercambiable
- Lint del build/test: en `src/rpg/` no aparecen `SPECIES_*`, `ITEM_*`, `MAP_*`, `RECIPE_*`, `FLAG_*`
  ni literales de texto (salvo depuración).
- **Paquete alternativo (M2):** `games/faro/tests/content_alt/` (2 especies, 1 mapa de 1 sector, 3
  objetos, 1 receta, 1 guion, otro idioma de ejemplo) compilado con el mismo `src/`; un test juega un
  combate, una captura y una receta con él.

### 10.3 Datos y formatos (fuentes ASCII revisables por agentes; conversores en `harness/`)
| Fuente | Conversor | Salida (con banco) | Contenido |
|---|---|---|---|
| `res/data/*.tbl` | `harness/tables.py` (E12) | structs C + cargador Python para tests | `species` (tiers, catch, xp, familia, resistencias 5x2 bits, movimientos y pesos, comportamiento, vista, velocidad, horario, cebo, cond, botín, sprites), `moves`, `items` (categoría, tope, precio, efecto, ability, role, perece), `recipes`, `skills`, `player` (por nivel), `shops`, `spawns`, `fishing`, `forage`, `caps`, `statuses`, `buffs`, `families`, `dtypes`, `looks` (aspectos de NPC), `rules` (constantes sueltas de este documento: `RULE_*`) |
| `res/metatiles_<set>.mt` | `metatiles.py` (+ E16: `kind` y grupos de animación) | `mt_tiles`, `mt_attr` por tileset | §2.2 |
| `res/maps/<mapa>.map` | `harness/world.py` (E10) | sectores sin repetir, cabecera de mapa (tileset, rejilla de sectores, borde, música, banderas), eventos por sector | rejilla ASCII 1 carácter = metatile (leyenda del `.mt`), capa de objetos, líneas `@` |
| `res/scripts/*.evs` | `harness/script.py` (E11) | bytecode + tabla de textos con diccionario | guiones y diálogos |
| `res/*.pic` | `harness/pictures.py` (E9) | tiles sin repetir + mapa | imágenes grandes (criaturas, título, espaldas, final) |
| `res/*.tiles` | `asciitiles.py` (existe) | tiles | sprites, tilesets, UI |

**Datos de M1b (v1.1):** los esquemas (columnas y su significado) están en la cabecera de cada
`res/data/*.tbl`; `tests/test_data.py` reproduce los ejemplos de §3.10 con esas tablas (semilla de
`battle_model.py`). Nombres cortos de ui.md §17 adoptados (Cuchillo, Farol de plata, Madera, VEN...).

**Ejemplo de mapa** (`res/maps/varadero.map`):
```
@ map VARADERO            @ tileset exterior     @ origin 2 5      @ size 2 1
@ music pueblo            @ flags OUTDOOR BIKE   @ border SEA
grid:                     ; 16 filas x 32 caracteres (leyenda de metatiles_exterior.mt)
objects:                  ; misma rejilla: letras = eventos, '.' nada
@ obj A npc sprite=COCINERA move=STILL face=DOWN script=tomasa_casa
@ obj B sign script=cartel_varadero
@ obj C warp to=CASA_INES 4 7 face=UP
@ obj D item POCION 1 flag=PICK_VAR_1
@ obj E spawn table=PLAYA_VAR radius=3
@ obj F forage table=BAYAS respawn=512
@ obj G trigger script=intro_muelle once=F_INTRO
@ obj H patch flag=F_PUENTE mt=PUENTE          ; cambio permanente del mapa si la bandera está puesta
```
**Ejemplo de guion** (`res/scripts/varadero.evs`):
```
script tomasa_casa
  if flag F_DIARIO goto ya
  face player
  say "{N}! Tu abuela me dejo esto para ti."
  give DIARIO_INES 1
  give FAROLILLO 5
  set F_DIARIO
  end
ya:
  ask "Cocinamos algo?" no=fin
  cook                          ; op de juego: abre la COCINA
fin:
  end
```
**Opcodes del VM** (núcleo en el motor, ~30): `END GOTO CALL RET IF_FLAG IFN_FLAG SET CLR VAR_SET VAR_ADD
IF_VAR SAY ASK CHOICE WAIT FACE MOVE_ACTOR MOVE_PLAYER SHOW HIDE EMOTE WARP FADE SHAKE SFX MUSIC CAMERA
SET_CELL RAND LOCK UNLOCK`. **Operaciones de juego** (kit, por tabla de despacho, ~20): `GIVE TAKE HAS
MONEY BATTLE SHOP HEAL INN COOK LEARN_RECIPE LEARN_SKILL REG_COUNT LAMP_RING SAVE_PROMPT QUEST TEACH
SET_GADGET PHASE CREDITS NAME`.

**Texto:** volumen estimado ~63 KB (NPC 16, escenas 16, objetos 8, fichas 6, carteles 5, diario y libros
7, combate/sistema/UI 5). Codificación: 1 byte por carácter; bytes ≥ 0x80 = una de 128 palabras o
pares frecuentes del diccionario que calcula `script.py` (≈ 35-40 % menos). Se decodifica al escribir
(1-2 caracteres por frame): coste despreciable.

### 10.4 Lint del mundo (Python, `world.py` + tests)
Warps con destino válido y casilla de llegada transitable; eventos sobre casillas válidas; todas las
casillas transitables alcanzables con el conjunto de habilidades y anillos de su acto (BFS por acto);
cada especie obtenible tras su puerta (spawn o guardián que se rinde); ≤ 4 especies y ≤ 3 aspectos de NPC
por ventana de 3x3 sectores; ≤ 6 NPC por sector; ≤ 12 eventos por sector; manadas ≤ 3; costuras de
tileset (M3) solo con metatiles comunes; textos ≤ 18 caracteres por línea tras partir.

### 10.5 Trabajo de motor (`harness/common`), en orden de M1a
Reutiliza tal cual: `gbe_frame`, `gbe_oam`, `gbe_screen`, `gbe_sfx`, `gbe_vram` (`vram_mt4_list`,
`vram_row20`), `gbe_vq`, `gbe_text`, `gbe_menu`, `gbe_rng`, `gbe_bank`, `gbe_save` (2 ranuras),
`gbe_spr` (rotación), fuentes, `screens.py`, `gb.run_bot`, `gb.profile`, `gb.worst_frames`,
`gb.selftest`, `gb.power_off`. **No usa:** `gbe_map`, `gbe_vmap`, `gbe_pool`, `gbe_aim`, `gbe_view`, `gbe_bgbuf`.

| # | Pieza | Qué hace | Para quién más |
|---|---|---|---|
| E1 | `gbe_world` (+ `.s`) | mapa de sectores en 4 direcciones: caché 3x3 en WRAM con tabla de huecos, cámara centrada, anillo de BG 32x32 con margen de 1 casilla, borde por paso a ≤ 2 metatiles/VBlank, `world_set_cell` + parches temporales, `wmt_at(x,y)`/`wattr_at` en asm (+ C), recarga completa con LCD apagado | cualquier aventura/RPG de vista cenital |
| E2 | `gbe_gact` (+ `.s`) | actores por casillas: interpolación por tabla de velocidades, animación de andar, dibujo en 8 bits relativo a la cámara con bit PRIO por casilla, ocupación, comportamientos genéricos parametrizados (quieto, mirar, errar, huir, perseguir, ruta, seguir al líder) | NPC y enemigos de cualquier juego de rejilla |
| E3 | `gbe_script` | VM de bytecode (§10.3): núcleo + tabla de operaciones del juego; lee de cualquier banco; traza `script_trace` para tests | eventos de cualquier juego con historia |
| E4 | `gbe_tbox` | cuadro de diálogo en la ventana: máquina de escribir, 2 líneas, paginar, ▼, Sí/No y elección de hasta 4, variables, diccionario | todos los juegos con diálogo |
| E5 | `gbe_list` | lista con scroll (n elementos, k visibles, columnas nombre/cuenta/precio), sobre `gbe_menu` | inventarios, tiendas, registros |
| E6 | `gbe_tiles` | cola de datos de tile (16 B) con presupuesto por VBlank (la E15 pendiente de dungeon) | animaciones de fondo, cambios de sprite |
| E7 | `gbe_flags` | banderas (bitset u16) y variables | historia y guardado |
| E8 | `gbe_music` (M2) | hUGEDriver en su banco, llamado desde el bucle tras las copias, cede canales a `gbe_sfx` | primera música del estudio |
| E9 | `harness/pictures.py` + `.pic` | imagen ASCII de cualquier tamaño (múltiplo de 8) → tiles sin repetir + mapa; vista previa | criaturas, títulos, finales |
| E10 | `harness/world.py` + `.map` | mapas/eventos → sectores con banco; lint (§10.4); PNG del mundo entero y de cada mapa con eventos | RPG/aventura |
| E11 | `harness/script.py` + `.evs` | compilador de guiones y textos con diccionario; lint de etiquetas, banderas y longitudes | idem |
| E12 | `harness/tables.py` + `.tbl` | tablas de datos → C con banco + cargador Python | cualquier juego con datos |
| E13 | `harness/gbtest.py` | leer structs/arrays por nombre, `gb.script_trace()`, `gb.window_map()`, avanzar diálogos (`gb.advance_text()`) | tests de RPG |
| E14 | fuentes compartidas | glifos COMMA, APOS, EXCL_OPEN (¡), QUES_OPEN (¿) + mapeo en `screens.py`/`preview.py`/`gbe_text` | todos (texto en español) |
| E15 | `gbe_video` | sombras de WX/WY y bit de ventana aplicadas en VBlank; modos: ventana abajo, panel derecho, pantalla completa | menús superpuestos sin interrupción |
| E16 | `metatiles.py` | campo `kind` de 5 bits y grupos de animación (`@ anim WATER 4 2 24`) | mapas con agua/flores animadas |

---

## 11. Plan de pruebas

Bots con `gb.run_bot` que **deben avanzar** (progreso = casillas nuevas visitadas + 50 x capturas + 20 x
cazas + 500 x anillo). El bot de campo lee `px/py`, actores y la caché, hace BFS en Python con las mismas
reglas de casilla (`world.py`) y traduce a pulsaciones.

| Qué | Cómo |
|---|---|
| Autoprueba del motor | `gb.selftest()` → 0 diferencias en `wmt_at`, borde de streaming, `gact` mover/dibujar, decodificador de texto |
| Movimiento | por dirección: 16/32/8/12 f por casilla (andar/sigilo/bici/bote); toque < 6 f gira sin andar; chocar no mueve; bordillo 2 casillas en 24 f solo en su sentido; SLOPE 32 f andando |
| **Streaming == modelo** | tras cada paso del bot (2000 pasos por el exterior, en bici y andando): la ventana visible + margen del mapa de BG == metatiles de `world.py` en esa posición; `vram_late == 0` |
| Caché de sectores | al cruzar límites en las 4 direcciones y en esquinas: `wcache_sector[]` correcto; consultas en el borde de la caché iguales al mapa |
| Casillas especiales | zarza con/sin CUT, cueva oscura con/sin LIGHT, grieta con HOOK, mar con BOAT, muro de BRUMA según `lamp_ring`, hierba con bit PRIO en OAM |
| Comportamientos | criatura sola con `cheat_flags` congelando las demás: vista andando/sigilo/bici (distancias exactas), "!" 24 f, huida/persecución/vuelta a casa, dormilón (probabilidad de despertar con `rng_state` fijado), emboscada salta al quedar adyacente, ≤ 1 criatura piensa por frame |
| Spawns | ≤ 6 criaturas activas; nunca aparecen dentro de la pantalla; reaparición a 600 f / 1024 pasos / al descansar; horario |
| **Combate == modelo** | `battle_model.py` (Python, mismas tablas y fórmulas): 500 combates con `rng_state` aleatorio fijado → daño, acierto, crítico, orden, estados, huida, captura y PX idénticos al ROM (`b_*`). Ejemplos A y B de §3.10 exactos |
| Captura | cada factor de §3.6 por separado; condición no cumplida → 0; guardián RENDIDO; primera captura registra y da PX x2; repetida va a farolillos llenos; tope de la lista |
| Supervivencia | `sac` −1 cada 32 pasos y −1 por combate; umbrales 60/25/0 (regeneración, ATQ, PV mínimo 1); EN +1/24 pasos; veneno en el campo; buffs con duración en pasos; estropeado a `age` 40 (la mitad, `age` 20), sal |
| Campamento | dónde sí/no (CAMP, pueblo, criatura alerta cerca), gasta 1 leña, descansar (+50 % PV, EN llena, estados, `sac −8`, spawns reiniciados), abrir farolillos |
| Cocina | todas las recetas de `recipes.tbl` con sus ingredientes en cualquier orden; descubrimiento pone `recipe_known`; mejunje; repetir y x N; topes |
| Economía e inventario | comprar/vender con precios de la tabla, dinero ≤ 9999, topes por categoría (y Zurrón), desmayo = mitad del dinero y enfermería |
| Guiones y texto | `script_trace` de cada guion de M1 contra lo esperado; ramas por bandera; `gb.window_map()` == texto esperado (lint de 18 car.); máquina de escribir a la velocidad elegida, ≤ 4 tiles/f |
| **Guardado** | guardar en campo, campamento y tras cada tipo de evento; `ram = gb.power_off(); GB(rom, ram=ram)` → Continuar → todo el estado de §8.7 igual; ranuras alternas; corromper la nueva → carga la vieja; SRAM deshabilitada fuera del acceso |
| Contenido intercambiable | lint de `src/rpg/`; paquete alternativo (M2) |
| **Presupuesto de frame** | bot de campo 20 000 f (andar + bici, cruzando sectores, con 12 actores) + bot de combates 5000 f + bot de menús: `max_frame_lines < 120`, `vram_late == 0`; `gb.profile` de `world_*`, `gact_*`, IA, OAM, VM; `gb.worst_frames()` |
| Lint del mundo (Python puro) | §10.4 sobre todos los `.map` |
| Capturas | campo de día/noche, hierba sobre el jugador, texto, panel, combate (inicio, golpe, captura), Cuaderno (lista y ficha), cocina, campamento, tienda → revisión con Read |
| **Bots de equilibrio (informes, con asserts amplios)** | (1) combate: para cada zona, jugador al nivel esperado de §6.2 con el equipo de su tienda contra cada especie de la zona → turnos para cazar 2-5, PV perdidos 10-40 %, capturable con ≤ 3 farolillos de media con la táctica "Golpe suave + mejor estado"; (2) hambre: comidas por hora 3-6, nunca desfallecido en una ruta normal si come lo que caza; (3) economía: dinero al final de cada acto 100-600 C tras compras básicas; (4) tiempo por región ±25 % de §6.2 (pasos x 16 f + combates x duración media medida); (5) PX: nivel al llegar a cada anillo dentro del rango de §6.2 |
| **Playtest humano** | sensación del paso y del scroll, legibilidad de criaturas y hierba en LCD borroso, si el sigilo y los cebos divierten, si el hambre agobia o se olvida, claridad de la captura (¿se entiende "debilitar sin matar"?), ritmo del Prólogo, duración del slice |

---

## 12. Decisiones tomadas (2026-10-14, por el estudio con la recomendación del diseñador)

El usuario pidió no preguntar lo que se puede cambiar luego; estas cuatro se toman con la opción
recomendada y se pueden revisar:
1. **48 especies.**
2. **Imagen de combate hasta 56x56** con el jugador de espaldas 40x48.
3. **Ciclo de día y noche por pasos** (cada 1536) y al descansar, desde M2.
4. **hUGEDriver + hUGETracker** para la música (tarea del arnés en M2).

Decidido por el diseñador (barato de cambiar, se puede tocar después): título y escenario (FARO, isla
de Albor), nombres, historia, tono; HUD discreto con iconos; muerte = mitad del dinero; enfermería
gratis; el hambre no mata; sigilo con B; 3 armas a mano; 1 partida guardada con 2 ranuras de seguridad.
