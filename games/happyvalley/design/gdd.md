# HAPPY VALLEY — Documento de diseño

Estado: aprobado    Versión: 1.0 (2026-10-15)    Carpeta: `games/happyvalley`

> Gestión de una cuadra de carreras de caballos en Hong Kong, al estilo de *Derby Stallion*.
> Regla del estudio: **primero greybox** (cuadrados de `harness/common/greybox.tiles` + `font_mini`)
> para validar toda la lógica; el arte llega en M3, cuando el usuario haya jugado M1.
> Tema, nombres, textos y dificultad los decide el diseñador. Lo caro de cambiar está en §12.
> Especificación ejecutable de la carrera: `design/race_proto.py` (prototipo de calibración en
> Python, enteros y el mismo xorshift que `gbe_rng`). Si este documento y el prototipo discrepan en
> la carrera, manda el prototipo y se corrige el GDD.

---

## 1. Pitch

- **Género:** gestión de cuadra + crianza, por turnos semanales, con carreras simuladas que se ven.
- **Fantasía:** heredas la cuadra pequeña de tu tío en Sha Tin: tres caballos, una yegua vieja en la
  última granja de Lantau y 800k en la cuenta. Entrenas semana a semana, eliges jinete y táctica,
  miras la carrera bajo los focos de Happy Valley y, generación tras generación, crías al caballo que
  gane la **Copa Internacional** de diciembre.
- **Bucle principal:** planifica la semana (entrenar / descansar / inscribir) → mira tus carreras →
  cobra, sube de rating y de clase → cruza a tus yeguas → la siguiente generación es mejor.
- **Qué lo hace distinto:** dos hipódromos que se juegan distinto. **Happy Valley** (miércoles por la
  noche): óvalo pequeño, curvas cerradas, el **cajón de salida pesa mucho**. **Sha Tin** (domingos):
  pista grande, césped y arena, rectas largas, las grandes copas. Sistema de hándicap de Hong Kong
  (clases 5 → 1, rating que se mueve con los resultados, peso según rating).
- **Sesión:** una semana de juego = 20 s - 2 min. Una temporada (44 semanas) ≈ 40-60 min. Guardado
  automático cada semana: se deja en cualquier momento.
- **Referencias:** *Derby Stallion* (SFC/GB: semanas, cruces, carrera vista); *Winning Post* (economía,
  sementales con cuota); hipódromos reales de Hong Kong (calendario, clases, pesos, carreras nocturnas).
  Estudio: `games/dungeon` (menús, bancos, guardado), `games/mazmorra` (`font_mini` + `gbe_vwf`),
  `games/faro` (tablas `.tbl` y modelo Python espejo; y su lección de alcance).

### Historia y tono
Tu tío Lam entrenó 30 años en Sha Tin sin ganar nunca la Copa Internacional. Te deja la cuadra con
una nota: "La yegua es mejor de lo que parece". Textos breves y cálidos, con humor de hipódromo
(el mozo de cuadra **Ah Fat** da los consejos y los partes semanales). Dificultad objetivo: amable al
principio (nada te arruina en la temporada 1 si no maltratas a los caballos), profunda a largo plazo
(ganar la Copa Internacional pide 3-5 temporadas y caballos criados por ti).

---

## 2. Mecánicas

Convenciones: todo entero (8/16 bits, u32 solo para el dinero). RNG único `rng_state` de `gbe_rng`
(xorshift16 7,9,8), sembrado con DIV + contador de frames al pulsar "Nueva partida" y guardado en la
partida. `rng_range(n) = (rng_next() * n) >> 8`. **El orden de las llamadas al RNG es parte de la
especificación** (cada sección lo dice): el modelo Python de los tests (`tests/hv_model.py`) lo repite
exactamente. **Todos los números de equilibrio van en `res/data/*.tbl` (§2.13)**; los valores de este
documento son los de partida: (*) = ajustar con los bots de equilibrio (§11).

### 2.1 El caballo

| Atributo | Rango | Visible | Qué hace |
|---|---|---|---|
| VEL velocidad | 1-99 | sí | velocidad de crucero máxima (`vmax`) |
| RES resistencia | 1-99 | sí | energía para la carrera |
| REM remate | 1-99 | sí | aceleración y velocidad extra en el sprint final |
| TEM temperamento | 1-99 | sí | alto = tranquilo: menos salidas malas y menos "tirones" |
| SAL salud | 1-99 | sí | recuperación de fatiga y resistencia a lesiones (no se entrena) |
| Potencial (VEL RES REM TEM SAL) | 10-99 | no (estrellas) | techo de cada atributo |
| Distancia ideal `dpref` | 10-24 (x100 m) | sí | fuera de ella rinde menos |
| Superficie `surf` | -3..+3 | sí ("Cesped ++") | + césped, - arena |
| Estilo natural | puntero / acecho / cerrador | tras 1 carrera | táctica distinta = más tirones |
| Curva de crecimiento | precoz / normal / tardío | no (pista de Ah Fat) | a qué edad entrena mejor |
| Rating | 0-140 | sí | clase y peso |
| Fatiga `fat` | 0-100 | sí (barra) | > 50 rinde menos; > 80 no puede correr |
| Lesión | semanas (bit 7 = grave) | sí | solo descanso |

- Los atributos actuales VEL RES REM se guardan x16 (`vel16`, u16) para que el entrenamiento sume
  fracciones; se muestran `>> 4`. TEM y SAL son u8 directos.
- **Estrellas de potencial** (ficha, tras 4 semanas en la cuadra): media de los potenciales de VEL RES
  REM: < 40 = 1, < 55 = 2, < 70 = 3, < 85 = 4, si no 5. Yeguas y sementales muestran sus potenciales
  como números (ya están hechos).
- Edad: sube en la semana 1 de cada temporada. Corre de 2 a 8 años; retiro obligado al cumplir 9.

### 2.2 Calendario y semana

- **Temporada = 44 semanas.** Semanas 1-40: carreras (septiembre → mediados de julio, como Hong Kong).
  Semanas 41-44: **verano** (sin carreras; nacen los potros en la 41). En la semana 44 → semana 1 de
  la temporada siguiente (envejecer, §2.11). Mes de cada semana en `calendar.tbl` ("Sep sem 2").
