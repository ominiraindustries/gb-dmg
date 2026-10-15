---
name: mazmorra-style
description: MADRIGUERA (games/mazmorra) first art pass 2026-10-15 - burrow look, Tilo's bell cap, babosa, and the title-ownership clash with the ui-designer
metadata:
  type: project
---
First art pass (not yet user-reviewed when written):
- Burrow walls: flat dark-gray earth mass with lumpy black-rimmed overhangs (8 px period), a timber
  retaining board on the top face, light 4 px side faces, white calm floor with rare pebbles (FLOOR2).
  Doors = timber posts + lintel with a light-gray passage (dark passage vanished into the earth).
  Whole room painted in screen coords and sliced: 50 tiles for all M1 metatiles.
- Tilo: bell-shaped dark cap (narrow crown, flared black rim) = silhouette identity; first tries read
  as mushroom/helmet until the crown was narrowed. Raised arms at 16 px read as rabbit ears: avoid.
- Babosa: dark mound + light belly band + two stalk eyes (4x4 eyeballs); profile slugs read as shoes.
- The ui-designer painted title.tiles with their own generator (design/paint_title.py) in parallel,
  although the brief gave the title to me. I did not overwrite it; their Tilo and door don't match.
**Why:** two agents writing one tileset would clobber each other.
**How to apply:** before drawing a shared screen asset, check games/<game>/design for another agent's
generator and coordinate via the report instead of overwriting.
Related: [[faro-style]], [[font-lessons]]
