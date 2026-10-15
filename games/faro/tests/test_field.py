"""FARO field (GDD 2.1-2.3, 2.9): new game, the start items, doors between maps, the screen equals
the map model, talking, save and continue after a power cycle."""
from faro_nav import GAME, MAP_IDS, current_map, map_model, new_game, settle, walk_to
from gbtest import GB
from battle_model import T

ITEM = T["items"].ids


def region_errors(gb):
    """Every cell of the drawn region == the map model (gbe_world region 13x12)."""
    m = current_map(gb)
    rx, ry = gb.u8("reg_x"), gb.u8("reg_y")
    bg = gb.bg_map(map=0)
    import screens, preview, json, metatiles
    bad = []
    tiles = {i: [m_tile for m_tile in t] for i, t in enumerate(_mt_tiles(m))}
    for r in range(12):
        for c in range(13):
            x, y = (rx + c) & 0xFF, (ry + r) & 0xFF
            t4 = tiles[m.at(x, y)]
            got = [bg[(y & 15) * 2 + k // 2][(x & 15) * 2 + k % 2] for k in range(4)]
            if got != t4:
                bad.append((x, y))
    return bad


_MT = {}


def _mt_tiles(m):
    if m.mt_stem not in _MT:
        import json, metatiles, preview, screens
        from faro_nav import GAME
        sets = preview.find_tilesets(GAME)
        cfg = json.loads((GAME / "game.json").read_text(encoding="utf-8"))
        bases = screens.vram_bases(cfg["vram_order"], sets)
        mt_file = GAME / "res" / f"{m.mt_stem}.mt"
        ts = next(l.split()[2] for l in mt_file.read_text(encoding="utf-8").splitlines() if l.startswith("@ tileset"))
        mt = metatiles.parse(mt_file, sets[ts].labels, bases)
        _MT[m.mt_stem] = [mt.vram_tiles(i) for i in range(len(mt.names))]
    return _MT[m.mt_stem]


def test_new_game_starts_home_with_the_items(gb):
    new_game(gb)
    assert gb.u8("wmap_id") == MAP_IDS["MAP_CASA_INES"]
    assert (gb.u8("px"), gb.u8("py")) == (11, 6)
    inv = gb.bytes("inv", 128)
    assert inv[ITEM["POCION"]] == 2 and inv[ITEM["CUCHILLO"]] == 1
    assert gb.bytes("weapons", 3)[0] == ITEM["CUCHILLO"] and gb.u8("armor") == ITEM["ROPA_FAENA"]
    assert gb.u8("plevel") == 2 and gb.u8("pv") == gb.u8("pv_max") > 0
    assert region_errors(gb) == []
    gb.screenshot("casa")


def test_door_to_the_island_and_back(gb):
    new_game(gb)
    assert walk_to(gb, (7, 11)) or gb.u8("wmap_id") == MAP_IDS["MAP_ISLA"]
    assert settle(gb)
    assert gb.u8("wmap_id") == MAP_IDS["MAP_ISLA"] and (gb.u8("px"), gb.u8("py")) == (36, 83)
    gb.frames(20)
    assert region_errors(gb) == []
    gb.screenshot("varadero")
    assert gb.u8("vram_late") == 0


def test_walk_varadero_screen_matches_map(gb):
    new_game(gb)
    walk_to(gb, (7, 11))
    settle(gb)
    gb.write_u8("max_frame_lines", 0)                     # the title's menu frame is not the field
    gb.write_u8("cheat_flags", 1)                         # creatures live (their cost counts) but start no battle
    for goal in ((40, 86), (50, 88), (36, 84)):
        walk_to(gb, goal, limit=80)
        gb.frames(10)
        assert region_errors(gb) == [], goal
    assert gb.u8("vram_late") == 0 and gb.u16("world_lost") == 0
    print("worst lines", gb.u8("max_frame_lines"))
    assert gb.u8("max_frame_lines") < 120


def test_save_and_continue(gb):
    new_game(gb)
    walk_to(gb, (9, 8))
    gb.write_u16("money", 77)
    gb.write_u8("save_req", 1)                            # what the panel's Guardar will do
    gb.frames(4)
    ram = gb.power_off()
    g2 = GB(GAME / "build" / "faro.gb", ram=ram)
    try:
        g2.frames(10)
        g2.tap("start")
        g2.frames(10)
        assert g2.u8("menu_sel") == 0                     # cursor on Continuar
        g2.tap("a")
        assert settle(g2)
        assert g2.u8("wmap_id") == MAP_IDS["MAP_CASA_INES"] and (g2.u8("px"), g2.u8("py")) == (9, 8)
        assert g2.u16("money") == 77
    finally:
        g2.close()


def test_field_graphics_are_their_own(gb):
    """Every visible sprite and BG tile holds its own graphics (game.json vram_scenes 'field'):
    the title loaded its beam over the NPC sprite tiles and nobody reloaded them."""
    new_game(gb)
    walk_to(gb, (7, 11))
    settle(gb)
    gb.frames(30)
    errs = gb.vram_errors("field")
    gb.screenshot("field_graphics")
    assert errs == [], "\n".join(errs[:10])
