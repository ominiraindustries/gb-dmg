# 5. Enemigos y jefes

## Enemigos

**5.1 Cada enemigo es una pregunta distinta.** Un enemigo debe pedir una respuesta concreta (saltar por encima, esperar
a que se gire, golpear desde abajo, mantener distancia). Si dos enemigos se resuelven igual, sobra uno.
Fuente: The Level Design Book, "Enemy design" (diversidad, jerarquía, longevidad, emergencia, consistencia).

**5.2 Haz una tabla del reparto.** Columnas mínimas: vida, velocidad, daño, alcance/comportamiento, tamaño y "qué le
enseña al jugador". *Por qué:* deja ver huecos (no hay ningún enemigo a distancia media) y redundancias. Combina tipos:
un enemigo cercano solo no hace que el terreno importe; uno que dispara de lejos convierte cada repisa y cada cobertura
en una decisión. Fuente: The Level Design Book, "Enemy design", con la cita de Mike Stout (GDC 2012, Skylanders).

**5.3 Silueta y color legibles a distancia.** El tipo de enemigo debe reconocerse por silueta y paleta antes de que sea
peligroso; su estado (alerta, a punto de atacar, vulnerable) debe verse en la animación. Fuente: The Level Design Book,
"Enemy design" (con la referencia de Valve, "How Valve Connects Art Direction to Gameplay").

**5.4 Avisa antes de golpear: anticipación → ataque → recuperación.** Un ataque es justo si antes hubo un aviso que el
jugador pudo percibir (pose, destello, sonido); entonces el fallo es suyo. La recuperación tras el ataque es la ventana
para castigarlo. Combina canales (animación + sonido + efecto) para que se lea aunque no se mire al enemigo. El aviso es
más largo cuanto más daño hace el ataque. Fuente: "Enemy Attacks and Telegraphing",
https://gamedeveloper.com/design/enemy-attacks-and-telegraphing

**5.5 Enemigos que enseñan.** En Super Metroid unas criaturas muestran el salto de pared y otra el salto con carrerilla;
un insecto que antes era amenaza vuelve como plataforma al congelarlo. *Por qué:* el enemigo enseña sin texto y se
reaprovecha. Fuente: "The Invisible Hand of Super Metroid", https://gamedeveloper.com/design/the-invisible-hand-of-super-metroid

**5.6 Nada aparece sin que se pueda ver.** Ningún enemigo nace dentro de la pantalla encima del jugador ni dispara desde
fuera de la vista. Aparecer por detrás es especialmente injusto si el personaje tarda en girarse. Fuente: The Level
Design Book, "Verticality" (backspawning).

**5.7 Afina con cambios grandes.** En las primeras pasadas no cambies la vida de 100 a 115: prueba 200; si es mucho,
ya tienes el intervalo. *Por qué:* los cambios pequeños no se notan en una prueba y hacen perder iteraciones.
Fuente: The Level Design Book, "Enemy design".

## Jefes

**5.8 Un jefe es un examen de lo aprendido.** Debe pedir las habilidades que el juego acaba de enseñar (en un
metroidvania, la llave de la zona). *Por qué:* recompensa haber aprendido y confirma que la habilidad se domina.
Fuente: Mike Stout, "Boss Battle Design and Structure" (2010), https://www.gamedeveloper.com/design/boss-battle-design-and-structure

**5.9 Ocho tiempos de un combate de jefe** (Stout):
1. *Preparación:* se anuncia y se enseña lo necesario antes.
2. *Presentación:* entrada con fuerza.
3. *Lo normal:* ataques básicos; lo nuevo se enseña aquí, con el jugador a salvo.
4. *Escalada:* ataques y complicaciones nuevas.
5. *Mitad:* giro emocional (falsa derrota, transformación) y un respiro.
6. *A tope:* todo el repertorio, máxima presión.
7. *Derrota:* se muestra claramente que ha caído.
8. *Victoria:* premio, progreso, celebración.

**5.10 Fases que cambian algo, no sólo la vida.** Cada fase añade un ataque, un peligro del escenario o cambia el punto
débil; la transición se señala claramente. Fuente: Stout 2010 (escalada de Ganon y GLaDOS).

**5.11 El jefe se defiende.** Si el jugador puede golpearlo en bucle sin que ataque, el combate se rompe: dale escudos,
retiradas o un empujón. Fuente: Stout 2010.

**5.12 No enseñes nada nuevo bajo amenaza** y no dejes que el jefe escape antes del momento de victoria. Fuente:
Stout 2010.

**5.13 Ventanas de vulnerabilidad claras.** Punto débil visible, momentos breves para atacar y fases de supervivencia
entre ellos. Fuente: "Game Design Deep Dive: One-hit kills in Titan Souls" (Game Developer),
https://gamedeveloper.com/design/game-design-deep-dive-one-hit-kills-in-i-titan-souls-i-

**5.14 Patrones aprendibles; la variación, dentro de reglas.** Cuphead elige ataques al azar dentro de cada fase pero
cada ataque se lee igual siempre, y al morir muestra cuánto faltaba para ganar (ganas de reintentar). Fuente: Game
Maker's Toolkit, "How Cuphead's Bosses (Try to) Kill You" (vídeo; no consultado su texto completo).

**5.15 Reintentar debe ser rápido.** Punto de control a la puerta del jefe; sin largas escenas ni recorridos antes de
volver a intentarlo. Sakamoto (Metroid Dread) buscó que tras un *game over* el jugador sepa qué probar en el siguiente
intento. Fuente: https://mynintendonews.com/2022/01/23/metroid-dread-producer-yoshio-sakamoto-discussed-the-games-difficulty/

**5.16 El escenario del jefe es parte del diseño.** Itera la arena mientras prototipas el jefe: plataformas, altura,
huecos de huida. Fuente: The Level Design Book, "Enemy design" (boss design).

## Adaptación Game Boy (DMG)

- Los jefes grandes suelen ir en el fondo (o la ventana) para ahorrar sprites: se mueven con SCX/SCY y el resto del
  decorado se queda quieto con un corte de raster (`docs/tecnicas/fondos-y-raster.md`). Diseña sus ataques sabiendo
  qué parte es fondo (se mueve entera) y qué parte son sprites.
- 10 sprites por línea y 40 en total: los proyectiles del jefe y del jugador comparten la línea; un patrón de "lluvia"
  hace parpadear sprites. Diseña patrones en diagonal o en columnas, no en filas.

## Antipatrones

- Esponjas de vida: más vida y más daño en lugar de comportamiento nuevo.
- Ataques sin aviso o con aviso invisible (fuera de pantalla, tapado por otro sprite).
- Jefe que exige una habilidad que el juego nunca enseñó.
- Recorrido largo desde el punto de control hasta el jefe.
- Combate tan fácil que no se nota que ha empezado (crítica a los jefes de Ufouria).
