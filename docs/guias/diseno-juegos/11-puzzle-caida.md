# 11. Puzle de piezas que caen (o suben): versus y modo infinito

Para quien elige y afina un núcleo de puzle competitivo con simulador (estudio actual:
proyecto SNES, `C:/Users/David/Desktop/SNES/docs/estudios/navidad-puzzle/`, `sim.py` y `rulespace.py`). El capítulo resume lo que dicen la teoría de la
complejidad, la IA de juegos, la ciencia cognitiva y la teoría del diseño sobre este género, y cómo se traduce en
**medidas del simulador, diseño de bots y valores por defecto de la ROM**.

Marcas: **[V]** comprobado en la fuente durante la redacción (2026-11-15); **[S]** leído en un resumen secundario
fiable (wiki de la comunidad, reseña, índice bibliográfico) pero no en el texto original; **[M]** conocimiento
general sin fuente comprobada: contrastar antes de citarlo como cifra. Lista de fuentes al final.

Qué mide ya el simulador (para no repetirlo): escalera de habilidad L0→L1→L2(→L3), ventaja del primer asiento,
duración, cambios de líder y momento en que se decide la partida, remontadas y partidas al borde de la muerte,
opciones "casi óptimas" por decisión y su dispersión, ataques grandes por minuto, cuota de cadenas ≥2, habilidad
frente a suerte (L2 contra L1 con secuencias distintas) y, en solitario, nivel alcanzado, fracción en peligro,
recuperaciones por minuto y coeficiente de variación del tiempo por nivel (`rulespace.evaluate`, `rulespace.score`).

## 1. Complejidad computacional: qué significa para el techo de habilidad

**Resultados**

- **Tetris** (Demaine, Hohenberger y Liben-Nowell, COCOON 2003; versión de revista con Breukelaar, Hoogeboom y
  Kosters, IJCGA 2004): en la versión *offline* (se conoce toda la secuencia), maximizar filas borradas, tetris
  hechos, piezas colocadas antes de perder o minimizar la altura máxima es NP-completo; además, para cualquier ε > 0
  es NP-difícil aproximar el número de piezas o de filas a un factor p^(1−ε). [V]
- **Tetris con pocas piezas** (MIT Hardness Group, Demaine, Hall y Li, FUN 2024): limpiar un tablero sigue siendo
  NP-difícil con sólo **dos** tipos de pieza bajo SRS, y también en modo "sólo caída instantánea" y en 20G. [V]
  Las pruebas anteriores necesitaban cinco de los siete tipos.
- **Puyo Puyo** (Matsukane y Takenaga, informe técnico IEICE COMP2004-85, presentado en marzo de 2005; otras
  fuentes lo fechan en 2006): el problema de la **cadena máxima** en Puyo generalizado es NP-completo, por reducción
  desde 3-Partition. [V] Trabajos japoneses posteriores refuerzan el resultado. [S]
- **Match-3**: Walsh, "Candy Crush is NP-hard" (arXiv 1403.1911, 2014): alcanzar una puntuación en un número fijo de
  intercambios es NP-difícil (el cuerpo del artículo lo da como NP-completo). [V] Gualà, Leucci y Natale,
  "Bejeweled, Candy Crush and other Match-Three Games are (NP-)Hard" (arXiv 1403.5830; IEEE CIG 2014): resultado más
  fuerte y general para toda la familia, desde 1-in-3 SAT positivo. [V]
- **Lumines**: existe "LUMINES Strategies" (Aloupis, Cardinal, Collette y Langerman, LNCS 4630, 2007), un análisis
  del juego; no pude leer su resumen, así que no afirmo ningún resultado de dureza. [S]
- **Panel de Pon / Tetris Attack**: no encontré ninguna prueba publicada de su complejidad. Por analogía con match-3
  es plausible que sea NP-difícil, pero es una inferencia, no un resultado.
- **Tetris no se puede sobrevivir para siempre con un generador sin memoria**: Burgiel, "How to Lose at Tetris"
  (Mathematical Gazette 81(491), 1997) muestra que una secuencia alterna de S y Z acaba la partida en un pozo de 10
  de ancho; como un generador uniforme acaba produciendo esa racha, toda partida larga termina. [S] Con bolsa, 3
  piezas de vista previa y reserva se puede jugar indefinidamente. [S]

**Qué significa (y qué no)**

- NP-difícil habla del peor caso *offline* y de tableros generales. No prueba que el juego sea profundo ni que sea
  divertido; sí indica que **no hay una regla sencilla que lo resuelva**, así que el jugador depende de heurísticas
  que se pueden mejorar con práctica. Eso es una condición necesaria para un techo de habilidad alto, no suficiente.
- La dureza de la *cadena máxima* en Puyo es la versión formal de lo que el estudio ya observó: montar cadenas
  largas no tiene atajo y por eso sostiene el techo competitivo.
- La dureza de inaproximación de Tetris explica por qué los bots fuertes no "resuelven" el juego: lo juegan bien con
  funciones de evaluación, no con búsqueda exacta.
- Lo que siente el jugador es la versión *online* con reloj, que es más dura todavía: decide sin conocer la
  secuencia y en 0,2–1 s. La complejidad real para un humano la marca la vista previa y la velocidad, no la teoría.

