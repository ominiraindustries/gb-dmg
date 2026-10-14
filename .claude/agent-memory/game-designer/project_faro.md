---
name: project-faro
description: games/faro = commercial capture+survival RPG "FARO: la isla en la bruma" (GDD v1.1 approved, M1b data tables written 2026-10-14); protagonist Leo, data-driven RPG kit
metadata:
  type: project
---

games/faro: GDD approved v1.0 (2026-10-14), v1.1 the same day when I wrote the M1b data tables.
Decisions taken: 48 species, battle image 56x56, day/night by steps (M2), hUGEDriver (M2).
User-fixed requirements: player (not creatures) fights turn-based 1v1; creatures visible on a 4-way
smooth-scrolling 16x16-cell world with behaviours; hunger, camp, cooking with discovered recipes;
registry relights the lighthouse; bicycle; save; towns/shops/clinics; **everything content is data**.

Current facts (check the GDD before reusing): protagonist **Leo** (boy, 14; was "Mar" in v0.1),
grandmother Ines, cook Tomasa. UI designer's short names (ui.md §17) are ACCEPTED: Cuchillo, Farol de
plata/bruma/maestro, Madera (not Lena), Galleta, Somnifero, Vendaje, VEN for poisoned, short dish names.
Data lives in games/faro/res/data/*.tbl (16 tables incl. rules.tbl = every loose balance constant as
RULE_*; statuses/buffs are "rule tables" whose row order the kit relies on). Text columns: no '+'/'%'
in the font; item descriptions 2 x 12 so they fit all three UI layouts. Technique multipliers are in
eighths (`(d*mul)>>3`, Golpe suave 6). tests/test_data.py = GDD 3.10 examples (seed of battle_model.py).
Fixed ids other agents use: LOOK ABUELA/PESCADOR/VECINA (spr 0/16/32), SPAWN PLAYA_VAR/SENDERO/CABO/CLARO,
FORAGE BAYAS/RAMAS. flags.txt/vars.txt are append-only.

**Why:** commercial product, 10-15 h; also grows the harness with RPG infrastructure.
**How to apply:** keep M1a engine before M1b slice; bank 0 <= 14 KB; when adding species/items, append
rows (row order = registry number / save ids); re-run test_data.py after any table change.
Related: [[feedback-commercial-scope]], [[project-dungeon]], [[user-taste]].
