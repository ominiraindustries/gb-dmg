# 10. Playtest y métricas

Fuente principal: The Level Design Book, "Playtesting" (`docs/ref/diseno/level-design-book-full.md`, sección
`# Playtesting`; en línea https://book.leveldesignbook.com/process/blockout/playtesting).

## Cuándo

- **Cada día, tú mismo**, para los fallos evidentes.
- **Al final de cada fase** (recorrido, bloque gris, guion, arte): revisión por otro diseñador o agente revisor.
- **Con jugadores normales** cuando el arte permite leer el nivel: un bloque gris es difícil de leer para quien no
  desarrolla.

## Cómo

1. **Prepara:** alcance (qué parte y cuánto tiempo), la pregunta principal ("¿encuentran el atajo?"), qué datos se
   recogen y cómo se anotan.
2. **Explica poco:** concepto, duración, qué tipo de comentario buscas. Nada más.
3. **Observa:** mira lo que hace, no lo que dice. No interrumpas; interviene sólo si está atascado de verdad o el juego
   está roto. No te disculpes ni expliques el diseño: la incomodidad señala el problema.
4. **Entrevista al final:** preguntas preparadas de comprensión ("¿qué hacía el grifo?") y de opinión.
5. **Escucha el problema, no la solución:** el arreglo que propone el jugador suele ser malo, pero el problema que
   señala casi siempre es real.

## Qué medir

- Tiempo por sala, por zona y hasta cada hito.
- Muertes por sitio (mapa de calor) y causa.
- Tiempo sin avanzar (perdido) y salas revisitadas sin motivo.
- Qué secretos se encuentran y cuáles no.
- Qué habilidad o arma domina (si una lo resuelve todo, el reparto está mal).

## En este repositorio (agentes)

No hay jugadores humanos en cada iteración, así que el playtest se aproxima con pruebas reproducibles:

- **Validador del nivel:** alcanzabilidad con la envolvente real de movimiento, puertas, llaves y todos los estados del
  mundo; sin softlocks (skill `gb-game-design` y el lint de niveles (`harness/levels.py`, `harness/physics.py`)).
- **Bot con modelo humano:** tiempo de reacción y error de puntería calibrados, para medir tiempos por sala y muertes
  (`GB.human` en `harness/gbtest.py`, perfiles experto/medio/novato; agente `playtester`).
- **Entrada reproducible:** PyBoy (`python -I harness/gb.py test <juego>`, bots con `gb.run_bot`) y Mesen headless
  (`python -I harness/gbrun.py <juego> --input ... --check-at ...`): grabar un recorrido, comprobar estados
  intermedios y capturas.
- **Revisión independiente:** un agente `qa-tester` que no ha diseñado el nivel lo juega o lo lee con la lista del
  final de `docs/guias/diseno-juegos.md`.
- El usuario es el playtester humano final; prepárale una ROM y preguntas concretas.

## Antipatrones

- Dar por bueno un nivel porque al diseñador le sale a la primera.
- Explicar, disculparse o interrumpir durante la prueba.
- Descartar un comentario porque la solución propuesta no sirve.
- Medir sólo si se termina, no cuánto cuesta ni dónde se atasca.
- Usar siempre el mismo tipo de probador (los expertos fingen que todo es fácil; los novatos son demasiado educados).
