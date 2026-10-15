"""MADRIGUERA QA bot: walks Tilo cell by cell (BFS on the map's SOLID cells) to a goal, fights the
babosas of the room with the sword and leaves through a doorway. Used by test_qa.py for the frame
budget (run_bot must make progress) and the contact sheet."""
from collections import deque

from maz_nav import DIRS, MAP, ROOM_H, ROOM_W, SOLID, enemies

BUTTONS = ("up", "down", "left", "right", "a")
# doorway cells (outside the room) to leave it: (room) -> {target room: cell beyond the border}
EXITS = {
    (1, 3): {(1, 2): (14, 23)},
    (1, 2): {(1, 3): (14, 24), (0, 2): (9, 19)},
    (0, 2): {(1, 2): (10, 19)},
}


def solid(x, y):
    return SOLID[MAP.at(x, y)]


def feet(gb):
    return (gb.u16("lx") + 8) >> 4, (gb.u16("ly") + 12) >> 4


def path(start, goal, room):
    """4-connected BFS over non-solid cells inside the room (+ the goal, which may be a doorway
    cell of the next room)."""
    c, r = room
    x0, y0 = c * ROOM_W, r * ROOM_H

    def ok(x, y):
        if (x, y) == goal:
            return not solid(x, y)
        return x0 <= x < x0 + ROOM_W and y0 <= y < y0 + ROOM_H and not solid(x, y)

    prev, q = {start: None}, deque([start])
    while q:
        p = q.popleft()
        if p == goal:
            out = []
            while p is not None:
                out.append(p)
                p = prev[p]
            return out[::-1]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (p[0] + dx, p[1] + dy)
            if n not in prev and ok(*n):
                prev[n] = p
                q.append(n)
    return None


def press(gb, want):
    for b in BUTTONS:
        if b in want:
            gb.pyboy.button_press(b)
        else:
            gb.pyboy.button_release(b)


def toward(gb, cell):
    """Buttons that bring Tilo's feet box into `cell` (lx = 16x, ly = 16y - 4)."""
    tx, ty = cell[0] * 16, cell[1] * 16 - 4
    lx, ly, out = gb.u16("lx"), gb.u16("ly"), set()
    if lx < tx - 1:
        out.add("right")
    elif lx > tx + 1:
        out.add("left")
    if ly < ty - 1:
        out.add("down")
    elif ly > ty + 1:
        out.add("up")
    return out


class Bot:
    """route: list of rooms to visit in order, e.g. [(1, 3), (1, 2), (0, 2), (1, 2), (1, 3)].
    In each room: kill its babosas (fight_frames at most), then leave to the next room."""

    def __init__(self, route, fight_frames=600):
        self.route, self.leg, self.fight_frames = route, 0, fight_frames
        self.room_t, self.last_room, self.kills, self.a_t = 0, None, 0, 0

    def progress(self, gb):
        return self.leg * 1000 + self.kills * 50 + min(self.room_t, 49)

    def step(self, gb, f):
        room = (gb.u8("room_c"), gb.u8("room_r"))
        if gb.u8("sliding") or gb.u8("trans_phase") or gb.u8("scene") != 1:
            press(gb, set())
            return
        if room != self.last_room:
            self.last_room, self.room_t = room, 0
            if self.leg + 1 < len(self.route) and room == self.route[self.leg + 1]:
                self.leg += 1
        self.room_t += 1
        alive = gb.u8("en_alive")
        if hasattr(self, "_alive") and alive < self._alive:
            self.kills += self._alive - alive
        self._alive = alive
        here = feet(gb)
        want = set()
        if alive and self.room_t < self.fight_frames:
            want = self.fight(gb, here, room)
        elif self.leg + 1 < len(self.route):
            goal = EXITS[room][self.route[self.leg + 1]]
            p = path(here, goal, room)
            if p and len(p) > 1:
                want = toward(gb, p[1])
            elif p:
                want = toward(gb, goal)
        press(gb, want)

    def fight(self, gb, here, room):
        best = None
        for _, ex, ey in enemies(gb):
            for sx, face in ((ex - 1, "right"), (ex + 1, "left")):
                if solid(sx, ey):
                    continue
                p = path(here, (sx, ey), room)
                if p and (best is None or len(p) < len(best[0])):
                    best = (p, face)
        if best is None:
            return set()
        p, face = best
        if len(p) == 1:
            self.a_t += 1
            if gb.u8("ldir") != DIRS[face]:
                return {face}
            return {"a"} if self.a_t % 6 < 2 else set()
        return toward(gb, p[1])
