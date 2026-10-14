"""Equivalence of every asm routine with its C reference: the gbe engine ones (mt_at/solid_at
exhaustive over the level, act_move, column fill) plus the game's walk_on_map on the real level."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from helpers import start_play


def test_asm_routines_equal_c_references(gb):
    start_play(gb)                                # a map must be loaded
    mismatches, cases = gb.selftest()
    assert cases != 0
    assert mismatches == 0
