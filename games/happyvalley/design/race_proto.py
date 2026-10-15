"""HAPPY VALLEY - race model prototype used to calibrate GDD section 2.4 (design tool, not a test).

The programmer ports this to tests/hv_model.py (the reference the ROM is compared with) reading the
constants from res/data/rules.tbl. Integer maths only; RNG = gbe_rng xorshift16 (7, 9, 8).
Run:  python games/happyvalley/design/race_proto.py      (prints calibration stats, ~1 min)
"""
import collections

# ---------------------------------------------------------------- rules.tbl (starting values)
LEN = 38                        # 1 length (cuerpo) = 38/16 m = 2.375 m
V0, KV, KW, KJ = 2720, 3, 2, 2  # vmax = V0 + KV*VEL - KW*(peso-113) + KJ*jockey
KDS, KSF = 6, 12                # per 100 m under dpref / per surface aptitude point
FAT_FROM, FAT_K = 50, 2         # vmax -= (fat-50)*2 when fat > 50
FORMA_K = 6                     # (rng_range(7)-3) * 6
EB, EK = 800, 12                # ene0 = (EB + EK*RES) * 16
COST = [3, 5, 8, 14]            # drain per tick (1/16 units), efforts E0..E3
DPCT = [10, 6, 3, 0]            # target = vmax - (vmax>>4)*dpct>>4
DPCT_TIRED = 32
ACC_L0, ACC_0, DEC = 24, 2, 4   # launch acc = 24 + PUN>>2, acc = 2 + PUN>>4, decel 4
START_M = 200
START_EFF = [2, 1, 0]           # puntero, acecho, cerrador
SPRINT_AT = [350, 450, 650]     # m to go (+ rng_range(41) - 20)
SPC = 20                        # jockey (skill >= 5) waits while ene < rem_m * 20
RES_SH = 7                      # reserve kick = ene >> 7 when the sprint starts
PULL_BASE = 4
MISMATCH = [0, 12, 30]
PULL_TICKS = 32
FREE_BACK = 19                  # an inner lane is free if nobody is in (pos-19, pos+38)
LANE_MASK = 7
COVER_SH = 2                    # cover: drain -= drain >> 2
LANES_MAX = 13

# courses.tbl: (bend factor, [(metres, bend?) ... from the start to the post])
COURSES = {
    ("HV", 1000): (5, [(269, 0), (419, 1), (312, 0)]),
    ("HV", 1200): (5, [(169, 1), (300, 0), (419, 1), (312, 0)]),
    ("HV", 1650): (5, [(200, 0), (419, 1), (300, 0), (419, 1), (312, 0)]),
    ("HV", 1800): (5, [(350, 0), (419, 1), (300, 0), (419, 1), (312, 0)]),
    ("ST", 1000): (4, [(1000, 0)]),
    ("ST", 1200): (4, [(335, 0), (435, 1), (430, 0)]),
    ("ST", 1400): (4, [(535, 0), (435, 1), (430, 0)]),
    ("ST", 1600): (4, [(135, 1), (600, 0), (435, 1), (430, 0)]),
    ("ST", 2000): (4, [(100, 0), (435, 1), (600, 0), (435, 1), (430, 0)]),
    ("ST", 2400): (4, [(70, 1), (430, 0), (435, 1), (600, 0), (435, 1), (430, 0)]),
    ("AW", 1200): (5, [(38, 1), (400, 0), (397, 1), (365, 0)]),
    ("AW", 1650): (5, [(91, 0), (397, 1), (400, 0), (397, 1), (365, 0)]),
}


class Rng:
    def __init__(self, seed): self.s = seed
    def next(self):
        x = self.s
        x ^= (x << 7) & 0xFFFF; x ^= x >> 9; x ^= (x << 8) & 0xFFFF
        self.s = x
        return x & 0xFF
    def range(self, n): return (self.next() * n) >> 8


def clamp(v, a, b): return max(a, min(b, v))


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
    h["name"] = (rng.range(32), rng.range(32))       # names.tbl: noun, adjective
    return h