- Cada semana de carreras: **miércoles noche en Happy Valley** (4 carreras) y **domingo en Sha Tin**
  (4 carreras, una puede ser especial). Las cartas salen de plantillas (`meetings.tbl`), y
  `calendar.tbl` dice qué plantilla y qué carrera especial toca cada semana.
- Un caballo corre como mucho una vez por semana. Plan de cada caballo para la semana: un
  entrenamiento (§2.5) o una inscripción (§2.3). Por defecto se repite el plan anterior.

**Orden de resolución al pulsar "Avanzar semana"** (el modelo Python lo sigue igual):
1. Carreras del miércoles (HV) con inscripciones tuyas, por orden de carta: generar campo (§2.9) →
   presentación → carrera (§2.4) → resultado (premio §2.7, rating §2.6, fatiga y lesión de carrera §2.8).
2. Entrenamiento de cada caballo en cuadra sin carrera esta semana, por orden de hueco (§2.5, §2.8).
3. Carreras del domingo (ST), igual que el paso 1.
4. Para todos los caballos en cuadra, por hueco: recuperación de fatiga (§2.8), cuenta atrás de lesión,
   contador de inactividad.
5. Gastos semanales (§2.7), deudas.
6. `week++`; eventos: confirmación de preñez (§2.10), nacimientos (semana 41), cambio de temporada.
7. Parte semanal (pantalla INFORME) y **autoguardado**.
Las carreras sin caballos tuyos no se simulan (los rivales no persisten entre carreras).

### 2.3 Inscripción

- Requisitos: edad ≥ 2, sin lesión, `fat ≤ 80`, no inscrito ya esta semana, y clase permitida:
  carrera de su clase (rating dentro de la banda) o **una clase por encima** (sube con el peso mínimo).
  Carreras especiales: rating mínimo propio (§2.12).
- Bandas de clase (rating): C5 0-40, C4 40-60, C3 60-80, C2 80-100, C1 100-140. En el límite exacto
  (40, 60...) el caballo es de la clase superior.
- Se eligen: **jinete** (§2.4.6, coste por monta + 12.5 % del premio) y **táctica**: Puntero, Acecho,
  Cerrador. El cajón se sortea al generar el campo (después de inscribir).
- **Peso (lb)**: hándicap: `peso = clamp(133 - (techo_banda - rating), 113, 133) - descargo_jinete`.
  Especiales (peso por edad): 126 lb, hembras 122 lb.
- Número de dorsal: por peso descendente, empate por rating descendente, luego por hueco.

### 2.4 La carrera (modelo)

Unidades: posición `pos` en 1/16 m (u16, hasta 4095 m) + fracción u8; velocidad `spd` en 1/4096 m por
tick (u16; m/s = spd / 163.84). **1 tick = 1 frame = 0.04 s de carrera** (la tele va a x2.4: 1200 m
se ven en ~30 s, 2400 m en ~60 s). Tiempo mostrado = ticks x 4 centésimas. 1 cuerpo `LEN` = 38
(2.375 m). Campo: HV 12 caballos, ST 14.

#### 2.4.1 Recorridos (`courses.tbl`)
Cada recorrido = lista de tramos (metros, recta/curva) de la salida a la meta, y factor de curva `bk`.

| Recorrido | Tramos (m, R = recta, C = curva) | bk |
|---|---|---|
| HV 1000 | R269 C419 R312 | 5 |
| HV 1200 | C169 R300 C419 R312 (sale en curva: el cajón decide) | 5 |
| HV 1650 | R200 C419 R300 C419 R312 | 5 |
| HV 1800 | R350 C419 R300 C419 R312 | 5 |
| ST 1000 | R1000 (recta) | 4 |
| ST 1200 | R335 C435 R430 | 4 |
| ST 1400 | R535 C435 R430 | 4 |
| ST 1600 | C135 R600 C435 R430 | 4 |
| ST 2000 | R100 C435 R600 C435 R430 | 4 |
| ST 2400 | C70 R430 C435 R600 C435 R430 | 4 |
| Arena 1200 | C38 R400 C397 R365 | 5 |
| Arena 1650 | R91 C397 R400 C397 R365 | 5 |

Recta final = último tramo. En curva, un caballo a `lane` calles del palo avanza menos:
`prog = spd - (((spd >> 4) * (lane * bk)) >> 5)` (HV: -1 % por calle; ST: -0.8 %).

#### 2.4.2 Antes de la salida (una vez)
Para cada caballo `i` en orden de hueco del campo (RNG: forma, ruido de sprint, retraso):
```
apt  = surf (césped) o -surf (arena)
vmax = V0 + KV*VEL - KW*(peso-113) + KJ*jinete + KSF*apt          V0 2720, KV 3, KW 2, KJ 2, KSF 12
si dist100 < dpref: vmax -= (dpref - dist100) * KDS                 KDS 6
si fat > 50:        vmax -= (fat - 50) * 2
vmax += (rng_range(7) - 3) * 6                                      forma del día
ene  = (800 + 12*RES) * 16                                           energía, 1/16 unidades
dmul = 8 + max(0, dist100 - dpref)                                   gasto x dmul/8 si la carrera es larga
accL = 24 + (REM >> 2);  acc = 2 + (REM >> 4);  kick = REM >> 1
sprint_at = SPRINT_AT[táctica] + rng_range(41) - 20                 350 / 450 / 650 m
delay = rng_range(4)                                                 ticks sin moverse al abrirse los cajones
lane = cajón - 1;  eff = START_EFF[táctica]                          E2 / E1 / E0
```
Después, para cada `i`: salida mala si `rng_next() < ((100-TEM) >> 2) + (10 - jinete)`:
`delay += 8 + rng_range(8)`.

