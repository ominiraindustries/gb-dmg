# 4. Diseño de mundo conectado (metroidvania, tipo Ufouria)

Un mundo conectado es un grafo de zonas con cerraduras y llaves. Las llaves suelen ser habilidades (saltar más,
bucear, escalar), objetos o estados del mundo (agua alta/baja). La gracia está en que el jugador **recuerde** dónde vio
la cerradura y vuelva con la llave.

## El modelo de referencia: Ufouria (NES, 1991)

Mundo libre e interconectado; cuatro personajes intercambiables en cualquier momento: Hebe (con un objeto escala
paredes), O-Chan (nada y anda sobre hielo), Sukezaemon (salta alto), Jennifer/Gil (bucea). Tres de los jefes son los
amigos con amnesia: al vencerlos se unen. Los enemigos dejan proyectiles para lanzar. Se guarda por contraseña.
La crítica alabó el cambio de personaje y la exploración, y le reprochó poca dificultad, jefes fáciles, falta de mapa
en pantalla y de puntos de control. La secuela de 2023 cambia la disposición de zonas ya visitadas al volver con
habilidades nuevas.
Fuentes: https://en.wikipedia.org/wiki/Ufouria:_The_Saga ; https://dsiware.nintendolife.com/reviews/nintendo-switch/ufouria-the-saga-2

*Lección:* lo que hizo memorable a Ufouria (personajes como llaves, mundo único) se conserva; lo que se le criticó
(sin mapa, sin puntos de control, jefes flojos) es lo primero que hay que hacer mejor.

## Cerraduras y llaves

**4.1 Dibuja el grafo de dependencias antes que el mapa.** Nodos = zonas y llaves; aristas = "necesita". Comprueba que
desde el inicio siempre hay al menos una llave alcanzable, que no hay ciclos imposibles y cuántos caminos válidos hay.
*Por qué:* Game Maker's Toolkit (serie *Boss Keys*) analiza Zelda y Super Metroid con estos gráficos; muestran a la vez
lo lineal que es el juego y dónde puede romperse. Fuente: resumen del episodio de Super Metroid,
https://gamedeveloper.com/design/looking-back-at-the-level-design-triumphs-of-i-super-metroid-i-

**4.2 Enseña la cerradura antes que la llave.** El jugador debe toparse con la puerta, el muro o el pozo profundo antes de
conseguir la habilidad; así, al obtenerla, piensa "ya sé dónde usarla". Si la llave llega primero, encontrar la puerta
es casualidad, no un problema resuelto. Al dar la llave, **recuérdale la cerradura** (ventana con vista a ella,
enemigo igual al que bloqueaba el paso). Si una cerradura pide varias llaves, su dibujo lo indica (tres ranuras).
Fuente: The Level Design Book, "Gates" (`docs/ref/diseno/level-design-book-full.md`); en Hollow Knight, tras conseguir
el primer hechizo aparece al momento el mismo tipo de enemigo que bloqueaba un camino (Schütz, "Metroidvania Analysis",
HSLU 2021, sobre el episodio de Boss Keys de Hollow Knight).

**4.3 Que la cerradura se lea a primera vista y sea consistente.** Mismo color, forma o símbolo para la misma llave en
todo el juego (las puertas de colores de Metroid). Hollow Knight pone cristales junto a los sitios donde sirve el
impulso de cristal y flores azules junto a la puerta de vida. *Por qué:* el jugador sólo puede planear si sabe
clasificar los obstáculos. Fuente: Schütz 2021, https://blog.hslu.ch/games/files/2021/11/Metroidvania_Analysis.pdf

**4.4 Haz que cada llave abra varias cosas, cerca y lejos.** La garra de mantis de Hollow Knight abre la zona donde se
consigue y además puertas repartidas por todo el mapa. *Por qué:* una habilidad que sirve en un solo sitio es una llave
con forma de habilidad; una que reinterpreta todo el mapa da la sensación de crecer. Fuente: Schütz 2021.

