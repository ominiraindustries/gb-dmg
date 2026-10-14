"""QA tests for BLOCKS: exact timings, SRS against an independent reference, scoring table,
lock delay rules, edge cases, bot play with line clears and button mashing.

Tests named test_regression_* reproduce bugs found by QA (all fixed) so they cannot come back.
"""
import random

TITLE, PLAY, CLEARING, REDRAW, PAUSE, CURTAIN, GAMEOVER = range(7)
I, J, L, O, S, T, Z = range(7)
W, H = 10, 18
BLANK, WALL, BLOCK = 0, 1, 2
PANEL_X, WELL_X = 13, 2
TILE_DIGIT0, TILE_A = 9, 19                     # BG_COUNT + FONT_DIGIT0 / FONT_LETTER_A
GRAVITY = [53, 49, 45, 41, 37, 33, 28, 22, 17, 11, 10, 9, 8, 7, 6, 6, 5, 5, 4, 4, 3]


# ------------------------------------------------------------------ helpers

def s8(v):
    return v - 256 if v > 127 else v


def num(gb, name, n):
    if name == "score":
        return int("".join(f"{b:02X}" for b in reversed(gb.bytes("score", 3))))
    return int("".join(map(str, gb.bytes(name, n))))


def start(gb, level=0):
    for _ in range(level):
        gb.tap("right")
    gb.tap("start")
    gb.frames(10)                               # let the title texts be cleared from the well
    assert gb.u8("state") == PLAY
    assert gb.u8("level") == level
    assert gb.u8("text_count") == 0


def mark_row(gb, r):
    mem = gb.pyboy.memory
    flag = gb.addr("row_dirty") + r
    if mem[flag]:
        return
    mem[flag] = 1
    slot = (gb.u8("dirty_head") + gb.u8("dirty_count")) % H
    mem[gb.addr("dirty_list") + slot] = r
    gb.write_u8("dirty_count", gb.u8("dirty_count") + 1)


def set_board(gb, rows, clear=False):
    """rows: dict row -> 10 chars ('#' block, '.' empty). clear=True empties the rest."""
    base = gb.addr("board")
    if clear:
        rows = {r: rows.get(r, "." * W) for r in range(H)}
    for r, line in rows.items():
        for c, ch in enumerate(line):
            gb.pyboy.memory[base + r * W + c] = BLOCK if ch == "#" else BLANK
        mark_row(gb, r)


def set_piece(gb, kind, rot, x, y):
    gb.write_u8("piece_type", kind)
    gb.write_u8("piece_rot", rot)
    gb.write_u8("piece_x", x & 0xFF)
    gb.write_u8("piece_y", y & 0xFF)
    gb.write_u8("lowest_y", max(y, 0) & 0xFF)
    gb.write_u8("gravity_timer", 0)
    gb.write_u8("lock_timer", 0)
    gb.write_u8("lock_resets", 0)


def piece(gb):
    return gb.u8("piece_type"), gb.u8("piece_rot"), gb.s8("piece_x"), gb.s8("piece_y")


def board(gb):
    return gb.bytes("board", W * H)


def wait_play(gb, max_frames=150):
    for _ in range(max_frames):
        if gb.u8("state") in (PLAY, GAMEOVER, CURTAIN):
            return
        gb.frames(1)


def vram_row(gb, x, y, n):
    return [gb.pyboy.memory[0x9800 + y * 32 + x + i] for i in range(n)]


def vram_well(gb):
    return [t for r in range(H) for t in vram_row(gb, WELL_X, r, W)]


def text_tiles(s):
    return [TILE_DIGIT0 + int(c) if c.isdigit() else TILE_A + ord(c) - 65 for c in s]


def oam_y(gb, slot):
    return gb.pyboy.memory[gb.addr("shadow_OAM") + 4 * slot]


# --------------------------------------------- independent SRS reference