#### 2.4.3 Cada tick `t` (desde 0), caballos en orden de hueco, saltando los que ya llegaron
```
si delay > 0: delay--, siguiente caballo
si (t & 3) == (i & 3): pensar(i)                     (§2.4.4: 1 de cada 4 caballos por tick)
spd -> target: si spd < target: spd = min(target, spd + (launch ? accL : acc))
               si no:           spd = max(target, spd - 4)
launch = 0 cuando spd >= vmax - vmax/8 (fin de la arrancada)
si block >= 0: spd = min(spd, spd[block])            (encerrado detrás de otro)
prog = spd (menos la pérdida de curva §2.4.1); pos:frac += prog
energía: si ene > 0: dr = (COST[eff] * dmul) >> 3; si tirón: dr <<= 1; si no, si cubierto: dr -= dr >> 2
         ene = max(0, ene - dr)                      COST = 3 / 5 / 8 / 14 (E0..E3)
si tirón: tirón--
si pos >= dist*16: llegada = (t, pos - dist*16)
```
Al final del tick: ordenación por inserción estable de `order[]` por `pos` descendente (posición en
carrera = índice en `order`; inicial: por cajón).

#### 2.4.4 Pensar (cada 4 ticks por caballo)
```
rank = posición en order[] (del tick anterior); rem = metros que faltan
tirón: si (t & 31) == i y rng_next() < 4 + ((100-TEM) >> 2) + MISMATCH[|estilo - táctica|]: tirón = 32
       MISMATCH = 0 / 12 / 30: forzar a un puntero a esperar le pone nervioso
esfuerzo:
  pos < 200 m:              eff = START_EFF[táctica]
  rem <= sprint_at:         eff = E3, salvo jinete >= 5 y ene < rem*20 y rem > 150: eff = E1 (espera)
  puntero:                  eff = E1 si rank <= 1, si no E2 (pelea por ir delante)
  acecho:                   eff = E1
  cerrador:                 eff = E0
al pasar a E3 la primera vez: reserva = ene >> 7 (lo ahorrado se convierte en remate)
target = vmax - (((vmax >> 4) * DPCT[eff]) >> 4)      DPCT = 10 / 6 / 3 / 0, cansado (ene == 0): 32
si eff == E3 y ene > 0: target += kick + reserva
calles (con order[]): busca hacia delante el primer caballo en mi calle a <= 2 LEN
  -> cubierto = sí; si está a <= 1 LEN es "delante"
  si hay "delante" y target > su spd:
      en turno de calle ((t & 7) == (i & 7)) y calle exterior libre: lane++ (busca hueco por fuera)
      si no: block = ese caballo (encerrado)
  si no, en turno de calle, si lane > 0 y la calle interior está libre: lane-- (busca el palo),
      salvo en la recta final si no es puntero y ya esprinta (los cerradores atacan por fuera)
  calle libre = ningún caballo en ella con pos en (mi pos - 19, mi pos + 38)
```
Esto produce sin reglas especiales: el **sesgo del cajón** (los de fuera recorren más metros en la
primera curva o se meten detrás), el **duelo de punteros** (dos punteros a E2 se funden), los cerradores
**sin hueco** en la recta y los **tirones** de los caballos nerviosos.

#### 2.4.5 Llegada y resultados
- Orden: por tick de llegada, empate por mayor exceso sobre la meta (y por hueco si persiste).
- Tiempo del ganador = tick x 4 centésimas ("1:10.52").
- Margen con el anterior: al tick en que cruza el anterior se guarda la distancia que le falta a cada
  uno (`gap`, 1/16 m). Texto: `gap < 3` "nariz", `< 8` "cabeza", `< 16` "cuello", si no cuartos de cuerpo
  `q = (gap * 27) >> 8` → "1/2", "3/4", "1 1/4"... ; `q >= 40` → "10+".
- Límite de seguridad: 8000 ticks.

#### 2.4.6 Jinetes (`jockeys.tbl`, M1)
| Id | Nombre | Hab. | Monta k$ | Descargo lb | Fama mín. |
|---|---|---|---|---|---|
| NG | Ng (aprendiz) | 2 | 2 | 7 | 0 |
| LAU | Lau | 4 | 4 | 0 | 0 |
| KWOK | Kwok | 5 | 6 | 0 | 10 |
| SILVA | Silva | 7 | 10 | 0 | 40 |
| MOREAU | Moreau | 9 | 20 | 0 | 120 |
Habilidad: +2 de `vmax` por punto, menos salidas malas, y desde 5 sabe esperar el sprint si no le queda
energía. El aprendiz descarga 7 lb: útil en hándicaps con peso alto.

#### 2.4.7 Calibración actual (prototipo, 90 carreras por recorrido, rivales de clase 4)
| Recorrido | Tiempo ganador | Victorias por tercio de rating (bajo/medio/alto) | Por tercio de cajón (dentro/medio/fuera) | Índice táctica P/A/C |
|---|---|---|---|---|
| HV 1200 | 1:10.28 | 25 / 28 / 37 | 56 / 21 / 13 | 46 / 116 / 134 |
| HV 1650 | 1:36.80 | 22 / 29 / 39 | 26 / 36 / 28 | 98 / 122 / 79 |
| ST 1200 | 1:10.08 | 24 / 27 / 39 | 37 / 29 / 24 | 56 / 118 / 127 |
| ST 1600 | 1:33.88 | 24 / 27 / 39 | 45 / 31 / 14 | 84 / 129 / 87 |
| ST 2400 | 2:20.60 | 34 / 31 / 25 | 36 / 38 / 16 | 102 / 160 / 40 |
(Cajones sorteados con Fisher-Yates; el prototipo consume el RNG en el mismo orden que §2.9.)
Índice táctica = % de victorias x N / % de participantes (100 = neutral). Sensibilidad: un caballo con
+5 en VEL, RES y REM sobre lo que dice su rating gana el 44 % (con +10: 64 %): el entrenamiento se nota
enseguida y el hándicap lo corrige subiendo el rating. Objetivos de ajuste en §11 (los punteros están flojos: palancas `PUNT_RANK`,
`START_EFF`, `COST[E2]`).