**Qué aplicamos**

- No usar "es NP-difícil" como argumento a favor de un núcleo. Lo que vale es la medida empírica: la **escalera de
  habilidad** (L1 > L0, L2 > L1, L3 > L2) del simulador. Si un bot de búsqueda más profundo no gana claramente al
  voraz, el techo es bajo aunque el problema sea NP-difícil.
- Añadir una medida de **rendimiento decreciente de la búsqueda**: tasa de victorias de profundidad 3 contra 2 y de
  haz 12 contra 6. Si sube poco, el núcleo se agota pronto; si sube mucho, hay sitio para crecer como jugador.
- Ningún modo infinito debe permitir sequías que maten sin culpa (sección 5): es la lección práctica de Burgiel.

## 2. Jugadores artificiales: evaluación, búsqueda y bots humanos

**Tetris** (síntesis de Algorta y Şimşek, "The Game of Tetris in Machine Learning", arXiv 1905.01652, 2019,
presentado en el taller de videojuegos y aprendizaje automático de ICML 2017) [V]:

- **Dellacherie** (controlador hecho a mano, recogido por Fahey en 2003): seis rasgos, pesos a ojo:
  `−4·agujeros − pozos acumulados − transiciones por fila − transiciones por columna − altura de aterrizaje +
  celdas erosionadas` (celdas erosionadas = filas borradas × celdas de la pieza en esas filas). Media de 660 000
  filas en el tablero completo. [V]
- **Böhm, Kókai y Mandl** (MIC 2005): algoritmo evolutivo **conociendo la siguiente pieza**; 480 millones de filas
  con función lineal (34 millones con exponencial). El propio artículo de revisión avisa de que no es comparable con
  los de una sola pieza. [V]
- **Thiery y Scherrer, BCTS** (ICGA Journal 32, 2009): rasgos de Dellacherie más profundidad de agujeros y filas con
  agujeros, pesos con *cross-entropy*; 35 millones de filas; ganó la competición de aprendizaje por refuerzo de 2008
  con un rasgo más de diversidad de patrones. [V] Boumaza (2009) obtuvo pesos casi iguales a los de Dellacherie con
  CMA-ES y la misma cifra. [V] Gabillon et al. (2013, CBMPI) llegaron a 51 millones con aprendizaje por refuerzo. [V]
- **Estructura del problema**: la mediana de colocaciones posibles de una pieza es 17; la dominancia simple las
  reduce a 3 y la dominancia acumulada a 1 (Şimşek et al. 2016). [V] Es decir: casi todas las decisiones de Tetris
  tienen pocas alternativas razonables, y un humano probablemente filtra así.
- **Lo que no funciona**: el aprendizaje profundo desde píxeles apenas llegaba a unos cientos de filas en 2019. Con
  la puntuación que premia borrar varias filas a la vez, una evaluación lineal deja de ser la adecuada: hace falta
  "preparar" (subobjetivos como dejar el pozo para la I o el hueco del T-spin). [V]
- Las cifras de filas tienen varianza enorme y dependen de detalles de implementación; Thiery y Scherrer piden
  compararlas con mucho cuidado. [V]

**Puyo** [V salvo indicación]:

- Ikeda, Tomizawa, Viennot y Tanaka, "Playing PuyoPuyo: Two Search Algorithms for Constructing Chain and Tactical
  Heuristics" (IEEE CIG 2012): dos algoritmos de búsqueda en árbol más heurísticas tácticas; cadenas medias de 11,
  bastante por encima de las IA comerciales.
- Hanson y Moffat (AISB 50, 2014): búsqueda Monte Carlo frente a DFS y BFS; Monte Carlo rindió mejor. [S]
- Bot "Ama" (citrus610, blog, 2024): DFS a profundidad 2 sobre los dos pares conocidos (~8 ms; búsqueda completa
  ~60 ms); la medida más importante de la evaluación es la **cadena potencial** de la posición (simulando qué pasa si
  cae la pieza que falta); rasgos de forma (U, plantillas de cadena, enlaces de 2 y 3, basura, tiempo perdido);
  dispara cuando la cadena supera un umbral fijo. El autor sostiene que en versus **leer y temporizar al rival**
  importa más que hacer la cadena más grande. [V, fuente de aficionado]

**Qué hace buena a una función de evaluación**

1. Rasgos baratos y locales que un humano también ve (agujeros, alturas, transiciones, enlaces de color).
2. Un término de **potencial** que mire un paso más allá de lo visible (cadena latente en Puyo, pozo preparado en
   Tetris).
3. Pesos ajustados por optimización caja negra (CE o CMA-ES) con muchas partidas, no a mano; los pesos buenos
   suelen salir parecidos entre métodos, señal de que el paisaje es estable.
4. La profundidad rinde mucho cuando la vista previa existe (Böhm frente al resto), pero con rendimiento decreciente:
   Ama se queda en 2 por velocidad y gana por táctica.

**Bots humanos para playtest**

- Kirsh y Maglio (sección 3): un giro físico cuesta ~100 ms y uno mental 800–1200 ms; los humanos **prueban girando**.
  Un bot humano no debe pagar el pensamiento por orientación, sino un tiempo fijo de reconocimiento más el tiempo
  motor de cada pulsación.
