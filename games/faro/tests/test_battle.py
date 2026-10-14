"""Battle core in the ROM == battle_model.py: random battles with random actions, every turn compared
(creature and Leo numbers, statuses, events, inventory, RNG state). GDD 11 "Combate == modelo"."""
import random

import pytest
from battle_model import (ACT_ATTACK, ACT_CAPTURE, ACT_FLEE, ACT_GADGET, ACT_ITEM, ACT_SKILL, B_ONGOING,
                          NONE, T, Battle, Player, Rng)

ITEMS = T["items"]
WEAPONS = [i for i, r in enumerate(ITEMS.rows) if ITEMS.cols[[c["name"] for c in ITEMS.cols].index("cat")]["values"][r["cat"]] == "ARMA"][:3]
LANTERNS = [ITEMS.ids[k] for k in ("FAROLILLO", "FAROLILLO_FINO", "FAROL_PLATA")]
GADGETS = [ITEMS.ids[k] for k in ("RED", "CEBO_DULCE", "CEBO_CARNE", "CEBO_PESCADO", "BENGALA", "DARDO", "HONDA", "FAROL_MANO")]
USABLE = [ITEMS.ids[k] for k in ("POCION", "PAN", "ANTIDOTO", "TONICO")]
SKILLS = [i for i, s in enumerate(T["skills"].rows) if s["campo"] == 0 or True][:12]


def cmd(gb, c, a=0, b=0, d=0):
    gb.write_u8("bt_a", a)
    gb.write_u8("bt_b", b)
    gb.write_u8("bt_c", d)
    gb.write_u8("bt_cmd", c)
    for _ in range(10):                                   # the snapshot is taken in vsync, before the hook;
        gb.frames(1)                                      # a long turn may also take more than a frame
        if gb.u8("bt_cmd") == 0:
            break
    gb.frames(1)
    assert gb.u8("bt_cmd") == 0


def sync_player(gb, p):
    gb.write_u8("plevel", p.level)
    gb.write_u8("armor", p.armor)
    cmd(gb, 5)
    for k in ("pv", "en", "sac", "buff", "p_st", "p_st_t"):
        gb.write_u8(k, {"p_st": p.st, "p_st_t": p.st_t}.get(k, getattr(p, k, None)))
    gb.write_u16("xp", p.xp)
    gb.write_bytes("inv", p.inv)
    for name, sset in (("reg_seen", p.reg_seen), ("reg_caught", p.reg_caught)):
        gb.write_bytes(name, [sum(1 << (b & 7) for b in sset if b >> 3 == k) for k in range(6)])


def rom_state(gb):
    n = gb.u8("b_ev_n")
    ev = gb.bytes("b_ev", 4 * n)
    return {
        "cpv": gb.u8("b_cpv"), "cst": gb.u8("b_cst"), "cst_t": gb.u8("b_cst_t"), "ent": gb.u8("b_ent_t"),
        "calm": gb.u8("b_calm_t"), "lit": gb.u8("b_lit_t"), "down": gb.u8("b_down"), "res": gb.u8("b_result"),
        "pv": gb.u8("pv"), "en": gb.u8("en"), "pst": gb.u8("p_st"), "lvl": gb.u8("plevel"), "xp": gb.u16("xp"),
        "rng": gb.u16("rng_state"), "ev": [tuple(ev[i:i + 4]) for i in range(0, len(ev), 4)],
        "inv": list(gb.bytes("inv", 128)),
    }


def model_state(b, rng):
    p = b.p
    return {
        "cpv": b.cpv, "cst": b.cst, "cst_t": b.cst_t, "ent": b.ent_t, "calm": b.calm_t, "lit": b.lit_t,
        "down": b.down, "res": b.result, "pv": p.pv, "en": p.en, "pst": p.st, "lvl": p.level, "xp": p.xp,
        "rng": rng.state, "ev": b.ev, "inv": p.inv,
    }


def pick_action(rnd, p):
    k = rnd.random()
    if k < 0.45:
        return ACT_ATTACK, rnd.choice(WEAPONS), NONE
    if k < 0.60:
        return ACT_SKILL, rnd.choice(SKILLS), rnd.choice(WEAPONS)
    if k < 0.70:
        return ACT_ITEM, rnd.choice(USABLE), NONE
    if k < 0.82:
        return ACT_GADGET, rnd.choice(GADGETS), NONE
    if k < 0.95:
        return ACT_CAPTURE, rnd.choice(LANTERNS), NONE
    return ACT_FLEE, 0, NONE


@pytest.mark.parametrize("seed", range(12))
def test_rom_battles_equal_model(gb, seed):
    rnd = random.Random(seed)
    cmd(gb, 4)                                            # player_new
    turns = 0
    for battle in range(10):
        p = Player(level=rnd.randint(2, 14))
        for i in WEAPONS + LANTERNS + GADGETS + USABLE:
            p.inv[i] = rnd.randint(1, 5)
        p.sac = rnd.choice([80, 80, 20, 0])
        sync_player(gb, p)
        p.stats()
        species = rnd.randrange(len(T["species"].rows))
        level = rnd.randint(1, 12)
        free = rnd.choice([0, 0, 1, 2])
        state = rnd.randint(1, 0xFFFF)
        gb.write_u16("rng_state", state)
        rng = Rng(state)
        b = Battle(p, rng, species, level, free)
        cmd(gb, 1, species, level, free)
        b.open_turn()
        cmd(gb, 3)
        assert rom_state(gb) == model_state(b, rng), (seed, battle, "open")
        for t in range(30):
            if b.result != B_ONGOING:
                break
            kind, iid, weapon = pick_action(rnd, p)
            b.do_turn(kind, iid, weapon)
            cmd(gb, 2, kind, iid, weapon)
            r, m = rom_state(gb), model_state(b, rng)
            assert r == m, (seed, battle, t, (kind, iid, weapon), {k: (r[k], m[k]) for k in r if r[k] != m[k]})
            turns += 1
    assert turns >= 15
