"""QA pass on M1 (qa-tester): GDD §11 rows not covered elsewhere, edge cases, a bot that plays 1-1
to the goal, the 5-enemy frame budget, and regression tests for the bugs found in review."""
import io
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from helpers import (CLEAR, DYING, GAMEOVER, GOAL, INTRO, PAUSE, PLAY, TITLE, Y_BIAS,
                     expected_tile_column, level_cols, level_map, mt_tiles, s16, start_play,
                     teleport, vram_tile_column, wait_state)
from test_enemies import clear_enemies, place_enemy

T_NONE, T_WALKER, T_SHELL, T_ITEM_GROW, T_ITEM_SHOT, T_ITEM_1UP, T_SHOT, T_PUF = range(8)
E_WALK, E_SQUASH, E_FLIP, E_BALL, E_BALL_MOVE = range(5)
FORM_SMALL, FORM_BIG, FORM_SHOT = 0, 1, 2
MT_SKY, MT_Q_COIN, MT_USED = 0, 3, 6
A_ITEM, A_SHOT0 = 5, 6
GROUND_TOP = Y_BIAS + 7 * 16
SMALL_ON_GROUND = GROUND_TOP - 16
BIG_ON_GROUND = SMALL_ON_GROUND - 16
SOLID_MT = {1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 31, 32}    # ATTR_SOLID metatiles (metatiles.c)
WIN = 0x9C00


# ---------------------------------------------------------------- helpers

def score(gb):
    return int("".join(f"{b:02X}" for b in reversed(gb.bytes("score", 3))))


def bcd(gb, name):
    return int("".join(f"{b:02X}" for b in reversed(gb.bytes(name, 3))))


def cell(gb, col, row):
    return gb.bytes("level", 200 * 8)[col * 8 + row]


def actors(gb):
    t = gb.bytes("act_type", 14)
    st = gb.bytes("act_state", 14)
    raw = gb.bytes("act_x", 28)
    x = [raw[2 * i] | (raw[2 * i + 1] << 8) for i in range(14)]
    vraw = gb.bytes("act_vx", 28)
    vx = [s16(vraw[2 * i] | (vraw[2 * i + 1] << 8)) for i in range(14)]
    return t, st, x, gb.bytes("act_y", 14), vx


def set_form(gb, form):
    gb.write_u8("player_form", form)
    gb.write_u8("hb_y", 2 if form == FORM_SMALL else 4)
    gb.write_u8("hb_h", 14 if form == FORM_SMALL else 28)


def fly_to(gb, x_target, step=8):
    """Fly the camera to x_target with streaming (teleports in steps <= 8 px/f)."""
    x = gb.u16("player_x")
    while x < x_target:
        x = min(x + step, x_target)
        teleport(gb, x)
        gb.frames(1)


def setup(gb, x=8 * 16, cheat=2):
    start_play(gb)
    gb.write_u8("cheat_flags", cheat)
    clear_enemies(gb)
    if x > 200:
        fly_to(gb, x)
    teleport(gb, x, SMALL_ON_GROUND)
    gb.frames(20)


def poke(gb, name, offset, value):
    """Write a byte of a global (through the driver, so the WRAM snapshot stays coherent)."""
    gb._write(gb.addr(name) + offset, value)


def touch_pole(gb, row, frames=60):
    """Teleport Teo touching the pole (hitbox right edge on its 4 px) with the feet in level row
    `row`. Writes land mid-update (PyBoy ticks end at LY 0), so do not rely on writing vx."""
    fly_to(gb, 185 * 16)
    teleport(gb, 189 * 16 - 6, Y_BIAS + 16 * row)
    gb.pyboy.button_press("right")
    ok = wait_state(gb, GOAL, frames)
    gb.pyboy.button_release("right")
    return ok


def win_row(gb, row):
    return [gb.pyboy.memory[WIN + 32 * row + c] for c in range(20)]


def save(gb):
    buf = io.BytesIO()
    gb.pyboy.save_state(buf)
    return buf


def load(gb, buf):
    buf.seek(0)
    gb.pyboy.load_state(buf)          # WRAM snapshot is stale until the next frames() call


def release_all(gb):
    for b in ("a", "b", "left", "right", "up", "down", "start", "select"):
        gb.pyboy.button_release(b)


def sprites_per_line_max(gb):
    """Visible 8x16 sprites per scanline from the real OAM (lines 16-143: below the HUD)."""
    m = gb.pyboy.memory
    counts = [0] * 144
    for s in range(40):
        y = m[0xFE00 + 4 * s]
        if 0 < y < 160:
            for ly in range(max(0, y - 16), min(144, y)):
                counts[ly] += 1
    return max(counts[16:])


# ---------------------------------------------------------------- physics (GDD §2.2, §2.6)

