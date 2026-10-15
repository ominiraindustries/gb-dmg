"""HAPPY VALLEY - geometry of the oval tracks (the race view: camera over a big oval, user's choice).

One source for the generated maps (res/maps/hv.map, st.map for gbe_world), the ROM's path tables
(src/track_data.c: a point every STEP_M metres of each course) and the tests.
Scale: PX_PER_M px per metre (0.25 m per px). Running is clockwise on screen (Happy Valley and Sha Tin
are right-handed): the home straight is at the top, heading east, with the stands above it; the
finish post at its east end. Each track is a CLOSED oval (two straights of `straight` m, two half
circles of radius bend/pi): a runner `d` metres from the finish is found by walking back `d` metres
around it. The model's course segments (courses.tbl, where the straights are not equal: Sha Tin
430 m home vs 600 m back) are not used for drawing; the view differs from them by a few metres.
Sha Tin's 1000 m straight course is drawn on the oval like the rest (greybox simplification).
Lane 0 = inside rail; lane k is LANE_PX further out (to the left of the running direction).
Heading unit: 64 per turn (0 = east, 16 = south: y grows down), the ROM's sine table.
"""
import math
from pathlib import Path

import hv_model as M

PX_PER_M = 4
STEP_M = 8                     # path table resolution (metres): the ROM interpolates between points
LANE_PX = 4                    # 1 m per lane
LANES = 14
MARGIN = 160                   # city around the oval (px)
STANDS = 200                   # above the home straight (px)
SECTOR_PX = 256
# per track: straight (m), bend radius (m), map it is drawn on
TRACKS = {
    "HV": dict(straight=306, radius=419 / math.pi, map="HV"),
    "ST": dict(straight=515, radius=435 / math.pi, map="ST"),
    "AW": dict(straight=515, radius=110, map="ST"),          # inside Sha Tin's turf, same finish x
}
GAME = Path(__file__).resolve().parents[1]


def _px(m):
    return m * PX_PER_M


def finish(track):
    """Finish post (world px) of a track: east end of the home straight."""
    t = TRACKS[track]
    host = TRACKS[t["map"]]
    x = MARGIN + _px(host["radius"]) + LANES * LANE_PX + _px(host["straight"])
    y = STANDS + (_px(host["radius"] - t["radius"]) if track != t["map"] else 0)
    return round(x), round(y)


def map_size_sectors(map_name):
    t = TRACKS[map_name]
    fx, fy = finish(map_name)
    w = fx + _px(t["radius"]) + LANES * LANE_PX + MARGIN
    h = fy + 2 * _px(t["radius"]) + LANES * LANE_PX + MARGIN
    return math.ceil(w / SECTOR_PX), math.ceil(h / SECTOR_PX)


def track_of(course):
    v = M.COURSES[course]["track"]
    return {0: "HV", 1: "ST", 2: "AW"}.get(v, v)


def walk_back(track, d_m):
    """(x, y, heading radians) of the inside rail d_m metres before the finish."""
    t = TRACKS[track]
    s, r = _px(t["straight"]), _px(t["radius"])
    fx, fy = finish(track)
    per = 2 * s + 2 * math.pi * r
    d = _px(d_m) % per
    if d <= s:                                  # home straight (top, heading east)
        return fx - d, fy, 0.0
    d -= s
    if d <= math.pi * r:                        # left bend (forward: from the bottom up to the top)
        a = d / r                               # angle walked back from the top
        cx, cy = fx - s, fy + r
        th = -a                                 # heading at that point (forward)
        return cx - r * math.sin(a), cy - r * math.cos(a), th
    d -= math.pi * r
    if d <= s:                                  # back straight (bottom, heading west)
        return fx - s + d, fy + 2 * r, -math.pi
    d -= s
    a = d / r                                   # right bend (forward: from the top down to the bottom)
    cx, cy = fx, fy + r
    return cx + r * math.sin(a), cy + r * math.cos(a), math.pi - a


def point(track, d_m, lane):
    """World px of a runner d_m metres from the finish in `lane`."""
    x, y, th = walk_back(track, d_m)
    return x + math.sin(th) * lane * LANE_PX, y - math.cos(th) * lane * LANE_PX


def table(course):
    """ROM path table, from the start to the finish every STEP_M m: (x, y, heading 0..63)."""
    tr, dist = track_of(course), M.COURSES[course]["dist"]
    out = []
    for k in range(dist // STEP_M + 1):
        x, y, th = walk_back(tr, dist - k * STEP_M)
        out.append((int(round(x)), int(round(y)), int(round(th / (2 * math.pi) * 64)) & 63))
    return out


def sine64():
    """sin(h) x 64 for heading h (64 per turn): the ROM's table."""
    return [int(round(math.sin(h * 2 * math.pi / 64) * 64)) for h in range(64)]
