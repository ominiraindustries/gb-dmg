"""MADRIGUERA M1 - QA review (2026-10-15). What the player sees after every transition, the GDD 11
test plan rows test_m1.py does not cover, edge cases of GDD 2.2-2.6, second playthroughs and the frame
budget with a bot that fights through the three rooms. Known bugs are strict xfails (a fix turns them
into XPASS failures: remove the mark then)."""
import io

import pytest
from maz_bot import Bot
from maz_nav import (DIRS, MAP, MT, RULES as R, SC_FIN, SC_PLAY, SC_TITLE, _bases, _sets, enemies,
                     new_game, place, room_errors, settle)

UI = _bases["ui"]
UIL = _sets["ui"].labels
HEART = {"full": UI + UIL["HEART_FULL"], "half": UI + UIL["HEART_HALF"], "empty": UI + UIL["HEART_EMPTY"]}
BLANK = UI + UIL["BLANK"]
CURSOR = UI + UIL["CURSOR"]
GACT = 24                                         # sizeof(gact_t)
G_X, G_Y, G_TX, G_TY, G_DIR, G_STEP, G_MOVING, G_BEH = 1, 2, 3, 4, 5, 6, 10, 16
ROUTE = [(1, 3), (1, 2), (0, 2), (1, 2), (1, 3)]


# ------------------------------------------------------------------ helpers
def poke(gb, name, off, values):
    gb.write_bytes(name, values, offset=off)


def pin(gb, i, x, y):
    """Stand enemy i on cell (x, y), not walking, never wandering (until a sword knockback ends)."""
    poke(gb, "gact", i * GACT + G_X, [x, y, x, y])
    poke(gb, "gact", i * GACT + G_STEP, [0])
    poke(gb, "gact", i * GACT + G_MOVING, [0])
    poke(gb, "gact", i * GACT + G_BEH, [0])
    poke(gb, "en_knock", i, [0])


def gact(gb, i):
    return gb.bytes("gact", GACT * 6)[i * GACT:(i + 1) * GACT]


def room_objects(c, r):
    return [(x, y) for x, y, _, t, _ in MAP.objects
            if t == "enemy" and c * 10 <= x < c * 10 + 10 and r * 8 <= y < r * 8 + 8]


def all_still(gb):
    """Every enemy GACT_STILL and standing (lets the knockback move them, but never wander)."""
    for i, _, _ in enemies(gb):
        poke(gb, "gact", i * GACT + G_BEH, [0])
    for _ in range(60):
        gb.frames(1)
        if not any(gact(gb, i)[G_MOVING] for i, _, _ in enemies(gb)):
            return


def wtile(tx, ty):
    return MT.vram_tiles(MAP.at(tx >> 1, ty >> 1))[(ty & 1) * 2 + (tx & 1)]


def s16(v):
    return v - 65536 if v > 32767 else v


def view_errors(gb):
    """BG under the HUD vs the world map at the scroll the screen shows (SCX/SCY are one frame behind
    cam_x/cam_y in the snapshot: the VBlank ISR writes them), sampled every 4 px. Works mid-slide."""
    scx, scy = gb.io(0xFF43), gb.io(0xFF42)
    cx, cy = s16(gb.u16("cam_x")), s16(gb.u16("cam_y"))
    cx -= ((cx & 255) - scx + 128) % 256 - 128
    cy -= ((cy & 255) - scy + 128) % 256 - 128
    bg, errs = gb.bg_map(map=0), []
    for line in range(16, 144, 4):
        for px in range(0, 160, 4):
            if wtile((cx + px) >> 3, (cy + line) >> 3) != bg[((scy + line) & 255) >> 3][((scx + px) & 255) >> 3]:
                errs.append((line, px))
    return errs


def walk_out(gb, d, start, n=200):
    """Place Tilo at start facing d and hold d until the slide begins; returns frames walked."""
    place(gb, *start, d)
    gb.pyboy.button_press(d)
    for f in range(n):
        gb.frames(1)
        if gb.u8("sliding"):
            return f
    raise AssertionError(f"no slide walking {d} from {start}")


def to_r2(gb):
    walk_out(gb, "up", (236, 420))
    gb.pyboy.button_release("up")
    assert settle(gb) and (gb.u8("room_c"), gb.u8("room_r")) == (1, 2)


def die(gb):
    """Lose the last half heart against the first enemy and wait for FIN."""
    gb.write_u8("cheat_flags", 2)
    gb.write_u8("hp", 1)
    i, ex, ey = enemies(gb)[0]
    place(gb, ex * 16 + 8, ey * 16)
    assert settle(gb, SC_FIN, 300)
    gb.frames(3)


def hearts(gb):
    return gb.screen_tiles()[0][1:6]


