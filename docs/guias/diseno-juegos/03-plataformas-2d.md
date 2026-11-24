# 3. Patrones de niveles de plataformas 2D

## Vocabulario (Smith, Cha y Whitehead, 2008)

Un nivel de plataformas se descompone en cinco tipos de pieza:

| Pieza | Qué es | Ejemplo |
|---|---|---|
| Plataforma | Donde se pisa sin daño; tiene tamaño, pendiente, fricción, movimiento, duración | suelo, bloque, plataforma que cae |
| Obstáculo | Lo que hace daño; los huecos cuentan como obstáculo | enemigo, pinchos, foso |
| Ayuda de movimiento | Ayuda a desplazarse mientras se usa, sin cambiar al personaje | muelle, cuerda, escalera, corriente |
| Coleccionable | Recompensa | moneda, vida, mejora, montura |
| Disparador | Cambia el estado del nivel | interruptor P, botón que activa plataformas, **grifo que inunda** |

Estructura: el nivel se divide en **celdas** (tramos lineales) unidas por **portales** (puntos donde se puede elegir
otro camino: tubería, plataforma que sube a otro piso). Cada celda se compone de **grupos rítmicos**: tramos cortos de
reto con principio, desarrollo y final, como una frase musical. Entre grupos hay una pausa: un sitio seguro para
respirar, buen lugar para punto de control o recompensa.

*Por qué sirve:* obliga a pensar el nivel como una secuencia de frases con silencios, no como un pasillo de obstáculos.
Los periodos largos de acción sin pausa multiplican los errores; un grupo corto y arrítmico es difícil de dominar; uno
largo y regular empieza fácil pero exige concentración sostenida.
Fuente: Smith, Cha y Whitehead, "A Framework for Analysis of 2D Platformer Levels" (Sandbox 2008),
https://expressiveintelligence.github.io/papers/smith-sandbox-08.pdf ; y Smith et al., "Rhythm-Based Level Generation
for 2D Platformers" (FDG 2009), https://expressiveintelligence.github.io/papers/smith-fdg-09.pdf

## Principios

**3.1 Las recompensas guían y compensan el riesgo.** Una fila de monedas en arco enseña el salto óptimo; un plátano en
flecha señala el pasadizo oculto; la moneda grande sobre la plataforma que se hunde paga el riesgo; el bloque de objeto
garantiza algo aunque falles. Fuente: Smith et al. 2008 (ejemplos de Super Mario World y Donkey Kong Country 2).

**3.2 Da una segunda oportunidad dentro del nivel.** En Emerald Hill (Sonic 2), quien no tiene velocidad para el
tirabuzón cae a un camino inferior con un escudo de premio en lugar de morir. *Por qué:* el fallo cambia el camino, no
castiga; el jugador incluso puede elegirlo. Fuente: Smith et al. 2008, análisis de Emerald Hill.

**3.3 Antepieza antes del reto.** Pon una versión pequeña y segura del reto justo antes del reto real (el foso con un
muro a cada lado en la intro de Mega Man X invita a probar el salto de pared sin riesgo).
Fuente: "Another Approach for Teaching Gameplay — Antepieces, Challenges, and Megaman X",
https://medium.com/cores-of-game-design/another-approach-for-teaching-gameplay-antepieces-challenges-and-megaman-x-55c88e13443e

**3.4 Primero el primer enemigo trivial.** Miyamoto cambió el Koopa por el Goomba como primer enemigo porque el Koopa
(saltar y luego patear) era demasiado para los cinco primeros segundos; el champiñón aparece de forma que cueste
esquivarlo (tubería delante, cae desde arriba). *Por qué:* el primer encuentro enseña una sola regla.
Fuente: entrevista de Eurogamer (2015), resumida en
https://www.avclub.com/shigeru-miyamoto-explains-the-making-of-super-mario-bro-1798284041

**3.5 Patrones reutilizables.** Dahlskog y Togelius catalogaron patrones de Super Mario Bros. (enemigo suelto, grupo de
enemigos, hueco, varios huecos, valle, escalera, caminos múltiples...) en tres escalas: *micro* (una columna),
*meso* (un patrón reconocible) y *macro* (una secuencia de patrones). *Por qué:* nombrar los patrones permite medir su
frecuencia y variarlos a propósito. Fuente: "Procedural Content Generation Using Patterns as Objectives" (2014),
https://www.academia.edu/79715544/Procedural_Content_Generation_Using_Patterns_as_Objectives

**3.6 El nivel encaja con el repertorio de movimiento.** Ningún hueco obligatorio mayor que el salto; los movimientos
avanzados abren rutas opcionales y luego se vuelven estándar. Fuente: Josh Bycer, "The Art of the Platformer",
https://www.gamedeveloper.com/design/the-art-of-the-platformer

**3.7 Bajar es fácil, subir cuesta.** La caída de un solo sentido cierra lo anterior ("lo de atrás ya no importa") y
fuerza a avanzar; la subida necesita espacio para escaleras, muelles o paredes. Usa la vertical para dar sensación de
progreso (subir a la torre, bajar a la cisterna). Limita a unos tres "pisos" visibles por zona.
Fuente: The Level Design Book, "Verticality".

**3.8 Secciones de vuelo y de buceo son otro juego: dales su propio método.** Al cambiar la física (agua, vuelo) cambian
todas las métricas: velocidad, inercia, alcance. Presenta el medio en un estanque seguro, mide de nuevo los huecos y
diseña sus propios grupos rítmicos (corrientes, zonas sin aire, techos). *Por qué:* las salas pensadas para el salto
pierden su sentido con otra física; el agua mal medida es la causa más citada de odio a los niveles acuáticos.
Fuente: crítica al Templo del Agua de Ocarina of Time, https://zeldauniverse.net/features/why-we-hate-the-water-temple-and-every-other-aquatic-dungeon/

## Adaptación Game Boy (DMG)

- 160 px de ancho son 10 teselas de 16 px; con la cámara adelantada (cap. 7) el jugador ve unas 6 teselas delante. Un
  grupo rítmico tiene que caber en pantalla: los grupos son más cortos que en una consola de 256 px.
- Límite de 10 sprites por línea (8 px de ancho cada uno): un personaje de 16 px son 2 sprites, así que 5 objetos en
  la misma horizontal ya llenan la línea. Reparte en altura y usa la rotación de gbe_spr (`docs/tecnicas/sprites.md`).
- Sin color: plataformas, peligros y fondo se distinguen por tono y forma; el fondo en el tono 0-1, lo sólido con borde
  oscuro, los peligros con el contraste más alto.

## Antipatrones

- Saltos de fe: un hueco donde no se ve si debajo hay suelo o muerte (cap. 9).
- Huecos "imposibles por un píxel" en el camino obligatorio.
- Plataformas idénticas repetidas sin variación de ritmo.
- Pinchos o enemigos justo en el punto de aterrizaje que no se ve antes de saltar.
