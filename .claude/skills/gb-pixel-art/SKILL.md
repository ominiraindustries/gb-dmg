---
name: gb-pixel-art
description: Pixel art for Game Boy DMG - drawing 8x8 tiles, sprites, animations, tilesets and title logos in the repo's ASCII .tiles format with 4 shades, designed for the blurry DMG LCD, tile and sprite budgets, and reviewing art through rendered PNG previews. Load when creating or editing anything in games/*/res/*.tiles, harness/common/*.tiles, or judging how a game looks.
---

# Pixel art for the DMG

> Rules of the workspace (CLAUDE.md): art sources stay editable (`res/*.tiles`, `.screen`), generators only seed
> them; text only with the harness fonts (`harness/common/font*.tiles`); paid APIs (PixelLab...) only with permission.

## The format (`res/*.tiles`, converted at build time by `harness/asciitiles.py`)
```
@ HERO_IDLE_TL        <- optional label: becomes #define <STEM>_HERO_IDLE_TL <index>
..####..              8 rows x 8 chars per tile
.#----#.              .  shade 0 white  (TRANSPARENT in sprites)
#-+--+-#              -  shade 1 light gray
#------#              +  shade 2 dark gray
#-++++-#              #  shade 3 black
.#----#.
..####..
........
```
`;` starts a comment. Tiles are numbered in file order; code relies on consecutive runs
(e.g. DIGIT0..9), so **append new tiles at the end** or keep runs intact, and never rename a
label without updating the code (grep the label).

## Workflow (always)
1. Read the GDD asset list and budgets (`games/<game>/design/gdd.md`).
2. Draw tiles; larger objects as several tiles with labels `NAME_TL, NAME_TR, NAME_BL, NAME_BR`
   (16x16) or `NAME_0..N` for animation frames.
3. `python harness/gb.py preview <game>` and **Read the PNGs** in `games/<game>/build/preview/`:
   `tiles_<stem>.png` (sheet) and `screen_<name>.png` (mockups with the art in context).
4. Judge against the checklist below, iterate. Art is judged in context (a mockup screen), not alone.

## How the DMG shows art
- 4 shades only. BG uses BGP (4 shades); sprites use OBP0/OBP1 where **shade 0 is transparent**,
  so a sprite has 3 visible shades. Two sprite palettes allow e.g. a "light" and "dark" enemy variant.
- The original LCD is small, low-contrast and blurry with motion ghosting: details of 1 px vanish,
  light gray next to white is barely visible, fast-moving thin things smear.
- Sprites are 8x8 or 8x16 (one mode for all). A 16x16 character is 2 sprites in 8x16 mode.

## Style rules that work
- **Actors dark, backgrounds light.** Characters with black (`#`) outlines, BG mostly white/light
  with dark details sparse. The player must pop out instantly.
- **Silhouette first:** fill the shape in black, check it reads, then add interior shades.
- Outline: 1 px black around actors; interior shading light->dark with light from the top-left.
- Use light gray (`-`) for large fills and soft shading, dark gray (`+`) for depth, black for edges
  and key details (eyes). Avoid `-` directly on `.` for important features.
- Eyes and faces: 2x2 or 1x2 dark pixels, white highlight optional; big heads read better (chibi).
- Dithering (`-+-+` checker) for gradients in BG only; never on moving sprites (shimmer).
- BG tiles: design to tile seamlessly (check edges of repeating tiles in a mockup), vary repeating
  textures with 2-3 alternate tiles to break the grid.
- Leave the playfield calm: busy backgrounds hide actors and bullets.
- Text/UI: black on white. The shared fonts are bold (2 px vertical stems, 1 px bars): capitals 7x7,
  lowercase x-height 5 with descenders 1 px into row 7 (`harness/common/font*.tiles`). The user
  called the old thin 5x7 font "basura": thin 1 px strokes look spindly at 1x. New text art
  (logos, labels) matches this weight. Never reorder a font's tiles (code indexes by label order).

## Sprites and animation
- Hitbox != art: draw slightly bigger than the collision box.
- Walk cycle 2-4 frames at 8-10 frames per step; idle 1-2 frames; attack 2-3; hit 1 (+ blink).
- Store right-facing frames only; flip with `S_FLIPX` in code (say so in a comment in the .tiles).
- Moving objects >= 4x4 px with a dark outline (ghosting).
- Budget per scanline: 10 sprites. A 16-px-wide actor uses 2. Keep wide bosses as BG tiles.

- **Sprites have no white**: shade 0 is transparent, and OBP0 0xE4 / OBP1 0xD8 map no color to
  white. A sprite that must read over gray (a bullet over a boss in the BG) uses a black ring +
  light core, plus a 1 px light-gray halo to separate it from dark BG (games/shmup EBULLET_BOSS).
- Check sprites over every BG they will cross, including large BG bosses of mid gray: QA found
  bullets and explosions vanishing over the boss wings (same shade family).
- Blinking items (OBP0 <-> OBP1 swap) need one big area of a single shade so the swap is visible;
  0xD8 swaps colors 1 and 2 (light <-> dark gray).

## Tile budget
GBDK default: BG tiles 0-127 private, 128-255 shared with sprites; sprites 0-127 private.
Count unique tiles; reuse via flips (sprites only - DMG BG tiles cannot be flipped), shared corners,
symmetric designs. Report the count against the GDD budget when delivering.

## Pieced first-person views and big BG art (games/dungeon)
- Paint with a scratch script in SCREEN coordinates (one painter per piece), slice into tiles and
  dedupe globally: textures line up across pieces and dedup does the budget work.
- Same scale on all faces: near and far walls with different brick sizes looked disconnected
  (user). 4 courses per face ~58 tiles, 8 courses ~114 (measured).
- Lines that straddle tile rows double the tiles; keep side-wall courses inside one tile row.
- The background behind the pieces must be periodic in 16 px (2 tiles per row) or the count explodes.
- Bayer gradients on a narrow piece read as a dotted column: flat tones per depth instead.
- Monsters drawn as layered shapes, each with its own black outline, plus a light-gray halo, read
  over both black darkness and light walls.

## Visual questions to the user
When the user must choose between looks ("sin ejemplos visuales no puedo decidir"), render the
options side by side in one PNG (A/B, 1x and 3x) and let them pick from the image.

## Logos and title screens
Big text logos from BG tiles (each letter 2x2 or 3x3 tiles), drawn with thick strokes and a
1 px dark drop shadow; count tiles (logos eat budget: reuse repeated letters).

## Review checklist (write the answers when delivering art)
- [ ] Reads at 1x? (look at the preview's pixels mentally at real size: 160x144 is tiny)
- [ ] Player distinguishable from enemies and from BG in the mockup?
- [ ] Important details >= 2 px and not light-gray-on-white?
- [ ] Repeating BG tiles seamless; no accidental lines at tile edges?
- [ ] Labels follow conventions; consecutive runs intact; code references still valid?
- [ ] Tile count vs budget; sprites per scanline in the busiest mockup <= 10?
