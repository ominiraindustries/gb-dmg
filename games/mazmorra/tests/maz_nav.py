"""MADRIGUERA test helpers: start a game, read the rooms as Python models (map + metatiles), place
Tilo, list enemies, and the expected screen of a room. Shared by the tests and the playtester."""
import json
from pathlib import Path

import metatiles
import preview
import screens
import tables
import world

GAME = Path(__file__).resolve().parents[1]
SC_TITLE, SC_PLAY, SC_FIN = 0, 1, 2
DIRS = {"down": 0, "up": 1, "left": 2, "right": 3}
ROOM_W, ROOM_H = 10, 8
MAP = world.load(GAME, GAME / "res" / "maps" / "mazmorra.map")
_cfg = json.loads((GAME / "game.json").read_text(encoding="utf-8"))
_sets = preview.find_tilesets(GAME)
_bases = screens.vram_bases(_cfg["vram_order"], _sets)
MT = metatiles.parse(GAME / "res" / "metatiles.mt", _sets["dungeon"].labels, _bases)
RULES = {r["id"]: r["v"] for r in tables.load_all(GAME / "res" / "data")["rules"].rows}
SOLID = [("SOLID" in MAP.mt_attrs[i]) for i in range(len(MAP.mt_attrs))]


def settle(gb, scene=SC_PLAY, n=200):
    """Wait until `scene` owns the frame (no transition, no slide)."""
    for _ in range(n):
        gb.frames(1)
        if gb.u8("scene") == scene and not gb.u8("trans_phase") and not gb.u8("sliding"):
            return True
    return False


def new_game(gb):
    gb.frames(20)
    gb.tap("start")
    assert settle(gb), "TITLE -> play did not happen"
    gb.frames(2)


def place(gb, x, y, d="down"):
    """Put Tilo at world px (x, y) facing d (tests only: the next frame uses it)."""
    gb.write_u16("lx", x)
    gb.write_u16("ly", y)
    gb.write_u8("ldir", DIRS[d])
    gb.frames(2)


def enemies(gb):
    """[(slot, cell x, cell y)] of the live gact actors."""
    raw = gb.bytes("gact", 24 * 6)
    return [(i, raw[i * 24 + 1], raw[i * 24 + 2]) for i in range(6) if raw[i * 24]]


def room_expected(c, r):
    """16 x 20 BG tiles the room (c, r) shows under the HUD (screen rows 2-17)."""
    out = []
    for row in range(16):
        line = []
        for col in range(20):
            mt = MAP.at(c * ROOM_W + col // 2, r * ROOM_H + row // 2)
            line.append(MT.vram_tiles(mt)[(row % 2) * 2 + col % 2])
        out.append(line)
    return out


def room_errors(gb):
    """Cells of the screen under the HUD that differ from the current room's map."""
    c, r = gb.u8("room_c"), gb.u8("room_r")
    want = room_expected(c, r)
    got = gb.screen_tiles()[2:18]
    return [(row + 2, col) for row in range(16) for col in range(20) if want[row][col] != got[row][col]]
