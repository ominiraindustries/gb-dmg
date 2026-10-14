"""GRIFO M1b mechanics (GDD 11): weapons, core hitbox, bomb, death/respawn, items, extra lives,
enemy routes, turrets. Objects are placed straight into the pool records (gbe_pool layout)."""
from stage_model import check_screen

CHEAT_INVINCIBLE, CHEAT_BOMBS, CHEAT_FREEZE, CHEAT_NO_LEVEL = 0x01, 0x02, 0x04, 0x20
P_BULLET, P_ENEMY, P_ITEM, P_SHOT, P_EXPLO, P_TURRET, P_END = 0, 12, 18, 19, 27, 29, 33
OBJ_DART, OBJ_WAVE, OBJ_SWOOP, OBJ_CARRIER_P, OBJ_EXPLO, OBJ_ITEM_P, OBJ_ITEM_B = 1, 2, 4, 6, 20, 30, 31
PS_NORMAL, PS_DYING, PS_RESPAWN = 0, 1, 2


def isolate(gb, cheats=CHEAT_NO_LEVEL):
    """No level objects, empty pools: one mechanic at a time."""
    gb.write_u8("cheat_flags", cheats)
    gb.write_bytes("pool", [0] * (P_END * 16))
    gb.frames(2)


def put(gb, i, t, x, y, vx=0, vy=0, hp=1, tile=0):
    # +9 s, +10 tm, +11 aux (route x0), +12 tile, +13 prop, +14 aux2 (hp), +15 pad
    rec = [t, x, 0, y, 0, vx & 0xFF, (vx >> 8) & 0xFF, vy & 0xFF, (vy >> 8) & 0xFF,
           0, 0, x, tile, 0, hp, 0]
    gb.write_bytes("pool", rec, i * 16)


def rec(gb, i):
    return gb.bytes("pool", P_END * 16)[i * 16:i * 16 + 16]


def live(gb, first, n):
    raw = gb.bytes("pool", P_END * 16)
    return [i for i in range(first, first + n) if raw[i * 16]]


def test_weapon_levels(gb):
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_INVINCIBLE)
    for power, per_burst in ((1, [1]), (2, [1]), (3, [1, 3])):
        gb.write_bytes("pool", [0] * (8 * 16), P_SHOT * 16)
        gb.write_u8("power", power)
        gb.frames(9)                                       # fire cooldown over
        gb.write_bytes("pool", [0] * (8 * 16), P_SHOT * 16)
        gb.pyboy.button_press("a")
        counts = []
        for _ in range(2):                                 # two bursts, 8 f apart
            before = len(live(gb, P_SHOT, 8))
            gb.frames(8)
            counts.append(len(live(gb, P_SHOT, 8)) - before)
        gb.pyboy.button_release("a")
        assert sorted(counts) == sorted(per_burst * (2 // len(per_burst))), (power, counts)


def test_player_core_hitbox(gb):
    """4x4 core at (6,6): an enemy bullet (4x4 box at (2,2)) 4 px away misses, 3 px away kills."""
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_FREEZE)
    px, py = gb.u8("player_x"), gb.u8("player_y")
    # bullet box x: bx+2..bx+6, core: px+6..px+10. Touch when |(bx+2)-(px+6)| < 4
    put(gb, P_BULLET, 1, px + 4 + 4, py + 4)              # 4 px right of touching
    gb.frames(2)
    assert gb.u8("play_sub") == PS_NORMAL
    put(gb, P_BULLET, 1, px + 4 + 3, py + 4)              # 3 px: overlap
    gb.frames(2)
    assert gb.u8("play_sub") == PS_DYING


def test_bomb_clears_bullets_and_hurts(gb):
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_FREEZE)
    for i in range(12):
        put(gb, P_BULLET + i, 1, 20 + i * 10, 40)
    put(gb, P_ENEMY, OBJ_SWOOP, 60, 40, hp=10)
    score0, bombs0 = gb.bytes("score", 3), gb.u8("bombs")
    gb.tap("b")
    gb.frames(2)
    assert live(gb, P_BULLET, 12) == []
    s = gb.bytes("score", 3)
    assert (s[1] << 8 | s[0]) - (score0[1] << 8 | score0[0]) == 0x0120   # BCD +120
    assert rec(gb, P_ENEMY)[14] == 2                       # 10 - 8 HP
    assert gb.u8("bombs") == bombs0 - 1
    assert 80 <= gb.u8("player_inv") <= 90
    gb.tap("b")                                            # second bomb during the roar: nothing
    gb.frames(2)
    assert gb.u8("bombs") == bombs0 - 1


