"""Tests of harness/gbrun.py (Mesen 2 accuracy runner).

    python -I -m pytest harness/tests -q

Parsing tests always run; the Mesen runs skip when Mesen.exe is missing or games/hello is not built.
"""
import json, subprocess, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))
import gbrun  # noqa: E402

HELLO = ROOT / "games" / "hello" / "build" / "hello.gb"


def mesen_ok():
    return HELLO.exists() and any(p.exists() for p in gbrun.MESEN_CANDIDATES)


def run(tmp_path, *args):
    p = subprocess.run([sys.executable, "-I", str(ROOT / "harness" / "gbrun.py"), str(HELLO),
                        "--out", str(tmp_path), *args], capture_output=True, text=True, timeout=120)
    res = tmp_path / "result.json"
    return p.returncode, (json.loads(res.read_text()) if res.exists() else None), p.stdout + p.stderr


# ---------------------------------------------------------------- parsing (no emulator)
def test_parse_input():
    assert gbrun.parse_input("30-40:start;60:right+a", 100) == [(30, 40, ["start"]), (60, 60, ["right", "a"])]
    for bad in ("0:a", "5:x", "50-40:a", "90-200:a", "a"):
        with pytest.raises(gbrun.BadArgs):
            gbrun.parse_input(bad, 100)


def test_parse_check_symbols_and_memories():
    gbrun.SYMS.update({"_player_x": 0xC0B1, "player_x": 0xC0B1})
    assert gbrun.parse_check("player_x==96")[:4] == ("bus", 0xC0B1, 1, 96)
    assert gbrun.parse_check("player_x+1.w>=0x10")[:4] == ("bus", 0xC0B2, 2, 16)
    assert gbrun.parse_check("hram:0x0!=3")[-1] == "~="
    assert gbrun.parse_check("bus:0xFF40==0x91")[:4] == ("bus", 0xFF40, 1, 0x91)
    with pytest.raises(gbrun.BadArgs):
        gbrun.parse_check("no_such_symbol==1")
    with pytest.raises(gbrun.BadArgs):
        gbrun.parse_check("player_x = 3")


# ---------------------------------------------------------------- Mesen runs
@pytest.mark.skipif(not mesen_ok(), reason="Mesen.exe or games/hello/build/hello.gb missing")
def test_hello_input_checks_and_dumps(tmp_path):
    code, res, out = run(tmp_path, "--frames", "60", "--input", "10-29:right", "--shot", "5,60",
                         "--check", "player_x==96,player_y==68", "--check-at", "9:player_x==76",
                         "--expect", "player_y==68@1-60", "--watch", "player_x", "--every", "10",
                         "--dump", "oam:0:4", "--nonblank")
    assert code == 0, out
    assert res["ok"] and res["console"] == "Gameboy" and res["frames"] == 60
    assert res["boot_frames"] > 0                      # frame 1 = after the boot ROM, like PyBoy
    assert (tmp_path / "shot_0060.png").exists() and (tmp_path / "oam.bin").stat().st_size == 4
    rows = (tmp_path / "watch.csv").read_text().split()
    assert rows[0] == "frame,player_x" and rows[-1] == "60,96"
    from PIL import Image
    assert Image.open(tmp_path / "shot_0060.png").size == (160, 144)


@pytest.mark.skipif(not mesen_ok(), reason="Mesen.exe or games/hello/build/hello.gb missing")
def test_failing_check_sets_exit_code(tmp_path):
    code, res, out = run(tmp_path, "--frames", "20", "--check", "player_x==1")
    assert code == 1 and res["ok"] is False and "FAIL: check player_x==1" in out


@pytest.mark.skipif(not mesen_ok(), reason="Mesen.exe or games/hello/build/hello.gb missing")
def test_bad_arguments_exit_3_before_mesen(tmp_path):
    code, res, out = run(tmp_path, "--frames", "20", "--shot", "50")
    assert code == 3 and res is None


@pytest.mark.skipif(not mesen_ok(), reason="Mesen.exe or games/hello/build/hello.gb missing")
def test_golden_roundtrip(tmp_path):
    gold = tmp_path / "gold"
    code, _, out = run(tmp_path / "a", "--frames", "30", "--golden", str(gold), "--update-golden")
    assert code == 0 and (gold / "shot_0030.png").exists(), out
    code, res, out = run(tmp_path / "b", "--frames", "30", "--golden", str(gold))
    assert code == 0 and res["golden"][0]["diff_pixels"] == 0, out
    code, res, out = run(tmp_path / "c", "--frames", "30", "--input", "1-10:left", "--golden", str(gold))
    assert code == 1 and res["golden"][0]["diff_pixels"] > 0


@pytest.mark.skipif(not mesen_ok(), reason="Mesen.exe or games/hello/build/hello.gb missing")
def test_same_result_as_pyboy(tmp_path):
    """The two runners agree on frame numbering for plain logic: 20 frames of RIGHT move 20 px in both."""
    from gbtest import GB
    g = GB(HELLO)
    g.frames(9)
    g.hold("right", 20)
    pyboy_x = g.u8("player_x")
    g.close()
    code, res, out = run(tmp_path, "--frames", "40", "--input", "10-29:right", "--check", f"player_x=={pyboy_x}")
    assert code == 0, out
