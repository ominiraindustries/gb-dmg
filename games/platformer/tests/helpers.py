"""Shared helpers for CABALLERITO tests (state ids, memory views, level data from the ROM)."""
TITLE, INTRO, PLAY, PAUSE, DYING, GOAL, CLEAR, GAMEOVER = range(8)
Y_BIAS = 32
ROWS = 8


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def start_play(gb, max_frames=600):
    """Get to gameplay from whatever screen the game boots into."""
    for _ in range(max_frames):
        st = gb.u8("state")
        if st == PLAY:
            return
        if st == TITLE:
            gb.tap("start")
        else:
            gb.frames(1)
    raise AssertionError(f"never reached PLAY (state {gb.u8('state')})")


def level_cols(gb):
    return gb.u8("level_cols")


def level_map(gb):
    return gb.bytes("level", level_cols(gb) * ROWS)


def mt_tiles(gb):
    """Metatile -> [TL, TR, BL, BR] read from the ROM table."""
    count = 33
    raw = gb.bytes("mt_tiles", count * 4)
    return [raw[i * 4:i * 4 + 4] for i in range(count)]


def expected_tile_column(level, tiles, ncols, tc):
    """The 16 BG tiles the game should have written for world tile column tc."""
    col = tc >> 1
    if col >= ncols:
        return [0] * 16
    h = tc & 1
    out = []
    for r in range(ROWS):
        t = tiles[level[col * ROWS + r]]
        out += [t[h], t[2 + h]]
    return out


def vram_tile_column(gb, tc):
    base = 0x9800 + (tc & 31)
    return [gb.pyboy.memory[base + 32 * row] for row in range(16)]


def teleport(gb, x, y=20):
    """Place Teo in the air above the level (y < Y_BIAS is open sky), no velocity."""
    gb.write_u16("player_x", x)
    gb.write_u8("player_y", y)
    gb.write_u16("player_vx", 0)
    gb.write_u16("player_vy", 0)


def wait_state(gb, state, max_frames=600):
    """Advance until the game reaches `state` (e.g. back to PLAY after a death and the intro)."""
    for _ in range(max_frames):
        if gb.u8("state") == state:
            return True
        gb.frames(1)
    return gb.u8("state") == state
