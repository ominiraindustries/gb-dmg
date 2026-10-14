"""GRIFO M1b QA pass (GDD 11 gaps): autofire with the pool full, flicker union, enemy fire rules,
extra lives / score cap, pause in every sub-state, HUD VRAM vs variables, CLEAR bonus count,
second game after GAMEOVER / CLEAR. Known bugs are strict xfails (remove the mark once fixed)."""
import pytest

from stage_model import MT_ID, MT_TILES, STOP_SCROLL, check_screen
from test_flow import BOSS_DEAD, BOSS_FIGHT, ST_CLEAR, ST_CONTINUE, ST_GAMEOVER, ST_PAUSE, \
    ST_PLAY, ST_TITLE, die, to_boss, wait_state, word
from test_mechanics import CHEAT_FREEZE, CHEAT_INVINCIBLE, CHEAT_NO_LEVEL, OBJ_DART, OBJ_SWOOP, \
    P_BULLET, P_ENEMY, P_SHOT, P_TURRET, PS_DYING, PS_NORMAL, PS_RESPAWN, isolate, live, put, rec

OBJ_WAVE_F = 3
T_DIGIT0, T_BLANK = 24, 0
UI_ICON_LIFE, UI_ICON_BOMB, UI_ICON_POWER = 1, 2, 3
UI_BAR_0, UI_BAR_CAP_L, UI_BAR_CAP_R = 5, 14, 15
PS_BOSS_INTRO = 3
BOSS_OUTRO = 4


def put_full(gb, i, t, x, y, vx=0, vy=0, s=0, tm=0, hp=1, tile=0):
    rec_ = [t, x, 0, y, 0, vx & 0xFF, (vx >> 8) & 0xFF, vy & 0xFF, (vy >> 8) & 0xFF,
            s, tm, x, tile, 0, hp, 0]
    gb.write_bytes("pool", rec_, i * 16)


def put_turret(gb, y_target, tm=40):
    """Logical turret record whose map row is now at OAM y ~y_target (t, x, s mt, tm, aux col, pad row)."""
    row = (gb.u16("scroll_y") + 144 - y_target) // 16
    put_full(gb, P_TURRET, 1, 72, 0, s=0, tm=tm, hp=6)
    gb.write_bytes("pool", [4], P_TURRET * 16 + 11)
    gb.write_bytes("pool", [row & 255], P_TURRET * 16 + 15)


def bcd(gb, name="score"):
    b = gb.bytes(name, 3)
    return int(f"{b[2]:02x}{b[1]:02x}{b[0]:02x}")


def set_bcd(gb, value, name="score"):
    s = f"{value:06d}"
    gb.write_bytes(name, [int(s[4:6], 16), int(s[2:4], 16), int(s[0:2], 16)])


def win_row0(gb):
    gb.frames(1)
    return gb.bg_map(window=True)[0][:20]


# ------------------------------------------------------------------ autofire (GDD 2.2, 11)

@pytest.mark.parametrize("power", [1, 2, 3])
def test_autofire_8_bursts_in_64_frames(gb, power):
    """A held 64 f -> 8 bursts at every weapon level; level 3 adds the 2 side shots on every 2nd."""
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_INVINCIBLE)
    gb.write_u8("power", power)
    gb.frames(10)
    b0 = gb.u8("burst")
    created = 0
    prev = set(live(gb, P_SHOT, 8))
    gb.pyboy.button_press("a")
    for _ in range(64):
        gb.frames(1)
        cur = set(live(gb, P_SHOT, 8))
        created += len(cur - prev)
        prev = cur
    gb.pyboy.button_release("a")
    bursts = (gb.u8("burst") - b0) & 255
    assert bursts == 8, bursts
    assert created == {1: 8, 2: 8, 3: 16}[power], created


@pytest.mark.parametrize("power", [1, 3])
def test_autofire_pool_full_creates_nothing(gb, power):
    """8 frozen shots fill the pool: holding A must not overwrite any record; with 1 slot free a
    level-3 burst only gets its central beam out (the side shots are lost, GDD 2.2)."""
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_INVINCIBLE | CHEAT_FREEZE)
    gb.write_u8("power", power)
    for k in range(8):
        put_full(gb, P_SHOT + k, 1, 16 + k * 16, 60, vy=-0x0500, tile=12)
    before = [rec(gb, P_SHOT + k) for k in range(8)]
    gb.pyboy.button_press("a")
    gb.frames(40)
    assert [rec(gb, P_SHOT + k) for k in range(8)] == before
    gb.pyboy.button_release("a")
    gb.frames(10)
    if power == 3:
        gb.write_bytes("pool", [0] * 16, (P_SHOT + 3) * 16)       # one free slot
        gb.write_u8("burst", 0)                                   # next burst has side shots
        gb.pyboy.button_press("a")
        gb.frames(3)
        gb.pyboy.button_release("a")
        assert len(live(gb, P_SHOT, 8)) == 8
        assert rec(gb, P_SHOT + 3)[9] == 1                        # the double beam took it