- El tiempo de decisión crece con el número de alternativas que sobreviven al filtro de dominancia, no con las 17 (o
  22) colocaciones brutas.
- El error humano no es ruido blanco sobre todas las opciones: es elegir entre las 2–3 primeras con algo de ruido y,
  a veces, un fallo motor (columna equivocada, sobre todo en caídas largas: Kirsh observó que los expertos "cuentan"
  contra la pared antes de soltar cuando la pieza está alta).
- Holmgård, Green, Liapis y Togelius (IEEE Transactions on Games 11(4), 2019) proponen **personas procedurales**:
  bots con funciones de utilidad sencillas que un diseñador entiende (prudente, agresivo, coleccionista) para
  probar contenido como lo harían arquetipos de jugador. [V]

**Qué aplicamos**

- Mantener tres familias de bot, como ya hace `sim.Bot`, pero separar en el bot `human`:
  - `think` = reconocimiento base (p. ej. 15–25 fotogramas) + coste por alternativa viva tras dominancia.
  - tiempo motor = DAS inicial + ARR por columna + pulsación por giro (ver sección 3), en lugar de `T_MOVE` plano.
  - error motor dependiente de la altura de caída (más alto, más probable equivocarse de columna en ±1).
  - ruido de valor aplicado sólo a las k mejores (k = 3) en vez de a todas, que es lo que observan Şimşek et al.
- Añadir al bot de búsqueda un **término de potencial** explícito (cadena que se dispararía con la pieza que falta) y
  ajustar los pesos de `heuristic` con CMA-ES o *cross-entropy* sobre auto-juego, guardando la semilla. Comparar el
  bot ajustado contra el actual antes de usarlo en la escalera.
- Añadir **juego restringido** (Jaffe et al., AIIDE 2012) como prueba de profundidad: bots que nunca encadenan, que
  disparan siempre en cuanto pueden, o que nunca cancelan. Si uno restringido gana casi tanto como el completo, esa
  parte del sistema no aporta decisiones. [V]
- Un "lector de rival": el bot de búsqueda decide disparar mirando la basura pendiente y la altura del rival, no un
  umbral fijo. Medir cuánto gana sobre el umbral fijo: si no gana nada, el versus no premia la lectura.

## 3. Ciencia cognitiva: lectura, giro, vista previa y tacto

**Hallazgos**

- **Acción epistémica** (Kirsh y Maglio, "On Distinguishing Epistemic from Pragmatic Action", Cognitive Science 18,
  1994) [V]: los jugadores giran y mueven piezas no sólo para colocarlas sino para **saber** dónde encajan; girar
  físicamente 90° cuesta unos 100 ms y hacerlo mentalmente unos 800–1200 ms. Los giros empiezan pronto, a veces antes
  de que la pieza esté entera a la vista. En ~1 % de las caídas los jugadores llevan la pieza a la pared y vuelven
  para comprobar la columna; ocurre cuando la pieza está unas 6 filas más alta de lo normal (19 frente a 13 en
  expertos). En su montaje la caída libre empezaba en ~200 ms por fila.
- **Marcadores de pericia** (Lindstedt y Gray): Meta-T es un Tetris de laboratorio con registro completo (Behavior
  Research Methods 47(4), 2015). Con 39 rasgos por pieza, 240 jugadores y hasta 16 niveles, un análisis de
  componentes da tres factores que separan expertos de novatos, que combinan percepción, decisión y motricidad
  (Cognitive Psychology 109, 2019). [V, resumen] Los campeones del mundo tienen tiempos de acción mucho mejores y
  pagan una breve pausa (*cognitive speed-bump*) para decidir el sentido del giro aunque no cambie el resultado
  (CogSci 2020, preliminar). [V]
- **Aprendizaje y eficiencia** (Haier et al., Brain Research 570, 1992): tras 4–8 semanas de práctica diaria el
  rendimiento en Tetris subió más de 7 veces mientras el metabolismo cortical de glucosa bajaba; ocho sujetos. [V]
  Lectura de diseño: el juego pasa de deliberado a automático; lo que era difícil al principio se vuelve gratis.
- **Efecto Tetris** (Stickgold et al., Science 290, 2000): tras jugar varios días, muchos jugadores ven piezas al
  dormirse, incluidos amnésicos que no recuerdan haber jugado. [V] (Un recuento secundario da 17 de 27. [S]) Lectura de diseño: el
  género se aprende como memoria procedimental; un estímulo simple y repetido se graba.

**Lo que dicen los juegos sobre el tacto** (cifras comprobadas en TetrisWiki salvo indicación)

| Sistema | DAS inicial | Repetición (ARR) | Retardo de bloqueo | Entrada (ARE) | Vista previa |
|---|---|---|---|---|---|
| NES Tetris (NTSC) | 16 f | 6 f | — (bloqueo inmediato) | — | 1 |
| TGM1 | 16 f | 1 f [M] | 30 f | 30 f | 1 |
| Guía moderna (recomendado) | 10 f (~167 ms) | 2 f (~33 ms) | 0,5 s con reinicio por movimiento, máx. 15 | 6 f | variable, hasta 6 |