def savestate(gb):
    s = io.BytesIO()
    gb.pyboy.save_state(s)
    return s


def loadstate(gb, s):
    s.seek(0)
    gb.pyboy.load_state(s)
    gb.frames(1)


# exits (Tilo start, direction) -> (from room, to room)
SLIDES = [
    ("up", (236, 420), (1, 3), (1, 2)),
    ("left", (176, 308), (1, 2), (0, 2)),
    ("right", (120, 308), (0, 2), (1, 2)),
    ("down", (236, 336), (1, 2), (1, 3)),
]


# ------------------------------------------------------------------ rooms and slides (GDD 2.2, 11)
def test_every_slide_shows_the_map_each_frame_and_spawns_one_enemy_per_frame(gb):
    """GDD 11 Transicion + Enemigos en la transicion, in the 4 directions: the screen == the world
    map in every frame of the slide, the old room's enemies go on the first frame, at most 1 spawn per
    frame, then as many actors as 'enemy' objects; nothing lost, nothing late; sprites owned."""
    new_game(gb)
    gb.write_u8("cheat_flags", 3)
    for d, start, frm, to in SLIDES:
        assert (gb.u8("room_c"), gb.u8("room_r")) == frm
        walk_out(gb, d, start)
        gb.pyboy.button_release(d)
        assert len(enemies(gb)) <= 1, f"{d}: old room's enemies not freed on the first frame"
        n, frames = len(enemies(gb)), 0
        while gb.u8("sliding"):
            assert view_errors(gb) == [], f"{d}: BG != map at slide frame {frames}"
            assert gb.vram_errors("play") == [], f"{d}: sprite/tile ownership at slide frame {frames}"
            assert gb.mockup_errors("play", (0, 0, 20, 2)) == [], f"{d}: HUD moved during the slide"
            m = len(enemies(gb))
            assert m - n <= 1, f"{d}: {m - n} spawns in one frame"
            n, frames = m, frames + 1
            gb.frames(1)
        assert settle(gb)
        assert (gb.u8("room_c"), gb.u8("room_r")) == to
        assert gb.u8("en_alive") == len(enemies(gb)) == len(room_objects(*to))
        assert room_errors(gb) == [] and view_errors(gb) == []
        assert gb.vram_errors("play") == []
        assert gb.u16("world_lost") == 0 and gb.u8("vram_late") == 0
        assert frames == (40 if d in ("left", "right") else 32), (d, frames)   # 160/4 or 128/4


@pytest.mark.xfail(strict=True, reason="BUG: the slide starts when the feet centre has LEFT the room "
                   "(link.c:132-137 cx/cy outside room_c/room_r), 16 px later than GDD 2.2 (centre enters the "
                   "border row): Tilo ends 1 cell too deep (row 5 of R2 instead of 6, row 2 of R1 instead of 1, "
                   "col 7 of R3 instead of 8, col 2 of R2 instead of 1) next to R2's babosa at (16,21)")
def test_slide_lands_on_the_first_interior_cell(gb):
    new_game(gb)
    gb.write_u8("cheat_flags", 3)
    want = {"up": ("row", 6), "left": ("col", 8), "right": ("col", 1), "down": ("row", 1)}
    got = {}
    for d, start, frm, to in SLIDES:
        walk_out(gb, d, start)
        gb.pyboy.button_release(d)
        assert settle(gb)
        fx, fy = (gb.u16("lx") + 8) >> 4, (gb.u16("ly") + 12) >> 4
        got[d] = ("row", fy - to[1] * 8) if want[d][0] == "row" else ("col", fx - to[0] * 10)
    assert got == want


@pytest.mark.xfail(strict=True, reason="BUG: walking up through a door Tilo disappears under the HUD for "
                   "~8 frames before the slide starts (sprite top at lines 4-7, only its feet below the cut at "
                   "16): same late trigger as above (link.c:136)")
def test_tilo_stays_visible_walking_up_to_the_slide(gb):
    new_game(gb)
    gb.write_u8("cheat_flags", 3)
    place(gb, 236, 420, "up")
    gb.pyboy.button_press("up")
    worst = 16
    for _ in range(80):
        gb.frames(1)
        if gb.u8("sliding"):
            break
        top = gb.oam()[0][0] - 16
        if gb.oam()[0][0]:                        # not in a blink frame
            worst = min(worst, top + 16 - max(top, 16))
    gb.pyboy.button_release("up")
    assert worst >= 8, f"only {worst} lines of Tilo below the HUD"


