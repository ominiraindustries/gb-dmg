"""HAPPY VALLEY - the stable and the week (GDD 2.2, 2.5, 2.7, 2.8): the specification of src/stable.c.
The ROM must give exactly this (tests/test_week.py): same slots, same RNG calls in the same order.

Horse (one slot): state 0 empty / 1 stable (trains and races) / 2 mare / 3 foal; the trainable
attributes VEL RES REM TEM as x16 (`a16`), SAL in points; pot[5] the ceilings (VEL RES REM TEM SAL).
Advance a week (races come later, step 1 and 3 of GDD 2.2 are skipped):
  2. training, stable horses by slot: an injured horse rests; else for VEL RES REM TEM with base b > 0:
     room = pot - a16 >> 4 (<= 0: nothing); g = (b * min(room, 32)) >> 5; g = (g * AGE[curve][age]) >> 2;
     fat > FAT_TRAIN: g >>= 1; g > 0: g = max(0, g + rng_range(5) - 2); a16 = min(a16 + g, pot * 16).
     Then fat += training fat (0..100) and, if risk > 0, the injury roll with the fatigue BEFORE:
     p = risk + max(0, (fat0 - INJ_FAT) >> 1) + max(0, (INJ_SAL - SAL) >> 3); rng_next() < p: injury
     3 + rng_range(6) weeks; then rng_next() < 32: serious, 16 + rng_range(16) weeks | 0x80, pot VEL -3.
  4. every stable horse by slot: fat -= REC_BASE + (SAL >> 3) (>= 0); injury weeks - 1 (the flag
     clears with them); idle = worked ? 0 : idle + 1 (rest or injury = no work); idle >= IDLE_WEEKS:
     VEL RES REM a16 -= IDLE_LOSS (>= pot * 8); age 2-4: VEL RES REM a16 += AGE[curve][age] (<= pot * 16).
  5. money -= BOX_COST * stable + FARM_COST * (mares + foals).
  6. week + 1; past WEEKS: week 1, season + 1 (ageing: later).
"""
import hv_model as M

T, R = M.T, M.R
TRAIN = T["training"].rows
GROW = T["growth"].rows
START = T["start"].rows
SLOTS = 12
ATTR = ("vel", "res", "rem", "tem")


def age_q(h):
    """Training multiplier in quarters for the horse's curve and age (2..8)."""
    g = GROW[h["curve"]]
    return g["a%d" % max(2, min(h["age"], 8))]


def new_game():
    st = {"week": 1, "season": 1, "money": R["MONEY0"], "fame": 0, "horses": [None] * SLOTS}
    for k, r in enumerate(START):
        h = {"state": 1 if r["state"] in ("CUADRA", 0) else 2, "name": r["name"],
             "sex": 0 if r["sex"] in ("MACHO", 0) else 1, "age": r["age"],
             "a16": [r["vel"] * 16, r["res"] * 16, r["rem"] * 16, r["tem"] * 16], "sal": r["sal"],
             "pot": [r["pvel"], r["pres"], r["prem"], r["ptem"], r["psal"]],
             "dpref": r["dpref"], "surf": r["surf"], "style": r["style"], "curve": r["curve"],
             "rating": r["rating"], "fat": 0, "injury": 0, "idle": 0, "plan": 0}
        if isinstance(h["style"], str):
            h["style"] = ("PUNTERO", "ACECHO", "CERRADOR").index(h["style"])
        if isinstance(h["curve"], str):
            h["curve"] = [g["id"] for g in GROW].index(h["curve"])
        st["horses"][k] = h
    return st


def train(h, rng):
    t = TRAIN[h["plan"]]
    fat0 = h["fat"]
    for i, a in enumerate(ATTR):
        b = t[a]
        if b <= 0:
            continue
        room = h["pot"][i] - (h["a16"][i] >> 4)
        if room <= 0:
            continue
        g = (b * min(room, 32)) >> 5
        g = (g * age_q(h)) >> 2
        if h["fat"] > R["FAT_TRAIN"]:
            g >>= 1
        if g > 0:
            g = max(0, g + rng.range(5) - 2)
        h["a16"][i] = min(h["a16"][i] + g, h["pot"][i] * 16)
    h["fat"] = M.clamp(h["fat"] + t["fat"], 0, 100)
    if t["risk"] > 0:
        p = t["risk"] + max(0, (fat0 - R["INJ_FAT"]) >> 1) + max(0, (R["INJ_SAL"] - h["sal"]) >> 3)
        if rng.next() < p:
            h["injury"] = 3 + rng.range(6)
            if rng.next() < 32:
                h["injury"] = (16 + rng.range(16)) | 0x80
                h["pot"][0] = max(10, h["pot"][0] - 3)
                h["a16"][0] = min(h["a16"][0], h["pot"][0] * 16)


def advance(st, rng):
    hs = st["horses"]
    worked = [False] * SLOTS
    for k, h in enumerate(hs):                       # 2. training
        if h and h["state"] == 1 and not h["injury"]:
            train(h, rng)
            worked[k] = h["plan"] != 0
    for k, h in enumerate(hs):                       # 4. recovery, injuries, idle, growth
        if not h or h["state"] != 1:
            continue
        h["fat"] = max(0, h["fat"] - (R["REC_BASE"] + (h["sal"] >> 3)))
        if h["injury"]:
            w = (h["injury"] & 0x7F) - 1
            h["injury"] = (w | (h["injury"] & 0x80)) if w else 0
        h["idle"] = 0 if worked[k] else min(h["idle"] + 1, 255)
        for i in range(3):
            if h["idle"] >= R["IDLE_WEEKS"]:
                h["a16"][i] = max(h["a16"][i] - R["IDLE_LOSS"], h["pot"][i] * 8)
            if 2 <= h["age"] <= 4:
                h["a16"][i] = min(h["a16"][i] + age_q(h), h["pot"][i] * 16)
    stable = sum(1 for h in hs if h and h["state"] == 1)
    farm = sum(1 for h in hs if h and h["state"] in (2, 3))
    st["money"] -= R["BOX_COST"] * stable + R["FARM_COST"] * farm       # 5.
    st["week"] += 1                                                     # 6.
    if st["week"] > R["WEEKS"]:
        st["week"], st["season"] = 1, st["season"] + 1
