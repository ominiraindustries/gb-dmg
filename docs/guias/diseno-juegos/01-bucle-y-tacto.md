# 1. Bucle principal y tacto (game feel)

Antes de diseñar niveles hay que tener un verbo que guste por sí solo. Un nivel bueno no salva un salto que se siente
mal; un salto que se siente bien hace que hasta un pasillo vacío sea agradable.

## Principios

**1.1 Define el bucle en una frase y en números.** Qué hace el jugador cada segundo (moverse, saltar, lanzar), cada
minuto (superar una sala, abrir una puerta) y cada hora (conseguir una habilidad, cambiar el mundo). *Por qué:* cada
escala alimenta a la siguiente; si la de un segundo es aburrida, las otras no la compensan. Las cifras (velocidad,
altura de salto, ventanas en fotogramas) son las que luego usa el generador o el validador del nivel.
Fuente: Dan Cook, "The Chemistry of Game Design" (átomos de habilidad: acción → simulación → respuesta → modelo mental
del jugador; los átomos se encadenan y una cadena rota deja sin sentido lo que depende de ella),
https://www.gamedeveloper.com/pc/feature-the-chemistry-of-game-design-

**1.2 El tacto es control en tiempo real + espacio simulado + pulido.** Steve Swink lo define como control continuo de
un objeto en un espacio, con las interacciones realzadas por el pulido (animación, sonido, partículas, sacudida). Sus
piezas: entrada, respuesta, contexto (el nivel da sentido al movimiento), pulido, metáfora y reglas. *Por qué:* el
contexto es parte del tacto; un salto sólo se aprecia con huecos y plataformas medidos para él.
Fuente: Steve Swink, *Game Feel* (libro, de pago); definición resumida en https://en.wikipedia.org/wiki/Game_feel

**1.3 Perdona en favor del jugador, sin que se note.** Las técnicas que Maddy Thorson describe para Celeste:
- *Tiempo de coyote:* se puede saltar unos fotogramas después de dejar el borde.
- *Búfer de salto:* un salto pulsado justo antes de aterrizar sale en el primer fotograma en el suelo.
- *Gravedad reducida en el vértice* mientras se mantiene el botón: da tiempo a corregir el aterrizaje.
- *Corrección de esquinas:* si la cabeza roza una esquina, se desplaza al personaje para que pase.
- *Ventana amplia de salto de pared* (2 px en 320×180, ≈ ¼ de tesela) y más amplia aún para el movimiento más exigente.
- *Conservación del impulso de plataformas* durante unos fotogramas después de que se paren.
*Por qué:* la entrada humana llega unos fotogramas tarde o temprano; si el juego exige el fotograma exacto, el jugador
siente que el juego le roba. Celeste es muy difícil y aun así se percibe amable porque "quiere que ganes".
Fuente: Maddy Thorson, "Celeste & Forgiveness", https://maddymakesgames.com/articles/celeste_and_forgiveness/

**1.4 Cada acción tiene respuesta visible y audible en el mismo fotograma o el siguiente.** Un golpe sin sonido, sin
parpadeo o sin retroceso parece que no ha ocurrido. *Por qué:* la respuesta cierra el átomo de habilidad (1.1); sin ella
el jugador no aprende.

**1.5 Las habilidades extra no deben trivializar el reto.** Doble salto, planeo o vuelo infinitos borran el nivel
diseñado para el salto básico. Limítalos (combustible, una carga por salto, zonas) y diseña salas que los necesiten.
Fuente: Josh Bycer, "The Art of the Platformer", https://www.gamedeveloper.com/design/the-art-of-the-platformer

**1.6 Mira el diseño con varias "lentes".** Jesse Schell propone hacerse preguntas sistemáticas desde perspectivas
distintas: experiencia esencial (¿qué debe sentir el jugador y qué parte del juego lo produce?), sorpresa, diversión,
curiosidad, desafío, recompensa, elección significativa, castigo, simplicidad/complejidad, elegancia, etc. *Por qué:*
cada lente destapa un problema distinto; usarlas como lista evita diseñar sólo desde lo que ya gusta al diseñador.
Fuente: Jesse Schell, *The Art of Game Design: A Book of Lenses* (libro y baraja de lentes, de pago; no se descarga).

## Adaptación Game Boy (DMG)

- Mide en fotogramas a 59,73 Hz y en píxeles de 160×144: una tesela de 16 px es 1/10 de la anchura de pantalla, el
  doble de grande en proporción que en SNES. Todo se ve más cerca y llega antes: las velocidades "de SNES" son rápidas aquí.
- Las ventanas de perdón (coyote, búfer) son de pocos fotogramas; anótalas como constantes del juego, mide la física
  real con `python -I harness/physics.py --game <juego>` y pruébalas con entrada reproducible (`gb.hold`, `gbrun --input`).
- El pulido barato en DMG: cambio de `BGP`/`OBP` (parpadeo de daño, destello), sacudida con `shake_x/y` de gbe_video,
  SFX con prioridad de canal (gbe_sfx). Sin color, la lectura depende de contraste y silueta: 4 tonos.

## Antipatrones

- Ajustar niveles antes de cerrar la física: cada cambio de salto rompe todos los huecos.
- Exigir precisión de fotograma exacto sin ventanas de perdón.
- Control en el aire nulo o diferido sin que sea una decisión de diseño (los juegos antiguos sin control aéreo son duros
  por eso, no por el nivel).
- Respuestas retardadas (animación de anticipación larga) en el verbo principal del jugador.
