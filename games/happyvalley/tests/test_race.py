"""HAPPY VALLEY race model (GDD 2.4): the ROM's race == tests/hv_model.py, field and race from the same
seed, on every course: finishing order, finish tick and overshoot of every runner."""
import pytest

import hv_model as M

CASES = [("HV1200", 8), ("HV1650", 8), ("ST1200", 8), ("ST1600", 8), ("ST2400", 8), ("AW1200", 8)]


def rom_race(gb, seed, course, lo, hi, n):
    gb.write_u16("race_seed", seed)
    gb.write_u8("race_req_course", M.COURSE_IDS.index(course))
    gb.write_u8("race_lo", lo)
    gb.write_u8("race_hi", hi)
    gb.write_u8("race_req_n", n)
    gb.write_u8("race_req", 1)
    for _ in range(6000):                       # a whole race runs inside one game frame
        gb.frames(10)
        if not gb.u8("race_req"):
            break
    else:
        raise AssertionError("the ROM race did not finish")
    gb.frames(2)
    ids = gb.bytes("res_i", n)
    rt, ro = gb.bytes("res_t", 2 * n), gb.bytes("res_over", 2 * n)
    t = [rt[2 * k] | rt[2 * k + 1] << 8 for k in range(n)]
    o = [ro[2 * k] | ro[2 * k + 1] << 8 for k in range(n)]
    return [(ids[k], t[k], o[k]) for k in range(n) if ids[k] != 0xFF]


@pytest.mark.parametrize("use_c", [0, 1], ids=["asm", "c"])
@pytest.mark.parametrize("course,n", CASES)
def test_rom_race_equals_model(gb, course, n, use_c):
    gb.write_u8("race_use_c", use_c)            # race_move.s and its C reference, both == the model
    for seed in (0xBEEF, 0x1234, 0x0F0F):
        hs, w, want = M.race_from_seed(seed, course, 40, 60, n)
        got = rom_race(gb, seed, course, 40, 60, n)
        assert got == want, (course, hex(seed))