**4.5 Mezcla cerraduras duras y blandas.** *Dura:* imposible sin la llave. *Blanda:* posible pero cara (enemigos
fuertes, camino difícil, objeto caro), lo que permite variar el orden de las primeras llaves a quien se atreva.
Fuente: Boss Keys sobre Hollow Knight (vía Schütz 2021); The Level Design Book, "Gates".

**4.6 Atrapa al jugador hasta que aprenda lo imprescindible.** Una zona de entrada sin salida hasta conseguir la
habilidad que se encuentra dentro asegura que nadie se la salte (Hollow Knight con la garra de mantis; la sala de
Super Metroid que no te deja salir hasta que aprendes a correr). Fuentes: Schütz 2021;
https://gamedeveloper.com/design/the-invisible-hand-of-super-metroid

## Guiar sin llevar de la mano

**4.7 Espera la cooperación del jugador, pero no dependas de ella.** Super Metroid supone un camino, pero si te
desvías siempre deja una puerta trasera para que acabes viendo lo esencial; las mejoras opcionales repartidas hacen que
un camino "equivocado" casi siempre dé algo. Fuente: "The Invisible Hand of Super Metroid",
https://gamedeveloper.com/design/the-invisible-hand-of-super-metroid

**4.8 Encierra temporalmente en trozos pequeños.** Metroid Dread bloquea muchas veces una porción pequeña del mapa y
corta el paso si vas demasiado lejos en la dirección errónea; Super Metroid limita las primeras visitas a Norfair.
*Por qué:* el jugador no se pierde porque el espacio de búsqueda es pequeño, pero sigue sintiendo que explora.
Fuentes: análisis de Mark Brown "Why You Didn't Get Lost in Metroid Dread" (resumido en
https://tildes.net/~games/z02/why_you_didnt_get_lost_in_metroid_dread); "The Invisible Hand of Super Metroid".

**4.9 Usa caminos de un solo sentido y puertas que se abren desde el otro lado.** Un desnivel que sólo se baja, una
palanca visible tras una reja: el jugador ve el atajo antes de poder usarlo y lo abre al llegar por detrás. Diseña la
palanca parecida a la puerta para asociarlas. Fuentes: Schütz 2021; The Level Design Book, "Gates" (shortcuts).

**4.10 Luz, música y señales para el camino principal.** En Hollow Knight, tras el primer jefe un camino tiene antorchas
y el otro vuelve a zona conocida: casi todos siguen las antorchas. Super Metroid cambia la música al salir al exterior y
pone salas de guardado antes de los peligros grandes (anuncian lo que viene). Usa el aviso más sutil que funcione y
añade más sólo donde el playtest muestre gente perdida. Fuentes: Schütz 2021; "The Invisible Hand of Super Metroid";
The Level Design Book, "Wayfinding".

## Cambios de estado del mundo (agua, interruptores, eventos)

**4.11 Un estado global debe ser visible, reversible o claramente permanente, y comprobable.** El Templo del Agua de
Ocarina of Time es el ejemplo clásico: la idea (subir y bajar el agua para abrir caminos) es buena, pero la disposición
confusa, no saber qué nivel de agua hace falta y el coste de cambiarlo lo convirtieron en el nivel más odiado; Aonuma
pidió disculpas y la versión 3DS añadió marcas de color que señalan dónde cambiar el nivel. Reglas que se derivan:
- El jugador debe ver el estado actual y saber dónde se cambia (indicador en el sitio, marca en el mapa).
- Cada cambio debe abrir algo visible cerca; si no, parece que no ha pasado nada.
- Si es reversible, el control debe estar cerca de donde se necesita; si es permanente, avisa antes y comprueba que
  ningún estado deja el mundo sin salida.
- No combines un estado global con un laberinto opaco: uno de los dos debe ser sencillo.
Fuentes: https://en.wikipedia.org/wiki/Water_Temple_(Ocarina_of_Time) ;
https://zeldauniverse.net/features/why-we-hate-the-water-temple-and-every-other-aquatic-dungeon/

**4.12 Prueba todos los estados contra el grafo.** Con N interruptores binarios hay 2^N mundos posibles. El validador
de niveles debe recorrer el grafo en cada combinación alcanzable y demostrar que ninguna deja al jugador sin camino de
vuelta (bloqueo sin salida, *softlock*). En este repo: skill `gb-game-design` y el lint de niveles (`harness/levels.py`, `harness/physics.py`) (sin saltos imposibles, puertas
bloqueadas ni softlocks).

## Volver atrás (backtracking)

**4.13 Volver debe dar algo nuevo.** Al volver con una habilidad, el sitio conocido cambia de sentido: rutas nuevas,
enemigos que ahora se vencen, secretos que antes no se alcanzaban, o una disposición distinta (Ufouria 2). Super Metroid
hace que el primer túnel se recorra en ambos sentidos y que el regreso, vertical, se sienta distinto.
*Por qué:* repetir un camino idéntico sin novedad es el principal riesgo del género. Fuentes: "The Invisible Hand of
Super Metroid"; reseña de Ufouria 2 citada arriba; The Level Design Book, "Typology" (un *hub* que no cambia entre
visitas se siente como retroceso).

