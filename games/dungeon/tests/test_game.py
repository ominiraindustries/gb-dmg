"""TORRE HUNDIDA M1a: engine on the dungeon - view composition, double buffer, banks (GDD 11)."""
import random

from view_model import expected, shown


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
    """200 random actions (walk, back, turn, side step, about-face): after each map flip the
    screen == fpview.compose of the ROM's position; no tearing (the hidden map is written)."""
    rnd = random.Random(7)
    actions = [("up",), ("down",), ("left",), ("right",), ("b", "left"), ("b", "right"), ("b", "down")]
    worst = 0
    for i in range(200):
        act = rnd.choice(actions)
        flips = gb.u8("view_flips")
        for b in act:
            gb.pyboy.button_press(b)
        gb.frames(2)
        for b in act:
            gb.pyboy.button_release(b)
        assert wait_flip(gb, flips), (i, act)
        dmap, px, py, pf = state(gb)
        assert shown(gb) == expected(dmap, px, py, pf), (i, act, px, py, pf)
        worst = max(worst, gb.u8("max_frame_lines"))
        gb.frames(12)
    assert gb.u8("vram_late") == 0
    print("worst frame lines", worst)


def test_costs(gb):
    """M1a measures (GDD 9.3/9.4): view_compose, the VBlank copy, the whole step frame."""
    p = gb.profile(["view_compose", "view_blit", "bgbuf_draw_vram", "view_cell", "view_copy240", "update"])
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


T_A = 24 + 10                                              # VRAM_FONT + LETTER_A


def win_text(gb, row):
    """Window row as text (letters, digits, space) from VRAM."""
    out = ""
    for t in gb.bg_map(window=True)[row][:20]:
        if T_A <= t < T_A + 26:
            out += chr(65 + t - T_A)
        elif 24 <= t < 34:
            out += chr(48 + t - 24)
        else:
            out += " "
    return out.rstrip()


def test_log_types_messages(gb):
    gb.frames(30)
    assert win_text(gb, 5) == "PISO 1"
    gb.write_u8("pf", 0)                                    # face north: (5,1) is the sealed UP
    gb.tap("up")
    gb.frames(30)
    assert win_text(gb, 5) == "PARED" and win_text(gb, 4) == "PISO 1"
    assert gb.u8("vq_lost") == 0


def test_rng_is_predictable(gb):
    s = gb.u16("rng_state")
    gb.tap("right")
    gb.frames(20)
    s2, b = gb.rng_next(s)
    assert gb.u16("rng_state") == s2 and gb.u8("last_roll") == b


def test_save_continue_after_power_off(gb):
    from pathlib import Path
    from gbtest import GB
    for b in ("left", "up", "up"):                         # move somewhere
        gb.tap(b)
        gb.frames(20)
    pos = (gb.u8("px"), gb.u8("py"), gb.u8("pf"))
    gb.tap("start")
    gb.frames(30)
    assert win_text(gb, 5) == "PARTIDA GUARDADA"
    ram = gb.power_off()
    g2 = GB(Path(__file__).resolve().parents[1] / "build" / "dungeon.gb", ram=ram)
    try:
        assert (g2.u8("px"), g2.u8("py"), g2.u8("pf")) != pos
        g2.tap("select")
        g2.frames(30)
        assert (g2.u8("px"), g2.u8("py"), g2.u8("pf")) == pos
        assert win_text(g2, 5) == "PARTIDA CARGADA"
        from view_model import expected, shown
        assert shown(g2) == expected(g2.bytes("dmap", 256), *pos)
    finally:
        g2.close()
