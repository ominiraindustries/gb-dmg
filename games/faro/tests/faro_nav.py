"""FARO test helpers: start a game, read the maps as Python models, walk Leo along BFS paths.
Shared by the tests and the playtester's bots (ROM addresses come from the .noi via gbtest)."""
import json
from collections import deque
from pathlib import Path

import metatiles  # noqa: F401  (world.load needs it importable)
import preview
import screens
import world
from gbtest import GB

GAME = Path(__file__).resolve().parents[1]
MAP_IDS = world.map_ids(GAME)                      # {"MAP_ISLA": n, ...}
MAP_NAMES = {v: k[4:] for k, v in MAP_IDS.items()}
_MAPS = {}
BASES = screens.vram_bases(json.loads((GAME / "game.json").read_text(encoding="utf-8"))["vram_order"],
                           preview.find_tilesets(GAME))
ST_TITLE, ST_FIELD = 0, 1
DIRS = {(0, 1): "down", (0, -1): "up", (-1, 0): "left", (1, 0): "right"}
DIR_IDS = {"down": 0, "up": 1, "left": 2, "right": 3}


def screen_text(gb):
    """The 18 text rows the player sees (BG + window as LCDC shows them; other tiles = spaces)."""
    return [GB.tile_text(r, BASES["font"], BASES["font_lower"], BASES["font_es"]) for r in gb.screen_tiles()]


def map_model(name):
    if name not in _MAPS:
        f = next(p for p in (GAME / "res" / "maps").glob("*.map") if world.load(GAME, p).name == name)
        _MAPS[name] = world.load(GAME, f)
    return _MAPS[name]


def current_map(gb):
    return map_model(MAP_NAMES[gb.u8("wmap_id")])


def settle(gb, n=200):
    """Wait until the field owns the frame (no transition)."""
    for _ in range(n):
        gb.frames(1)
        if gb.u8("state") == ST_FIELD and not gb.u8("trans_phase") and not gb.u8("warp_pending"):
            return True
    return False


def new_game(gb):
    gb.frames(10)
    gb.tap("start")
    gb.frames(10)
    gb.tap("a")                                     # "Nueva partida" (the cursor starts there without a save)
    assert settle(gb), "TITLE -> field did not happen"
    gb.frames(4)


def walkable(m, x, y):
    return x < m.width and y < m.height and "SOLID" not in m.mt_attrs[m.at(x, y)]


def path(m, start, goal, blocked=()):
    """BFS over walkable cells; returns the list of directions."""
    prev, q = {start: None}, deque([start])
    while q:
        c = q.popleft()
        if c == goal:
            break
        for d in DIRS:
            n = (c[0] + d[0], c[1] + d[1])
            if n not in prev and (n == goal or (walkable(m, *n) and n not in blocked)):
                prev[n] = (c, d)
                q.append(n)
    if goal not in prev:
        return None
    out, c = [], goal
    while prev[c]:
        c, d = prev[c]
        out.append(DIRS[d])
    return out[::-1]


def actors(gb):
    n = gb.u8("gact_count")
    raw = gb.bytes("gact", 24 * n)
    return {(raw[i * 24 + 1], raw[i * 24 + 2]) for i in range(n) if raw[i * 24]}


def step(gb, d):
    """One cell in direction d (turns first if needed). Returns True if Leo moved."""
    x, y = gb.u8("px"), gb.u8("py")
    if gb.u8("pdir") != DIR_IDS[d]:
        gb.tap(d)
        gb.frames(2)
    gb.pyboy.button_press(d)                        # held until the step starts, not longer: a
    for _ in range(12):                             # held button chains the next step
        gb.frames(1)
        if gb.u8("pmoving") or (gb.u8("px"), gb.u8("py")) != (x, y):
            break
    gb.pyboy.button_release(d)
    for _ in range(80):
        if not gb.u8("pmoving"):
            break
        gb.frames(1)
    return (gb.u8("px"), gb.u8("py")) != (x, y)


def walk_to(gb, goal, limit=200):
    """Walk to goal on the current map, re-planning around actors. Returns True when there."""
    for _ in range(limit):
        pos = (gb.u8("px"), gb.u8("py"))
        if pos == goal:
            return True
        p = path(current_map(gb), pos, goal, actors(gb) - {goal})
        if not p:
            p = path(current_map(gb), pos, goal)
            if not p:
                return False
        if not step(gb, p[0]):
            gb.frames(30)                           # an actor in the way: let it move
        if gb.u8("state") != ST_FIELD or gb.u8("tbox_visible"):
            return (gb.u8("px"), gb.u8("py")) == goal
    return False