def test_no_damage_during_the_slide(gb):
    """GDD 2.2: the logic is frozen during the slide; an enemy over Tilo does not hurt him."""
    new_game(gb)
    gb.write_u8("cheat_flags", 2)
    walk_out(gb, "up", (236, 420))
    gb.pyboy.button_release("up")
    for _ in range(8):                            # let the new room's enemies spawn
        gb.frames(1)
    i = enemies(gb)[0][0]
    fx, fy = (gb.u16("lx") + 8) >> 4, (gb.u16("ly") + 12) >> 4
    poke(gb, "gact", i * GACT + G_X, [fx, fy, fx, fy])
    while gb.u8("sliding"):
        assert gb.u8("hp") == R["HP_START"] and gb.u8("inv_t") == 0
        gb.frames(1)


# ------------------------------------------------------------------ HUD (GDD 11 HUD, ui.md 3)
@pytest.mark.parametrize("hp_max", [6, 8, 10])
def test_hud_hearts_for_every_hp(gb, hp_max):
    new_game(gb)
    gb.write_u8("cheat_flags", 3)
    gb.write_u8("hp_max", hp_max)
    for hp in range(hp_max + 1):
        gb.write_u8("hp", hp)
        seen = set()
        gb.frames(3)                              # the HUD is rewritten through gbe_vq
        for _ in range(40):                       # the low-hp blink is 16/16 f
            gb.frames(1)
            seen.add(tuple(hearts(gb)))
        want = []
        for k in range(5):
            if k >= hp_max // 2:
                want.append(BLANK)
            else:
                want.append(HEART["full"] if hp >= 2 * k + 2 else HEART["half"] if hp == 2 * k + 1 else HEART["empty"])
        if 1 <= hp <= 2:
            blink = list(want)
            blink[(hp - 1) >> 1] = HEART["empty"]
            assert seen == {tuple(want), tuple(blink)}, (hp_max, hp, seen)
        else:
            assert seen == {tuple(want)}, (hp_max, hp, seen)
    assert gb.window_on() and gb.u8("hud_cut") == 1 and gb.io(0xFF45) == 16


# ------------------------------------------------------------------ movement (GDD 2.3, 11)
def test_walk_60_frames_is_75_px_and_diagonal_too(gb):
    new_game(gb)
    gb.write_u8("cheat_flags", 3)
    place(gb, 192, 428)                           # row 27 of R1 is free from col 11 to 18
    gb.hold("right", 60)
    assert gb.u16("lx") == 192 + 75
    place(gb, 213, 392)                           # diagonal inside the free cols 13-16 of R1
    poke(gb, "lxs", 0, [0])
    poke(gb, "lys", 0, [0])
    gb.pyboy.button_press("right")
    gb.pyboy.button_press("down")
    gb.frames(32)
    gb.pyboy.button_release("right")
    gb.pyboy.button_release("down")
    gb.frames(1)
    assert (gb.u16("lx"), gb.u16("ly")) == (213 + 40, 392 + 40)   # 1.25 px/f on each axis


@pytest.mark.parametrize("d,start,axis,stop", [
    ("left", (200, 428), "lx", 176 - 3),          # feet box x+3 on the left wall (col 10)
    ("right", (260, 428), "lx", 304 - 13),        # x+12 on the right wall (col 19)
    ("up", (256, 440), "ly", 400 - 8),            # y+8 under the top wall (row 24), col 16
    ("down", (256, 420), "ly", 496 - 16),         # y+15 on the bottom wall (row 31)
])
def test_walls_stop_at_the_feet_box(gb, d, start, axis, stop):
    new_game(gb)
    gb.write_u8("cheat_flags", 3)
    place(gb, *start)
    gb.hold(d, 120)
    assert gb.u16(axis) == stop
    other = "ly" if axis == "lx" else "lx"
    before = gb.u16(other)
    gb.hold(d, 30)
    assert gb.u16(axis) == stop and gb.u16(other) == before


@pytest.mark.xfail(strict=True, reason="BUG (minor): pushing against a wall still advances the 8.8 "
                   "subpixel (link.c:122-130 lxs/lys updated before the blocked step); GDD 2.3 'ni un subpixel'")
def test_pushing_a_wall_changes_not_even_the_subpixel(gb):
    new_game(gb)
    gb.write_u8("cheat_flags", 3)
    place(gb, 173, 428)                           # already on the left wall
    sub = gb.u8("lxs")
    for _ in range(5):
        gb.hold("left", 1)
        assert gb.u16("lx") == 173 and gb.u8("lxs") == sub


