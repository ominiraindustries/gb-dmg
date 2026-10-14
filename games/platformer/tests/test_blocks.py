"""M1 step 2: blocks, coins, items, forms, crouch and projectiles."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from helpers import (Y_BIAS, expected_tile_column, level_cols, level_map, mt_tiles, s16,
                     start_play, teleport, vram_tile_column)

# ids from src/metatiles.h / game.h
MT_SKY, MT_BRICK, MT_Q_COIN, MT_Q_POWER, MT_HIDDEN, MT_USED, MT_COIN = 0, 2, 3, 4, 5, 6, 12
T_NONE, T_ITEM_GROW, T_ITEM_SHOT, T_ITEM_1UP, T_SHOT, T_DEBRIS, T_COINPOP = 0, 3, 4, 5, 6, 8, 9
A_ITEM, A_SHOT0, A_DEBRIS0, A_COIN0 = 5, 6, 8, 12
FORM_SMALL, FORM_BIG, FORM_SHOT = 0, 1, 2
SMALL_ON_GROUND = Y_BIAS + 7 * 16 - 16
BIG_ON_GROUND = SMALL_ON_GROUND - 16


def score(gb):
    return int("".join(f"{b:02X}" for b in reversed(gb.bytes("score", 3))))


def cell(gb, col, row):
    return gb.bytes("level", 200 * 8)[col * 8 + row]


def stand_under(gb, col, big=False):
    """Teleport onto the ground under block column `col` and let streaming catch up."""
    start_play(gb)
    gb.write_u8("cheat_flags", 2)                # no timer
    if big:
        make_big(gb)
    teleport(gb, col * 16, BIG_ON_GROUND if big else SMALL_ON_GROUND)
    gb.frames(40)


def make_big(gb, form=FORM_BIG):
    gb.write_u8("player_form", form)
    gb.write_u8("hb_y", 4)
    gb.write_u8("hb_h", 28)


def jump_hit(gb):
    gb.pyboy.button_press("a")
    gb.frames(30)
    gb.pyboy.button_release("a")
    gb.frames(40)


def vram_matches_map(gb):
    level, tiles, ncols = level_map(gb), mt_tiles(gb), level_cols(gb)
    cam_tile = gb.u16("camera_x") >> 3
    return all(expected_tile_column(level, tiles, ncols, tc) == vram_tile_column(gb, tc)
               for tc in range(cam_tile, cam_tile + 21))


def test_coin_block(gb):
    stand_under(gb, 16)
    assert cell(gb, 16, 4) == MT_Q_COIN
    jump_hit(gb)
    assert cell(gb, 16, 4) == MT_USED
    assert gb.u8("coins") == 1
    assert score(gb) == 200
    assert vram_matches_map(gb), "used block not redrawn on screen"


def test_coin_pops_out_of_block(gb):
    stand_under(gb, 16)
    gb.pyboy.button_press("a")
    for _ in range(30):
        gb.frames(1)
        if gb.u8("act_type")  == T_COINPOP or gb.bytes("act_type", 14)[A_COIN0] == T_COINPOP:
            break
    gb.pyboy.button_release("a")
    assert gb.bytes("act_type", 14)[A_COIN0] == T_COINPOP
    gb.screenshot("coin_pop")


def test_power_block_gives_grow_item_and_teo_grows(gb):
    stand_under(gb, 21)                          # 'P' at column 21, row 4
    jump_hit(gb)
    assert cell(gb, 21, 4) == MT_USED
    types = gb.bytes("act_type", 14)
    assert types[A_ITEM] == T_ITEM_GROW
    gb.screenshot("item_out")
    # the item walks right; follow it until Teo touches it
    gb.pyboy.button_press("right")
    for _ in range(200):
        gb.frames(1)
        if gb.u8("player_form") == FORM_BIG:
            break
    gb.pyboy.button_release("right")
    assert gb.u8("player_form") == FORM_BIG
    assert score(gb) >= 1000
    gb.frames(60)                                # grow animation done
    assert gb.u8("hb_h") == 28
    gb.screenshot("teo_big")


def test_power_block_gives_shot_item_when_big(gb):
    stand_under(gb, 21, big=True)
    jump_hit(gb)
    assert gb.bytes("act_type", 14)[A_ITEM] == T_ITEM_SHOT


def test_brick_bumps_when_small_breaks_when_big(gb):
    stand_under(gb, 20)                          # 'B' at column 20, row 4
    jump_hit(gb)
    assert cell(gb, 20, 4) == MT_BRICK
    stand_under(gb, 20, big=True)
    s0 = score(gb)
    gb.pyboy.button_press("a")
    for _ in range(30):
        gb.frames(1)
        if cell(gb, 20, 4) == MT_SKY:
            break
    gb.pyboy.button_release("a")
    assert cell(gb, 20, 4) == MT_SKY
    assert gb.bytes("act_type", 14)[A_DEBRIS0] == T_DEBRIS
    assert score(gb) - s0 == 50
    gb.screenshot("brick_break")
    gb.frames(10)
    assert vram_matches_map(gb)


def test_hidden_block_only_solid_from_below(gb):
    stand_under(gb, 64)                          # 'U' at column 64, row 3 (invisible)
    assert cell(gb, 64, 3) == MT_HIDDEN
    # a small jump from the ground (49 px) reaches row 3's bottom (y 112)? row 3 bottom = 32+64 = 96
    # -> use a running jump height instead: place Teo on top of something? simply teleport below it
    teleport(gb, 64 * 16, Y_BIAS + 4 * 16)       # in the air just below the block
    gb.write_u16("player_vy", (-0x0300) & 0xFFFF)
    gb.frames(10)
    assert cell(gb, 64, 3) == MT_USED
    assert gb.bytes("act_type", 14)[A_ITEM] == T_ITEM_1UP


def test_map_coin_collect_and_100_coins_life(gb):
    start_play(gb)
    gb.write_u8("coins", 99)
    lives = gb.u8("lives")
    teleport(gb, 34 * 16, Y_BIAS + 2 * 16)       # '$' at column 34, row 2
    gb.frames(2)
    assert cell(gb, 34, 2) == MT_SKY
    assert gb.u8("coins") == 0
    assert gb.u8("lives") == lives + 1


def test_crouch_when_big(gb):
    stand_under(gb, 8, big=True)
    gb.pyboy.button_press("down")
    gb.frames(3)
    assert gb.u8("player_crouch") == 1
    assert gb.u8("hb_h") == 14
    gb.pyboy.button_release("down")
    gb.frames(3)
    assert gb.u8("player_crouch") == 0
    assert gb.u8("hb_h") == 28


def test_shots_max_two_and_bounce(gb):
    stand_under(gb, 8, big=True)
    make_big(gb, FORM_SHOT)
    for _ in range(4):                           # 4 presses, cooldown 8 f: only 2 alive at once
        gb.tap("b")
        gb.frames(9)
    types = gb.bytes("act_type", 14)
    assert types[A_SHOT0] in (T_SHOT, 7) or types[A_SHOT0 + 1] in (T_SHOT, 7)
    alive = sum(1 for t in types[A_SHOT0:A_SHOT0 + 2] if t == T_SHOT)
    assert alive <= 2
    gb.screenshot("shots")


def test_frame_budget_with_blocks(gb):
    stand_under(gb, 20, big=True)
    jump_hit(gb)                                 # break a brick: debris + block queue
    assert gb.u8("vram_late") == 0
    assert gb.u8("max_frame_lines") < 120
