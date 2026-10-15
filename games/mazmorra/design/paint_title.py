"""Paint the MADRIGUERA title screen in screen coordinates, slice to 8x8 tiles, dedupe, write
games/mazmorra/res/title.tiles + design/screens/title*.screen (ui-designer).

    python games/mazmorra/design/paint_title.py && python harness/gb.py preview mazmorra

Scene: the hill (cerro), one calm light-grey shape with no texture, with the burrow door in the
timber frame of the dungeon doors, a 'no-topos' sign, and Tilo as the player sprite (link.tiles
SIDE_A, bell cap) walking to the door, on a 2 px black ground line (pixel-artist, 2026-10-15). Logo MADRIGUERA
(outlined letters, white top / light bottom fill, 2 px dark shadow) and the subtitle painted with
proportional spacing (the 19 chars do not fit centred in 8 px cells). Text rows 14-17 stay white:
'Pulsa Start' / the menu are font tiles written by the code.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "harness"))
import asciitiles  # noqa: E402

W, H = 160, 144
img = [[0] * W for _ in range(H)]


def px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        img[y][x] = c


def get(x, y):
    return img[y][x] if 0 <= x < W and 0 <= y < H else 0


def rect(x0, y0, x1, y1, c):          # inclusive
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            px(x, y, c)


# ---------------------------------------------------------------- logo letters (20 px tall)
LETTERS = {
    "M": ["XXX.......XXX", "XXXX.....XXXX", "XXXXX...XXXXX", "XXXXXX.XXXXXX", "XXXXXXXXXXXXX",
          "XXXX.XXX.XXXX", "XXXX.XXX.XXXX", "XXXX..X..XXXX"] + ["XXXX.....XXXX"] * 12,
    "A": ["...XXXXXXX...", ".XXXXXXXXXXX.", "XXXXXXXXXXXXX"] + ["XXXX.....XXXX"] * 6
         + ["XXXXXXXXXXXXX"] * 4 + ["XXXX.....XXXX"] * 7,
    "D": ["XXXXXXXXX....", "XXXXXXXXXXX..", "XXXXXXXXXXXX.", "XXXX....XXXXX"]
         + ["XXXX.....XXXX"] * 12 + ["XXXX....XXXXX", "XXXXXXXXXXXX.", "XXXXXXXXXXX..", "XXXXXXXXX...."],
    "R": ["XXXXXXXXXX...", "XXXXXXXXXXXX.", "XXXXXXXXXXXXX"] + ["XXXX.....XXXX"] * 4
         + ["XXXXXXXXXXXXX", "XXXXXXXXXXXX.", "XXXXXXXXXXX..", "XXXXXXXXXX...", "XXXX..XXXX...",
            "XXXX...XXXX..", "XXXX...XXXXX.", "XXXX....XXXX."] + ["XXXX.....XXXX"] * 5,
    "I": ["XXXX"] * 20,
    "G": ["...XXXXXXX...", ".XXXXXXXXXXX.", "XXXXXXXXXXXXX", "XXXX.....XXXX"] + ["XXXX........."] * 4
         + ["XXXX...XXXXXX"] * 3 + ["XXXX.....XXXX"] * 6 + ["XXXXXXXXXXXXX", ".XXXXXXXXXXX.", "...XXXXXXX..."],
    "U": ["XXXX.....XXXX"] * 16 + ["XXXXX...XXXXX", "XXXXXXXXXXXXX", ".XXXXXXXXXXX.", "...XXXXXXX..."],
    "E": ["XXXXXXXXXXXXX"] * 4 + ["XXXX........."] * 4 + ["XXXXXXXXXX..."] * 4 + ["XXXX........."] * 4
         + ["XXXXXXXXXXXXX"] * 4,
}
for k, v in LETTERS.items():
    assert len(v) == 20 and len({len(r) for r in v}) == 1, k

LOGO_Y = 8
# 13-px letters on a 16 px pitch (and the I in an 8 px slot) all start at x = 4 mod 8, so their
# straight strokes fall on the same tile columns and dedupe between letters.
word = "MADRIGUERA"
x = 4
logo = set()
for ch in word:
    rows = LETTERS[ch]
    for b, row in enumerate(rows):
        for a, v in enumerate(row):
            if v == "X":
                logo.add((x + a, LOGO_Y + b))
    x += 8 if ch == "I" else 16

# ---------------------------------------------------------------- subtitle (proportional)
FONT = asciitiles.parse(ROOT / "harness/common/font.tiles")[0]
LOWER = asciitiles.parse(ROOT / "harness/common/font_lower.tiles")[0]
FONT_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-!.:?/"


def glyph(ch):
    t = LOWER[ord(ch) - 97] if ch.islower() else FONT[FONT_CHARS.index(ch)]
    cols = [i for i in range(8) if any(r[i] != "." for r in t)]
    return t, (min(cols), max(cols))


def text_prop(s, y, c=3):
    """Proportional text: glyph ink width + 1 px, space 4 px; centred."""
    parts = []
    for ch in s:
        if ch == " ":
            parts.append((None, 4))
        else:
            t, (a, b) = glyph(ch)
            parts.append(((t, a, b), b - a + 2))
    width = sum(w for _, w in parts) - 1
    x0 = (W - width) // 2
    for p, w in parts:
        if p:
            t, a, b = p
            for j, row in enumerate(t):
                for i in range(a, b + 1):
                    if row[i] != ".":
                        px(x0 + i - a, y + j, c)
        x0 += w
    return width


# ---------------------------------------------------------------- the hill and the burrow
# The hill is built from tile-aligned slopes (flat top, 1/4 shoulders, 1/2 flanks) so the ridge
# dedupes: a smooth curve made every ridge tile unique (141 tiles, budget 104).
HILL_BASE = 104


def hill_top(xx):
    m = xx if xx < 80 else 159 - xx        # mirror
    if m >= 64:
        return 64
    if m >= 32:
        return 64 + (63 - m) // 4
    return 72 + (31 - m) // 2


for xx in range(W):
    t = hill_top(xx)
    for yy in range(t, HILL_BASE):
        px(xx, yy, 1)                      # light grey earth
    px(xx, t, 3)                           # black ridge, 2 px
    px(xx, t + 1, 3)
# No earth texture: the user dislikes noise; the hill is one calm light-grey shape.

# burrow door: the timber frame of the dungeon doors (res/dungeon.tiles DOOR_*): 4 px posts
# '#-+#', a double lintel beam over them, cols 8-11 rows 10-12. The passage is dark here (outside,
# looking into the burrow).
DX0, DX1, DTOP = 64, 95, 80
# lintel: two beams (black / light / dark / black), the upper one overhangs the posts by 2 px
for yy, c in ((DTOP, 3), (DTOP + 1, 1), (DTOP + 2, 2), (DTOP + 3, 3)):
    for xx in range(DX0 - 2, DX1 + 3):
        px(xx, yy, c)
for yy, c in ((DTOP + 4, 1), (DTOP + 5, 2), (DTOP + 6, 3)):
    for xx in range(DX0, DX1 + 1):
        px(xx, yy, c)
for xx in (DX0 - 2, DX1 + 2):
    px(xx, DTOP + 1, 3); px(xx, DTOP + 2, 3)
# posts
for yy in range(DTOP + 4, HILL_BASE):
    for k, c in enumerate((3, 1, 2, 3)):
        px(DX0 + k, yy, c)
        px(DX1 - 3 + k, yy, c)
# passage: plain darkness (steps inside read as a shutter)
rect(DX0 + 4, DTOP + 7, DX1 - 4, HILL_BASE - 1, 3)

# sign 'no moles' (prohibido el paso a no-topos: a crossed-out mole) right of the door
SX, SY = 105, 80                                      # board in row 10, cols 13-14
rect(SX + 4, SY + 8, SX + 5, HILL_BASE - 1, 3)         # post
rect(SX, SY, SX + 10, SY + 7, 3)                      # board outline
rect(SX + 1, SY + 1, SX + 9, SY + 6, 0)               # white board
rect(SX + 3, SY + 2, SX + 7, SY + 5, 2)               # a little mole head
px(SX + 4, SY + 3, 3); px(SX + 6, SY + 3, 3)
for i in range(9):                                    # the 'no' bar
    px(SX + 1 + i, SY + 6 - (i * 5) // 8, 3)

# Tilo = the player sprite (res/link.tiles SIDE_A, bell-shaped cap), facing right towards the door.
# Sprite shade 0 is transparent: those pixels keep the hill. 16x16 tile-aligned (cols 5-6).
LINK = asciitiles.parse(ROOT / "games/mazmorra/res/link.tiles")
F = LINK[1]["SIDE_A"]
TX, TY = 40, HILL_BASE - 16
code = {".": None, "-": 1, "+": 2, "#": 3}
pts = []
for half in (0, 1):
    for vb in (0, 1):
        t = LINK[0][F + half * 2 + vb]
        for j, row in enumerate(t):
            for i, ch in enumerate(row):
                if code[ch] is not None:
                    px(TX + half * 8 + i, TY + vb * 8 + j, code[ch])
                    pts.append((TX + half * 8 + i, TY + vb * 8 + j))
inside = set(pts)
for (a, b) in pts:                         # white rim against the grey hill (sides and top)
    for dx, dy in ((1, 0), (-1, 0), (0, -1)):
        q = (a + dx, b + dy)
        if q not in inside and get(*q) == 1:
            px(q[0], q[1], 0)

# ---------------------------------------------------------------- ground (row 13)
# a plain 2 px black ground line under the hill; rows 14-17 are text rows
rect(0, HILL_BASE, W - 1, HILL_BASE + 1, 3)

# ---------------------------------------------------------------- logo on top
for (x, y) in logo:                         # white halo
    for dx in range(-1, 4):
        for dy in range(-1, 4):
            px(x + dx, y + dy, 0)
for (x, y) in logo:                         # drop shadow (2, 2) dark grey
    for s in (1, 2):
        px(x + s, y + s, 2)
for (x, y) in logo:
    edge = any((x + dx, y + dy) not in logo for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
    px(x, y, 3 if edge else (0 if y - LOGO_Y < 8 else 1))   # fill change on a tile row edge
SUB_Y = 40
text_prop("La campana del alba", SUB_Y, 3)


# ---------------------------------------------------------------- slice
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


for r in range(14, 18):                       # text rows stay white
    rect(0, r * 8, W - 1, r * 8 + 7, 0)
tiles, grid = slice_tiles()
blank = tuple("........" for _ in range(8))
if "--debug" in sys.argv:                     # per-row new-tile counts + raw PNG in the scratchpad
    from PIL import Image
    seen = set()
    for ty in range(18):
        new = [grid[ty][tx] for tx in range(20) if grid[ty][tx] not in seen and tiles[grid[ty][tx]] != blank]
        seen |= set(new)
        print(ty, len(set(new)), file=sys.stderr)
    im = Image.new("RGB", (W, H))
    for y in range(H):
        for x in range(W):
            im.putpixel((x, y), [(255, 255, 255), (170, 170, 170), (85, 85, 85), (0, 0, 0)][img[y][x]])
    im.resize((W * 3, H * 3), Image.NEAREST).save(sys.argv[-1])
    sys.exit(0)


POOL = [chr(c) for c in list(range(0x3B1, 0x3CA)) + list(range(0x391, 0x3AA)) + list(range(0x430, 0x450))
        + list(range(0x410, 0x430)) + list(range(0x5D0, 0x5EB))]
POOL = [c for c in POOL if c not in "ς΢"]

out = ["; MADRIGUERA - title screen art (pixel-artist; layout by the ui-designer): logo, subtitle, hill,",
       "; timber burrow door, sign, Tilo (= link.tiles SIDE_A). Painted in screen coordinates by design/paint_title.py, sliced and deduped: never",
       "; edit by hand, re-run the painter. Only used through screen_title_map / screen_title_menu_map",
       "; (LCD-off load of TITULO). Shares the BG slot with dungeon (GDD 7.2, <= 106). Empty cells use ui",
       "; BLANK (not stored here).", ""]
names = {}
for i, t in enumerate(tiles):
    if t == blank:
        continue
    names[i] = f"T{len(names):03d}"
    out.append(f"@ {names[i]}")
    out.extend(t)
(ROOT / "games/mazmorra/res/title.tiles").write_text("\n".join(out) + "\n", encoding="utf-8")
print("title tiles", len(names), file=sys.stderr)
# budget: the dungeon/title slot is max(dungeon, title). GDD 7.2 plans 104 + ui 24 + fonts 72 = 200;
# ui is 21, so title <= 107 keeps the same 200 total (the 200-211 margin stays free).
assert len(names) <= 106, len(names)
legend_of = {i: POOL[k] for k, i in enumerate(names)}


def screen(fname, header, texts, extra_legend=(), boxes=(), offset=0, center=()):
    """text: first tile of the proportional texts in the text slot; center: text names (ui.md 1.3)."""
    rows = [[legend_of.get(grid[ty][tx], ".") for tx in range(20)] for ty in range(18)]
    for r0, c0, r1, c1 in boxes:
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                ch = "."
                if r == r0:
                    ch = "<" if c == c0 else (">" if c == c1 else "_")
                elif r == r1:
                    ch = "(" if c == c0 else (")" if c == c1 else "=")
                elif c in (c0, c1):
                    ch = "{" if c == c0 else "}"
                rows[r][c] = ch
    for r, c, text in texts:
        assert c + len(text) <= 20, text
        for j, ch in enumerate(text):
            rows[r][c + j] = "." if ch == " " else ch
    rows = ["".join(r) for r in rows]
    used = {ch for r in rows for ch in r}
    lines = header + ["tilesets: title ui font_mini font_mini_lower font_mini_es"]
    lines += ([f"text: {offset}"] if offset else []) + ([f"center: {' '.join(center)}"] if center else [])
    lines += ["legend:"]
    lines += [f"{legend_of[i]} title:{names[i]}" for i in sorted(names) if legend_of[i] in used]
    lines += [f"{k} {v}" for k, v in extra_legend if k in used]
    lines += ["grid:"] + rows + ["sprites:"]
    for r in rows:
        assert len(r) == 20
    (ROOT / "games/mazmorra/design/screens" / fname).write_text("\n".join(lines) + "\n", encoding="utf-8")


UI = [("*", "ui:CURSOR"), ("<", "ui:FRAME_TL"), ("_", "ui:FRAME_T"), (">", "ui:FRAME_TR"),
      ("{", "ui:FRAME_L"), ("}", "ui:FRAME_R"), ("(", "ui:FRAME_BL"), ("=", "ui:FRAME_B"),
      (")", "ui:FRAME_BR"), ("?", "font_mini:QUESTION"), ("¿", "font_mini_es:QUEST_OPEN"),
      ("·", "font_mini:DOT")]
(ROOT / "games/mazmorra/design/screens").mkdir(parents=True, exist_ok=True)
screen("title.screen", [
    "; TITULO (scene title, M1). Generated by design/paint_title.py: edit there. LCD-off load of",
    "; screen_title_map (gbe_screen), SCX = SCY = 0, window off, hud_cut 0, no sprites. Logo rows 1-3,",
    "; subtitle row 5 (painted, proportional), hill rows 8-12, fog row 12, ground row 13, text rows 14-17.",
    "; 'Pulsa Start' (centred, text slot tiles 0-10) blinks 30/30 f: the code writes BLANK over",
    "; SCREEN_TITLE_LEN_PULSA_START cells. All title texts (0-70) are loaded once with the scene.",
], [(15, 4, "Pulsa Start")], center=["PULSA_START"])
screen("title_menu.screen", [
    "; TITULO, menu state (M3, after Start when a save exists). Same art; the code copies rows 14-17",
    "; of screen_title_menu_map over the 'Pulsa Start' rows. Cursor (BG) col 4, options col 5, 2-row",
    "; pitch, left-aligned. Without a save the title goes straight to INTRO on Start (no menu).",
    "; Text slot tiles 11-32 (text: 11): no clash with 'Pulsa Start' when B goes back.",
], [(14, 4, "*Continuar"), (16, 5, "Nueva partida")], UI, offset=11)
screen("title_borrar.screen", [
    "; TITULO, confirm (M3): 'Nueva partida' with a save. Box rows 11-17 over the scene (code copies",
    "; rows 11-17 of screen_title_borrar_map; B/No restores rows 11-17 from screen_title_menu_map).",
    "; Starts on 'No'. Cursor col 5 (Si) / col 11 (No). Question centred; text slot tiles 33-70.",
], [(12, 1, "¿Empezar de nuevo?"), (13, 2, "Se borrara todo·"), (15, 6, "Si"), (15, 11, "*No")],
   UI, boxes=[(11, 0, 17, 19)], offset=33, center=["EMPEZAR_DE_NUEVO", "SE_BORRARA_TODO"])