@pytest.mark.parametrize("off,crosses", [(5, True), (6, True), (7, False)])
def test_corner_slide_into_the_north_door(gb, off, crosses):
    """GDD 11: Tilo misaligned with the door holds up: <= 6 px (CORNER_SLIDE) crosses in <= 40 f,
    7 px does not. The door's walkable opening is the 2 door cells (x 224-255, metatiles.mt): the
    misalignment is measured against it (feet box x+3..x+12)."""
    new_game(gb)
    gb.write_u8("cheat_flags", 3)
    for lx in (224 - 3 - off, 256 - 13 + off):    # from the left jamb and from the right one
        place(gb, lx, 404, "up")                  # feet just under the top wall row
        crossed = False
        for _ in range(40):
            gb.hold("up", 1)
            if gb.u8("sliding") or gb.u16("ly") + 8 < 400:
                crossed = True
                break
        assert crossed == crosses, (lx, off)


# ------------------------------------------------------------------ sword (GDD 2.4, 11)
def _sword_setup(gb):
    new_game(gb)
    gb.write_u8("cheat_flags", 1)                 # invincible; enemies move (knockback) but never wander
    all_still(gb)
    (i, _, _), (j, _, _) = enemies(gb)[:2]
    pin(gb, i, 13, 27)
    pin(gb, j, 18, 25)                            # out of the way
    place(gb, 12 * 16, 27 * 16 - 4, "right")      # one cell left of it, facing it
    return i


def stab(gb):
    gb.pyboy.button_press("a")
    gb.frames(1)
    gb.pyboy.button_release("a")


def test_sword_hits_on_frame_2_knocks_one_cell_and_kills_on_the_second(gb):
    i = _sword_setup(gb)
    stab(gb)
    log = []
    for f in range(30):
        g = gact(gb, i)
        log.append((gb.u8("sword_t"), gb.bytes("en_hp", 6)[i], gb.u8("hitstop"), g[G_X], g[G_MOVING]))
        gb.frames(1)
    start = next(k for k, e in enumerate(log) if e[0] == 1)
    hit = next(k for k, e in enumerate(log) if e[1] == 1)
    assert hit - start == 2, log[:8]
    assert log[hit][2] == R["HITSTOP"]
    assert log[hit + 2 + 7][3:] == (14, 0), log[hit:hit + 12]  # one cell away at 6 f/cell, after hit-stop
    assert gb.u16("lx") == 192                    # Tilo does not move
    gb.frames(20)
    assert gb.bytes("en_inv", 6)[i] == 0
    pin(gb, i, 14, 27)
    place(gb, 13 * 16, 27 * 16 - 4, "right")
    alive = gb.u8("en_alive")
    stab(gb)
    gb.frames(4)
    assert gb.u8("en_alive") == alive - 1
    assert gb.u8("fx_t") > 0                      # the puf


def test_enemy_invulnerable_20_frames_after_a_hit(gb):
    i = _sword_setup(gb)
    poke(gb, "en_hp", i, [3])
    stab(gb)
    gb.frames(4)
    assert gb.bytes("en_hp", 6)[i] == 2
    pin(gb, i, 13, 27)                            # back in front of the sword at once
    gb.frames(8)                                  # the stab ends (14 f)
    stab(gb)
    gb.frames(4)
    assert gb.bytes("en_hp", 6)[i] == 2, "hit twice inside the 20 f of invulnerability"
    gb.frames(20)
    pin(gb, i, 13, 27)
    stab(gb)
    gb.frames(4)
    assert gb.bytes("en_hp", 6)[i] == 1


def test_sword_buffer_chains_and_tilo_never_moves(gb):
    new_game(gb)
    gb.write_u8("cheat_flags", 3)
    place(gb, 220, 428, "right")
    gb.pyboy.button_press("right")                # held through both stabs: must not move
    gb.tap("a")
    while gb.u8("sword_t") < 10:
        gb.frames(1)
    gb.tap("a")                                   # in the buffer window (8..13)
    restarted = False
    for _ in range(30):
        gb.frames(1)
        if gb.u8("sword_t") <= 2:
            restarted = True
            break
        assert gb.u16("lx") == 220
    assert restarted, "A at f10 did not chain another stab"
    gb.pyboy.button_release("right")
    # A before the window (f5) does not chain
    place(gb, 220, 428, "right")
    gb.frames(20)
    gb.tap("a")
    while gb.u8("sword_t") < 5:
        gb.frames(1)
    gb.tap("a")
    for _ in range(20):
        gb.frames(1)
    assert gb.u8("sword_t") == 0


def test_hitstop_freezes_the_sword_and_the_enemies(gb):
    i = _sword_setup(gb)
    stab(gb)
    for _ in range(10):
        if gb.u8("hitstop"):
            break
        gb.frames(1)
    assert gb.u8("hitstop") == R["HITSTOP"]
    s, g = gb.u8("sword_t"), gact(gb, i)
    gb.frames(1)
    assert gb.u8("sword_t") == s and gact(gb, i)[G_STEP] == g[G_STEP]
    gb.frames(1)
    assert gb.u8("sword_t") == s
    gb.frames(1)
    assert gb.u8("sword_t") == s + 1 and gb.u8("hitstop") == 0


