"""TORRE HUNDIDA: engine on the dungeon - view composition, double buffer, costs (GDD 11)."""
import random

from view_model import expected, shown

CHEAT_INVINCIBLE, CHEAT_FROZEN, CHEAT_ONE_HIT, CHEAT_SEEN_ALL = 1, 2, 4, 8


def state(gb):
    return gb.bytes("dmap", 256), gb.u8("px"), gb.u8("py"), gb.u8("pf")


def test_engine_selftest(gb):
    mismatch, count = gb.selftest()
    assert count > 0 and mismatch == 0, (mismatch, count)


def test_start_view_matches_model(gb):
    dmap, px, py, pf = state(gb)
    assert (px, py, pf) == (5, 2, 2)                       # floor1.lvl '@', facing S
    assert shown(gb) == expected(dmap, px, py, pf)
    gb.screenshot("start")


def wait_flip(gb, flips0, frames=30):
    for _ in range(frames):
        gb.frames(1)
        if gb.u8("view_flips") != flips0 and not gb.u8("bgbuf_rows_left"):
            gb.frames(1)
            return True
    return False


def test_walk_and_turn_view_matches_model_every_step(gb):
    """200 random actions (walk, back, turn, side step, about-face, A) with frozen monsters: after
    each action the screen == fpview.compose of the ROM's position (opened doors included)."""
    gb.write_u8("cheat_flags", CHEAT_INVINCIBLE | CHEAT_FROZEN)
    rnd = random.Random(7)
    actions = [("up",), ("down",), ("left",), ("right",), ("b", "left"), ("b", "right"), ("b", "down"), ("a",)]
    worst = 0
    for i in range(200):
        act = rnd.choice(actions)
        flips = gb.u8("view_flips")
        for b in act:
            gb.pyboy.button_press(b)
        gb.frames(2)
        for b in act:
            gb.pyboy.button_release(b)
        wait_flip(gb, flips)                               # bumps and attacks do not flip
        gb.frames(14)
        dmap, px, py, pf = state(gb)
        assert shown(gb) == expected(dmap, px, py, pf), (i, act, px, py, pf)
        worst = max(worst, gb.u8("max_frame_lines"))
    assert gb.u8("vram_late") == 0
    assert gb.u8("vq_lost") == 0
    print("worst frame lines", worst)


def test_costs(gb):
    """GDD 9.3/9.4 measures: view_compose, the VBlank copy, the whole step frame."""
    gb.write_u8("cheat_flags", CHEAT_INVINCIBLE)
    p = gb.profile(["view_compose", "view_blit", "bgbuf_draw_vram", "view_copy240", "play_update",
                    "monsters_update", "play_sprites", "log_update", "vq_draw_vram"])
    for k in range(40):
        gb.pyboy.button_press("right" if k % 3 else "up")
        gb.frames(2)
        gb.pyboy.button_release("right")
        gb.pyboy.button_release("up")
        gb.frames(14)
    p.stop()
    print(p.report())
    print("max_frame_lines", gb.u8("max_frame_lines"), "vram_late", gb.u8("vram_late"))
    assert gb.u8("vram_late") == 0
    assert gb.u8("max_frame_lines") < 120
