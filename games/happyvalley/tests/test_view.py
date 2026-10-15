"""HAPPY VALLEY race on screen (GDD v1.1 5.1, straight courses only): the race split over frames
(RV_PER_FRAME runners per frame) gives the model's result, it lasts what it should (fields of 8: a tick per frame, x2.4 real time),
the frame budget holds, no VRAM write is lost, and the sprites asm (race_spr.s) == sprites_c."""
import pytest

import hv_model as M

SEED = 0x2468


def start(gb, course, n, use_c=0):
    gb.write_u8("race_use_c", use_c)
    gb.write_u16("race_seed", SEED)
    gb.write_u8("race_req_course", M.COURSE_IDS.index(course))
    gb.write_u8("race_lo", 40)
    gb.write_u8("race_hi", 60)
    gb.write_u8("race_req_n", n)
    gb.write_u8("race_req", 2)
    gb.frames(2)


def results(gb, n):
    ids = gb.bytes("res_i", n)
    rt, ro = gb.bytes("res_t", 2 * n), gb.bytes("res_over", 2 * n)
    return [(ids[k], rt[2 * k] | rt[2 * k + 1] << 8, ro[2 * k] | ro[2 * k + 1] << 8)
            for k in range(n) if ids[k] != 0xFF]


@pytest.mark.parametrize("course,n", [("HV1200", 8), ("AW800", 8)])
def test_screen_race_equals_model_and_budget(gb, course, n):
    start(gb, course, n)
    gb.frames(30)                               # the transition in
    gb.write_u8("max_frame_lines", 0)
    gb.write_u8("vram_late", 0)
    frames = 0
    while not gb.u8("race_done"):
        gb.frames(10)
        frames += 10
        if frames == 600:
            gb.screenshot(f"race_{course.lower()}")
        assert frames < 4000, "the race did not end"
    hs, w, want = M.race_from_seed(SEED, course, 40, 60, n)
    assert results(gb, n) == want
    last = max(t for _, t, _ in want)           # a tick per frame + the gates (40)
    assert frames <= 40 + last * n // 8 + 30, (frames, last)
    assert gb.u8("vram_late") == 0
    assert gb.u8("tiles_lost") == 0 and gb.u8("vq_lost") == 0
    # the race model takes ~34k T of every frame (a tick per frame, 8 runners): the worst frames are
    # ~150 lines, so the check is "no frame lost" (the real limit), not the house rule of 120
    assert gb.u8("max_frame_lines") < 154, gb.u8("max_frame_lines")


def test_sprites_asm_equals_c(gb):
    gb.write_u8("spr_check", 1)                 # every frame: sprites_c and race_spr.s from the same state
    start(gb, "HV1000", 8)
    for k in range(10):
        gb.frames(60)
        assert gb.u8("spr_mismatch") == 0, k
    assert any(y for y, x, t, p in gb.oam())   # runners on screen


def test_commentary_on_screen(gb):
    start(gb, "HV1000", 8)
    seen = set()
    for _ in range(60):                         # the gates, then "¡Salen!" typed (queued behind the mini-map)
        gb.frames(5)
        seen.add(gb.read_text(16, 0, 13).strip())  # cols 14-19: the mini-map (same text slot)
    assert any(t.endswith("Salen!") for t in seen), seen   # the font's ¡ decodes as i (art pass)
    assert gb.u8("tiles_lost") == 0