# ------------------------------------------------------------------ sprites per line (GDD 7.3)

def _bullet_lines(gb, n, y):
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_INVINCIBLE | CHEAT_FREEZE)
    gb.write_u8("player_y", 136)                                  # player off the bullet band
    for k in range(n):
        put_full(gb, P_BULLET + k, 1, 12 + k * 12, y, tile=18)
    gb.frames(2)


def _drawn_bullets(gb, line):
    oam = gb.oam()
    req, drawn = gb.line_sprites(line, line)[line]
    return {(oam[i][1]) for i in drawn if 2 <= i < 14}


def test_flicker_12_bullets_one_line_every_bullet_within_2_frames(gb):
    """12 bullets on one line (+0 player): 10 drawn per frame; each bullet must be drawn at least
    once in any 2 consecutive frames (GDD 7.3: never hidden 2 frames in a row)."""
    _bullet_lines(gb, 12, 80)
    line = 80 - 16 + 2
    xs = {12 + k * 12 for k in range(12)}
    prev, worst = None, 12
    for f in range(40):
        gb.frames(1)
        cur = _drawn_bullets(gb, line)
        if prev is not None:
            worst = min(worst, len(prev | cur))
        prev = cur
    assert worst == len(xs), f"union of 2 frames had only {worst} of 12 bullets"


def test_flicker_player_plus_12_bullets_union_of_2_frames(gb):
    """GDD 11: frozen objects, 14 sprites on one line (player 2 + 12 bullets): the player is always
    drawn and the union of 2 consecutive frames contains all 12 bullets."""
    _bullet_lines(gb, 12, 80)
    gb.write_u8("player_y", 78)
    gb.write_u8("player_x", 150)
    line = 80 - 16 + 2
    prev, worst, lost_player = None, 12, 0
    for f in range(40):
        gb.frames(1)
        req, drawn = gb.line_sprites(line, line)[line]
        lost_player += 0 not in drawn
        cur = _drawn_bullets(gb, line)
        if prev is not None:
            worst = min(worst, len(prev | cur))
        prev = cur
    assert lost_player == 0
    assert worst == 12, f"union of 2 frames had only {worst} of 12 bullets"


# ------------------------------------------------------------------ enemy fire rules (GDD 2.6)

def _stopped_swoop(gb, y=56):
    # SWOOP already stopped (s = 0x80, vy 0): fires FAN(3) when tm >= 20
    put_full(gb, P_ENEMY, OBJ_SWOOP, 72, y, s=0x80, tm=0, hp=4, tile=38)


def test_no_fire_within_32px_above_player(gb):
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_INVINCIBLE)
    gb.write_u8("player_y", 56 + 31)                              # 31 px below the swoop
    gb.write_u8("player_x", 40)
    _stopped_swoop(gb)
    gb.frames(36)
    assert live(gb, P_BULLET, 12) == []
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_INVINCIBLE)
    gb.write_u8("player_y", 56 + 32)                              # 32 px: fires
    _stopped_swoop(gb)
    gb.frames(36)
    assert len(live(gb, P_BULLET, 12)) == 3


def test_no_fire_from_below_player(gb):
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_INVINCIBLE)
    gb.write_u8("player_y", 40)
    gb.write_u8("player_x", 40)
    _stopped_swoop(gb, y=80)
    gb.frames(36)
    assert live(gb, P_BULLET, 12) == []


def test_no_fire_during_bomb(gb):
    isolate(gb, CHEAT_NO_LEVEL)
    gb.write_u8("bombs", 2)
    gb.tap("b")
    _stopped_swoop(gb)                                           # would fire 20 f later
    gb.frames(36)
    assert gb.u8("bomb_timer") > 0
    assert live(gb, P_BULLET, 12) == []
    # turret too: put one in range, timer about to fire
    put_turret(gb, 64, tm=2)
    gb.frames(4)
    assert 32 <= rec(gb, P_TURRET)[3] <= 112
    assert live(gb, P_BULLET, 12) == []


def test_no_fire_60_frames_after_respawn(gb):
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_FREEZE)
    die(gb)                                                       # 40 f: dying -> respawn
    gb.write_u8("cheat_flags", CHEAT_NO_LEVEL)
    for _ in range(40):
        gb.frames(1)
        if gb.u8("play_sub") == PS_NORMAL:
            break
    assert gb.u8("play_sub") == PS_NORMAL
    nf = gb.u8("no_fire")
    assert 30 <= nf <= 42, nf                                     # 60 - 20 f of the entry
    _stopped_swoop(gb)
    gb.frames(30)                                                 # swoop tries at tm 20
    assert live(gb, P_BULLET, 12) == []
    gb.frames(nf)
    assert gb.u8("no_fire") == 0
    _stopped_swoop(gb)                                            # a new one fires again
    gb.frames(36)
    assert len(live(gb, P_BULLET, 12)) == 3