### 2.5 Entrenamiento (`training.tbl`)
| Id | Nombre | VEL | RES | REM | TEM | Fatiga | Riesgo /256 |
|---|---|---|---|---|---|---|---|
| DESCANSO | Descanso | 0 | 0 | 0 | 0 | -15 | 0 |
| GALOPE | Galope | 6 | 6 | 4 | 0 | +12 | 2 |
| SERIES | Series | 16 | 0 | 8 | 0 | +25 | 6 |
| FONDO | Fondo | 0 | 16 | 0 | 0 | +20 | 3 |
| REMATES | Remates | 4 | 0 | 16 | 0 | +22 | 5 |
| SALIDAS | Salidas | 0 | 0 | 2 | 16 | +8 | 1 |
(Valores base en 1/16 de punto por semana.) Para cada atributo con base `b > 0`, en orden VEL RES REM TEM:
```
room = pot - actual                     (en puntos; si <= 0, no gana)
g = (b * min(room, 32)) >> 5
g = (g * EDAD[curva][min(edad,8)-2]) >> 2        EDAD (en cuartos), edades 2..8:
                                                 precoz 6 5 4 2 1 0 0 / normal 4 5 5 3 2 1 0 / tardío 2 4 5 5 3 2 1
si fat > 70: g >>= 1
si g > 0: g = max(0, g + rng_range(5) - 2)      (RNG: una llamada por atributo que gana)
actual16 += g, sin pasar de pot*16
```
Además, **crecimiento natural** de los caballos en cuadra de 2-4 años: VEL16 RES16 REM16 += `(4 * EDAD) >> 2`
cada semana (sin RNG), también en semanas de carrera. **Desentreno**: con 3+ semanas seguidas sin trabajo
(descanso o lesión), VEL16 RES16 REM16 -= 8 por semana (sin bajar de pot*8).
Al entrar en cuadra (2 años) los atributos actuales valen `pot * 10` (en 1/16: 62.5 % del potencial).

### 2.6 Rating (hándicap)
- Debut: rating 35. Tras cada carrera de hándicap, por puesto (`rating.tbl`):
  1º +6 (+1 por cuerpo entero de ventaja sobre el 2º a partir del segundo, máx. +4), 2º +2, 3º +1,
  4º-6º 0, 7º-8º -1, 9º-10º -2, 11º-14º -3; batido por más de 10 cuerpos: -1 más.
- Especiales: 1º +4, 2º +2, 3º +1, resto 0, últimos 3: -1. Rating entre 0 y 140.
- La clase se recalcula tras cada carrera (§2.3). M2 sustituye la tabla por cifras de actuación (§10).

### 2.7 Dinero y fama
- Dinero `money` s32 en miles de HK$ ("k"); empiezas con **800k**.
- Premios por puesto (k$, `races.tbl` columnas p1-p5; reparto 57/22/11.5/6/3.5 %):

| Clase | Bolsa | 1º | 2º | 3º | 4º | 5º | Fama 1º |
|---|---|---|---|---|---|---|---|
| C5 | 900 | 513 | 198 | 103 | 54 | 32 | 1 |
| C4 | 1150 | 655 | 253 | 132 | 69 | 40 | 2 |
| C3 | 1600 | 912 | 352 | 184 | 96 | 56 | 3 |
| C2 | 2300 | 1311 | 506 | 264 | 138 | 81 | 5 |
| C1 | 3200 | 1824 | 704 | 368 | 192 | 112 | 8 |
| G3 | 4000 | 2280 | 880 | 460 | 240 | 140 | 15 |
| G2 | 6000 | 3420 | 1320 | 690 | 360 | 210 | 25 |
| G1 | 13000 | 7410 | 2860 | 1495 | 780 | 455 | 40 |
| Copa Internacional | 30000 | 17100 | 6600 | 3450 | 1800 | 1050 | 80 |

- Cobras `premio - (premio >> 3)` (12.5 % para jinete y mozo) y pagas la monta del jinete siempre.
- Fama (u16): 1º la columna de la tabla, 2º la mitad, 3º un cuarto (redondeo hacia abajo). Abre jinetes
  y sementales (columna "fama mín.").
- Gastos semanales (paso 5): **20k por caballo en cuadra**, 3k por yegua o potro en la granja.
  Veterinario al lesionarse: 20k (leve), 60k (grave).
- Venta (ficha → Vender): `20 + 2*rating + 10*victorias` k (mitad desde 6 años).
- Números rojos: con dinero < 0 solo se permite Descanso. Tras 8 semanas seguidas en rojo, el banco
  vende tu caballo en cuadra de mayor rating y el contador vuelve a 0. Sin caballos en cuadra ni potros
  y en rojo: FIN ("La cuadra cierra").

### 2.8 Fatiga y lesiones
- Recuperación (paso 4, todos los caballos en cuadra): `fat -= 8 + (SAL >> 3)`.
- Entrenamiento: `fat += fatiga de training.tbl`. Carrera: `fat += 20 + dist100` al acabar.
  `fat` entre 0 y 100. Más de 80: el veterinario no deja correr.
- Lesión: tras cada entrenamiento con riesgo > 0 y tras cada carrera (riesgo 4), con la fatiga de antes:
  `p = riesgo + max(0, (fat-50) >> 1) + max(0, (60-SAL) >> 3)`; si `rng_next() < p`: lesión de
  `3 + rng_range(6)` semanas; y si `rng_next() < 32`, grave: `16 + rng_range(16)` semanas y pot VEL -3.
- Un caballo lesionado solo descansa; al llegar a 0 semanas vuelve con su fatiga actual.

### 2.9 Campo rival (`gen_field`)
Al resolver una carrera: los caballos del jugador ocupan los primeros huecos; el resto, por hueco
(RNG en este orden): `rating = lo + rng_range(hi - lo + 1)` (rangos: C5 10-40, C4 40-60, C3 60-80,
C2 80-100, C1 100-120, G3 75-100, G2 85-110, G1 95-120, Copa Internacional 110-125), y luego:
```
base = 20 + (rating >> 1)
VEL = clamp(base + rng_range(17) - 8, 1, 99)
RES = clamp(base + rng_range(17) - 8 + (dist100 - 14) * 3, 1, 99)
REM = clamp(base + rng_range(17) - 8, 1, 99)
TEM = 30 + rng_range(51);  dpref = clamp(dist100 + rng_range(5) - 2, 10, 24)
fat = rng_range(30);  jinete = rng_range(8);  estilo = rng_range(3);  táctica = estilo;  surf = rng_range(5) - 2
nombre = sustantivo rng_range(NS) + adjetivo rng_range(NA)
```
Después, cajones: Fisher-Yates (`for k = N-1..1: j = rng_range(k+1); swap`). En la Copa Internacional
los rivales llevan país "(JPN)", "(GB)", "(AUS)", "(FR)" (`rng_range(4)` tras el nombre).

