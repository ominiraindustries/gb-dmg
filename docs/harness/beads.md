# Seguimiento del trabajo con Beads

Desde 2026-11-24, **Beads/Dolt es la fuente de verdad** de las tareas, sus estados y sus dependencias en GBDMG
(mismo backend que el workspace de SNES: Dolt embebido, base `GB`, prefijo `GB-`). El backlog inicial se sembró
leyendo los hitos de cada GDD y los `xfail` de los tests; cada juego en marcha tiene un epic.

Se usa siempre el adaptador del repositorio, que encuentra el `bd.exe` nativo (PowerShell puede bloquear el shim
`bd.ps1` de npm) y convierte las reglas de este documento en comprobaciones:

```text
python -I harness/scripts/beads.py prime
python -I harness/scripts/beads.py ready --json
python -I harness/scripts/beads.py show GB-xxxx
python -I harness/scripts/beads.py update GB-xxxx --claim
```

Todos los worktrees del repositorio descubren el mismo `.beads`.

## Estados y cierre verificable

| Estado | Significado | Evidencia mínima |
|---|---|---|
| `open` | reporte o idea sin confirmar | origen y aceptación |
| `confirmed` | existe ahora mismo | reproducción, inspección o prueba fechada |
| `in_progress` | trabajo reclamado | confirmación y responsable |
| `resolved` | solución hecha pero sin validar | commit o rutas |
| `closed` | solución verificada o descarte razonado | prueba y resultado, o motivo del descarte |

Flujo normal:

```text
python -I harness/scripts/beads.py create "Título" -t task -p 2 -l area:gbe --acceptance "..."
python -I harness/scripts/beads.py update ID --status confirmed --append-notes "Evidence (AAAA-MM-DD): ..."
python -I harness/scripts/beads.py update ID --claim
python -I harness/scripts/beads.py update ID --status resolved --append-notes "Resolution: commit/rutas"
python -I harness/scripts/beads.py close ID --reason "Verification (AAAA-MM-DD): comando: resultado"
```

Lo que `beads.py` exige (si no, se niega y explica por qué):

- `create` lleva `--acceptance` con un resultado comprobable y una etiqueta `area:<nombre>`.
- `--status confirmed` necesita criterios de aceptación y una nota `Evidence (AAAA-MM-DD): ...`.
- `--claim` sólo desde `confirmed` (el `--claim` nativo de bd sólo acepta `open`).
- `close` lleva `--reason` con `Verification`, `Discarded`, `Duplicate` o `Superseded` y una fecha; un cierre
  verificado exige que la tarea esté antes en `resolved`. Un descarte añade la etiqueta `outcome:discarded`.
- `--notes` en una tarea que ya tiene notas se convierte en `--append-notes` y avisa; para sustituirlas a propósito
  se escribe `--replace-notes` (en SNES dos agentes borraron así la evidencia de otros, 2026-11-21).

Un commit no basta para cerrar una tarea. Si la prueba aún no se puede ejecutar (p. ej. falta que el usuario
juegue la versión), queda `resolved`.

## Áreas y etiquetas

| Etiqueta | Para qué |
|---|---|
| `area:gbe` | la biblioteca `harness/common` (motor gbe); añade `mod:<módulo>` si es de uno (`mod:vq`) |
| `area:harness` | `harness/*.py`, `harness/scripts`, tests comunes, agentes, skills, CLAUDE.md |
| `area:docs` | `docs/` |
| `area:juego:<nombre>` | un juego (`area:juego:faro`) |
| `kind:<tipo>` | `bug`, `gap`, `idea`, `game`, `tool`, `doc`, `art`, `design`, `audio` (opcional) |
| `hito:<M>` | hito del GDD del juego (`hito:M2`) |

Los huecos de la biblioteca que encuentra un juego **no** se resuelven en el juego: se abre una tarea `area:gbe`
con `--acceptance`, se hace en un worktree con su prueba (`gb.selftest()`, `gbe_lab`) y se migra el juego después.

## Dependencias y coordinación

```text
python -I harness/scripts/beads.py dep add HIJA BLOQUEADORA
python -I harness/scripts/beads.py ready --json
python -I harness/scripts/beads.py dep tree ID
python -I harness/scripts/beads.py create "..." --parent EPIC ...     # subtarea de un epic
```

Beads decide qué está desbloqueado y hace el claim atómico de la tarea. `board.py` tiene otra responsabilidad:
reservar rutas y módulos antes de lanzar trabajo en paralelo, para que dos agentes no toquen lo mismo. La reserva
enlaza la misma tarea; si está en `confirmed`, el board la reclama antes de reservar:

```text
python -I harness/scripts/board.py claim AGENTE --bead ID --task "..." --owns RUTAS --uses MODULOS
python -I harness/scripts/board.py release AGENTE [--remove-worktree]
python -I harness/scripts/board.py doctor
```

## Almacenamiento y comprobación

La base Dolt embebida vive en `.beads/embeddeddolt/` y no se versiona. Los metadatos, la configuración y los hooks
de `.beads/` sí. `.beads/issues.jsonl` es una exportación automática para visores, no una copia de seguridad.
No hay remoto Dolt configurado: una copia en otra máquina necesita `bd dolt remote add` y `bd dolt push`
(no confundir con `git push`).

```text
python -I harness/scripts/beads.py check      # tareas activas sin aceptación o sin área
python -I harness/scripts/backlog.py audit    # estados contradictorios (lo usa kb.py check)
```