SPAWN = {
    I: [(0, 1), (1, 1), (2, 1), (3, 1)],
    J: [(0, 0), (0, 1), (1, 1), (2, 1)],
    L: [(2, 0), (0, 1), (1, 1), (2, 1)],
    O: [(1, 0), (2, 0), (1, 1), (2, 1)],
    S: [(1, 0), (2, 0), (0, 1), (1, 1)],
    T: [(1, 0), (0, 1), (1, 1), (2, 1)],
    Z: [(0, 0), (1, 0), (1, 1), (2, 1)],
}


def ref_cells(kind, rot):
    cells = SPAWN[kind]
    if kind == O:
        return sorted(cells)
    n = 4 if kind == I else 3
    for _ in range(rot):
        cells = [(n - 1 - y, x) for x, y in cells]
    return sorted(cells)


# Wiki SRS tables with y pointing UP, keyed by (from, to)
_KJ = {(0, 1): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
       (1, 0): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
       (1, 2): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
       (2, 1): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
       (2, 3): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
       (3, 2): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
       (3, 0): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
       (0, 3): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)]}
_KI = {(0, 1): [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],
       (1, 0): [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],
       (1, 2): [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)],
       (2, 1): [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],
       (2, 3): [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],
       (3, 2): [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],
       (3, 0): [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],
       (0, 3): [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)]}


def ref_fits(brd, kind, rot, x, y):
    for cx, cy in ref_cells(kind, rot):
        cx += x
        cy += y
        if cx < 0 or cx >= W or cy >= H:
            return False
        if cy >= 0 and brd[cy * W + cx]:
            return False
    return True


def ref_rotate(brd, kind, rot, x, y, cw):
    if kind == O:
        return rot, x, y
    to = (rot + (1 if cw else 3)) & 3
    for dx, dy in (_KI if kind == I else _KJ)[(rot, to)]:
        if ref_fits(brd, kind, to, x + dx, y - dy):      # y up -> y down
            return to, x + dx, y - dy
    return rot, x, y


def game_cells(gb, kind, rot):
    base = gb.addr("shapes") + (kind * 4 + rot) * 4
    return sorted((gb.pyboy.memory[base + i] & 3, gb.pyboy.memory[base + i] >> 2) for i in range(4))


# ------------------------------------------------------------------ spec: pieces and SRS

def test_shape_table_matches_srs_reference(gb):
    for kind in range(7):
        for rot in range(4):
            assert game_cells(gb, kind, rot) == ref_cells(kind, rot), (kind, rot)


def test_srs_rotation_matches_reference_on_random_boards(gb):
    """Random stacks, pieces and positions; every A/B press must land where real SRS says."""
    rng = random.Random(42)
    start(gb)
    checked = kicked = 0
    for _ in range(250):
        rows = {}
        top = rng.randrange(6, H)
        for r in range(H):
            rows[r] = "".join("#" if r >= top and rng.random() < 0.55 else "." for _ in range(W))
        set_board(gb, rows)
        brd = [1 if ch == "#" else 0 for r in range(H) for ch in rows[r]]
        kind, rot = rng.randrange(7), rng.randrange(4)
        spots = [(x, y) for x in range(-2, W) for y in range(-1, H) if ref_fits(brd, kind, rot, x, y)]
        x, y = rng.choice(spots)
        cw = rng.random() < 0.5
        gb.frames(6)                            # let the board rows reach VRAM (not required)
        set_piece(gb, kind, rot, x, y)
        gb.tap("a" if cw else "b")
        want = ref_rotate(brd, kind, rot, x, y, cw)
        got = piece(gb)
        assert got[0] == kind and gb.u8("state") == PLAY
        if want != (rot, x, y) and want[1:] != (x, y):
            kicked += 1
        assert got[1:] == want, f"kind {kind} rot {rot} at ({x},{y}) cw={cw}: got {got[1:]} want {want}"
        checked += 1
    assert kicked >= 20, "too few kicked rotations exercised"