### 2.10 Cría (M1 básica)
- Ventana de cubrición: semanas 23-36. En GRANJA eliges yegua (4-18 años, no preñada) y semental
  (`stallions.tbl`, con fama mínima). Concepción: `rng_next() < 192` (75 %); solo se paga la cuota si
  concibe. Se confirma en el parte de la semana siguiente; si falla, puedes repetir dentro de la ventana.
- Nacimiento en la semana 41 en un hueco de potro libre (si no hay, el potro se vende por 30k).
- **Herencia** (RNG en este orden): para VEL RES REM TEM SAL:
```
mid = (padre + madre + 1) >> 1
reg = mid + ((50 - mid) >> 3)                    regresión a la media (desplazamiento aritmético)
ruido = rng_range(17) - 8
si rng_next() < 8: ruido += rng_range(9)          "estrella" (3 %): salto hacia arriba
pot = clamp(reg + ruido, 10, 99)
```
  luego `dpref = clamp(((dp_p + dp_m + 1) >> 1) + rng_range(5) - 2, 10, 24)`,
  `surf = clamp(((s_p + s_m) >> 1) + rng_range(3) - 1, -3, 3)`,
  estilo = del padre si `rng_next() < 128` si no de la madre, y si `rng_next() < 32`: `rng_range(3)`;
  curva = del padre si `rng_next() < 128`, si no de la madre; sexo = `rng_next() & 1` (1 = hembra);
  nombre (2 llamadas).
- Edad 0 al nacer, 1 en la temporada siguiente (granja), 2 la otra: entra en cuadra si hay box libre
  (si no, espera en la granja sin entrenar).
- El gancho: la regresión (1/8 hacia 50) y el ruido ±8 hacen que superar a los padres pida elegir bien
  semental y yegua durante varias generaciones. Objetivo de bot en §11.

**Sementales (M1, `stallions.tbl`)**
| Id | Nombre | VEL RES REM TEM SAL | dpref | surf | estilo | curva | Cuota k$ | Fama |
|---|---|---|---|---|---|---|---|---|
| TRUENO | Trueno Lento | 60 35 55 50 60 | 11 | +1 | puntero | precoz | 50 | 0 |
| PUERTO | Rey del Puerto | 65 60 55 60 65 | 16 | 0 | acecho | normal | 150 | 0 |
| JADE | Dragon de Jade | 75 70 70 45 60 | 18 | +2 | cerrador | tardío | 600 | 60 |
| SEDA | Seda Imperial | 85 80 80 65 75 | 20 | +1 | acecho | normal | 2000 | 200 |

### 2.11 Edad, retiro y cambio de temporada (semana 44 → 1)
Por hueco: `edad++`; desde 7 años: pot VEL y REM -= 3*(edad-6), pot RES -= 2*(edad-6) (actuales
recortados al potencial); 9 años: retiro obligado. Retirar (ficha, o forzado): hembra → yegua en la
granja si hay hueco (si no, venta); macho → venta (precio de §2.7). Yeguas de 19: dejan la cría
(se quitan con un mensaje). Potros: 0 → 1 → 2 (a cuadra si hay box).

### 2.12 Carreras especiales (M1: dos)
| Semana | Nombre | Pista | Dist. | Tipo | Rating mín. |
|---|---|---|---|---|---|
| 6 | Premio Linterna (fiesta de medio otoño) | HV noche | 1650 | G3 | 70 |
| 15 | **Copa Internacional** (diciembre) | ST césped | 2000 | Internacional | 100 |
M2 añade el resto (§10). La Copa Internacional es la meta del juego: al ganarla, pantalla de victoria
y se sigue jugando.

### 2.13 Datos (`res/data/*.tbl`, `harness/tables.py`)
`rules.tbl` (constantes de §2.4-2.8 en filas id/valor), `courses.tbl` (tramos), `races.tbl` (clases y
especiales: pista, distancia, superficie, banda, rangos rivales, p1-p5, fama), `meetings.tbl` (plantillas
de 4 carreras), `calendar.tbl` (44 filas: mes, plantilla HV, plantilla ST, especial), `training.tbl`,
`jockeys.tbl`, `stallions.tbl`, `start.tbl` (caballos iniciales), `names.tbl` (32 sustantivos + 32
adjetivos invariables de género, sin acentos: "Oro", "Viento", "Perla", "Jade", "Loto", "Tifon",
"Grulla"... + "Feliz", "Lunar", "Veloz", "Sesenta", "Ocho", "Imperial", "Fugaz", "Leal"...; nombre de
14 caracteres máx.), `comment.tbl` (frases de comentario con `{N}`).

**Partida inicial (`start.tbl`, fija):**
| Nombre | Sexo/edad | VEL RES REM TEM SAL (actual) | Potencial | dpref | Estilo | Rating |
|---|---|---|---|---|---|---|
| Oro Sesenta | macho 3 | 38 32 36 55 60 | 58 50 55 60 60 | 12 | puntero | 30 |
| Viento Feliz | macho 3 | 34 38 30 45 55 | 50 62 48 55 55 | 16 | acecho | 25 |
| Perla Lunar | hembra 2 | 30 28 32 60 65 | 64 56 62 65 65 | 14 | cerrador | 35 (sin correr) |
| Brisa Dorada | yegua 8 | (yegua) | 58 62 50 55 60 | 16 | cerrador | - |

---

## 3. Controles

| Botón | Menús / gestión | Carrera |
|---|---|---|
| Cruceta arriba/abajo | mover cursor (repetición 16/6 f, gbe_menu/gbe_list) | - |
| Cruceta izq./der. | cambiar valor (plan, jinete, táctica) / página de la ficha | - |
| A | confirmar | cambiar cámara: mi caballo ↔ el líder |
| B | volver | mantener 30 f: "Saltar al resultado" (pide confirmación) |
| Start | en ESTABLO: "Avanzar semana" (con confirmación) | pausa |
| Select | en FICHA: siguiente caballo | - |
Título: Select + Start = menú de depuración de M1 (saltar a semana N, +1000k), quitar en M3.

