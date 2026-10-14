"""GRIFO screens and boss (GDD 4, 2.10; design/ui.md 2-8)."""
from stage_model import STOP_SCROLL, check_screen
from test_mechanics import CHEAT_INVINCIBLE, CHEAT_NO_LEVEL, P_BULLET, isolate, put

ST_TITLE, ST_PLAY, ST_PAUSE, ST_CONTINUE, ST_GAMEOVER, ST_CLEAR = range(6)
BOSS_NONE, BOSS_INTRO, BOSS_FIGHT, BOSS_DEAD, BOSS_OUTRO = range(5)
T_DIGIT0, T_A = 24, 34


def word(s):
    return [T_A + ord(c) - 65 if c != " " else 0 for c in s]


def wait_state(gb, state, frames):
    for _ in range(frames):
        gb.frames(1)
        if gb.u8("state") == state and not gb.u8("trans_phase"):
            return True
    return False


def die(gb):
    px, py = gb.u8("player_x"), gb.u8("player_y")
    put(gb, P_BULLET, 1, px + 4, py + 4)
    gb.frames(40)


def to_boss(gb):
    gb.write_u8("cheat_flags", CHEAT_INVINCIBLE | 0x08)
    gb.write_u16("cheat_scroll", 0x0800)
    for _ in range(600):
        gb.frames(1)
        if gb.u8("boss_state") == BOSS_FIGHT:
            break
    gb.write_u8("cheat_flags", CHEAT_INVINCIBLE)
    assert gb.u8("boss_state") == BOSS_FIGHT


def test_title_screen(title):
    assert title.u8("state") == ST_TITLE
    seen = set()
    for _ in range(70):                                    # "PULSA START" blinks 30/30
        title.frames(1)
        seen.add(tuple(title.bg_map()[10][4:15]))
    assert tuple(word("PULSA START")) in seen and tuple([0] * 11) in seen
    title.screenshot("title")


def test_hud_shows_fase_then_counters(gb):
    win = gb.bg_map(window=True)[0]
    assert win[7:11] == word("FASE")
    gb.frames(130)
    win = gb.bg_map(window=True)[0]
    assert win[8] == T_DIGIT0 + gb.u8("lives") and win[11] == T_DIGIT0 + gb.u8("bombs")
    assert win[14] == T_DIGIT0 + gb.u8("power")


def test_pause_freezes(gb):
    gb.frames(130)
    gb.tap("start")
    gb.frames(3)
    assert gb.u8("state") == ST_PAUSE
    s0 = gb.u16("scroll_y")
    assert gb.bg_map(window=True)[0][7:12] == word("PAUSA")
    gb.frames(60)
    assert gb.u16("scroll_y") == s0
    gb.screenshot("pause")
    gb.tap("start")
    gb.frames(3)
    assert gb.u8("state") == ST_PLAY
    gb.frames(10)
    assert gb.u16("scroll_y") > s0


def test_continue_in_place(gb):
    isolate(gb, CHEAT_NO_LEVEL)
    gb.write_u8("lives", 1)
    gb.write_bytes("score", [0x00, 0x50, 0x00])
    s0 = gb.u16("scroll_y")
    die(gb)
    assert wait_state(gb, ST_CONTINUE, 60)
    gb.frames(50)
    gb.screenshot("continue")
    assert gb.bg_map(window=True)[8][9] in [T_DIGIT0 + d for d in (8, 9)]
    gb.tap("start")
    assert wait_state(gb, ST_PLAY, 80)
    assert gb.u8("lives") == 3 and gb.u8("continues") == 2 and gb.bytes("score", 3) == [0, 0, 0]
    assert gb.u8("play_sub") in (1, 2, 0) and gb.u16("scroll_y") >= s0
    assert gb.bytes("hiscore", 3) == [0x00, 0x50, 0x00]


def test_gameover_without_continues(gb):
    isolate(gb, CHEAT_NO_LEVEL)
    gb.write_u8("lives", 1)
    gb.write_u8("continues", 0)
    die(gb)
    assert wait_state(gb, ST_GAMEOVER, 80)
    gb.frames(20)
    gb.screenshot("gameover")
    assert wait_state(gb, ST_TITLE, 260)


def test_boss_scroll_stop_and_sway(gb):
    to_boss(gb)
    assert gb.u16("scroll_y") == STOP_SCROLL
    xs = set()
    for _ in range(140):
        gb.frames(1)
        xs.add(gb.s8("boss_dx"))
        # SCX shows last frame's -boss_dx: the sway table steps up to 3 px between frames
        assert ((gb.io(0xFF43) + gb.s8("boss_dx") + 3) & 255) <= 6
    assert max(xs) >= 30 and min(xs) <= -30 or max(xs) - min(xs) >= 30
    gb.screenshot("boss")


def test_boss_phase_change_and_death_to_clear(gb):
    to_boss(gb)
    gb.write_u8("boss_hp", 102)
    gb.pyboy.button_press("a")
    for _ in range(300):
        gb.frames(1)
        if gb.u8("boss_phase") == 2:
            break
    assert gb.u8("boss_phase") == 2
    gb.frames(100)
    gb.screenshot("boss_phase_b")
    gb.write_u8("boss_hp", 2)
    for _ in range(300):
        gb.frames(1)
        if gb.u8("boss_state") >= BOSS_DEAD:
            break
    gb.pyboy.button_release("a")
    assert gb.u8("boss_state") >= BOSS_DEAD
    assert wait_state(gb, ST_CLEAR, 600)
    gb.frames(40)
    gb.screenshot("clear_counting")
    for _ in range(300):
        gb.frames(1)
    gb.screenshot("clear_done")
    assert wait_state(gb, ST_TITLE, 400)