def test_t_floor_kick(gb):
    start(gb)
    set_piece(gb, T, 0, 3, H - 2)               # flat T lying on the floor
    gb.tap("a")                                 # 0->R: tests (0,0),(-1,0) fail, (-1,+1 up) fits
    assert piece(gb) == (T, 1, 2, H - 3)


def test_o_piece_does_not_rotate(gb):
    start(gb)
    set_piece(gb, O, 0, 3, 5)
    gb.tap("a")
    gb.tap("b")
    assert piece(gb) == (O, 0, 3, 5)


def test_bag_49_pieces_each_block_of_7_is_a_permutation(gb):
    start(gb)
    seq = []
    for _ in range(49):
        seq.append(gb.u8("piece_type"))
        set_board(gb, {}, clear=True)
        gb.tap("up")
        wait_play(gb)
        assert gb.u8("state") == PLAY
    for i in range(0, 49, 7):
        assert sorted(seq[i:i + 7]) == list(range(7)), seq
    assert seq[:7] != seq[7:14] or seq[7:14] != seq[14:21], "bag order never changes"


def test_next_preview_shows_next_type(gb):
    start(gb)
    for _ in range(5):
        oam = gb.addr("shadow_OAM")
        for s in range(4, 8):
            assert gb.pyboy.memory[oam + 4 * s + 2] == BLOCK + gb.u8("next_type")
            assert gb.pyboy.memory[oam + 4 * s] >= 16 + 96   # inside the NEXT box (y >= row 12)
        nxt = gb.u8("next_type")
        set_board(gb, {}, clear=True)
        gb.tap("up")
        wait_play(gb)
        assert gb.u8("piece_type") == nxt


# ------------------------------------------------------------------ spec: timings

def test_das_16_then_every_6(gb):
    start(gb)
    set_piece(gb, T, 0, 0, 2)
    gb.pyboy.button_press("right")
    xs = []
    for _ in range(60):
        gb.frames(1)
        xs.append(gb.s8("piece_x"))
    gb.pyboy.button_release("right")
    changes = [i for i in range(len(xs)) if xs[i] != (xs[i - 1] if i else 0)]
    assert changes[0] <= 1, "first step must happen right on the press"
    intervals = [b - a for a, b in zip(changes, changes[1:])]
    # PyBoy ticks end at LY 0, ~10 lines into the game's update(): a sample can be 1 frame off
    assert len(intervals) == 6, f"x per frame {xs}"
    assert all(abs(a - b) <= 1 for a, b in zip(intervals, [16, 6, 6, 6, 6, 6])), f"x per frame {xs}"
    assert abs(changes[-1] - changes[0] - 46) <= 1, f"x per frame {xs}"
    assert xs[-1] == W - 3


def test_gravity_table_per_level(gb):
    start(gb)
    for level in (0, 1, 5, 8, 9, 10, 13, 15, 16, 18, 19, 20, 25, 99):
        gb.write_u8("level", level)
        set_board(gb, {}, clear=True)
        set_piece(gb, T, 0, 3, 0)
        drops = []
        for f in range(320):
            y = gb.s8("piece_y")
            gb.frames(1)
            if gb.s8("piece_y") != y:
                drops.append(f)
            if len(drops) == 5:
                break
        want = GRAVITY[min(level, 20)]
        # the first drop is skipped (the test's writes land at an arbitrary point of the loop);
        # PyBoy ticks end ~10 lines into update(), so single samples can be 1 frame off
        iv = [b - a for a, b in zip(drops[1:], drops[2:])]
        assert all(abs(v - want) <= 1 for v in iv), (level, drops)
        assert abs(drops[4] - drops[1] - 3 * want) <= 1, (level, drops)


def test_soft_drop_rate_and_points(gb):
    start(gb)
    set_piece(gb, T, 0, 3, 0)
    s0 = num(gb, "score", 6)
    gb.pyboy.button_press("down")
    ys = []
    for _ in range(20):
        gb.frames(1)
        ys.append(gb.s8("piece_y"))
    gb.pyboy.button_release("down")
    gb.frames(1)
    rows = ys[-1]
    # 1 row every 2 frames (the phase of the gravity timer decides 9 or 10 after 20 frames)
    assert rows in (9, 10), f"1 row every 2 frames, got y per frame {ys}"
    assert all(ys[i + 2] - ys[i] == 1 for i in range(len(ys) - 2)), ys
    assert num(gb, "score", 6) - s0 == gb.s8("piece_y"), "+1 point per soft dropped row"