def test_turret_does_not_fire_below_screen_y_96(gb):
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_INVINCIBLE | CHEAT_FREEZE)
    gb.write_u8("cheat_flags", CHEAT_NO_LEVEL | CHEAT_INVINCIBLE)
    put_turret(gb, 124, tm=2)
    gb.frames(4)
    assert rec(gb, P_TURRET)[3] > 112
    assert live(gb, P_BULLET, 12) == []


# ------------------------------------------------------------------ score, lives (GDD 2.4, 2.11)

def _kill_dart(gb):
    put(gb, P_ENEMY, OBJ_DART, gb.u8("player_x"), 40, hp=1)
    gb.pyboy.button_press("a")
    for _ in range(40):
        gb.frames(1)
        if rec(gb, P_ENEMY)[0] != OBJ_DART:
            break
    gb.pyboy.button_release("a")
    gb.frames(2)


def test_extra_life_at_50000(gb):
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_INVINCIBLE)
    set_bcd(gb, 49990)
    gb.write_u8("extends", 1)                                     # 20 000 already given
    lives = gb.u8("lives")
    _kill_dart(gb)
    assert bcd(gb) == 50090
    assert gb.u8("lives") == lives + 1
    set_bcd(gb, 49990)
    _kill_dart(gb)
    assert gb.u8("lives") == lives + 1                             # once only


def test_extra_lives_cap_at_9(gb):
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_INVINCIBLE)
    gb.write_u8("lives", 9)
    set_bcd(gb, 19990)
    _kill_dart(gb)
    assert gb.u8("lives") == 9
    gb.frames(130)
    assert win_row0(gb)[8] == T_DIGIT0 + 9


def test_score_saturates_at_999999(gb):
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_INVINCIBLE)
    gb.write_u8("extends", 3)
    set_bcd(gb, 999950)
    _kill_dart(gb)
    assert bcd(gb) == 999999
    gb.frames(130)                                                # FASE 1 message over
    assert win_row0(gb)[0:6] == [T_DIGIT0 + 9] * 6


# ------------------------------------------------------------------ HUD vs variables (ui.md 2)

def test_hud_counters_match_variables(gb):
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_INVINCIBLE)
    gb.frames(130)
    set_bcd(gb, 12340)
    gb.write_u8("extends", 3)
    gb.write_u8("lives", 7)
    gb.write_u8("bombs", 4)
    gb.write_u8("power", 3)
    _kill_dart(gb)                                                # add_score marks the score dirty
    row = win_row0(gb)
    want_score = [T_DIGIT0 + int(c) for c in f"{bcd(gb):06d}"]
    assert row[0:6] == want_score
    assert row[6:15] == [T_BLANK, UI_ICON_LIFE, T_DIGIT0 + 7, T_BLANK, UI_ICON_BOMB, T_DIGIT0 + 4,
                         T_BLANK, UI_ICON_POWER, T_DIGIT0 + 3]
    assert row[15:20] == [T_BLANK] * 5


def _bar_expected(hp):
    px = (hp * 31) >> 8
    if hp and not px:
        px = 1
    tiles = []
    for i in range(3):
        v = min(8, max(0, px - 8 * i))
        tiles.append(UI_BAR_0 + v)
    return [UI_BAR_CAP_L] + tiles + [UI_BAR_CAP_R]


def test_boss_bar_vram_matches_hp(gb):
    to_boss(gb)
    for _ in range(300):                                          # PELIGRO still up at 8 px/f
        gb.frames(1)
        if gb.u8("hud_msg") == 0:
            break
    gb.frames(30)                                                 # intro fill over
    for hp in (200, 150, 101, 64, 9, 8, 1):
        gb.write_u8("boss_hp", hp)
        gb.frames(4)
        assert gb.u8("boss_hp") == hp
        assert win_row0(gb)[15:20] == _bar_expected(hp), hp
    gb.screenshot("qa_boss_bar")


def test_boss_bar_cleared_in_outro(gb):
    to_boss(gb)
    gb.write_u8("boss_hp", 1)
    gb.pyboy.button_press("a")
    for _ in range(200):
        gb.frames(1)
        if gb.u8("boss_state") >= BOSS_OUTRO:
            break
    gb.pyboy.button_release("a")
    gb.frames(70)
    assert gb.u8("boss_state") == BOSS_OUTRO
    assert win_row0(gb)[15:20] == [T_BLANK] * 5


# ------------------------------------------------------------------ pause (ui.md 2.4, 4)