def test_death_respawn(gb):
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_FREEZE)
    gb.write_u8("power", 3)
    gb.write_u8("bombs", 0)
    lives = gb.u8("lives")
    px, py = gb.u8("player_x"), gb.u8("player_y")
    put(gb, P_BULLET, 1, px + 4, py + 4)
    gb.frames(2)
    assert gb.u8("play_sub") == PS_DYING and gb.u8("lives") == lives - 1
    gb.write_u8("cheat_flags", CHEAT_NO_LEVEL)
    gb.frames(40)
    assert gb.u8("play_sub") in (PS_RESPAWN, PS_NORMAL)
    assert gb.u8("power") == 2 and gb.u8("bombs") == 2
    gb.frames(30)
    assert gb.u8("play_sub") == PS_NORMAL and gb.u8("player_y") == 136
    assert gb.u8("player_inv") > 0
    gb.screenshot("respawn")


def test_items(gb):
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_INVINCIBLE)
    px, py = gb.u8("player_x"), gb.u8("player_y")
    p0, b0 = gb.u8("power"), gb.u8("bombs")
    put(gb, P_ITEM, OBJ_ITEM_P, px, py - 4, vy=0x0080)
    gb.frames(4)
    assert gb.u8("power") == p0 + 1 and live(gb, P_ITEM, 1) == []
    put(gb, P_ITEM, OBJ_ITEM_B, px, py - 4, vy=0x0080)
    gb.frames(4)
    assert gb.u8("bombs") == b0 + 1


def test_carrier_drops_item(gb):
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_INVINCIBLE)
    put(gb, P_ENEMY, OBJ_CARRIER_P, 72, 40, vy=0, hp=1)
    gb.write_u8("power", 1)
    gb.pyboy.button_press("a")
    for _ in range(60):
        gb.frames(1)
        if live(gb, P_ITEM, 1):
            break
    gb.pyboy.button_release("a")
    assert rec(gb, P_ITEM)[0] == OBJ_ITEM_P


def test_extra_life_at_20000(gb):
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_INVINCIBLE)
    gb.write_bytes("score", [0x90, 0x99, 0x01])            # 19 990
    lives = gb.u8("lives")
    put(gb, P_ENEMY, OBJ_DART, gb.u8("player_x"), 40, hp=1)
    gb.pyboy.button_press("a")
    gb.frames(40)
    gb.pyboy.button_release("a")
    assert gb.u8("lives") == lives + 1
    gb.write_bytes("score", [0x90, 0x99, 0x01])            # once only
    put(gb, P_ENEMY, OBJ_DART, gb.u8("player_x"), 40, hp=1)
    gb.pyboy.button_press("a")
    gb.frames(40)
    gb.pyboy.button_release("a")
    assert gb.u8("lives") == lives + 1


def test_wave_route(gb):
    """WAVE: x = x0 + sine (amplitude 24, period 128), down at 0.75 px/f."""
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_INVINCIBLE)
    put(gb, P_ENEMY, OBJ_WAVE, 40, 0, vy=0x00C0)
    xs = []
    for _ in range(128):
        gb.frames(1)
        xs.append(rec(gb, P_ENEMY)[1])
    assert max(xs) - 40 in (23, 24) and 40 - min(xs) in (23, 24)
    assert 90 <= rec(gb, P_ENEMY)[3] <= 98                 # 128 f x 0.75 = 96


def test_swoop_stops_and_fires_fan(gb):
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_INVINCIBLE)
    gb.write_u8("player_y", 136)
    put(gb, P_ENEMY, OBJ_SWOOP, 72, 0, vy=0x0180, hp=4)
    for _ in range(40):                                    # dives to y >= 56 (~37 f)
        gb.frames(1)
    y_stop = rec(gb, P_ENEMY)[3]
    gb.frames(10)
    assert rec(gb, P_ENEMY)[3] == y_stop                   # stopped
    for _ in range(30):
        gb.frames(1)
        if len(live(gb, P_BULLET, 12)) == 3:
            break
    assert len(live(gb, P_BULLET, 12)) == 3                # FAN(3)


def test_turret_follows_scroll_and_becomes_crater(gb):
    """Run until the first turret (row 48) is alive: its Y = scroll formula and the BG under it
    is a turret metatile; shooting it down leaves a crater in the ring and in VRAM."""
    gb.write_u8("cheat_flags", CHEAT_INVINCIBLE | 0x08)
    gb.write_u16("cheat_scroll", 0x0400)
    for _ in range(400):
        gb.frames(1)
        if live(gb, P_TURRET, 4):
            break
    gb.write_u8("cheat_flags", CHEAT_INVINCIBLE)
    t = live(gb, P_TURRET, 4)[0]
    for _ in range(60):
        gb.frames(1)
        r = rec(gb, t)
        row, scroll = r[15], gb.u16("scroll_y")
        assert r[3] == (scroll + 144 - row * 16) & 255
    assert check_screen(gb) == []
    col, row = rec(gb, t)[11], rec(gb, t)[15]
    gb.write_u8("player_x", col * 16 + 8 - 4)
    gb.pyboy.button_press("a")
    for _ in range(400):
        gb.frames(1)
        if not rec(gb, t)[0]:
            break
    gb.pyboy.button_release("a")
    assert rec(gb, t)[0] == 0, "turret not destroyed"
    gb.frames(2)
    assert check_screen(gb) == []
    gb.screenshot("crater")
