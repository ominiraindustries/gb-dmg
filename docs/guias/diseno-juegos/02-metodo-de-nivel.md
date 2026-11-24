# 2. Método para hacer un nivel

Un nivel se diseña en capas: idea → recorrido → bloque jugable → prueba → arte. Cada capa es barata de cambiar sólo
mientras no se ha construido la siguiente.

## Proceso

**2.1 Una idea central por nivel (el *parti*).** Resume el nivel en una frase ("la sala se inunda y hay que subir antes
que el agua"). *Por qué:* da coherencia, sirve para decidir qué sobra y permite explicar el nivel a otro agente.
Fuente: The Level Design Book, "Parti" (`docs/ref/diseno/level-design-book-full.md`, sección `# Parti`).

**2.2 Presentar → desarrollar → giro → cierre (kishōtenketsu).** El método que Koichi Hayashida aplicó en Super Mario
3D Land/World, inspirado en la estructura de las tiras de cuatro viñetas:
1. *Presentar* la mecánica en un sitio seguro, donde fallar no cuesta.
2. *Desarrollarla:* más exigente, combinada con algo ya conocido.
3. *Girarla:* usarla de una forma inesperada (otro ángulo, al revés, con presión de tiempo).
4. *Cerrar:* una última prueba breve o la recompensa, y se pasa a otra idea.
*Por qué:* enseña jugando, sin texto, y retira la idea antes de que canse. En 3D World cabe en unos cinco minutos.
Fuente: análisis de Mark Brown (Game Maker's Toolkit) recogido en
https://www.engadget.com/2015/03/17/super-mario-3d-world-design/ y entrevista de Hayashida a Gamasutra (resumen en
https://en.wikipedia.org/wiki/Koichi_Hayashida). Variante occidental: *enseñar, probar, girar* (The Level Design Book,
"Pacing"), que añade separar los giros para comprobar que el jugador recuerda la habilidad.

**2.3 Marca el camino crítico y los ritmos.** Dibuja inicio, salida, los *beats* numerados y la ruta. *Por qué:* el
camino crítico es lo que ve todo jugador; lo que queda fuera lo ve una minoría y debe justificar su coste (en Game Boy,
también su coste en VRAM/ROM). Fuente: The Level Design Book, "Critical path".

**2.4 Fija las métricas antes de dibujar.** Altura y longitud de salto, anchura del personaje, alcance del ataque,
velocidad de caída. Con ellas define medidas estándar: hueco "fácil", "justo" e "imposible"; pared escalable; altura
de techo mínima. *Por qué:* las medidas coherentes hacen el espacio legible y evitan rediseñar después del arte.
Fuente: The Level Design Book, "Metrics". En este repo: skill `gb-game-design` y el lint de niveles (`harness/levels.py`, `harness/physics.py`) (deriva la envolvente de las
constantes reales y la valida con aserciones).

**2.5 Bloque gris primero, arte después.** Prueba el nivel con teselas de marcador y la física final. *Por qué:* cambiar
un bloque cuesta minutos; cambiar arte terminado cuesta días y créditos de PixelLab.

**2.6 Ritmo de intensidad: alterna picos y descansos.** Empieza tranquilo, alterna, pon descanso como recompensa tras
un pico, y no hagas que el final sea el momento más duro del juego: el clímax necesita una resolución que se sienta
merecida. Usa repetición (motivo), acento, silencio y variación como en música.
Fuente: The Level Design Book, "Pacing".

**2.7 Haz primero un "montón de beats".** Prototipa muchas situaciones sueltas (una sala, un enemigo, un artilugio),
pruébalas y monta el nivel con las mejores. *Por qué:* lo que funciona se descubre jugando, no en el papel.
Fuente: The Level Design Book, "Pacing".

**2.8 Una pieza memorable por zona.** Cada zona necesita al menos un momento que el jugador cuente después (la sala que
se inunda, la huida, la revelación del jefe). Debe caber en el presupuesto y entusiasmar al equipo.
Fuente: The Level Design Book, "Pacing" (set pieces).

## Orden de construcción que funciona

Miyamoto y Tezuka contaron que en Super Mario Bros. hicieron 2-1 y 2-2 antes que 1-1: el primer nivel se diseña al
final, cuando ya se sabe qué tiene que enseñar. Fuente: entrevista de Eurogamer (2015), resumida en
https://www.avclub.com/shigeru-miyamoto-explains-the-making-of-super-mario-bro-1798284041

## Antipatrones

- Empezar por el arte o por el mapa completo sin haber probado una sola sala.
- Meter cinco ideas nuevas en un nivel: ninguna se desarrolla.
- Ideas que sólo aparecen una vez sin giro ni cierre (se olvidan) o que se repiten idénticas veinte veces (cansan).
- Diseñar el nivel 1 primero.
- Documentos de ritmo que nadie contrasta con una partida real.
