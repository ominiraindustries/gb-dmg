"""harness/physics.py must match the ROM: designers and the level lint trust its numbers."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(Path(__file__).parent))
import physics  # noqa: E402
from helpers import start_play  # noqa: E402

P = physics.GAMES["platformer"]


def rom_jump_height(gb, hold, run=False, walk=False):
    start_play(gb)
    gb.write_u8("cheat_flags", 3)
    gb.frames(5)
    if run or walk:
        gb.pyboy.button_press("right")
        if run:
            gb.pyboy.button_press("b")
        gb.frames(30)                                # reach full speed
    y0 = gb.u8("player_y")
    gb.pyboy.button_press("a")
    top = y0
    for f in range(120):
        gb.frames(1)
        if f == hold - 1:
            gb.pyboy.button_release("a")
        top = min(top, gb.u8("player_y"))
        if f > 5 and gb.u8("player_on_ground"):
            break
    for b in ("a", "b", "right"):
        gb.pyboy.button_release(b)
    return y0 - top


def sim(jump_v, vx, hold):
    return physics.simulate_jump(jump_v, P["grav_hold"], P["grav"], P["fall_max"], vx, hold)["height"]


def test_running_jump_matches_model(gb):
    assert rom_jump_height(gb, 200, run=True) == sim(P["jump_v_run"], P["run"], 10**6)


def test_walking_jump_matches_model(gb):
    assert rom_jump_height(gb, 200, walk=True) == sim(P["jump_v"], P["walk"], 10**6)


def test_tap_jump_matches_model(gb):
    h = rom_jump_height(gb, 1)
    assert abs(h - sim(P["jump_v"], 0, 1)) <= 1, h      # A release lands on a frame boundary
