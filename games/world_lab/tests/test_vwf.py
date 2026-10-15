"""gbe_vwf (proportional text) == harness/vwf.py byte for byte, and the decoder reads it back."""
import pytest

import vwf



TEXTS = ["Hola, Tilo. ¿Vienes?", "La campana del alba", "MADRIGUERA 2026!", "illi mmm - a/b: ¡ya!", "x"]


@pytest.mark.parametrize("x", [0, 3, 13])
def test_rom_draws_what_the_reference_draws(gb, x):
    for text in TEXTS:
        raw = text.encode("latin-1") + b"\0"
        gb.write_bytes("vwf_str", list(raw))
        gb.write_u8("vwf_x", x)
        gb.write_u8("vwf_req", 1)
        gb.frames(8)                                # ~2k T per glyph: a long line takes > 1 frame
        got = gb.bytes("vwf_buf", 20 * 16)
        want = sum(vwf.render(gb.game_dir, text, 20, x=x), [])
        assert got == want, text
        assert gb.u8("vwf_end") == x + vwf.width(gb.game_dir, text)
        tiles = [got[k * 16:(k + 1) * 16] for k in range(20)]
        assert vwf.decode(gb.game_dir, tiles) == text
