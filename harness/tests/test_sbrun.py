"""Tests of harness/sbrun.py (SameBoy accuracy sign-off runner).

    python -I -m pytest harness/tests/test_sbrun.py -q

Parsing tests always run; the SameBoy runs skip when tools/sameboy (source + release) or games/hello is missing.
"""
import argparse, json, subprocess, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))
import gbrun  # noqa: E402
import sbrun  # noqa: E402

HELLO = ROOT / "games" / "hello" / "build" / "hello.gb"


def sameboy_ok():
    return HELLO.exists() and sbrun.core_dir() is not None and (sbrun.SB / "bin" / "dmg_boot.bin").exists()


needs_sameboy = pytest.mark.skipif(not sameboy_ok(), reason="tools/sameboy or games/hello build missing")


def run(tmp_path, *args):
    p = subprocess.run([sys.executable, "-I", str(ROOT / "harness" / "sbrun.py"), str(HELLO),
                        "--out", str(tmp_path), *args], capture_output=True, text=True, timeout=300)
    res = tmp_path / "result.json"
    return p.returncode, (json.loads(res.read_text()) if res.exists() else None), p.stdout + p.stderr


def ns(**kw):
    base = dict(frames=100, shot=None, input=None, check=None, check_at=None, expect=None, watch=None, every=60,
                regs=None, dump=None, sram_in=None, sram_out=None)
    base.update(kw)
    return argparse.Namespace(**base)


# ---------------------------------------------------------------- parsing (no emulator)
def test_plan_input_masks_change_only():
    plan, _ = sbrun.build_plan(ns(input="10-12:right;12-13:a+start"), Path("."))
    keys = [l for l in plan if l.startswith("K ")]
    right, a, start = 1 << 0, 1 << 4, 1 << 7
    assert keys == [f"K 10 {right}", f"K 12 {right | a | start}", f"K 13 {a | start}", "K 14 0"]


def test_plan_reads_for_checks_expect_and_watch():
    gbrun.SYMS.clear()
    gbrun.SYMS.update({"player_x": 0xC0B1})
    plan, spec = sbrun.build_plan(ns(check="player_x==96", check_at="9:player_x==76", expect="player_x>=76@20-22",
                                     watch="player_x", every=50), Path("."))
    reads = {l for l in plan if l.startswith("R ")}
    assert {f"R {f} bus {0xC0B1} 1" for f in (9, 20, 21, 22, 50, 100)} <= reads
    assert "S 100" in plan and spec["wframes"] == [50, 100]


def test_plan_bad_arguments():
    for kw in ({"shot": "0"}, {"shot": "101"}, {"input": "5:x"}, {"check_at": "200:a==1"}, {"expect": "a==1"},
               {"dump": "nope"}, {"regs": "q==1"}, {"regs": "b=3"}, {"every": 0}, {"check": "no_such_symbol==1"}):
        with pytest.raises(gbrun.BadArgs):
            sbrun.build_plan(ns(**kw), Path("."))


def test_evaluate_checks_expects_regs():
    gbrun.SYMS.clear()
    gbrun.SYMS.update({"x": 0xC000})
    _, spec = sbrun.build_plan(ns(frames=3, check="x==5", expect="x>=4@2-3", regs="b==3,c==5,pc==0x150"), Path("."))
    out = "R 2 bus 49152 04\nR 3 bus 49152 05\nEND 3 85 0 0080 0305 0000 0000 dffe 0150\n"
    d = sbrun.evaluate(spec, out, 3)
    assert d["ok"] and d["boot_frames"] == 85 and d["expects"][0]["min"] == 4
    d = sbrun.evaluate(spec, out.replace("R 3 bus 49152 05", "R 3 bus 49152 03"), 3)
    assert not d["ok"] and d["expects"][0]["first_fail_frame"] == 3
    assert sbrun.evaluate(spec, "garbage", 3) is None      # no END line -> exit 2 in main


def test_shade_remap_matches_mesen_palette():
    assert bytes([0x00, 0x55, 0xAA, 0xFF]).translate(sbrun.SHADES) == bytes([0x00, 0x6B, 0xB5, 0xFF])


# ---------------------------------------------------------------- SameBoy runs
@needs_sameboy
def test_hello_input_and_checks(tmp_path):
    code, res, log = run(tmp_path, "--frames", "60", "--input", "10-29:right", "--check", "player_x==96",
                         "--check-at", "9:player_x==76", "--watch", "player_x", "--every", "10", "--nonblank")
    assert code == 0, log
    assert res["frames"] == 60 and res["ok"]
    assert (tmp_path / "shot_0060.png").exists() and (tmp_path / "watch.csv").exists()


@needs_sameboy
def test_failing_check_exit_1(tmp_path):
    code, res, _ = run(tmp_path, "--frames", "20", "--check", "player_x==1")
    assert code == 1 and not res["ok"]


@needs_sameboy
def test_bad_arguments_exit_3(tmp_path):
    code, res, log = run(tmp_path, "--frames", "20", "--check", "player_x=1")
    assert code == 3 and res is None and "bad check" in log


@needs_sameboy
def test_golden_roundtrip(tmp_path):
    g = tmp_path / "golden"
    assert run(tmp_path / "a", "--frames", "30", "--golden", str(g), "--update-golden")[0] == 0
    assert run(tmp_path / "b", "--frames", "30", "--golden", str(g))[0] == 0
    code, _, log = run(tmp_path / "c", "--frames", "30", "--input", "1-30:right", "--golden", str(g))
    assert code == 1 and "pixels differ" in log