- La guía añade reserva (*hold*, una vez por pieza), pieza fantasma, caída instantánea que bloquea y caída suave que
  no bloquea; IRS e IHS (girar o reservar durante la entrada) son opcionales. [V] En 20G el retardo de bloqueo es
  todo el margen del jugador; TGM1 lo mantiene en 30 f mientras la gravedad sube. [V]

**Qué aplicamos**

- **Legibilidad**: cada celda debe leerse en un vistazo por color y forma; nada de reglas que obliguen a "rotar
  mentalmente" o contar en el tablero (Kirsh). `READ_COST` de `rulespace.py` va en esa línea; mantenerlo y
  validarlo con capturas reales, no sólo con el número.
- **Girar debe ser barato e instantáneo** (respuesta en el mismo fotograma, sin animación que bloquee) y en ambos
  sentidos: el jugador lo usa para pensar.
- **Valores de entrada por defecto para la ROM**: DAS 10–12 f, ARR 2 f (pozo de 6 de ancho: llegar de borde a borde
  cuesta ~20 f), retardo de bloqueo 30 f con reinicio por movimiento limitado a 15, ARE 6–8 f, IRS sí (barato y
  ayuda a altas velocidades), caída suave y caída instantánea. Hoy el versus usa `T_LOCK = 16` y `T_MOVE = 3` sin
  DAS: subir el bloqueo a 30 o justificar por qué 16, y modelar el DAS en el bot humano.
- **Vista previa**: con pares, mostrar **2** (actual + 2) por defecto; el simulador ya pasa 3 piezas al bot en
  solitario. Medir la escalera con 1, 2 y 3 vistas: Böhm sugiere que la vista previa multiplica la fuerza del
  experto; si con 2 la distancia experto-novato se dispara, quizá convenga 1 en el modo fácil.
- **Ayudas legibles**: pieza fantasma siempre; resaltar el grupo que se va a formar al tocar (barato y reduce
  acciones epistémicas).
- Medir en el simulador **piezas por minuto** y **tiempo de decisión disponible frente a usado** (`avail` y `think`
  en `sim.solo`): el *flow* se rompe cuando el disponible cae por debajo del reconocimiento base.

## 4. Flujo, dificultad y curvas de velocidad

**Teoría**

- **Flujo** (Csikszentmihalyi, *Flow: The Psychology of Optimal Experience*, 1990): aparece cuando el reto percibido
  y la habilidad están equilibrados, hay metas claras y retroalimentación inmediata. [S] Una revisión de 2020
  (Frontiers in Psychology) critica que el concepto apenas ha cambiado desde 1975 y se mide de forma inconsistente.
  [S]
- **Jenova Chen**, "Flow in Games (and Everything Else)" (Communications of the ACM 50(4), 2007) y su tesis de máster
  en USC (2006): cada jugador tiene su propia zona de flujo; un juego de experiencia única y estrecha deja fuera a
  novatos y expertos; mejor que el ajuste dinámico pasivo es dar **elecciones integradas en la propia acción** con las
  que el jugador regula su reto sin salir del juego. [V]
- **Análisis de supervivencia** (Isaksen, Gopstein y Nealen, FDG 2015; versión de revista IEEE TCIAIG 2018 con datos
  de más de 100 millones de partidas de una variante de Flappy Bird): la dificultad se describe como **tasa de
  riesgo** (probabilidad de perder en cada punto dado que se ha llegado) y se explora variando parámetros con bots.
  [V]

**Curvas documentadas** [V]

- **NES Tetris** (fotogramas por fila): 48, 43, 38, 33, 28, 23, 18, 13, 8, 6 (niveles 0–9), 5 (10–12), 4 (13–15),
  3 (16–18), 2 (19–28), 1 (29+). Bajada casi lineal de 5 f por nivel hasta el 8 y luego escalones largos.
- **TGM1** (gravedad interna en 1/256 de fila por fotograma; nivel interno 0–999): 4 → 32 en el nivel 70 → 144 en el
  170, **vuelve a 4 en el nivel 200**, sube rápido a 1G en el 251, 2G–5G entre 300 y 400, **baja a 4G y 3G** en 420 y
  450, y **20G desde el 500**. Tiempos constantes: ARE 30, DAS 16, bloqueo 30, borrado de línea 41 f. La curva es en
  dientes de sierra a propósito: descansos antes de cada salto.

**Qué mantiene el modo infinito en flujo**

1. Subidas en escalón con descansos (TGM), no una rampa continua.
2. Al llegar a 20G el reto pasa del tiempo de caída al **retardo de bloqueo y la entrada**: la curva sigue con otra
  variable (TGM2 y siguientes acortan esos tiempos [M]).
3. Recompensa inmediata y escalada: más puntos por borrar a la vez o encadenar a más velocidad (multiplicador de
  nivel), para que arriesgar valga la pena.
4. Recuperación posible: tras un susto hay que poder bajar la pila; las recuperaciones son la parte memorable.

**Qué aplicamos**

