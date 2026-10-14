"""Template tests: one per mechanic, plus the frame budget and VRAM guard every game needs."""


def test_player_starts_centered(gb):
    assert gb.u8("player_x") == (160 - 16) // 2
    assert gb.u8("player_y") == (144 - 16) // 2
    gb.screenshot("start")


def test_player_moves_and_stays_on_screen(gb):
    x = gb.u8("player_x")
    gb.hold("right", 10)
    assert gb.u8("player_x") > x
    gb.hold("left", 300)
    gb.hold("up", 300)
    assert (gb.u8("player_x"), gb.u8("player_y")) == (0, 0)
    gb.hold("right", 300)
    gb.hold("down", 300)
    assert (gb.u8("player_x"), gb.u8("player_y")) == (160 - 16, 144 - 16)


def test_frame_budget_and_vram_guard(gb):
    """A bot that must make progress (a stuck bot measures nothing), then the budget checks."""
    gb.write_u8("max_frame_lines", 0)
    seen = set()
    for i in range(600):
        gb.hold(["right", "down", "left", "up"][(i // 60) % 4], 1)
        seen.add((gb.u8("player_x") // 32, gb.u8("player_y") // 32))
    assert len(seen) >= 4, "the bot did not move around: fix the bot before trusting the budget"
    assert gb.u8("vram_late") == 0, "VRAM written outside VBlank"
    assert gb.u8("max_frame_lines") < 120, "less than 20% headroom"