def test_sword_against_a_wall_changes_nothing(gb):
    new_game(gb)
    gb.write_u8("cheat_flags", 3)
    for d, pos in (("left", (173, 428)), ("up", (256, 392)), ("right", (291, 428)), ("down", (256, 480))):
        place(gb, *pos, d)
        alive = gb.u8("en_alive")
        gb.tap("a")
        gb.frames(20)
        assert (gb.u16("lx"), gb.u16("ly")) == pos and gb.u8("ldir") == DIRS[d]
        assert gb.u8("en_alive") == alive and gb.u8("hitstop") == 0 and gb.u8("sword_t") == 0


@pytest.mark.xfail(strict=True, reason="BUG: a babosa hit while walking between cells is not knocked back "
                   "and jumps up to 16 px: gact_try_move() on a moving actor still changes a->dir "
                   "(gbe_gact.c:84) so it is drawn offset along the new axis, then snaps to its old target "
                   "at 6 f/cell; room.c:147-152 calls it without checking g->moving (~25% of hits)")
def test_babosa_hit_mid_step_does_not_teleport(gb):
    new_game(gb)
    gb.write_u8("cheat_flags", 1)
    for _ in range(600):
        gb.frames(1)
        g = gact(gb, 0)
        if g[0] and g[G_MOVING] and 3 <= g[G_STEP] <= 8 and g[G_DIR] >= 2:
            break
    else:
        pytest.skip("no babosa walked sideways")
    g = gact(gb, 0)
    place(gb, g[G_X] * 16, g[G_Y] * 16 + 20, "up")        # below it: knockback is upwards
    before = (gb.oam()[6][0], gb.oam()[6][1])
    gb.tap("a")
    jumps = []
    for _ in range(30):
        gb.frames(1)
        o = gb.oam()[6]
        if o[0]:
            jumps.append(abs(o[0] - before[0]) + abs(o[1] - before[1]))
            before = (o[0], o[1])
    assert max(jumps) <= 6, f"sprite jumped {max(jumps)} px in one frame"


# ------------------------------------------------------------------ damage (GDD 2.5)
def test_two_enemies_touching_at_once_cost_one_half_heart(gb):
    new_game(gb)
    gb.write_u8("cheat_flags", 2)
    gb.frames(2)
    (i, _, _), (j, _, _) = enemies(gb)[:2]
    pin(gb, i, 15, 27)
    pin(gb, j, 16, 27)
    place(gb, 15 * 16 + 8, 27 * 16)
    gb.frames(10)
    assert gb.u8("hp") == R["HP_START"] - 1


def test_knockback_stops_at_the_wall(gb):
    new_game(gb)
    gb.write_u8("cheat_flags", 2)
    gb.frames(2)
    i = enemies(gb)[0][0]
    pin(gb, i, 11, 27)
    place(gb, 173, 27 * 16)                       # on the left wall, the babosa overlapping it
    gb.frames(12)
    assert gb.u8("hp") == R["HP_START"] - 1
    assert gb.u16("lx") == 173, "pushed into the wall"


@pytest.mark.xfail(strict=True, reason="BUG: knockback can push Tilo out of the room through a doorway "
                   "(link.c:99-106 steps without the room-exit check, and the exit check at :132-137 only runs "
                   "while a direction is held): he stands off-screen under R2 and pressing UP slides DOWN")
def test_knockback_into_a_doorway_keeps_tilo_in_the_room(gb):
    new_game(gb)
    gb.write_u8("cheat_flags", 2)
    to_r2(gb)
    i = enemies(gb)[0][0]
    pin(gb, i, 15, 22)                            # above R2's south doorway
    place(gb, 235, 358, "up")                     # in the doorway, overlapping it from below
    gb.frames(20)
    assert gb.u8("hp") == R["HP_START"] - 1
    assert (gb.u16("ly") + 12) >> 4 < 24, "Tilo's feet left R2 without a slide"


def test_hurt_invulnerability_blinks_4_on_4_off(gb):
    new_game(gb)
    gb.write_u8("cheat_flags", 2)
    gb.frames(2)
    i, ex, ey = enemies(gb)[0]
    place(gb, ex * 16 + 8, ey * 16)
    vis = []
    for _ in range(64):
        gb.frames(1)
        if gb.u8("inv_t"):
            vis.append((gb.u8("inv_t"), bool(gb.oam()[0][0])))
    assert len(vis) >= 55
    for t, v in vis:
        assert v == (not (t & 4)), (t, v)


