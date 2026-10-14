import random

TITLE, PLAY, CLEARING, REDRAW, PAUSE, CURTAIN, GAMEOVER = range(7)
I, J, L, O, S, T, Z = range(7)
W, H = 10, 18
BLANK, WALL, BLOCK = 0, 1, 2


def s8(v):
    return v - 256 if v > 127 else v


def num(gb, name, n):
    if name == "score":                         # packed BCD, little-endian, 3 bytes
        return int("".join(f"{b:02X}" for b in reversed(gb.bytes("score", 3))))
    return int("".join(map(str, gb.bytes(name, n))))


def start(gb):
    gb.tap("start")
    gb.frames(2)
    assert gb.u8("state") == PLAY


def set_board(gb, rows):
    """rows: dict row -> string of 10 chars, '#' = block, '.' = empty."""
    base = gb.addr("board")
    for r, line in rows.items():
        for c, ch in enumerate(line):
            gb.pyboy.memory[base + r * W + c] = BLOCK if ch == "#" else BLANK
        mark_row(gb, r)


def mark_row(gb, r):
    """Same as the game's mark_row(): flag the row and append it to the dirty FIFO."""
    mem = gb.pyboy.memory
    flag = gb.addr("row_dirty") + r
    if mem[flag]:
        return
    mem[flag] = 1
    slot = (gb.u8("dirty_head") + gb.u8("dirty_count")) % H
    mem[gb.addr("dirty_list") + slot] = r
    gb.write_u8("dirty_count", gb.u8("dirty_count") + 1)


def set_piece(gb, kind, rot, x, y):
    gb.write_u8("piece_type", kind)
    gb.write_u8("piece_rot", rot)
    gb.write_u8("piece_x", x & 0xFF)
    gb.write_u8("piece_y", y & 0xFF)


def wait_play(gb, max_frames=120):
    for _ in range(max_frames):
        if gb.u8("state") in (PLAY, GAMEOVER, CURTAIN):
            return
        gb.frames(1)


def test_title_screen(gb):
    assert gb.u8("state") == TITLE
    gb.screenshot("title")


def test_level_select(gb):
    gb.tap("right")
    gb.tap("right")
    gb.tap("left")
    assert gb.u8("start_level") == 1
    start(gb)
    assert gb.u8("level") == 1


def test_start_spawns_piece(gb):
    start(gb)
    assert gb.u8("piece_type") < 7
    assert gb.u8("next_type") < 7
    assert s8(gb.u8("piece_x")) == 3
    assert num(gb, "score", 6) == 0
    gb.screenshot("playing")


def test_bag_gives_each_piece_once_per_7(gb):
    start(gb)
    seen = []
    side = ["left", "right"]
    for i in range(14):
        seen.append(gb.u8("piece_type"))
        gb.hold(side[i % 2], 30 + (i % 4) * 4)   # spread pieces so the stack stays low
        gb.tap("up")
        wait_play(gb)
        assert gb.u8("state") == PLAY, f"topped out after {i + 1} pieces"
    assert sorted(seen[:7]) == list(range(7))
    assert sorted(seen[7:]) == list(range(7))


def test_move_and_wall(gb):
    start(gb)
    set_piece(gb, T, 0, 3, 0)
    gb.tap("left")
    assert s8(gb.u8("piece_x")) == 2
    gb.hold("left", 60)                         # auto-repeat reaches the wall
    assert s8(gb.u8("piece_x")) == 0
    gb.hold("right", 120)
    assert s8(gb.u8("piece_x")) == W - 3


def test_rotation_cw_ccw(gb):
    start(gb)
    set_piece(gb, T, 0, 3, 2)
    gb.tap("a")
    assert gb.u8("piece_rot") == 1
    gb.tap("b")
    gb.tap("b")
    assert gb.u8("piece_rot") == 3


def test_wall_kick_i_piece_at_right_wall(gb):
    start(gb)
    set_piece(gb, I, 1, 7, 4)                   # vertical I in the rightmost column (box x+2 = 9)
    gb.tap("a")                                 # R->2 needs a kick to the left
    assert gb.u8("piece_rot") == 2
    assert s8(gb.u8("piece_x")) <= 6


def test_gravity(gb):
    start(gb)
    y = s8(gb.u8("piece_y"))
    gb.frames(60)                               # level 0: 53 frames per row
    assert s8(gb.u8("piece_y")) == y + 1


def test_soft_drop_scores(gb):
    start(gb)
    gb.hold("down", 21)
    assert s8(gb.u8("piece_y")) >= 8
    assert num(gb, "score", 6) >= 8


def test_hard_drop_locks_and_spawns_next(gb):
    start(gb)
    nxt = gb.u8("next_type")
    gb.tap("up")
    wait_play(gb)
    assert gb.u8("piece_type") == nxt
    assert num(gb, "score", 6) > 0
    assert any(gb.bytes("board", W * H)[W * (H - 2):])   # something landed at the bottom


def test_lock_delay(gb):
    start(gb)
    set_board(gb, {H - 1: "#########."})
    set_piece(gb, O, 0, 3, H - 3)               # O (box rows 0-1) resting on row 17
    gb.frames(20)
    assert s8(gb.u8("piece_y")) == H - 3        # still the same piece, not locked yet
    board = gb.bytes("board", W * H)
    assert board[(H - 2) * W + 4] == BLANK
    gb.frames(20)                               # 30 frame lock delay expired
    board = gb.bytes("board", W * H)
    assert board[(H - 2) * W + 4] == BLOCK + O  # locked into the board