**4.14 Atajos que se abren al avanzar.** Cada zona grande, al terminarla, abre un atajo de vuelta al núcleo (ascensor,
puerta de un sentido, tubería). *Por qué:* el mundo crece sin que crezca el tiempo de viaje. Cuidado con los atajos
demasiado convenientes, que parecen artificiales. Fuente: The Level Design Book, "Typology" (loopback) y "Gates".

**4.15 Salas de guardado, recarga y mapa con criterio.** Guardado antes de un jefe o de una zona peligrosa (y como
aviso de que viene algo); sala de mapa que revela la zona y el sitio del jefe (Super Metroid marca la guarida de Kraid);
en Hollow Knight el mapa se compra y se actualiza al descansar en un banco. Fuentes: "The Invisible Hand of Super
Metroid"; Schütz 2021.

**4.16 El mapa debe dejar ver lo que falta.** Habitaciones sin explorar, puertas sin abrir y símbolos de cerradura en el
mapa convierten el recuerdo del jugador en una lista de tareas. No todo secreto tiene que salir en el mapa (así hay
motivo para volver), pero las cerraduras del camino principal sí. Fuente: Schütz 2021 (mapa y símbolos de Hollow
Knight).

**4.17 Puntos sin retorno: avisa y comprueba.** Un pozo de una vía que cierra el mundo superior centra la atención,
pero no debe dejar fuera nada imprescindible ni coleccionables sin otra vía. Fuente: "The Invisible Hand of Super
Metroid" (pozo de Super Metroid).

**4.18 Romper la secuencia es un regalo para el experto si no rompe el juego.** Permite que un jugador hábil consiga una
llave antes de tiempo (salto difícil, cerradura blanda), pero comprueba con el grafo que cualquier orden sigue teniendo
salida. Fuente: The Level Design Book, "Gates" (soft gates); análisis de Dread arriba.

## Adaptación Game Boy (DMG)

- La memoria del estado del mundo (habilidades, puertas abiertas, salas visitadas) cabe en un puñado de bytes de SRAM;
  diséñala como un vector de bits desde el principio (`gbe_flags`) y versiona su formato (`gbe_save` guarda versión,
  secuencia y suma de control).
- Un mapa de pantalla completa es una pantalla aparte (el fondo es uno solo) o la ventana: decide pronto y cuenta sus
  teselas en los 384 de VRAM.
- Las salas tipo "pantalla" simplifican cámara y carga; el mundo continuo con scroll en 4 direcciones está hecho en
  `gbe_world` (sectores de 16x16, peor frame ~10k T medido en world_lab).

## Antipatrones

- Habilidad que sólo abre una puerta.
- Puerta cerrada sin señal que diga qué llave pide.
- Volver por el mismo pasillo vacío tres veces.
- Estado global invisible (no se sabe si el agua está alta o baja hasta probar).
- Mundo enorme sin mapa ni puntos de control (la crítica a Ufouria).
- Softlocks: quedarse en un sitio sin habilidad para salir y sin forma de morir o volver.
