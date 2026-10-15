# HAPPY VALLEY — Documento de diseño

Estado: v1.1 en revisión (v1.0 aprobada)    Versión: 1.1 (2026-10-15)    Carpeta: `games/happyvalley`

> Gestión de una cuadra de carreras de caballos en una ciudad al estilo de Hong Kong, a lo *Derby Stallion*.
> Regla del estudio: **primero greybox** (cuadrados de `harness/common/greybox.tiles` + `font_mini`)
> para validar toda la lógica; el arte llega en M3, cuando el usuario haya jugado M1.
> Tema, nombres, textos y dificultad los decide el diseñador. Lo caro de cambiar está en §12.
> Especificación ejecutable de la carrera: `design/race_proto.py` → `tests/hv_model.py` (enteros y el
> mismo xorshift que `gbe_rng`). Si este documento y el modelo discrepan en la carrera, manda el modelo
> y se corrige el GDD.

**Cambios v1.1** (decisiones del usuario): (1) **pistas como datos** (§2.4.1, §2.13): hipódromos
ficticios con sabor de Hong Kong, el código no conoce ninguna pista; (2) **cámara lateral inclinada
tipo TV** con tribunas, ciudad, parallax, curvas por raster y minimapa (§5.1, §7, §9): sustituye a la
vista cenital implementada; (3) **mercado de jinetes y de caballos** (§2.14, §2.15, hitos §10).
Afecta a §1, 2.2, 2.4, 2.7, 2.12, 2.13, 3, 4, 5.1, 7, 9, 10, 11, 12, 13.

---

## 1. Pitch

- **Género:** gestión de cuadra + crianza, por turnos semanales, con carreras simuladas que se ven.
- **Fantasía:** heredas la cuadra pequeña de tu tío en Pak Shan: tres caballos, una yegua vieja en la
  última granja de la isla y 800k en la cuenta. Entrenas semana a semana, contratas jinetes, compras y
  vendes caballos, miras la carrera bajo los focos de **Valle Linterna** y, generación tras generación,
  crías al caballo que gane la **Copa Internacional** de diciembre.
- **Bucle principal:** planifica la semana (entrenar / descansar / inscribir, jinetes, mercado) → mira
  tus carreras → cobra, sube de rating y de clase → cruza a tus yeguas → la siguiente generación es mejor.
- **Qué lo hace distinto:** hipódromos que se juegan distinto, todos definidos como datos.
  **Valle Linterna** (miércoles por la noche, en mitad de la ciudad): óvalo pequeño de curvas cerradas,
  el **cajón de salida pesa mucho**. **Pak Shan** (domingos): óvalo grande de césped con arena por dentro
  y una recta de 1200 m, las grandes copas. En M2, reuniones de provincia en **Fung Wan** (a izquierdas,
  campo) y **Bahia Ming** (medio óvalo junto al puerto). Hándicap al estilo de Hong Kong (clases 5 → 1,
  rating que se mueve con los resultados, peso según rating). "HAPPY VALLEY" es la marca y el ambiente de
  la ciudad; los recintos son ficticios (sin nombres del Hong Kong Jockey Club).
- **Sesión:** una semana de juego = 20 s - 2 min. Una temporada (44 semanas) ≈ 40-60 min. Guardado
  automático cada semana: se deja en cualquier momento.
- **Referencias:** *Derby Stallion* (SFC/GB: semanas, cruces, carrera vista de lado); la realización de
  TV de las carreras nocturnas de Hong Kong (cámara que acompaña al pelotón, tribunas y rascacielos
  detrás); *Winning Post* (economía, sementales con cuota, subastas). Estudio: `games/dungeon` (menús,
  bancos, guardado), `games/mazmorra` (`font_mini` + `gbe_vwf`), `games/faro` (tablas `.tbl` y modelo
  Python espejo; y su lección de alcance), `games/shmup` (parallax y grupos de OAM).

### Historia y tono
Tu tío Lam entrenó 30 años en Pak Shan sin ganar nunca la Copa Internacional. Te deja la cuadra con
una nota: "La yegua es mejor de lo que parece". Textos breves y cálidos, con humor de hipódromo
(el mozo de cuadra **Ah Fat** da los consejos y los partes semanales). Dificultad objetivo: amable al
principio (nada te arruina en la temporada 1 si no maltratas a los caballos), profunda a largo plazo
(ganar la Copa Internacional pide 3-5 temporadas y caballos criados o comprados con buen ojo).

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
- **Estrellas de potencial** (ficha, tras 4 semanas en la cuadra; en el mercado, al momento): media de
  los potenciales de VEL RES REM: < 40 = 1, < 55 = 2, < 70 = 3, < 85 = 4, si no 5. Yeguas y sementales
  muestran sus potenciales como números (ya están hechos).
- Edad: sube en la semana 1 de cada temporada. Corre de 2 a 8 años; retiro obligado al cumplir 9.

### 2.2 Calendario y semana

- **Temporada = 44 semanas.** Semanas 1-40: carreras (septiembre → mediados de julio). Semanas 41-44:
  **verano** (sin carreras; nacen los potros en la 41). En la semana 44 → semana 1 de la temporada
  siguiente (envejecer, §2.11). Mes de cada semana en `calendar.tbl` ("Sep sem 2").
- Cada semana de carreras: **miércoles noche en Valle Linterna** (4 carreras) y **domingo en Pak Shan**
  (4 carreras, una puede ser especial). Las cartas salen de plantillas (`meetings.tbl`, cada carrera =
  un recorrido de `courses.tbl` + clase), y `calendar.tbl` dice qué plantilla y qué especial toca cada
  semana. M2: **sábado de provincia** cada 2 semanas (Fung Wan y Bahia Ming alternos, 3 carreras): una
  columna más en `calendar.tbl` y un paso más en la resolución, entre el 2 y el 3.
- Un caballo corre como mucho una vez por semana. Plan de cada caballo para la semana: un
  entrenamiento (§2.5) o una inscripción (§2.3). Por defecto se repite el plan anterior.

**Orden de resolución al pulsar "Avanzar semana"** (el modelo Python lo sigue igual):
1. Carreras del miércoles con inscripciones tuyas, por orden de carta: generar campo (§2.9) →
   presentación → carrera (§2.4) → resultado (premio §2.7, rating §2.6, fatiga y lesión de carrera §2.8).
2. Entrenamiento de cada caballo en cuadra sin carrera esta semana, por orden de hueco (§2.5, §2.8).
3. Carreras del domingo, igual que el paso 1.
4. Para todos los caballos en cuadra, por hueco: recuperación de fatiga (§2.8), cuenta atrás de lesión,
   contador de inactividad.
5. Gastos semanales (§2.7: boxes, granja, **sueldos de jinetes** §2.14), deudas; contratos de jinete −1 semana.
6. `week++`; eventos: confirmación de preñez (§2.10), nacimientos (semana 41), cambio de temporada,
   **disponibilidad de jinetes** de la semana nueva (§2.14), **ofertas del mercado** si toca (§2.15).
7. Parte semanal (pantalla INFORME) y **autoguardado**.
Las carreras sin caballos tuyos no se simulan (los rivales no persisten entre carreras).

### 2.3 Inscripción

- Requisitos: edad ≥ 2, sin lesión, `fat ≤ 80`, no inscrito ya esta semana, y clase permitida:
  carrera de su clase (rating dentro de la banda) o **una clase por encima** (sube con el peso mínimo).
  Carreras especiales: rating mínimo propio (§2.12).
- Bandas de clase (rating): C5 0-40, C4 40-60, C3 60-80, C2 80-100, C1 100-140. En el límite exacto
  (40, 60...) el caballo es de la clase superior.
- Se eligen: **jinete** (tus contratados libres o un jinete libre ese día por monta suelta, §2.14; un
  jinete monta una vez por carrera) y **táctica**: Puntero, Acecho, Cerrador. El cajón se sortea al
  generar el campo (después de inscribir).
- **Peso (lb)**: hándicap: `peso = clamp(133 - (techo_banda - rating), 113, 133) - descargo_jinete`.
  Especiales (peso por edad): 126 lb, hembras 122 lb (sin descargo).
- Número de dorsal: por peso descendente, empate por rating descendente, luego por hueco.

### 2.4 La carrera (modelo)

Unidades: posición `pos` en 1/16 m (u16, hasta 4095 m) + fracción u8; velocidad `spd` en 1/4096 m por
tick (u16; m/s = spd / 163.84). **1 tick = 1 frame = 0.04 s de carrera** (la tele va a x2.4: 1200 m
se ven en ~30 s, 2400 m en ~60 s). Tiempo mostrado = ticks x 4 centésimas. 1 cuerpo `LEN` = 38
(2.375 m). Tamaño del campo y número de calles: columnas `field` y `lanes` de la pista (§2.4.1).

#### 2.4.1 Pistas y recorridos como datos