def test_qa_jump_from_top_row_is_not_a_pit_death(gb):
    """BUG: Teo standing on the high brick row (c80-87, row 1) and jumping goes above y = 0;
    player_y wraps to ~224-239 and the pit check kills him. BIG Teo dies on any held jump."""
    for form, run in ((FORM_SMALL, True), (FORM_BIG, False)):
        setup(gb, x=76 * 16)
        if form != FORM_SMALL:
            set_form(gb, form)
        teleport(gb, 80 * 16, 10)              # lands on the bricks of row 1
        gb.frames(30)
        assert gb.u8("player_on_ground") == 1
        gb.pyboy.button_press("right")
        if run:
            gb.pyboy.button_press("b")
        gb.frames(20)
        gb.pyboy.button_press("a")
        died = False
        for _ in range(70):
            gb.frames(1)
            if gb.u8("state") != PLAY:
                died = True
                break
        release_all(gb)
        assert not died, f"form {form}: jumping from row 1 counted as falling in a pit"


def test_qa_running_jump_clears_four_high_turret(gb):
    """BUG: max running jump is 62 px (sum of -0x400 + 0x20/f), the GDD says ~64; the 4-high
    turrets of 1-1 (c46, c57) need 63. Brute force every take-off frame: none gets over c46."""
    setup(gb, x=40 * 16, cheat=3)
    gb.write_u8("obj_next", 255)
    state = save(gb)
    best = 0
    for jump_at in range(0, 40):
        load(gb, state)
        gb.pyboy.button_press("right")
        gb.pyboy.button_press("b")
        for f in range(110):
            if f == jump_at:
                gb.pyboy.button_press("a")
            if f == jump_at + 35:
                gb.pyboy.button_release("a")
            gb.frames(1)
        best = max(best, gb.u16("player_x"))
        release_all(gb)
    assert best >= 48 * 16, f"Teo never gets past the 4-high turret at c46 (best x {best})"


def test_qa_jump_buffer(gb):
    """A pressed <= 5 f before landing jumps on touchdown; pressed earlier does not (GDD §2.2)."""
    setup(gb)
    teleport(gb, 8 * 16, SMALL_ON_GROUND - 40)
    gb.frames(1)
    state = save(gb)
    n = 0
    while not gb.u8("player_on_ground"):
        gb.frames(1)
        n += 1
    assert n > 10
    results = {}
    for early in (3, 9):
        load(gb, state)
        gb.frames(n - early - 1)              # -1: input latency
        gb.pyboy.button_press("a")
        jumped = False
        for _ in range(early + 6):
            gb.frames(1)
            if s16(gb.u16("player_vy")) < -0x0200:
                jumped = True
        gb.pyboy.button_release("a")
        results[early] = jumped
    assert results[3], "A 3 frames before landing should be buffered"
    assert not results[9], "A 9 frames before landing must not jump"


def test_qa_head_corner_correction_3px_vs_6px(gb):
    """3 px of overlap with the block edge: pushed aside, block untouched; 6 px: head bump and
    the block is hit. (The existing corner test places Teo fully right of the block.)"""
    for overlap, expect_hit in ((3, False), (6, True)):
        setup(gb, x=8 * 16)
        teleport(gb, 16 * 16 + 16 - overlap - 3, SMALL_ON_GROUND)   # hitbox overlaps c16 by `overlap`
        gb.frames(5)
        assert cell(gb, 16, 4) == MT_Q_COIN
        gb.pyboy.button_press("a")
        gb.frames(40)
        gb.pyboy.button_release("a")
        gb.frames(30)
        hit = cell(gb, 16, 4) == MT_USED
        assert hit == expect_hit, f"overlap {overlap}: block hit {hit}"


def test_qa_crouch_slides_and_cannot_accelerate(gb):
    setup(gb)
    set_form(gb, FORM_BIG)
    teleport(gb, 8 * 16, BIG_ON_GROUND)
    gb.frames(5)
    gb.pyboy.button_press("right")
    gb.frames(20)
    v0 = s16(gb.u16("player_vx"))
    gb.pyboy.button_press("down")
    gb.frames(3)
    assert gb.u8("player_crouch") == 1
    assert s16(gb.u16("player_vx")) < v0
    gb.frames(15)
    assert gb.u16("player_vx") == 0            # 0x140 / 0x20 = 10 f, right still held
    release_all(gb)


# ---------------------------------------------------------------- items and forms (GDD §2.3, §2.9)

def put_item(gb, kind, x, y):
    a, m = gb.addr, gb.pyboy.memory
    m[a("act_type") + A_ITEM] = kind
    m[a("act_state") + A_ITEM] = 1
    m[a("act_x") + 2 * A_ITEM] = x & 0xFF
    m[a("act_x") + 2 * A_ITEM + 1] = x >> 8
    m[a("act_y") + A_ITEM] = y
    for v in ("act_vx", "act_vy"):
        m[a(v) + 2 * A_ITEM] = 0
        m[a(v) + 2 * A_ITEM + 1] = 0


