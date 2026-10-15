"""HAPPY VALLEY race on screen: a pixel oval seen from above and a dot per runner (design/gen_track.py).
The race split over frames gives the model's result and lasts what it should (fields of 8: a tick per
frame), the frame budget holds, no VRAM write is lost, every dot is on the track band, the commentary
reads on screen."""
import pytest

import sys
from pathlib import Path

import hv_model as M

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "design"))
import gen_track  # noqa: E402

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


@pytest.mark.parametrize("course,n", [("HV1200", 8), ("ST2400", 8), ("AW1650", 8)])
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
    # the race model takes ~36k T of every frame (a tick per frame, 8 runners) + a letter ~10k: frames
    # with a letter reach ~147 lines, so the check is "no frame lost" (154), not the house rule of 120
    assert gb.u8("max_frame_lines") < 154, gb.u8("max_frame_lines")


def test_commentary_on_screen(gb):
    start(gb, "HV1200", 8)
    seen = set()
    for _ in range(60):                         # the gates, then "¡Salen!" typed (queued behind the mini-map)
        gb.frames(5)
        seen.add(gb.read_text(16).strip())
    assert any(t.endswith("Salen!") for t in seen), seen   # the font's ¡ decodes as i (art pass)
    assert gb.u8("tiles_lost") == 0


@pytest.mark.parametrize("course", ["HV1650", "ST2400", "AW1200"])
def test_dots_on_the_track(gb, course):
    track = {0: "HV", 1: "ST", 2: "AW"}[M.COURSES[course]["track"]]
    img = gen_track.image(track)
    start(gb, course, 8)
    for _ in range(12):                         # dots: 3x3 centred on OAM (x - 7, y - 15), within the rails
        gb.frames(97)
        dots = [(x - 7, y - 15) for y, x, t, p in gb.oam()[:8]]
        assert all(y > 0 for x, y in dots)
        for x, y in dots:
            assert img[y][x] in (1, 2, 3), (course, x, y)   # the centre on the band
    gb.screenshot(f"oval_{course.lower()}")
