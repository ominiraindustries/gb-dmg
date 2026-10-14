"""M1 step 1: level load, camera, column streaming, HUD, player movement and map collision."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from helpers import (PLAY, Y_BIAS, expected_tile_column, level_cols, level_map, mt_tiles,
                     s16, start_play, teleport, vram_tile_column)

GROUND_FEET = Y_BIAS + 7 * 16          # top of the ground row
SMALL_Y_ON_GROUND = GROUND_FEET - 16   # box top of a 16x16 small Teo standing on the ground


def test_starts_on_ground_at_x(gb):
    start_play(gb)
    gb.frames(10)
    assert gb.u16("player_x") == 2 * 16
    assert gb.u8("player_y") == SMALL_Y_ON_GROUND
    assert gb.u8("player_on_ground") == 1
    assert gb.u8("level_cols") == 200
    gb.screenshot("start")


def frames_until(gb, cond, limit):
    for f in range(1, limit + 1):
        gb.frames(1)
        if cond():
            return f
    return None


def test_walk_and_run_acceleration(gb):
    start_play(gb)
    gb.pyboy.button_press("right")
    f = frames_until(gb, lambda: s16(gb.u16("player_vx")) == 0x0140, 30)
    assert f is not None and 9 <= f <= 11, f
    gb.frames(10)
    assert s16(gb.u16("player_vx")) == 0x0140          # walking max holds
    gb.pyboy.button_press("b")
    f = frames_until(gb, lambda: s16(gb.u16("player_vx")) == 0x0200, 30)
    assert f is not None and 5 <= f <= 7, f            # 0x140 -> 0x200 at 0x20/f = 6 frames
    gb.pyboy.button_release("b")
    f = frames_until(gb, lambda: s16(gb.u16("player_vx")) == 0x0140, 30)
    assert f is not None and f <= 5, f                 # decays to walk max by 0x30/f
    gb.pyboy.button_release("right")
    f = frames_until(gb, lambda: gb.u16("player_vx") == 0, 30)
    assert f is not None and 6 <= f <= 8, f            # 0x140 / 0x30


def test_skid_when_reversing(gb):
    start_play(gb)
    gb.hold("right", 20)
    gb.pyboy.button_press("left")
    gb.frames(2)
    assert gb.u8("player_skid") == 1
    f = frames_until(gb, lambda: s16(gb.u16("player_vx")) <= 0, 10)
    assert f is not None and f <= 4                    # 0x140 / 0x60
    gb.pyboy.button_release("left")


def jump_height(gb, hold_a_frames, run=False, walk=False):
    start_play(gb)
    gb.frames(5)
    if run or walk:
        gb.pyboy.button_press("right")
        if run:
            gb.pyboy.button_press("b")
        gb.frames(30)
    y0 = gb.u8("player_y")
    gb.pyboy.button_press("a")
    top = y0
    for f in range(90):
        if f == hold_a_frames:
            gb.pyboy.button_release("a")
        gb.frames(1)
        top = min(top, gb.u8("player_y"))
        if f > 5 and gb.u8("player_on_ground"):
            break
    for b in ("a", "b", "right"):
        gb.pyboy.button_release(b)
    return y0 - top


def test_jump_heights_match_gdd(gb):
    tap = jump_height(gb, 1)
    assert 14 <= tap <= 24, tap                        # GDD ~20 px


def test_jump_height_walking_held(gb):
    h = jump_height(gb, 90, walk=True)
    assert 44 <= h <= 54, h                            # GDD ~49 px


def test_jump_height_running_held(gb):
    h = jump_height(gb, 90, run=True)
    assert 58 <= h <= 70, h                            # GDD ~64 px


def test_coyote_time(gb):
    """Walk off the right edge of the col 28 turret top... simpler: stand at a pit edge."""
    start_play(gb)
    # pit at columns 69-70: place Teo on the ground just left of it, moving right
    teleport(gb, 68 * 16 + 2, SMALL_Y_ON_GROUND)
    gb.write_u16("camera_x", 60 * 16)
    gb.frames(2)
    gb.write_u16("player_vx", 0x0140)
    gb.pyboy.button_press("right")
    f = frames_until(gb, lambda: gb.u8("player_on_ground") == 0, 30)
    assert f is not None
    gb.frames(2)                                       # + 1 frame input latency = 3 frames late
    gb.tap("a")
    assert s16(gb.u16("player_vy")) < -0x0200, "coyote jump should still work"
    gb.pyboy.button_release("right")


def test_no_jump_after_coyote_window(gb):
    start_play(gb)
    teleport(gb, 68 * 16 + 2, SMALL_Y_ON_GROUND)
    gb.write_u16("camera_x", 60 * 16)
    gb.frames(2)
    gb.write_u16("player_vx", 0x0140)
    gb.pyboy.button_press("right")
    assert frames_until(gb, lambda: gb.u8("player_on_ground") == 0, 30)
    gb.frames(7)
    gb.tap("a")
    assert s16(gb.u16("player_vy")) > 0, "too late: must not jump"
    gb.pyboy.button_release("right")


def test_head_bump_and_corner_correction(gb):
    start_play(gb)
    # rune block at column 16, row 4 (y 96..111). Stand under it and jump.
    teleport(gb, 16 * 16, SMALL_Y_ON_GROUND)
    gb.write_u16("camera_x", 8 * 16)
    gb.frames(3)
    gb.tap("a")
    gb.frames(20)
    top = gb.u8("player_y") + 2
    assert top >= Y_BIAS + 5 * 16 - 2                  # never got inside the block
    gb.frames(60)
    # 3 px overlap on the block's right edge: corrected, jumps past it
    teleport(gb, 17 * 16 - 3 - 3 + 3, SMALL_Y_ON_GROUND)
    gb.frames(3)
    gb.pyboy.button_press("a")
    peak = 255
    for _ in range(40):
        gb.frames(1)
        peak = min(peak, gb.u8("player_y"))
    gb.pyboy.button_release("a")
    assert peak < Y_BIAS + 4 * 16, "corner correction should let Teo rise past the block"


def test_camera_never_goes_back_and_left_edge_blocks(gb):
    start_play(gb)
    gb.pyboy.button_press("right")
    gb.pyboy.button_press("b")
    gb.frames(120)
    gb.pyboy.button_release("right")
    gb.pyboy.button_release("b")
    gb.frames(30)                                      # let Teo stop sliding first
    cam = gb.u16("camera_x")
    assert cam > 0
    assert gb.u16("player_x") - cam <= 64 + 2
    gb.hold("left", 200)
    assert gb.u16("camera_x") == cam
    assert gb.u16("player_x") >= cam


def walk_camera(gb, step, check_every=1):
    """Fly Teo over the level at `step` px/frame and compare VRAM with the map each frame."""
    start_play(gb)
    level, tiles, ncols = level_map(gb), mt_tiles(gb), level_cols(gb)
    x = gb.u16("player_x")
    mismatches = []
    frame = 0
    while gb.u16("camera_x") < ncols * 16 - 160:
        x += step
        teleport(gb, x)
        gb.frames(1)
        frame += 1
        if frame % check_every:
            continue
        cam_tile = gb.u16("camera_x") >> 3
        for tc in range(cam_tile, cam_tile + 21):
            exp = expected_tile_column(level, tiles, ncols, tc)
            got = vram_tile_column(gb, tc)
            if exp != got:
                mismatches.append((frame, tc))
    return mismatches


def test_streaming_vram_matches_map_whole_level(gb):
    bad = walk_camera(gb, 2)
    assert not bad, f"{len(bad)} wrong columns, first {bad[:5]}"
    assert gb.u8("vram_late") == 0


def test_streaming_stress_4px(gb):
    bad = walk_camera(gb, 4)
    assert not bad, bad[:5]
    assert gb.u8("vram_late") == 0


def test_streaming_stress_8px(gb):
    bad = walk_camera(gb, 8)
    assert not bad, bad[:5]
    assert gb.u8("vram_late") == 0
    assert gb.u8("max_frame_lines") < 120


def test_camera_stops_at_level_end(gb):
    start_play(gb)
    for x in range(100, 200 * 16, 8):
        teleport(gb, x)
        gb.frames(1)
    assert gb.u16("camera_x") == 200 * 16 - 160


def test_hud_shows_labels_and_values(gb):
    start_play(gb)
    gb.frames(30)
    win = [gb.pyboy.memory[0x9C00 + i] for i in range(20)]
    font = gb.addr  # noqa: just to keep the import list small
    # PUNTOS at cols 1-6 uses font letters; check it differs from blank and the time ticks down
    t0 = gb.u16("time_units")
    gb.frames(24 * 3 + 2)
    assert gb.u16("time_units") in (t0 - 3, t0 - 4)
    assert win[1] != win[0]
    gb.screenshot("hud")


def test_fall_in_pit_restarts(gb):
    start_play(gb)
    teleport(gb, 69 * 16 + 4, SMALL_Y_ON_GROUND)
    gb.write_u16("camera_x", 60 * 16)
    gb.frames(60)
    assert gb.u16("player_x") == 2 * 16   # step 1 behaviour: restart at the start
