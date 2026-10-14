"""Exact 8.8 fixed-point jump simulator: verify design numbers before building levels.

Simulates the frame order used by games/platformer/src/player.c (common platformer loop):
  1. jump: vy = jump_v (frame 0)
  2. every frame: vy += grav_hold if (vy < 0 and A still held) else grav; vy = min(vy, fall_max)
  3. y += vy with an 8-bit sub-pixel accumulator (starting at 0), x += vx likewise
Heights/distances are in pixels, times in frames (59.73 fps). A test in games/platformer checks
that this model matches the ROM, so designers (game-designer agent) and level lints can rely on it.

    python harness/physics.py --jump -0x400 --grav-hold 0x20 --grav 0x50 --fall-max 0x400 --vx 0x200
    python harness/physics.py --game platformer          # the GDD values of games/platformer
"""
import argparse


def simulate_jump(jump_v, grav_hold, grav, fall_max, vx=0, hold_frames=10**6, max_frames=600):
    """Returns dict: height (px, peak above take-off), apex_frame, air_frames (back to take-off
    height), distance (px travelled horizontally until then), path [(x, y_up)] per frame."""
    vy = jump_v
    y = 0           # pixels, positive = down (screen coordinates), take-off at 0
    ys = 0          # sub-pixel accumulator (0..255)
    x, xs = 0, 0
    peak, apex = 0, 0
    path = []
    for f in range(1, max_frames + 1):
        held = f <= hold_frames
        vy += grav_hold if (vy < 0 and held) else grav
        if vy > fall_max:
            vy = fall_max
        t = ys + (vy & 0xFF)
        ys = t & 0xFF
        y += (vy >> 8) + (t >> 8)           # python >> is arithmetic, like (int8_t)(vy >> 8)
        t = xs + (vx & 0xFF)
        xs = t & 0xFF
        x += (vx >> 8) + (t >> 8)
        path.append((x, -y))
        if -y > peak:
            peak, apex = -y, f
        if y >= 0 and f > 1:
            return {"height": peak, "apex_frame": apex, "air_frames": f, "distance": x, "path": path}
    return {"height": peak, "apex_frame": apex, "air_frames": None, "distance": x, "path": path}


def max_step_up(height, block=16, margin=1):
    """Whole blocks a jump of `height` px can climb (feet must clear the top by `margin`)."""
    return max(0, (height - margin) // block)


def max_gap(distance, block=16, hitbox_w=10):
    """Whole empty blocks a jump covers between two ledges (take-off at the very edge)."""
    return max(0, (distance + hitbox_w) // block - 1)


GAMES = {   # GDD values (games/<game>/design/gdd.md); keep in sync with the code
    "platformer": {"jump_v": -0x0380, "jump_v_run": -0x0400, "grav_hold": 0x0020, "grav": 0x0050,
                   "fall_max": 0x0400, "walk": 0x0140, "run": 0x0200},
}


def report(p):
    rows = []
    for name, jv, vx in (("tap (A 1 frame)", p["jump_v"], 0),
                         ("walk, A held", p["jump_v"], p["walk"]),
                         ("run, A held", p["jump_v_run"], p["run"])):
        hold = 1 if name.startswith("tap") else 10**6
        r = simulate_jump(jv, p["grav_hold"], p["grav"], p["fall_max"], vx, hold)
        rows.append((name, r["height"], r["air_frames"], r["distance"],
                     max_step_up(r["height"]), max_gap(r["distance"])))
    out = [f"{'jump':<18}{'height px':>10}{'air f':>7}{'dist px':>9}{'step up':>9}{'gap':>5}"]
    for r in rows:
        out.append(f"{r[0]:<18}{r[1]:>10}{r[2]:>7}{r[3]:>9}{r[4]:>9}{r[5]:>5}")
    return "\n".join(out)


def _num(s):
    return int(s, 0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", choices=sorted(GAMES))
    ap.add_argument("--jump", type=_num)
    ap.add_argument("--grav-hold", type=_num)
    ap.add_argument("--grav", type=_num)
    ap.add_argument("--fall-max", type=_num, default=0x0400)
    ap.add_argument("--vx", type=_num, default=0)
    ap.add_argument("--hold", type=int, default=10**6, help="frames A is held")
    a = ap.parse_args()
    if a.game:
        print(report(GAMES[a.game]))
    else:
        r = simulate_jump(a.jump, a.grav_hold, a.grav, a.fall_max, a.vx, a.hold)
        print(f"height {r['height']} px, apex frame {r['apex_frame']}, air {r['air_frames']} f, "
              f"distance {r['distance']} px -> climbs {max_step_up(r['height'])} blocks, "
              f"clears {max_gap(r['distance'])}-block gaps")