---

## 4. Pantallas y flujo

```
TITULO -(Nueva/Continuar)-> ESTABLO
ESTABLO -> CABALLOS (gbe_list) -> FICHA (2 páginas; plan, retirar, vender)
        -> CARRERAS (carta de miércoles y domingo) -> INSCRIBIR (caballo -> jinete -> táctica)
        -> GRANJA (yeguas, potros) -> CUBRIR (semental)
        -> AVANZAR -> [por carrera tuya: PRESENTACION -> CARRERA -> RESULTADO] -> INFORME -> ESTABLO
        -> GUARDAR
RESULTADO (Copa Internacional ganada) -> VICTORIA -> INFORME
INFORME (sin caballos y en rojo) -> FIN -> TITULO
```
Maquetas aproximadas (el ui-designer las rehace): `design/screens/carrera.screen`,
`design/screens/establo.screen`. Transiciones: fundido a **blanco** (gbe_screen) para que los frames
con el LCD apagado (dibujo del texto proporcional) no destellen.

| Pantalla | Contenido |
|---|---|
| TITULO | logo de texto, "Nueva partida" / "Continuar" (si hay guardado) |
| ESTABLO | fila 0 fecha ("Sep sem 2  Temp 1"), fila 1 dinero y fama, filas 3-10 lista de caballos (2 filas: nombre + clase/rating; fatiga + plan), filas 12-17 menú |
| FICHA p1 | nombre, sexo, edad, rating/clase, VEL RES REM TEM SAL (número + barra de 8 tiles), estrellas, fatiga, lesión, plan |
| FICHA p2 | distancia ideal, superficie, estilo, récord (carreras/victorias/colocado), ganancias, padre/madre, última carrera |
| CARRERAS | lista de las 8 carreras de la semana (día, pista, clase, distancia, bolsa) con tu inscrito al lado |
| PRESENTACION | 1 fila por corredor: dorsal, cajón, nombre, peso, rating; tus caballos con flecha |
| CARRERA | §5.1 |
| RESULTADO | fila 0 carrera; filas 1-14 puesto, dorsal, nombre, margen; filas 15-17 tiempo, premio, rating antes>después |
| INFORME | parte de Ah Fat: líneas por caballo (+VEL 1, lesión, fatiga), dinero de la semana, nacimientos |
| GRANJA | yeguas (preñada de...), potros (edad, estrellas) |

## 5. HUD e interfaz

### 5.1 Pantalla de carrera
- **BG filas 0-14** (desplazamiento horizontal con SCX): fila 0 = palos interiores (WALL x4 / GRAY x4,
  periodo 64 px: se nota el movimiento); filas 1-14 = césped (FLOOR); una fila de 8 px por corredor.
  El mapa de 32 columnas es periódico, así que no hay que cargar columnas: solo los **postes** (800,
  600, 400, 200 m: columna de DOOR; meta: columna de CHECK; cajones de salida: columna de BOX) se
  escriben con `gbe_vq` (15 tiles) cuando entran por la derecha y se borran al salir por la izquierda.
- **Ventana** (WY = 120, filas 15-17): fila 15 HUD con dígitos de `font_mini` monoespaciados ("400m
  0:52.40  3/12": metros que faltan, tiempo, puesto de tu caballo); filas 16-17 comentario (2 líneas
  proporcionales, máquina de escribir 1 letra/frame).
- Escala: **1 px = 0.5 m** (`x = pos >> 3`): un cuerpo ≈ 5 px; un campo de 15-20 cuerpos cabe casi
  entero en los 160 px. Cámara: `c = foco - 72`; si el líder queda a > 144 px de `c`,
  `c = min(lider - 144, foco - 16)`; la cámara se mueve hacia `c` a ≤ 3 px/frame. Foco = tu caballo
  mejor colocado (A: el líder).
- Filas: cada 8 frames, clave `lane*16 + cajón` ordenada → fila de cada caballo (`y = 8 + 8*fila`);
  la y real se acerca 1 px/frame (los cambios de calle se ven como subir/bajar). Calle 0 (palo) arriba.
- Caballo (greybox): sprite BOX + dígito(s) del dorsal (`font_mini` copiado a tiles de sprite);
  10-14 llevan 2 dígitos (3 sprites). Tus caballos con OBP1 invertida (caja negra).
- Antes de salir: 60 frames con los caballos en los cajones; campana (SFX) y tick 0. Tras cruzar tu
  último caballo, 60 frames más (los llegados siguen visualmente frenando 8/tick, fuera del modelo).
- Comentario (`comment.tbl`, prioridad, mínimo 90 frames en pantalla salvo prioridad mayor), mirado
  cada 16 frames: salida, salida mala de un caballo tuyo, nuevo líder (estable 32 ticks), entrada en
  curva, entrada en la recta, tu caballo encerrado ≥ 16 ticks ("{N} no encuentra hueco"), ataque por
  fuera (E3 con calle ≥ 2), líder cansado ("{N} se queda"), quedan 400 m, ganador y margen.
  El texto con el nombre se parte en 2 líneas en tiempo de ejecución con `vwf_width` palabra a palabra.

### 5.2 Menús
- Texto proporcional `font_mini` (gbe_vwf), mayúscula inicial, sin acentos ni eñe ("espera un potro").
  Números que cambian (dinero, fatiga, stats) con dígitos monoespaciados de `font_mini` en VRAM (baratos).
- Cursor ARROW_R de greybox; barras de atributo con GRAY/SOLID (8 tiles = 0-99 en pasos de ~12).
- Pantallas con mucho texto (FICHA, PRESENTACION, RESULTADO): se dibujan con el LCD apagado en
  `screen_build` (unos 200-300k T: 3-4 frames en blanco dentro del fundido a blanco, `skip_measure`).

---

## 6. Progresión y dificultad

