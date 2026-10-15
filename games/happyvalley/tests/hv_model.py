"""HAPPY VALLEY - reference model of the race (GDD 2.4, port of design/race_proto.py with the constants
of res/data/rules.tbl and courses.tbl). The ROM must give the same result tick for tick: tests compare
finishing order, ticks and overshoot after the same seed. Integer maths; RNG = gbe_rng xorshift16.
Also the rival field (GDD 2.9) so a whole race can be rebuilt from a seed, and bots can simulate seasons.
"""
from pathlib import Path

import tables

GAME = Path(__file__).resolve().parents[1]
T = tables.load_all(GAME / "res" / "data")
R = {r["id"]: r["v"] for r in T["rules"].rows}
COURSES = {r["id"]: r for r in T["courses"].rows}
COURSE_IDS = [r["id"] for r in T["courses"].rows]
COST = [R[f"COST{k}"] for k in range(4)]
DPCT = [R[f"DPCT{k}"] for k in range(4)]
START_EFF = [R[f"START_EFF{k}"] for k in range(3)]
SPRINT_AT = [R[f"SPRINT_AT{k}"] for k in range(3)]
MISMATCH = [R[f"MISMATCH{k}"] for k in range(3)]


class Rng:
    def __init__(self, seed):
        self.s = seed

    def next(self):
        x = self.s
        x ^= (x << 7) & 0xFFFF
        x ^= x >> 9
        x ^= (x << 8) & 0xFFFF
        self.s = x
        return x & 0xFF

    def range(self, n):
        return (self.next() * n) >> 8


def clamp(v, a, b):
    return max(a, min(b, v))