- La tabla `SPEED` de `sim.py` es una rampa suave de 48 f a 20G en 16 niveles. Probar una variante en **dientes de
  sierra** (dos o tres bajadas de gravedad tras subidas fuertes) y compararla con `sec_cv`, `danger_frac` y
  `recov_per_min` por perfil. Hipótesis: misma duración media, más recuperaciones y menos muertes súbitas.
- Añadir al modo solitario la **curva de riesgo por nivel** (Isaksen): proporción de partidas que mueren en cada
  nivel entre las que llegan. Una curva sana sube despacio; un pico aislado señala un salto mal calibrado.
- Objetivo por perfil: el novato debe pasar ~3–5 minutos antes de la primera zona de riesgo alto y el experto debe
  llegar a 20G; si el novato muere en el nivel 2–3, la curva empieza demasiado arriba.
- Puntuación que premia el riesgo: `puntos × (nivel + 1)` ya está; añadir bonificación por borrar con la pila alta o
  por cadena hecha con poco margen de tiempo, y medir si el bot experto la persigue (si no cambia su conducta, el
  bono no crea decisión).
- Elección integrada à la Chen: el jugador puede **acelerar** voluntariamente (caída instantánea, subida manual en
  pilas que suben) a cambio de más puntos; es ajuste dinámico que el jugador controla.

## 5. Justicia y azar: generadores

**Generadores comprobados** [V salvo indicación]

- **Sin memoria** (uniforme): permite cualquier racha, incluidas las mortales de Burgiel.
- **NES Tetris**: tira 0–7; si sale el número de la pieza anterior o el 7 vuelve a tirar una vez (0–6). Evita algo
  las repeticiones, pero las sequías siguen siendo largas.
- **TGM1**: historial de 4 piezas, inicializado a Z Z Z Z; hasta 4 intentos para sacar una pieza que no esté en el
  historial; la primera pieza nunca es S, Z ni O. **TGM2**: historial inicial Z Z S S y 6 intentos.
- **TGM3**: bolsa de 35 (5 de cada); al sacar una pieza se devuelve a la bolsa una copia de la menos reciente; según
  la wiki ninguna pieza falta más de 35 seguidas (con errores sutiles documentados aparte).
- **Bolsa de 7** (guía): las 7 piezas barajadas por bolsa. Cota: como mucho 12 piezas entre dos I y como mucho 4 S/Z
  seguidas (TetrisWiki, citado en el estudio).
- **Puyo Puyo Tsu**: tres tablas de 256 puyos (128 pares) según el número de colores, que se repiten; los dos primeros
  pares sólo con 3 colores (Puyo Nexus, citado en el estudio). Que ambos jugadores reciban la misma secuencia **no lo
  he podido verificar** para Tsu; en Puyo Puyo Tetris las secuencias son fijas por modo (*dropsets*). [S]

**Suerte frente a habilidad**

- Una bolsa acota la sequía: el peor caso pasa de "infinito" a un número fijo. Eso convierte la mala suerte en algo
  que el jugador puede planificar (sabe que la pieza vendrá), y por eso es el estándar competitivo.
- Una secuencia **compartida** elimina la diferencia de suerte entre jugadores; sólo queda la suerte de la basura y
  del ritmo. El simulador ya mide la diferencia (`L2>L1_diffseq`); si con secuencias distintas cae poco respecto a la
  compartida, el núcleo es robusto al azar.
- Las primeras piezas importan: TGM y Puyo restringen el inicio para no dar aperturas imposibles.

**Qué aplicamos**

- Para pares de colores: **bolsa** de todos los pares del juego de colores en uso (o de colores individuales en
  múltiplos de 4), barajada con el LCG determinista de `sim.Rng`, y **secuencia compartida** en versus. Medir
  explícitamente la **sequía máxima** de cualquier color y del detonador/llave si existe (la queja de Puzzle Fighter).
- Restringir las dos primeras piezas (pocos colores) como Tsu, para que la apertura siempre tenga algo que hacer.
- Si la basura tiene huecos o colores aleatorios, que salgan de un generador aparte y también compartido, para que
  la misma cadena produzca la misma basura en ambos lados.
- Añadir al simulador una prueba de "supervivencia ante racha adversa": el bot experto contra la peor ventana de N
  piezas que el generador permite. Si muere sin culpa, el generador es injusto.

## 6. Diseño del versus

**Fórmulas de ataque comprobadas** [V]

- **Puyo Tsu**: `puntos = 10 · PC · clamp(CP + CB + GB, 1, 999)` y basura = puntos / 70 con el resto arrastrado
  (Puyo Nexus). Contraataque clásico: tus puntos cancelan primero tu bandeja y el resto va al rival. *All clear*:
  +30 en la siguiente cadena. *Margin time* 96: a partir de ahí el divisor baja y una sola cadena llega a mandar 40 o
  más. Caen como mucho **30 puyos (5 filas) de una vez**; el resto espera (descrito para la familia; no lo vi
  afirmado aparte para Tsu). [S]