El código (ROM, modelo Python, vista, minimapa) **no conoce ninguna pista concreta**: todo sale de cuatro
tablas. Añadir una pista o un recorrido = añadir filas y regenerar los minimapas con
`python games/happyvalley/design/gen_track.py` (lee las tablas; nada a mano).

**`venues.tbl`** — hipódromo (lo que ve la cámara):
```
@ col name    text 14
@ col hand    enum DER IZQ              ; DER = sentido horario: en pantalla de izquierda a derecha
@ col theme   enum CIUDAD PARQUE CAMPO PUERTO    ; juego de fondos (skyline, capa media)
@ col night   bool
@ col stand_a u16                       ; tribuna desde stand_a m antes del poste...
@ col stand_b u16                       ; ...hasta stand_b m después (recta de meta)
@ col crowd   u8                        ; 0-3 densidad de público (tiles animados)
;id  name             hand theme  night stand_a stand_b crowd
LIN  "Valle Linterna" DER  CIUDAD yes   260     40      3
PAK  "Pak Shan"       DER  PARQUE no    400     60      3
FUN  "Fung Wan"       IZQ  CAMPO  no    150     30      1
MIN  "Bahia Ming"     DER  PUERTO no    250     40      2
```
**`tracks.tbl`** — una superficie/trazado dentro de un hipódromo:
```
@ col venue  ref venues
@ col surf   enum CESPED ARENA
@ col closed bool                       ; óvalo cerrado (se puede dar más de una vuelta)
@ col lanes  u8                         ; calles: calle máx. = lanes - 1 (sustituye a RULE LANES_MAX)
@ col field  u8                         ; corredores máx.
@ col inner  bool                       ; dentro de otra pista (vista: franja de césped antes de la tribuna)
;id    venue surf   closed lanes field inner
LIN_T  LIN   CESPED yes    13    12    no
PAK_T  PAK   CESPED yes    14    14    no
PAK_A  PAK   ARENA  yes    14    14    yes
PAK_R  PAK   CESPED no     16    14    no
FUN_T  FUN   CESPED yes    14    12    no
FUN_R  FUN   ARENA  no     16    12    no
MIN_T  MIN   CESPED no     14    12    no
```
**`segs.tbl`** — tramos de cada pista en sentido de carrera, **empezando justo después del poste y
acabando en el poste** (orden de fichero). `ang` en 1/64 de vuelta (32 = 180°), `bk` factor de curva,
`chute` = metros de recta extra hacia atrás (salida en "manga", fuera del óvalo):
```
@ col track ref tracks
@ col kind  enum R C
@ col m     u16
@ col ang   u8
@ col bk    u8
@ col chute u16
;id     track kind m    ang bk chute
LIN1    LIN_T R    20   0   0  0
LIN2    LIN_T C    314  32  6  0
LIN3    LIN_T R    310  0   0  120
LIN4    LIN_T C    314  32  6  0
LIN5    LIN_T R    290  0   0  0
PAKT1   PAK_T R    130  0   0  0
PAKT2   PAK_T C    456  32  4  0
PAKT3   PAK_T R    560  0   0  0
PAKT4   PAK_T C    456  32  4  0
PAKT5   PAK_T R    430  0   0  0
PAKA1   PAK_A R    130  0   0  0
PAKA2   PAK_A C    346  32  5  0
PAKA3   PAK_A R    560  0   0  0
PAKA4   PAK_A C    346  32  5  0
PAKA5   PAK_A R    430  0   0  0
PAKR1   PAK_R R    1200 0   0  0
FUN1    FUN_T R    50   0   0  0
FUN2    FUN_T C    393  32  5  0
FUN3    FUN_T R    400  0   0  200
FUN4    FUN_T C    393  32  5  0
FUN5    FUN_T R    350  0   0  0
FUNR1   FUN_R R    1200 0   0  0
MIN1    MIN_T R    700  0   0  0
MIN2    MIN_T C    440  32  4  0
MIN3    MIN_T R    460  0   0  0
```
Reglas (lint en Python, `tests/test_tracks.py`): como mucho 6 tramos por pista; radio de curva
`r = m * 64 / (2π * ang)`; `bk = round(600 / r)` (≈ 1 calle = 1.17 m de radio extra: Linterna r 100 m →
6, Pak Shan césped r 145 → 4, arena r 110 → 5); en pistas cerradas la suma de `ang` es 64 y la figura
cierra (punto final == inicial ± 2 m); `chute` solo en rectas; un recorrido no pasa de la longitud de
una pista abierta y produce ≤ 8 tramos. La arena de Pak Shan comparte centros de curva y poste (x) con
el césped: queda 35 m por dentro.

**`courses.tbl`** — recorrido = pista + distancia (la salida queda `dist` m antes del poste):
```
@ col track ref tracks
@ col dist  u16
;id        track dist
LIN1000    LIN_T 1000   ...   (lista completa abajo)
```
**`course_build(track, dist)`** (C en `race_init`, una vez; Python idéntico en `hv_model`; test ROM ==
Python en los 27 recorridos): recorre los tramos **hacia atrás desde el poste**:
```
rem = dist; k = último tramo; out = []                     (out se llena por delante)
mientras rem > 0:
    s = seg[k]
    si s.kind == R y s.m < rem <= s.m + s.chute: take = rem   (la salida está en la manga)
    si no: take = min(rem, s.m)
    si out no vacío y out[0].bk == s.bk: out[0].m += take       (une rectas consecutivas)
    si no: insertar delante (take, s.bk, s.ang * take / s.m)
    rem -= take; k -= 1; si k < 0: k = último (pista cerrada; abierta = error de lint)
final_from = dist - out[último].m   (inicio de la recta final; 0 si hay un solo tramo)
```
El modelo solo usa `out[].m` y `out[].bk` (`bk = 0` = recta). La vista usa además el giro de cada tramo
(rotación del fondo, §5.1) y el minimapa usa la geometría de la pista entera.

**Recorridos por defecto** (salida de `course_build`; R = recta, C = curva/bk):

| Pista | Recorridos |
|---|---|
| LIN_T Valle Linterna, césped, noche, óvalo 1248 m, r 100 | 1000 R396(manga) C314/6 R290 · 1200 C286/6 R310 C314/6 R290 (sale en curva: el cajón decide) · 1650 C112/6 R310 C314/6 R310 C314/6 R290 · 1800 C262/6 R310 C314/6 R310 C314/6 R290 · 2200 R348(manga) C314/6 R310 C314/6 R310 C314/6 R290 |
| PAK_T Pak Shan césped, óvalo 2032 m, r 145 | 1200 R314 C456/4 R430 · 1400 R514 C456/4 R430 · 1600 C154/4 R560 C456/4 R430 · 1800 C354/4 R560 C456/4 R430 · 2000 R98 C456/4 R560 C456/4 R430 · 2400 R498 C456/4 R560 C456/4 R430 |
| PAK_A Pak Shan arena (interior), óvalo 1812 m, r 110 | 1200 R424 C346/5 R430 · 1650 C314/5 R560 C346/5 R430 · 1800 R118 C346/5 R560 C346/5 R430 |
| PAK_R Pak Shan recta de césped 1200 m | 1000 R1000 · 1200 R1200 |
| FUN_T Fung Wan césped, a izquierdas, óvalo 1586 m, r 125 (M2) | 1000 R257 C393/5 R350 · 1200 R457(manga) C393/5 R350 · 1400 C257/5 R400 C393/5 R350 · 1600 R64 C393/5 R400 C393/5 R350 · 2000 C64/5 R400 C393/5 R400 C393/5 R350 |
| FUN_R Fung Wan recta de arena 1200 m (M2) | 1000 R1000 · 1200 R1200 |
| MIN_T Bahia Ming medio óvalo, césped (M2) | 1000 R100 C440/4 R460 · 1200 R300 C440/4 R460 · 1400 R500 C440/4 R460 · 1600 R700 C440/4 R460 |

Ids: `LIN1000`, `PAK1200`, `PAKA1650`, `PAKR1000`, `FUN1400`, `FUNR1200`, `MIN1600`... (27). Las 7 pistas
están en los datos desde M1 (el test de "pista desconocida para el código" corre el modelo y
`course_build` en todas), pero el calendario de M1 solo usa LIN y PAK.

**Curva en el modelo**: en un tramo con `bk > 0`, un caballo a `lane` calles del palo avanza menos:
`prog = spd - (((spd >> 4) * (lane * bk)) >> 5)` (bk 6: −1.2 % por calle; 4: −0.8 %). Cambio respecto a
v1.0: `bk` es del tramo (antes uno por recorrido + máscara de curvas) y el tope de calle es
`tracks.lanes - 1` (antes `LANES_MAX`). Con los recorridos v1.0 el resultado es idéntico (mismo bk en
todas las curvas): los tests de igualdad ROM == modelo siguen sirviendo durante el cambio.

