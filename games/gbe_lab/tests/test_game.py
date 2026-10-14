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


def _req(g, r):
    g.write_u8("save_req", r)
    g.frames(3)


def test_save_survives_power_off_and_detects_corruption(gb):
    """gbe_save.c: a stored block reads back after a power cycle (SRAM kept by the battery);
    a corrupted byte or a different version reads as no save; a blank cart has no save."""
    from pathlib import Path
    from gbtest import GB
    _req(gb, 2)
    assert gb.u8("save_ok") == 0                        # blank SRAM: no save
    data = list(range(100, 116))
    gb.write_bytes("save_buf", data)
    _req(gb, 1)
    ram = gb.power_off()
    rom = Path(__file__).resolve().parents[1] / "build" / "gbe_lab.gb"
    g2 = GB(rom, ram=ram)
    try:
        _req(g2, 2)
        assert g2.u8("save_ok") == 1 and g2.bytes("load_buf", 16) == data
        bad = bytearray(g2.power_off())
    finally:
        pass
    bad[6 + 7] ^= 0x10                                   # flip one data bit (6-byte header)
    g3 = GB(rom, ram=bytes(bad))
    _req(g3, 2)
    assert g3.u8("save_ok") == 0
    g3.close()


def test_save_two_slots_torn_write_keeps_previous(gb):
    """gbe_save.c alternates slots: store A, store B (other slot, seq + 1), then B is torn (as if
    the power went off mid-store): the load returns A."""
    from pathlib import Path
    from gbtest import GB
    a, b = list(range(1, 17)), list(range(50, 66))
    gb.write_bytes("save_buf", a)
    _req(gb, 1)
    gb.write_bytes("save_buf", b)
    _req(gb, 1)
    _req(gb, 2)
    assert gb.bytes("load_buf", 16) == b                 # newest wins
    ram = bytearray(gb.power_off())
    assert ram[0x0000:0x0002] == b"GB" and ram[0x1000:0x1002] == b"GB"   # both slots used
    ram[0x1000 + 6 + 3] ^= 0xFF                          # B's data corrupted
    rom = Path(__file__).resolve().parents[1] / "build" / "gbe_lab.gb"
    g2 = GB(rom, ram=bytes(ram))
    _req(g2, 2)
    assert g2.u8("save_ok") == 1 and g2.bytes("load_buf", 16) == a
    g2.close()
