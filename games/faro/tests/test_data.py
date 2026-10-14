"""FARO data tables (res/data/*.tbl), pure Python: integrity of the M1b data and the GDD 3.10 worked
examples reproduced with the integer formulas of GDD 3.3/3.4/3.6 and the numbers of the tables.
The formula helpers here are the seed of battle_model.py (GDD 11: "Combate == modelo")."""
from pathlib import Path

import tables

GAME = Path(__file__).resolve().parents[1]
T = tables.load_all(GAME / "res" / "data")
RULE = {r["id"]: r["v"] for r in T["rules"].rows}
RECIP = [0] * 4 + [1024 // d for d in range(4, 256)]       # RECIP[d] = 1024 / d (u16 table, d >= 4)


def rid(table, key):
    return T[table].ids[key]


def row(table, key):
    return T[table][key]


def bit(table, key):
    return 1 << rid(table, key)


# ---------------------------------------------------------------- formulas (GDD 3.2-3.6)
def creature_stats(tiers, level):
    tpv, tat, tdf, tag = tiers
    return (min(255, 10 + ((tpv * level * 3) >> 3)), 4 + ((tat * level * 3) >> 4),
            3 + ((tdf * level * 3) >> 4), 2 + ((tag * level * 3) >> 4))


def species_tiers(key):
    s = row("species", key)
    return s["tpv"], s["tat"], s["tdf"], s["tag"]


def player_stats(level, armor="ROPA_FAENA"):
    p = row("player", f"L{level:02d}")
    return p["pv"], p["atq"], p["def"] + row("items", armor)["val"], p["agi"]


def damage(atq, def_, pot, dtype, weak=0, resist=0, immune=0, mul=8, crit=False, rnd=0,
           target_pv=None, gentle=False):
    """GDD 3.4 in order: R16 -> base -> type -> crit -> mods (mul = technique, in 1/8) -> random -> min 1
    -> gentle cap. rnd = the raw rng byte (only rnd & DMG_RND is used)."""
    d_ = max(RULE["DEF_MIN"], def_)
    r16 = min(RULE["R16_MAX"], max(RULE["R16_MIN"], (atq * RECIP[d_]) >> 6))
    d = (pot * r16) >> 4
    b = 1 << dtype
    if immune & b:
        return 0
    if weak & b:
        d <<= 1
    elif resist & b:
        d >>= 1
    if crit:
        d += d >> 1
    d = (d * mul) >> 3
    d -= (d * (rnd & RULE["DMG_RND"])) >> 8
    d = max(1, d)
    if gentle and target_pv is not None and d >= target_pv:
        d = target_pv - 1
    return d


def q_hp(pv, pvmax):
    if pv * 8 <= pvmax:
        return RULE["QHP_12"]
    if pv * 4 <= pvmax:
        return RULE["QHP_25"]
    if pv * 2 <= pvmax:
        return RULE["QHP_50"]
    return RULE["QHP_HI"]


def catch_value(catch, pv, pvmax, status=None, lantern="FAROLILLO", bait=None, fav=None, fam=None):
    lt = row("items", lantern)
    if lt["val"] == 255:
        return 255
    q_st = row("statuses", status)["q"] if status else RULE["QST_NONE"]
    q_tool = lt["val2"] if (lt["fam"] is not None and lt["fam"] == fam) else lt["val"]
    q_bait = RULE["QBAIT_NONE"] if bait is None else (RULE["QBAIT_FAV"] if bait == fav else RULE["QBAIT_OTHER"])
    v = catch
    for q in (q_hp(pv, pvmax), q_st, q_tool, q_bait):
        v = (v * q) >> 2
    return v


def flee_p(agi_p, agi_c, tries=0):
    p = RULE["FLEE_BASE"] + RULE["FLEE_AGI"] * (agi_p - agi_c) + RULE["FLEE_TRY"] * tries
    return min(RULE["FLEE_MAX"], max(RULE["FLEE_MIN"], p))


def weapon(key):
    w = row("items", key)
    return w["pot"], w["dtype"]


def defs_of(species=None, family=None):
    src = row("species", species) if species else row("families", family)
    return dict(weak=src["debil"], resist=src["resiste"], immune=src["inmune"])


# ---------------------------------------------------------------- GDD 3.10 A: Leo L3 vs Pinzarro L3
def test_example_a_stats():
    assert creature_stats(species_tiers("PINZARRO"), 3) == (16, 6, 6, 3)
    assert player_stats(3) == (30, 8, 7, 8)


def test_example_a_knife_takes_four_hits():
    pv, atq, _, _ = player_stats(3)
    cpv, _, cdef, _ = creature_stats(species_tiers("PINZARRO"), 3)
    pot, dt = weapon("CUCHILLO")
    assert (pot, dt) == (8, rid("dtypes", "CORTE"))
    for rnd in (0, 31):
        d = damage(atq, cdef, pot, dt, **defs_of("PINZARRO"), rnd=rnd)
        assert d == 5                                        # 10, resists CUT -> 5
        assert -(-cpv // d) == 4


def test_example_a_oar_kills_in_one_hit():
    _, atq, _, _ = player_stats(3)
    cpv, _, cdef, _ = creature_stats(species_tiers("PINZARRO"), 3)
    pot, dt = weapon("REMO")
    assert damage(atq, cdef, pot, dt, **defs_of("PINZARRO")) == 18
    for rnd in range(32):
        assert damage(atq, cdef, pot, dt, **defs_of("PINZARRO"), rnd=rnd) >= cpv     # hunt, not capture


def test_example_a_gentle_blow_then_lantern_88_percent():
    _, atq, _, _ = player_stats(3)
    cpv, _, cdef, _ = creature_stats(species_tiers("PINZARRO"), 3)
    pot, dt = weapon("REMO")
    gs = row("skills", "GOLPE_SUAVE")
    assert gs["suave"] == 1 and gs["nivel"] == 3
    left = set()
    for rnd in range(32):
        d = damage(atq, cdef, pot, dt, **defs_of("PINZARRO"), mul=gs["mul"], rnd=rnd, target_pv=cpv, gentle=True)
        left.add(cpv - d)
    assert left == {3, 4}                                   # (18 * 6) >> 3 = 13, random 12-13
    for pv in left:
        assert q_hp(pv, cpv) == 6
        v = catch_value(row("species", "PINZARRO")["catch"], pv, cpv)
        assert v == 225 and round(100 * v / 256) == 88


def test_example_a_claw_against_leo():
    _, _, def_, _ = player_stats(3)
    _, catq, _, _ = creature_stats(species_tiers("PINZARRO"), 3)
    m = row("moves", "PINZA")
    for rnd in (0, 31):
        assert damage(catq, def_, m["pot"], m["dtype"], rnd=rnd) == 4


# ---------------------------------------------------------------- GDD 3.10 B: Leo L20 vs Musgali L20
MUSGALI = dict(tiers=(9, 9, 7, 6), catch=80, family="BESTIA")      # species row #15 arrives in M3


def test_example_b_stats():
    assert creature_stats(MUSGALI["tiers"], 20) == (77, 37, 29, 24)
    assert player_stats(20, "CAPA") == (98, 34, 37, 25)


def test_example_b_machete_two_hits_to_half():
    _, atq, _, _ = player_stats(20, "CAPA")
    cpv, _, cdef, _ = creature_stats(MUSGALI["tiers"], 20)
    pot, dt = weapon("MACHETE")
    assert damage(atq, cdef, pot, dt, **defs_of(family="BESTIA")) == 28
    assert cpv - 2 * 28 == 21
    for rnd in (0, 31):
        left = cpv - 2 * damage(atq, cdef, pot, dt, **defs_of(family="BESTIA"), rnd=rnd)
        assert q_hp(left, cpv) == RULE["QHP_50"]


def test_example_b_charge_leo_survives_7_or_8():
    pv, _, def_, _ = player_stats(20, "CAPA")
    _, catq, _, _ = creature_stats(MUSGALI["tiers"], 20)
    m = row("moves", "CARGA")
    assert (m["pot"], m["dtype"]) == (14, rid("dtypes", "GOLPE"))
    assert damage(catq, def_, m["pot"], m["dtype"]) == 13
    survived = {(pv - 1) // damage(catq, def_, m["pot"], m["dtype"], rnd=r) for r in (0, 31)}
    assert survived == {7, 8}


def test_example_b_capture_flee_and_accuracy():
    _, _, _, agi = player_stats(20, "CAPA")
    cpv, _, _, cagi = creature_stats(MUSGALI["tiers"], 20)
    left = 21
    with_dart = catch_value(MUSGALI["catch"], left, cpv, status="DORMIDO", lantern="FAROLILLO_FINO")
    without = catch_value(MUSGALI["catch"], left, cpv, lantern="FAROLILLO_FINO")
    assert (with_dart, without) == (240, 120)
    assert (round(100 * with_dart / 256), round(100 * without / 256)) == (94, 47)
    assert row("items", "DARDO")["st"] == rid("statuses", "DORMIDO")
    assert flee_p(agi, cagi) == 136 and round(100 * 136 / 256) == 53
    assert row("items", "MACHETE")["acc"] == 242


# ---------------------------------------------------------------- data integrity (M1b)
def test_fixed_ids_used_by_maps_and_art():
    assert [(r["id"], r["spr"]) for r in T["looks"].rows][:3] == [("ABUELA", 0), ("PESCADOR", 16), ("VECINA", 32)]
    for key in ("PLAYA_VAR", "SENDERO", "CABO", "CLARO"):
        assert key in T["spawns"].ids
    for key in ("BAYAS", "RAMAS"):
        assert key in T["forage"].ids
    for key in ("POCION", "FAROLILLO", "SAL", "MADERA", "PAN", "MACHETE", "CEBO_CARNE"):
        assert key in T["items"].ids
    assert len(T["items"]) <= 128                            # items[128] in the save


def test_player_table_matches_gdd_formulas():
    for L in range(1, 41):
        p = row("player", f"L{L:02d}")
        assert (p["pv"], p["en"], p["atq"], p["def"], p["agi"]) == (
            18 + 4 * L, 8 + L, 4 + L + (L >> 1), 3 + L + (L >> 2), 5 + L)
        assert p["xp"] == (8 + 4 * L + L * L if L < 40 else 0)
    assert row("player", "L35")["xpacum"] == 16337


def test_species_match_art_and_family_defaults():
    crit = [ln[2:].strip() for ln in (GAME / "res" / "critters.tiles").read_text(encoding="utf-8").splitlines()
            if ln.startswith("@ ")]
    for s in T["species"].rows:
        name = s["name"].upper()
        assert (GAME / "res" / f"battle_{name.lower()}.tiles").exists()
        assert crit[2 * s["fspr"]] == f"{name}_A"
        fam = T["families"][s["fam"]]
        assert (s["debil"], s["resiste"], s["inmune"]) == (fam["debil"], fam["resiste"], fam["inmune"]), name
        assert sum(s[f"w{k}"] for k in range(1, 5)) > 0
        assert s["b1"] is not None and 1 <= s["b1lo"] <= s["b1hi"]
        assert s["cebo"] is not None and T["items"][s["cebo"]]["cebo"] & s["come"]


def test_every_species_spawns_and_levels_fit():
    seen = set()
    for sp in T["spawns"].rows:
        for k in range(1, 5):
            if sp[f"e{k}"] is None:
                continue
            seen.add(sp[f"e{k}"])
            lo, hi = sp[f"e{k}lo"], sp[f"e{k}hi"]
            assert 1 <= lo <= hi <= 40 and sp[f"e{k}w"] > 0
            tiers = species_tiers(T["species"][sp[f"e{k}"]]["id"])
            assert creature_stats(tiers, hi)[0] <= 255
    assert seen == set(range(len(T["species"])))


def m1b_sources():
    """Items a player can get in the M1b slice: Varadero shop, forage, loot, salting."""
    items = T["items"]
    src = {i for k in range(1, 17) if (i := T["shops"]["VARADERO"][f"i{k:02d}"]) is not None}
    for f in T["forage"].rows:
        src |= {f["it"], f["it2"]} - {None}
    for s in T["species"].rows:
        src |= {s["b1"], s["b2"], s["b3"]} - {None}
    src |= {items[i]["salado"] for i in list(src) if items[i]["salado"] is not None}
    return src


def test_recipes_1_to_8_can_be_cooked_in_m1b():
    items, src = T["items"], m1b_sources()
    ing = [c for c in T["recipes"].cols if c["name"] == "ac"][0]["values"]
    for r in T["recipes"].rows:
        assert items[r["res"]]["cat"] == items.cols[3]["values"].index("PLATO")
        for s in "abc":
            it, cat = r[f"{s}x"], r[f"{s}c"]
            assert not (it is not None and cat != 0), r["id"]
            if it is not None:
                assert it in src, (r["id"], items[it]["id"])
            elif cat:
                b = 1 << (cat - 1)
                assert any(items[i]["ing"] & b for i in src), (r["id"], ing[cat])
    assert [r["id"] for r in T["recipes"].rows if r["inicio"]] == ["ASADO", "PESCADO_ASADO", "CALDO_ALGAS"]


def test_items_consistency():
    items = T["items"]
    cat = items.cols[3]["values"]
    for it in items.rows:
        if it["perece"]:
            p = items[it["pasado"]]
            assert p["cebo"] and not p["perece"], it["id"]
        if it["precio"] and cat[it["cat"]] != "DINERO":
            assert it["venta"] * 2 <= it["precio"], it["id"]
        if cat[it["cat"]] in ("LLAVE", "ARMA", "ROPA"):
            assert T["caps"][it["tope"]]["id"] == "UNICO", it["id"]
        if cat[it["cat"]] == "ARMA":
            assert it["dtype"] is not None and it["pot"] > 0 and it["acc"] > 0, it["id"]
    abil = [c for c in items.cols if c["name"] == "ability"][0]["values"]
    for i, name in enumerate(abil):                          # each ability comes from exactly one item
        assert sum(1 for it in items.rows if it["ability"] & (1 << i)) == 1, name
    assert items["MACHETE"]["ability"] == 1 << abil.index("CUT")
    assert items["HONDA"]["ability"] == 1 << abil.index("SLING")
    for k in range(1, 17):
        i = T["shops"]["VARADERO"][f"i{k:02d}"]
        assert i is None or items[i]["precio"] > 0


def test_moves_and_skills_consistency():
    eff = T["moves"].cols[1]["values"]
    for m in T["moves"].rows:
        if eff[m["efecto"]] == "DANO":
            assert m["dtype"] is not None and m["pot"] > 0, m["id"]
        if eff[m["efecto"]] == "ESTADO":
            assert m["st"] is not None and m["stp"] > 0, m["id"]
    lv = {s["id"]: s["nivel"] for s in T["skills"].rows}
    assert lv["CONCENTRAR"] <= RULE["START_LEVEL"] < lv["GOLPE_SUAVE"] <= 3
    assert [s["abbr"] for s in T["statuses"].rows if s["kind"] == 0] == ["DOR", "ATU", "CEG", "VEN", "QUE", "REN"]


def test_slice_reaches_about_level_8():
    """GDD 3.9 + 9 (M1b 'PX hasta ~L8' in 25-45 min): battles at the middle level of the M1b spawns,
    the first capture of each of the 6 species counts x2. From START_LEVEL to L8 must take 20-45
    battles (the bot of GDD 11 measures the real number)."""
    lv = []
    for sp in T["spawns"].rows:
        for k in range(1, 5):
            if sp[f"e{k}"] is not None:
                lv += [(sp[f"e{k}"], (sp[f"e{k}lo"] + sp[f"e{k}hi"]) >> 1)] * sp[f"e{k}w"]
    avg = sum(((T["species"][s]["xp"] * L) >> RULE["XP_SH"]) + RULE["XP_ADD"] for s, L in lv) / len(lv)
    need = sum(row("player", f"L{L:02d}")["xp"] for L in range(RULE["START_LEVEL"], 8))
    first = sum(((s["xp"] * 4) >> RULE["XP_SH"]) + RULE["XP_ADD"] for s in T["species"].rows)  # bonus of x2
    battles = (need - first) / avg
    assert 20 <= battles <= 45, battles
