---
name: project-faro
description: games/faro = commercial capture+survival RPG "FARO: la isla en la bruma" (GDD v0.1 2026-10-14); player fights creatures 1v1, visible creatures, hunger/camp/cooking, data-driven RPG kit
metadata:
  type: project
---

games/faro (GDD v0.1 drafted 2026-10-14, pending the user's 4 decisions: species count 48/64/36,
battle image 56x56/48x48/64x64, day/night yes/no, music driver hUGEDriver/GBT).
User-fixed requirements: player (not creatures) fights turn-based 1v1 on a battle screen; creatures
visible on a continuous 4-way smooth-scrolling 16x16-cell world with behaviours; hunger, camp, cooking
with discovered recipes; registry to relight the lighthouse; bicycle; save; towns/shops/hospitals;
**everything content is data** (tables, maps, scripts) so the setting can be swapped.

My design choices (check the GDD before reusing): island of Albor, protagonist Mar, grandmother Ines,
lamp rings opened by capture count (5/11/19/26/33/39) push back Bruma walls; 48 species, 7 families,
5 damage types; damage d = (POT * clamp((ATQ*RECIP[DEF])>>6,2,64))>>4; capture by quarter multipliers
(HP bands via shifts); MBC5 512 KB, 8 KB SRAM; engine items E1-E16 (gbe_world 4-way sectors with 3x3
WRAM cache, gbe_gact, gbe_script VM, gbe_tbox, gbe_list, gbe_tiles, tables.py, world.py, script.py,
pictures.py); layers: engine (harness) / RPG kit (games/faro/src/rpg, no content) / content (res).

**Why:** commercial product, 10-15 h; also grows the harness with RPG infrastructure.
**How to apply:** keep M1a engine before M1b slice (Varadero + Sendero + Faro, 6 species); bank 0 <= 14 KB
from the start; re-measure CPU estimates (12 actors ~9.6k T) once gbe_gact exists.
Related: [[feedback-commercial-scope]], [[project-dungeon]], [[user-taste]].