# ------------------------------------------------------------------ pickups (GDD 2.10, 11 Recogibles)
def test_babosa_drops_a_heart_with_the_right_roll_and_it_expires(gb):
    i = _sword_setup(gb)
    poke(gb, "en_hp", i, [1])
    s = savestate(gb)
    dropped = None
    for seed in range(1, 40):
        loadstate(gb, s)
        gb.write_u16("rng_state", seed * 2654435761 & 0xFFFF or 1)
        stab(gb)
        gb.frames(6)
        assert gb.u8("en_alive") == 1
        if gb.u16("pk_t"):
            dropped = seed
            break
    assert dropped, "no heart in 39 kills (1 in 4 expected)"
    x, y = gb.bytes("pk_x", 1)[0], gb.bytes("pk_y", 1)[0]
    assert gb.vram_errors("play") == []           # heart + puf drawn with their own tiles
    o = gb.oam()[18]
    assert o[0] == y + 16 and o[1] == x + 8
    # it blinks in the last 60 f and is gone at 300
    t = gb.u16("pk_t")
    gb.frames(t - 50)
    vis = set()
    for _ in range(20):
        gb.frames(1)
        vis.add(bool(gb.oam()[18][0]))
    assert vis == {True, False}
    gb.frames(40)
    assert gb.u16("pk_t") == 0 and gb.oam()[18][0] == 0


def test_heart_pickup_does_not_pass_the_maximum(gb):
    new_game(gb)
    gb.write_u8("cheat_flags", 2)
    gb.write_u8("hp", 5)
    place(gb, 240, 448)
    gb.write_bytes("pk_x", [(240 - 160) + 4])
    gb.write_bytes("pk_y", [448 - 368])
    gb.write_u16("pk_t", 200)
    gb.frames(3)
    assert gb.u8("hp") == 6 and gb.u16("pk_t") == 0


# ------------------------------------------------------------------ death, FIN, flows (GDD 2.5, 4)
@pytest.mark.xfail(strict=True, reason="BUG (spec): death fades to WHITE; GDD 2.5 and ui.md 9 ask for a fade "
                   "to black (JUEGO->FIN and FIN->JUEGO): main.c:124/131 use transition() = set_fade (white) "
                   "instead of set_fade_dark")
def test_death_fades_to_black(gb):
    new_game(gb)
    gb.write_u8("cheat_flags", 2)
    gb.write_u8("hp", 1)
    i, ex, ey = enemies(gb)[0]
    place(gb, ex * 16 + 8, ey * 16)
    last = None
    for _ in range(80):
        gb.frames(1)
        if gb.u8("trans_phase") == 1:
            last = gb.io(0xFF47)
        if gb.u8("scene") == SC_FIN:
            break
    assert last == 0xFF, hex(last)


@pytest.mark.xfail(strict=True, reason="BUG: the screen shakes for 5 frames after 'Continuar' and at the start "
                   "of a new game after Salir: the fatal hit sets shake_t (link.c:69) but link_update never runs "
                   "while dead_t, and the static shake_t is not reset by link_place/screen_build")
@pytest.mark.parametrize("how", ["continue", "salir_new_game"])
def test_no_screen_shake_after_dying(gb, how):
    new_game(gb)
    die(gb)
    if how == "continue":
        gb.tap("a")
    else:
        gb.tap("down")
        gb.tap("a")
        assert settle(gb, SC_TITLE, 300)
        gb.tap("start")
    assert settle(gb, SC_PLAY, 300)
    for _ in range(30):
        gb.frames(1)
        assert gb.s8("shake_x") == 0


def test_fin_texts_cursor_and_wrap(gb):
    new_game(gb)
    die(gb)
    assert [gb.read_text(r) for r in (6, 9, 11)] == ["Has caido.", "Continuar", "Salir"]
    assert gb.mockup_errors("fin") == [] and gb.vram_errors("gameover") == []
    assert not gb.window_on() and gb.u8("hud_cut") == 0
    assert all(o[0] == 0 for o in gb.oam())
    col = lambda r: gb.screen_tiles()[r][6]       # noqa: E731
    assert (col(9), col(11)) == (CURSOR, BLANK)
    for k, key in enumerate(("down", "down", "up", "up")):
        gb.tap(key)
        gb.frames(2)
        assert gb.u8("fin_sel") == [1, 0, 1, 0][k]
        assert (col(9), col(11)) == ((BLANK, CURSOR) if gb.u8("fin_sel") else (CURSOR, BLANK))
    gb.tap("b")                                   # B does nothing
    gb.frames(20)
    assert gb.u8("scene") == SC_FIN


