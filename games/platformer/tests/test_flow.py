"""M1 step 3b: title, intro, pause, goal sequence, clear and game over screens, record."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from helpers import CLEAR, GOAL, INTRO, PAUSE, PLAY, TITLE, Y_BIAS, start_play, teleport, wait_state

SMALL_ON_GROUND = Y_BIAS + 7 * 16 - 16


def score(gb):
    return int("".join(f"{b:02X}" for b in reversed(gb.bytes("score", 3))))


def bcd(gb, name):
    return int("".join(f"{b:02X}" for b in reversed(gb.bytes(name, 3))))


def test_boots_into_title(gb):
    assert wait_state(gb, TITLE)
    gb.frames(30)
    gb.screenshot("title")


def test_start_goes_through_intro_to_play(gb):
    wait_state(gb, TITLE)
    gb.frames(20)
    gb.tap("start")
    assert wait_state(gb, INTRO, 200)
    gb.frames(60)
    gb.screenshot("intro")
    assert wait_state(gb, PLAY, 300)
    assert gb.u8("lives") == 3


def test_pause_freezes_and_resumes(gb):
    start_play(gb)
    gb.write_u8("cheat_flags", 2)
    gb.frames(10)
    gb.tap("start")
    assert gb.u8("state") == PAUSE
    t = gb.u16("time_units")
    x = gb.u16("player_x")
    gb.hold("right", 60)
    assert gb.u16("player_x") == x
    gb.screenshot("pause")
    gb.tap("start")
    assert gb.u8("state") == PLAY


def test_goal_scores_by_height_and_counts_time(gb):
    start_play(gb)
    gb.write_u8("cheat_flags", 2)
    gb.write_u8("obj_next", 255)
    s0 = score(gb)
    time0 = gb.u16("time_units")
    # jump at the pole from high up (row 1): top score 5000
    teleport(gb, 189 * 16 - 8, Y_BIAS + 16)        # in the air, just left of the pole
    gb.write_u16("player_vx", 0x0140)
    gb.pyboy.button_press("right")
    assert wait_state(gb, GOAL, 120)
    gb.pyboy.button_release("right")
    assert score(gb) - s0 == 5000
    gb.frames(40)
    gb.screenshot("goal_slide")
    assert wait_state(gb, CLEAR, 900)
    gb.frames(20)
    # time bonus: 50 per remaining unit
    assert score(gb) - s0 == 5000 + 50 * time0
    assert bcd(gb, "record") == score(gb)       # record updated on CLEAR
    gb.screenshot("clear")


def test_clear_returns_to_title(gb):
    start_play(gb)
    gb.write_u8("obj_next", 255)
    gb.write_u16("time_units", 2)
    teleport(gb, 189 * 16 - 8, Y_BIAS + 5 * 16)
    gb.pyboy.button_press("right")
    assert wait_state(gb, GOAL, 120)
    gb.pyboy.button_release("right")
    assert wait_state(gb, CLEAR, 900)
    gb.frames(40)
    gb.tap("start")
    assert wait_state(gb, TITLE, 200)
