"""gbe_script + gbe_tbox on world_lab: talk to the NPC, typewriter pages, yes/no, a 2x2 choice,
a game op that takes time, flags deciding the second conversation."""
import json
from pathlib import Path

import preview
import screens
from gbtest import GB

GAME = Path(__file__).resolve().parents[1]
BASES = screens.vram_bases(json.loads((GAME / "game.json").read_text(encoding="utf-8"))["vram_order"],
                           preview.find_tilesets(GAME))
F_LE_GUSTA, F_DADO = 0, 1


def win_line(gb, row):
    return GB.tile_text(gb.bg_map(window=True)[row][1:19], BASES["font"], BASES["font_lower"]).strip()


def start_talk(gb):
    gb.frames(2)
    npc = gb.u8("npc")
    raw = gb.bytes("gact", 24 * 13)
    for i in range(13):                                   # only the NPC stays
        if i != npc:
            gb.write_bytes("gact", [0], offset=i * 24)
    gb.hold("up", 40)                                     # (34,34) -> (34,33), then bump the NPC
    gb.frames(4)
    assert (gb.u8("px"), gb.u8("py"), gb.u8("pdir")) == (34, 33, 1)
    gb.tap("a")
    gb.frames(2)
    assert gb.u8("script_active") == 1


def wait_state(gb, st, n=200):
    for _ in range(n):
        gb.frames(1)
        if gb.u8("tbox_state") == st:
            return True
    return False


TB_OPEN, TB_PAGE, TB_END, TB_YESNO, TB_CHOOSE = 1, 4, 5, 6, 7


def test_conversation_no_branch_and_game_ops(gb):
    start_talk(gb)
    assert wait_state(gb, TB_PAGE)
    gb.screenshot("talk_page1")
    assert win_line(gb, 2).endswith("Hola Leo! Esta") and win_line(gb, 4) == "es una prueba"
    assert "Tomasa" in GB.tile_text(gb.bg_map(window=True)[0][:20], BASES["font"], BASES["font_lower"])
    gb.tap("a")
    assert wait_state(gb, TB_PAGE)
    assert win_line(gb, 2) == "larga del cuadro"
    gb.tap("a")
    assert wait_state(gb, TB_END)
    assert win_line(gb, 2) == "ocupa varias"
    gb.tap("a")
    assert wait_state(gb, TB_YESNO)
    gb.frames(4)
    assert win_line(gb, 2) == "Te gusta?" and win_line(gb, 4).split() == ["Si", "No"]
    gb.screenshot("talk_ask")
    gb.tap("right")
    gb.tap("a")                                           # No
    assert wait_state(gb, TB_END)
    assert win_line(gb, 2) == "Vaya."
    gb.tap("a")
    assert wait_state(gb, TB_CHOOSE)
    gb.frames(4)
    assert win_line(gb, 2).split() == ["Uno", "Dos"] and win_line(gb, 4).split() == ["Tres", "Cuatro"]
    gb.screenshot("talk_choice")
    gb.tap("right")
    gb.tap("down")
    gb.tap("a")                                           # Cuatro
    gb.frames(10)
    assert gb.u8("spin_left") > 0 and gb.u8("script_active")   # game op running: script waits
    gb.frames(40)
    assert gb.u8("script_active") == 0 and gb.u8("tbox_visible") == 0
    assert gb.bytes("vars", 1)[0] == 3
    assert gb.u8("given_item") == 7 and gb.u8("given_count") == 2
    f = gb.bytes("flags", 1)[0]
    assert f & (1 << F_DADO) and not f & (1 << F_LE_GUSTA)
    assert gb.u8("vram_late") == 0 and gb.u8("vq_lost") == 0


def test_second_talk_yes_branch_skips_the_gift(gb):
    start_talk(gb)
    gb.write_bytes("flags", [1 << F_DADO])
    for _ in range(3):
        assert wait_state(gb, TB_PAGE) or gb.u8("tbox_state") == TB_END
        gb.tap("a")
    assert wait_state(gb, TB_YESNO)
    gb.tap("a")                                           # Si
    assert wait_state(gb, TB_END)
    assert win_line(gb, 2) == "Me alegro."
    gb.tap("a")
    assert wait_state(gb, TB_CHOOSE)
    gb.tap("a")                                           # Uno
    gb.frames(10)
    assert gb.u8("script_active") == 0
    assert gb.bytes("flags", 1)[0] & (1 << F_LE_GUSTA)
    assert gb.u8("given_count") == 0 and gb.bytes("vars", 1)[0] == 0


def test_a_mid_page_finishes_it_quickly(gb):
    start_talk(gb)
    gb.frames(3)
    gb.tap("a")
    gb.frames(6)
    assert gb.u8("tbox_state") == TB_PAGE