def _to_peligro(gb):
    gb.write_u8("cheat_flags", CHEAT_INVINCIBLE | 0x08)
    gb.write_u16("cheat_scroll", 0x0800)
    for _ in range(600):
        gb.frames(1)
        if gb.u8("hud_msg") == 2:
            break
    gb.write_u8("cheat_flags", CHEAT_INVINCIBLE)
    assert gb.u8("hud_msg") == 2


def test_pause_during_peligro_resumes_message(gb):
    _to_peligro(gb)
    gb.frames(20)
    timer = gb.u8("hud_msg_timer")
    gb.tap("start")
    gb.frames(3)
    assert gb.u8("state") == ST_PAUSE
    assert win_row0(gb)[7:12] == word("PAUSA")
    gb.frames(30)
    gb.tap("start")
    gb.frames(3)
    assert gb.u8("state") == ST_PLAY
    assert gb.u8("hud_msg") == 2, "PELIGRO lost after the pause"
    assert abs(gb.u8("hud_msg_timer") - (timer - 5)) <= 6


def test_pause_during_peligro_freezes_and_restores_counters(gb):
    """What must hold even with the current behaviour: logic frozen, HUD row not garbage after."""
    _to_peligro(gb)
    gb.tap("start")
    gb.frames(3)
    s0 = gb.u16("scroll_y")
    gb.frames(60)
    assert gb.u16("scroll_y") == s0 and gb.u8("state") == ST_PAUSE
    gb.tap("start")
    gb.frames(200)
    row = win_row0(gb)
    assert row[7] == UI_ICON_LIFE and row[10] == UI_ICON_BOMB and row[13] == UI_ICON_POWER


@pytest.mark.parametrize("sub", ["respawn", "boss_intro", "boss"])
def test_pause_allowed_substates(gb, sub):
    if sub == "respawn":
        isolate(gb, CHEAT_NO_LEVEL | CHEAT_FREEZE)
        die(gb)
        gb.write_u8("cheat_flags", CHEAT_NO_LEVEL)
        for _ in range(20):
            if gb.u8("play_sub") == PS_RESPAWN:
                break
            gb.frames(1)
        assert gb.u8("play_sub") == PS_RESPAWN
    elif sub == "boss_intro":
        gb.write_u8("cheat_flags", CHEAT_INVINCIBLE | 0x08)
        gb.write_u16("cheat_scroll", 0x0800)
        for _ in range(600):
            gb.frames(1)
            if gb.u8("boss_state") == 1:
                break
        assert gb.u8("boss_state") == 1
    else:
        to_boss(gb)
    gb.tap("start")
    gb.frames(2)
    assert gb.u8("state") == ST_PAUSE, sub
    y0, t0 = gb.u8("player_y"), gb.u8("boss_t")
    gb.frames(30)
    assert gb.u8("boss_t") == t0
    assert gb.u8("player_y") == y0
    gb.tap("start")
    gb.frames(2)
    assert gb.u8("state") == ST_PLAY


def test_pause_ignored_while_dying_and_boss_dead(gb):
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_FREEZE)
    px, py = gb.u8("player_x"), gb.u8("player_y")
    put(gb, P_BULLET, 1, px + 4, py + 4)
    gb.frames(2)
    assert gb.u8("play_sub") == PS_DYING
    gb.tap("start")
    assert gb.u8("state") == ST_PLAY
    gb.frames(40)
    to_boss(gb)
    gb.write_u8("boss_hp", 1)
    gb.pyboy.button_press("a")
    for _ in range(200):
        gb.frames(1)
        if gb.u8("boss_state") == BOSS_DEAD:
            break
    gb.pyboy.button_release("a")
    gb.tap("start")
    gb.frames(2)
    assert gb.u8("state") == ST_PLAY


def test_pause_right_after_bomb_shows_normal_palette(gb):
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_INVINCIBLE)
    gb.frames(130)
    gb.pyboy.button_press("b")
    gb.frames(2)
    gb.pyboy.button_release("b")
    assert gb.u8("bomb_timer") > 0
    gb.pyboy.button_press("start")
    gb.frames(1)
    gb.pyboy.button_release("start")
    gb.frames(20)
    assert gb.u8("state") == ST_PAUSE
    assert gb.io(0xFF47) == 0xE4, hex(gb.io(0xFF47))


def test_start_during_fade_in_is_ignored(title):
    """Mash Start on TITLE through the transition: one game starts, no pause on the first frames."""
    for _ in range(80):
        title.pyboy.button_press("start")
        title.frames(1)
        title.pyboy.button_release("start")
        title.frames(1)
    st = title.u8("state")
    assert st in (ST_PLAY, ST_PAUSE)
    # a mash after the fade may pause: unpause, the game must be a fresh one
    if st == ST_PAUSE:
        title.tap("start")
        title.frames(2)
    assert title.u8("state") == ST_PLAY
    assert title.u8("lives") == 3 and title.u8("continues") == 3


# ------------------------------------------------------------------ CONTINUAR (ui.md 5)

