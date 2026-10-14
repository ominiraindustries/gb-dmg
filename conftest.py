"""Pytest fixtures shared by every game: `gb` boots the ROM of the game being tested."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "harness"))
from gbtest import GB  # noqa: E402


@pytest.hookimpl(tryfirst=True)
def pytest_collect_file(file_path, parent):
    """--import-mode=importlib (pytest.ini: every game has a test_game.py) does not put the test
    folder on sys.path: add it so games/<g>/tests/<helper>.py can be imported. Helper module
    names must be unique across games (they share sys.modules in one run)."""
    d = str(file_path.parent)
    if file_path.name.startswith("test_") and d not in sys.path:
        sys.path.insert(0, d)


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
