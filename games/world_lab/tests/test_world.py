"""gbe_world on world_lab: the visible BG equals the map model every frame of a random walk (walking
and at bike speed), the drawn region is complete when idle, solid cells block, costs."""
import random
from pathlib import Path

import pytest
import world

GAME = Path(__file__).resolve().parents[1]
MAP = world.load(GAME, GAME / "res" / "maps" / "test.map")
import metatiles  # noqa: E402  (after world: same parse as the build)
import json  # noqa: E402
import preview  # noqa: E402
import screens  # noqa: E402

SETS = preview.find_tilesets(GAME)
BASES = screens.vram_bases(json.loads((GAME / "game.json").read_text(encoding="utf-8"))["vram_order"], SETS)
MT = metatiles.parse(GAME / "res" / "metatiles.mt", SETS["bg"].labels, BASES)
SOLID = {i for i, a in enumerate(MT.attrs) if "SOLID" in a}
DIRS = ["down", "up", "left", "right"]


def tile_at(wtx, wty):
    """VRAM tile of world tile column/row (8 px units, may be negative)."""
    mt = MAP.at(wtx >> 1, wty >> 1)
    return MT.vram_tiles(mt)[(wtx & 1) + 2 * (wty & 1)]


def visible_errors(gb, cam):
    """Compare the screen (SCX/SCY applied this frame = camera of the previous logic frame)."""
    cx, cy = cam
    scx, scy = gb.io(0xFF43), gb.io(0xFF42)
    assert (scx, scy) == (cx & 0xFF, cy & 0xFF), "SCX/SCY do not follow the camera"
    bg = gb.bg_map(map=0)
    errs = []
    for ty in range(18 + (1 if cy & 7 else 0)):
        for tx in range(20 + (1 if cx & 7 else 0)):
            wtx, wty = (cx >> 3) + tx, (cy >> 3) + ty
            got = bg[wty & 31][wtx & 31]
            if got != tile_at(wtx, wty):
                errs.append((tx, ty, got, tile_at(wtx, wty)))
    return errs


def region_errors(gb, m=None):
    m = m or MAP
    rx, ry = gb.u8("reg_x"), gb.u8("reg_y")
    bg = gb.bg_map(map=0)
    errs = []
    for r in range(12):
        for c in range(13):
            x, y = (rx + c) & 0xFF, (ry + r) & 0xFF
            for k, t in enumerate(MT.vram_tiles(m.at(x, y))):
                if bg[((y & 15) * 2 + (k >> 1))][((x & 15) * 2 + (k & 1))] != t:
                    errs.append((x, y))
                    break
    return errs


def cam(gb):
    return (gb.s16("cam_x") if hasattr(gb, "s16") else _s16(gb.u16("cam_x")),
            gb.s16("cam_y") if hasattr(gb, "s16") else _s16(gb.u16("cam_y")))


def _s16(v):
    return v - 0x10000 if v & 0x8000 else v


def test_selftest_asm_equals_c(gb):
    gb.frames(2)
    mism, cases = gb.selftest()
    assert mism == 0 and cases == ((2 * 65536) + 200) & 0xFFFF   # world 131072 (u16 wraps) + gact 200


def actor_errors(gb):
    """Cells taken by actors (x,y and target) never shared, never solid, never the player's."""
    raw = gb.bytes("gact", 24 * 13)
    taken, errs = {}, []
    player = {(gb.u8("px"), gb.u8("py"))}
    for i in range(13):
        r = raw[i * 24:(i + 1) * 24]
        if not r[0]:
            continue
        for cell in {(r[1], r[2]), (r[3], r[4])}:
            if cell in taken or cell in player or MAP.at(*cell) in SOLID:
                errs.append((i, cell, taken.get(cell)))
            taken[cell] = i
    return errs


def test_start_region_drawn(gb):
    gb.frames(2)
    assert (gb.u8("px"), gb.u8("py")) == (34, 34)
    assert region_errors(gb) == []
    gb.screenshot("start")


