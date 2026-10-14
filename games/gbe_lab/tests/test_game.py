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


def test_banked_assets_load_from_their_banks(gb):
    """game.json banked_res puts generated assets in switchable banks; gbe_bank.c loads them
    from bank 0 code. VRAM must hold the exact bytes of each tileset (not another bank's)."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "harness"))
    import asciitiles
    ids = gb.bytes("bank_ids", 3)
    assert all(b >= 1 for b in ids), ids
    res = Path(__file__).resolve().parents[1] / "res"
    for k, first in enumerate((128, 160, 192)):
        tiles, _ = asciitiles.parse(res / f"bank{k}.tiles")
        want = [b for t in tiles[:32] for b in asciitiles.encode(t)]
        addr = 0x8800 + (first - 128) * 16                 # BG 128+ = 0x8800 in either LCDC mode
        got = [gb.pyboy.memory[addr + i] for i in range(32 * 16)]
        assert got == want, f"bank{k} (ROM bank {ids[k]}) not loaded correctly"
