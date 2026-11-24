---
name: kb
description: The GBDMG knowledge base - one command over lessons, technique cards, studies, the gbe API (gbe.h, docs/api), Beads tasks, guides and rules, game GDDs and the hardware references (Pan Docs, GBDK docs), plus SQL over the structured data. Use at the START of any Game Boy task (kb.py brief), whenever you need a technique, a measured number or a hardware detail, to ask "is there a gbe function for X", before proposing a new engine module, and to file a finding (gap, lesson, bug) you will not integrate yourself.
---

# kb: ask the knowledge base first, read only what it points to

```bash
python -I harness/scripts/kb.py brief --role gb-game-dev --task "what you are about to do"   # FIRST, in every task
python -I harness/scripts/kb.py query "scroll horizontal streaming" [--kind tecnica|lesson|study|api|backlog|tool|doc|game|project|ref]
python -I harness/scripts/kb.py card SC1          # a technique card in full (or a lesson id, or a Beads id: GB-xxx)
python -I harness/scripts/kb.py sql "SELECT id,title FROM backlog WHERE status='open' AND area='gbe'"   # no query = tables
python -I harness/scripts/beads.py ready --json   # live, dependency-aware work
python -I harness/scripts/beads.py show GB-xxx    # task, evidence and history
```

1. **Start** with `brief` (lessons for your role, technique cards, open Beads of the modules or games you name, gbe
   API, guides, GDD sections). Hits are `path:line`: open the file at that line, never whole files. Grep only when
   kb gives nothing.
2. **Function for X?** `query "X" --kind api`. Hardware: `--kind ref` (Pan Docs, GBDK). Earlier games: `--kind game`.
   An open Beads task or a "pendiente" card = a known gap: cite its id instead of inventing an API.
3. If the task produced genuinely new, reusable evidence you will not integrate, add an optional
   **"Lecciones para mi rol"**, **"Huecos de gbe"** or **"Bugs encontrados"** section to your final report. Do not
   create findings to satisfy a template. The SubagentStop hook files the sections that are present.
4. Beads is the task source of truth (`docs/harness/beads.md`). Never edit `docs/tecnicas/index.json` or `docs/api`
   by hand (generated).

Where things go so kb finds them, and how to write them: `docs/harness/kb.md`.

Coordinator: `kb.py check` (links, cards, lessons, Beads, untriaged inbox, compliance); `kb.py test` (queries that
must hit); `kb.py inbox list --status new`; `kb.py inbox apply FILE` or
`kb.py inbox triage ID --to lesson|backlog|tecnica|discard [--ref id|reason] [--area gbe --bkind gap --priority 2]`.