def test_qa_1up_item_gives_a_life(gb):
    setup(gb)
    lives = gb.u8("lives")
    put_item(gb, T_ITEM_1UP, 8 * 16, SMALL_ON_GROUND)
    gb.frames(3)
    assert gb.u8("lives") == lives + 1
    assert gb.u8("player_form") == FORM_SMALL


def test_qa_grow_item_when_big_only_scores(gb):
    setup(gb)
    set_form(gb, FORM_BIG)
    teleport(gb, 8 * 16, BIG_ON_GROUND)
    gb.frames(5)
    s0 = score(gb)
    put_item(gb, T_ITEM_GROW, 8 * 16, SMALL_ON_GROUND)
    gb.frames(3)
    assert score(gb) - s0 == 1000
    assert gb.u8("player_form") == FORM_BIG
    assert gb.u8("player_freeze") == 0


def test_qa_shot_item_when_small_gives_big(gb):
    setup(gb)
    put_item(gb, T_ITEM_SHOT, 8 * 16, SMALL_ON_GROUND)
    gb.frames(3)
    assert gb.u8("player_form") == FORM_BIG


def test_qa_shrink_then_90f_invulnerability(gb):
    setup(gb)
    set_form(gb, FORM_BIG)
    teleport(gb, 8 * 16, BIG_ON_GROUND)
    gb.frames(5)
    place_enemy(gb, 0, T_WALKER, 8 * 16 + 8, vx=0)
    gb.frames(3)
    assert gb.u8("player_form") == FORM_SMALL
    clear_enemies(gb)
    freeze = gb.u8("player_freeze")
    assert 44 <= freeze <= 48
    gb.frames(freeze)
    inv = gb.u8("player_inv")
    assert 86 <= inv <= 90, inv
    gb.frames(inv + 2)
    assert gb.u8("player_inv") == 0


def test_qa_shot_cooldown_and_wall_puf(gb):
    setup(gb, x=35 * 16)
    set_form(gb, FORM_SHOT)
    teleport(gb, 35 * 16, BIG_ON_GROUND)
    gb.frames(5)
    gb.tap("b")
    gb.tap("b")                                # second press 3 f later: inside the 8 f cooldown
    t = gb.bytes("act_type", 14)[A_SHOT0:A_SHOT0 + 2]
    assert t.count(T_SHOT) == 1, t
    puf = False
    for _ in range(30):
        gb.frames(1)
        if T_PUF in gb.bytes("act_type", 14)[A_SHOT0:A_SHOT0 + 2]:   # turret c38
            puf = True
            break
    assert puf


# ---------------------------------------------------------------- enemies (GDD §2.8, §2.10)

def test_qa_stomp_chain_full_table_then_1up(gb):
    setup(gb)
    teleport(gb, 8 * 16, 80)                   # in the air, never touches the ground
    s0, lives = score(gb), gb.u8("lives")
    gains = []
    for k in range(11):
        for _ in range(60):                    # back down to y 80 after each bounce
            gb.frames(1)
            if s16(gb.u16("player_vy")) > 0 and gb.u8("player_y") >= 80:
                break
        before = score(gb)
        place_enemy(gb, k % 5, T_WALKER, gb.u16("player_x"), y=gb.u8("player_y") + 10, vx=0)
        gb.frames(2)
        assert actors(gb)[1][k % 5] == E_SQUASH, f"stomp {k} missed"
        gains.append(score(gb) - before)
        assert gb.u8("player_on_ground") == 0
    assert gains[:10] == [100, 200, 400, 500, 800, 1000, 2000, 4000, 5000, 8000], gains
    assert gains[10] == 0 and gb.u8("lives") == lives + 1
    assert score(gb) - s0 == 22000


def test_qa_ball_chain_scores_500_800_1000(gb):
    """BUG: the kicked ball's kill chain uses the stomp table (100, 200, 400) instead of
    GDD §2.10 (500, 800, 1000, 2000, 4000, 5000, 8000, then 1UP)."""
    setup(gb, cheat=3)
    gb.write_u8("obj_next", 255)
    # on screen (camera 64): enemies only exist up to camera + 200 (8-bit relative x)
    place_enemy(gb, 0, T_SHELL, 9 * 16, state=E_BALL_MOVE, vx=0x300)
    for k, c in enumerate((11, 13, 15)):
        place_enemy(gb, k + 1, T_WALKER, c * 16, vx=0)
    s0 = score(gb)
    for _ in range(60):
        gb.frames(1)
        if all(s == E_FLIP for s in actors(gb)[1][1:4]):
            break
    assert all(s == E_FLIP for s in actors(gb)[1][1:4]), "ball should kill all three"
    assert score(gb) - s0 == 500 + 800 + 1000


