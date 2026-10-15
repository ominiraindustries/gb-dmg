"""Template tests: one per mechanic, plus the frame budget and VRAM guard every game needs."""


def test_player_starts_centered(gb):
    assert gb.u8("player_x") == (160 - 16) // 2
    assert gb.u8("player_y") == (144 - 16) // 2
    gb.screenshot("start")


def test_screen_shows_its_own_graphics(gb):
    """Every visible sprite and BG tile holds the bytes of its tileset (game.json vram_scenes):
    declare one scene per screen of the game and check each one after entering it."""
    gb.hold("right", 20)
    assert gb.vram_errors("game") == []


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
    dirs = ["right", "down", "left", "up"]
    moved = {"dist": 0, "last": None}

    def step(g, f):                       # walk a square, one side every 60 frames
        for d in dirs:
            g.pyboy.button_release(d)
        g.pyboy.button_press(dirs[(f // 60) % 4])

    def progress(g):                      # total distance walked (keeps growing while moving)
        pos = (g.u8("player_x"), g.u8("player_y"))
        if moved["last"] is not None:
            moved["dist"] += abs(pos[0] - moved["last"][0]) + abs(pos[1] - moved["last"][1])
        moved["last"] = pos
        return moved["dist"]

    r = gb.run_bot(step, progress, 600)
    assert r["progress"] >= 300 and not r["gave_up"], r
    assert r["vram_late"] == 0, "VRAM written outside VBlank"
    assert r["worst_lines"] < 120, "less than 20% headroom"