def run(horses, course, dist, rng, weights, turf=True):
    """horses: dicts (vel res pun tem dpref surf fat jock estilo tac gate); weights: lb per horse.
    Returns the horses in finishing order, each with fin=(tick, overshoot)."""
    bk, segs = COURSES[(course, dist)]
    D16, d100 = dist * 16, dist // 100
    seg_end, acc = [], 0
    for m, b in segs:
        acc += m * 16
        seg_end.append((acc, b))
    final_from = seg_end[-2][0] if len(seg_end) > 1 else 0
    N, H = len(horses), []
    for i, h in enumerate(horses):                       # pre-race, RNG: forma, sprint noise, delay
        apt = h["surf"] if turf else -h["surf"]
        vmax = V0 + KV * h["vel"] - KW * (weights[i] - 113) + KJ * h["jock"] + KSF * apt
        if d100 < h["dpref"]: vmax -= (h["dpref"] - d100) * KDS
        if h["fat"] > FAT_FROM: vmax -= (h["fat"] - FAT_FROM) * FAT_K
        vmax += (rng.range(7) - 3) * FORMA_K
        x = dict(h=h, i=i, pos=0, frac=0, spd=0, ene=(EB + EK * h["res"]) * 16, lane=h["gate"] - 1,
                 vmax=vmax, dmul=8 + max(0, d100 - h["dpref"]), accL=ACC_L0 + (h["pun"] >> 2),
                 acc=ACC_0 + (h["pun"] >> 4), kick=h["pun"] >> 1, launch=True, eff=START_EFF[h["tac"]],
                 sprinting=False, reserve=0, cover=False, pull=0, block=-1, fin=None, target=0)
        x["sprint_at"] = SPRINT_AT[h["tac"]] + rng.range(41) - 20
        x["delay"] = rng.range(4)
        H.append(x)
    for x in H:                                          # slow starts, RNG: 1 or 2 calls per horse
        if rng.next() < ((100 - x["h"]["tem"]) >> 2) + (10 - x["h"]["jock"]):
            x["delay"] += 8 + rng.range(8)
    order = sorted(range(N), key=lambda k: horses[k]["gate"])
    t = nfin = 0
    while nfin < N and t < 8000:
        for x in H:
            if x["fin"] is not None: continue
            if x["delay"]:
                x["delay"] -= 1
                continue
            if (t & 3) == (x["i"] & 3):
                think(x, H, order, t, D16, final_from, rng)
            tg = x["target"]
            if x["spd"] < tg: x["spd"] = min(tg, x["spd"] + (x["accL"] if x["launch"] else x["acc"]))
            else: x["spd"] = max(tg, x["spd"] - DEC)
            if x["launch"] and x["spd"] >= x["vmax"] - (x["vmax"] >> 3): x["launch"] = False
            if x["block"] >= 0: x["spd"] = min(x["spd"], H[x["block"]]["spd"])
            prog = x["spd"]
            if on_bend(seg_end, x["pos"]): prog -= ((x["spd"] >> 4) * (x["lane"] * bk)) >> 5
            p = (x["pos"] << 8 | x["frac"]) + prog
            x["pos"], x["frac"] = p >> 8, p & 0xFF
            if x["ene"]:
                dr = (COST[x["eff"]] * x["dmul"]) >> 3
                if x["pull"]: dr <<= 1
                elif x["cover"]: dr -= dr >> COVER_SH
                x["ene"] = max(0, x["ene"] - dr)
            if x["pull"]: x["pull"] -= 1
            if x["pos"] >= D16:
                x["fin"] = (t, x["pos"] - D16)
                nfin += 1
        for k in range(1, N):                            # stable insertion sort, pos descending
            j = k
            while j > 0 and H[order[j]]["pos"] > H[order[j - 1]]["pos"]:
                order[j], order[j - 1] = order[j - 1], order[j]
                j -= 1
        t += 1
    return sorted(H, key=lambda x: (x["fin"][0], -x["fin"][1]))


def on_bend(seg_end, pos):
    for end, b in seg_end:
        if pos < end: return b
    return 0