- **Guía Tetris** (TetrisWiki, "Garbage"): simple 0, doble 1, triple 2, tetris 4; T-spin simple 2, doble 4, triple 6;
  mini T-spin simple 0, doble 1; *back-to-back* +1 (mini y T-spin simple), +2 (T-spin doble y tetris), +3 (T-spin
  triple); *perfect clear* 10 más lo de la línea. La basura espera en cola, tus líneas la cancelan y el sobrante va al
  rival; entra al soltar una pieza sin borrar. Huecos: en Tetris Worlds dos huecos alineados en 1 de cada 10 filas,
  tres en 1 de 100; en Game Boy la columna cambia cada ~9 filas.
- **Combos** (TetrisWiki, "Combo"), filas extra por combo 1, 2, 3…: Tetris Online 0,1,1,2,2,3,3,4,4,4,5,5 (máx. 5);
  Tetris 99 1,1,2,2,3,3,4,4,4,5,5,5; Puyo Puyo Tetris 2 0,1,1,2,2,3,3,4,4,4,4,4,5.
- **Panel de Pon**: la basura tocada por una eliminación se convierte en paneles normales; combos y cadenas congelan
  la subida (*stop time*) (estudio, [PP1]).

**Principios que repiten las comunidades competitivas** (síntesis; las citas exactas en el estudio)

1. **Crecimiento superlineal con tope por caída**: lo grande debe valer el riesgo (tabla de cadena de Tsu, T-spin,
  combo), pero nadie muere de un solo golpe sin poder responder (tope de 5 filas, cola visible).
2. **Contraataque**: cancelar convierte la partida en intercambio y premia guardar una respuesta. Sin él, gana quien
  dispara primero.
3. **Basura legible y aprovechable** (Panel de Pon, patrones de caída de Puzzle Fighter según Sirlin): la remontada
  es habilidad.
4. **Reloj contra el atrincheramiento**: *margin time* sube el ataque con el tiempo para que esperar no sea la mejor
  estrategia.
5. **Ataque en unidad común** (celdas de basura) para poder comparar sistemas y ajustar con un solo número.
6. **Primer jugador**: con secuencia compartida y salida simultánea no hay turno, pero sí puede haber ventaja de
  asiento por detalles (quién resuelve primero en el mismo fotograma). [M] El simulador la mide (`fair_p1`).
7. **Estancamiento**: si cancelar es gratis y nadie pierde altura, la partida se alarga sin decisiones; el tope por
  caída y el *margin time* lo resuelven. [M]

**Qué aplicamos**

- Medir la **duración** contra 2–4 minutos (`length` en `rulespace.score`, banda 120–240 s) y añadir el **tiempo
  hasta la primera basura** recibida: si es < 20 s, la apertura no deja construir.
- Medir **intercambios**: número de cancelaciones por partida y fracción de ataques grandes que se devuelven. Si casi
  ningún ataque grande se cancela, el versus es una carrera.
- Medir **estancamiento**: tramos de > 30 s sin cambio de líder ni basura caída. Ajustar `MARGIN_T` y `MARGIN_STEP`
  hasta que sean raros.
- Mantener `GARB_CAP` (18 celdas = 3 filas de 6) y comprobarlo contra Tsu (5 filas de 6 = 30): medir si 3 o 5 filas
  dan más remontadas sin alargar demasiado.
- Hacer **visible la cola** de basura pendiente con su tamaño (unidad: fila y celda) y el momento en que caerá.
- Probar **basura convertible** (Panel de Pon) como palanca de remontada y compararla con la basura inerte usando
  `comeback`, `near_death` y `lead_changes`.

## 7. Teoría del diseño de puzles y diseño automatizado

**Autores y obras**

- **Scott Kim**: su definición más citada es que "un puzle es divertido y tiene una respuesta correcta". [S] Kim es
  ponente habitual sobre diseño de puzles en la GDC. [S] Las "ocho fases" de su método y sus diapositivas no las he
  podido leer de primera mano.
- **Jesper Juul**, *A Casual Revolution* (MIT Press, 2009) y *The Art of Failure* (MIT Press, 2013) [V]: el primero
  estudia los juegos casuales y su público ampliado (los puzles de emparejar son su ejemplo central [M]); el segundo
  pregunta por qué seguimos jugando a algo que nos hace fracasar: el fracaso es aceptable cuando el jugador lo vive
  como **suyo** y ve cómo mejorar. [S]
- **Cameron Browne**, tesis *Automatic Generation and Evaluation of Recombination Games* (QUT, 2008; sistema Ludi):
  genera juegos de tablero recombinando reglas, los evalúa con auto-juego y **57 medidas estéticas** y comprueba que
  las medidas correlacionan con las preferencias humanas; de ahí salió *Yavalath*. [V]
- **Ludii** (Piette, Soemers, Stephenson, Sironi, Winands y Browne, ECAI 2020): sistema general de juegos que describe
  cada juego como composición de **ludemas** (conceptos de juego de alto nivel). [V]
- **Smith y Mateas**: "Answer Set Programming for Procedural Content Generation: A Design Space Approach" (IEEE
  TCIAIG 3(3), 2011) y "Variations Forever" (CIG 2010): describir el **espacio de diseño** de forma declarativa y
  "esculpirlo" con restricciones para generar reglas o niveles válidos. [V]
