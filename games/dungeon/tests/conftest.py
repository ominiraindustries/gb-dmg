"""TORRE HUNDIDA fixtures: `gb` starts a new game (TITLE -> NUEVA PARTIDA -> PLAY); `title` is
the ROM at boot; `boot(ram)` boots with a given SRAM (save/continue tests)."""
from pathlib import Path

import pytest
from gbtest import GB

ROM = Path(__file__).resolve().parents[1] / "build" / "dungeon.gb"
ST_TITLE, ST_PLAY = 0, 1


def wait_state(g, st, frames=200):
    for _ in range(frames):
        g.frames(1)
        if g.u8("state") == st and not g.u8("trans_phase"):
            return True
    return False


def start_play(g):
    g.tap("start")
    assert wait_state(g, ST_PLAY), "TITLE -> PLAY did not happen"
    g.frames(10)
    return g


@pytest.fixture
def gb(gb):
    return start_play(gb)


@pytest.fixture
def title():
    g = GB(ROM)
    yield g
    g.close()


def boot(ram=None):
    return GB(ROM, ram=ram)