| Etapa | Qué pasa | Meta del jugador |
|---|---|---|
| Temporada 1 | 3 caballos C5, 800k, jinetes baratos | ganar en C5, subir uno a C4-C3, no lesionar |
| Temporada 2 | primer potro propio (de Brisa Dorada), fama abre Kwok/Silva y Dragon de Jade | C2-C1, Premio Linterna |
| Temporadas 3-5 | segunda generación, Seda Imperial | caballo de rating 110+, Copa Internacional |
La dificultad no cambia con el tiempo: la ponen los rangos de rating de los rivales por clase (tablas)
y la Copa Internacional (110-125). Clásico de GB pero amable: nada castiga sin aviso (Ah Fat avisa de
fatiga > 60 y de caballos fuera de su distancia).

---

## 7. Contenido y assets (M1 greybox)

| Asset | Tipo | Tiles | Notas |
|---|---|---|---|
| greybox | BG + sprite | 13 | `harness/common/greybox.tiles` |
| font_mini | BG (+ 10 dígitos en sprite) | 42 | dígitos y mayúsculas monoespaciados (HUD, números) |
| texto proporcional | BG, slot reservado | 200 | `font_mini` + `font_mini_lower` + `font_mini_es` vía gbe_vwf (no hace falta cargarlas en VRAM) |
**Totales:** BG 13 + 42 + 200 = **255/256**; sprites 13 + 10 = 23 tiles; sprites en pantalla peor caso
14 caballos: 9 x 2 + 5 x 3 = **33/40**; **sprites por línea peor caso: 6/10** (filas únicas de 8 px: como
mucho 2 caballos solapan una línea durante un cambio de fila, 3 sprites cada uno).
M3 (arte): caballo 16x16 al galope 4 frames (16 tiles de sprite, 8x16), pista (palos, césped, horizonte
de Happy Valley de noche / tribunas de Sha Tin, ~40 tiles) compartiendo hueco con el título
(`vram_order` en lista), marcos de UI ~20 tiles: el slot de texto baja a 150.

### 7.1 Hogares de VRAM (→ game.json)
LCDC.4 = 0 (fondo en $8800): fondo 0-255, sprites 0-127 propios (no se tocan los compartidos).
```
"vram_order": ["greybox", "font_mini", {"text": 200}],
"vwf": {"fonts": ["font_mini", "font_mini_lower", "font_mini_es"], "slot": "text"},
"vram_scenes": {
  "menu": { "spr": [[0, "greybox"]] },
  "race": { "spr": [[0, "greybox"], [16, "font_mini", 0, 10]] }
}
```
Slot de texto por escena (offset `text:` de cada maqueta): menús 0-199 (cada pantalla reparte texto fijo
+ dinámico, ≤ 200); carrera: HUD 0-15, comentario 2 x 19 = 38 tiles en 16-53. Nadie más escribe en el
slot; al cambiar de escena `screen_build` lo rellena entero.

---

## 8. Sonido
M1: solo SFX con `gbe_sfx` (cursor, confirmar, volver, campana de salida, ganador, lesión). Sin música
(el motor no tiene reproductor: riesgo R5, M3).

---

## 9. Técnica

- **Cartucho:** MBC5 + RAM + batería, 128 KB: `["-autobank", "-Wm-yt0x1B", "-Wm-yo8", "-Wm-ya1"]`,
  `GBE_BANKED`. Banco 0 (~11 KB estimado): gbe caliente (frame, oam, video, vq, tiles, bank), simulación
  y dibujo de la carrera, bucle principal. En bancos: menús y pantallas, semana (entrenamiento,
  lesiones, calendario), cría, campo rival, comentario, guardado, tablas, fuentes, maquetas.
- **Módulos gbe usados:** gbe_frame, gbe_oam, gbe_video (sombras SCX y paletas, fundidos), gbe_screen,
  gbe_sfx, gbe_bank, gbe_save (por trozos), gbe_rng, gbe_vq, gbe_tiles, gbe_vwf, gbe_menu, gbe_list,
  gbe_text (dígitos), gbe_selftest. **No** se usan gbe_map/gbe_world/gbe_actors.
- **Trabajo nuevo** (del juego, no del motor): escena de carrera (SCX periódico + columnas de postes por
  gbe_vq, ventana inferior con WY), partir texto en líneas con `vwf_width` (candidato a `vwf_wrap` en
  gbe_vwf), formato de u32 con puntos de miles, modelo de carrera en C (+ asm si hace falta, R1).
- **Guardado** (`save_begin/put`, versión 1): estado 32 B (semana, temporada, dinero s32, fama, rng_state,
  semanas en rojo, flags) + 12 caballos x 50 B + registro de pedigrí 32 x 16 B ≈ **1.15 KB** (cabe
  dos veces en 8 KB de SRAM).
  - Caballo (50 B): flags (usado, sexo, estado: cuadra/yegua/potro/retirado), nombre[14], edad,
    vel16/res16/rem16 (u16), tem, sal, pot[5], dpref, surf (s8), estilo, curva, rating, fat, lesión,
    inactivo, carreras, victorias, colocados, ganancias (u16 k$, satura), padre, madre, registro, plan,
    inscripción, jinete, táctica, último puesto, preñez (semental o 0xFF).
  - Huecos M1: 6 boxes de cuadra (4 abiertos al empezar), 3 yeguas, 3 potros.
- **WRAM:** caballos 600 + registro 512 + carrera (14 x ~30 = 420) + campo rival (14 x 40 = 560) +
  tira vwf 320 + colas ≈ 2.7 KB.
- **CPU de la carrera (peor frame, 14 caballos, estimado con budgets.md):** mover + energía 14 x ~900 T
  = 12.6k; pensar 3.5 caballos x ~2.5k = 9k; ordenar 1.7k; dibujar 33 sprites x ~300 = 10k; cámara,
  postes y HUD 2k; vwf 1 letra 2.5k; frame 2k → **~40k T ≈ 88 líneas** (objetivo < 100). Si al medir
  pasa de 90: `race_move` en asm (como `act_move`, ~250 T por caballo: -8k).
- **Saltar al resultado:** simula sin dibujar con el LCD encendido y una barra de progreso,
  todos los ticks que quepan en 60 000 T por frame (C: ~3/frame → 2400 m en 20 s; con asm ~5/frame
  → 12 s), `skip_measure`.
