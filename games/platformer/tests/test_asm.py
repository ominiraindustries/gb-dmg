"""Equivalence of the asm routines in vram.s with their C references: mt_at / solid_at (exhaustive
over the level) and act_move (signed velocities, carries, 16-bit wrap)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from helpers import start_play


def test_asm_routines_equal_c_references(gb):
    start_play(gb)
    gb.write_u8("eq_request", 1)
    for _ in range(300):                      # ~840k comparisons = ~12000 frames
        gb.frames(100)
        if gb.u8("eq_done"):
            break
    assert gb.u8("eq_done") == 1, "equivalence run did not finish"
    assert gb.u16("eq_count") != 0
    assert gb.u16("eq_mismatch") == 0
