"""TORRE HUNDIDA M1b: title, pause menu, OBJETOS, ESTADO, automap, save/continue, game over,
clear (design/ui.md 3-9)."""
from gbtest import GB
from conftest import boot, start_play, wait_state
from test_game import CHEAT_FROZEN, CHEAT_INVINCIBLE, CHEAT_SEEN_ALL
from test_play import clear_monsters, place, put_monster
from view_model import BASES, expected, shown

ST_TITLE, ST_PLAY, ST_MENU, ST_MAP, ST_GAMEOVER, ST_CLEAR = range(6)
T_0, T_UI, T_LOWER = BASES["font"], BASES["ui"], BASES["font_lower"]
CURSOR = 9                                                   # ui.tiles: BLANK, 8 frame pieces, CURSOR


def text_at(rows, r, c, n):
    """Text of a map row, uppercased: the mockups' case is the ui-designer's choice."""
    return GB.tile_text(rows[r][c:c + n], T_0, T_LOWER).upper()


def visible(gb):
    return gb.bg_map(map=gb.active_bg())


def settle(gb, n=12):
    gb.frames(n)


def test_title_without_save(title):
    rows = title.bg_map(map=0)
    assert "NUEVA PARTIDA" in "".join(text_at(rows, r, 0, 20) for r in range(18))
    assert "CONTINUAR" not in "".join(text_at(rows, r, 0, 20) for r in range(18))
    title.screenshot("title")


def test_pause_menu_and_estado(gb):
    gb.write_u8("cheat_flags", CHEAT_FROZEN | CHEAT_INVINCIBLE)
    gb.tap("start")
    settle(gb)
    assert gb.u8("state") == ST_MENU
    v = visible(gb)
    assert text_at(v, 8 + 4, 7, 7) == "OBJETOS" and v[8 + 4][6] == CURSOR
    gb.screenshot("pause")
    gb.tap("down")
    settle(gb, 4)
    assert visible(gb)[8 + 5][6] == CURSOR
    gb.tap("a")                                              # ESTADO
    settle(gb)
    v = visible(gb)
    assert text_at(v, 8 + 4, 13, 5) == "20/20"
    gb.screenshot("estado")
    gb.tap("b")                                              # back to the pause box
    settle(gb)
    assert gb.u8("menu_page") == 0
    gb.tap("start")                                          # close all
    settle(gb)
    assert gb.u8("state") == ST_PLAY
    assert shown(gb) == expected(gb.bytes("dmap", 256), gb.u8("px"), gb.u8("py"), gb.u8("pf"))
    assert gb.u8("vram_late") == 0


def test_drink_potion_from_objetos(gb):
    gb.write_u8("cheat_flags", CHEAT_FROZEN | CHEAT_INVINCIBLE)
    gb.write_u8("hp", 5)
    gb.write_u8("potions", 1)
    gb.tap("start")
    settle(gb)
    gb.tap("a")                                              # OBJETOS (remembered option 0)
    settle(gb)
    assert gb.u8("menu_page") == 1
    assert text_at(visible(gb), 8 + 4, 4, 6) == "POCION"
    gb.screenshot("objetos")
    gb.tap("a")
    settle(gb, 30)
    assert gb.u8("hp") == 15 and gb.u8("potions") == 0


def test_automap_hides_window_and_shows_seen(gb):
    gb.write_u8("cheat_flags", CHEAT_FROZEN | CHEAT_INVINCIBLE | CHEAT_SEEN_ALL)
    gb.tap("select")
    settle(gb, 20)
    assert gb.u8("state") == ST_MAP and not (gb.io(0xFF40) & 0x20)    # window off
    gb.screenshot("automap")
    gb.tap("b")
    settle(gb, 20)
    assert gb.u8("state") == ST_PLAY and gb.io(0xFF40) & 0x20
    assert shown(gb) == expected(gb.bytes("dmap", 256), gb.u8("px"), gb.u8("py"), gb.u8("pf"))


def test_save_then_continue_after_power_off(gb):
    gb.write_u8("cheat_flags", CHEAT_FROZEN | CHEAT_INVINCIBLE)
    clear_monsters(gb)
    place(gb, 5, 8, 1)
    gb.write_u8("potions", 3)
    gb.tap("start")
    settle(gb)
    for _ in range(3):
        gb.tap("down")
        settle(gb, 4)
    gb.tap("a")                                              # GUARDAR
    settle(gb, 30)
    ram = gb.power_off()
    g2 = boot(ram)
    try:
        rows = g2.bg_map(map=0)
        assert "CONTINUAR" in "".join(text_at(rows, r, 0, 20) for r in range(18))
        assert g2.u8("menu_sel") == 1                        # cursor on CONTINUAR
        g2.tap("start")
        assert wait_state(g2, ST_PLAY)
        g2.frames(10)
        assert (g2.u8("px"), g2.u8("py"), g2.u8("pf"), g2.u8("potions")) == (5, 8, 1, 3)
        assert shown(g2) == expected(g2.bytes("dmap", 256), 5, 8, 1)
    finally:
        g2.close()


def test_death_gameover_continue_loads_save(gb):
    gb.write_u8("cheat_flags", CHEAT_FROZEN | CHEAT_INVINCIBLE)
    clear_monsters(gb)
    place(gb, 5, 8, 1)
    gb.tap("start")
    settle(gb)
    for _ in range(3):
        gb.tap("down")
        settle(gb, 4)
    gb.tap("a")                                              # save at (5, 8)
    settle(gb, 20)
    gb.tap("start")
    settle(gb)
    place(gb, 3, 8, 3)
    gb.write_u8("cheat_flags", 0)
    m = gb.bytes("mon_type", 12).index(0)
    put_monster(gb, m, 3, 2, 8)
    gb.write_u8("hp", 1)
    assert wait_state(gb, ST_GAMEOVER, 1500)
    gb.frames(20)
    gb.screenshot("gameover")
    gb.tap("start")                                          # CONTINUAR
    assert wait_state(gb, ST_PLAY, 200)
    gb.frames(10)
    assert (gb.u8("px"), gb.u8("py")) == (5, 8) and gb.u8("hp") > 0


def test_stairs_to_clear_and_title(gb):
    gb.write_u8("cheat_flags", CHEAT_FROZEN | CHEAT_INVINCIBLE)
    clear_monsters(gb)
    place(gb, 13, 13, 1)                                     # the stairs X at (14, 13)
    gb.tap("up")
    assert wait_state(gb, ST_CLEAR, 200)
    gb.frames(10)
    gb.screenshot("clear")
    gb.frames(30)
    gb.tap("start")
    assert wait_state(gb, ST_TITLE, 200)