#### 2.4.2 Antes de la salida (una vez)
Para cada caballo `i` en orden de hueco del campo (RNG: forma, ruido de sprint, retraso):
```
apt  = surf (césped) o -surf (arena)                                  superficie de tracks.surf
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
`delay += 8 + rng_range(8)`. (`jinete` = habilidad 0-7, §2.14.)

#### 2.4.3 Cada tick `t` (desde 0), caballos en orden de hueco, saltando los que ya llegaron
```
si delay > 0: delay--, siguiente caballo
si (t & 3) == (i & 3): pensar(i)                     (§2.4.4: 1 de cada 4 caballos por tick)
spd -> target: si spd < target: spd = min(target, spd + (launch ? accL : acc))
               si no:           spd = max(target, spd - 4)
launch = 0 cuando spd >= vmax - vmax/8 (fin de la arrancada)
si block >= 0: spd = min(spd, spd[block])            (encerrado detrás de otro)
prog = spd (menos la pérdida de curva del tramo actual §2.4.1); pos:frac += prog
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
      en turno de calle ((t & 7) == (i & 7)) y lane < lanes-1 y calle exterior libre: lane++
      si no: block = ese caballo (encerrado)
  si no, en turno de calle, si lane > 0 y la calle interior está libre: lane-- (busca el palo),
      salvo en la recta final si no es puntero y ya esprinta (los cerradores atacan por fuera)
  calle libre = ningún caballo en ella con pos en (mi pos - 19, mi pos + 38)
