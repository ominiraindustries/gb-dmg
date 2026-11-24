# Base de conocimiento (`kb.py`): fuentes y convenciones

`harness/scripts/kb.py` es la única puerta a todo lo que el arnés sabe: documentación, API de gbe, lecciones,
tareas de Beads y referencias de hardware. Un agente empieza **toda** tarea con:

```text
python -I harness/scripts/kb.py brief --role <rol> --task "<tarea>"
```

y luego lee sólo las rutas y secciones que cita el brief. Para una duda concreta:
`kb.py query "texto" [--kind K]`. El índice (`.cache/kb/kb.sqlite`, SQLite + FTS5) se reconstruye solo,
fichero a fichero, cuando cambia una fuente; no se versiona.

## Fuentes indexadas y su tipo (`--kind`)

| Tipo | Fuente | Cómo se trocea |
|---|---|---|
| `tecnica` | `docs/tecnicas/*.md` | una ficha por `## ID · título` (ver abajo) |
| `api` | `harness/common/src/gbe.h`, `harness/common/src/*.h` y `docs/api/*.md` | una sección por bloque `// ---- gbe_x.c`, y una entrada por función/macro/`extern` |
| `tool` | `docs/guias/*.md`, `docs/harness/*.md`, `docs/normas/*.md`, `harness/common/README.md` | por encabezado `#`/`##`/`###` |
| `study` | `docs/estudios/*.md` | por encabezado |
| `doc` | `docs/diseno/*.md`, `docs/auditorias/*.md` | por encabezado |
| `game` | `games/*/design/*.md` (GDD, ui, estudios del juego) | por encabezado, con el juego delante |
| `project` | `games/*/README.md`, `games/*/INFORME.md` | por encabezado, con el juego delante |
| `ref` | `docs/ref/**/*.md`, `reference/pandocs/src/**/*.md` | por encabezado (ventanas de 60 líneas si una sección es larga) |
| `lesson` | `docs/datos/lessons.jsonl` (vía `lessons.py`) | una por lección |
| `backlog` | Beads vivo (`bd list --all --json`) | una por tarea |

`docs/INDEX.md` es el mapa de la documentación y no se indexa. `reference/` está fuera de git: si falta, sólo
se pierden esos resultados. Si existe `docs/ref/pandocs/` (la copia versionada), `reference/pandocs/` no se indexa para no duplicar.

## Convenciones para escribir documentación que `kb.py` encuentre

Generales (todas las carpetas):

- Un fichero por tema; título `# Tema` en la primera línea. Secciones `##` cortas (idealmente < 90 líneas: las más
  largas se parten en ventanas y el título de la ventana pierde precisión).
- El encabezado dice de qué va la sección con las palabras que alguien buscaría, en castellano y, si el
  término técnico es inglés, también en inglés: `## Scroll con streaming de columnas (column streaming)`.
- Cifras con su unidad y dónde se midieron: `~20 T/byte (games/tetris, tile_copy16)`.
- Rutas del repositorio en texto (`harness/common/src/gbe_vq.c`), sin `../`; enlaces Markdown relativos que
  existan (`kb.py check` denuncia los rotos). Una línea en blanco antes y después de cada tabla.
- Texto en castellano; identificadores, código y nombres de registros tal cual (`LCDC`, `SCX`, `act_move`).

`docs/tecnicas/` (libro de técnicas):

- Fichero por capítulo (`scroll.md`, `sprites.md`, `rendimiento.md`...), primera línea `# Capítulo`, una
  introducción breve y después fichas separadas por `---`.
- Cada ficha empieza con `## XX1 · Título` (2–3 letras mayúsculas + número, único en todo el libro; p. ej.
  `SC1`, `SP3`, `VR2`) y lleva estos campos en negrita, cada uno al principio de línea:
  `**Problema**`, `**Cómo lo resolvían**`, `**En gbe**`, `**Medido en nuestros juegos**`, `**Estado**`.
- Opcional: `<!-- tags: scroll, vram -->` en una línea propia.
- `docs/tecnicas/README.md` lleva la tabla de todas las fichas:
  `| ID | Título | Capítulo | Estado | Fuentes |` (fuentes separadas por comas). `kb.py check` exige que tabla y
  fichas coincidan y que ninguna ficha `pendiente` nombre una función que ya existe en `gbe.h`.
- `kb.py card SC1` imprime la ficha entera.

`docs/api/`: generado desde los comentarios de `harness/common/src/gbe.h`. Se corrige el comentario del `.h`
y se regenera; no se edita a mano. En `gbe.h`, cada módulo abre con `// ---------------- gbe_x.c` y cada
función lleva su comentario en la misma línea o en las líneas `//` justo encima.

`docs/ref/`: referencias de hardware en Markdown (copias o extractos con su fuente y licencia al principio).
`docs/estudios/`: estudios de juegos comerciales (cómo lo hacían, con cifras); nunca copian recursos ni código.
`docs/guias/`: cómo se hace algo con nuestro arnés (`que-usar.md`, `diseno-juegos.md`...).

## Lecciones (`docs/datos/lessons.jsonl`)

Una por línea: `id`, `text`, `evidence` (de dónde sale, con fecha), `roles`, `topics`, `created` y, si se puede,
un `check` automático (`forbid`/`require`/`unique`/`cmd`, formato en `harness/scripts/lessons.py`).
Se añaden con `lessons.py add`; `lessons.py check` ejecuta los automáticos. Roles válidos (el prefijo `gb-` es
opcional: `gb-game-dev` y `game-dev` son el mismo rol): `all`, `sdk-dev`, `game-dev`, `reviewer`, `docs-writer`, `game-designer`, `pixel-artist`, `ui-designer`,
`qa-tester`, `playtester`, `coordinator`.

## Buzón de hallazgos (`docs/datos/inbox.jsonl`)

El hook `SubagentStop` (`harness/scripts/inbox_hook.py`) lee el informe final de cada subagente y archiva las
viñetas de las secciones `## Lecciones para mi rol`, `## Huecos de gbe` y `## Bugs encontrados`. Son opcionales.
El aviso de inicio de sesión (`kb.py inbox status`) pide cribar con 20 o más pendientes o más de 2 días:
`kb.py inbox list --status new` y `kb.py inbox apply FICHERO` (JSONL de decisiones `{"id", "to", "ref"...}`).
Lo vigente va a Beads o a lecciones; el buzón no es un sitio donde vivir.

## Comandos

```text
kb.py brief --role R --task "..." [--broad]   # inicio de tarea (< 60 líneas)
kb.py query "texto" [--kind tecnica,api] [--n 5] [--full]
kb.py card SC1 | lesson-id | GB-xxxx          # ficha, lección o tarea completa
kb.py sql "SELECT id, title FROM backlog WHERE status='open'"   # sin consulta: las tablas
kb.py inbox status | list | add | triage | apply | match
kb.py check                                   # enlaces, fichas, lecciones, Beads
kb.py test                                    # harness/scripts/kb_tests.json: consultas que deben acertar
```