def test_soft_drop_must_be_repressed_for_next_piece(gb):
    start(gb)
    set_piece(gb, T, 0, 3, 0)
    gb.pyboy.button_press("down")
    for _ in range(80):                          # soft drop until the piece locks
        gb.frames(1)
        if any(board(gb)):
            break
    gb.frames(1)                                 # a PyBoy frame can end in the middle of lock_piece()
    assert any(board(gb)), "soft drop never locked the piece"
    assert gb.u8("state") == PLAY and gb.u8("down_locked") == 1
    y0, s0 = gb.s8("piece_y"), num(gb, "score", 6)
    gb.frames(40)                                # still holding Down: normal gravity only
    assert gb.s8("piece_y") - y0 <= 1
    assert num(gb, "score", 6) == s0
    gb.pyboy.button_release("down")
    gb.frames(1)
    gb.pyboy.button_press("down")                # re-press: soft drop works again
    y1 = gb.s8("piece_y")
    gb.frames(10)
    gb.pyboy.button_release("down")
    assert gb.s8("piece_y") - y1 >= 4


def test_hard_drop_two_points_per_row_level_0(gb):
    start(gb)
    set_piece(gb, I, 0, 3, 0)                   # flat I on row 1 -> lands on row 17: 16 rows
    gb.tap("up")
    wait_play(gb)
    assert num(gb, "score", 6) == 32
    assert board(gb)[(H - 1) * W + 3:(H - 1) * W + 7] == [BLOCK + I] * 4


def test_hard_drop_is_edge_triggered(gb):
    start(gb)
    gb.pyboy.button_press("up")                 # holding Up must drop only one piece
    gb.frames(30)
    gb.pyboy.button_release("up")
    assert sum(1 for b in board(gb) if b) == 4


def test_lock_delay_is_30_frames(gb):
    start(gb)
    set_piece(gb, O, 0, 3, H - 2)               # resting on the floor
    for f in range(1, 60):
        gb.frames(1)
        if any(board(gb)):
            break
    assert f in (30, 31), f"locked after {f} frames"


