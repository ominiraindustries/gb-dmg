# Coste de IA (tokens): reglas

Medido en el workspace de SNES (164 agentes del 17 al 21-10-2026, ~880 M tokens ponderados): el 90 % del coste es
**releer el contexto**. Cada llamada de un agente vuelve a leer todo su contexto, así que
**coste ≈ número de llamadas × tamaño del contexto**. La salida (lo que escriben) es menos del 1 %. Los agentes más
caros fueron los reanudados una y otra vez con mensajes nuevos (2841 llamadas, contexto de hasta 965 k tokens).

## Reglas

1. **Tareas cortas**: un encargo = un trozo cerrado. Objetivo 80–120 llamadas; máximo 150. A las ~130 el agente
   termina el bloque y escribe un handoff corto (README del juego o `docs/harness/estado.md`); **otro agente nuevo**
   sigue con contexto limpio. No se reanuda un agente largo para una fase nueva.
2. **Contexto limpio**: nunca volcar logs, transcritos, JSONL, binarios ni árboles completos (`head`, `grep`,
   resúmenes; los tests imprimen PASS/FAIL y lo justo). No leer ficheros enteros si basta una sección:
   `kb.py brief`/`query` en vez de leer documentos enteros.
3. **Pocos agentes a la vez**: 2–3 bien definidos, con rutas que no se solapen y reserva en `board.py`.
4. **Mensajes a agentes en marcha**: cortos y agrupados; cada mensaje a un agente largo cuesta su contexto entero.
5. **El coordinador también**: resúmenes cortos, no reenviar informes enteros, sesión nueva cuando el contexto es enorme.
6. **Hallazgos opcionales**: las secciones `Lecciones para mi rol` / `Huecos de gbe` sólo con evidencia nueva,
   reutilizable y que no esté ya en `kb.py`. Nada de rellenar plantillas.
7. **Pruebas proporcionales**: cada agente ejecuta las pruebas de su bloque (`gb.py test <juego>`, `gb.selftest()`
   si tocó asm de gbe). La batería de todos los juegos, una vez al día o al integrar cambios de gbe.
8. **Modelo por rol** (Claude Code): `gb-sdk-dev` y `gb-game-dev` con Opus; `gb-reviewer` con Opus;
   `gb-docs-writer` con Sonnet. Lo fija el `model:` de cada `.claude/agents/*.md`; el usuario puede cambiarlo.
9. **Esperas**: todo bucle de espera lleva límite (`timeout 1800 bash -c 'until ...; do sleep 5; done'`). Si se
   sospecha de procesos colgados, `python -I harness/scripts/bgwatch.py` (y `--kill`).
