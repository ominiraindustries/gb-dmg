"""TORRE HUNDIDA M1b: items, doors, keys, combat, death, seen cells, HUD (GDD 2.4-2.11)."""
from test_game import CHEAT_FROZEN, CHEAT_INVINCIBLE, CHEAT_ONE_HIT
from view_model import expected, shown

CELL_FLOOR, CELL_WALL, CELL_DOOR, CELL_LOCKED, CELL_DOOR_OPEN = 0, 1, 2, 3, 4
IT_KEY, IT_POTION, IT_STAFF, IT_AMULET = 1, 2, 3, 4
T_A, T_0 = 24 + 10, 24


def win_text(gb, row):
    out = ""
    for t in gb.bg_map(window=True)[row][:20]:
        if T_A <= t < T_A + 26:
            out += chr(65 + t - T_A)
        elif T_0 <= t < T_0 + 10:
            out += chr(48 + t - T_0)
        else:
            out += " "
    return out.strip()


def place(gb, x, y, f):
    """Teleport the hero (tests only): position, then a turn-in-place to recompose the view."""
    gb.write_u8("px", x)
    gb.write_u8("py", y)
    gb.write_u8("pf", (f + 1) & 3)
    gb.tap("left")
    gb.frames(20)
    assert (gb.u8("px"), gb.u8("py"), gb.u8("pf")) == (x, y, f)


def clear_monsters(gb):
    gb.write_bytes("mon_hp", [0] * 12)
    gb.write_u8("maps_dirty", 1)                            # rebuild the occupancy maps


def put_item(gb, i, t, x, y):
    gb.write_bytes("item_type", [t], i)
    gb.write_bytes("item_x", [x], i)
    gb.write_bytes("item_y", [y], i)
    gb.write_u8("maps_dirty", 1)


def put_monster(gb, m, hp, x, y):
    gb.write_bytes("mon_hp", [hp], m)
    gb.write_bytes("mon_x", [x], m)
    gb.write_bytes("mon_y", [y], m)
    gb.write_bytes("mon_atk_t", [0], m)
    gb.write_u8("maps_dirty", 1)


def test_hud_and_first_message(gb):
    gb.frames(30)
    assert win_text(gb, 5) == "PISO 1"
    row = gb.bg_map(window=True)[0]
    assert row[2:4] == [T_0 + 2, T_0 + 0] and row[5:7] == [T_0 + 2, T_0 + 0]   # 20/20
    assert row[12] == T_0 + 0 and row[15] == T_0 + 1 and row[18] == T_A + ord("S") - 65


def test_pick_up_potion_and_staff(gb):
    gb.write_u8("cheat_flags", CHEAT_FROZEN | CHEAT_INVINCIBLE)
    clear_monsters(gb)
    put_item(gb, 0, IT_STAFF, 5, 3)
    place(gb, 5, 2, 2)
    gb.tap("down")                                          # back off and step onto it
    gb.frames(20)
    gb.tap("up")
    gb.frames(20)
    gb.tap("up")
    gb.frames(30)
    assert gb.u8("weapon") == 1 and gb.u8("staff_owned") == 1
    assert win_text(gb, 5) == "COGES EL BACULO"


def test_door_opens_and_locked_needs_key(gb):
    gb.write_u8("cheat_flags", CHEAT_FROZEN | CHEAT_INVINCIBLE)
    clear_monsters(gb)
    place(gb, 3, 3, 1)                                      # facing the door at (4, 3)
    gb.tap("a")
    gb.frames(30)
    assert gb.bytes("dmap", 256)[3 * 16 + 4] == CELL_DOOR_OPEN
    assert shown(gb) == expected(gb.bytes("dmap", 256), 3, 3, 1)
    place(gb, 12, 10, 2)                                    # LOCKED at (12, 11)
    gb.tap("a")
    gb.frames(30)
    assert gb.bytes("dmap", 256)[11 * 16 + 12] == CELL_LOCKED and win_text(gb, 5) == "ESTA CERRADA"
    gb.write_u8("key_count", 1)
    gb.tap("a")
    gb.frames(30)
    assert gb.bytes("dmap", 256)[11 * 16 + 12] == CELL_DOOR_OPEN and gb.u8("key_count") == 0


