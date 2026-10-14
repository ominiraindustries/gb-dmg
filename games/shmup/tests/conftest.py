"""GRIFO fixtures: `gb` starts a game (TITLE -> Start -> PLAY); `title` is the ROM at boot."""
from pathlib import Path

import pytest
from gbtest import GB

ST_TITLE, ST_PLAY = 0, 1


def start_play(g):
    g.tap("start")
    for _ in range(120):
        g.frames(1)
        if g.u8("state") == ST_PLAY and not g.u8("trans_phase"):
            break
    assert g.u8("state") == ST_PLAY, "TITLE -> PLAY did not happen"
    return g


@pytest.fixture
def gb(gb):                       # the root conftest boots the ROM; begin a game on top of it
    return start_play(gb)


@pytest.fixture
def title():
    rom = Path(__file__).resolve().parents[1] / "build" / "shmup.gb"
    g = GB(rom)
    yield g
    g.close()