def test_qa_kick_score_and_direction_by_centres(gb):
    setup(gb)
    place_enemy(gb, 0, T_SHELL, 8 * 16 - 10, state=E_BALL, vx=0)   # ball left of Teo
    gb.write_u16("enemy_wait", 300)
    s0 = score(gb)
    gb.frames(3)
    t, st, x, y, vx = actors(gb)
    assert st[0] == E_BALL_MOVE and vx[0] < 0, "kicked away from Teo (to the left)"
    assert score(gb) - s0 == 400


def test_qa_kick_grace_then_ball_hurts(gb):
    for grace, hurt in ((8, False), (0, True)):
        setup(gb)
        set_form(gb, FORM_BIG)
        teleport(gb, 8 * 16, BIG_ON_GROUND)
        gb.frames(5)
        place_enemy(gb, 0, T_SHELL, 8 * 16 + 6, state=E_BALL_MOVE, vx=-0x300)
        poke(gb, "enemy_grace", 0, grace)
        gb.frames(3)
        assert (gb.u8("player_form") == FORM_SMALL) == hurt, f"grace {grace}"


def test_qa_ball_rebounds_off_wall(gb):
    setup(gb, cheat=3)
    gb.write_u8("obj_next", 255)
    teleport(gb, 20 * 16, SMALL_ON_GROUND)       # camera near the c28 turret
    gb.frames(30)
    place_enemy(gb, 0, T_SHELL, 24 * 16, state=E_BALL_MOVE, vx=0x300)
    gb.frames(1)
    poke(gb, "enemy_grace", 0, 0)
    for _ in range(30):
        gb.frames(1)
        if actors(gb)[4][0] < 0:
            break
    assert actors(gb)[4][0] == -0x300, "ball should bounce back off the c28 turret"


def test_qa_ball_wakes_up_towards_player(gb):
    setup(gb, cheat=3)
    gb.write_u8("obj_next", 255)
    place_enemy(gb, 0, T_SHELL, 13 * 16, state=E_BALL, vx=0)
    gb.write_u16("enemy_wait", 70)              # 60 f of trembling left, then walks
    gb.frames(30)
    assert actors(gb)[1][0] == E_BALL
    gb.screenshot("qa_ball_peek")
    gb.frames(50)
    t, st, x, y, vx = actors(gb)
    assert st[0] == E_WALK and vx[0] < 0, "wakes up walking towards Teo (left)"


def test_qa_stomp_moving_ball_stops_it(gb):
    setup(gb, cheat=3)
    gb.write_u8("obj_next", 255)
    teleport(gb, 12 * 16, SMALL_ON_GROUND - 30)
    gb.write_u16("player_vy", 0x0200)
    place_enemy(gb, 0, T_SHELL, 12 * 16 + 2, state=E_BALL_MOVE, vx=0x0010)
    for _ in range(10):
        gb.frames(1)
        if actors(gb)[1][0] == E_BALL:
            break
    assert actors(gb)[1][0] == E_BALL and actors(gb)[4][0] == 0
    gb.frames(10)
    assert actors(gb)[1][0] == E_BALL, "Teo bounced off: the stopped ball must not be re-kicked"


def test_qa_two_walkers_turn_around(gb):
    setup(gb, cheat=3)
    gb.write_u8("obj_next", 255)
    place_enemy(gb, 0, T_WALKER, 12 * 16, vx=0x80)
    place_enemy(gb, 1, T_WALKER, 12 * 16 + 20, vx=-0x80)
    gb.frames(30)
    vx = actors(gb)[4]
    assert vx[0] < 0 and vx[1] > 0, vx[:2]


def test_qa_stomp_while_invulnerable(gb):
    setup(gb)
    gb.write_u8("player_inv", 80)
    place_enemy(gb, 0, T_WALKER, 8 * 16 + 2, vx=0)
    teleport(gb, 8 * 16, SMALL_ON_GROUND - 30)
    gb.write_u16("player_vy", 0x0200)
    gb.frames(8)
    assert actors(gb)[1][0] == E_SQUASH
    assert s16(gb.u16("player_vy")) < 0 or gb.u8("player_y") < SMALL_ON_GROUND - 4   # bounced


def test_qa_max_five_enemies_spawn_waits(gb):
    setup(gb, cheat=3)
    teleport(gb, 15 * 16 + 8, SMALL_ON_GROUND)  # camera 184: c22 (352) < camera + 176
    gb.frames(2)                                # camera first: enemies only live near it
    for s in range(5):
        place_enemy(gb, s, T_WALKER, 21 * 16 + 4 * s, vx=0)
    gb.write_u8("obj_next", 1)                 # the Limo of c22 is next (index 0 = start 'x')
    gb.frames(10)
    assert gb.u8("obj_next") == 1, "no free slot: the list must wait"
    poke(gb, "act_type", 4, T_NONE)
    gb.frames(3)
    assert gb.u8("obj_next") == 2
    assert abs(actors(gb)[2][4] - 22 * 16) <= 4