- **Menús:** coste despreciable salvo el dibujo con LCD apagado (§5.2).
- `harness/physics.py` no aplica (no hay saltos); el equivalente es `race_proto.py` → `tests/hv_model.py`.

---

## 10. Hitos

- **M1 greybox jugable** (el usuario lo prueba al final), en dos pasos:
  - **M1a carrera:** modelo de carrera en ROM == `tests/hv_model.py` (posiciones en ticks 300/600,
    llegadas exactas), escena de carrera con scroll, postes, filas, cámara, comentario, HUD, pausa,
    saltar; PRESENTACION y RESULTADO; menú de depuración que lanza una carrera con caballos fijos.
  - **M1b gestión:** TITULO, ESTABLO, CABALLOS/FICHA, plan semanal (6 entrenamientos), CARRERAS e
    INSCRIBIR (jinete, táctica), calendario de 44 semanas con 2 plantillas por pista y las 2 carreras
    especiales, premios, rating y clases, fatiga y lesiones, gastos y números rojos, envejecer y
    retirar, GRANJA con cubrición, nacimiento y herencia, INFORME, guardado. Bots del modelo (§11).
- **M2 profundidad:** calendario completo (Copa de Oro, Derby de 4 años, Milla de Campeones, Copa del
  Fundador, Gran Final de HV, Copa de Año Nuevo), arena de Sha Tin en todas las plantillas, subasta de
  potros de 1 año, instalaciones (piscina: entrenamiento de fondo sin riesgo; caminadora; boxes
  extra), sementales propios con ingresos por cubriciones, consanguinidad (ancestro común en 2
  generaciones: SAL -5 y ruido x2) y "nicks" entre líneas, hándicap con cifras de actuación,
  ensayos de salida (barrier trials) antes del debut, castrar (TEM +10, no cría), jinetes extranjeros
  de temporada, rival (Cuadra Imperial del señor Ko), nombre del caballo a elegir, estadísticas de
  cajón por recorrido en la carta (el jugador aprende el sesgo).
- **M3 arte, UI y sonido:** sprites de caballo con dorsal y galope, pistas de noche/día, título, marcos,
  fuente/UI del ui-designer, música (reproductor nuevo), fotofinish, fuegos en la Copa Internacional.
- **M4 hardware real** (flash cart): tiempos de LCD apagado, guardado con corte de corriente.

---

## 11. Plan de pruebas

| Qué | Cómo |
|---|---|
| Carrera ROM == modelo | test: campo fijo + `rng_state` fijo → `pos`, `spd`, `ene`, `lane` de los 14 en los ticks 1, 50, 300, 600 y el orden/ticks de llegada iguales a `hv_model.run`; 20 semillas |
| Saltar == ver | la misma carrera saltada y vista da el mismo resultado y `rng_state` |
| Campo rival | `gen_field` ROM == modelo (ratings, stats, cajones, nombres) |
| Semana | estado guardado + planes + semilla → tras "Avanzar" (carreras saltadas) atributos, fatiga, lesiones, dinero, rating, `rng_state` == modelo; 100 semanas seguidas |
| Herencia | 50 cruces ROM == modelo (pot, dpref, surf, estilo, curva, sexo) |
| Reglas | inscripción rechaza lesionado, fat > 80, clase baja; peso y dorsales; números rojos → venta en la semana 8 |
| Guardado | apagar/encender con SRAM (`gb.power_off()`), corrupción de un byte → slot anterior |
| Rendimiento | bot que mira 5 carreras completas de 14 caballos (HV y ST 2400): `max_frame_lines < 100`, `vram_late == 0`; `gb.worst_frames` en la peor |
| Pantallas | `gb.vram_errors("race"/"menu")`, `gb.mockup_errors` en ESTABLO y CARRERA, texto leído con `gb.vwf_text` |
| Sprites por línea | en cada frame de una carrera, ninguna línea con > 10 sprites (contar desde OAM) |
| **Equilibrio (bots del modelo, Python)** | ver objetivos abajo |
| Feel, ritmo, ganas de "una semana más" | playtest humano (usuario) tras M1b |

**Objetivos de equilibrio** (bots de `hv_model` sobre 200+ carreras o 10 temporadas; el playtester
los usa para proponer cambios en las tablas):
- Tiempos del ganador (clase 4): HV 1200 1:09.5-1:10.8, ST 1600 1:33.5-1:35.0, ST 2000 1:59.5-2:02.0.
- HV 1200: tercio interior de cajones 45-60 % de victorias; ST 1200-1400: 36-45 %.
- Índice de cada táctica entre 70 y 140 en la media de recorridos (hoy los punteros 44-80: ajustar).
- Dentro de una banda, el tercio de rating alto gana ≤ 1.5 veces lo que el bajo (el hándicap iguala).
- Bot "medio" (rota Galope/Series/Fondo, corre cada 3 semanas en su clase, descansa con fat > 50):
  acaba la temporada 1 con 300-1500k y una lesión como mucho por caballo cada 25 semanas.
- Bot "novato" (siempre Series, corre cada semana): ≥ 1 lesión en la temporada, dinero menor que el
  medio, pero no llega al FIN antes de la semana 30.
- Bot "experto": un caballo a C3 en la temporada 1 y un especial ganado antes de la temporada 4.
- Cría: con el mejor semental asequible cada año, la media de potencial de la generación 3 supera a la
  1 en ≥ 10 puntos; sin elegir (semental al azar) no sube.

---

## 12. Decisiones (2026-10-15)
- [x] **Vista de la carrera: lateral + mini-óvalo en el HUD** (elegida por el usuario). M1: la lateral
  con una fila por corredor; el mini-óvalo con la posición del líder y la tuya entra en M2 (+~10 tiles
  y 2 sprites) y se reserva su hueco en el HUD desde M1.
- [x] **Ritmo: x2.4** de la realidad (1200 m ≈ 30 s) y saltar con B (estudio, con la recomendación).
- [x] **Temporada: 44 semanas**, un turno por semana, con menú de depuración para saltar semanas en
  las pruebas (estudio, con la recomendación).
