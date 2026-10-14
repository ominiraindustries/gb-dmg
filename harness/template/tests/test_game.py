def test_player_starts_centered(gb):
    assert gb.u8("player_x") == 76
    assert gb.u8("player_y") == 68
    gb.screenshot("start")


def test_player_moves_right(gb):
    x = gb.u8("player_x")
    gb.hold("right", 10)
    assert gb.u8("player_x") > x


def test_player_stays_on_screen(gb):
    gb.hold("left", 200)
    gb.hold("up", 200)
    assert gb.u8("player_x") == 0
    assert gb.u8("player_y") == 0
    gb.hold("right", 300)
    gb.hold("down", 300)
    assert gb.u8("player_x") == 160 - 8
    assert gb.u8("player_y") == 144 - 8
    gb.screenshot("corner")
