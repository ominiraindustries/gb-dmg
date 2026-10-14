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
    return GB.tile_text(gb.bg_map(window=True)[row][1:19], BASES["font"], BASES["font_lower"], BASES["font_es"]).strip()


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
    assert win_line(gb, 2) == "¡Hola Leo! Esta" and win_line(gb, 4) == "es una prueba"
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
    assert gb.u8("given_item") == 3 and gb.u8("given_count") == 2
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


def test_table_ids_and_rom_rows(gb):
    import tables
    t = tables.load_all(GAME / "res" / "data")["items"]
    assert t.ids["FAROL"] == 3 and t["FAROL"]["better"] == t.ids["MACHETE"]
    assert t["FAROL"]["ability"] == 0b110 and t["CARNE"]["perece"] == 1
    # the ROM table: tbl_items rows of 15 + 1 + 2 + 1 + 1 + 1 = 21 bytes
    bank, addr = gb.syms["tbl_items"] >> 16, gb.syms["tbl_items"] & 0xFFFF      # .noi: bank << 16 | address
    for i, r in enumerate(t.rows):
        row = [gb.pyboy.memory[bank, addr + i * 21 + k] for k in range(21)]
        assert bytes(row[:15]).rstrip(b"\0").decode("latin-1") == r["name"]
        assert row[15] == r["cat"] and row[16] | (row[17] << 8) == r["price"]
        assert row[18:21] == [r["ability"], r["perece"], 0xFF if r["better"] is None else r["better"]]


def test_tile_queue_copies_rom_data_over_two_frames(gb):
    import asciitiles
    tiles, _ = asciitiles.parse(GAME / "res" / "spr.tiles")
    want = b"".join(asciitiles.tile_bytes(t) for t in tiles[:6]) if hasattr(asciitiles, "tile_bytes") else None
    gb.frames(2)
    gb.write_u8("tq_test", 1)
    gb.frames(1)
    assert gb.u8("tiles_lost") == 0
    gb.frames(3)
    got = bytes(gb.pyboy.memory[0x8000 + 60 * 16 + k] for k in range(6 * 16))
    src = bytes(gb.pyboy.memory[0x8000 + k] for k in range(6 * 16))   # spr tiles were loaded at 0
    assert got == src