def test_salir_then_new_game_resets_everything(gb):
    """Second playthrough: die in R3 after hurting things, Salir, new game -> the start state again."""
    new_game(gb)
    gb.write_u8("cheat_flags", 3)
    first = {k: gb.u16(k) for k in ("lx", "ly")}
    to_r2(gb)
    walk_out(gb, "left", (176, 308))
    gb.pyboy.button_release("left")
    assert settle(gb) and (gb.u8("room_c"), gb.u8("room_r")) == (0, 2)
    gb.write_u8("hp_max", 8)                      # as if the M3 heart container had been taken
    gb.write_u16("pk_t", 100)
    die(gb)
    gb.tap("down")
    gb.tap("a")
    assert settle(gb, SC_TITLE, 300)
    gb.frames(3)
    assert gb.mockup_errors("title", ignore=["PULSA_START"]) == []
    assert gb.vram_errors("title") == []
    assert not gb.window_on() and all(o[0] == 0 for o in gb.oam())
    assert (gb.io(0xFF42), gb.io(0xFF43)) == (0, 0)
    gb.write_u8("cheat_flags", 0)
    new_game(gb)
    assert (gb.u8("room_c"), gb.u8("room_r")) == (1, 3)
    assert {k: gb.u16(k) for k in ("lx", "ly")} == first
    assert gb.u8("hp") == gb.u8("hp_max") == R["HP_START"]
    assert gb.u16("deaths") == 0
    assert gb.u8("en_alive") == len(enemies(gb)) == 2
    for v in ("sliding", "hitstop", "knock_t", "inv_t", "dead_t", "sword_t", "sword_buf", "fx_t"):
        assert gb.u8(v) == 0, v
    assert gb.bytes("pk_t", 8) == [0] * 8         # shake_x: see test_no_screen_shake_after_dying
    assert room_errors(gb) == [] and gb.vram_errors("play") == []
    assert gb.mockup_errors("play", (0, 0, 20, 2)) == []
    assert gb.u8("ldir") == DIRS["up"]


def test_continue_twice_counts_deaths_and_returns_to_the_room_entry(gb):
    new_game(gb)
    gb.write_u8("cheat_flags", 3)
    to_r2(gb)
    entry = (gb.u16("lx"), gb.u16("ly"), gb.u8("ldir"))
    for n in (1, 2):
        die(gb)
        gb.tap("a")
        assert settle(gb, SC_PLAY, 300)
        assert (gb.u8("room_c"), gb.u8("room_r")) == (1, 2)
        assert (gb.u16("lx"), gb.u16("ly"), gb.u8("ldir")) == entry
        assert gb.u8("hp") == gb.u8("hp_max") and gb.u16("deaths") == n
        assert gb.u8("en_alive") == 3                 # enemies come back (GDD 2.5)
        assert room_errors(gb) == [] and gb.vram_errors("play") == []
        assert gb.mockup_errors("play", (0, 0, 20, 2)) == []


def test_title_and_fin_still_work_after_more_than_255_frames(gb):
    gb.frames(700)
    seen = set()
    for _ in range(64):
        gb.frames(1)
        seen |= {gb.read_text(r) for r in range(14, 18)}
    assert "Pulsa Start" in seen, seen
    new_game(gb)
    die(gb)
    gb.frames(700)
    gb.tap("down")
    assert gb.u8("fin_sel") == 1
    gb.tap("a")
    assert settle(gb, SC_TITLE, 300)


def test_mashing_buttons_through_the_transitions(gb):
    gb.frames(20)
    for f in range(40):                           # title -> play while mashing
        b = ("start", "a", "b", "select")[f % 4]
        gb.hold(b, 1)
    assert settle(gb, SC_PLAY, 300)
    assert gb.u8("trans_phase") == 0 and gb.vram_errors("play") == []
    gb.write_u8("cheat_flags", 2)
    gb.write_u8("hp", 1)
    i, ex, ey = enemies(gb)[0]
    place(gb, ex * 16 + 8, ey * 16)
    for f in range(120):                          # death freeze + fade while mashing
        gb.hold(("a", "start", "up", "b")[f % 4], 1)
        if gb.u8("scene") == SC_FIN and not gb.u8("trans_phase"):
            break
    assert gb.u8("scene") in (SC_FIN, SC_PLAY)
    assert settle(gb, gb.u8("scene"), 300)
    assert gb.vram_errors("gameover" if gb.u8("scene") == SC_FIN else "play") == []


def test_start_and_select_do_nothing_in_play(gb):
    """M1 has no pause (M3): Start/Select in a room, mid-slide and mid-death change nothing."""
    new_game(gb)
    gb.write_u8("cheat_flags", 3)
    gb.tap("start")
    gb.tap("select")
    assert gb.u8("scene") == SC_PLAY and gb.u8("trans_phase") == 0
    walk_out(gb, "up", (236, 420))
    gb.pyboy.button_release("up")
    gb.tap("start")
    assert settle(gb) and gb.u8("room_r") == 2