```
Esto produce sin reglas especiales: el **sesgo del cajón** (los de fuera recorren más metros en la
primera curva o se meten detrás), el **duelo de punteros**, los cerradores **sin hueco** en la recta y
los **tirones** de los caballos nerviosos.

#### 2.4.5 Llegada y resultados
- Orden: por tick de llegada, empate por mayor exceso sobre la meta (y por hueco si persiste).
- Tiempo del ganador = tick x 4 centésimas ("1:10.52").
- Margen con el anterior: al tick en que cruza el anterior se guarda la distancia que le falta a cada
  uno (`gap`, 1/16 m). Texto: `gap < 3` "nariz", `< 8` "cabeza", `< 16` "cuello", si no cuartos de cuerpo
  `q = (gap * 27) >> 8` → "1/2", "3/4", "1 1/4"... ; `q >= 40` → "10+".
- Límite de seguridad: 8000 ticks.

#### 2.4.6 Jinetes
Habilidad `jinete` 0-7 (la de los rivales: `rng_range(8)`): +2 de `vmax` por punto (KJ), menos salidas
malas (`10 - jinete`), y desde 5 sabe esperar el sprint si no le queda energía. El descargo (aprendices)
baja el peso: cada lb vale 2 de `vmax` (KW). Plantilla, contratos y precios en §2.14.

#### 2.4.7 Calibración
La tabla de v1.0 (prototipo, 90 carreras por recorrido, rivales de clase 4) queda como referencia:

| Recorrido v1.0 | Tiempo ganador | Victorias por tercio de rating (bajo/medio/alto) | Por tercio de cajón (dentro/medio/fuera) | Índice táctica P/A/C |
|---|---|---|---|---|
| HV 1200 | 1:10.28 | 25 / 28 / 37 | 56 / 21 / 13 | 46 / 116 / 134 |
| HV 1650 | 1:36.80 | 22 / 29 / 39 | 26 / 36 / 28 | 98 / 122 / 79 |
| ST 1200 | 1:10.08 | 24 / 27 / 39 | 37 / 29 / 24 | 56 / 118 / 127 |
| ST 1600 | 1:33.88 | 24 / 27 / 39 | 45 / 31 / 14 | 84 / 129 / 87 |
| ST 2400 | 2:20.60 | 34 / 31 / 25 | 36 / 38 / 16 | 102 / 160 / 40 |

**Pendiente en M1a**: repetir la calibración con los recorridos v1.1 (equivalentes más cercanos: HV 1200 →
LIN1200, HV 1650 → LIN1650, ST 1200 → PAK1200, ST 1600 → PAK1600, ST 2400 → PAK2400; arena → PAKA) y
los objetivos de §11. Linterna tiene curvas más cerradas (bk 6): se espera un sesgo de cajón algo mayor
que en HV v1.0, que es lo buscado. Sensibilidad v1.0: un caballo con +5 en VEL, RES y REM sobre lo que
dice su rating gana el 44 % (con +10: 64 %).

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

- Cobras `premio - (premio >> 3)` (12.5 % para jinete y mozo); la monta suelta se paga siempre (§2.14).
- Fama (u16): 1º la columna de la tabla, 2º la mitad, 3º un cuarto (redondeo hacia abajo). Abre
  contratos de jinetes y sementales (columna "fama mín.").
- Gastos semanales (paso 5): **20k por caballo en cuadra**, 3k por yegua o potro en la granja, sueldos
  de jinetes contratados. Veterinario al lesionarse: 20k (leve), 60k (grave).
- Venta de un caballo: al mercado, por el 75 % de su valor (§2.15).
- Números rojos: con dinero < 0 solo se permite Descanso (y no se puede comprar ni contratar). Tras 8
  semanas seguidas en rojo, el banco vende tu caballo en cuadra de mayor valor y el contador vuelve a 0.
  Sin caballos en cuadra ni potros y en rojo: FIN ("La cuadra cierra").

### 2.8 Fatiga y lesiones
- Recuperación (paso 4, todos los caballos en cuadra): `fat -= 8 + (SAL >> 3)`.
- Entrenamiento: `fat += fatiga de training.tbl`. Carrera: `fat += 20 + dist100` al acabar.
  `fat` entre 0 y 100. Más de 80: el veterinario no deja correr.
- Lesión: tras cada entrenamiento con riesgo > 0 y tras cada carrera (riesgo 4), con la fatiga de antes:
  `p = riesgo + max(0, (fat-50) >> 1) + max(0, (60-SAL) >> 3)`; si `rng_next() < p`: lesión de
  `3 + rng_range(6)` semanas; y si `rng_next() < 32`, grave: `16 + rng_range(16)` semanas y pot VEL -3.
- Un caballo lesionado solo descansa; al llegar a 0 semanas vuelve con su fatiga actual.

### 2.9 Campo rival (`gen_field`)
Al resolver una carrera: los caballos del jugador ocupan los primeros huecos; el resto hasta
`tracks.field`, por hueco (RNG en este orden): `rating = lo + rng_range(hi - lo + 1)` (rangos: C5 10-40,
C4 40-60, C3 60-80, C2 80-100, C1 100-120, G3 75-100, G2 85-110, G1 95-120, Copa Internacional 110-125), y luego:
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
- Nacimiento en la semana 41 en un hueco de potro libre (si no hay, el potro se vende por su valor de
  subasta estimado, §2.15.3, mínimo 30k).
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
granja si hay hueco (si no, venta al mercado); macho → venta al mercado (§2.15). Yeguas de 19: dejan
la cría (se quitan con un mensaje). Potros: 0 → 1 → 2 (a cuadra si hay box).

### 2.12 Carreras especiales (M1: dos)
| Semana | Nombre | Recorrido | Tipo | Rating mín. |
|---|---|---|---|---|
| 6 | Premio Linterna (fiesta de medio otoño) | LIN1650 (noche) | G3 | 70 |
| 15 | **Copa Internacional** (diciembre) | PAK2000 césped | Internacional | 100 |
M2 añade el resto (§10). La Copa Internacional es la meta del juego: al ganarla, pantalla de victoria
y se sigue jugando.

### 2.13 Datos (`res/data/*.tbl`, `harness/tables.py`)
`rules.tbl` (constantes de §2.4-2.8 en filas id/valor; sale `LANES_MAX`), **`venues.tbl`, `tracks.tbl`,
`segs.tbl`, `courses.tbl`** (§2.4.1; `courses.tbl` pierde las columnas bk, nseg, m1-m6 y bends),
`races.tbl` (clases y especiales: recorrido, banda, rangos rivales, p1-p5, fama), `meetings.tbl`
(plantillas de 4 carreras: recorrido + clase), `calendar.tbl` (44 filas: mes, plantilla del miércoles,
plantilla del domingo, especial; M2: sábado), `training.tbl`, **`jockeys.tbl`** (§2.14), `stallions.tbl`,
**`market.tbl`** (filas id/valor de §2.15: CREC, ROOM, OFFER_CLS, márgenes), `start.tbl` (caballos
iniciales), `names.tbl` (32 sustantivos + 32 adjetivos invariables de género, sin acentos: "Oro",
"Viento", "Perla", "Jade", "Loto", "Tifon", "Grulla"... + "Feliz", "Lunar", "Veloz", "Sesenta", "Ocho",
"Imperial", "Fugaz", "Leal"...; nombre de 14 caracteres máx.), `comment.tbl` (frases con `{N}`).
Generados por `design/gen_track.py` desde las tablas: minimapa de cada pista (`mm_<pista>`: 24 tiles +
camino de puntos, §5.1). Los mapas `res/maps/hv.map`, `st.map` y `src/track_data.c` de la vista cenital
se borran.

**Partida inicial (`start.tbl`, fija):**
| Nombre | Sexo/edad | VEL RES REM TEM SAL (actual) | Potencial | dpref | Estilo | Rating |
|---|---|---|---|---|---|---|
| Oro Sesenta | macho 3 | 38 32 36 55 60 | 58 50 55 60 60 | 12 | puntero | 30 |
| Viento Feliz | macho 3 | 34 38 30 45 55 | 50 62 48 55 55 | 16 | acecho | 25 |
| Perla Lunar | hembra 2 | 30 28 32 60 65 | 64 56 62 65 65 | 14 | cerrador | 35 (sin correr) |
| Brisa Dorada | yegua 8 | (yegua) | 58 62 50 55 60 | 16 | cerrador | - |
Jinetes al empezar: ninguno contratado (Lau y los aprendices montan sueltos).

### 2.14 Mercado de jinetes (M1b; extras en M2)

**Plantilla (`jockeys.tbl`)** — nombres ficticios:
| Id | Nombre | Hab. | Descargo lb | Sueldo k$/sem | Monta suelta k$ | Fama mín. contrato | Ocupado /256 |
|---|---|---|---|---|---|---|---|
| AHKEUNG | Ah Keung (aprendiz) | 0 | 10 | 2 | 1 | 0 | 40 |
| NG | Ng (aprendiz) | 1 | 7 | 3 | 2 | 0 | 50 |
| LAU | Lau | 2 | 0 | 4 | 3 | 0 | 60 |
| CHAN | Chan (aprendiz) | 3 | 2 | 5 | 3 | 5 | 80 |
| KWOK | Kwok | 3 | 0 | 6 | 4 | 10 | 90 |
| WONG | Wong | 4 | 0 | 8 | 6 | 25 | 110 |
| DUARTE | Duarte | 5 | 0 | 12 | 9 | 50 | 140 |
| BRADY | Brady | 6 | 0 | 18 | 14 | 90 | 170 |
| FONTAINE | Fontaine | 7 | 0 | 26 | 20 | 150 | 200 |
(*) Cifras de partida. El descargo vale tanto como la habilidad: 7 lb = 14 de `vmax` ≈ 7 puntos de jinete;
por eso un buen aprendiz es la jugada barata en hándicaps de peso alto (no descarga en especiales).

**Monta suelta** (como v1.0): en INSCRIBIR eliges cualquier jinete **libre ese día**; pagas su monta
siempre y el 12.5 % del premio. Un jinete monta una sola vez por carrera.
**Disponibilidad** (paso 6 de la semana, tras `week++`; RNG en este orden): por fila de la tabla, para
cada jinete no contratado por ti: `ocupado_mie = rng_next() < OCUP`, luego `ocupado_dom = rng_next() < OCUP`
(los buenos suelen estar comprometidos con otras cuadras). Se guarda como 2 bits por jinete y se ve en
JINETES e INSCRIBIR ("ocupado el miercoles").

**Contrato** (pantalla JINETES → CONTRATO): hasta **2 jinetes de cuadra** a la vez.
- Requisito: `fama >= fama_min` y dinero ≥ prima. Duración a elegir: 10, 20 o 40 semanas.
- Prima de firma = `2 * sueldo` (una vez). Sueldo semanal en el paso 5. Monta gratis para tus caballos
  (solo el 12.5 % del premio) y **siempre disponible** para ti (no tira ocupación).
- Despedir antes de tiempo: indemnización `(semanas_restantes * sueldo) >> 1`.
- Al acabar: aviso en INFORME 2 semanas antes y al terminar ("El contrato de Wong acaba"); renovar =
  firmar otra vez (prima incluida).
- Rentabilidad (para el texto de ayuda de Ah Fat): el contrato compensa con ~2 montas por semana.

**M2**: aprendices que ganan bajan descargo (10 → 7 a las 15 victorias, → 5 a las 30, → 2 a las 45, 0 a
las 60) y suben 1 de habilidad cada 20 victorias; jinetes extranjeros de temporada (llegan en la
semana 1, se van en la 40); cuadras rivales con nombre que tienen contratados a jinetes concretos
(ocupado = 255 en sus reuniones); sanciones (suspensión 1-2 semanas por "monta descuidada",
`rng_next() < 3` por carrera con tirón); afinidad (+1 de habilidad con un caballo montado ≥ 4 veces).

**Estado guardado**: por jinete 3 B (semanas de contrato u8, bits de ocupación, victorias contigo u8) = 27 B.

### 2.15 Mercado de caballos

#### 2.15.1 Valor de un caballo (`valor(h)`, k$, u16; ROM == modelo)
```
act  = ((VEL + RES + REM) * 85) >> 8          (≈ media; en puntos)
pot  = ((pVEL + pRES + pREM) * 85) >> 8
perf = (rating * rating) >> 3                  (rating 30 → 112, 60 → 450, 100 → 1250, 125 → 1953)
gan  = 15 * min(victorias, 10)
crec = max(0, pot - act) * CREC[edad]          CREC edades 2..8: 12 8 4 1 0 0 0
v = 40 + perf + gan + crec
hembra y edad >= 4:  v += 4 * max(0, pot - 45)            (valor de cría)
edad >= 6:           v = (v * EDADV[edad - 6]) >> 2         EDADV 6: 3, 7: 2, 8: 1
lesión grave en curso: v >>= 1;  leve: v -= v >> 3
v = max(v, 10)
```
Ejemplos: Oro Sesenta al empezar (3 años, rating 30, act 35, pot 54) = 304k; potro de 2 años sin correr,
pot 60 = 469k; C1 de 4 años rating 110, 6 victorias = ~1660k. Un caballo cuesta entre media y una
temporada de premios de su clase (*). **Vender** (FICHA): instantáneo al 75 % (`v - (v >> 2)`).

#### 2.15.2 Venta privada (M1b): pantalla MERCADO
- **4 ofertas** que se renuevan en las semanas 1, 5, 9, ..., 41 (paso 6, cada 4 semanas; también en
  verano). Una oferta comprada deja su hueco vacío hasta la renovación. Comprar: dinero ≥ precio (no a
  crédito) y box libre; el caballo entra con plan Descanso y sus estrellas visibles al momento.
- Generación, por oferta k = 0..3 (RNG en este orden):
```
cls  = OFFER_CLS[rng_range(16)]                C5 x7, C4 x5, C3 x3, C2 x1
edad = 2 + rng_range(4)
rating = edad == 2 ? 35 : lo + rng_range(hi - lo + 1)        C5 15-39, C4 40-59, C3 60-79, C2 80-99
ai_horse(rating, dist100 = 14)                 las llamadas de §2.9 (VEL RES REM TEM dpref fat jinete
                                               estilo surf nombre x2); fat y jinete se descartan (fat = 0)
para VEL, RES, REM: pot = clamp(actual + ROOM[edad - 2] + rng_range(9), 10, 99)    ROOM 20 12 6 2
si edad == 2: actual = (pot * 10) >> 4  (62.5 %, como un potro propio)
pTEM = min(99, TEM + rng_range(6));  SAL = 40 + rng_range(41) (pSAL = SAL)
curva = rng_range(3);  sexo = rng_next() & 1
victorias = edad == 2 ? 0 : (rating >> 5) + rng_range(2);  carreras = 4 * victorias + rng_range(6)
precio = valor + ((valor * (6 + rng_range(14))) >> 6)        +9..+30 % de margen del tratante (en 32 bits)
```
- La ficha de la oferta es FICHA en modo "oferta" (sin plan; opciones Comprar / Volver). El precio
  delata algo del potencial oculto, con ruido: es parte del juego ("caro no siempre es bueno").
- **Estado guardado**: 4 ofertas x 50 B (formato de caballo) + 4 precios u16 = 208 B.

#### 2.15.3 Subasta de potros de 1 año (M2)
- Semana 42 (verano): SUBASTA con 6 potros de 1 año generados con padres de `stallions.tbl` y yeguas
  ficticias (`pedigree` visible: padre, madre y su récord) y **nota de morfología** A-E =
  `pot_media + rng_range(13) - 6` (≥ 75 A, ≥ 65 B, ≥ 55 C, ≥ 45 D, si no E): el potencial real no se ve.
- Valor de salida: `40 + 6 * max(0, PS - 40) + (cuota_padre >> 3)`, PS = media de los potenciales
  medios de padre y madre.
- Puja contra 3 pujadores: cada uno tiene un tope `valor_real * (192 + rng_range(129)) >> 8` (75-125 %).
  Cada ronda: A = subir 10 % (mínimo 10k), B = retirarse; los pujadores siguen mientras el precio no
  pase su tope. Gana el último que sube; paga su última puja. El potro va a la granja (hueco de potro).
- También puedes **llevar tus potros de 1 año** a la subasta: se venden por el tope más alto de los 3.
- M2 además: ofertas de cuadras rivales por tus caballos tras una victoria (90-120 % del valor, en
  INFORME, aceptar/rechazar), reclamar caballos en carreras "de reclamo" de C5.

---

## 3. Controles

| Botón | Menús / gestión | Carrera |
|---|---|---|
| Cruceta arriba/abajo | mover cursor (repetición 16/6 f, gbe_menu/gbe_list) | - |
| Cruceta izq./der. | cambiar valor (plan, jinete, táctica, duración de contrato) / página de la ficha | - |
| A | confirmar (en SUBASTA: pujar) | cámara: mi caballo ↔ el líder |
| B | volver (en SUBASTA: retirarse) | mantener 30 f: "Saltar al resultado" (pide confirmación) |
| Start | en ESTABLO: "Avanzar semana" (con confirmación) | pausa |
| Select | en FICHA: siguiente caballo | cambiar el foco entre tus caballos (si llevas 2) |
Título: Select + Start = menú de depuración de M1 (saltar a semana N, +1000k, carrera en cualquier
recorrido), quitar en M3.

---

## 4. Pantallas y flujo

```
TITULO -(Nueva/Continuar)-> ESTABLO
ESTABLO -> CABALLOS (gbe_list) -> FICHA (2 páginas; plan, retirar, vender)
        -> CARRERAS (carta de miércoles y domingo) -> INSCRIBIR (caballo -> jinete -> táctica)
        -> JINETES (gbe_list) -> CONTRATO (duración, firmar / despedir)
        -> MERCADO (4 ofertas) -> FICHA modo oferta (comprar)
        -> GRANJA (yeguas, potros) -> CUBRIR (semental)
        -> AVANZAR -> [por carrera tuya: PRESENTACION -> CARRERA -> RESULTADO] -> INFORME -> ESTABLO
        -> GUARDAR
M2: INFORME (semana 42) -> SUBASTA -> INFORME
RESULTADO (Copa Internacional ganada) -> VICTORIA -> INFORME
INFORME (sin caballos y en rojo) -> FIN -> TITULO
```
Maquetas aproximadas (el ui-designer las rehace): `design/screens/carrera.screen` (**rehacer con §5.1**),
`design/screens/establo.screen` (menú de 7 opciones en 2 columnas: Caballos, Carreras, Jinetes, Mercado,
Granja, Guardar, Avanzar). Transiciones: fundido a **blanco** (gbe_screen) para que los frames con el LCD
apagado (dibujo del texto proporcional) no destellen.

| Pantalla | Contenido |
|---|---|
| TITULO | logo de texto, "Nueva partida" / "Continuar" (si hay guardado) |
| ESTABLO | fila 0 fecha ("Sep sem 2  Temp 1"), fila 1 dinero y fama, filas 3-10 lista de caballos (2 filas: nombre + clase/rating; fatiga + plan), filas 12-17 menú |
| FICHA p1 | nombre, sexo, edad, rating/clase, VEL RES REM TEM SAL (número + barra de 8 tiles), estrellas, fatiga, lesión, plan |
| FICHA p2 | distancia ideal, superficie, estilo, récord (carreras/victorias/colocado), ganancias, padre/madre, última carrera, **valor** |
| CARRERAS | las 8 carreras de la semana (día, hipódromo, clase, distancia, superficie, bolsa) con tu inscrito al lado |
| INSCRIBIR | caballo → jinete (lista: tuyos primero, luego libres ese día con monta; ocupados en gris) → táctica |
| JINETES | 9 filas: nombre, habilidad (barra 0-7), descargo, sueldo, monta, estado ("tuyo 12 sem" / "libre" / "ocupado mie" / "fama 50") |
| CONTRATO | jinete, duración 10/20/40 (izq./der.), prima, sueldo; o "Despedir: indemnizacion 36k" |
| MERCADO | 4 filas de 2 líneas: nombre, sexo/edad, clase/rating, estrellas, precio; "Nuevas ofertas en 3 sem" |
| PRESENTACION | 1 fila por corredor: dorsal, cajón, nombre, peso, rating; tus caballos con flecha; cabecera con hipódromo, recorrido y superficie |
| CARRERA | §5.1 |
| RESULTADO | fila 0 carrera; filas 1-14 puesto, dorsal, nombre, margen; filas 15-17 tiempo, premio, rating antes>después |
| INFORME | parte de Ah Fat: líneas por caballo (+VEL 1, lesión, fatiga), dinero de la semana, nacimientos, contratos que acaban, "Hay ofertas nuevas en el mercado" |
| GRANJA | yeguas (preñada de...), potros (edad, estrellas) |

## 5. HUD e interfaz

### 5.1 Pantalla de carrera: cámara lateral de TV

La cámara está **en el interior del óvalo** y corre junto al pelotón mirando hacia fuera: el palo
interior queda delante (abajo), las calles exteriores más arriba y más lejos, y detrás la tribuna y la
ciudad. Caballos de perfil. En pistas DER los caballos van de izquierda a derecha; en IZQ (M2) todo en
espejo (x de pantalla = 159 - x, sprites con FLIPX, SCX negado).

**Disposición** (20x18 tiles; BG con un SCX por banda, cambiado por raster; ventana abajo):

| Filas | Líneas | Capa | Contenido | Desplazamiento (SCX) |
|---|---|---|---|---|
| 0-2 | 0-23 | lejana | cielo + skyline de la ciudad / montes (panorama de 256 px: columnas 0-15 = lado de la tribuna, 16-31 = lado contrario) | `rot + (cam >> 5)` (sombra de SCX en VBlank) |
| 3-4 | 24-39 | media | tribuna con público (en la zona de tribuna) o escenario del tema (árboles, edificios bajos, campo, agua); en pistas `inner`: franja de la pista exterior | `cam >> 1` |
| 5 | 40-47 | pista | palo exterior (lejano) + muro de la tribuna | `cam + curva[0]` |
| 6-12 | 48-103 | pista | banda de la pista (césped o arena), rayas de corte cada 64 px, postes de distancia, cajones, meta | `cam + curva[1..7]` (bandas de 8 líneas) |
| 13 | 104-111 | cercana | palo interior en primer plano | `cam + (cam >> 2)` (x1.25: sensación de velocidad) |
| 14-17 | 112-143 | ventana (WY 112) | HUD + comentario + minimapa | fija |

`cam` = x de cámara en px de mundo (u16). Escala: **4 px = 1 m** (`x = pos >> 2`; un cuerpo ≈ 9.5 px;
la pantalla abarca 40 m ≈ 17 cuerpos). Velocidad típica: ~0.71 m/tick → la banda de pista corre ~2.8
px/frame, la media ~1.4, la cercana ~3.5, la lejana ~0.1 + el giro: el parallax de 4 capas es la
sensación de velocidad.

**Calles → pantalla (filas visuales).** Cada 8 frames se ordena a los corredores por clave
`lane * 16 + cajón` (de fuera a dentro) y cada uno recibe una **fila visual única** `v` = 0 (más
exterior) .. N-1 (palo): `pies_y = 50 + 4 * (v + 14 - N)` → de 50 a 102 (la última línea del sprite).
La y real se acerca 1 px/frame (los cambios de calle se ven como subir/bajar). Por ser filas únicas a
4 px, **una línea cruza como mucho 4 caballos = 8 sprites** (5 = 10 durante un cambio de fila).
Escala por profundidad: filas visuales 0-6 usan los fotogramas "lejos" (caballo de 12 px de alto dentro
del 16x16), 7-13 los "cerca" (16 px). Mismo número de sprites.

**Caballos**: **16x16 (elegido por el usuario, 2026-10-15: todo el pelotón en pantalla; el arte se pule al final, ver design/horse_study.png)** = 2 sprites 8x16, galope de 4 fotogramas compartidos (fase = `(t >> 2) + i` & 3),
x de pantalla en 8 bits relativa a la cámara (`(pos >> 2) - cam`, más `curva[banda de sus pies]`),
morro en x. Tus caballos con OBP1 (seda invertida). Ocultos con Y = 0 si están fuera de 0..167 en x.
Orden de OAM: de la fila más cercana a la más lejana (en la misma x gana el cercano). **Límite del DMG**:
con x distintas tapa el sprite de menor x, no el más cercano: se acepta (contornos de color 3 en el
arte para que se lean los solapes). Arranque del OAM rotatorio como hoy (`rv_rot`): si algún frame
pasa de 10 por línea, el que sobra parpadea en vez de desaparecer.

**Cámara**: foco = tu caballo mejor colocado (A: el líder; Select: tu otro caballo). Objetivo: morro
del foco en x = 88; si el líder queda a más de 152, `objetivo = min(lider - 152, foco - 24)`.
`cam += clamp(objetivo - cam, -6, +6)` por frame. Antes de salir: cámara en los cajones; tras la meta,
se para en el poste.

**Curvas (por raster)**. El tramo del foco (`course_build`) da dos cosas:
- **Giro del fondo**: `rot = (rumbo * 4) & 255` px, con rumbo en 1/64 de vuelta = giro acumulado de
  los tramos anteriores + `ang * metros_dentro / m` del actual (0 en la recta de meta). Una curva de
  180° desliza el panorama lejano 128 px: en la recta de enfrente se ve "el otro lado" de la ciudad y en
  una vuelta entera el panorama da la vuelta completa. Signo según `hand`.
- **Curvatura de la pista**: `curva[b] = (curv * KC[b]) >> 4`, KC = 16 12 9 6 4 2 1 0 (banda 0 = palo
  exterior ... 7 = junto al palo interior); la capa cercana no se curva. `curv` va hacia
  `±CURV_MAX` (12 px (*), signo por `hand`) dentro de un tramo con `bk > 0`, escalado por
  `min(metros_dentro, metros_que_quedan, 48) / 48` (entrada y salida suaves), y se acerca 1 px cada 2
  frames. Así los postes, rayas de corte, cajones y la meta (columnas verticales) se doblan en arco y el
  palo lejano se adelanta: la pista "se curva" hacia el fondo. Signo y CURV_MAX: ajustar en playtest.
- En recta (`curv == 0`) las bandas 0-7 tienen el mismo SCX y la tabla de raster se comprime.

**Raster** (módulo nuevo `gbe_raster`, §9): tabla de hasta 10 entradas (línea, SCX) preparada en
`update()` y cambiada en VBlank (doble búfer). Interrupción LYC en la línea anterior a cada cambio;
el manejador en asm espera el modo 0 (HBlank) y escribe SCX, luego programa el siguiente LYC.
Entradas: 24 (media), 40, 48, 56, ..., 96 (bandas de pista), 104 (cercana). En recta: 3 entradas.

**Zona de tribuna y escenario**: con `d = dist - pos/16` (m antes del poste; en pista cerrada `d mod
longitud`), la capa media muestra tribuna si `d <= stand_a` o `d >= longitud - stand_b`, si no el
escenario del tema. La capa media se rellena por columnas (2 tiles) por `gbe_vq` al entrar por el
borde (≤ 1 columna cada 4 frames a 1.4 px/frame). Público animado: `crowd` tiles de público con 2
fotogramas cambiados cada 16 frames (tile data, ≤ 4 tiles). Noche (`night`): cielo oscuro con ventanas
encendidas y focos sobre la tribuna (otro juego de tiles del tema, no otra paleta).

**Columnas en la banda** (escritas por `gbe_vq` al entrar por la derecha, borradas al salir, como v1.0):
cajones (filas 5-12, 8 tiles), postes de 1000/800/600/400/200 m que faltan (palo exterior y palo
interior: 2 tiles), meta (filas 5-13, 9 tiles, con el poste de foto). Las rayas de corte y los postes
del palo son periódicos en el mapa de 32 columnas: no se cargan.

**Ventana (filas 14-17)**:
- cols 0-13 fila 14: dígitos monoespaciados de `font_mini`: "0400m 0:52.40" (metros que faltan al
  líder, tiempo).
- cols 0-13 fila 15: "3/12" (puesto de tu foco / corredores) + marca de cámara ("TU" / "1o").
- cols 0-13 filas 16-17: comentario, 2 líneas proporcionales de 13 tiles (máquina de escribir, 1
  letra/frame).
- **cols 14-19 filas 14-17: minimapa** de 48x32 px (24 tiles de fondo). Base generada por
  `gen_track.py` desde `segs.tbl`: la pista entera a escala uniforme dentro de 44x28 px, recta de meta
  arriba (como la ve la cámara: la tribuna "detrás" = arriba), sentido según `hand`, poste marcado
  (en rectas sueltas, una barra horizontal). Camino `mm_path_<pista>`: (x, y) u8 cada 16 m hacia atrás
  desde el poste. Cada 8 frames: copiar la base a un búfer de WRAM (384 B) y pintar un punto de 2x2 px
  por rival (`índice = d >> 4`); el búfer va a VRAM en 4 frames (6 tiles por VBlank) sobre el juego de
  tiles que no se ve (doble búfer de 24 + 24 tiles), y al acabar se cambian los 24 índices de la ventana.
  Tus caballos: 1 sprite 8x8 cada uno (anillo de 3x3, OBP1, parpadeo cada 16 frames).

**Comentario** (`comment.tbl`, prioridad, mínimo 90 frames en pantalla salvo prioridad mayor), mirado
cada 16 frames: salida, salida mala de un caballo tuyo, nuevo líder (estable 32 ticks), entrada en
curva, entrada en la recta, tu caballo encerrado ≥ 16 ticks ("{N} no encuentra hueco"), ataque por
fuera (E3 con calle ≥ 2), líder cansado ("{N} se queda"), quedan 400 m, ganador y margen. El texto con
el nombre se parte en 2 líneas en tiempo de ejecución con `vwf_width` palabra a palabra.
Antes de salir: 60 frames con los caballos en los cajones; campana (SFX) y tick 0. Tras cruzar tu
último caballo, 60 frames más (los llegados siguen frenando 8/tick, fuera del modelo).

**Greybox (antes del arte, M1a)**: cielo BLANK (noche: SOLID); skyline = bloques de SOLID/GRAY de
alturas distintas, mitad de tribuna "torres" altas y mitad contraria "montes" bajos (se ve el giro);
tribuna = damero GRAY/DOOR (público, los 2 fotogramas = damero invertido), escenario = WALL sueltos
(árboles); palos = fila de WALL con hueco GRAY cada 32 px; pista = FLOOR (arena: GRAY) con una columna
GRAY cada 64 px (las rayas: con ellas se ve la curvatura); postes DOOR; cajones BOX; meta CHECK.
Caballo = 2 sprites: BOX sobre BOX (cuerpo) + dígito del dorsal sobre BOX (cabeza); 10-14 se muestran
como A-E. Minimapa: línea de 1 px de la pista + puntos. Todo ello se ve en una captura de test en una
recta y en una curva.

### 5.2 Menús
- Texto proporcional `font_mini` (gbe_vwf), mayúscula inicial, sin acentos ni eñe ("espera un potro").
  Números que cambian (dinero, fatiga, stats) con dígitos monoespaciados de `font_mini` en VRAM (baratos).
- Cursor ARROW_R de greybox; barras de atributo con GRAY/SOLID (8 tiles = 0-99 en pasos de ~12).
- Pantallas con mucho texto (FICHA, PRESENTACION, RESULTADO, JINETES, MERCADO): se dibujan con el LCD
  apagado en `screen_build` (unos 200-300k T: 3-4 frames en blanco dentro del fundido a blanco, `skip_measure`).

---

## 6. Progresión y dificultad

| Etapa | Qué pasa | Meta del jugador |
|---|---|---|
| Temporada 1 | 3 caballos C5, 800k, aprendices y Lau, 4 ofertas C5-C4 asequibles | ganar en C5, subir uno a C4-C3, no lesionar, decidir si comprar o ahorrar |
| Temporada 2 | primer potro propio (de Brisa Dorada), fama abre Wong/Duarte y Dragon de Jade | C2-C1, Premio Linterna, primer jinete contratado |
| Temporadas 3-5 | segunda generación, Seda Imperial, Fontaine, subastas (M2) | caballo de rating 110+, Copa Internacional |
La dificultad no cambia con el tiempo: la ponen los rangos de rating de los rivales por clase (tablas)
y la Copa Internacional (110-125). Clásico de GB pero amable: nada castiga sin aviso (Ah Fat avisa de
fatiga > 60, caballos fuera de su distancia, contratos que acaban y compras que dejan la cuenta por
debajo de 8 semanas de gastos).

---

## 7. Contenido y assets

| Asset | Tipo | Tiles | Notas |
|---|---|---|---|
| greybox | BG + sprite | 13 | `harness/common/greybox.tiles` |
| font_mini | BG (+ 10 dígitos y A-E en sprite en greybox) | 42 | dígitos y mayúsculas monoespaciados (HUD, números) |
| texto proporcional | BG, slot reservado | 200 | `font_mini` + `font_mini_lower` + `font_mini_es` vía gbe_vwf |
| minimapas (7 pistas) | BG, en el slot durante la carrera | 24 c/u en ROM, 48 en VRAM (doble búfer) | generados por `gen_track.py` |
| M3: caballo | sprite | 32 | 2 escalas x 4 fotogramas x 4 tiles (8x16) |
| M3: pista y fondos | BG, en el slot durante la carrera | ~70 por tema | skyline (día/noche) 24, tribuna + público 16 (+4 anim.), palos 6, césped/arena 6, postes/cajones/meta 8, escenario del tema 10 |
| M3: espejo IZQ | BG | +~20 | tiles asimétricos de tribuna/escenario volteados (el DMG no voltea el fondo) |

**Carrera, VRAM de fondo**: greybox 13 + font_mini 42 + slot 200 (comentario 26 + minimapa 48 + arte del
tema M3 ~70 = 144 ≤ 200) = **255/256**. **Sprites**: greybox 13 + dígitos/letras 15 + punto del minimapa 1
(M3: + caballo 32) ≤ 61/128. **Sprites en pantalla**: 14 x 2 + 2 puntos = **30/40**. **Por línea**: ≤ 8 en
la banda de pista (filas únicas a 4 px), 10 durante un cambio de fila; la ventana solo tiene los 1-2
puntos del minimapa.

### 7.1 Hogares de VRAM (→ game.json)
LCDC.4 = 0 (fondo en $8800): fondo 0-255, sprites 0-127 propios.
```
"vram_order": ["greybox", "font_mini", {"text": 200}],
"vwf": {"fonts": ["font_mini", "font_mini_lower", "font_mini_es"], "slot": "text"},
"vram_scenes": {
  "menu": { "spr": [[0, "greybox"]] },
  "race": { "spr": [[0, "greybox"], [16, "font_mini", 0, 10]] }
}
```
Slot de texto por escena: menús 0-199 (cada pantalla reparte texto fijo + dinámico, ≤ 200); carrera:
comentario 0-25, minimapa A 26-49, minimapa B 50-73, arte de pista/fondo 74-199 (M3). `rv_build` carga
el slot de carrera con el LCD apagado; al volver a un menú, `screen_build` lo rellena entero. Nadie más
escribe en el slot.

---

## 8. Sonido
M1: solo SFX con `gbe_sfx` (cursor, confirmar, volver, campana de salida, ganador, lesión, martillo de
la subasta en M2). Sin música (el motor no tiene reproductor: riesgo R5, M3). M3: rumor de público
(ruido canal 4 bajo) que sube en la recta final.

---

## 9. Técnica

- **Cartucho:** MBC5 + RAM + batería, 128 KB: `["-autobank", "-Wm-yt0x1B", "-Wm-yo8", "-Wm-ya1"]`,
  `GBE_BANKED`. Banco 0 (~11 KB estimado): gbe caliente (frame, oam, video, vq, tiles, bank, **raster**),
  simulación de la carrera (asm) y bucle principal. En bancos: vista de carrera (`race_view.c`, BANKED,
  como hoy), menús y pantallas, semana, mercados, cría, campo rival, comentario, guardado, tablas,
  fuentes, minimapas. **Se quitan `gbe_world.c/.s`** de `common_src` (la vista cenital): libera banco 0.
- **Módulos gbe usados:** gbe_frame, gbe_oam, gbe_video (sombras SCX y paletas, fundidos; **sin** el
  corte de HUD superior), gbe_screen, gbe_sfx, gbe_bank, gbe_save (por trozos), gbe_rng, gbe_vq,
  gbe_tiles, gbe_vwf, gbe_menu, gbe_list, gbe_text (dígitos), gbe_selftest. No: gbe_map/world/actors.
- **Trabajo nuevo del motor (riesgo R6):** `gbe_raster` — cadena de LYC desde una tabla (línea, SCX) de
  hasta 12 entradas, doble búfer cambiado en VBlank, manejador STAT en asm (vector directo, no la cadena
  de `add_LCD`: espera modo 0 y escribe SCX primero). Probarlo en `games/gbe_lab` (test: captura con
  rayas verticales → cada banda desplazada lo esperado; coste por interrupción medido).
- **Trabajo nuevo del juego:** `course_build` (C + Python), vista lateral (capas, filas visuales,
  curva, columnas, minimapa con doble búfer), `gen_track.py` reescrito (lint + minimapas desde las
  tablas), mercados (valor, ofertas, contratos, disponibilidad), partir texto con `vwf_width`, u32 con
  puntos de miles.
- **Guardado** (`save_begin/put`, versión 2): estado 32 B + 12 caballos x 50 B + registro de pedigrí
  32 x 16 B + jinetes 27 B + mercado 208 B ≈ **1.4 KB** (cabe dos veces en 8 KB de SRAM).
  - Caballo (50 B): flags (usado, sexo, estado: cuadra/yegua/potro/retirado/oferta), nombre[14], edad,
    vel16/res16/rem16 (u16), tem, sal, pot[5], dpref, surf (s8), estilo, curva, rating, fat, lesión,
    inactivo, carreras, victorias, colocados, ganancias (u16 k$, satura), padre, madre, registro, plan,
    inscripción, jinete, táctica, último puesto, preñez (semental o 0xFF).
  - Huecos M1: 6 boxes de cuadra (4 abiertos al empezar), 3 yeguas, 3 potros.
- **WRAM:** caballos 600 + registro 512 + carrera (14 x 64 = 896) + campo rival 560 + tira vwf 260 +
  minimapa 384 + tablas de raster 48 + ofertas 208 + jinetes 27 + colas ≈ **3.6 KB** (pila ≥ 512 B libre).
- **CPU de la vista de carrera (peor frame, 14 caballos, objetivo ≤ 20k T; la simulación va aparte, en asm):**

| Parte | T peor | Nota |
|---|---|---|
| Interrupciones de raster (10 x ~450) | 4.5k | en recta 3 x 450 = 1.4k |
| Colocar 14 caballos (x relativa en 8 bits, y suavizada, curva) | 2.5k | asm (`race_place.s` adaptado) |
| OAM: 28 sprites + 2 puntos | 4.2k | asm, ~300 T por caballo |
| Filas visuales (ordenar 14 claves) | 2k | solo en el frame 4 de cada 8 |
| Cámara, capas, rumbo, curva, tabla de raster | 1.5k | |
| Minimapa | 3.5k | frame 0: copiar base; frame 1: 14 puntos (nunca el mismo frame que las filas) |
| Columnas y capa media (preparar para `gbe_vq`) | 0.8k | |
| Comentario: 1 letra vwf | 2.5k | medido en v1.0 |
| HUD | 0.5k | |
| **Peor frame** | **≈ 20k** | ≈ 44 líneas; con la simulación asm (~15-20k) y el frame (~3k): ~85-95 líneas |
Palancas si se pasa: raster cada 16 líneas en vez de 8 (6 entradas), minimapa cada 16 frames,
comentario 1 letra cada 2 frames.
- **VBlank por frame en carrera** (≤ 3.4k T): minimapa 6 tiles (2k, frames 1-4 de cada 8) + letra del
  comentario 1 tile (0.33k) + HUD 14 índices (0.3k) + columnas ≤ 9 índices (0.2k) + capa media 2
  índices. Público animado (4 tiles, 1.3k) solo en los frames 5-7. Peor ≈ 2.9k.
- **Saltar al resultado:** simula sin dibujar (raster apagado) con el LCD encendido y una barra de
  progreso, todos los ticks que quepan en 60 000 T por frame, `skip_measure`.
- **Menús:** coste despreciable salvo el dibujo con LCD apagado (§5.2).

---

## 10. Hitos

- **M1 greybox jugable** (el usuario lo prueba al final), en tres pasos:
  - **M1a carrera** (hecho: modelo en ROM == `hv_model` en 6 recorridos v1.0, menú de depuración).
  - **M1a' pistas como datos + vista lateral:** `venues/tracks/segs/courses.tbl` y `course_build` (C ==
    Python, 27 recorridos, lint), `bk` por tramo y `lanes`/`field` por pista, recalibración (§2.4.7);
    `gbe_raster` en gbe_lab; vista lateral greybox (§5.1) en DER con capas, filas visuales, curva,
    columnas, cámara, HUD, comentario y minimapa; borrar la vista cenital (mapas, `track_data`, gbe_world).
    El usuario mira la carrera en Linterna y Pak Shan antes de seguir (es el núcleo visual).
  - **M1b gestión:** TITULO, ESTABLO, CABALLOS/FICHA, plan semanal (6 entrenamientos), CARRERAS e
    INSCRIBIR, calendario de 44 semanas (Linterna + Pak Shan, 2 plantillas por hipódromo, 2 especiales),
    premios, rating y clases, fatiga y lesiones, gastos y números rojos, envejecer y retirar, GRANJA con
    cubrición, nacimiento y herencia, **JINETES (9 jinetes, monta suelta con disponibilidad, 2
    contratos)**, **MERCADO (venta privada de 4 ofertas, vender al 75 %, `valor`)**, INFORME, guardado.
    Bots del modelo (§11).
- **M2 profundidad:** sábados de provincia (Fung Wan a izquierdas con la vista en espejo, Bahia Ming),
  calendario completo (Copa de Oro, Derby de 4 años, Milla de Campeones, Copa del Fundador, Gran Final
  de Linterna, Copa de Año Nuevo), arena de Pak Shan en todas las plantillas, **subasta de potros de 1
  año** (§2.15.3), ofertas de rivales por tus caballos, carreras de reclamo, **jinetes M2** (descargo que
  baja, extranjeros de temporada, cuadras rivales con contratos, sanciones, afinidad), instalaciones
  (piscina, caminadora, boxes extra), sementales propios, consanguinidad y "nicks", hándicap con cifras de
  actuación, ensayos de salida, castrar, rival (Cuadra Imperial del señor Ko), nombre del caballo a
  elegir, estadísticas de cajón por recorrido en la carta.
- **M3 arte, UI y sonido:** caballo de perfil con 2 escalas y galope, 4 temas de fondo (día/noche),
  público animado, título, marcos, fuente/UI del ui-designer, música (reproductor nuevo), fotofinish,
  fuegos en la Copa Internacional.
- **M4 hardware real** (flash cart): raster en hardware (temblor de SCX), tiempos de LCD apagado,
  guardado con corte de corriente.

---

## 11. Plan de pruebas

| Qué | Cómo |
|---|---|
| Carrera ROM == modelo | test: campo fijo + `rng_state` fijo → `pos`, `spd`, `ene`, `lane` de los 14 en los ticks 1, 50, 300, 600 y el orden/ticks de llegada iguales a `hv_model.run`; 20 semillas x recorridos de las 7 pistas |
| Pistas como datos | lint de `segs.tbl` (cierre, `bk` del radio, mangas solo en rectas, ≤ 6 tramos, recorridos ≤ 8 tramos y ≤ longitud en pistas abiertas); `course_build` ROM == Python en los 27; test con una **pista sintética** añadida solo en Python (tablas cargadas + fila nueva) que corre modelo y generador de minimapa sin tocar código |
| Saltar == ver | la misma carrera saltada y vista da el mismo resultado y `rng_state` |
| Campo rival | `gen_field` ROM == modelo (ratings, stats, cajones, nombres), tamaño = `tracks.field` |
| Semana | estado guardado + planes + semilla → tras "Avanzar" (carreras saltadas) atributos, fatiga, lesiones, dinero, rating, disponibilidad de jinetes, ofertas, `rng_state` == modelo; 100 semanas seguidas |
| Mercados | `valor()` ROM == modelo en 200 caballos aleatorios; ofertas ROM == modelo con semilla fija; comprar exige dinero y box; vender da el 75 %; contrato: fama mínima, prima, sueldo en gastos, indemnización al despedir, aviso de fin; un jinete no monta dos caballos en la misma carrera; ocupado no aparece en INSCRIBIR |
| Herencia | 50 cruces ROM == modelo (pot, dpref, surf, estilo, curva, sexo) |
| Reglas | inscripción rechaza lesionado, fat > 80, clase baja; peso con descargo y dorsales; números rojos → venta en la semana 8 |
| Guardado | apagar/encender con SRAM (`gb.power_off()`), corrupción de un byte → slot anterior; versión 1 → partida nueva |
| Vista: sprites por línea | en cada frame de 5 carreras completas (LIN y PAK 2400), contar desde OAM: ≤ 8 por línea fuera de cambios de fila y nunca > 10 |
| Vista: raster | tabla de cada frame: líneas ascendentes, ≤ 10 entradas, SCX de cada capa == fórmulas de §5.1 (lejana, media, bandas con `curva[]`, cercana); en recta 3 entradas; razón de avance de las capas en 120 frames ≈ 1/32 : 1/2 : 1 : 1.25 |
| Vista: geometría | rumbo al salir de cada curva == suma de `ang` (pista cerrada: 64 por vuelta); posición de los puntos del minimapa == camino de `gen_track` (±1 px); la tribuna aparece en `d <= stand_a` |
| Vista: capturas | recta de meta con tribuna, curva con la pista doblada, salida en cajones, llegada, noche en Linterna: PNG en `build/shots/` revisados con Read |
| Rendimiento | bot que mira 5 carreras completas de 14 caballos: `max_frame_lines < 110`, `vram_late == 0`; `gb.profile` de la vista ≤ 20k T; `gb.worst_frames` en la peor |
| Pantallas | `gb.vram_errors("race"/"menu")`, `gb.mockup_errors` en ESTABLO y CARRERA, texto leído con `gb.vwf_text` |
| **Equilibrio (bots del modelo, Python)** | ver objetivos abajo |
| Feel, ambiente de la carrera, ganas de "una semana más" | playtest humano (usuario) tras M1a' (la carrera) y tras M1b |

**Objetivos de equilibrio** (bots de `hv_model` sobre 200+ carreras o 10 temporadas):
- Tiempos del ganador (clase 4): LIN1200 1:10.0-1:11.5, PAK1600 1:33.5-1:35.0, PAK2000 1:59.5-2:02.0.
- LIN1200: tercio interior de cajones 45-60 % de victorias; PAK1200-1400: 36-45 %.
- Índice de cada táctica entre 70 y 140 en la media de recorridos (v1.0: punteros 44-80, ajustar con
  `START_EFF`, `COST[E2]`).
- Dentro de una banda, el tercio de rating alto gana ≤ 1.5 veces lo que el bajo (el hándicap iguala).
- Bot "medio" (rota Galope/Series/Fondo, corre cada 3 semanas en su clase, descansa con fat > 50, monta
  suelta con el mejor libre): acaba la temporada 1 con 300-1500k y una lesión como mucho por caballo
  cada 25 semanas.
- Bot "novato" (siempre Series, corre cada semana): ≥ 1 lesión en la temporada, dinero menor que el
  medio, pero no llega al FIN antes de la semana 30.
- Bot "experto": un caballo a C3 en la temporada 1 y un especial ganado antes de la temporada 4.
- **Mercado**: un caballo comprado en oferta recupera su precio en premios en ≤ 1.5 temporadas de media
  (bot medio); comprar y revender al momento pierde 30-45 %; un contrato de jinete de hab. ≥ 5 sube las
  ganancias del bot medio ≥ 10 % y su sueldo no supera el 25 % de lo que aporta.
- Cría: con el mejor semental asequible cada año, la media de potencial de la generación 3 supera a la
  1 en ≥ 10 puntos; sin elegir (semental al azar) no sube.

---

## 12. Decisiones

Tomadas:
- [x] **Vista de la carrera (v1.1, usuario): lateral inclinada tipo TV / Derby Stallion** con tribuna,
  ciudad, parallax, curvas por raster y minimapa con todos los corredores. Sustituye a la cenital
  implementada en M1a.
- [x] **Pistas como datos (v1.1, usuario)**, hipódromos ficticios.
- [x] **Mercado de jinetes y de caballos (v1.1, usuario)**: venta privada y contratos en M1b; subasta y
  extras en M2 (estudio).
- [x] **Ritmo: x2.4** de la realidad (1200 m ≈ 30 s) y saltar con B.
- [x] **Temporada: 44 semanas**, un turno por semana, con menú de depuración para saltar semanas.

Pendientes (caras de cambiar una vez hecha la vista):
- [ ] **P1. Profundidad de las calles.** (a) **Filas visuales únicas por orden de calle** (recomendada):
  nunca más de 8-10 sprites por línea, sin parpadeo, la profundidad es fiel en el orden pero no en la
  distancia (dos caballos en la calle 0 separados 10 cuerpos ocupan filas distintas). (b) y = calle real
  (4 px por calle): más fiel, pero con el pelotón pegado al palo 5-7 caballos comparten líneas →
  parpadeo constante en carreras de 12-14. (c) Híbrido: calle real y, si una línea pasaría de 5
  caballos, separar los de esa línea (más código y casos raros).
- [ ] **P2. Pistas a izquierdas en pantalla.** (a) **Espejo completo** (recomendada, M2: los caballos van
  de derecha a izquierda como en la TV; +~20 tiles de arte volteado); (b) siempre de izquierda a derecha
  y la mano solo cambia el sentido del giro y del minimapa (sin coste de arte, menos verosímil).

---

## 13. Riesgos
- **R1 CPU de la carrera**: simulación (asm) + vista (≤ 20k) en < 110 líneas; medir con `gb.profile`
  y `worst_frames` en cuanto exista la vista; palancas en §9.
- **R5 Música**: sin reproductor en el motor (M3).
- **R6 Raster**: `gbe_raster` es motor nuevo; temblor si otra interrupción o un `di` largo retrasa el LYC
  (el guardado y los cambios de banco con `di` no ocurren durante la carrera); PyBoy no garantiza el
  timing del hardware real a mitad de línea → M4 en flash cart. Plan B: 3 bandas sin curvatura (solo
  parallax + giro del fondo + minimapa) si la curvatura tiembla.
- **R7 Lectura de la curva**: que el arco por SCX se lea como "curva" y no como "pista torcida" no se
  sabe hasta verlo: CURV_MAX y KC son datos (`rules.tbl`) y se ajustan en el playtest de M1a'.
- **R8 Prioridad de sprites del DMG** (gana la x menor): solapes "al revés" entre caballos; se mitiga
  con contornos y con las filas a 4 px; no tiene arreglo en DMG.
- **R9 Alcance de M1b**: dos mercados más sobre la gestión; si M1b se alarga, la venta privada pasa a M2
  y solo queda "Vender" (los contratos se quedan: tocan la carrera).
- **R10 Recalibración**: los recorridos nuevos cambian el equilibrio de v1.0; hay que repetir los bots
  antes de M1b (los tests de igualdad ROM == modelo no dependen de ello).