# ---------------------------------------------------------------- freezes, deaths, timer

def test_qa_hit_during_grow_animation_then_shrinks_not_dies(gb):
    """Touch the Yelmo with a Limo on top of Teo: no damage during the 48 f freeze, then the hit
    shrinks him (BIG -> SMALL) instead of killing him."""
    setup(gb)
    put_item(gb, T_ITEM_GROW, 8 * 16, SMALL_ON_GROUND)
    gb.frames(2)
    assert gb.u8("player_freeze") > 0
    place_enemy(gb, 0, T_WALKER, 8 * 16 + 10, vx=0)   # touching big Teo during the animation
    seen_big = False
    for _ in range(140):
        gb.frames(1)
        assert gb.u8("state") == PLAY, "died during/after the grow animation"
        seen_big |= gb.u8("player_form") == FORM_BIG
    assert seen_big
    assert gb.u8("player_form") == FORM_SMALL and gb.u8("player_inv") > 0


def test_qa_freeze_stops_enemies_and_timer(gb):
    setup(gb)
    gb.write_u8("cheat_flags", 0)
    place_enemy(gb, 0, T_WALKER, 14 * 16, vx=-0x80)
    gb.write_u16("time_units", 1)
    gb.write_u8("time_tick", 20)
    gb.write_u8("player_freeze", 30)
    gb.write_u8("player_freeze_kind", 1)
    x0 = 14 * 16
    gb.frames(20)
    assert gb.u8("state") == PLAY and gb.u16("time_units") == 1
    assert actors(gb)[2][0] == x0
    gb.frames(30)
    assert gb.u8("state") == DYING, "the timer resumes after the freeze"


def test_qa_dying_while_big_from_time_out_shows_death(gb):
    setup(gb)
    set_form(gb, FORM_BIG)
    teleport(gb, 8 * 16, BIG_ON_GROUND)
    gb.write_u8("cheat_flags", 0)
    gb.write_u16("time_units", 1)
    gb.frames(30)
    assert gb.u8("state") == DYING
    gb.frames(40)
    gb.screenshot("qa_death_big")


# ---------------------------------------------------------------- HUD (ui.md §2, §5, §13)

def digit0(gb):
    return gb.bytes("hud_buf", 40)[20 + 1] - (gb.bytes("score", 3)[2] >> 4)


