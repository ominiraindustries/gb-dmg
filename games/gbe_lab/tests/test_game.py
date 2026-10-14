"""gbe_lab scenario 1: shmup peak load (26 objects + player) - cost per engine function."""


def test_shmup_peak_budget(gb):
    gb.frames(120)                                # pools fill up
    gb.write_u8("max_frame_lines", 0)
    p = gb.profile(["update", "draw_sprites", "spawn",
                    "collide", "pool_move", "hit_first", "spr_group"])
    gb.pyboy.button_press("left")
    gb.frames(300)
    gb.pyboy.button_release("left")
    p.stop()
    raw = gb.bytes("pool", 26 * 16)
    live = sum(1 for i in range(26) if raw[i * 16])
    print(p.report())
    print(f"live objects {live}, worst {gb.u8('max_frame_lines')} lines, max sprites/line {gb.max_line_sprites()}")
    gb.screenshot("peak")
    assert live >= 20
    assert gb.u8("vram_late") == 0


def test_engine_selftest(gb):
    mismatches, cases = gb.selftest()
    assert cases > 0 and mismatches == 0, (mismatches, cases)
