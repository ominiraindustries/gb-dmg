"""Python model of the stage map for ROM tests: what each BG tile row must contain.

Built from the same sources as the ROM: res/stage1.lvl + game.json (cells), src/metatiles.h
(MT ids) and src/metatiles.c (tiles of each metatile, + BG_BASE).
"""
import json
import re
import sys
from pathlib import Path

GAME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GAME.parents[1] / "harness"))
import levels  # noqa: E402

CFG = json.loads((GAME / "game.json").read_text(encoding="utf-8"))["levels"]
H_SRC = (GAME / "src" / "metatiles.h").read_text(encoding="utf-8")
C_SRC = (GAME / "src" / "metatiles.c").read_text(encoding="utf-8")

BG_BASE = int(re.search(r"#define BG_BASE (\d+)", H_SRC).group(1))
MT_ID = {m.group(1): int(m.group(2)) for m in re.finditer(r"(MT_\w+) = (\d+),", H_SRC)}
MT_TILES = [[BG_BASE + int(v) for v in m.groups()]
            for m in re.finditer(r"T\(\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)", C_SRC.split("mt_attr")[0])]

LVL = levels.parse(GAME / "res" / "stage1.lvl", layered=CFG["width"])
WIDTH, HEIGHT = LVL.width, LVL.height
STOP_ROW = int(LVL.meta["STOP_ROW"])
STOP_SCROLL = STOP_ROW * 16 - 112


def _cell_id(row, col):
    line = HEIGHT - 1 - row
    obj = LVL.layer[line][col]
    if obj in CFG.get("object_cells", {}):
        return MT_ID[CFG["object_cells"][obj]]
    return MT_ID[CFG["cells"][LVL.rows[line][col]]]


MAP = [[_cell_id(r, c) for c in range(WIDTH)] for r in range(HEIGHT)]   # MAP[row][col], row 0 bottom


def tile_row(tr, overrides=None):
    """The 20 tiles of world tile row tr (counted up from the bottom). overrides: {(col, row): mt}."""
    r, top = tr >> 1, tr & 1
    out = []
    for c in range(WIDTH):
        mt = MAP[r][c] if r < HEIGHT else 0
        if overrides and (c, r) in overrides:
            mt = overrides[(c, r)]
        t = MT_TILES[mt]
        out += t[0:2] if top else t[2:4]
    return out


def displayed_scroll(scy, scroll_y):
    """Full scroll value the screen shows: SCY = 112 - scroll (8 bits), a little behind scroll_y."""
    low = (112 - scy) & 255
    return scroll_y - ((scroll_y - low) & 255)


def check_screen(gb, first_line=8, last_line=143, overrides=None):
    """Compare the BG rows the screen shows (lines first..last) with the map. Returns mismatches."""
    scroll = displayed_scroll(gb.io(0xFF42), gb.u16("scroll_y"))
    bad = []
    rows = gb.bg_map()
    scy = gb.io(0xFF42)
    seen = set()
    for line in range(first_line, last_line + 1):
        bg_row = ((scy + line) & 255) >> 3
        if bg_row in seen:
            continue
        seen.add(bg_row)
        tr = (scroll + 143 - line) >> 3
        want = tile_row(tr, overrides)
        if rows[bg_row][:20] != want:
            bad.append((line, tr, bg_row))
    return bad