def test_qa_hud_vram_matches_values(gb):
    setup(gb)
    gb.write_u8("coins", 41)
    teleport(gb, 34 * 16, Y_BIAS + 2 * 16)       # coin '$' c34 -> 42 coins, +200
    gb.frames(30)
    d0 = digit0(gb)
    r0, r1 = win_row(gb, 0), win_row(gb, 1)
    sc = f"{score(gb):06d}"
    assert r1[1:7] == [d0 + int(c) for c in sc]
    assert r0[12:14] == [d0 + 4, d0 + 2]
    lv = gb.u8("lives")
    assert r1[12:14] == [d0 + lv // 10, d0 + lv % 10]
    t = gb.u16("time_units")
    assert r1[16:19] in ([d0 + int(c) for c in f"{t:03d}"], [d0 + int(c) for c in f"{t + 1:03d}"])
    assert r0[16:19] == [d0 + 1, r0[17], d0 + 1] and r0[17] != r0[0]   # "1-1"


def test_qa_hourglass_blinks_when_time_low(gb):
    """MISSING: ui.md §2 / GDD §12.15 - with time <= 100 ICON_TIME alternates with BLANK every
    16 f. HUD_TIMEICON is defined in hud.c but never used."""
    setup(gb)
    icon = win_row(gb, 1)[15]
    gb.write_u16("time_units", 100)
    seen = set()
    for _ in range(40):
        gb.frames(1)
        seen.add(gb.pyboy.memory[WIN + 32 + 15])
    assert icon in seen and len(seen) == 2, f"hourglass tile values seen: {seen}"


def test_qa_pause_blinks_and_restores_hud_row(gb):
    setup(gb)
    row0 = win_row(gb, 0)
    gb.tap("start")
    assert gb.u8("state") == PAUSE
    paused = win_row(gb, 0)
    assert paused != row0 and paused[7:12] != [paused[0]] * 5      # "PAUSA" at cols 7-11
    assert paused[:7] == [paused[0]] * 7 and paused[12:] == [paused[0]] * 8
    hidden = False
    for _ in range(40):
        gb.frames(1)
        if win_row(gb, 0)[7:12] == [paused[0]] * 5:
            hidden = True
    assert hidden, "PAUSA should blink"
    t = gb.u16("time_units")
    gb.frames(60)
    assert gb.u16("time_units") == t
    gb.tap("start")
    assert gb.u8("state") == PLAY
    assert win_row(gb, 0) == row0, "row 0 restored after the pause"


# ---------------------------------------------------------------- flow and transitions

def test_qa_start_ignored_outside_play(gb):
    # TITLE fade-in after boot is skipped by the 180 boot frames; INTRO:
    wait_state(gb, TITLE)
    gb.frames(20)
    gb.tap("start")
    assert wait_state(gb, INTRO, 100)
    for _ in range(30):                         # 90 f, the intro lasts 136
        gb.tap("start")
        assert gb.u8("state") == INTRO
    assert wait_state(gb, PLAY, 300)
    # DYING
    clear_enemies(gb)
    teleport(gb, 2 * 16, Y_BIAS + 9 * 16)
    gb.frames(3)
    assert gb.u8("state") == DYING
    for _ in range(10):
        gb.tap("start")
        assert gb.u8("state") != PAUSE
    assert wait_state(gb, PLAY, 400)
    # GOAL
    gb.write_u8("cheat_flags", 2)
    gb.write_u8("obj_next", 255)
    assert touch_pole(gb, 3)
    for _ in range(20):
        gb.tap("start")
        assert gb.u8("state") == GOAL


def test_qa_clear_ignores_start_before_30_frames(gb):
    start_play(gb)
    gb.write_u8("obj_next", 255)
    gb.write_u16("time_units", 2)
    assert touch_pole(gb, 5)
    assert wait_state(gb, CLEAR, 900)
    gb.frames(18)                               # 16 f fade-in, then the first CLEAR frames
    gb.tap("start")
    gb.frames(20)
    assert gb.u8("state") == CLEAR, "Start before f30 must not skip CLEAR"


def test_qa_title_ignores_start_during_fade_in(gb):
    start_play(gb)
    clear_enemies(gb)
    gb.write_u8("lives", 1)
    teleport(gb, 2 * 16, Y_BIAS + 9 * 16)
    assert wait_state(gb, GAMEOVER, 300)
    gb.frames(60)                               # 16 f fade-in + 30 f before Start counts
    gb.tap("start")
    assert wait_state(gb, TITLE, 100)
    gb.tap("start")                             # first 3 frames of the title fade-in
    gb.frames(60)
    assert gb.u8("state") == TITLE and gb.u8("title_pressed") == 0


def test_qa_time_does_not_kill_during_goal(gb):
    start_play(gb)
    gb.write_u8("obj_next", 255)
    fly_to(gb, 185 * 16)
    gb.write_u16("time_units", 1)
    gb.write_u8("time_tick", 8)
    assert touch_pole(gb, 2)
    s0 = score(gb)
    for _ in range(400):
        gb.frames(1)
        assert gb.u8("state") in (GOAL, CLEAR)
        if gb.u8("state") == CLEAR:
            break
    assert gb.u8("state") == CLEAR
    assert score(gb) - s0 in (0, 50)


@pytest.mark.parametrize("row,points", [(0, 5000), (2, 2000), (3, 800), (4, 400), (5, 100)])
def test_qa_goal_points_by_height(gb, row, points):
    start_play(gb)
    gb.write_u8("cheat_flags", 2)
    gb.write_u8("obj_next", 255)
    s0 = score(gb)
    assert touch_pole(gb, row, 30)
    assert score(gb) - s0 == points


def test_qa_goal_walk_to_castle_on_the_ground(gb):
    """BUG: after sliding down to the base block (top y 128), Teo walks to the door at the same
    height; from c190 on the ground is at y 144, so he floats 16 px above it."""
    start_play(gb)
    gb.write_u8("cheat_flags", 2)
    gb.write_u8("obj_next", 255)
    assert touch_pole(gb, 3)
    for _ in range(200):
        gb.frames(1)
        if gb.u16("player_x") >= 191 * 16:
            break
    gb.screenshot("qa_goal_walk")
    gb.screenshot("qa_goal_walk")               # 2nd render: PyBoy's first one shifts the window
    feet = gb.u8("player_y") + gb.u8("hb_y") + gb.u8("hb_h")
    assert feet == GROUND_TOP, f"Teo's feet at y {feet}, ground at {GROUND_TOP}"


def test_qa_game_over_then_new_game_resets_everything(gb):
    start_play(gb)
    clear_enemies(gb)
    gb.write_u8("checkpoint", 1)
    gb.write_u8("coins", 42)
    poke(gb, "score", 0, 0x00)
    poke(gb, "score", 1, 0x34)
    poke(gb, "score", 2, 0x12)
    poke(gb, "level", 16 * 8 + 4, MT_USED)
    gb.write_u8("lives", 1)
    teleport(gb, 2 * 16, Y_BIAS + 9 * 16)
    assert wait_state(gb, GAMEOVER, 300)
    assert bcd(gb, "record") == 123400, "record updated on GAME OVER (GDD §12.13)"
    gb.frames(60)
    gb.tap("start")
    assert wait_state(gb, TITLE, 100)
    gb.frames(30)
    gb.tap("start")
    assert wait_state(gb, PLAY, 400)
    assert gb.u8("lives") == 3 and gb.u8("coins") == 0 and score(gb) == 0
    assert gb.u8("checkpoint") == 0
    assert gb.u16("player_x") == 2 * 16
    assert cell(gb, 16, 4) == MT_Q_COIN
    assert gb.u16("time_units") == 300
    assert bcd(gb, "record") == 123400


def test_qa_checkpoint_respawn_reloads_map_keeps_score(gb):
    start_play(gb)
    gb.write_u8("cheat_flags", 3)
    clear_enemies(gb)
    fly_to(gb, 101 * 16)
    teleport(gb, 101 * 16, SMALL_ON_GROUND)
    gb.frames(10)
    assert gb.u8("checkpoint") == 1
    gb.write_u8("cheat_flags", 2)
    set_form(gb, FORM_BIG)
    gb.write_u8("coins", 7)
    poke(gb, "score", 1, 0x77)
    poke(gb, "level", 106 * 8 + 4, MT_USED)
    s, lives = score(gb), gb.u8("lives")
    clear_enemies(gb)
    teleport(gb, 104 * 16, Y_BIAS + 9 * 16)
    assert wait_state(gb, DYING, 30)
    assert wait_state(gb, PLAY, 400)
    assert gb.u16("player_x") == 100 * 16 and gb.u8("player_form") == FORM_SMALL
    assert gb.u8("coins") == 7 and score(gb) == s and gb.u8("lives") == lives - 1
    assert cell(gb, 106, 4) == MT_Q_COIN, "map reloaded from ROM"
    assert gb.u16("time_units") == 300
    gb.frames(30)
    assert vram_matches_map(gb)


def test_qa_intro_shows_two_digit_lives(gb):
    start_play(gb)
    clear_enemies(gb)
    gb.write_u8("lives", 12)
    teleport(gb, 2 * 16, Y_BIAS + 9 * 16)
    assert wait_state(gb, INTRO, 200)
    gb.frames(40)
    d0 = digit0(gb)
    assert [gb.pyboy.memory[WIN + 11 * 32 + c] for c in (11, 12)] == [d0 + 1, d0 + 1]
    gb.screenshot("qa_intro")
    gb.screenshot("qa_intro")


def test_qa_caps_score_lives_coins(gb):
    setup(gb)
    for i, v in enumerate((0x90, 0x99, 0x99)):
        poke(gb, "score", i, v)
    gb.write_u8("lives", 99)
    gb.write_u8("coins", 99)
    teleport(gb, 34 * 16, Y_BIAS + 2 * 16)       # coin: +200 and the 100th coin (+1 life)
    gb.frames(20)
    assert score(gb) == 999999
    assert gb.u8("lives") == 99 and gb.u8("coins") == 0
    d0 = digit0(gb)
    assert win_row(gb, 1)[1:7] == [d0 + 9] * 6
    assert win_row(gb, 1)[12:14] == [d0 + 9] * 2


def test_qa_button_mashing_survives(gb):
    """Random buttons every frame from boot for ~5000 frames: valid states, no late VRAM, no hang."""
    rng = random.Random(11)
    names = ["a", "b", "start", "select", "left", "right", "up", "down"]
    seen = set()
    last_time = None
    for f in range(5000):
        for n in names:
            if rng.random() < 0.3:
                gb.pyboy.button_press(n)
            else:
                gb.pyboy.button_release(n)
        gb.frames(1)
        st = gb.u8("state")
        assert 0 <= st <= 7
        seen.add(st)
    release_all(gb)
    assert gb.u8("vram_late") == 0
    assert PLAY in seen, seen
    print("mashing states seen:", sorted(seen), "worst lines", gb.u8("max_frame_lines"))


# ---------------------------------------------------------------- bot through 1-1 + budgets

def vram_matches_map(gb):
    level, tiles, ncols = level_map(gb), mt_tiles(gb), level_cols(gb)
    cam_tile = gb.u16("camera_x") >> 3
    return all(expected_tile_column(level, tiles, ncols, tc) == vram_tile_column(gb, tc)
               for tc in range(cam_tile, cam_tile + 21))


def _solid(lv, c, r):
    if r < 0 or r > 7:
        return False
    if c >= 200:
        return True
    return lv[c * 8 + r] in SOLID_MT


def _want_jump(lv, x, y, h):
    feet_row = (y + h - 1 - Y_BIAS) // 16
    top_row = max(0, (y + 2 - Y_BIAS) // 16)
    for dx in (8, 20, 32):
        c = (x + 12 + dx) // 16
        if any(_solid(lv, c, r) for r in range(top_row, feet_row + 1)):
            return True
        if feet_row < 7 and not any(_solid(lv, c, rr) for rr in range(feet_row + 1, 8)):
            return True
    return False


def play_level(gb, max_frames=12000):
    """Bot: run right holding B, jump at walls/pits reading level[] (invincible). If stuck for
    90 f it is lifted 24 px (counted in `assists`: places the bot could not pass).
    Returns a dict of measurements."""
    start_play(gb)
    gb.write_u8("cheat_flags", 3)
    gb.write_u8("max_frame_lines", 0)
    gb.pyboy.button_press("right")
    gb.pyboy.button_press("b")
    out = {"assists": [], "frames": 0, "lines": [], "spr_line": 0, "vram_bad": [], "states": set(),
           "bricks": 0}
    hold = still = lastx = 0
    for f in range(max_frames):
        st = gb.u8("state")
        out["states"].add(st)
        if st == CLEAR:
            break
        if st == PLAY:
            lv = level_map(gb)
            x, y, og = gb.u16("player_x"), gb.u8("player_y"), gb.u8("player_on_ground")
            h = gb.u8("hb_h") + gb.u8("hb_y")
            still = still + 1 if x == lastx else 0
            lastx = x
            if still > 90:
                out["assists"].append(x >> 4)
                teleport(gb, x + 4, y - 24 if y > 60 else y)
                still = 0
            if hold:
                hold -= 1
                if hold == 0:
                    gb.pyboy.button_release("a")
            elif og and y > 40 and _want_jump(lv, x, y, h):   # y > 40: see the row-1 wrap bug
                gb.pyboy.button_press("a")
                hold = 32
            if f % 16 == 0 and not vram_matches_map(gb):
                out["vram_bad"].append(f)
        gb.frames(1)
        out["lines"].append(gb.u8("frame_lines"))
        if st in (PLAY, GOAL):
            out["spr_line"] = max(out["spr_line"], sprites_per_line_max(gb))
        out["frames"] = f
    release_all(gb)
    out["worst"] = gb.u8("max_frame_lines")
    out["late"] = gb.u8("vram_late")
    return out


def test_qa_bot_plays_1_1_to_clear(gb):
    r = play_level(gb)
    print(f"bot: {r['frames']} f, states {sorted(r['states'])}, assists at columns {r['assists']}, "
          f"worst {r['worst']} lines, sprites/line {r['spr_line']}, vram_late {r['late']}")
    assert CLEAR in r["states"], "bot did not reach CLEAR"
    assert r["late"] == 0
    assert not r["vram_bad"], f"BG != level[] at frames {r['vram_bad'][:5]}"
    assert r["spr_line"] <= 10


def test_qa_bot_frame_budget_through_whole_level(gb):
    """BUG: the 3-Limo group (c122-126) plus a streamed column costs 128 lines (> 120).
    The step-3 bot never got past c45 (stuck at the turret), so it never measured this."""
    r = play_level(gb)
    assert 255 not in r["lines"], "dropped frame"
    assert r["worst"] < 120, f"worst frame {r['worst']} lines"


def test_qa_five_enemies_on_screen_frame_budget(gb):
    """BUG: GDD allows 5 active enemies; each costs ~15-20 lines. 4 standing Limos = 120 lines,
    5 = 150, 5 with Teo running (streaming) = dropped frames (255)."""
    start_play(gb)
    gb.write_u8("cheat_flags", 3)
    clear_enemies(gb)
    gb.frames(2)
    for s in range(5):
        place_enemy(gb, s, T_WALKER, 6 * 16 + s * 32, vx=-0x80)
    gb.frames(2)
    gb.write_u8("max_frame_lines", 0)
    p = gb.profile(["update_play", "enemies_update", "enemies_draw", "walk_on_map", "enemy_vs_enemy",
                    "prepare_column", "actors_draw", "player_draw", "collect_coins", "move_x",
                    "move_y", "draw_vram", "shots_vs_enemy", "player_touches"])
    gb.pyboy.button_press("right")
    gb.pyboy.button_press("b")
    lines = []
    for _ in range(90):
        gb.frames(1)
        lines.append(gb.u8("frame_lines"))
    release_all(gb)
    p.stop()
    print(p.report())
    print("5 enemies, frame lines:", lines[:30])
    assert gb.u8("vram_late") == 0
    assert 255 not in lines, "dropped frames with 5 enemies"
    assert gb.u8("max_frame_lines") < 120
