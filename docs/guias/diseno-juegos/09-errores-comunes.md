# 9. Errores comunes de diseño (antipatrones)

Cada error lleva su porqué y su arreglo habitual. Los capítulos 1-8 tienen además su lista específica.

| Error | Por qué falla | Arreglo |
|---|---|---|
| **Salto de fe**: hueco o caída sin ver si hay suelo o muerte | El jugador no puede decidir; muere por desconocer, no por fallar | Cámara que muestre el fondo, mirar abajo, monedas o luces que indiquen la caída segura ([TV Tropes, Leap of Faith](https://tvtropes.org/pmwiki/pmwiki.php/Main/LeapOfFaith)) |
| **Peligro fuera de pantalla** que golpea al entrar | No hay tiempo de reacción; se siente trampa | Foco adelantado (cap. 7), aviso sonoro, aparición en el borde con anticipación |
| **Muerte por primera vez inevitable** (trampa "kaizo") | Sólo se supera memorizando; castiga la curiosidad | Mostrar la trampa antes de que pueda matar; reservarla para contenido opcional de expertos |
| **Hueco o salto "por un píxel"** en el camino obligatorio | La variación de entrada humana lo hace aleatorio | Margen sobre la envolvente medida; perdón de coyote/búfer (cap. 1) |
| **Tutorial de texto largo** | Se olvida antes de usarlo | Presentar → desarrollar → girar (cap. 2 y 6) |
| **Mecánica de un solo uso** | Coste de aprendizaje sin rendimiento | Desarróllala o quítala |
| **Habilidad que trivializa el mundo** (vuelo infinito) | Borra los retos ya diseñados | Limitarla o diseñar salas que la necesiten (cap. 1) |
| **Cerradura sin señal** | No se puede planear | Símbolo/color consistente por llave (cap. 4) |
| **Volver por el mismo camino vacío** | Tiempo muerto | Atajos, rutas nuevas al volver, enemigos o secretos nuevos (cap. 4) |
| **Estado global invisible** (agua alta/baja, interruptores) | El jugador no sabe en qué mundo está | Indicador visible, control cerca, mapa (cap. 4, Templo del Agua) |
| **Softlock**: atrapado sin salida ni forma de morir | Obliga a reiniciar o perder la partida | Validar el grafo en todos los estados; salida de emergencia (cap. 4) |
| **Punto sin retorno silencioso** con coleccionables detrás | Pérdida permanente sin aviso | Avisar, dejar otra vía o devolver el acceso |
| **Esponja de vida** en jefes | Duración sin decisiones nuevas | Fases que cambian comportamiento (cap. 5) |
| **Ataque sin anticipación** | Fallo injusto | Anticipación → ataque → recuperación (cap. 5) |
| **Puntos de control lejanos** | Repetir lo superado frustra más que el reto | Control antes de cada reto grande y del jefe (cap. 6) |
| **Final más difícil que todo** sin resolución | El clímax no se disfruta | Clímax intenso pero legible y una resolución merecida (cap. 2) |
| **Exceso de señales** ("Disneylandia") | El mundo parece un parque guiado; se pierde la exploración | El aviso más sutil que funcione; más sólo si el playtest lo pide ([LDB, Wayfinding](https://book.leveldesignbook.com/process/blockout/wayfinding)) |
| **Explicar el diseño durante el playtest** | Contamina la prueba | Observar en silencio (cap. 10) |
| **Diseñar el nivel 1 primero** | Aún no sabes qué tiene que enseñar | Hazlo al final (cap. 2) |
| **Ajustar niveles con la física sin cerrar** | Cada cambio de física rompe todos los huecos | Congelar métricas antes de construir (cap. 2) |
| **Concepto de jefe imposible de implementar** | Se rehace entero | Prototipo jugable antes del arte (Stout 2010) |

Fuentes adicionales para la tabla: Josh Bycer, "The Art of the Platformer",
https://www.gamedeveloper.com/design/the-art-of-the-platformer ; Mike Stout, "Boss Battle Design and Structure",
https://www.gamedeveloper.com/design/boss-battle-design-and-structure ; The Level Design Book
(`docs/ref/diseno/level-design-book-full.md`).

## Errores específicos de nuestro contexto (Game Boy, agentes)

- Validar sólo que el mapa "es válido" (alcanzable) y no que es interesante: alcanzable no es divertido
  (`gb-game-design`, paso 4).
- Diseñar sin el presupuesto técnico: más sprites en una línea de los que caben, más teselas que copiar de las que caben en el
  VBlank. Un nivel bonito que parpadea es un nivel malo.
- Copiar la disposición de un juego comercial. Se estudia la referencia, nunca se copian sus recursos ni sus mapas.
- Afirmar que algo es divertido o justo sin una observación reproducible (`gb-game-design`).
