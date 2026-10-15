"""HAPPY VALLEY stable and week (GDD 2.2, 2.5, 2.7, 2.8): the ROM's week == tests/hv_week.py, week by
week, with every training plan, high fatigue (half gains, injuries) and idle horses."""
import hv_week as W

HSIZE = 41                                      # horse_t in src/hv.h (no padding)


def rom_horses(gb):
    raw = gb.bytes("hv_horse", HSIZE * W.SLOTS)
    out = []
    for k in range(W.SLOTS):
        b = raw[k * HSIZE:(k + 1) * HSIZE]
        if not b[0]:
            out.append(None)
            continue
        out.append({"state": b[0], "sex": b[1], "age": b[2], "curve": b[3], "style": b[4], "dpref": b[5],
                    "rating": b[6], "fat": b[7], "injury": b[8], "idle": b[9], "plan": b[10], "sal": b[11],
                    "surf": b[12] - 256 if b[12] > 127 else b[12], "pot": list(b[13:18]),
                    "a16": [b[18 + 2 * i] | b[19 + 2 * i] << 8 for i in range(4)],
                    "name": bytes(b[26:41]).split(b"\0")[0].decode()})
    return out


def model_view(h):
    return None if h is None else {k: h[k] for k in ("state", "sex", "age", "curve", "style", "dpref", "rating",
                                                     "fat", "injury", "idle", "plan", "sal", "surf", "pot", "a16", "name")}


def money(gb):
    return int.from_bytes(bytes(gb.bytes("hv_money", 4)), "little", signed=True)


def test_new_game_matches_start_table(gb):
    gb.write_u16("race_seed", 0x1234)
    gb.write_u8("game_req", 1)
    gb.frames(2)
    st = W.new_game()
    assert rom_horses(gb) == [model_view(h) for h in st["horses"]]
    assert money(gb) == st["money"] and gb.u8("hv_week") == 1 and gb.u8("hv_season") == 1


def test_weeks_equal_model(gb):
    seed = 0xBEEF
    gb.write_u16("race_seed", seed)
    gb.write_u8("game_req", 1)
    gb.frames(2)
    st = W.new_game()
    rng = W.M.Rng(gb.u16("rng_state"))
    plans = [[2, 3, 1], [4, 5, 2], [2, 2, 2], [0, 0, 0], [3, 1, 4]]   # SERIES FONDO GALOPE...
    injured = idle = 0
    for week in range(60):
        p = plans[(week // 4) % len(plans)]
        for k in range(3):
            gb._write(gb.addr("hv_horse") + k * HSIZE + 10, p[k])
            st["horses"][k]["plan"] = p[k]
        gb.write_u8("week_req", 1)
        gb.frames(2)
        W.advance(st, rng)
        assert rom_horses(gb) == [model_view(h) for h in st["horses"]], week
        assert money(gb) == st["money"], week
        assert (gb.u8("hv_week"), gb.u8("hv_season")) == (st["week"], st["season"]), week
        assert gb.u16("rng_state") == rng.s, week
        injured += any(h["injury"] for h in st["horses"] if h)
        idle += any(h["idle"] >= 3 for h in st["horses"] if h)
    assert injured and idle                     # the run went through injuries and detraining
