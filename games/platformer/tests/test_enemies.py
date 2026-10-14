"""M1 step 3a: enemies, stomps and chains, damage, ball kick, shots, deaths, lives, checkpoint."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from helpers import DYING, GAMEOVER, PLAY, Y_BIAS, s16, start_play, teleport

T_NONE, T_WALKER, T_SHELL = 0, 1, 2
E_WALK, E_SQUASH, E_FLIP, E_BALL, E_BALL_MOVE = range(5)
FORM_SMALL, FORM_BIG, FORM_SHOT = 0, 1, 2
GROUND_TOP = Y_BIAS + 7 * 16
SMALL_ON_GROUND = GROUND_TOP - 16


def score(gb):
    return int("".join(f"{b:02X}" for b in reversed(gb.bytes("score", 3))))


def actors(gb):
    """(types, states, xs, ys) of the 14 actor slots (0-4 are enemies)."""
    t = gb.bytes("act_type", 14)
    st = gb.bytes("act_state", 14)
    raw = gb.bytes("act_x", 28)
    x = [raw[2 * i] | (raw[2 * i + 1] << 8) for i in range(14)]
    return t, st, x, gb.bytes("act_y", 14)


def place_enemy(gb, slot, kind, x, y=SMALL_ON_GROUND, state=E_WALK, vx=-0x80):
    """Put an enemy directly in slot 0-4."""
    a, m = gb.addr, gb.pyboy.memory
    m[a("act_type") + slot] = kind
    m[a("act_state") + slot] = state
    m[a("act_x") + 2 * slot] = x & 0xFF
    m[a("act_x") + 2 * slot + 1] = x >> 8
    m[a("act_y") + slot] = y
    m[a("act_vx") + 2 * slot] = vx & 0xFF
    m[a("act_vx") + 2 * slot + 1] = (vx >> 8) & 0xFF
    m[a("act_vy") + 2 * slot] = 0
    m[a("act_vy") + 2 * slot + 1] = 0


def clear_enemies(gb):
    for s in range(5):
        gb.pyboy.memory[gb.addr("act_type") + s] = T_NONE
    gb.write_u8("obj_next", 255)                  # stop the level spawner


def setup(gb, x=8 * 16):
    start_play(gb)
    gb.write_u8("cheat_flags", 2)                 # no timer
    clear_enemies(gb)
    teleport(gb, x, SMALL_ON_GROUND)
    gb.frames(30)


def make_form(gb, form):
    gb.write_u8("player_form", form)
    gb.write_u8("hb_y", 4)
    gb.write_u8("hb_h", 28)


def test_enemies_spawn_from_level(gb):
    start_play(gb)
    gb.write_u8("cheat_flags", 3)
    gb.pyboy.button_press("right")
    gb.pyboy.button_press("b")
    for _ in range(300):
        gb.frames(1)
        if T_WALKER in actors(gb)[0][:5]:
            break
    gb.pyboy.button_release("right")
    gb.pyboy.button_release("b")
    assert T_WALKER in actors(gb)[0][:5]          # the Limo of column 22
    gb.screenshot("enemy_spawn")


def test_stomp_walker_and_chain(gb):
    setup(gb)
    s0 = score(gb)
    place_enemy(gb, 0, T_WALKER, 8 * 16 + 2, vx=0)
    teleport(gb, 8 * 16, SMALL_ON_GROUND - 30)    # falling onto it
    gb.write_u16("player_vy", 0x0200)
    gb.frames(8)
    assert actors(gb)[1][0] == E_SQUASH
    assert score(gb) - s0 == 100
    # a second stomp before touching the ground scores 200
    place_enemy(gb, 1, T_WALKER, gb.u16("player_x") + 2, vx=0)
    for _ in range(60):
        gb.frames(1)
        if actors(gb)[1][1] == E_SQUASH:
            break
    assert actors(gb)[1][1] == E_SQUASH
    assert score(gb) - s0 == 300
    gb.screenshot("stomp")


def test_side_hit_shrinks_big_then_kills_small(gb):
    setup(gb)
    make_form(gb, FORM_BIG)
    teleport(gb, 8 * 16, SMALL_ON_GROUND - 16)
    gb.frames(5)
    place_enemy(gb, 0, T_WALKER, 8 * 16 + 12, vx=-0x80)
    gb.frames(10)
    assert gb.u8("player_form") == FORM_SMALL
    assert gb.u8("player_inv") > 0
    gb.frames(150)                                # invulnerability over
    place_enemy(gb, 0, T_WALKER, gb.u16("player_x") + 12, vx=-0x80)
    gb.frames(10)
    assert gb.u8("state") == DYING
    gb.screenshot("death")


def test_shot_form_hit_becomes_big(gb):
    setup(gb)
    make_form(gb, FORM_SHOT)
    teleport(gb, 8 * 16, SMALL_ON_GROUND - 16)
    gb.frames(5)
    place_enemy(gb, 0, T_WALKER, 8 * 16 + 12, vx=-0x80)
    gb.frames(10)
    assert gb.u8("player_form") == FORM_BIG       # decided: SHOT -> BIG


def test_invulnerability_ignores_side_hits(gb):
    setup(gb)
    gb.write_u8("player_inv", 90)
    place_enemy(gb, 0, T_WALKER, 8 * 16 + 12, vx=-0x80)
    gb.frames(10)
    assert gb.u8("state") == PLAY


def test_shell_becomes_ball_and_kick_kills_walker(gb):
    setup(gb)
    place_enemy(gb, 0, T_SHELL, 8 * 16 + 2, vx=0)
    teleport(gb, 8 * 16, SMALL_ON_GROUND - 30)
    gb.write_u16("player_vy", 0x0200)
    gb.frames(8)
    assert actors(gb)[1][0] == E_BALL
    gb.frames(30)                                 # Teo lands
    ball_x = actors(gb)[2][0]
    place_enemy(gb, 1, T_WALKER, ball_x + 64, vx=0)
    teleport(gb, ball_x - 20, SMALL_ON_GROUND)    # walk into the ball from the left
    gb.pyboy.button_press("right")
    for _ in range(30):
        gb.frames(1)
        if actors(gb)[1][0] == E_BALL_MOVE:
            break
    gb.pyboy.button_release("right")
    assert actors(gb)[1][0] == E_BALL_MOVE
    assert s16(gb.u16("act_vx")) > 0              # kicked to the right
    for _ in range(60):
        gb.frames(1)
        if actors(gb)[1][1] == E_FLIP:
            break
    assert actors(gb)[1][1] == E_FLIP, "the moving ball should kill the walker"
    gb.screenshot("ball")


def test_shot_kills_enemy(gb):
    setup(gb)
    make_form(gb, FORM_SHOT)
    teleport(gb, 8 * 16, SMALL_ON_GROUND - 16)
    gb.frames(5)
    place_enemy(gb, 0, T_WALKER, 8 * 16 + 48, vx=0)
    gb.tap("b")
    for _ in range(40):
        gb.frames(1)
        if actors(gb)[1][0] == E_FLIP:
            break
    assert actors(gb)[1][0] == E_FLIP


def test_block_bump_kills_enemy_on_top(gb):
    setup(gb, x=16 * 16)                          # under the rune block of column 16 (row 4)
    place_enemy(gb, 0, T_WALKER, 16 * 16, y=Y_BIAS + 3 * 16, vx=0)   # standing on the block
    gb.pyboy.button_press("a")
    for _ in range(30):
        gb.frames(1)
        if actors(gb)[1][0] == E_FLIP:
            break
    gb.pyboy.button_release("a")
    assert actors(gb)[1][0] == E_FLIP


def test_time_over_kills(gb):
    start_play(gb)
    clear_enemies(gb)
    gb.write_u16("time_units", 1)
    gb.frames(30)
    assert gb.u8("state") == DYING


def test_checkpoint_respawn(gb):
    start_play(gb)
    clear_enemies(gb)
    gb.write_u8("cheat_flags", 3)
    teleport(gb, 101 * 16, SMALL_ON_GROUND)       # past the checkpoint (column 100)
    gb.frames(60)
    assert gb.u8("checkpoint") == 1
    gb.write_u8("cheat_flags", 2)
    clear_enemies(gb)
    teleport(gb, 104 * 16, Y_BIAS + 9 * 16)       # below the level: fell
    gb.frames(150)
    assert gb.u8("state") == PLAY
    assert gb.u16("player_x") == 100 * 16


def test_game_over_when_no_lives(gb):
    start_play(gb)
    clear_enemies(gb)
    gb.write_u8("lives", 1)
    teleport(gb, 69 * 16 + 4, SMALL_ON_GROUND)
    gb.write_u16("camera_x", 60 * 16)
    gb.frames(120)
    assert gb.u8("state") == GAMEOVER


def test_frame_budget_bot(gb):
    """Bot runs and jumps through 1-1 (invincible): GDD budget < 120 lines, no late VRAM."""
    start_play(gb)
    gb.write_u8("cheat_flags", 3)
    rng = random.Random(5)
    gb.pyboy.button_press("right")
    gb.pyboy.button_press("b")
    for f in range(6000):
        if f % 14 == 0:
            gb.pyboy.button_press("a")
        if f % 14 == 6 + rng.randrange(7):
            gb.pyboy.button_release("a")
        gb.frames(1)
        if gb.u16("camera_x") >= 200 * 16 - 160:
            break
    worst = gb.u8("max_frame_lines")
    print(f"bot: x {gb.u16('player_x')}, worst {worst}/154 lines, vram_late {gb.u8('vram_late')}")
    assert gb.u8("vram_late") == 0
    assert worst < 120