def _to_continue(gb):
    isolate(gb, CHEAT_NO_LEVEL)
    gb.write_u8("lives", 1)
    die(gb)
    assert wait_state(gb, ST_CONTINUE, 60)
    for _ in range(40):                                          # until the count starts
        if gb.u8("screen_sub") == 1:
            break
        gb.frames(1)


def test_continue_count_one_digit_per_60_frames(gb):
    _to_continue(gb)
    changes, last, f = [], gb.u8("count_n"), 0
    for f in range(900):
        gb.frames(1)
        if gb.u8("state") != ST_CONTINUE:
            break
        c = gb.u8("count_n")
        if c != last:
            changes.append(f)
            last = c
    gaps = [b - a for a, b in zip(changes, changes[1:])]
    assert all(g == 60 for g in gaps), (changes, gaps)
    assert f <= 16 + 600 + 20, f


def test_continue_start_accepted_late_in_count(gb):
    _to_continue(gb)
    gb.frames(256 + 20)                                           # timer wrapped, t ~ 20
    assert gb.u8("state") == ST_CONTINUE
    gb.tap("start")
    assert wait_state(gb, ST_PLAY, 80), "Start ignored on CONTINUAR"


# ------------------------------------------------------------------ CLEAR bonus (ui.md 7)

def _boss_kill_to_clear(gb, bombs, died):
    to_boss(gb)
    gb.write_bytes("pool", [0] * (33 * 16))       # a late enemy still on screen would score too
    gb.write_u8("bombs", bombs)
    gb.write_u8("died_in_stage", died)
    gb.write_u8("extends", 3)
    set_bcd(gb, 0)
    gb.write_u8("boss_hp", 1)
    gb.pyboy.button_press("a")
    for _ in range(200):
        gb.frames(1)
        if gb.u8("boss_state") >= BOSS_DEAD:
            break
    gb.pyboy.button_release("a")
    assert bcd(gb) == 20000
    assert wait_state(gb, ST_CLEAR, 700)


def test_clear_bonus_count_full(gb):
    _boss_kill_to_clear(gb, bombs=3, died=0)
    gb.frames(10)
    assert gb.bg_map()[4][9] == T_DIGIT0 + 3
    assert gb.bg_map()[6][12:17] == [T_DIGIT0 + d for d in (1, 0, 0, 0, 0)]
    for _ in range(260):
        gb.frames(1)
        if gb.u8("screen_sub") == 2:
            break
    assert gb.u8("screen_sub") == 2
    assert bcd(gb) == 20000 + 3 * 2000 + 10000
    gb.frames(2)
    assert gb.bg_map()[8][11:17] == [T_DIGIT0 + int(c) for c in "036000"]
    assert gb.bg_map()[4][9] == T_DIGIT0 and gb.bg_map()[6][12:17] == [T_DIGIT0] * 5
    assert bcd(gb, "hiscore") >= 36000


def test_clear_no_death_bonus_only_if_no_death(gb):
    _boss_kill_to_clear(gb, bombs=0, died=1)
    for _ in range(200):
        gb.frames(1)
        if gb.u8("screen_sub") == 2:
            break
    assert bcd(gb) == 20000


def test_clear_start_skips_count_with_same_total(gb):
    _boss_kill_to_clear(gb, bombs=2, died=0)
    for _ in range(40):                                           # 30 f wait + ~7 f of counting
        gb.frames(1)
        if gb.u8("screen_sub") == 1 and gb.u8("screen_timer") >= 7:
            break
    gb.tap("start")
    gb.frames(3)
    assert gb.u8("screen_sub") == 2
    assert bcd(gb) == 20000 + 2 * 2000 + 10000, bcd(gb)


def test_clear_start_skip_frame_budget(gb):
    """The skip runs up to 180 add_score in one frame: it must not lose a frame (255)."""
    _boss_kill_to_clear(gb, bombs=4, died=0)
    for _ in range(40):
        gb.frames(1)
        if gb.u8("screen_sub") == 1:
            break
    gb.write_u8("max_frame_lines", 0)
    gb.tap("start")
    gb.frames(3)
    print("CLEAR skip max_frame_lines", gb.u8("max_frame_lines"))
    assert gb.u8("max_frame_lines") < 255


# ------------------------------------------------------------------ second game (resets)

