"""HAPPY VALLEY race view on the oval: every runner is drawn where hv_geom puts it (the course table
point at its metre, interpolated, + its lane along the track normal), checked against the ROM's
place_all (race_place.s) during real races; the camera keeps the focus horse on screen."""
import hv_geom as G
import hv_model as M
import pytest

pytestmark = pytest.mark.skip(reason="top-down view replaced by the side camera (GDD v1.1 §5.1); kept for the mini-map maths")

RUNNER = 64                                     # sizeof(runner_t)


def table_point(course, pos, lane):
    """The ROM's maths in Python: interpolate the 8 m table, add the lane offset (lane_off table)."""
    pts = G.table(course)
    sn = G.sine64()
    last = len(pts) - 1
    idx, f, extra = pos >> 7, pos & 127, 0
    if idx >= last:
        extra, idx, f = (pos - last * 128) >> 2, last - 1, 127
    (x0, y0, h), (x1, y1, _) = pts[idx], pts[idx + 1]

    def sm(d):
        d = ((d + 128) & 255) - 128
        v = (abs(d) * f * 2) >> 8
        return -v if d < 0 else v

    def off(hh):
        s = sn[hh]
        return (s * lane * G.LANE_PX) >> 6 if s >= 0 else -((-s * lane * G.LANE_PX) >> 6)

    return x0 + sm(x1 - x0) + off(h) + extra, y0 + sm(y1 - y0) - off((h + 16) & 63)


@pytest.mark.parametrize("course", ["HV1200", "ST1600", "AW1650"])
def test_runners_are_where_the_geometry_says(gb, course):
    n = 12 if course.startswith("HV") else 14
    gb.write_u16("race_seed", 0x2468)
    gb.write_u8("race_req_course", M.COURSE_IDS.index(course))
    gb.write_u8("race_lo", 40)
    gb.write_u8("race_hi", 60)
    gb.write_u8("race_req_n", n)
    gb.write_u8("race_req", 2)                  # on screen
    checked = 0
    for _ in range(12):
        gb.frames(97)
        gb.tap("start")                         # pause: positions and their drawing are from one frame
        gb.frames(4)
        raw = gb.bytes("rx", RUNNER * n)
        xs, ys = gb.bytes("rv_x", 2 * n), gb.bytes("rv_y", 2 * n)
        for k in range(n):
            pos = raw[k * RUNNER] | raw[k * RUNNER + 1] << 8
            lane = raw[k * RUNNER + 17]
            got = (xs[2 * k] | xs[2 * k + 1] << 8, ys[2 * k] | ys[2 * k + 1] << 8)
            want = table_point(course, pos, lane)
            assert abs(got[0] - want[0]) <= 1 and abs(got[1] - want[1]) <= 1, (k, pos, lane, got, want)
            checked += 1
        gb.tap("start")
    assert checked == 12 * n
    gb.screenshot(f"view_{course.lower()}")
    assert gb.u8("vram_late") == 0 and gb.u16("world_lost") == 0