def test_single_line_clear(gb):
    start(gb)
    set_board(gb, {H - 1: "######...."})
    set_piece(gb, I, 0, 6, 0)                   # horizontal I fills columns 6-9
    gb.tap("up")
    wait_play(gb)
    assert num(gb, "lines", 3) == 1
    assert num(gb, "score", 6) >= 40
    assert gb.bytes("board", W * H)[W * (H - 1):] == [BLANK] * W


def test_tetris_scores_1200(gb):
    start(gb)
    set_board(gb, {r: "#########." for r in range(H - 4, H)})
    set_piece(gb, I, 1, 7, 0)                   # vertical I in column 9
    gb.tap("up")
    gb.frames(10)
    assert gb.u8("state") == CLEARING
    oam = gb.addr("shadow_OAM")
    assert all(gb.pyboy.memory[oam + 4 * i] == 0 for i in range(4)), "locked piece still drawn as sprites"
    gb.screenshot("tetris_flash")
    wait_play(gb)
    assert num(gb, "lines", 3) == 4
    assert 1200 <= num(gb, "score", 6) < 1300   # 1200 + hard drop points
    assert gb.bytes("board", W * H) == [BLANK] * (W * H)


def test_tetris_at_level_9_and_hard_drop_points(gb):
    for _ in range(9):
        gb.tap("right")
    start(gb)
    assert gb.u8("level") == 9
    set_board(gb, {r: "#########." for r in range(H - 4, H)})
    set_piece(gb, I, 1, 7, 0)                   # vertical I occupies box rows 0-3 -> drops 14 rows
    gb.tap("up")
    wait_play(gb)
    assert num(gb, "score", 6) == 1200 * 10 + 14 * 2


def test_score_saturates_at_999999(gb):
    start(gb)
    gb.pyboy.memory[gb.addr("score")] = 0x90     # 999990
    gb.pyboy.memory[gb.addr("score") + 1] = 0x99
    gb.pyboy.memory[gb.addr("score") + 2] = 0x99
    set_board(gb, {H - 1: "######...."})
    set_piece(gb, I, 0, 6, 0)
    gb.tap("up")
    wait_play(gb)
    assert num(gb, "score", 6) == 999999


def test_level_up_after_10_lines(gb):
    start(gb)
    for _ in range(3):
        set_board(gb, {r: "#########." for r in range(H - 4, H)})
        set_piece(gb, I, 1, 7, 0)
        gb.tap("up")
        wait_play(gb)
    assert num(gb, "lines", 3) == 12
    assert gb.u8("level") == 1


def test_pause(gb):
    start(gb)
    gb.tap("start")
    assert gb.u8("state") == PAUSE
    y = gb.u8("piece_y")
    gb.frames(120)
    assert gb.u8("piece_y") == y
    gb.tap("start")
    assert gb.u8("state") == PLAY


def test_game_over_and_back_to_title(gb):
    start(gb)
    set_board(gb, {r: "#########." for r in range(2, H)})
    gb.tap("up")                                # locks at the top, next piece cannot spawn
    gb.frames(60)
    assert gb.u8("state") == GAMEOVER
    gb.screenshot("game_over")
    gb.tap("start")
    gb.frames(2)
    assert gb.u8("state") == TITLE


def vram_well(gb):
    return [gb.pyboy.memory[0x9800 + r * 32 + 2 + c] for r in range(H) for c in range(W)]


def test_vram_matches_board_after_play(gb):
    """End-to-end check of the asm row copy: what is on screen equals the board in RAM."""
    rng = random.Random(7)
    start(gb)
    for i in range(40):
        if gb.u8("state") != PLAY:
            break
        if i % 5 == 0:   # force line clears now and then
            set_board(gb, {r: "#########." for r in range(H - 4, H)})
            set_piece(gb, I, 1, 7, 0)
        else:
            gb.hold(rng.choice(["left", "right"]), rng.randrange(1, 30))
        gb.tap("up")
        wait_play(gb)
        gb.frames(6)     # let pending rows reach VRAM
        assert vram_well(gb) == gb.bytes("board", W * H), f"mismatch after piece {i}"
    assert num(gb, "lines", 3) >= 4
    assert gb.u8("vram_late") == 0


def test_frame_budget_random_play(gb):
    """Random but sensible play for a few thousand frames, including line clears."""
    rng = random.Random(1)
    start(gb)
    for _ in range(400):
        st = gb.u8("state")
        if st == GAMEOVER:
            gb.tap("start")
            gb.frames(2)
            gb.tap("start")
            continue
        if st != PLAY:
            gb.frames(1)
            continue
        for _ in range(rng.randrange(4)):
            gb.tap("a")
        gb.hold(rng.choice(["left", "right"]), rng.randrange(1, 40))
        gb.tap("up")
    worst = gb.u8("max_frame_lines")
    print(f"worst frame: {worst}/154 scanlines, lines {num(gb, 'lines', 3)}, score {num(gb, 'score', 6)}")
    gb.screenshot("random_play")
    assert gb.u8("vram_late") == 0, "VRAM writes ran past VBlank (tiles lost)"
    assert worst != 255, "a frame overran"
    assert worst < 120, "less than 20% headroom left"


def test_frame_budget_tetris_at_level_20(gb):
    """Worst case for a single frame: 4-line collapse + score x21 + HUD."""
    start(gb)
    gb.write_u8("level", 20)
    for _ in range(3):
        set_board(gb, {r: "#########." for r in range(H - 4, H)})
        set_piece(gb, I, 1, 7, 0)
        gb.tap("up")
        wait_play(gb)
    worst = gb.u8("max_frame_lines")
    print(f"worst frame (level 20 tetris): {worst}/154 scanlines")
    assert gb.u8("vram_late") == 0
    assert worst < 120