def _fresh_game_checks(gb):
    assert gb.u8("state") == ST_PLAY and gb.u8("play_sub") == PS_NORMAL
    assert gb.u16("scroll_y") < 60
    assert gb.u8("boss_state") == 0 and gb.u8("obj_ptr") <= 1
    assert (gb.u8("lives"), gb.u8("bombs"), gb.u8("power"), gb.u8("continues")) == (3, 2, 1, 3)
    assert bcd(gb) == 0 and gb.u8("died_in_stage") == 0 and gb.u8("extends") == 0
    assert gb.u8("player_inv") == 0 and gb.u8("bomb_timer") == 0 and gb.u8("no_fire") == 0
    assert gb.u8("boss_bar_on") == 0 and gb.u8("bgp_below_on") == 0
    assert gb.u8("scx_shadow") == 0 and gb.io(0xFF43) == 0
    assert gb.u8("hud_cut") == 1
    assert gb.io(0xFF47) == 0xE4
    assert gb.io(0xFF40) & 0x02, "sprites off in the new game"
    fm = gb.bytes("fm_left", 4)
    assert fm == [0, 0, 0, 0]
    assert live(gb, 0, 33) == []
    assert check_screen(gb) == []
    oam = gb.oam()
    assert oam[0][0] == gb.u8("player_y") and oam[0][1] == gb.u8("player_x")


def _back_to_title_and_start(gb, frames=400):
    assert wait_state(gb, ST_TITLE, frames)
    gb.frames(20)
    gb.tap("start")
    assert wait_state(gb, ST_PLAY, 120)


def test_second_game_after_gameover_in_boss_fight(gb):
    """Die in the boss fight without continues -> GAMEOVER -> TITLE -> a new game starts clean."""
    to_boss(gb)
    gb.frames(40)
    gb.write_u8("cheat_flags", 0)
    gb.write_u8("lives", 1)
    gb.write_u8("continues", 0)
    gb.write_u8("bombs", 3)
    gb.write_u8("power", 3)
    set_bcd(gb, 4560)
    die(gb)
    assert wait_state(gb, ST_GAMEOVER, 120)
    _back_to_title_and_start(gb)
    gb.frames(4)
    _fresh_game_checks(gb)
    assert bcd(gb, "hiscore") == 4560
    # play on: the first wave appears, the boss does not start, the HUD is the normal one
    gb.write_u8("cheat_flags", CHEAT_INVINCIBLE)
    gb.frames(300)
    assert gb.u8("boss_state") == 0 and gb.u8("obj_ptr") >= 1
    assert check_screen(gb) == []
    gb.screenshot("qa_second_game")


def test_second_game_after_continue_then_gameover(gb):
    """Use a continue (CONTINUAR screen, window full screen, OBJ off) then GAMEOVER via the count."""
    isolate(gb, CHEAT_NO_LEVEL)
    gb.write_u8("lives", 1)
    die(gb)
    assert wait_state(gb, ST_CONTINUE, 60)
    gb.frames(60)
    gb.tap("start")
    assert wait_state(gb, ST_PLAY, 80)
    gb.write_u8("lives", 1)
    gb.write_u8("player_inv", 0)
    gb.frames(30)
    die(gb)
    assert wait_state(gb, ST_CONTINUE, 60)
    assert wait_state(gb, ST_GAMEOVER, 1200)                      # let the count run out
    _back_to_title_and_start(gb)
    gb.frames(4)
    _fresh_game_checks(gb)


def test_second_game_after_clear(gb):
    to_boss(gb)
    gb.write_u8("boss_hp", 1)
    gb.pyboy.button_press("a")
    for _ in range(200):
        gb.frames(1)
        if gb.u8("boss_state") >= BOSS_DEAD:
            break
    gb.pyboy.button_release("a")
    assert wait_state(gb, ST_CLEAR, 700)
    gb.frames(60)
    gb.tap("start")                                               # skip the count
    gb.frames(40)
    gb.tap("start")                                               # leave
    _back_to_title_and_start(gb)
    gb.frames(4)
    _fresh_game_checks(gb)
    assert bcd(gb, "hiscore") >= 20000
    gb.write_u8("cheat_flags", CHEAT_INVINCIBLE)
    gb.frames(300)
    assert check_screen(gb) == []


def test_boss_death_erases_boss_rows_to_fog(gb):
    """GDD 11 Jefe: after the death the boss rows are NIEBLA in VRAM (and SCX back to 0)."""
    to_boss(gb)
    gb.write_u8("boss_hp", 1)
    gb.pyboy.button_press("a")
    for _ in range(200):
        gb.frames(1)
        if gb.u8("boss_state") >= BOSS_DEAD:
            break
    gb.pyboy.button_release("a")
    for _ in range(200):
        gb.frames(1)
        if gb.u8("boss_state") == BOSS_OUTRO:
            break
    gb.frames(10)
    fog = MT_ID["MT_FOG"]
    overrides = {(c, r): fog for r in range(188, 194) for c in range(10)}
    assert check_screen(gb, overrides=overrides) == []
    assert gb.io(0xFF43) == 0
    gb.screenshot("qa_boss_erased")


# ------------------------------------------------------------------ bomb at the peak (budget)

