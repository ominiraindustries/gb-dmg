"""First-person grid view (dungeon crawlers): view pieces in ASCII, a reference compositor and PNGs.

    python harness/fpview.py <game>                 canonical views -> build/preview/view_*.png
    python harness/fpview.py <game> X Y F [level]   the view from cell (X, Y) facing F (0 N 1 E 2 S 3 W)

The view is 20x12 tiles (160x96 px) built far to near from pieces (games/dungeon GDD 2.3): exact
perspective with depth planes at z = 2, 3, 4, every edge on a multiple of 8 px, so each piece is a
set of rows of whole tiles. Range 3 cells.

Piece file res/view.pcs (drawn by the pixel-artist):
    ; comment
    @ tileset walls             tile references below are labels or indices of res/walls.tiles
    @ base 66                   VRAM index of that tileset's tile 0 (added in the C tables)
    legend:
    # WALL_A                    char -> tile label or index ('.' is always transparent)
    piece BG                    then exactly H lines of W chars (size from GEOMETRY below)
    ...
Every row of a piece must be ONE contiguous run of non-'.' chars (the asm blitter copies one run
per row). Geometry (column, row, width, height) is fixed per piece name: see GEOMETRY.

Cells (games/dungeon GDD 2.0): 0 FLOOR, 1 WALL, 2 DOOR, 3 LOCKED, 4 DOOR_OPEN, 5 UP, 6 DOWN.
Solid for the view: WALL DOOR LOCKED UP DOWN. Off the map = WALL. Facing 0 N (dy -1), 1 E, 2 S, 3 W.

Output (build/gen/view.c/.h, built by gb.py when res/view.pcs exists; can go in "banked_res"):
    const uint8_t view_pcs[]       per piece: row0, rows, then per row: col, len, tiles[len]
    const uint16_t view_piece[]    offset of each piece in view_pcs (VIEW_P_<NAME> order)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FLOOR, WALL, DOOR, LOCKED, DOOR_OPEN, UP, DOWN = range(7)
SOLID = {WALL, DOOR, LOCKED, UP, DOWN}
DX, DY = (0, 1, 0, -1), (-1, 0, 1, 0)
W, H = 20, 12

# name: (col, row, width, height). Fronts F<d><side>, sides S<d><side>, D/E = door/stairs fronts,
# LK = lock or seal drawn over a door front.
GEOMETRY = {
    "BG": (0, 0, 20, 12),
    "F3L2": (0, 4, 1, 4), "F3L1": (1, 4, 6, 4), "F3C": (7, 4, 6, 4), "D3": (7, 4, 6, 4), "E3": (7, 4, 6, 4),
    "F3R1": (13, 4, 6, 4), "F3R2": (19, 4, 1, 4),
    "S2L2": (0, 3, 1, 6), "S2L1": (6, 3, 1, 6), "S2R1": (13, 3, 1, 6), "S2R2": (19, 3, 1, 6),
    "F2L1": (0, 3, 6, 6), "F2C": (6, 3, 8, 6), "D2": (6, 3, 8, 6), "E2": (6, 3, 8, 6), "F2R1": (14, 3, 6, 6),
    "S1L1": (4, 2, 2, 8), "S1R1": (14, 2, 2, 8),
    "F1L1": (0, 2, 4, 8), "F1C": (4, 2, 12, 8), "D1": (4, 2, 12, 8), "E1": (4, 2, 12, 8), "F1R1": (16, 2, 4, 8),
    "S0L": (0, 0, 4, 12), "S0R": (16, 0, 4, 12),
    "LK1": (9, 5, 2, 2), "LK2": (9, 5, 2, 1), "LK3": (9, 5, 1, 1),
}
NAMES = list(GEOMETRY)

# Painting order (far to near): (layer pieces with their view cell (d, l)), GDD 2.3
FRONTS = {3: [(-2, "F3L2"), (-1, "F3L1"), (0, "F3C"), (1, "F3R1"), (2, "F3R2")],
          2: [(-1, "F2L1"), (0, "F2C"), (1, "F2R1")],
          1: [(-1, "F1L1"), (0, "F1C"), (1, "F1R1")]}
SIDES = {2: [(-2, "S2L2"), (-1, "S2L1"), (1, "S2R1"), (2, "S2R2")],
         1: [(-1, "S1L1"), (1, "S1R1")],
         0: [(-1, "S0L"), (1, "S0R")]}
ORDER = [("F", 3), ("S", 2), ("F", 2), ("S", 1), ("F", 1), ("S", 0)]


class Pieces:
    def __init__(self, path, pieces, tileset, base):
        self.path, self.pieces, self.tileset, self.base = Path(path), pieces, tileset, base


def parse(path, labels=None):
    """{name: [[tile or None] * w] * h} with tile = index in the tileset (no base)."""
    path = Path(path)
    legend, pieces, tileset, base = {}, {}, None, 0
    lines = path.read_text(encoding="utf-8").splitlines()
    i, section = 0, None
    while i < len(lines):
        raw = lines[i]
        line = raw.split(";", 1)[0].rstrip()
        i += 1
        if not line.strip():
            continue
        parts = line.split()
        where = f"{path}:{i}"
        if parts[0] == "@":
            if parts[1] == "tileset":
                tileset = parts[2]
            elif parts[1] == "base":
                base = int(parts[2], 0)
            else:
                raise ValueError(f"{where}: unknown '@ {parts[1]}'")
        elif parts[0] == "legend:":
            section = "legend"
        elif parts[0] == "piece":
            name = parts[1]
            if name not in GEOMETRY:
                raise ValueError(f"{where}: unknown piece {name} (known: {', '.join(NAMES)})")
            c, r, w, h = GEOMETRY[name]
            rows = []
            for k in range(h):
                if i >= len(lines):
                    raise ValueError(f"{where}: piece {name} needs {h} lines of {w}")
                row = lines[i].rstrip("\n")
                i += 1
                row = row[:w].ljust(w, ".")
                cells = []
                for x, ch in enumerate(row):
                    if ch == ".":
                        cells.append(None)
                    elif ch in legend:
                        cells.append(legend[ch])
                    else:
                        raise ValueError(f"{path}:{i}: piece {name} char {ch!r} not in the legend")
                run = [x for x, t in enumerate(cells) if t is not None]
                if run and run[-1] - run[0] + 1 != len(run):
                    raise ValueError(f"{path}:{i}: piece {name} row {k}: tiles must form one contiguous run")
                rows.append(cells)
            if name in pieces:
                raise ValueError(f"{where}: piece {name} defined twice")
            pieces[name] = rows
            section = None
        elif section == "legend":
            ch, ref = raw[0], raw[2:].split(";", 1)[0].strip()
            if ch == ".":
                raise ValueError(f"{where}: '.' is reserved for transparent")
            if ref.isdigit():
                legend[ch] = int(ref)
            elif labels and ref.upper() in labels:
                legend[ch] = labels[ref.upper()]
            else:
                raise ValueError(f"{where}: tile '{ref}' is not an index or a label of {tileset}")
        else:
            raise ValueError(f"{where}: expected '@', 'legend:' or 'piece NAME'")
    return Pieces(path, pieces, tileset, base)


def cell(dmap, x, y):
    if (x | y) & 0xF0 or x < 0 or y < 0:
        return WALL
    return dmap[(y << 4) | x]


def view_cell(dmap, px, py, pf, d, l):
    r = (pf + 1) & 3
    return cell(dmap, px + d * DX[pf] + l * DX[r], py + d * DY[pf] + l * DY[r])


def pieces_for(dmap, px, py, pf):
    """The pieces painted for a position, in painting order (GDD 2.3)."""
    out = ["BG"]
    for kind, d in ORDER:
        for l, name in (FRONTS if kind == "F" else SIDES)[d]:
            t = view_cell(dmap, px, py, pf, d, l)
            if t not in SOLID:
                continue
            if kind == "F" and l == 0:
                if t in (DOOR, LOCKED, UP):
                    out.append(f"D{d}")
                elif t == DOWN:
                    out.append(f"E{d}")
                else:
                    out.append(name)
                if t in (LOCKED, UP):
                    out.append(f"LK{d}")
            else:
                out.append(name)
    return out


def compose(pcs, dmap, px, py, pf):
    """20x12 VRAM tile indices (base added) of the view; missing pieces are skipped."""
    view = [[0] * W for _ in range(H)]
    for name in pieces_for(dmap, px, py, pf):
        if name not in pcs.pieces:
            continue
        c, r, w, h = GEOMETRY[name]
        for k, row in enumerate(pcs.pieces[name]):
            for x, t in enumerate(row):
                if t is not None:
                    view[r + k][c + x] = pcs.base + t
    return view


def to_c(pcs, out_dir):
    out_dir = Path(out_dir)
    blob, offs = [], []
    for name in NAMES:
        offs.append(len(blob))
        if name not in pcs.pieces:
            blob += [0, 0]                          # absent: zero rows
            continue
        c, r, w, h = GEOMETRY[name]
        rows = pcs.pieces[name]
        blob += [r, h]
        for row in rows:
            run = [x for x, t in enumerate(row) if t is not None]
            if not run:
                blob += [0, 0]
                continue
            blob += [c + run[0], len(run)] + [pcs.base + row[x] for x in run]
    out_dir.mkdir(parents=True, exist_ok=True)
    body = ",\n".join("    " + ", ".join(str(b) for b in blob[i:i + 20]) for i in range(0, len(blob), 20))
    (out_dir / "view.c").write_text(
        "// Generated from view.pcs by harness/fpview.py - do not edit\n#include <stdint.h>\n\n"
        f"const uint8_t view_pcs[] = {{\n{body}\n}};\n"
        f"const uint16_t view_piece[] = {{ {', '.join(map(str, offs))} }};\n", encoding="utf-8")
    ids = "\n".join(f"    VIEW_P_{n} = {i}," for i, n in enumerate(NAMES))
    (out_dir / "view.h").write_text(
        "// Generated from view.pcs by harness/fpview.py - do not edit\n#pragma once\n#include <stdint.h>\n\n"
        f"enum {{\n{ids}\n    VIEW_P_COUNT = {len(NAMES)}\n}};\n"
        "// per piece: row0, rows, then per row: col, len, tiles[len] (one contiguous run per row)\n"
        "extern const uint8_t view_pcs[];\nextern const uint16_t view_piece[];\n", encoding="utf-8")
    return out_dir / "view.c"


# ---------------------------------------------------------------- canonical scenes (for the artist)
def _scene(rows):
    """rows: list of strings (map around the hero), '#' wall '.' floor 'D' door 'L' locked 'U' up
    'X' down; the hero is at the bottom row middle facing north. Returns (dmap, px, py, pf)."""
    m = [WALL] * 256
    chars = {"#": WALL, ".": FLOOR, "D": DOOR, "L": LOCKED, "U": UP, "X": DOWN, "o": DOOR_OPEN, "@": FLOOR}
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            m[(y << 4) | x] = chars[ch]
            if ch == "@":
                px, py = x, y
    return m, px, py, 0


SCENES = {
    "corridor": ["#####", "##.##", "##.##", "##.##", "##@##"],
    "cross":    ["#####", "##.##", ".....", "##.##", "##@##"],
    "room":     [".....", ".....", ".....", ".....", "..@.."],
    "door1":    ["#####", "##D##", "##@##"],
    "door2":    ["#####", "##D##", "##.##", "##@##"],
    "door3":    ["##D##", "##.##", "##.##", "##@##"],
    "locked1":  ["#####", "##L##", "##@##"],
    "stairs1":  ["#####", "##X##", "##@##"],
    "stairs3":  ["##X##", "##.##", "##.##", "##@##"],
    "wall1":    ["#####", "#####", "##@##"],
    "turn_l":   ["#####", "#...#", "#.###", "#.@##"],
}


def render(view, images, scale=3):
    from PIL import Image
    img = Image.new("RGB", (W * 8, H * 8), (255, 255, 255))
    for y, row in enumerate(view):
        for x, t in enumerate(row):
            if t in images:
                img.paste(images[t], (x * 8, y * 8))
    return img.resize((W * 8 * scale, H * 8 * scale), Image.NEAREST)


def preview(gdir, out=None):
    """Canonical views as one labelled sheet + one PNG each. Returns the written paths."""
    import preview as pv
    from PIL import Image, ImageDraw
    gdir = Path(gdir)
    sets = pv.find_tilesets(gdir)
    pcs_path = gdir / "res" / "view.pcs"
    pcs = parse(pcs_path, sets[_tileset_of(pcs_path)].labels)
    ts = sets[pcs.tileset]
    images = {pcs.base + i: im for i, im in enumerate(ts.images)}
    out = Path(out or gdir / "build" / "preview")
    out.mkdir(parents=True, exist_ok=True)
    written, cells = [], []
    for name, rows in SCENES.items():
        dmap, px, py, pf = _scene(rows)
        img = render(compose(pcs, dmap, px, py, pf), images, 2)
        p = out / f"view_{name}.png"
        img.save(p)
        written.append(p)
        cells.append((name, img))
    cw, ch = cells[0][1].size
    sheet = Image.new("RGB", (4 * (cw + 8) + 8, ((len(cells) + 3) // 4) * (ch + 20) + 8), (230, 230, 240))
    d = ImageDraw.Draw(sheet)
    for k, (name, img) in enumerate(cells):
        x, y = 8 + (k % 4) * (cw + 8), 8 + (k // 4) * (ch + 20)
        sheet.paste(img, (x, y + 12))
        d.text((x, y), name, fill=(0, 0, 0))
    p = out / "view_sheet.png"
    sheet.save(p)
    written.append(p)
    missing = [n for n in NAMES if n not in pcs.pieces]
    if missing:
        print("pieces not drawn yet:", ", ".join(missing))
    return written


def _tileset_of(pcs_path):
    for line in Path(pcs_path).read_text(encoding="utf-8").splitlines():
        p = line.split(";", 1)[0].split()
        if p[:2] == ["@", "tileset"]:
            return p[2]
    raise ValueError(f"{pcs_path}: missing '@ tileset <name>'")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    g = ROOT / "games" / sys.argv[1]
    if len(sys.argv) == 2:
        for p in preview(g):
            print(p)
    else:
        print("view from a level position: needs the grid level format (games/dungeon E10)")
