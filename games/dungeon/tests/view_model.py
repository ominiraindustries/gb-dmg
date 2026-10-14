"""Python model of the dungeon view for ROM tests: harness/fpview.py with this game's pieces."""
import json
import sys
from pathlib import Path

GAME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GAME.parents[1] / "harness"))
import asciitiles  # noqa: E402
import fpview  # noqa: E402
import preview  # noqa: E402
import screens  # noqa: E402

CFG = json.loads((GAME / "game.json").read_text(encoding="utf-8"))
SETS = preview.find_tilesets(GAME)
BASES = screens.vram_bases(CFG["vram_order"], SETS)
PCS = fpview.parse(GAME / "res" / "view.pcs", SETS["walls"].labels, BASES)
VIEW_ROW = 8


def expected(dmap, px, py, pf):
    return fpview.compose(PCS, dmap, px, py, pf)


def shown(gb):
    """The 12x20 view on screen: rows 8-19, columns 0-19 of the visible BG map."""
    m = gb.bg_map(map=gb.active_bg())
    return [row[:20] for row in m[VIEW_ROW:VIEW_ROW + 12]]
