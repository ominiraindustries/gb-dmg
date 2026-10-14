"""FARO battle screen (ui.md 6): a battle from the field, the command menu, attacking until the end,
messages, back to the field where it started."""
from faro_nav import MAP_IDS, new_game, settle, walk_to
from battle_model import T

ST_BATTLE = 2
SPECIES = T["species"].ids


def start_battle(gb, species="PINZARRO", level=2, free=0):
    gb.write_u8("bt_a", SPECIES[species])
    gb.write_u8("bt_b", level)
    gb.write_u8("bt_c", free)
    gb.write_u8("bt_cmd", 6)
    for _ in range(120):
        gb.frames(1)
        if gb.u8("state") == ST_BATTLE and not gb.u8("trans_phase"):
            return True
    return False


def wait_menu(gb, limit=900):
    """Advance messages (A) until the command menu or the end of the battle."""
    for f in range(limit):
        gb.frames(1)
        if gb.u8("state") != ST_BATTLE:
            return "left"
        if gb.u8("bu_state") == 1:
            return "menu"
        if f % 20 == 0:
            gb.tap("a")
    return "stuck"


def test_battle_from_field_attack_until_it_ends(gb):
    new_game(gb)
    walk_to(gb, (7, 11))
    settle(gb)
    pos = (gb.u8("px"), gb.u8("py"))
    gb.write_u8("cheat_flags", 2)                     # frozen creatures: no second battle on return
    gb.write_u8("plevel", 8)
    gb.write_u8("bt_cmd", 5)
    gb.frames(3)
    gb.write_u8("pv", gb.u8("pv_max"))
    assert start_battle(gb)
    gb.frames(30)
    gb.screenshot("battle_intro")
    assert wait_menu(gb) == "menu"
    gb.screenshot("battle_menu")
    for turn in range(15):
        gb.tap("a")                                   # Atacar
        gb.frames(12)
        if turn == 0:
            gb.screenshot("battle_attack_list")
        gb.tap("a")                                   # the first weapon
        r = wait_menu(gb)
        if r == "left":
            break
        assert r == "menu", (turn, r)
    assert settle(gb)
    assert gb.u8("wmap_id") == MAP_IDS["MAP_ISLA"] and (gb.u8("px"), gb.u8("py")) == pos
    assert gb.u8("b_result") in (1, 5)               # hunted (or fainted at worst)
    assert gb.u8("vram_late") == 0
    gb.screenshot("after_battle")
