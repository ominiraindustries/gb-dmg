"""Lint of res/stage1.lvl (pure Python, no ROM): GDD 2.6, 2.8, 2.10, 6.1, 6.2 and 11.

If an enemy lifetime, route or formation changes in the engine, update the tables below and the
lint checks the wave script again.
"""
import json
import sys
from pathlib import Path

import pytest

GAME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GAME.parents[1] / "harness"))
import levels  # noqa: E402

LVL_PATH = GAME / "res" / "stage1.lvl"
CFG = json.loads((GAME / "game.json").read_text(encoding="utf-8"))["levels"]

WIDTH, HEIGHT = 10, 200
ROW_FRAMES = 32                      # 16 px per row at 0.5 px/f (GDD 2.9)
FOG = "`"
FOG_START = 176                      # rows 176-199: fog (GDD 6.1 / 2.10)
BOSS_ROWS = {191: "BCDE", 190: "HIJK", 189: "LNOP"}   # top -> bottom, columns 3-6
BOSS_COLS = range(3, 7)
STOP_ROW = 191
LATE_OBJECT_ROWS = {180, 184}        # DART columns in the fog (GDD 6.2)

# Chars whose metatile has ATTR_GROUND in src/metatiles.c (a turret may stand there).
# Not ground: fog ` ^, water ~, shores [ ] - _ 5 6 7 8, bridges { = }, wall face W, gate G,
# houses r R, keep q p d k, cone A, boss B..P.
GROUND = set(",.*b:TFnu()1234cM|%")

# Flyers per object letter: (count, spawn interval f, lifetime f, vy px/f) - GDD 2.6.
FLYERS = {
    "d": (3, 13, 117, 1.5),     # DART column of 3 (ROM route: 176 px / 1.5)
    "w": (4, 16, 235, 0.75),    # WAVE row of 4 (ROM: 176 / 0.75)
    "f": (4, 16, 235, 0.75),
    "s": (1, 0, 130, 1.5),      # SWOOP
    "g": (1, 0, 130, 1.5),
    "c": (1, 0, 235, 0.75),     # CARRIER
    "e": (1, 0, 235, 0.75),
}
TURRET_LIFE = int(9.5 * ROW_FRAMES)  # ~9.5 rows on screen (GDD 6.2)
MAX_FLYERS, MAX_TURRETS, MAX_IN_BAND, BAND_PX = 6, 4, 3, 16


@pytest.fixture(scope="module")
def lvl():
    return levels.parse(LVL_PATH, layered=WIDTH)


@pytest.fixture(scope="module")
def objs(lvl):
    return levels.objects_of(lvl, CFG["objects"])


def row(lvl, r):
    """Terrain line of map row r (row 0 = last text line)."""
    return lvl.rows[lvl.height - 1 - r]


def flyer_spawns(objs):
    """(spawn frame, lifetime, vy, (col, row, ch)) for every single flyer."""
    out = []
    for col, r, ch in objs:
        if ch in FLYERS:
            n, step, life, vy = FLYERS[ch]
            for k in range(n):
                out.append((r * ROW_FRAMES + k * step, life, vy, (col, r, ch)))
    return sorted(out)


def test_grid_size_and_cells(lvl):
    assert lvl.width == WIDTH and lvl.height == HEIGHT
    cells, objects = CFG["cells"], CFG["objects"]
    for i, line in enumerate(lvl.rows):
        bad = [c for c in line if c not in cells]
        assert not bad, f"row {HEIGHT - 1 - i}: chars {bad} not in game.json cells"
        assert " " not in line, f"row {HEIGHT - 1 - i}: space in terrain (fog is '`')"
    for i, line in enumerate(lvl.layer):
        bad = [c for c in line if c != "." and c not in objects]
        assert not bad, f"row {HEIGHT - 1 - i}: object chars {bad} not in game.json objects"


def test_turrets_on_ground(lvl, objs):
    turrets = [(c, r) for c, r, ch in objs if ch == "t"]
    assert turrets, "no turrets"
    for c, r in turrets:
        under = row(lvl, r)[c]
        assert under in GROUND, f"turret at col {c} row {r} stands on {under!r}"


def test_max_flyers_alive(objs):
    spawns = flyer_spawns(objs)
    for t, _, _, src in spawns:
        alive = [s for s in spawns if s[0] <= t < s[0] + s[1]]
        assert len(alive) <= MAX_FLYERS, \
            f"{len(alive)} flyers alive at frame {t} (spawn of {src}): {[a[3] for a in alive]}"


def test_max_turrets_alive(objs):
    starts = sorted(r * ROW_FRAMES for c, r, ch in objs if ch == "t")
    for t in starts:
        alive = sum(1 for s in starts if s <= t < s + TURRET_LIFE)
        assert alive <= MAX_TURRETS, f"{alive} turrets alive at row {t // ROW_FRAMES}"


def test_max_flyers_in_spawn_band(objs):
    """At each spawn, flyers still inside the top 16 px band (y = vy * age) <= 3."""
    spawns = flyer_spawns(objs)
    for t, _, _, src in spawns:
        band = [s for s in spawns if s[0] <= t and (t - s[0]) * s[2] < BAND_PX]
        assert len(band) <= MAX_IN_BAND, \
            f"{len(band)} flyers in the spawn band at frame {t}: {[b[3] for b in band]}"


def test_fog_before_boss(lvl):
    boss_bottom = min(BOSS_ROWS)
    n, r = 0, boss_bottom - 1
    while r >= 0 and row(lvl, r) == FOG * WIDTH:
        n, r = n + 1, r - 1
    assert n >= 9, f"only {n} rows of pure fog below the boss"
    for r in range(FOG_START, HEIGHT):
        if r not in BOSS_ROWS:
            assert row(lvl, r) == FOG * WIDTH, f"row {r} is not pure fog"


def test_boss_block(lvl):
    for r in range(188, HEIGHT):
        line = row(lvl, r)
        for c in range(WIDTH):
            if r in BOSS_ROWS and c in BOSS_COLS:
                assert line[c] == BOSS_ROWS[r][c - BOSS_COLS.start], f"boss cell col {c} row {r}"
            else:
                assert line[c] == FOG, f"col {c} row {r} must be fog, is {line[c]!r}"


def test_stop_row(lvl):
    assert int(lvl.meta["STOP_ROW"]) == STOP_ROW == max(BOSS_ROWS)


def test_objects_before_fog(objs):
    for c, r, ch in objs:
        if r >= FOG_START:
            assert r in LATE_OBJECT_ROWS and ch == "d", f"object {ch!r} at col {c} row {r} in the fog"