def test_bomb_at_peak_keeps_frame_budget(gb):
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_INVINCIBLE)
    gb.frames(130)
    gb.write_u8("bombs", 2)
    for k in range(12):
        put_full(gb, P_BULLET + k, 1, 12 + k * 12, 30 + (k & 3) * 8, vy=0x0100, tile=18)
    for k in range(6):
        put_full(gb, P_ENEMY + k, OBJ_SWOOP, 16 + k * 24, 40, vy=0x0040, hp=4, tile=38)
    sy = gb.u16("scroll_y")
    for k in range(4):
        row = (sy + 144 - (40 + k * 20)) // 16
        put_full(gb, P_TURRET + k, 1, 8 + (k * 2 + 1) * 16, 0, s=0, tm=90, hp=6)
        gb.write_bytes("pool", [k * 2 + 1], (P_TURRET + k) * 16 + 11)
        gb.write_bytes("pool", [row & 255], (P_TURRET + k) * 16 + 15)
    gb.pyboy.button_press("a")
    gb.frames(3)
    gb.write_u8("max_frame_lines", 0)
    gb.tap("b")
    gb.frames(2)
    gb.pyboy.button_release("a")
    print("bomb frame max lines", gb.u8("max_frame_lines"))
    assert gb.u8("max_frame_lines") < 120


# ------------------------------------------------------------------ patterns and enemies (GDD 2.5-2.8)

def _dir_table(gb):
    """{(vx, vy) 16-bit: (spd, dir)} from the ROM tables aim_vx/aim_vy (128 int16 each)."""
    m = gb.pyboy.memory
    ax, ay = gb.addr("aim_vx"), gb.addr("aim_vy")
    out = {}
    for i in range(128):
        vx = m[ax + 2 * i] | m[ax + 2 * i + 1] << 8
        vy = m[ay + 2 * i] | m[ay + 2 * i + 1] << 8
        out[(vx, vy)] = (i >> 5, i & 31)
    return out


def _bullet_dirs(gb, table):
    raw = gb.bytes("pool", 12 * 16)
    dirs = []
    for b in range(12):
        r = raw[b * 16:b * 16 + 16]
        if r[0]:
            dirs.append(table[(r[5] | r[6] << 8, r[7] | r[8] << 8)])
    return dirs


def test_swoop_fan_3_step_2_speed_125(gb):
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_INVINCIBLE)
    gb.write_u8("player_x", 40)
    gb.write_u8("player_y", 136)
    _stopped_swoop(gb)
    for _ in range(40):
        gb.frames(1)
        if live(gb, P_BULLET, 12):
            break
    dirs = _bullet_dirs(gb, _dir_table(gb))
    assert len(dirs) == 3 and {s for s, d in dirs} == {1}, dirs
    ds = sorted(d for s, d in dirs)
    assert ds[1] - ds[0] == 2 and ds[2] - ds[1] == 2, ds
    # aimed: from (72, 56) to (40, 136) -> down-left, ~dir 2-4 (0 = down, 8 = left)
    assert 1 <= ds[1] <= 5, ds


def test_fan_with_pool_almost_full_does_not_corrupt(gb):
    """11 bullets alive: a FAN(3) only gets 1 out, the other records are untouched."""
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_INVINCIBLE)
    gb.write_u8("player_x", 40)
    gb.write_u8("player_y", 136)
    for k in range(11):
        put_full(gb, P_BULLET + k, 1, 10 + k * 13, 150, tile=18)      # parked low, v = 0
    before = [rec(gb, P_BULLET + k) for k in range(11)]
    _stopped_swoop(gb)
    for _ in range(40):
        gb.frames(1)
        if len(live(gb, P_BULLET, 12)) == 12:
            break
    gb.frames(2)
    assert len(live(gb, P_BULLET, 12)) == 12
    after = [rec(gb, P_BULLET + k) for k in range(11)]
    assert after == before


@pytest.mark.parametrize("t,points,tile", [(1, 100, 22), (2, 150, 30), (4, 400, 38), (6, 800, 46),
                                           (7, 800, 46)])
def test_enemy_points_and_carrier_items(gb, t, points, tile):
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_INVINCIBLE)
    gb.write_u8("extends", 3)
    set_bcd(gb, 0)
    gb.write_u8("player_x", 72)
    put_full(gb, P_ENEMY, t, 72, 40, s=0x80 if t == 4 else 0, hp=1, tile=tile)
    if t == 2:                                  # WAVE: x = x0 + sine; sit on the crest (t ~ 22-38)
        put_full(gb, P_ENEMY, t, 72, 40, tm=16, hp=1, tile=tile)
        gb.write_bytes("pool", [48], P_ENEMY * 16 + 11)
    gb.pyboy.button_press("a")
    for _ in range(40):
        gb.frames(1)
        if rec(gb, P_ENEMY)[0] != t:
            break
    gb.pyboy.button_release("a")
    gb.frames(1)
    assert bcd(gb) == points
    item = rec(gb, 18)[0]
    assert item == {6: 30, 7: 31}.get(t, 0), item