def test_kill_guard_drops_key(gb):
    gb.write_u8("cheat_flags", CHEAT_FROZEN | CHEAT_INVINCIBLE | CHEAT_ONE_HIT)
    types = gb.bytes("mon_type", 12)
    items = gb.bytes("mon_item", 12)
    m = items.index(IT_KEY)
    mx, my = gb.u8("mon_x") if False else gb.bytes("mon_x", 12)[m], gb.bytes("mon_y", 12)[m]
    place(gb, mx - 1, my, 1)                                 # west of it, facing east
    kills = gb.u8("kills")
    gb.tap("a")
    gb.frames(40)
    assert gb.bytes("mon_hp", 12)[m] == 0 and gb.u8("kills") == kills + 1
    n = gb.u8("item_count")
    assert gb.bytes("item_type", 24)[n - 1] == IT_KEY and gb.bytes("item_x", 24)[n - 1] == mx
    gb.screenshot("kill")


def test_monster_winds_up_and_hits(gb):
    """A FAST next to the hero: alert, wind-up (12 f), then the roll; dodging by stepping away."""
    gb.write_u8("cheat_flags", 0)
    m = gb.bytes("mon_type", 12).index(0)                   # first FAST
    clear_monsters(gb)
    put_monster(gb, m, 3, 6, 8)
    place(gb, 5, 8, 1)                                      # facing it
    hp = gb.u8("hp")
    seen_windup = False
    for _ in range(200):
        gb.frames(1)
        seen_windup |= bool(gb.bytes("mon_state", 12)[m] & 2)
        if gb.u8("hp") < hp:
            break
    assert seen_windup
    msgs = [win_text(gb, r) for r in range(2, 6)]
    assert gb.u8("hp") < hp or any(t == "ESQUIVAS" for t in msgs)
    gb.screenshot("monster_d1")


def test_death_locks_input(gb):
    gb.write_u8("cheat_flags", 0)
    m = gb.bytes("mon_type", 12).index(0)
    clear_monsters(gb)
    put_monster(gb, m, 3, 6, 8)
    place(gb, 5, 8, 1)
    gb.write_u8("hp", 1)
    for _ in range(1500):
        gb.frames(1)
        if gb.u8("play_sub") == 2:
            break
    assert gb.u8("hp") == 0 and gb.u8("play_sub") == 2


def seen_model(dmap, px, py, pf):
    dx, dy = (0, 1, 0, -1), (-1, 0, 1, 0)
    r = (pf + 1) & 3

    def cell(d, l):
        return px + d * dx[pf] + l * dx[r], py + d * dy[pf] + l * dy[r]

    def walk(x, y):
        return 0 <= x < 16 and 0 <= y < 16 and dmap[y * 16 + x] in (0, 4)

    out = {(px, py), cell(0, -1), cell(0, 1)}
    for d in (1, 2, 3):
        lo = 1 if d == 1 else 2
        for l in range(-lo, lo + 1):
            if abs(l) == 2 and not walk(*cell(d, l // 2)):
                continue
            out.add(cell(d, l))
        if not walk(*cell(d, 0)):
            break
    return {(x, y) for x, y in out if 0 <= x < 16 and 0 <= y < 16}


def test_seen_cells_follow_the_rule(gb):
    gb.write_u8("cheat_flags", CHEAT_FROZEN | CHEAT_INVINCIBLE)
    clear_monsters(gb)
    gb.write_bytes("seen", [0] * 32)
    place(gb, 5, 8, 1)
    bits = gb.bytes("seen", 32)
    got = {(x, y) for y in range(16) for x in range(16) if bits[y * 2 + x // 8] & (0x80 >> (x & 7))}
    want = seen_model(gb.bytes("dmap", 256), 5, 8, 1)     # place() composed only the east view
    assert got == want, (sorted(got - want), sorted(want - got))
