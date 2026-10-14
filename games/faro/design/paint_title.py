"""Paint the FARO title screen in screen coordinates, slice to 8x8 tiles, dedupe,
write games/faro/res/title.tiles + design/screens/title.screen and title_menu.screen."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
W, H = 160, 144
img = [[0] * W for _ in range(H)]
# mask of cells that are text (font) - painter leaves them white
TEXT_ROWS = {}


def px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        img[y][x] = c


def rect(x0, y0, x1, y1, c):          # inclusive
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            px(x, y, c)


BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def dither(x0, y0, x1, y1, level, c):   # level 0..16 = coverage
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if BAYER[y & 3][x & 3] < level:
                px(x, y, c)


# ---------------------------------------------------------------- logo letters
def letter_mask(ch):
    """22x24 mask (set of (x,y)) for F A R O, stroke 6."""
    m = set()

    def r(x0, y0, x1, y1):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                m.add((x, y))

    def cut(*pts):
        for p in pts:
            m.discard(p)

    if ch == "F":
        r(0, 0, 21, 5); r(0, 0, 5, 23); r(0, 10, 16, 15)
        cut((0, 0), (21, 0), (21, 5), (16, 10), (16, 15), (0, 23), (5, 23))
    elif ch == "A":
        r(0, 6, 5, 23); r(16, 6, 21, 23); r(0, 13, 21, 17)
        r(3, 0, 18, 5); r(1, 2, 20, 6)
        cut((1, 2), (20, 2), (0, 23), (5, 23), (16, 23), (21, 23), (3, 0), (18, 0))
    elif ch == "R":
        r(0, 0, 5, 23); r(0, 0, 17, 5); r(0, 10, 17, 15); r(15, 2, 21, 13)
        cut((21, 2), (21, 13), (20, 2), (20, 13), (0, 0), (0, 23), (5, 23))
        r(16, 1, 18, 2); r(16, 13, 18, 14)
        for i in range(9):                      # leg
            r(9 + i, 15 + i, 14 + i, 15 + i)
        r(16, 22, 21, 23)
        cut((21, 23),)
    elif ch == "O":
        cx, cy = 10.5, 11.5
        for y in range(24):
            for x in range(22):
                d = ((x - cx) / 11.0) ** 2 + ((y - cy) / 12.0) ** 2
                if d <= 1.0 and ((x - cx) / 5.2) ** 2 + ((y - cy) / 6.2) ** 2 > 1.0:
                    m.add((x, y))
    return m


LOGO_X, LOGO_Y, GAP = 26, 8, 6
masks = []
x = LOGO_X
for ch in "FARO":
    masks.append((x, letter_mask(ch)))
    x += 22 + GAP
logo_pixels = {(x0 + a, LOGO_Y + b) for x0, m in masks for a, b in m}

# ---------------------------------------------------------------- sky fog (row 0 and wisps)
# clean sky: the fog lives on the horizon

# ---------------------------------------------------------------- sea, horizon, fog bank
SEA_Y = 116
rect(0, SEA_Y, W - 1, H - 1, 1)              # light sea
for y in range(SEA_Y, H):
    k = y - SEA_Y
    for x in range(W):
        # wave crests: short dark dashes, period 16 px, rows every 6 px, offset per band
        band = k // 6
        if k % 6 == 2 and (x + band * 5) % 16 < 5:
            px(x, y, 2)
        if k % 6 == 3 and (x + band * 5 + 1) % 16 < 3:
            px(x, y, 2)
rect(0, SEA_Y, W - 1, SEA_Y, 2)              # horizon line
# fog bank above the horizon (dither fading up)
dither(0, SEA_Y - 8, W - 1, SEA_Y - 7, 2, 1)
dither(0, SEA_Y - 6, W - 1, SEA_Y - 4, 5, 1)
dither(0, SEA_Y - 3, W - 1, SEA_Y - 1, 9, 1)
# ---------------------------------------------------------------- lighthouse (right)
LX = 140                                    # tower centre x
# rocks: black silhouette, dark gray lit facets on top, a light rim where the fog touches
import math
def rock_top(xx):
    return int(105 + 3 * math.sin(xx * 0.35) + 2 * math.sin(xx * 0.9) + max(0, (124 - xx)) * 0.55)
for xx in range(112, W):
    t = rock_top(xx)
    for yy in range(t, SEA_Y + 6):
        c = 3
        if yy - t < 2:
            c = 2
        px(xx, yy, c)
    if (xx // 5) % 3 == 0:
        px(xx, t, 1)
# rock shadow facets
for xx in range(118, W, 9):
    t = rock_top(xx)
    for k in range(3):
        px(xx + k, t + 3 + k, 2)
# foam where rocks meet the sea
for xx in range(108, W):
    if (xx * 5) % 7 < 3:
        px(xx, SEA_Y + 6, 0)
        px(xx, SEA_Y + 7, 1)
# tower: from y 72 (top, half width 7) to y 110 (bottom, half width 10)
TOP, BOT = 72, 106
for yy in range(TOP, BOT + 1):
    hw = 7 + (yy - TOP) * 3 // (BOT - TOP)
    band = ((yy - TOP + 2) // 9) % 2
    for xx in range(LX - hw, LX + hw + 1):
        if xx in (LX - hw, LX + hw):
            c = 3
        elif band:
            c = 3 if xx > LX + hw - 4 else 2   # dark bands, black shade on the right
        else:
            c = 1 if xx > LX + hw - 4 else 0   # white bands, light shade on the right
        px(xx, yy, c)
# door + window
rect(LX - 2, 103, LX + 1, 110, 3)
rect(LX - 1, 84, LX, 87, 3)
# gallery (balcony) and railing
rect(LX - 10, 70, LX + 10, 71, 3)
rect(LX - 9, 72, LX + 9, 72, 2)
for xx in range(LX - 10, LX + 11, 4):
    rect(xx, 66, xx, 69, 3)
rect(LX - 10, 66, LX + 10, 66, 3)
# lantern room: black frame, white glass glowing, light halo inside the frame
rect(LX - 6, 56, LX + 6, 65, 3)
rect(LX - 5, 57, LX + 5, 64, 1)
rect(LX - 4, 58, LX + 4, 63, 0)
rect(LX, 57, LX, 64, 3)                    # centre mullion
rect(LX - 1, 59, LX + 1, 62, 0)
# roof (dome) + finial
for i in range(6):
    rect(LX - 7 + i, 55 - i, LX + 7 - i, 55 - i, 3)
rect(LX - 7, 55, LX + 7, 55, 3)
rect(LX - 2, 51, LX - 1, 51, 2)
rect(LX, 46, LX, 49, 3)
px(LX, 45, 2)

# ---------------------------------------------------------------- logo on top
# white halo around letters so fog never touches them
for (x, y) in logo_pixels:
    for dx in range(-2, 5):
        for dy in range(-2, 5):
            px(x + dx, y + dy, 0)
for (x, y) in logo_pixels:                   # drop shadow (3, 3) dark gray, solid
    for s in (1, 2, 3):
        px(x + s, y + s, 2)
# letters: black outline 1 px, light gray upper fill, dark gray lower fill (light over the sea)
for (x, y) in logo_pixels:
    edge = any((x + dx, y + dy) not in logo_pixels for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
    if edge:
        c = 3
    else:
        c = 0 if y - LOGO_Y < 12 else 1
    px(x, y, c)
# lens inside the O: concentric rings (the six rings of the lantern lens)
ox = masks[3][0]
for yy in range(24):
    for xx in range(22):
        d = ((xx - 10.5) / 5.0) ** 2 + ((yy - 11.5) / 6.0) ** 2
        if d <= 1.0:
            ring = int(d * 3.2)
            px(ox + xx, LOGO_Y + yy, [0, 1, 0, 2][min(ring, 3)])
# ---------------------------------------------------------------- text areas stay white
TEXT = {}          # row -> (col, text)


def clear_row(row, c0, c1):
    rect(c0 * 8, row * 8, c1 * 8 + 7, row * 8 + 7, 0)


def slice_tiles():
    tiles, index, grid = [], {}, []
    for ty in range(18):
        row = []
        for tx in range(20):
            t = tuple("".join(".-+#"[img[ty * 8 + j][tx * 8 + i]] for i in range(8)) for j in range(8))
            if t not in index:
                index[t] = len(tiles)
                tiles.append(t)
            row.append(index[t])
        grid.append(row)
    return tiles, grid


# text cells: subtitle row 5, menu rows 9/11/13 cols 3-15 (cleared to white)
clear_row(5, 0, 19)
for r in range(8, 13):
    clear_row(r, 2, 15)

tiles, grid = slice_tiles()
blank = tuple("........" for _ in range(8))
print("unique tiles", len(tiles), file=sys.stderr)

# legend chars: non-ASCII symbols (never letters of the text)
POOL = [chr(c) for c in list(range(0x3B1, 0x3CA)) + list(range(0x391, 0x3AA)) + list(range(0x430, 0x450))
        + list(range(0x410, 0x430)) + list(range(0x5D0, 0x5EB)) + list(range(0x3041, 0x3097))]
POOL = [c for c in POOL if c != "\u03c2" and c != "\u03a2"]

# title.tiles: BLANK-equivalent tile not stored (use ui BLANK); others labelled TITLE_nnn
out = ["; FARO - title screen art (ui-designer): logo FARO (the O is the lighthouse lens), lighthouse,",
       "; rocks, sea, fog. Painted in screen coordinates and sliced/deduped by a script; the tiles are",
       "; only used through screen_title_map / screen_title_menu_map (LCD-off load of the TITLE state).",
       "; Loaded into the tileset slot (GDD 7.2: 'Titulo: logo <= 150 + fuentes'). Empty cells use",
       "; ui BLANK. Do not reorder by hand: re-run the painter.", ""]
names = {}
k = 0
for i, t in enumerate(tiles):
    if t == blank:
        continue
    names[i] = f"T{k:03d}"
    out.append(f"@ {names[i]}")
    out.extend(t)
    k += 1
(ROOT / "games/faro/res/title.tiles").write_text("\n".join(out) + "\n", encoding="utf-8")
print("title tiles", k, file=sys.stderr)

legend_of = {}
for i in names:
    legend_of[i] = POOL[len(legend_of)]


def screen(fname, header, texts, sprites=()):
    rows = []
    for ty in range(18):
        s = ""
        for tx in range(20):
            i = grid[ty][tx]
            s += legend_of.get(i, ".")
        rows.append(list(s))
    for r, c, text in texts:
        for j, ch in enumerate(text):
            rows[r][c + j] = "." if ch == " " else ch
    rows = ["".join(r) for r in rows]
    for r in rows:
        assert len(r) == 20, r
    lines = header + ["tilesets: ui title font font_lower font_es", "legend:"]
    lines += [f"{legend_of[i]} title:{names[i]}" for i in sorted(names)]
    lines += ["* CURSOR", "grid:"] + rows + ["sprites:"] + list(sprites)
    (ROOT / "games/faro/design/screens" / fname).write_text("\n".join(lines) + "\n", encoding="utf-8")


(ROOT / "games/faro/design/screens").mkdir(parents=True, exist_ok=True)
SUB = (5, 0, "la isla en la bruma")
screen("title.screen", [
    "; TITLE, first state (M1b). LCD-off load (gbe_screen) of screen_title_map, SCX = SCY = 0, window off.",
    "; Logo rows 1-4 (the O is the lighthouse lens), subtitle row 5, lighthouse cols 15-18 rows 5-13,",
    "; sea rows 14-17. 'Pulsa Start' blinks 30/30 f (code blanks SCREEN_TITLE_LEN_PULSA_START tiles).",
    "; Beam sprites from the lantern (x 136, y 54) with OAM priority bit set: the beam passes BEHIND",
    "; the logo, the text and the tower (only shows on white). See ui.md 2.",
], [SUB, (10, 4, "Pulsa Start")],
   ["; 8x16 sprites are listed as their two 8x8 halves because the preview draws 8x8 sprites.",
    "; Leo (leo.tiles SIDE_A) on the rocks looking at the lighthouse: OAM 0-1 at (112, 95).",
    "leo:16 112 95", "leo:17 112 103", "leo:18 120 95", "leo:19 120 103",
    "; one beam frame (long, pointing left), OAM 2-9; the code animates it, see ui.md 2."] +
   [f"uispr:{i + h} {x} {52 + 8 * h}" for i, x in ((14, 128), (16, 120), (18, 112), (20, 104),
                                                (22, 96), (24, 88), (26, 80), (28, 72)) for h in (0, 1)])
screen("title_menu.screen", [
    "; TITLE, menu state (after Start). Same art; rows 8-13 cols 2-13 come from this map (code copies",
    "; the 6x12 block from screen_title_menu_map). 'Continuar' only with a valid save: without one the",
    "; code blanks SCREEN_TITLE_MENU_LEN_CONTINUAR tiles and the cursor starts on 'Nueva partida'.",
    "; BG cursor at col 3, 2-row pitch. Opciones opens OPCIONES (opciones.screen).",
], [SUB, (8, 3, "*Continuar"), (10, 4, "Nueva partida"), (12, 4, "Opciones")])