def test_turret_points_500(gb):
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_INVINCIBLE)
    gb.write_u8("extends", 3)
    set_bcd(gb, 0)
    put_turret(gb, 50, tm=200)
    gb.write_bytes("pool", [1], P_TURRET * 16 + 14)               # 1 HP
    gb.write_u8("player_x", 72)
    gb.pyboy.button_press("a")
    for _ in range(40):
        gb.frames(1)
        if not rec(gb, P_TURRET)[0]:
            break
    gb.pyboy.button_release("a")
    assert rec(gb, P_TURRET)[0] == 0
    assert bcd(gb) == 500


def test_dart_route_dives_and_drifts_to_player(gb):
    """DART: down at 1.5 px/f; below screen y 32 it drifts 0.25 px/f toward the player's x."""
    isolate(gb, CHEAT_NO_LEVEL | CHEAT_INVINCIBLE)
    gb.write_u8("player_x", 120)
    put_full(gb, P_ENEMY, OBJ_DART, 40, 0, vy=0x0180, hp=1, tile=22)
    gb.frames(20)
    r = rec(gb, P_ENEMY)
    assert 28 <= r[3] <= 32 and r[1] == 40                         # 20 x 1.5 = 30, no drift yet
    gb.frames(40)
    r = rec(gb, P_ENEMY)
    assert r[1] > 40 and r[1] - 40 <= 10, r[1]                     # drifting right, ~0.25 px/f


def test_boss_spiral_12_bullets(gb):
    to_boss(gb)
    gb.write_u8("cheat_flags", CHEAT_INVINCIBLE)
    gb.write_u8("player_x", 8)                                      # stay out of the shots
    gb.write_u8("boss_hp", 100)
    gb.write_u8("boss_phase", 2)
    gb.write_u8("boss_t", 0)
    gb.write_u8("boss_spiral", 0)
    fired = 0
    for _ in range(101):                           # t = 1, 9 .. 89 (the first one right away)
        before = gb.u8("boss_spiral")
        gb.frames(1)
        fired += ((gb.u8("boss_spiral") - before) & 255) // 5
    assert fired == 12, fired


# ------------------------------------------------------------------ wave script vs the 6-slot pool

def test_lint_lifetimes_match_the_rom_routes():
    """The lint's lifetimes are the GDD approximations; the routes in the ROM live longer:
    spawn at OAM Y 0, freed at Y >= 176 -> 176 / vy frames."""
    from test_level_lint import FLYERS
    measured = {"d": 176 / 1.5, "w": 176 / 0.75, "f": 176 / 0.75, "c": 176 / 0.75, "e": 176 / 0.75}
    short = {k: (FLYERS[k][2], round(v)) for k, v in measured.items() if FLYERS[k][2] < v - 5}
    print("lint lifetime vs route (f):", short)
    if short:
        pytest.xfail(f"BUG (lint): lifetimes shorter than the real routes {short}; with the real "
                     "ones the script needs 7 slots at row 36 (see test_no_spawn_dropped_without_shooting)")


def test_no_spawn_dropped_without_shooting(gb):
    gb.write_u8("cheat_flags", CHEAT_INVINCIBLE)
    prev_fm, prev_full, drops = sum(gb.bytes("fm_left", 4)), False, []
    for f in range(6000):
        gb.frames(1)
        raw = gb.bytes("pool", 18 * 16)
        full = all(raw[i * 16] for i in range(P_ENEMY, P_ENEMY + 6))
        fm = sum(gb.bytes("fm_left", 4))
        if fm < prev_fm and prev_full:
            drops.append((f, (gb.u16("scroll_y") + 144) // 16))
        prev_fm, prev_full = fm, full
        if gb.u8("boss_state"):
            break
    assert drops == [], f"spawns lost (frame, row): {drops}"


def test_boss_flashes_when_hit_for_both_parities(gb):
    to_boss(gb)
    gb.write_u8("cheat_flags", CHEAT_INVINCIBLE)
    gb.write_u8("boss_hp", 200)
    results = []
    for parity in (0, 1):
        if parity:
            gb.write_u8("boss_t", (gb.u8("boss_t") + 1) & 255)
        gb.pyboy.button_press("a")
        flashes, hits, last = 0, 0, gb.u8("boss_hp")
        for f in range(160):
            gb.write_u8("player_x", (72 + gb.s8("boss_dx")) & 255)
            gb.write_u8("player_y", 90 + (f // 20) * 5)
            gb.frames(1)
            flashes += gb.u8("bgp_below_on")
            h = gb.u8("boss_hp")
            hits += h < last
            last = h
        gb.pyboy.button_release("a")
        gb.frames(10)
        results.append((hits, flashes))
    assert all(h > 10 for h, _ in results), results
    assert all(fl > 0 for _, fl in results), results