def test_lock_resets_capped_at_15(gb):
    """Sliding on the floor keeps the piece alive for 15 resets, then it locks."""
    start(gb)
    set_piece(gb, O, 0, 3, H - 2)
    frames, side, max_resets = 0, ["left", "right"], 0
    while not any(board(gb)) and frames < 600:
        gb.frames(7)
        gb.tap(side[(frames // 10) % 2])
        frames += 10
        max_resets = max(max_resets, gb.u8("lock_resets"))
    assert any(board(gb)), "never locked"
    assert max_resets == 15
    assert 150 <= frames <= 200, f"locked after ~{frames} frames"


def test_lock_resets_restored_on_new_lowest_row(gb):
    start(gb)
    set_board(gb, {H - 1: "#####....."})
    set_piece(gb, O, 0, 3, H - 3)               # O on cols 4-5 resting on the ledge at col 4
    gb.write_u8("lock_resets", 15)
    gb.write_u8("lock_timer", 5)
    gb.tap("right")                             # slides off the ledge, no reset left
    assert gb.u8("lock_resets") == 15
    for _ in range(60):
        gb.frames(1)
        if gb.s8("piece_y") == H - 2:
            break
    assert gb.s8("piece_y") == H - 2
    assert gb.u8("lock_resets") == 0, "reaching a new lowest row must give the resets back"


# ------------------------------------------------------------------ spec: scoring and levels

def clear_with_i(gb, n):
    """n full-but-column-9 rows at the bottom, vertical I dropped into column 9 from row 0."""
    set_board(gb, {r: ("#########." if r >= H - n else "." * W) for r in range(H)})
    set_piece(gb, I, 1, 7, 0)                   # cells rows 0-3, lands on rows 14-17: 14 rows
    gb.tap("up")
    wait_play(gb)


def test_line_clear_points_table(gb):
    for level in (0, 3):
        for n, pts in ((1, 40), (2, 100), (3, 300), (4, 1200)):
            gb.write_u8("start_level", level)
            if gb.u8("state") != TITLE:
                gb.write_u8("state", GAMEOVER)
                gb.tap("start")
                gb.frames(2)
            gb.tap("start")
            gb.frames(2)
            assert gb.u8("state") == PLAY and gb.u8("level") == level
            clear_with_i(gb, n)
            assert num(gb, "lines", 3) == n
            assert num(gb, "score", 6) == pts * (level + 1) + 14 * 2, (level, n)


def test_level_up_every_10_lines_from_start_level(gb):
    start(gb, level=5)
    for _ in range(2):                          # 8 lines: still level 5
        clear_with_i(gb, 4)
    assert gb.u8("level") == 5 and num(gb, "lines", 3) == 8
    clear_with_i(gb, 2)                         # 10 lines -> level 6
    assert gb.u8("level") == 6
    for _ in range(3):                          # 22 lines -> level 7
        clear_with_i(gb, 4)
    assert gb.u8("level") == 7 and num(gb, "lines", 3) == 22
    gb.frames(10)
    assert vram_row(gb, PANEL_X + 4, 5, 2) == [BLANK] + text_tiles("7")
    assert vram_row(gb, PANEL_X + 3, 8, 3) == [BLANK] + text_tiles("22")


def test_lines_counter_saturates_at_999(gb):
    start(gb)
    for i, d in enumerate((9, 9, 8)):
        gb.pyboy.memory[gb.addr("lines") + i] = d
    clear_with_i(gb, 4)
    assert num(gb, "lines", 3) == 999
    assert gb.u8("state") == PLAY


def test_hud_two_digit_level(gb):
    start(gb)
    gb.write_u8("level", 25)
    clear_with_i(gb, 1)
    gb.frames(10)
    assert num(gb, "score", 6) == 40 * 26 + 28
    assert vram_row(gb, PANEL_X + 4, 5, 2) == text_tiles("25")
    assert vram_row(gb, PANEL_X, 2, 6) == [BLANK, BLANK] + text_tiles("1068")


# ------------------------------------------------------------------ spec: screens and flow

def test_title_level_select_bounds_and_display(gb):
    gb.tap("left")
    assert gb.u8("start_level") == 0
    for _ in range(12):
        gb.tap("right")
    assert gb.u8("start_level") == 9
    gb.frames(3)
    assert "9" in "".join(str(t - TILE_DIGIT0) for t in vram_row(gb, WELL_X, 9, W) if t)
    gb.screenshot("qa_title_level9")
    gb.tap("start")
    gb.frames(10)
    assert gb.u8("level") == 9
    assert vram_well(gb) == board(gb), "title texts left in the well"


def test_line_clear_flash(gb):
    start(gb)
    set_board(gb, {r: "#########." for r in range(H - 2, H)})
    set_piece(gb, I, 1, 7, 0)
    gb.tap("up")
    seen_blank = seen_full = 0
    clearing = 0
    for _ in range(40):
        if gb.u8("state") == CLEARING:
            clearing += 1
            row = vram_row(gb, WELL_X, H - 1, W)
            seen_blank += row == [BLANK] * W
            seen_full += all(row)
            if seen_blank == 1 and row == [BLANK] * W:
                gb.screenshot("qa_flash_blank")
        gb.frames(1)
    assert seen_blank and seen_full, "full rows should blink"
    assert 20 <= clearing <= 26
    assert vram_row(gb, WELL_X, H - 1, W) == [BLANK] * 9 + [BLOCK + I]   # I remnant fell down


def test_game_over_curtain(gb):
    start(gb)
    set_board(gb, {r: "#########." for r in range(2, H)})
    gb.tap("up")
    gb.frames(1)
    assert gb.u8("state") == CURTAIN
    assert all(oam_y(gb, s) == 0 for s in range(8)), "piece/next sprites must be hidden"
    rows = []
    for _ in range(50):
        gb.frames(1)
        rows.append(gb.u8("curtain_row"))
        if gb.u8("state") == CURTAIN and gb.u8("curtain_row") == 9:
            gb.screenshot("qa_curtain_half")
    assert gb.u8("state") == GAMEOVER
    assert board(gb) == [WALL] * (W * H)
    gb.frames(10)
    assert vram_row(gb, WELL_X, 7, W)[3:7] == text_tiles("GAME")
    assert vram_row(gb, WELL_X, 8, W)[3:7] == text_tiles("OVER")
    assert vram_row(gb, WELL_X, 0, W) == [WALL] * W
    gb.screenshot("qa_game_over")


def test_lock_above_well_is_game_over(gb):
    start(gb)
    set_board(gb, {1: "#########."})
    set_piece(gb, T, 0, 3, -1)                  # top row of the T above the well
    gb.frames(40)
    assert gb.u8("state") in (CURTAIN, GAMEOVER)


def test_new_game_after_game_over_resets_everything(gb):
    start(gb, level=3)
    clear_with_i(gb, 4)
    set_board(gb, {r: "#########." for r in range(2, H)})
    gb.tap("up")
    gb.frames(60)
    assert gb.u8("state") == GAMEOVER
    gb.tap("start")
    gb.frames(2)
    assert gb.u8("state") == TITLE and gb.u8("start_level") == 3
    gb.tap("start")
    gb.frames(10)
    assert gb.u8("state") == PLAY and gb.u8("level") == 3
    assert num(gb, "score", 6) == 0 and num(gb, "lines", 3) == 0
    assert gb.u8("lines_to_next") == 10
    assert vram_well(gb) == board(gb)
    gb.frames(10)
    assert vram_row(gb, PANEL_X, 2, 6) == [BLANK] * 5 + text_tiles("0")


# ------------------------------------------------------------------ edge cases

def test_pause_hides_piece_shows_text_and_resumes(gb):
    start(gb)
    set_piece(gb, T, 0, 3, 4)
    gb.frames(2)
    assert oam_y(gb, 0) != 0
    gb.tap("start")
    gb.frames(3)
    assert gb.u8("state") == PAUSE
    assert all(oam_y(gb, s) == 0 for s in range(4))
    assert vram_row(gb, PANEL_X, 15, 7)[1:6] == text_tiles("PAUSE")
    gb.screenshot("qa_pause")
    for b in ("a", "b", "left", "right", "up", "down"):
        gb.tap(b)
    assert piece(gb) == (T, 0, 3, 4), "input must be ignored while paused"
    assert num(gb, "score", 6) == 0
    gb.tap("start")
    gb.frames(3)
    assert gb.u8("state") == PLAY
    assert vram_row(gb, PANEL_X, 15, 7) == [BLANK] * 7
    assert oam_y(gb, 0) != 0


def test_pause_mashing(gb):
    start(gb)
    for _ in range(21):
        gb.tap("start")
    gb.frames(5)
    assert gb.u8("state") == PAUSE
    assert vram_row(gb, PANEL_X, 15, 7)[1:6] == text_tiles("PAUSE")
    gb.tap("start")
    gb.frames(5)
    assert gb.u8("state") == PLAY
    assert vram_row(gb, PANEL_X, 15, 7) == [BLANK] * 7


def test_start_during_line_clear_is_ignored_safely(gb):
    start(gb)
    set_board(gb, {H - 1: "#########."})
    set_piece(gb, I, 1, 7, 0)
    gb.tap("up")
    gb.tap("start")
    gb.tap("start")
    wait_play(gb)
    gb.frames(5)
    assert gb.u8("state") == PLAY
    assert num(gb, "lines", 3) == 1
    assert vram_well(gb) == board(gb)


def piece_ok(gb):
    kind, rot, x, y = piece(gb)
    brd = board(gb)
    for cx, cy in game_cells(gb, kind, rot):
        cx += x
        cy += y
        if not 0 <= cx < W or cy >= H or (cy >= 0 and brd[cy * W + cx]):
            return False
    return True


def test_button_mashing_keeps_invariants(gb):
    """Random presses of every button (several per frame) for ~4000 frames."""
    rng = random.Random(3)
    pb = gb.pyboy
    buttons = ["a", "b", "left", "right", "up", "down", "start"]
    held = set()
    games = 0
    bad = 0
    start(gb)
    for f in range(4000):
        for b in buttons:
            if rng.random() < (0.02 if b == "start" else 0.25):
                if b in held:
                    pb.button_release(b)
                    held.discard(b)
                else:
                    pb.button_press(b)
                    held.add(b)
        gb.frames(1)
        st = gb.u8("state")
        assert st <= GAMEOVER
        # a PyBoy frame can end inside lock_piece() (cells already in the board): only an
        # overlap that lasts two frames is a real bug
        bad = bad + 1 if st == PLAY and not piece_ok(gb) else 0
        assert bad < 2, f"piece overlaps the stack at frame {f}: {piece(gb)}"
        assert gb.u8("text_count") <= 6 and gb.u8("dirty_count") <= H
        assert gb.u8("lock_resets") <= 15
        if st == GAMEOVER:
            games += 1
    for b in held:
        pb.button_release(b)
    assert gb.u8("vram_late") == 0
    assert gb.u8("max_frame_lines") < 120


# ------------------------------------------------------------------ bot play + profile

def ai_choose(brd, kind):
    """Simple placement search: returns (rot, x) maximising a classic heuristic."""
    best, choice = None, (0, 3)
    for rot in range(1 if kind == O else 4):
        for x in range(-2, W):
            if not ref_fits(brd, kind, rot, x, 0):
                continue
            y = 0
            while ref_fits(brd, kind, rot, x, y + 1):
                y += 1
            b = list(brd)
            for cx, cy in ref_cells(kind, rot):
                if cy + y >= 0:
                    b[(cy + y) * W + cx + x] = 1
            rows = [b[r * W:(r + 1) * W] for r in range(H)]
            cleared = sum(all(r) for r in rows)
            rows = [r for r in rows if not all(r)]
            rows = [[0] * W] * cleared + rows
            heights, holes = [], 0
            for c in range(W):
                col = [rows[r][c] for r in range(H)]
                top = col.index(1) if 1 in col else H
                heights.append(H - top)
                holes += sum(1 for r in range(top, H) if not col[r])
            bump = sum(abs(heights[i] - heights[i + 1]) for i in range(W - 1))
            score = -0.51 * sum(heights) + 0.76 * cleared - 0.36 * holes - 0.18 * bump
            if best is None or score > best:
                best, choice = score, (rot, x)
    return choice


def bot_place(gb):
    kind = gb.u8("piece_type")
    brd = [1 if v else 0 for v in board(gb)]
    rot, x = ai_choose(brd, kind)
    if rot == 3:
        gb.tap("b")
    else:
        for _ in range(rot):
            gb.tap("a")
    for _ in range(12):
        if gb.u8("state") != PLAY:
            return
        px = gb.s8("piece_x")
        if px == x:
            break
        gb.tap("left" if px > x else "right")
    if gb.u8("state") == PLAY:
        gb.tap("up")


def test_bot_play_frame_budget_with_line_clears(gb):
    """A bot that actually clears lines plays ~6000 frames: budget, VRAM and profile."""
    start(gb, level=5)
    prof = gb.profile(["update", "draw_vram", "lock_piece", "collapse", "score_lines",
                       "spawn", "update_hud", "draw_sprites", "fits", "rotate"])
    frames0 = gb.pyboy.frame_count
    games = 0
    while gb.pyboy.frame_count - frames0 < 6000:
        st = gb.u8("state")
        if st == PLAY:
            bot_place(gb)
            wait_play(gb)
        elif st == GAMEOVER:
            games += 1
            gb.tap("start")
            gb.frames(2)
            gb.tap("start")
        else:
            gb.frames(1)
    prof.stop()
    worst = gb.u8("max_frame_lines")
    print(f"\nbot: lines {num(gb, 'lines', 3)}, level {gb.u8('level')}, score {num(gb, 'score', 6)}, "
          f"games over {games}, worst frame {worst}/154\n{prof.report()}")
    gb.screenshot("qa_bot_play")
    assert num(gb, "lines", 3) >= 20, "the run must include many line clears"
    assert gb.u8("vram_late") == 0
    assert worst != 255 and worst < 120


# ------------------------------------------------------------------ open bugs

def test_regression_lock_delay_infinite_stall_with_floor_kicks(gb):
    """With the 15 resets used up, rotating a T on the floor kicks it up one row, which makes
    grounded() false and zeroes lock_timer for free; the piece never locks."""
    start(gb)
    set_piece(gb, T, 0, 3, H - 2)
    gb.write_u8("lock_resets", 15)
    alive = 0
    for _ in range(10):
        for _ in range(4):
            gb.tap("a")
        gb.frames(10)
        if any(board(gb)):
            break
        alive += 22
    assert any(board(gb)), f"piece still not locked after {alive} frames with no resets left"


def test_regression_das_repeats_old_direction_after_pressing_new_one(gb):
    """Hold Left, then press Right: one step right, then auto-repeat goes back LEFT."""
    start(gb)
    set_piece(gb, T, 0, 3, 2)
    gb.pyboy.button_press("left")
    gb.frames(4)
    gb.pyboy.button_press("right")
    gb.frames(30)
    x = gb.s8("piece_x")
    gb.pyboy.button_release("left")
    gb.pyboy.button_release("right")
    assert x >= 3, f"newest direction (right) should win, piece went to x={x}"


def test_regression_title_text_queue_overflow_leaves_digit_in_well(gb):
    """Left+Right+Start on the same title frame queues 7 texts in a 6-slot FIFO; the clear of
    the level digit row is dropped and the digit stays on screen inside the well."""
    gb.tap("right")
    gb.frames(3)
    for b in ("left", "right", "start"):
        gb.pyboy.button_press(b)
    gb.frames(2)
    for b in ("left", "right", "start"):
        gb.pyboy.button_release(b)
    gb.frames(20)
    assert gb.u8("state") == PLAY
    assert vram_row(gb, WELL_X, 9, W) == board(gb)[9 * W:10 * W], "stale title text in the well"


def test_regression_frame_budget_tetris_at_level_99(gb):
    """score_lines() adds the points (level + 1) times: the clearing frame grows with the level
    (measured worst: level 20 -> 89, 40 -> 104, 60 -> 119, 99 -> 149 lines). Level 99 is
    reachable from start level 9 after 900 lines (lines saturate at 999 -> level 108)."""
    start(gb)
    gb.write_u8("level", 99)
    gb.write_u8("max_frame_lines", 0)
    clear_with_i(gb, 4)
    gb.frames(10)
    worst = gb.u8("max_frame_lines")
    assert gb.u8("vram_late") == 0
    assert worst < 120, f"tetris at level 99 used {worst}/154 lines"


def test_level_caps_at_99_and_hud_shows_it(gb):
    """The HUD renders 2 level digits, so the level stops at 99 (was: level 104 showed 'A4')."""
    start(gb)
    gb.write_u8("level", 99)
    gb.write_u8("lines_to_next", 1)
    clear_with_i(gb, 1)
    gb.frames(10)
    assert gb.u8("level") == 99
    hud = vram_row(gb, PANEL_X + 4, 5, 2)
    assert hud == [TILE_DIGIT0 + 9, TILE_DIGIT0 + 9], hud