- **Togelius, Yannakakis, Stanley y Browne**, "Search-Based Procedural Content Generation: A Taxonomy and Survey"
  (IEEE TCIAIG 3(3), 2011): generar contenido con búsqueda/evolución; clasifica por qué se genera, cómo se representa
  y **cómo se evalúa** (directa, por simulación o interactiva). [V]
- **Jaffe et al.** (AIIDE 2012), juego restringido para medir equilibrio, e **Isaksen et al.** (FDG 2015),
  supervivencia: ver secciones 2 y 4. [V]

**Lo que nos sirve**

- `rulespace.py` ya es una búsqueda en un espacio de reglas con evaluación por simulación: es SBPCG aplicado a
  reglas, como Ludi. El riesgo conocido de este enfoque es que la búsqueda **explota la medida**: encuentra reglas
  que puntúan bien en las bandas pero que un humano no entiende o no disfruta.
- Browne validó sus medidas contra rankings humanos; nosotros aún no. Las bandas de `score` son hipótesis del
  estudio, no hechos.
- Juul: el fracaso debe tener **causa visible**. En el puzle versus eso significa que el jugador ve la basura venir,
  sabe por qué perdió (no por una racha del generador) y ve la jugada que le habría salvado.
- Kim: la regla tiene que gustar sola, antes del versus y de la piel.

**Qué aplicamos**

- Tratar las medidas como **filtro**, no como juez: de la búsqueda sólo salen candidatos; la decisión final pasa por
  un prototipo en ROM jugado por personas (`make mtest` para que no se rompa, y partida real para el gusto).
- Validar unas pocas medidas contra juicio humano con un experimento pequeño: tres núcleos de puntuación alta, media
  y baja jugados a ciegas; si el orden humano no coincide con `TOTAL`, reajustar los pesos `WGT`.
- Añadir **restricciones duras** al espacio de diseño al estilo Smith y Mateas en vez de penalizaciones blandas:
  legibilidad mínima, sin estados por celda > 2, ataque con tope; así la búsqueda no gasta tiempo en reglas
  inviables.
- Guardar con cada candidato la semilla, la versión de `sim.py` y las medidas brutas, para poder reproducir cualquier
  número de la tabla.

## Resumen: medidas y valores por defecto propuestos

| Tema | Ya en el simulador | Añadir |
|---|---|---|
| Techo de habilidad | escalera L0–L3 | profundidad 3 frente a 2, haz 12 frente a 6; juego restringido |
| Bot humano | `think`, `noise`, `err` | DAS/ARR y giros como coste motor; ruido sólo en las 3 mejores; error de columna según altura |
| Bot fuerte | voraz y búsqueda | término de cadena potencial; pesos por CMA-ES; disparo según rival |
| Lectura | `READ_COST` | validación con capturas; resaltar grupo y pieza fantasma en ROM |
| Solitario | nivel, peligro, recuperaciones, `sec_cv` | curva de riesgo por nivel; variante de gravedad en dientes de sierra |
| Azar | `L2>L1_diffseq` | sequía máxima por color/detonador; prueba de racha adversa |
| Versus | duración, líder, remontadas, ataques grandes | primera basura recibida; cancelaciones; estancamiento > 30 s |
| Validez de la medida | bandas de `score` | prueba a ciegas con personas |

Valores de partida para la ROM (a confirmar con el simulador): DAS 10–12 f, ARR 2 f, bloqueo 30 f con reinicio
limitado a 15, ARE 6–8 f, IRS sí, caída suave y caída instantánea, vista previa 2, pieza fantasma, bolsa de pares y
secuencia compartida en versus, tope de basura de 3–5 filas por caída y cola visible.

## Fuentes

Comprobadas (título, autores, año y enlace):

- E. D. Demaine, S. Hohenberger, D. Liben-Nowell, "Tetris is Hard, Even to Approximate", COCOON 2003, LNCS 2697,
  351–363; arXiv cs/0210020. https://arxiv.org/abs/cs/0210020 · https://erikdemaine.org/papers/Tetris_TR2002/
- MIT Hardness Group, E. D. Demaine, H. Hall, J. Li, "Tetris with Few Piece Types", FUN 2024; arXiv 2404.10712.
  https://erikdemaine.org/papers/TetrisPieces_FUN2024/
- T. Matsukane, Y. Takenaga, "NP-completeness of maximum chain problem on generalized Puyopuyo", IEICE Tech. Rep.
  COMP2004-85, 2005. https://ken.ieice.org/ken/paper/200503186A31/eng/
- T. Walsh, "Candy Crush is NP-hard", arXiv 1403.1911, 2014. https://arxiv.org/abs/1403.1911
- L. Gualà, S. Leucci, E. Natale, "Bejeweled, Candy Crush and other Match-Three Games are (NP-)Hard", IEEE CIG 2014;
  arXiv 1403.5830. https://arxiv.org/abs/1403.5830
- H. Burgiel, "How to Lose at Tetris", The Mathematical Gazette 81(491), 194–200, 1997 (resultado leído en resúmenes).
  https://cs.utexas.edu/~shivaram/readings/b2hd-Burgiel1997.html · https://harddrop.com/wiki/Deadly_piece_sequence
- S. Algorta, Ö. Şimşek, "The Game of Tetris in Machine Learning", arXiv 1905.01652, 2019.
  https://arxiv.org/abs/1905.01652