def test_random_walk_visible_equals_map(gb):
    rnd = random.Random(3)
    prev = cam(gb)
    bad, frames, held, bike = [], 0, None, False
    for seg in range(160):
        d = rnd.choice(DIRS)
        bike = rnd.random() < 0.5
        for b in DIRS + ["b"]:
            gb.pyboy.button_release(b)
        gb.pyboy.button_press(d)
        if bike:
            gb.pyboy.button_press("b")
        for _ in range(rnd.randint(8, 80)):
            gb.frames(1)
            frames += 1
            e = visible_errors(gb, prev)
            if e:
                bad.append((frames, (gb.u8("px"), gb.u8("py")), e[:3]))
            if frames % 4 == 0:
                bad += [("actor", frames, a) for a in actor_errors(gb)]
            prev = cam(gb)
    for b in DIRS + ["b"]:
        gb.pyboy.button_release(b)
    gb.frames(30)
    gb.screenshot("after_walk")
    print("steps", gb.u16("steps"), "frames", frames, "worst lines", gb.u8("max_frame_lines"))
    assert gb.u16("steps") > 300, "the bot did not walk"
    assert bad == [], bad[:5]
    assert region_errors(gb) == []
    assert gb.u16("world_lost") == 0 and gb.u8("vram_late") == 0
    assert gb.u8("max_frame_lines") < 120


def test_solid_cells_block(gb):
    gb.write_bytes("gact", [0] * 24 * 13)          # no actors in the way
    # walk left until the sand/water border stops the player: water is solid
    gb.pyboy.button_press("left")
    gb.frames(16 * 40)
    gb.pyboy.button_release("left")
    gb.frames(20)
    x, y = gb.u8("px"), gb.u8("py")
    assert MAP.at(x - 1, y) in SOLID and MAP.at(x, y) not in SOLID


def test_cache_follows_focus(gb):
    gb.pyboy.button_press("right")
    gb.pyboy.button_press("b")
    gb.frames(16 * 20 // 2)
    for b in ("right", "b"):
        gb.pyboy.button_release(b)
    gb.frames(10)
    px, py = gb.u8("px"), gb.u8("py")
    sx, sy = px >> 4, py >> 4
    want = {(sy + dy) * MAP.w + (sx + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
            if 0 <= sx + dx < MAP.w and 0 <= sy + dy < MAP.h}
    have = set(gb.bytes("wcache_sector", 9)) - {0xFF}
    assert want <= have


CASA = world.load(GAME, GAME / "res" / "maps" / "casa.map")
MAP_IDS = world.map_ids(GAME)


def walk_until(gb, button, cond, limit=200):
    gb.pyboy.button_press(button)
    for _ in range(limit):
        gb.frames(1)
        if cond():
            break
    gb.pyboy.button_release(button)
    gb.frames(20)
    assert cond()


def test_warp_into_the_house_and_back(gb):
    gb.write_bytes("gact", [0] * 24 * 13)               # nothing in the way
    gb.frames(2)
    walk_until(gb, "down", lambda: gb.u8("warps") == 1)   # (34,34) -> (34,35) -> door (34,36)
    assert gb.u8("wmap_id") == MAP_IDS["MAP_CASA"]
    assert (gb.u8("px"), gb.u8("py")) == (7, 13)
    assert region_errors(gb, CASA) == []
    gb.screenshot("casa")
    walk_until(gb, "down", lambda: gb.u8("warps") == 2)   # (7,13) -> (7,14) -> door (7,15) -> TEST
    assert gb.u8("wmap_id") == MAP_IDS["MAP_TEST"]
    assert (gb.u8("px"), gb.u8("py")) == (34, 37)          # below the door: walking on leaves it
    assert region_errors(gb) == []
    assert gb.u8("vram_late") == 0


def test_map_objects_compiled(gb):
    assert [(x, y, t) for x, y, _, t, _ in MAP.objects] == [(34, 32, "npc"), (37, 33, "sign"), (34, 36, "warp")]