def think(x, H, order, t, D16, final_from, rng):
    h, i = x["h"], x["i"]
    rank = order.index(i)
    rem = (D16 - x["pos"]) >> 4
    tac = h["tac"]
    if (t & 31) == i:                                    # pull (fighting the jockey)
        if rng.next() < PULL_BASE + ((100 - h["tem"]) >> 2) + MISMATCH[abs(h["estilo"] - tac)]:
            x["pull"] = PULL_TICKS
    if x["pos"] < START_M * 16: eff = START_EFF[tac]
    elif rem <= x["sprint_at"]:
        eff = 1 if (h["jock"] >= 5 and x["ene"] < rem * SPC and rem > 150) else 3
    elif tac == 0: eff = 1 if rank <= 1 else 2
    elif tac == 1: eff = 1
    else: eff = 0
    if eff == 3 and not x["sprinting"]:
        x["sprinting"], x["reserve"] = True, x["ene"] >> RES_SH
    x["eff"] = eff
    dp = DPCT_TIRED if x["ene"] == 0 else DPCT[eff]
    tg = x["vmax"] - (((x["vmax"] >> 4) * dp) >> 4)
    if eff == 3 and x["ene"]: tg += x["kick"] + x["reserve"]
    x["target"] = tg
    ahead, cover, k = -1, False, rank - 1                # nearest horse ahead in my lane
    while k >= 0:
        j = order[k]
        g = H[j]["pos"] - x["pos"]
        if g > 2 * LEN: break
        if H[j]["lane"] == x["lane"] and g > 0 and H[j]["fin"] is None:
            cover = True
            if g <= LEN: ahead = j
            break
        k -= 1
    x["cover"], x["block"] = cover, -1
    lane_turn = (t & LANE_MASK) == (i & LANE_MASK)
    if ahead >= 0 and tg > H[ahead]["spd"]:
        if lane_turn and x["lane"] < LANES_MAX and free(x, x["lane"] + 1, H): x["lane"] += 1
        else: x["block"] = ahead
    elif lane_turn and x["lane"] > 0 and free(x, x["lane"] - 1, H):
        if not (x["pos"] >= final_from and tac != 0 and eff == 3):
            x["lane"] -= 1


def free(x, lane, H):
    for y in H:
        if y is x or y["fin"] is not None: continue
        if y["lane"] == lane and -FREE_BACK < y["pos"] - x["pos"] < LEN: return False
    return True


def fmt(tick):
    cs = tick * 4
    return f"{cs // 6000}:{(cs // 100) % 60:02d}.{cs % 100:02d}"


def calibrate(course, dist, races=90, band=(40, 60), seed=0xBEEF):
    N = 12 if course == "HV" else 14
    rng = Rng(seed)
    wr, wg, wt, rt = (collections.Counter() for _ in range(4))
    times = []
    for _ in range(races):
        hs = []
        for g in range(N):
            hs.append(ai_horse(rng, band[0] + rng.range(band[1] - band[0] + 1), dist))
        gates = list(range(1, N + 1))                # Fisher-Yates, GDD 2.9
        for k in range(N - 1, 0, -1):
            j = rng.range(k + 1)
            gates[k], gates[j] = gates[j], gates[k]
        for h, g in zip(hs, gates): h["gate"] = g
        w = [clamp(133 - (band[1] - h["rating"]), 113, 133) for h in hs]
        res = run(hs, course, dist, rng, w, course != "AW")
        times.append(res[0]["fin"][0])
        wr[(res[0]["h"]["rating"] - band[0]) * 3 // (band[1] - band[0] + 1)] += 1
        wg[(res[0]["h"]["gate"] - 1) * 3 // N] += 1
        wt[res[0]["h"]["tac"]] += 1
        for x in res: rt[x["h"]["tac"]] += 1
    print(f"{course} {dist}: winner {fmt(sum(times) // races)}  wins by rating third {[wr[k] for k in range(3)]}"
          f"  by gate third {[wg[k] for k in range(3)]}  tactic index {[round(100 * wt[k] / rt[k] * N) for k in range(3)]}")


if __name__ == "__main__":
    for c, d in (("HV", 1200), ("HV", 1650), ("ST", 1200), ("ST", 1600), ("ST", 2400)):
        calibrate(c, d)
