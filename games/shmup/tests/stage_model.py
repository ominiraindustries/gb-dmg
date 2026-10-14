"""Python model of the stage map for ROM tests: what each BG tile row must contain.

Built from the same sources as the ROM: res/stage1.lvl + game.json (cells) and res/metatiles.mt.
"""
import json
import sys
from pathlib import Path

GAME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GAME.parents[1] / "harness"))
import levels  # noqa: E402
import metatiles  # noqa: E402

CFG = json.loads((GAME / "game.json").read_text(encoding="utf-8"))["levels"]
MT = metatiles.parse(GAME / "res" / "metatiles.mt")
MT_ID = {"MT_" + n: i for n, i in MT.ids.items()}
MT_TILES = [MT.vram_tiles(i) for i in range(len(MT.names))]

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

# Cells the game changes at run time: a turret turns (L/D/R) and becomes a crater
TURRET_MTS = [MT_ID[n] for n in ("MT_TURRET_L", "MT_TURRET_D", "MT_TURRET_R", "MT_CRATER")]
VARIANTS = {(c, r): TURRET_MTS for r in range(HEIGHT) for c in range(WIDTH)
            if MAP[r][c] == MT_ID["MT_TURRET_D"]}


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
        got = rows[bg_row][:20]
        if got != tile_row(tr, overrides) and not _variant_ok(tr, got):
            bad.append((line, tr, bg_row))
    return bad


def _variant_ok(tr, got):
    """Every mismatching 16 px cell is a run-time variant of the map cell (turret / crater)."""
    r, top = tr >> 1, tr & 1
    for c in range(WIDTH):
        cell = got[2 * c:2 * c + 2]
        mt = MAP[r][c] if r < HEIGHT else 0
        options = [mt] + VARIANTS.get((c, r), [])
        if not any(cell == (MT_TILES[m][0:2] if top else MT_TILES[m][2:4]) for m in options):
            return False
    return True
