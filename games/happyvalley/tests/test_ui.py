"""HAPPY VALLEY management screens (greybox): what is on screen. ESTABLO lists the stable's horses and
the farm, FICHA shows a horse and changes its plan with left/right, Start advances the week to the
INFORME and back. Text is read from the screen pixels (gb.read_text)."""

HSIZE = 41


def wait(gb, n=90):
    gb.frames(n)                                # a transition: fade 16 + build + fade 16


def screen(gb):
    return [gb.read_text(r).strip() for r in range(18)]


def test_stable_lists_horses(gb):
    wait(gb)
    s = screen(gb)
    assert s[0].startswith("Semana 1") and "800k" in s[1]
    for name in ("Oro Sesenta", "Viento Feliz", "Perla Lunar"):
        assert any(r.startswith(name) for r in s), (name, s)
    assert any("Granja: Brisa Dorada" in r for r in s)
    assert gb.u8("ui_next") <= 200


def test_sheet_changes_plan(gb):
    wait(gb)
    gb.tap("down"); gb.frames(4)
    gb.tap("a"); wait(gb)
    s = screen(gb)
    assert s[0] == "Viento Feliz" and any(r.startswith("Vel") for r in s)
    gb.tap("right"); gb.frames(6)
    plan = gb.bytes("hv_horse", 2 * HSIZE)[HSIZE + 10]
    assert plan == 1                            # Descanso -> Galope
    assert "Galope" in gb.read_text(15)
    gb.tap("b"); wait(gb)
    assert any("Galope" in r for r in screen(gb))


def test_start_advances_week_to_report(gb):
    wait(gb)
    gb.tap("start"); wait(gb)
    s = screen(gb)
    assert s[0] == "Parte de la semana 2", s
    assert any(r.startswith("Gastos -63k") for r in s) and any("737k" in r for r in s)
    gb.tap("a"); wait(gb)
    assert screen(gb)[0].startswith("Semana 2")
