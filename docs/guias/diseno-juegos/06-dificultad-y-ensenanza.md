# 6. Dificultad, ritmo y enseñar sin tutoriales

## Dificultad y flujo

**6.1 Mantén al jugador en la franja de flujo.** Csikszentmihalyi describe el flujo como el estado en que el reto
encaja con la habilidad: por encima aparece ansiedad, por debajo aburrimiento. La habilidad crece al jugar, así que el
reto debe crecer con ella, en dientes de sierra (subida, descanso, subida mayor) y no en línea recta. Jenova Chen
propone que la mejor forma de ajustarlo es dar al jugador elecciones que regulen su propia dificultad, en lugar de
que el juego la ajuste a escondidas. Fuente: Jenova Chen, *Flow in Games* (tesis USC, 2006), resumen en
https://jenovachen.info/abstract

**6.2 Dificultad invisible: tres "tuberías".** Los Mario ofrecen un camino normal, uno más fácil y uno más difícil, y el
jugador cambia entre ellos jugando: arriba, monedas difíciles, vidas en sitios arriesgados, salidas secretas y mundos
extra; abajo, niveles saltables, personajes más fáciles y ayudas tras morir muchas veces. Las ayudas aparecen sólo
cuando hacen falta y suelen dar menos premio; el premio por habilidad suele ser más reto. Miyamoto: lo mejor es que el
jugador ajuste la dificultad él mismo mientras juega.
Fuente: Mark Brown, "Super Mario's Invisible Difficulty Settings", https://gmtk.substack.com/p/super-marios-invisible-difficulty

**6.3 En un metroidvania, lo opcional regula la dificultad.** Contenedores de vida y mejoras escondidos hacen más fácil
el camino principal a quien explora; los secretos difíciles dan reto a quien lo busca. Celeste lo hace con las fresas
(opcionales, a menudo fuera del camino) y las caras B, y el modo asistencia va en la otra dirección.
Fuentes: https://filmstories.co.uk/features/the-new-normal-the-indie-developers-changing-our-conceptions-of-difficulty/ ;
https://en.wikipedia.org/wiki/Celeste_(video_game)

**6.4 El coste del fallo es parte de la dificultad.** Morir y repetir 5 s es muy distinto de repetir 3 min. Ajusta antes
la distancia entre puntos de control que la dureza del reto. *Por qué:* lo que frustra no suele ser el obstáculo sino
repetir lo ya superado. Celeste reaparece al principio de cada pantalla.

**6.5 Descansos entre picos.** Tras un tramo intenso, una zona tranquila (sala de guardado, tienda, paisaje) deja
recuperar y hace que el siguiente pico se note. El final no tiene por qué ser lo más difícil del juego.
Fuente: The Level Design Book, "Pacing".

## Enseñar jugando

**6.6 Una regla a la vez, en un sitio seguro.** El primer enemigo de Super Mario Bros. sólo pide saltar encima; el
champiñón está colocado para que cueste esquivarlo; más adelante dos huecos preparan la carrera con B.
Fuente: Miyamoto y Tezuka (Eurogamer 2015), resumido en https://www.avclub.com/shigeru-miyamoto-explains-the-making-of-super-mario-bro-1798284041

**6.7 Diseña el espacio para que la acción correcta sea la natural.** Un foso con dos paredes cerca invita al salto de
pared; un objeto visible tras un muro invita a probar (intro de Mega Man X). Una fila de bloques raros y un suelo
desconectado invitan a usar la bomba (Super Metroid). Fuentes: https://medium.com/cores-of-game-design/another-approach-for-teaching-gameplay-antepieces-challenges-and-megaman-x-55c88e13443e ;
https://gamedeveloper.com/design/the-invisible-hand-of-super-metroid

**6.8 Muestra la habilidad nueva justo después de darla.** Tras conseguir una habilidad, la primera sala debe necesitarla
y ser segura; luego una prueba real. Hollow Knight pone obstáculos que sólo se superan con el *dash* recién obtenido; al
salir con el traje de gravedad en Super Metroid el agua deja de frenar (la lección es el alivio).
Fuentes: Schütz 2021, https://blog.hslu.ch/games/files/2021/11/Metroidvania_Analysis.pdf ; "The Invisible Hand of Super Metroid".

**6.9 Presentar → desarrollar → girar → cerrar** para cada mecánica (cap. 2). Separa los giros en el tiempo para
comprobar que el jugador recuerda la habilidad, no sólo que la repite.

**6.10 Texto, sólo si el espacio no basta.** Si hace falta un cartel, que sea corto, en el sitio y con la fuente de la
biblioteca (`jtext`/`vwf`). Un tutorial largo antes de jugar se olvida.

## Antipatrones

- Pico de dificultad sin preparación (el jefe exige algo que se enseñó hace una hora y nunca se practicó).
- Línea recta de dificultad sin descansos.
- Castigar la exploración (secretos que matan sin aviso).
- Ayudas que humillan ("modo trampa"; Thorson cambió el nombre a "modo asistencia" porque sonaba a juicio,
  https://www.vice.com/en/article/celeste-difficulty-assist-mode).
- Puntos de control tan lejos que el jugador repite tramos fáciles para llegar al difícil.