- C. Thiery, B. Scherrer, "Building Controllers for Tetris", ICGA Journal 32(1), 3–11, 2009.
  https://hal.archives-ouvertes.fr/inria-00418954
- N. Böhm, G. Kókai, S. Mandl, "An Evolutionary Approach to Tetris", MIC 2005 (cifras vía Algorta y Şimşek).
  https://cs.utexas.edu/~shivaram/readings/b2hd-BohmKM2005.html
- K. Ikeda, D. Tomizawa, S. Viennot, Y. Tanaka, "Playing PuyoPuyo: Two Search Algorithms for Constructing Chain and
  Tactical Heuristics", IEEE CIG 2012, 71–78. https://bibtex.github.io/CIG-2012-IkedaTVT.html
- citrus610, "Puyo Puyo AI introduction: Ama AI" (blog), 2024.
  https://citrus61003.blogspot.com/2024/02/puyo-puyo-ai-introduction-ama-ai.html
- D. Kirsh, P. Maglio, "On Distinguishing Epistemic from Pragmatic Action", Cognitive Science 18, 513–549, 1994.
  https://adrenaline.ucsd.edu/kirsh/Articles/CogsciJournal/DistinguishingEpi_prag.pdf
- J. K. Lindstedt, W. D. Gray, "Meta-T: Tetris as an experimental paradigm for cognitive skills research", Behavior
  Research Methods 47(4), 945–965, 2015; "Distinguishing experts from novices by the Mind's Hand and Mind's Eye",
  Cognitive Psychology 109, 1–25, 2019; "The 'cognitive speed-bump'", CogSci 2020.
  https://cognitivesciencesociety.org/cogsci20/papers/0020/index.html
- R. J. Haier et al., "Regional glucose metabolic changes after learning a complex visuospatial/motor task: a PET
  study", Brain Research 570, 134–143, 1992. https://richardhaier.com/articles/learningtetris
- R. Stickgold et al., "Replaying the Game: Hypnagogic Images in Normals and Amnesics", Science 290, 350–353, 2000.
  https://ui.adsabs.harvard.edu/abs/2000Sci...290..350S/abstract
- J. Chen, "Flow in Games (and Everything Else)", Communications of the ACM 50(4), 31–34, 2007.
  https://cacm.acm.org/author/jenova-chen · tesis: https://jenovachen.info/abstract
- A. Isaksen, D. Gopstein, A. Nealen, "Exploring Game Space Using Survival Analysis", FDG 2015.
  https://bibtex.github.io/FDG-2015-IsaksenGN.html
- A. Jaffe, A. Miller, E. Andersen, Y.-E. Liu, A. Karlin, Z. Popović, "Evaluating Competitive Game Balance with
  Restricted Play", AIIDE 2012, 26–31. https://ojs.aaai.org/index.php/AIIDE/article/view/12513
- C. Holmgård, M. C. Green, A. Liapis, J. Togelius, "Automated Playtesting With Procedural Personas Through MCTS With
  Evolved Heuristics", IEEE Transactions on Games 11(4), 352–362, 2019.
  https://www.um.edu.mt/library/oar/handle/123456789/47265
- C. Browne, *Automatic Generation and Evaluation of Recombination Games*, tesis doctoral, QUT, 2008.
  https://eprints.qut.edu.au/17025/
- É. Piette, D. Soemers, M. Stephenson, C. Sironi, M. Winands, C. Browne, "Ludii – The Ludemic General Game System",
  ECAI 2020, 411–418; arXiv 1905.05013. https://arxiv.org/abs/1905.05013
- A. M. Smith, M. Mateas, "Answer Set Programming for Procedural Content Generation: A Design Space Approach", IEEE
  TCIAIG 3(3), 187–200, 2011. https://course.ccs.neu.edu/cs5150f14/readings/smith_asp4pcg.pdf
- J. Togelius, G. N. Yannakakis, K. O. Stanley, C. Browne, "Search-Based Procedural Content Generation: A Taxonomy
  and Survey", IEEE TCIAIG 3(3), 172–186, 2011. https://course.ccs.neu.edu/cs5150f13/readings/togelius_sbpcg.pdf
- J. Juul, *A Casual Revolution* (MIT Press, 2009) y *The Art of Failure* (MIT Press, 2013).
  https://en.wikipedia.org/wiki/Jesper_Juul_(game_researcher)
- TetrisWiki: "Tetris (NES, Nintendo)", "Tetris The Grand Master", "TGM randomizer", "Tetris Guideline", "Garbage",
  "Combo". https://tetris.wiki/
- Puyo Nexus: "Tsu (rule)", "Nuisance queue". https://www.puyonexus.com/wiki/Tsu_(rule) ·
  https://puyonexus.com/wiki/Garbage_queue

Sólo por resumen secundario: M. Csikszentmihalyi, *Flow: The Psychology of Optimal Experience* (1990); S. Kim,
definición de puzle (https://en.wikipedia.org/wiki/Scott_Kim); G. Aloupis et al., "LUMINES Strategies" (LNCS 4630,
2007); Hanson y Moffat, Monte Carlo en Puyo (AISB 50, 2014).
