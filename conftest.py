"""Pytest fixtures shared by every game: `gb` boots the ROM of the game being tested."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "harness"))
from gbtest import GB  # noqa: E402


@pytest.fixture
def gb(request):
    # games/<name>/tests/test_x.py -> games/<name>/build/<name>.gb
    gdir = Path(request.fspath).parent.parent
    rom = gdir / "build" / f"{gdir.name}.gb"
    if not rom.exists():
        pytest.fail(f"{rom} not built, run: python harness/gb.py build {gdir.name}")
    g = GB(rom)
    yield g
    g.close()
