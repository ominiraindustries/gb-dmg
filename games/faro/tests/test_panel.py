"""FARO Start panel (ui.md 5), the text box really on screen (ui.md 4), the HUD (ui.md 3) and
survival by steps (GDD 2.5). Text is read from what the screen shows (gb.screen_tiles: BG + window
as LCDC has them), not from the window map: a box written to a disabled window looks fine in VRAM."""
from faro_nav import GAME, MAP_IDS, new_game, screen_text, settle, step, walk_to
from gbtest import GB
from battle_model import T

ITEM = T["items"].ids
PN_CLOSED, PN_IN, PN_MENU, PN_OUT, PN_NOTE, PN_ASK = range(6)


def open_panel(gb):
    gb.tap("start")
    for _ in range(30):
        gb.frames(1)
        if gb.u8("panel_state") == PN_MENU:
            return
    assert False, "the panel did not open"


def panel_text(gb):
    return [r[10:].strip() for r in screen_text(gb)]


def test_sign_text_is_on_screen(gb):
    new_game(gb)
    walk_to(gb, (7, 11))
    settle(gb)
    gb.write_u8("cheat_flags", 2)                       # frozen creatures: nothing interrupts the walk
    walk_to(gb, (41, 85), limit=120)
    step(gb, "right")                                   # face the sign at (42, 85)
    gb.tap("a")
    gb.frames(60)
    assert gb.window_on()
    text = " ".join(screen_text(gb)[12:18])
    assert "Varadero" in text, text
    gb.screenshot("sign")


def test_panel_slides_in_with_the_stats_and_closes(gb):
    new_game(gb)
    gb.tap("start")
    gb.frames(5)
    assert gb.u8("panel_state") == PN_IN and gb.io(0xFF4B) > 87        # still sliding
    for _ in range(30):
        gb.frames(1)
        if gb.u8("panel_state") == PN_MENU:
            break
    gb.frames(1)
    assert gb.u8("panel_state") == PN_MENU and gb.io(0xFF4B) == 87 and gb.window_on()
    rows = panel_text(gb)
    assert rows[1:8] == ["Cuaderno", "Mochila", "Equipo", "Acampar", "Guardar", "Opciones", "Salir"], rows
    pv, pv_max, en, en_max = gb.u8("pv"), gb.u8("pv_max"), gb.u8("en"), gb.u8("en_max")
    assert rows[11].endswith(str(gb.u8("plevel")))
    assert rows[12] == f"{pv}/{pv_max}" and rows[13].replace(" ", "") == f"EN{en}/{en_max}"
    assert rows[14] == "Llena" if gb.u8("sac") >= 60 else "Normal"
    assert rows[15].endswith(str(gb.u16("money")))
    oam = gb.pyboy.memory[0xFE00:0xFE08]
    assert (oam[0], oam[1]) == (96 + 16, 88 + 8) and (oam[4], oam[5]) == (112 + 16, 88 + 8)   # HUD = labels
    gb.screenshot("panel")
    x, y = gb.u8("px"), gb.u8("py")
    gb.tap("down")                                      # the field is paused: the cursor moves, not Leo
    gb.frames(4)
    assert (gb.u8("px"), gb.u8("py")) == (x, y) and gb.u8("menu_sel") == 1
    gb.tap("b")
    gb.frames(14)
    assert gb.u8("panel_state") == PN_CLOSED and not gb.window_on()


def test_camp_refused_indoors(gb):
    new_game(gb)                                        # Ines' house: no CAMP cells
    open_panel(gb)
    for _ in range(3):
        gb.tap("down")
        gb.frames(3)
    gb.tap("a")
    gb.frames(10)
    assert gb.u8("panel_state") == PN_NOTE
    text = " ".join(panel_text(gb)[10:17])
    assert "Aqui no" in text and "acampar" in text, text
    gb.frames(100)                                      # 90 f, then the stats come back
    assert gb.u8("panel_state") == PN_MENU and panel_text(gb)[12] == f"{gb.u8('pv')}/{gb.u8('pv_max')}"


def test_save_from_the_panel_and_continue(gb):
    new_game(gb)
    walk_to(gb, (9, 8))
    gb.write_u16("money", 123)
    open_panel(gb)
    for _ in range(4):
        gb.tap("down")
        gb.frames(3)
    gb.tap("a")
    gb.frames(10)
    assert gb.u8("panel_state") == PN_ASK
    assert any("Guardar" in r for r in panel_text(gb)[14:17])
    gb.tap("a")
    gb.frames(30)
    assert "Guardado" in " ".join(panel_text(gb)[14:17])
    gb.frames(60)
    assert gb.u8("panel_state") == PN_MENU
    ram = gb.power_off()
    g2 = GB(GAME / "build" / "faro.gb", ram=ram)
    try:
        g2.frames(10)
        g2.tap("start")
        g2.frames(10)
        g2.tap("a")                                     # Continuar
        assert settle(g2)
        assert g2.u8("wmap_id") == MAP_IDS["MAP_CASA_INES"] and (g2.u8("px"), g2.u8("py")) == (9, 8)
        assert g2.u16("money") == 123
    finally:
        g2.close()


def walk_steps(gb, n):
    """n completed steps back and forth between two free cells of the house."""
    done, d = 0, "left"
    while done < n:
        if step(gb, d):
            done += 1
        else:
            d = "right" if d == "left" else "left"
        while gb.u8("tbox_visible") or gb.u8("script_active"):
            gb.tap("a")
            gb.frames(20)
    return done


def test_hunger_by_steps_warning_and_hud(gb):
    new_game(gb)
    walk_to(gb, (9, 8))
    gb.write_u8("sac", 25)                              # one tick above 'hungry' (RULE SAC_HUNGRY 25)
    gb.frames(200)                                      # the band-change show of the HUD runs out
    assert gb.pyboy.memory[0xFE04] != 0                 # bowl: 25-59 = half, always shown
    seen_warning = False
    done, d = 0, "left"
    while done < 33 and not seen_warning:
        if step(gb, d):
            done += 1
        else:
            d = "right" if d == "left" else "left"
        if gb.u8("tbox_visible"):
            gb.frames(80)
            seen_warning = "tripas" in " ".join(screen_text(gb)[12:18])
    assert seen_warning and gb.u8("sac") == 24
    gb.screenshot("hunger_warning")
    while gb.u8("tbox_visible") or gb.u8("script_active"):
        gb.tap("a")
        gb.frames(30)
    assert gb.bytes("flags", 3)[2] & 1                  # F_AVISO_HAMBRE (16): the script sets it


def test_perishables_go_off(gb):
    new_game(gb)
    walk_to(gb, (9, 8))
    meat = ITEM["MUSLO_CONEJO"]
    inv = gb.addr("inv")
    gb.write_u8("food_age", 39)                         # RULE AGE_SPOIL 40: the next age tick spoils
    gb.pyboy.memory[inv + meat] = 3
    walk_steps(gb, 64)                                  # RULE AGE_STEPS 64
    items = gb.bytes("inv", 128)
    past = T["items"].rows[meat]["pasado"]
    past = ITEM[past] if isinstance(past, str) else past
    assert items[meat] == 1 and items[past] == 2  # half rounded up went off
    assert gb.u8("food_age") in (20, 21)                # RULE AGE_AFTER (+1 if the walk ended past a tick)


def test_title_screen_is_its_mockup(gb):
    """The title on screen == design/screens/title.screen (the blinking 'Pulsa Start' aside)."""
    gb.frames(10)
    errs = gb.mockup_errors("title", ignore=["PULSA_START"])
    assert errs == [], errs[:10]
