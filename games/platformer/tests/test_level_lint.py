"""Level lint (pure Python, no emulator): design rules from GDD §6/§7.3/§11 for every res/*.lvl."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "harness"))
import levels  # noqa: E402

GAME = Path(__file__).resolve().parents[1]
LEVELS = sorted((GAME / "res").glob("*.lvl"))
SOLID = set("#BH?PU[]{}")           # solid map cells (U only from below, but blocks paths too)
ENEMIES = set("wsph")
MAX_PIT = 3                         # metatiles, walking jump (GDD §2.2); running allows 5
MAX_STEP_UP = 4                     # metatiles, running jump height
ENEMY_WINDOW = 11                   # 176 px / 16


@pytest.fixture(params=LEVELS, ids=[p.name for p in LEVELS])
def lvl(request):
    return levels.parse(request.param, height=8)


def test_size_and_markers(lvl):
    assert 20 <= lvl.width <= 255
    text = "".join(lvl.rows)
    assert text.count("x") == 1, "exactly one player start"
    assert "|" in text and "^" in text, "goal pole missing"


def test_pits_are_jumpable(lvl):
    run = 0
    for c in range(lvl.width):
        if lvl.cell(c, 7) in SOLID:
            run = 0
        else:
            run += 1
            assert run <= MAX_PIT, f"pit wider than {MAX_PIT} ending at column {c}"


def surface(lvl, c):
    """Height in metatiles of the solid stack standing on the ground at column c."""
    h = 0
    for r in range(6, -1, -1):
        if lvl.cell(c, r) in SOLID:
            h += 1
        else:
            break
    return h


def test_steps_are_climbable(lvl):
    for c in range(1, lvl.width):
        rise = surface(lvl, c) - surface(lvl, c - 1)
        assert rise <= MAX_STEP_UP, f"step of {rise} metatiles at column {c}"


def test_turrets_are_closed(lvl):
    for r in range(8):
        row = lvl.rows[r]
        for c, ch in enumerate(row):
            if ch in "[{":
                assert c + 1 < lvl.width and row[c + 1] == {"[": "]", "{": "}"}[ch], (r, c)
            if ch in "[{" and r < 7:
                below = lvl.cell(c, r + 1)
                assert below in "{#H", f"turret not grounded at column {c}, row {r}"


def test_max_three_enemies_per_band(lvl):
    """10 sprites per scanline: player 2 + 3 enemies x 2 + 2 shots (GDD §7.3)."""
    for r in range(8):
        cols = [c for c in range(lvl.width) if lvl.cell(c, r) in ENEMIES]
        for c in cols:
            near = [k for k in cols if c <= k < c + ENEMY_WINDOW]
            assert len(near) <= 3, f"{len(near)} enemies in row {r} from column {c}"