def ai_horse(rng, r, dist):
    """Rival from a rating (GDD 2.9). RNG order: vel res pun tem dpref fat jock estilo surf name(2)."""
    base = 20 + (r >> 1)
    h = dict(vel=clamp(base + rng.range(17) - 8, 1, 99),
             res=clamp(base + rng.range(17) - 8 + (dist // 100 - 14) * 3, 1, 99),
             pun=clamp(base + rng.range(17) - 8, 1, 99),
             tem=30 + rng.range(51),
             dpref=clamp(dist // 100 + rng.range(5) - 2, 10, 24),
             fat=rng.range(30), jock=rng.range(8), estilo=rng.range(3), rating=r)
    h["tac"] = h["estilo"]
    h["surf"] = rng.range(5) - 2
    h["name"] = (rng.range(32), rng.range(32))
    return h


def gen_field(rng, course, lo, hi, n):
    """n rivals with ratings lo..hi, gates by Fisher-Yates, weights by rating (race_proto calibrate)."""
    dist = COURSES[course]["dist"]
    hs = [ai_horse(rng, lo + rng.range(hi - lo + 1), dist) for _ in range(n)]
    gates = list(range(1, n + 1))
    for k in range(n - 1, 0, -1):
        j = rng.range(k + 1)
        gates[k], gates[j] = gates[j], gates[k]
    for h, g in zip(hs, gates):
        h["gate"] = g
    w = [clamp(133 - (hi - h["rating"]), 113, 133) for h in hs]
    return hs, w


def run(horses, course, rng, weights):
    """Returns [(horse index, finish tick, overshoot)] in finishing order (race_proto.run)."""
    c = COURSES[course]
    dist, bk, turf = c["dist"], c["bk"], c["track"] not in ("AW", 2)   # enum: name or index
    LEN = R["LEN"]
    D16, d100 = dist * 16, dist // 100
    seg_end, acc = [], 0
    for k in range(c["nseg"]):
        acc += c[f"m{k + 1}"] * 16
        seg_end.append((acc, (c["bends"] >> k) & 1))
    final_from = seg_end[-2][0] if len(seg_end) > 1 else 0
    N, H = len(horses), []
    for i, h in enumerate(horses):
        apt = h["surf"] if turf else -h["surf"]
        vmax = R["V0"] + R["KV"] * h["vel"] - R["KW"] * (weights[i] - 113) + R["KJ"] * h["jock"] + R["KSF"] * apt
        if d100 < h["dpref"]:
            vmax -= (h["dpref"] - d100) * R["KDS"]
        if h["fat"] > R["FAT_FROM"]:
            vmax -= (h["fat"] - R["FAT_FROM"]) * R["FAT_K"]
        vmax += (rng.range(7) - 3) * R["FORMA_K"]
        x = dict(h=h, i=i, pos=0, frac=0, spd=0, ene=(R["EB"] + R["EK"] * h["res"]) * 16, lane=h["gate"] - 1,
                 vmax=vmax, dmul=8 + max(0, d100 - h["dpref"]), accL=R["ACC_L0"] + (h["pun"] >> 2),
                 acc=R["ACC_0"] + (h["pun"] >> 4), kick=h["pun"] >> 1, launch=True, eff=START_EFF[h["tac"]],
                 sprinting=False, reserve=0, cover=False, pull=0, block=-1, fin=None, target=0)
        x["sprint_at"] = SPRINT_AT[h["tac"]] + rng.range(41) - 20
        x["delay"] = rng.range(4)
        H.append(x)
    for x in H:
        if rng.next() < ((100 - x["h"]["tem"]) >> 2) + (10 - x["h"]["jock"]):
            x["delay"] += 8 + rng.range(8)
    order = sorted(range(N), key=lambda k: horses[k]["gate"])
    t = nfin = 0
    while nfin < N and t < R["MAX_TICKS"]:
        for x in H:
            if x["fin"] is not None:
                continue
            if x["delay"]:
                x["delay"] -= 1
                continue
            if (t & 3) == (x["i"] & 3):
                _think(x, H, order, t, D16, final_from, rng)
            tg = x["target"]
            if x["spd"] < tg:
                x["spd"] = min(tg, x["spd"] + (x["accL"] if x["launch"] else x["acc"]))
            else:
                x["spd"] = max(tg, x["spd"] - R["DEC"])
            if x["launch"] and x["spd"] >= x["vmax"] - (x["vmax"] >> 3):
                x["launch"] = False
            if x["block"] >= 0:
                x["spd"] = min(x["spd"], H[x["block"]]["spd"])
            prog = x["spd"]
            if _on_bend(seg_end, x["pos"]):
                prog -= ((x["spd"] >> 4) * (x["lane"] * bk)) >> 5
            p = (x["pos"] << 8 | x["frac"]) + prog
            x["pos"], x["frac"] = p >> 8, p & 0xFF
            if x["ene"]:
                dr = (COST[x["eff"]] * x["dmul"]) >> 3
                if x["pull"]:
                    dr <<= 1
                elif x["cover"]:
                    dr -= dr >> R["COVER_SH"]
                x["ene"] = max(0, x["ene"] - dr)
            if x["pull"]:
                x["pull"] -= 1
            if x["pos"] >= D16:
                x["fin"] = (t, x["pos"] - D16)
                nfin += 1
        for k in range(1, N):
            j = k
            while j > 0 and H[order[j]]["pos"] > H[order[j - 1]]["pos"]:
                order[j], order[j - 1] = order[j - 1], order[j]
                j -= 1
        t += 1
    done = sorted((x for x in H if x["fin"] is not None), key=lambda x: (x["fin"][0], -x["fin"][1]))
    return [(x["i"], x["fin"][0], x["fin"][1]) for x in done]


def _on_bend(seg_end, pos):
    for end, b in seg_end:
        if pos < end:
            return b
    return 0


def _think(x, H, order, t, D16, final_from, rng):
    h, i = x["h"], x["i"]
    LEN = R["LEN"]
    rank = order.index(i)
    rem = (D16 - x["pos"]) >> 4
    tac = h["tac"]
    if (t & 31) == i:
        if rng.next() < R["PULL_BASE"] + ((100 - h["tem"]) >> 2) + MISMATCH[abs(h["estilo"] - tac)]:
            x["pull"] = R["PULL_TICKS"]
    if x["pos"] < R["START_M"] * 16:
        eff = START_EFF[tac]
    elif rem <= x["sprint_at"]:
        eff = 1 if (h["jock"] >= 5 and x["ene"] < rem * R["SPC"] and rem > 150) else 3
    elif tac == 0:
        eff = 1 if rank <= 1 else 2
    elif tac == 1:
        eff = 1
    else:
        eff = 0
    if eff == 3 and not x["sprinting"]:
        x["sprinting"], x["reserve"] = True, x["ene"] >> R["RES_SH"]
    x["eff"] = eff
    dp = R["DPCT_TIRED"] if x["ene"] == 0 else DPCT[eff]
    tg = x["vmax"] - (((x["vmax"] >> 4) * dp) >> 4)
    if eff == 3 and x["ene"]:
        tg += x["kick"] + x["reserve"]
    x["target"] = tg
    ahead, cover, k = -1, False, rank - 1
    while k >= 0:
        j = order[k]
        g = H[j]["pos"] - x["pos"]
        if g > 2 * LEN:
            break
        if H[j]["lane"] == x["lane"] and g > 0 and H[j]["fin"] is None:
            cover = True
            if g <= LEN:
                ahead = j
            break
        k -= 1
    x["cover"], x["block"] = cover, -1
    lane_turn = (t & R["LANE_MASK"]) == (i & R["LANE_MASK"])
    if ahead >= 0 and tg > H[ahead]["spd"]:
        if lane_turn and x["lane"] < R["LANES_MAX"] and _free(x, x["lane"] + 1, H):
            x["lane"] += 1
        else:
            x["block"] = ahead
    elif lane_turn and x["lane"] > 0 and _free(x, x["lane"] - 1, H):
        if not (x["pos"] >= final_from and tac != 0 and eff == 3):
            x["lane"] -= 1


def _free(x, lane, H):
    for y in H:
        if y is x or y["fin"] is not None:
            continue
        if y["lane"] == lane and -R["FREE_BACK"] < y["pos"] - x["pos"] < R["LEN"]:
            return False
    return True


def race_from_seed(seed, course, lo, hi, n):
    """The whole debug race the ROM runs from a seed: field, then the race (same RNG stream)."""
    rng = Rng(seed)
    hs, w = gen_field(rng, course, lo, hi, n)
    return hs, w, run(hs, course, rng, w)
