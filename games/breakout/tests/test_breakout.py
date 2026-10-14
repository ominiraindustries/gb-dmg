TITLE, SERVE, PLAY, GAMEOVER, CLEAR = range(5)
PADDLE_Y = 132
BRICK_COUNT = 54


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def score(gb):
    return int("".join(map(str, gb.bytes("score", 5))))


def start_game(gb):
    gb.tap("start")
    gb.frames(10)  # brick rows are redrawn one per frame
    assert gb.u8("state") == SERVE


def place_ball(gb, x, y, vx, vy):
    gb.write_u8("state", PLAY)
    gb.write_u16("ball_x", x << 8)
    gb.write_u16("ball_y", y << 8)
    gb.write_u16("ball_vx", vx & 0xFFFF)
    gb.write_u16("ball_vy", vy & 0xFFFF)


def test_title_screen(gb):
    assert gb.u8("state") == TITLE
    assert gb.u8("bricks_left") == BRICK_COUNT
    gb.screenshot("title")


def test_start_serves_with_full_lives(gb):
    start_game(gb)
    assert gb.u8("lives") == 3
    assert score(gb) == 0
    gb.screenshot("serve")


def test_ball_follows_paddle_while_serving(gb):
    start_game(gb)
    gb.hold("left", 20)
    paddle = gb.u8("paddle_x")
    assert paddle < 64
    assert gb.u16("ball_x") >> 8 == paddle + 10


def test_paddle_stays_inside_walls(gb):
    start_game(gb)
    gb.hold("left", 100)
    assert gb.u8("paddle_x") == 8
    gb.hold("right", 100)
    assert gb.u8("paddle_x") == 152 - 24


def test_launch_sends_ball_up(gb):
    start_game(gb)
    gb.tap("a")
    assert gb.u8("state") == PLAY
    y = gb.u16("ball_y")
    gb.frames(10)
    assert gb.u16("ball_y") < y


def test_wall_bounce(gb):
    start_game(gb)
    place_ball(gb, 9, 100, -0x100, -0x80)
    gb.frames(4)
    assert s16(gb.u16("ball_vx")) > 0


def test_paddle_bounce_angle_depends_on_hit_zone(gb):
    start_game(gb)
    paddle = gb.u8("paddle_x")
    place_ball(gb, paddle - 2, PADDLE_Y - 8, 0, 0x140)  # left edge
    gb.frames(6)
    assert s16(gb.u16("ball_vy")) < 0
    assert s16(gb.u16("ball_vx")) < -0x100
    place_ball(gb, paddle + 22, PADDLE_Y - 8, 0, 0x140)  # right edge
    gb.frames(6)
    assert s16(gb.u16("ball_vy")) < 0
    assert s16(gb.u16("ball_vx")) > 0x100


def test_breaking_bricks_scores(gb):
    start_game(gb)
    gb.tap("a")
    for _ in range(60):
        gb.frames(10)
        if gb.u8("bricks_left") < BRICK_COUNT:
            break
    assert gb.u8("bricks_left") < BRICK_COUNT
    assert score(gb) > 0
    gb.frames(2)
    gb.screenshot("brick_broken")


def test_losing_ball_costs_a_life(gb):
    start_game(gb)
    gb.write_u8("paddle_x", 8)
    place_ball(gb, 140, 120, 0, 0x200)
    gb.frames(30)
    assert gb.u8("lives") == 2
    assert gb.u8("state") == SERVE


def test_game_over_and_restart(gb):
    start_game(gb)
    gb.write_u8("lives", 1)
    gb.write_u8("paddle_x", 8)
    place_ball(gb, 140, 120, 0, 0x200)
    gb.frames(30)
    assert gb.u8("state") == GAMEOVER
    gb.screenshot("game_over")
    gb.tap("start")
    assert gb.u8("state") == SERVE
    assert gb.u8("lives") == 3
    assert score(gb) == 0


def test_stage_clear_and_next_level(gb):
    start_game(gb)
    gb.write_u8("bricks_left", 1)
    place_ball(gb, 80, 80, 0, -0x140)  # straight up into the bottom brick row
    gb.frames(20)
    assert gb.u8("state") == CLEAR
    gb.screenshot("stage_clear")
    gb.tap("start")
    gb.frames(10)
    assert gb.u8("state") == SERVE
    assert gb.u8("level") == 1
    assert gb.u8("bricks_left") == BRICK_COUNT


def test_frame_budget_during_autoplay(gb):
    """Bot keeps the paddle under the ball; worst frame must leave plenty of headroom."""
    start_game(gb)
    gb.tap("a")
    for _ in range(3000):
        state = gb.u8("state")
        if state == SERVE:
            gb.tap("a")
        elif state == CLEAR:
            gb.tap("start")
        else:
            x = (gb.u16("ball_x") >> 8) - 10
            gb.write_u8("paddle_x", max(8, min(128, x)))
            gb.frames(1)
    worst = gb.u8("max_frame_lines")
    print(f"worst frame: {worst}/154 scanlines, bricks left {gb.u8('bricks_left')}, "
          f"level {gb.u8('level')}, score {score(gb)}")
    gb.screenshot("autoplay")
    assert worst != 255, "a frame overran"
    assert worst < 100
