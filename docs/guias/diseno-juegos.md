# Diseño de juegos: base de conocimiento

Léela **antes de diseñar** cualquier juego, nivel, mundo, enemigo o jefe. Recoge principios contrastados (libros,
charlas GDC, análisis de Nintendo, Game Maker's Toolkit, artículos de desarrolladores), cada uno con su porqué y su
fuente. Viene del proyecto SNES (mismo usuario, 2026-11-15) y está generalizada para la Game Boy DMG; sirve para cualquier género (plataformas, exploración, puzle,
arcade, estrategia); el capítulo 4 es el específico de mundos conectados tipo Ufouria/metroidvania.

Cómo usarla sin gastar contexto: lee esta página entera (reglas de oro y listas) y abre sólo los capítulos de tu tarea.

| Tarea | Capítulos |
|---|---|
| Controles, física, sensación del personaje | [1](diseno-juegos/01-bucle-y-tacto.md) |
| Diseñar o revisar un nivel / una sala | [2](diseno-juegos/02-metodo-de-nivel.md), [3](diseno-juegos/03-plataformas-2d.md), [6](diseno-juegos/06-dificultad-y-ensenanza.md), [9](diseno-juegos/09-errores-comunes.md) |
| Mundo conectado, habilidades, llaves, estados del mundo, mapa | [4](diseno-juegos/04-mundo-metroidvania.md), [8](diseno-juegos/08-secretos-y-recompensas.md) |
| Enemigos y jefes | [5](diseno-juegos/05-enemigos-y-jefes.md) |
| Curva de dificultad, onboarding | [6](diseno-juegos/06-dificultad-y-ensenanza.md) |
| Cámara y desplazamiento | [7](diseno-juegos/07-camara-2d.md) |
| Secretos, coleccionables | [8](diseno-juegos/08-secretos-y-recompensas.md) |
| Probar y medir | [10](diseno-juegos/10-playtest-y-metricas.md) |
| Puzle de piezas que caen (versus, infinito, simulador) | [11](diseno-juegos/11-puzzle-caida.md) |

Capítulos:
1. [Bucle principal y tacto](diseno-juegos/01-bucle-y-tacto.md): átomos de habilidad, game feel, perdón (coyote, búfer), lentes.
2. [Método para hacer un nivel](diseno-juegos/02-metodo-de-nivel.md): parti, kishōtenketsu, camino crítico, métricas, ritmo.
3. [Plataformas 2D](diseno-juegos/03-plataformas-2d.md): piezas, grupos rítmicos, celdas, antepiezas, vuelo y buceo.
4. [Mundo conectado / metroidvania](diseno-juegos/04-mundo-metroidvania.md): cerraduras y llaves, estados del mundo, volver atrás, mapa, guardado.
5. [Enemigos y jefes](diseno-juegos/05-enemigos-y-jefes.md): reparto, anticipación, los ocho tiempos de un jefe.
6. [Dificultad y enseñanza](diseno-juegos/06-dificultad-y-ensenanza.md): flujo, dificultad invisible, enseñar sin texto.
7. [Cámara 2D](diseno-juegos/07-camara-2d.md): técnicas de "Scroll Back" y su uso en Game Boy.
8. [Secretos y recompensas](diseno-juegos/08-secretos-y-recompensas.md).
9. [Errores comunes](diseno-juegos/09-errores-comunes.md): tabla de antipatrones con arreglo.
10. [Playtest y métricas](diseno-juegos/10-playtest-y-metricas.md).

Relación con otras normas: los números y su validación están en la skill `gb-game-design` (GDD, feel, presupuestos,
géneros) y en el lint de niveles (`harness/levels.py`, `harness/physics.py`); el presupuesto técnico (sprites por
línea, VRAM, VBlank) en `docs/guias/rendimiento-vram.md` y `docs/guias/hardware-dmg.md`; qué módulo usar en
`docs/guias/que-usar.md`. Cada capítulo termina con su "Adaptación Game Boy (DMG)": pantalla de 160×144, 10 sprites
por línea, 4 tonos. Si un juego clona a otro, **manda el original**: esta guía sirve para entenderlo y para los huecos
que el original no resuelve, no para "mejorarlo".

## Reglas de oro

1. **El verbo primero.** Si moverse y saltar no gustan en una sala vacía, ningún nivel lo arregla. Cierra la física y
   sus métricas antes de construir niveles. (cap. 1, 2)
2. **Perdona al jugador sin que se note:** tiempo de coyote, búfer de salto, corrección de esquinas, cajas de daño
   generosas para él y ajustadas para los enemigos. (cap. 1)
3. **Una idea por tramo: presentar → desarrollar → girar → cerrar.** Presenta en un sitio seguro y retira la idea antes
   de que canse. (cap. 2)
4. **Ritmo con silencios.** Grupos de reto cortos separados por pausas seguras; alterna picos y descansos. (cap. 2, 3)
5. **Todo peligro se ve antes de que pueda dañar.** Sin saltos de fe, sin enemigos que nacen encima, sin ataques sin
   anticipación. (cap. 3, 5, 7, 9)
6. **Enseña con el espacio, no con texto:** antepiezas, enemigos que demuestran, recompensas que marcan el camino.
   (cap. 3, 6)
7. **Cerradura antes que llave, y cada llave abre muchas cerraduras.** Cerraduras legibles y consistentes. (cap. 4)
8. **Volver debe dar algo nuevo** y los atajos acortan el mundo a medida que crece. (cap. 4)
9. **Un estado del mundo siempre se ve, se entiende y se valida** en todas sus combinaciones; nunca un softlock. (cap. 4)
10. **Fallar cuesta poco:** puntos de control cerca de cada reto y del jefe; reintento inmediato. (cap. 5, 6)
11. **Jefes que examinan lo aprendido**, con fases que cambian el comportamiento, no sólo la vida. (cap. 5)
12. **Lo opcional regula la dificultad:** secretos y mejoras dan ayuda a quien explora y reto a quien lo busca. (cap. 6, 8)
13. **Mide, no opines:** tiempos, muertes por sitio, zonas donde se pierde la gente, con entrada reproducible. (cap. 10)

## Checklist antes de dar por bueno un nivel

Aplica a una sala, una pantalla o un nivel lineal. Cada punto debe tener evidencia (prueba, captura, cifra), no
opinión.

**Idea y estructura**
- [ ] El nivel se resume en una frase (parti) y tiene una sola idea nueva principal.
- [ ] La idea nueva se presenta en un sitio seguro, se desarrolla, gira y cierra.
- [ ] Hay camino crítico marcado; lo opcional justifica su coste (ROM, VRAM, tiempo).
- [ ] Hay al menos un momento memorable.

**Métricas y legibilidad**
- [ ] Todos los huecos y alturas obligatorios están dentro de la envolvente medida, con margen (validador en verde).
- [ ] Ningún salto de fe: desde cada punto de salto obligatorio se ve (o se puede mirar) el aterrizaje.
- [ ] Todo enemigo y peligro es visible y reconocible antes de poder dañar; los ataques tienen anticipación.
- [ ] Plataformas, peligros, fondo y elementos interactivos se distinguen por forma/color (captura revisada).
- [ ] La cámara muestra lo que viene en la dirección de marcha y en caídas.

**Ritmo y dificultad**
- [ ] Grupos de reto cortos con pausas seguras entre ellos.
- [ ] Puntos de control antes de cada reto grande; repetir tras morir cuesta poco (cifra en segundos).
- [ ] La dificultad sube respecto al nivel anterior, con al menos un descanso.
- [ ] Hay una recompensa o secreto con pista para quien explora.

**Técnica**
- [ ] Sin parpadeo de sprites en los momentos de más carga (10 por línea) y `max_frame_lines` < 120, `vram_late` == 0.
- [ ] Recorrido completo reproducible (test de PyBoy con bot y, para lo que dependa del timing, `harness/gbrun.py`)
      con capturas y estado esperado.
- [ ] Legible en 4 tonos: la captura en gris se entiende sin explicación (fondo claro, sólido con borde, peligro oscuro).

**Prueba**
- [ ] Bot o recorrido grabado: tiempo por tramo y muertes por sitio anotados.
- [ ] Revisado por alguien que no lo diseñó, sin explicaciones previas.

## Checklist antes de dar por bueno un mundo (conectado / metroidvania)

**Grafo y llaves**
- [ ] Grafo de dependencias dibujado (zonas, llaves, cerraduras, estados) y comprobado por el validador.
- [ ] Desde el inicio y desde cualquier estado alcanzable hay al menos un camino hacia la siguiente llave.
- [ ] Ningún estado del mundo (interruptores, agua, puertas de un sentido) produce un softlock; se han probado todas
      las combinaciones alcanzables.
- [ ] Cada cerradura se ve antes de tener su llave; al conseguir la llave, algo recuerda la cerradura.
- [ ] Cada llave abre varias cosas (cerca y lejos), y su primera sala tras obtenerla la enseña con seguridad.
- [ ] Cerraduras consistentes: mismo símbolo o color para la misma llave en todo el mundo.
- [ ] Las roturas de secuencia previstas siguen teniendo salida.

**Navegación**
- [ ] El mapa muestra salas visitadas, puertas sin abrir y cerraduras del camino principal.
- [ ] Hay hitos visuales reconocibles por zona (fondo, paleta, música).
- [ ] Al volver a una zona con una habilidad nueva hay rutas, secretos o enemigos nuevos.
- [ ] Cada zona grande abre un atajo hacia el núcleo al completarse.
- [ ] Guardado y recarga antes de jefes y zonas peligrosas; distancia máxima entre guardados anotada.
- [ ] Los puntos sin retorno avisan y no dejan atrás nada imprescindible.

**Estados del mundo (agua, vuelo, buceo, eventos)**
- [ ] El estado actual se ve en pantalla o en el mapa; el control que lo cambia está cerca de donde hace falta.
- [ ] Cada cambio abre algo visible cerca.
- [ ] Las secciones con otra física (agua, vuelo) tienen sus propias métricas medidas y su presentación segura.

**Ritmo global**
- [ ] Curva de dificultad en dientes de sierra a lo largo del mundo, con descansos.
- [ ] Jefes al final de cada llave importante, que examinan lo aprendido.
- [ ] Tiempo estimado del camino crítico y del 100 % medidos con bot.

## Fuentes principales

Leídas directamente para la guía original del proyecto SNES (2026-11-15):
- *The Level Design Book* (Robert Yang y colaboradores), CC BY-NC-SA 4.0, copia local en `docs/ref/diseno/`,
  https://book.leveldesignbook.com
- Itay Keren, "Scroll Back: The Theory and Practice of Cameras in Side-Scrollers" (GDC 2015),
  https://www.gamedeveloper.com/design/scroll-back-the-theory-and-practice-of-cameras-in-side-scrollers
- Smith, Cha, Whitehead, "A Framework for Analysis of 2D Platformer Levels" (2008),
  https://expressiveintelligence.github.io/papers/smith-sandbox-08.pdf
- Maddy Thorson, "Celeste & Forgiveness", https://maddymakesgames.com/articles/celeste_and_forgiveness/
- "The Invisible Hand of Super Metroid", https://gamedeveloper.com/design/the-invisible-hand-of-super-metroid
- Mike Stout, "Boss Battle Design and Structure" (2010), https://www.gamedeveloper.com/design/boss-battle-design-and-structure
- "Enemy Attacks and Telegraphing", https://gamedeveloper.com/design/enemy-attacks-and-telegraphing
- Mark Brown, "Super Mario's Invisible Difficulty Settings", https://gmtk.substack.com/p/super-marios-invisible-difficulty
- Lena Schütz, "Metroidvania Analysis: Locks, Keys and User Guidance" (HSLU 2021, sobre el episodio de *Boss Keys* de
  Hollow Knight), https://blog.hslu.ch/games/files/2021/11/Metroidvania_Analysis.pdf
- Josh Bycer, "The Art of the Platformer" (2012), https://www.gamedeveloper.com/design/the-art-of-the-platformer
- Ufouria: The Saga, https://en.wikipedia.org/wiki/Ufouria:_The_Saga

Conocidas por resúmenes secundarios (vídeos o libros; contrastar antes de citarlas literalmente):
- Game Maker's Toolkit (Mark Brown): *Boss Keys* (Zelda, Super Metroid, Hollow Knight, Metroid Dread), el método de
  cuatro pasos de Mario 3D World, "How Cuphead's Bosses (Try to) Kill You". Canal: https://www.youtube.com/@GMTK
- Koichi Hayashida sobre kishōtenketsu (entrevista de Gamasutra): https://en.wikipedia.org/wiki/Koichi_Hayashida
- Miyamoto y Tezuka sobre 1-1 (Eurogamer 2015): https://www.avclub.com/shigeru-miyamoto-explains-the-making-of-super-mario-bro-1798284041
- Templo del Agua (Ocarina of Time): https://en.wikipedia.org/wiki/Water_Temple_(Ocarina_of_Time)
- Jenova Chen, *Flow in Games* (tesis): https://jenovachen.info/abstract
- Dan Cook, "The Chemistry of Game Design" (2007): https://www.gamedeveloper.com/pc/feature-the-chemistry-of-game-design-
- Dahlskog y Togelius, patrones de Super Mario Bros.:
  https://www.academia.edu/79715544/Procedural_Content_Generation_Using_Patterns_as_Objectives
- Hullett y Whitehead, "Design Patterns in FPS Levels" (FDG 2010, DOI 10.1145/1822348.1822359), patrones de nivel
  con relación causa-efecto (para shooters; la idea de catalogar patrones y medir su efecto sirve a cualquier género);
  ampliado en la tesis de Hullett *The Science of Level Design* (2012), https://escholarship.org/uc/item/1m25b5j5

Libros de pago recomendados (no descargados; comprarlos o pedirlos en biblioteca):
- Steve Swink, *Game Feel* (2008): definición y anatomía del tacto.
- Jesse Schell, *The Art of Game Design: A Book of Lenses* (3.ª ed. 2019): más de cien lentes de preguntas.
- Anna Anthropy y Naomi Clark, *A Game Design Vocabulary* (2014): según The Level Design Book, probablemente el mejor
  libro de diseño de niveles 2D.
- Christopher Totten, *An Architectural Approach to Level Design* (2014/2019).
- Scott Rogers, *Level Up! The Guide to Great Video Game Design*.
- Raph Koster, *A Theory of Fun for Game Design*.
- Ian Schreiber, *Game Design Concepts* (curso gratuito, CC BY 3.0 US): https://gamedesignconcepts.wordpress.com/

Charlas gratuitas útiles (lista ampliada en `docs/ref/diseno/level-design-book-full.md`, sección `# Recommended talks`):
Maddy Thorson sobre el diseño de niveles de Celeste (GDC, canal de YouTube de GDC); Matthias Worch, "Meaningful Choice
in Game Level Design" (GDC 2014); Mike Stout, "Reaching Into the Toy-Chest" (GDC 2012).
