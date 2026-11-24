# Dónde está el conocimiento del arnés (Game Boy DMG)

**La regla:** busca antes de leer. `python -I harness/scripts/kb.py query "..." [--kind tecnica|api|tool|ref|study]`
devuelve `fichero:línea`; lee solo eso. Convenciones del índice y formato de las fichas: [`harness/kb.md`](harness/kb.md).
Trabajo pendiente: Beads (`python -I harness/scripts/beads.py ready --json`, flujo en [`harness/beads.md`](harness/beads.md)).

## Mapa

```text
docs/
  INDEX.md        este mapa
  guias/          cómo se hace algo con nuestro arnés (qué usar, rendimiento, bancos, hardware, C, pruebas, diseño)
  tecnicas/       libro de técnicas DMG: fichas "ID · título" por problema (README = índice)
  estudios/       estudios con números medidos (juegos comerciales con ROM del usuario; nuestras herramientas)
  api/            GENERADO: referencia de gbe (harness/scripts/apidoc.py); no se edita
  ref/            GENERADO: referencias locales (Pan Docs, GB CTR, opcodes, GBDK, hardware.inc, hUGEDriver; docs/ref/mkref.py)
  harness/        cómo funciona el arnés de agentes (kb, beads, coste en tokens)
  datos/          datos de las herramientas (lecciones, buzón)
```

## Cómo encuentra un agente...

| Busca | Primero | Dónde vive |
|---|---|---|
| ¿Hay una pieza de gbe para X? | [`guias/que-usar.md`](guias/que-usar.md) · `kb.py query --kind api` | `harness/common/src/gbe.h`, [`api/`](api/README.md) |
| Cómo se resuelve un problema típico (sprites por línea, HUD, VBlank, bancos, texto, audio) | `kb.py query --kind tecnica` · `kb.py card SP1` | [`tecnicas/`](tecnicas/README.md) |
| Un registro, un bit, un tiempo de hardware | `kb.py query --kind ref` | [`ref/pandocs/`](ref/pandocs/README.md), [`ref/gbctr.txt`](ref/gbctr.txt), [`ref/hardware-inc.md`](ref/hardware-inc.md) |
| Ciclos de una instrucción | `grep` en [`ref/sm83-opcodes.md`](ref/sm83-opcodes.md) | también skill `gb-asm` (`opcodes.md`, sintaxis sdasgb) |
| Una función de GBDK | `grep` en [`ref/gbdk/api/`](ref/gbdk/api/README.md) | manual: [`ref/gbdk/manual/`](ref/gbdk/manual/) |
| Música con tracker | [`ref/hugedriver/`](ref/hugedriver/) | ficha AU2 (pendiente) |
| Un número medido de nuestros juegos | [`guias/rendimiento-vram.md`](guias/rendimiento-vram.md), `harness/common/README.md` | `games/*/README.md`, `INFORME.md` |
| Diseñar un juego, nivel, enemigo o jefe | [`guias/diseno-juegos.md`](guias/diseno-juegos.md) (reglas de oro y checklists) | capítulos en `guias/diseno-juegos/`, The Level Design Book en `ref/diseno/` |
| Qué aprendió el proyecto SNES | [`guias/lecciones-snes.md`](guias/lecciones-snes.md) | `C:/Users/David/Desktop/SNES/docs/datos/lessons.jsonl` |

## Guías

| Guía | Contenido |
|---|---|
| [`que-usar.md`](guias/que-usar.md) | necesidad → API de gbe → juego que la usa |
| [`rendimiento-vram.md`](guias/rendimiento-vram.md) | bucle de frame, VBlank, colas de VRAM, perfilado, trampas de SDCC medidas (antes en CLAUDE.md) |
| [`bancos.md`](guias/bancos.md) | bancos de ROM, `banked_res`, flags de MBC, guardado (antes en CLAUDE.md) |
| [`hardware-dmg.md`](guias/hardware-dmg.md) | reglas de hardware DMG y cifras de referencia (antes en CLAUDE.md) |
| [`sdcc-c.md`](guias/sdcc-c.md) | C rápido con SDCC, gotchas de GBDK, ensamblador sdasgb (antes en CLAUDE.md) |
| [`pruebas.md`](guias/pruebas.md) | PyBoy para lo rápido, Mesen 2 (`harness/gbrun.py`) para lo exacto |
| [`diseno-juegos.md`](guias/diseno-juegos.md) | principios, antipatrones y checklists de diseño (de SNES, generalizado a DMG) |
| [`lecciones-snes.md`](guias/lecciones-snes.md) | método aprendido en el proyecto SNES que vale aquí |

## Ejecutar y probar

- Tests rápidos (PyBoy): `python -I harness/gb.py test <juego>`.
- Exactitud y timing (Mesen 2): `python -I harness/gbrun.py <juego> --frames N --input "F-F2:btn" --check "sym==v"
  [--check-at ...] [--expect ...] [--watch ...] [--dump ...] [--golden DIR] [--nonblank]`; sale con 0/1/2/3.
  Pruebas del ejecutor: `python -I -m pytest harness/tests -q`. Detalle: [`guias/pruebas.md`](guias/pruebas.md).

## Regenerar lo generado

| Qué | Orden | Comprobar |
|---|---|---|
| `docs/api/` | `python -I harness/scripts/apidoc.py` | `--check` (sale 1 si está desfasado) |
| `docs/ref/` | `python -I docs/ref/mkref.py` (necesita `reference/` y `tools/gbdk/`: `python -I harness/gb.py setup`; hUGEDriver en `reference/hugedriver_dl/`) | `--check` |

## Estado (para retomar)

2026-11-24, base de conocimiento técnico creada: referencias locales (Pan Docs entera por tema, GB CTR en texto, 512
opcodes SM83, 47 cabeceras de GBDK, manual de GBDK, hardware.inc con equivalencias de GBDK, hUGEDriver), API de gbe
generada (33 páginas con los juegos que usan cada módulo), 8 guías, 24 fichas de técnica en 7 capítulos, 1 estudio
(PyBoy frente a Mesen) y `harness/gbrun.py` probado en hello y platformer.

Huecos conocidos:
- Sin estudios de juegos comerciales todavía (hace falta una ROM que aporte el usuario; nunca se descargan).
- Fichas por escribir: paralaje con la ventana, tiles animados, scroll en 4 direcciones (gbe_world), mapa con
  streaming de columnas (gbe_map), OAM corruption en detalle, timer y serie (enlace).
- `harness/gb.py` no tiene todavía una orden `mesen`: `gbrun.py` acepta el nombre del juego directamente.
- No hay ROM de prueba propia que fuerce las diferencias de timing entre PyBoy y Mesen (estudio pyboy-vs-mesen, "Sin medir").
- Música: hUGEDriver documentado pero sin integrar (ficha AU2).