# ------------------------------------------------------------------ sprites per line, engine
def test_three_babosas_in_line_with_tilo_and_sword_fit_10_per_line(gb):
    """GDD 7.3: M1 peak = Tilo 2 + sword 2 + 3 babosas x 2 = 10 sprites on a line (no rotation
    until M2): every one must be drawn."""
    new_game(gb)
    gb.write_u8("cheat_flags", 3)
    to_r2(gb)
    for k, (i, _, _) in enumerate(enemies(gb)):
        pin(gb, i, (11, 16, 18)[k], 22)
    place(gb, 13 * 16, 22 * 16 - 4, "right")
    gb.tap("a")
    gb.frames(2)
    lines = gb.line_sprites(16, 143)
    worst = max(len(r) for r, _ in lines.values())
    assert worst == 10, worst
    assert all(r == d for r, d in lines.values())


def test_engine_selftest(gb):
    """gb.selftest() needs the world loaded (in a room: at the title 67/200 cases differ because the
    world cache is empty) and trashes it afterwards: run it on its own boot (gbe_selftest.c)."""
    new_game(gb)
    bad, n = gb.selftest()
    assert n > 0 and bad == 0, (bad, n)


# ------------------------------------------------------------------ frame budget (GDD 9.6, 11)
def test_bot_fights_through_the_three_rooms_within_the_frame_budget(gb):
    """GDD 11 Presupuesto: R1 -> R2 -> R3 -> R2 -> R1 killing every babosa (real wandering enemies,
    sword hits, hit-stop, knockback, pufs, slides). The bot must make progress."""
    new_game(gb)
    gb.write_u8("cheat_flags", 1)
    bot = Bot(ROUTE)
    res = gb.run_bot(bot.step, bot.progress, 6000,
                     done=lambda g: bot.leg == len(ROUTE) - 1 and not g.u8("en_alive") and not g.u8("sliding"))
    print("bot", res, "kills", bot.kills)
    assert not res["gave_up"] and res["assists"] == 0
    assert bot.leg == len(ROUTE) - 1 and bot.kills >= 10
    assert res["vram_late"] == 0 and gb.u16("world_lost") == 0 and gb.u8("vq_lost") == 0
    assert res["worst_lines"] < 100               # 97 measured on 2026-10-15: 3 lines of margin


def test_two_babosas_killed_in_one_swing_within_budget(gb):
    """The heaviest single frame we can build: 2 kills in one stab (2 x kill + puf + heart roll) while
    the third babosa thinks, in R2."""
    new_game(gb)
    gb.write_u8("cheat_flags", 1)
    to_r2(gb)
    en = enemies(gb)
    (i, _, _), (j, _, _) = en[:2]
    pin(gb, i, 14, 22)
    pin(gb, j, 13, 22)
    for k in (i, j):
        poke(gb, "en_hp", k, [1])
    place(gb, 13 * 16, 22 * 16 - 4, "right")
    gb.write_u8("max_frame_lines", 0)
    alive = gb.u8("en_alive")
    stab(gb)
    gb.frames(8)
    assert gb.u8("en_alive") == alive - 2
    print("double kill worst lines", gb.u8("max_frame_lines"))
    assert gb.u8("max_frame_lines") < 100 and gb.u8("vram_late") == 0


def test_contact_sheet_of_the_bot_run(gb):
    """Screenshots (build/shots/qa_sheet_*.png) on every state change of the fighting bot: room,
    slide start / middle, sword, hurt, kill, heart; Read them in a review (vram_errors judges only
    tile ownership, not art). Asserts the scene ownership on each of those frames."""
    new_game(gb)
    gb.write_u8("cheat_flags", 1)
    bot = Bot(ROUTE)
    keys = ("room_c", "room_r", "sliding", "en_alive", "hp", "fx_t")
    prev, n, slide_t = None, 0, 0
    for f in range(1600):
        bot.step(gb, f)
        gb.frames(1)
        state = tuple(gb.u8(k) for k in keys) + (gb.u8("sword_t") == 4, bool(gb.u16("pk_t")))
        slide_t = slide_t + 1 if gb.u8("sliding") else 0
        if (state != prev or slide_t == 16) and n < 80:
            assert gb.vram_errors("play") == [], f
            gb.screenshot(f"qa_sheet_{n:02d}")
            n += 1
        prev = state
        if bot.leg == len(ROUTE) - 1 and not gb.u8("en_alive") and not gb.u8("sliding"):
            break
    assert n > 20 and gb.u8("vq_lost") == 0
