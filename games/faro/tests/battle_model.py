"""FARO battle model: the rules of src/rpg/battle_core.c in Python, with the SAME rng_next() calls in
the same order. test_battle.py runs random battles in the ROM and here and compares every number.
Change one, change the other. Also usable by the balance bots (playtester)."""
from pathlib import Path

import tables

GAME = Path(__file__).resolve().parents[1]
T = tables.load_all(GAME / "res" / "data")
RULE = {r["id"]: r["v"] for r in T["rules"].rows}
ST = {r["id"]: i for i, r in enumerate(T["statuses"].rows)}
NONE = 0xFF
B_ONGOING, B_HUNTED, B_CAPTURED, B_FLED, B_ESCAPED, B_FAINTED = range(6)
ACT_ATTACK, ACT_SKILL, ACT_ITEM, ACT_GADGET, ACT_CAPTURE, ACT_FLEE = range(6)
(EV_USE, EV_MISS, EV_HIT, EV_STATUS, EV_STATUS_END, EV_SKIP, EV_DOT, EV_HEAL, EV_EN, EV_REVEAL, EV_AIM,
 EV_DEBUFF, EV_DEFUP, EV_BUFF, EV_BAIT, EV_THROW, EV_SHAKES, EV_NOCOND, EV_FLEE, EV_STEAL, EV_WATCH,
 EV_END) = range(22)
USE_WEAPON, USE_SKILL, USE_ITEM, USE_GADGET, USE_MOVE = range(5)
EV_MAX = 24


def _enum(table, col, name):
    return next(c for c in T[table].cols if c["name"] == col)["values"].index(name)


def _ref(v):
    return NONE if v is None else v


class Rng:
    def __init__(self, state):
        self.state = state

    def next(self):
        s = self.state
        s ^= (s << 7) & 0xFFFF
        s ^= s >> 9
        s ^= (s << 8) & 0xFFFF
        self.state = s
        return s & 0xFF

    def range(self, n):
        return (self.next() * n) >> 8


class Player:
    """Leo's battle-relevant state (globals of src/rpg/player.c)."""

    def __init__(self, level=2, armor=NONE):
        self.level, self.armor = level, armor
        self.inv = [0] * 128
        self.reg_seen, self.reg_caught = set(), set()
        self.kills = [0] * 48
        self.full = []
        self.buff, self.buff_steps = NONE, 0
        self.st, self.st_t = NONE, 0
        self.sac = RULE["SAC_START"]
        self.stats()
        self.pv, self.en = self.pv_max, self.en_max
        self.xp = T["player"].rows[level - 1]["xpacum"]

    def stats(self):
        r = T["player"].rows[self.level - 1]
        self.pv_max, self.en_max, self.atk, self.defn, self.agi = r["pv"], r["en"], r["atq"], r["def"], r["agi"]
        if self.armor != NONE:
            self.defn += T["items"].rows[self.armor]["val"]

    def gain_xp(self, n):
        ups = 0
        self.xp += n
        while self.level < 40:
            nxt = T["player"].rows[self.level]
            if self.xp < nxt["xpacum"]:
                break
            opv, oen = self.pv_max, self.en_max
            self.level += 1
            ups += 1
            self.stats()
            self.pv += self.pv_max - opv
            self.en += self.en_max - oen
        return ups


class Battle:
    def __init__(self, player, rng, species, level, free):
        self.p, self.rng = player, rng
        sp = T["species"].rows[species]
        self.sp = sp
        self.species, self.level = species, level
        self.moves = [None if _ref(sp[f"m{k}"]) == NONE else T["moves"].rows[sp[f"m{k}"]] for k in (1, 2, 3, 4)]
        self.mid = [_ref(sp[f"m{k}"]) for k in (1, 2, 3, 4)]
        self.w = [sp[f"w{k}"] for k in (1, 2, 3, 4)]
        self.cpv_max = min(255, 10 + ((sp["tpv"] * level * 3) >> 3))
        self.cpv = self.cpv_max
        self.catk = self.cstat(4, sp["tat"])
        self.cdef = self.cstat(3, sp["tdf"])
        self.cagi = self.cstat(2, sp["tag"])
        self.cst, self.cst_t = NONE, 0
        self.ent_t = self.calm_t = self.lit_t = self.def_t = self.down = 0
        self.def_sh = 0
        self.pdeb_t = self.pdeb_sh = self.cdeb_t = self.cdeb_sh = 0
        self.fly = sp["vuela"]
        self.bait = RULE["QBAIT_NONE"]
        self.flee_tries, self.last_move, self.aim, self.turn = 0, NONE, 0, 0
        self.result, self.free, self.seen = B_ONGOING, free, 0
        self.ev = []
        self.loot = []
        self.xp, self.levelups, self.new_species = 0, 0, 0
        player.reg_seen.add(species)

    def cstat(self, base, tier):
        return (base + ((tier * self.level * 3) >> 4)) & 0xFF

    def e(self, t, a=0, b=0, c=0):
        if len(self.ev) < EV_MAX:
            self.ev.append((t, a & 0xFF, b & 0xFF, c & 0xFF))

    def st_row(self, st):
        return T["statuses"].rows[st]

    def st_turns(self, r):
        if r["tmax"] > r["tmin"]:
            return r["tmin"] + self.rng.range(r["tmax"] - r["tmin"] + 1)
        return r["tmin"]

    # ---- effective stats
    def p_atk(self):
        a = self.p.atk
        if self.p.buff == T["buffs"].ids["FUERZA"]:
            a = (a + (a >> 2)) & 0xFF
        if self.pdeb_t:
            a -= a >> self.pdeb_sh
        return a

    def p_def(self):
        d = self.p.defn
        return (d + (d >> 2)) & 0xFF if self.p.buff == T["buffs"].ids["CORAZA"] else d

    def p_agi(self):
        a = self.p.agi
        if self.p.buff == T["buffs"].ids["AGIL"]:
            a = (a + (a >> 2)) & 0xFF
        if self.p.sac == 0:
            a >>= RULE["FAINT_AGI_SH"]
        return a

    def c_def(self):
        return (self.cdef + (self.cdef >> self.def_sh)) & 0xFF if self.def_t else self.cdef

    def c_agi(self):
        return self.cagi >> 1 if self.ent_t else self.cagi

    def c_flying(self):
        return self.fly and not self.down and not self.ent_t

    def r16(self, atk, d):
        d = max(d, RULE["DEF_MIN"])
        r = (atk * (1024 // d)) >> 6
        return max(RULE["R16_MIN"], min(RULE["R16_MAX"], r))

    def attack(self, side, pot, dtype, acc, crit_t, st, stp, mul8, suave, defsh):
        if side == 0:
            atk, df, agi_a, agi_d = self.p_atk(), self.c_def(), self.p_agi(), self.c_agi()
        else:
            atk, df, agi_a, agi_d = self.catk, self.p_def(), self.c_agi(), self.p_agi()
        if defsh:
            df >>= defsh
        hit = True
        if not (side == 0 and self.aim) and acc != 255:
            a = acc
            if agi_d > agi_a:
                a -= RULE["ACC_AGI"] * (agi_d - agi_a)
            if a < RULE["ACC_MIN"]:
                a = RULE["ACC_MIN"]
            if (self.p.st if side == 0 else self.cst) == ST["CEGADO"]:
                a >>= 1
            if side == 0 and self.c_flying():
                a -= RULE["FLY_ACC"]
            hit = self.rng.next() < (a if a >= 0 else 0) % 256
        if not hit:
            self.e(EV_MISS, side)
            return 0
        d = (pot * self.r16(atk, df)) >> 4
        bit, f = 1 << dtype, 0
        if side == 0:
            if self.sp["inmune"] & bit:
                self.e(EV_HIT, 1, 0, 8)
                return 0
            if self.sp["debil"] & bit:
                d <<= 1
                f |= 2
            elif self.sp["resiste"] & bit:
                d >>= 1
                f |= 4
        if not crit_t:
            crit_t = RULE["CRIT"]
        if side == 0 and self.aim:
            crit_t = RULE["CRIT_AIM"]
        if self.rng.next() < crit_t:
            d += d >> 1
            f |= 1
        if side == 0:
            if self.p.sac == 0:
                d >>= RULE["FAINT_DMG_SH"]
            elif self.p.sac < RULE["SAC_HUNGRY"]:
                d -= d >> RULE["HUNGRY_DMG_SH"]
            if self.p.st == ST["QUEMADO"]:
                d -= d >> 2
        elif self.cst == ST["QUEMADO"]:
            d -= d >> 2
        d = ((d * mul8) & 0xFFFF) >> 3
        d -= (d * (self.rng.next() & RULE["DMG_RND"])) >> 8
        d = max(d, 1)
        d = min(d, 255)
        if side == 0:
            if suave and d >= self.cpv:
                d = self.cpv - 1
            self.cpv -= min(d, self.cpv)
        else:
            self.p.pv -= min(d, self.p.pv)
        self.e(EV_HIT, 1 if side == 0 else 0, d, f)
        if side == 0:
            self.aim = 0
        if st != NONE and stp and self.rng.next() < stp:
            self.apply_status(1 if side == 0 else 0, st)
        if d:
            ts = self.cst if side == 0 else self.p.st
            if ts != NONE:
                r = self.st_row(ts)
                if r["despierta"] and self.rng.next() < r["despierta"]:
                    self.end_status(1 if side == 0 else 0)
        return d

    def apply_status(self, target, st):
        r = self.st_row(st)
        if r["kind"] == _enum("statuses", "kind", "PRINCIPAL"):
            if (self.cst if target else self.p.st) != NONE:
                return
            t = self.st_turns(r)
            if target:
                self.cst, self.cst_t = st, t
            else:
                self.p.st, self.p.st_t = st, t
        else:
            if target == 0:
                return
            t = self.st_turns(r)
            if st == ST["ENREDADO"]:
                self.ent_t = t
            elif st == ST["CALMADO"]:
                self.calm_t = t
            elif st == ST["ILUMINADO"]:
                self.lit_t = t
            elif st == ST["DERRIBADO"]:
                self.down = 1
        self.e(EV_STATUS, target, st)

    def end_status(self, target):
        st = self.cst if target else self.p.st
        if st == NONE:
            return
        if target:
            self.cst, self.cst_t = NONE, 0
        else:
            self.p.st, self.p.st_t = NONE, 0
        self.e(EV_STATUS_END, target, st)

    def loses_turn(self, target):
        st = self.cst if target else self.p.st
        if st == NONE or not self.st_row(st)["pierde"]:
            return False
        self.e(EV_SKIP, target, st)
        return True

    def creature_down(self):
        if self.sp["beh"] == _enum("species", "beh", "GUARDIAN"):
            self.cpv = 0
            if self.cst != ST["RENDIDO"]:
                self.cst = NONE
                self.apply_status(1, ST["RENDIDO"])
            return
        self.result = B_HUNTED

    def give_xp(self, doubled):
        self.xp = ((self.sp["xp"] * self.level) >> RULE["XP_SH"]) + RULE["XP_ADD"]
        if doubled:
            self.xp <<= RULE["XP_NEW_SH"]

    def roll_loot(self):
        sp = self.sp
        self.loot = []
        if _ref(sp["b1"]) != NONE:
            n = sp["b1lo"]
            if sp["b1hi"] > sp["b1lo"]:
                n += self.rng.range(sp["b1hi"] - sp["b1lo"] + 1)
            if self.p.buff == T["buffs"].ids["CAZADOR"]:
                n += 1
            self.loot.append((sp["b1"], n))
        if _ref(sp["b2"]) != NONE and self.rng.next() < sp["b2p"]:
            self.loot.append((sp["b2"], 1))
        if _ref(sp["b3"]) != NONE and self.rng.next() < sp["b3p"]:
            self.loot.append((sp["b3"], 1))

    # ---- Leo's actions
    def use_weapon(self, weapon, mul8, suave, defsh, hits):
        w = T["items"].rows[weapon]
        while hits and self.result == B_ONGOING and self.cpv:
            hits -= 1
            self.attack(0, w["pot"], _ref(w["dtype"]), w["acc"], w["crit"], _ref(w["st"]), w["stp"], mul8, suave, defsh)
            if not self.cpv:
                self.creature_down()

    def do_skill(self, sid, weapon):
        s = T["skills"].rows[sid]
        self.p.en = self.p.en - s["en"] if self.p.en >= s["en"] else 0
        self.e(EV_USE, 0, USE_SKILL, sid)
        ef = T["skills"].cols[[c["name"] for c in T["skills"].cols].index("efecto")]["values"][s["efecto"]]
        if ef == "ENERGIA":
            self.p.en = min(self.p.en_max, self.p.en + s["val"])
            self.e(EV_EN, 0, s["val"])
        elif ef == "VER":
            self.seen = 1
            self.e(EV_REVEAL, 1)
        elif ef == "ATAQUE":
            if _ref(s["dtype"]) == NONE:
                self.use_weapon(weapon, s["mul"] or 8, s["suave"], s["defsh"], s["golpes"] or 1)
            else:
                d = self.attack(0, s["pot"], s["dtype"], 255, 0, _ref(s["st"]), s["stp"], s["mul"] or 8, s["suave"], s["defsh"])
                if not self.cpv:
                    self.creature_down()
                if s["retro"] and d:
                    d >>= s["retro"]
                    self.p.pv -= min(d, self.p.pv)
                    self.e(EV_HIT, 0, d, 0)
        elif ef == "ESTADO":
            stp = s["stp2"] if s["fams"] & (1 << self.sp["fam"]) else s["stp"]
            if self.rng.next() < stp:
                self.apply_status(1, _ref(s["st"]))
            else:
                self.e(EV_MISS, 0)
        elif ef == "CURA":
            h = self.p.pv_max >> s["val"]
            self.p.pv = min(self.p.pv_max, self.p.pv + h)
            self.e(EV_HEAL, 0, h)
            if s["limpia"]:
                self.end_status(0)
        elif ef == "PUNTERIA":
            self.aim = 1
            self.e(EV_AIM)
        elif ef == "DEBUFF":
            self.cdeb_t, self.cdeb_sh = s["turnos"], s["val"]
            self.catk -= self.catk >> s["val"]
            self.e(EV_DEBUFF, 1)

    def do_item(self, iid):
        it = T["items"].rows[iid]
        if self.p.inv[iid]:
            self.p.inv[iid] -= 1
        self.e(EV_USE, 0, USE_ITEM, iid)
        if it["sac"]:
            self.p.sac = min(RULE["SAC_MAX"], self.p.sac + it["sac"])
        if it["pv"]:
            k = self.p.pv_max - self.p.pv if it["pv"] == 255 else it["pv"]
            self.p.pv = min(self.p.pv_max, self.p.pv + k)
            self.e(EV_HEAL, 0, k)
        if it["en"]:
            self.p.en = min(self.p.en_max, self.p.en + it["en"])
        if it["cura"] and self.p.st != NONE and self.p.st < 8 and it["cura"] & (1 << self.p.st):
            self.end_status(0)
        if _ref(it["buff"]) != NONE:
            self.p.buff, self.p.buff_steps = it["buff"], it["bpasos"]
            self.e(EV_BUFF, 0, it["buff"])
        if _ref(it["st"]) != NONE and it["stp"] and self.rng.next() < it["stp"]:
            self.apply_status(0, it["st"])

    def do_gadget(self, iid):
        it = T["items"].rows[iid]
        if it["cat"] != _enum("items", "cat", "LLAVE") and self.p.inv[iid]:
            self.p.inv[iid] -= 1
        self.e(EV_USE, 0, USE_GADGET, iid)
        ef = T["items"].cols[[c["name"] for c in T["items"].cols].index("efecto")]["values"][it["efecto"]]
        if ef == "RED":
            if self.rng.next() < it["stp"]:
                self.apply_status(1, ST["ENREDADO"])
            else:
                self.e(EV_MISS, 0)
            if not self.c_flying() and self.fly and not self.down:
                self.down = 1
                self.e(EV_STATUS, 1, ST["DERRIBADO"])
        elif ef == "CEBO":
            ok = 1 if (self.sp["come"] & it["cebo"]) else 0
            if ok:
                self.calm_t = RULE["BAIT_TURNS"]
                self.bait = RULE["QBAIT_FAV"] if iid == _ref(self.sp["cebo"]) else RULE["QBAIT_OTHER"]
            self.e(EV_BAIT, 1, ok)
        elif ef == "ATAQUE":
            self.attack(0, it["pot"], _ref(it["dtype"]), it["acc"], it["crit"], _ref(it["st"]), it["stp"], 8, 0, 0)
            if not self.cpv:
                self.creature_down()
            if self.result == B_ONGOING and it["derriba"] and self.fly and not self.down and self.rng.next() < it["derriba"]:
                self.down = 1
                self.e(EV_STATUS, 1, ST["DERRIBADO"])
        elif ef == "ESTADO":
            if self.rng.next() < it["acc"] and self.rng.next() < it["stp"]:
                self.apply_status(1, _ref(it["st"]))
            else:
                self.e(EV_MISS, 0)
        elif ef == "ILUMINAR":
            self.apply_status(1, ST["ILUMINADO"])
            if self.sp["hor"] == _enum("species", "hor", "NOCHE") and self.rng.next() < RULE["LAMP_NIGHT_CEG"]:
                self.apply_status(1, ST["CEGADO"])
        elif ef == "DERRIBAR":
            if self.fly and not self.down:
                self.down = 1
                self.e(EV_STATUS, 1, ST["DERRIBADO"])
            else:
                self.e(EV_MISS, 0)

    def q_status(self):
        q = RULE["QST_NONE"]
        if self.cst != NONE:
            q = self.st_row(self.cst)["q"]
        for flag, st in ((self.ent_t, "ENREDADO"), (self.down, "DERRIBADO"), (self.calm_t, "CALMADO")):
            if flag:
                q = max(q, self.st_row(ST[st])["q"])
        return q

    def do_capture(self, lantern):
        it, sp = T["items"].rows[lantern], self.sp
        v = sp["catch"]
        if self.p.inv[lantern]:
            self.p.inv[lantern] -= 1
        self.e(EV_THROW, 0, lantern)
        c, m = self.cpv, self.cpv_max
        q = RULE["QHP_12"] if (c << 3) <= m else RULE["QHP_25"] if (c << 2) <= m else RULE["QHP_50"] if (c << 1) <= m else RULE["QHP_HI"]
        v = (v * q) >> 2
        v = (v * self.q_status()) >> 2
        q = it["val"]
        if _ref(it["fam"]) != NONE and it["fam"] == sp["fam"]:
            q = it["val2"]
        if self.p.buff == T["buffs"].ids["MANO_FIRME"]:
            q += 2
        v = 255 if it["val"] == 255 else (v * (q & 0xFF)) >> 2
        v = (v * self.bait) >> 2
        cond = True
        cn = T["species"].cols[[cc["name"] for cc in T["species"].cols].index("cond")]["values"][sp["cond"]]
        if cn == "ESTADO":
            cond = self.cst == _ref(sp["cond_st"])
        elif cn == "SUELO":
            cond = bool(self.down or self.ent_t)
        elif cn == "FAROL":
            cond = lantern == _ref(sp["cond_it"])
        if not cond:
            v = 0
        roll = self.rng.next()
        if v >= 255 or roll < v:
            self.e(EV_SHAKES, 1, 3, 1)
            self.new_species = self.species not in self.p.reg_caught
            if self.new_species:
                self.p.reg_caught.add(self.species)
            elif len(self.p.full) < 24:
                self.p.full.append((self.species, self.level))
            self.give_xp(self.new_species)
            self.result = B_CAPTURED
            return
        shakes = 2 if roll < (v << 1) else 1 if roll < (v << 2) else 0
        self.e(EV_SHAKES, 1, shakes, 0)
        if not cond:
            self.e(EV_NOCOND, 1)
        beh = sp["beh"]
        if beh in (_enum("species", "beh", "ASUSTADIZO"), _enum("species", "beh", "VOLADOR")) and self.rng.next() < sp["escapa"]:
            self.e(EV_FLEE, 1, 1)
            self.result = B_ESCAPED

    def do_flee(self):
        self.flee_tries += 1
        if self.sp["beh"] == _enum("species", "beh", "GUARDIAN"):
            ok = 0
        elif self.ent_t:
            ok = 1
        else:
            p = RULE["FLEE_BASE"] + RULE["FLEE_AGI"] * (self.p_agi() - self.c_agi()) + RULE["FLEE_TRY"] * (self.flee_tries - 1)
            p = max(RULE["FLEE_MIN"], min(RULE["FLEE_MAX"], p))
            ok = 1 if self.rng.next() < p else 0
        self.e(EV_FLEE, 0, ok)
        if ok:
            self.result = B_FLED

    def player_act(self, kind, iid, weapon):
        if self.loses_turn(0):
            return
        if kind == ACT_ATTACK:
            self.e(EV_USE, 0, USE_WEAPON, iid)
            self.use_weapon(iid, 8, 0, 0, 1)
        elif kind == ACT_SKILL:
            self.do_skill(iid, weapon)
        elif kind == ACT_ITEM:
            self.do_item(iid)
        elif kind == ACT_GADGET:
            self.do_gadget(iid)
        elif kind == ACT_CAPTURE:
            self.do_capture(iid)
        elif kind == ACT_FLEE:
            self.do_flee()

    # ---- AI
    def mv_ef(self, k):
        return T["moves"].cols[[c["name"] for c in T["moves"].cols].index("efecto")]["values"][self.moves[k]["efecto"]]

    def choose_move(self):
        if (self.cpv << RULE["AI_LOW_SH"]) <= self.cpv_max:
            for k in range(4):
                if self.mid[k] == NONE:
                    continue
                if self.mv_ef(k) in ("HUIR", "CURA"):
                    if self.rng.next() < RULE["AI_LOW_P"]:
                        return k
                    break
        w, total = [0] * 4, 0
        for k in range(4):
            w[k] = 0 if self.mid[k] == NONE else self.w[k]
            if self.mid[k] != NONE:
                ef = self.mv_ef(k)
                if ef == "ESTADO" and self.p.st == NONE:
                    w[k] = (w[k] * RULE["AI_ST_MUL"]) & 0xFF
                if self.calm_t and ef == "DANO":
                    w[k] = 0
                if ef == "DEFENSA" and self.last_move == k:
                    w[k] = 0
                if ef == "HUIR" and (self.ent_t or self.down):
                    w[k] = 0
            total = (total + w[k]) & 0xFF
        if not total:
            return NONE
        r = self.rng.range(total)
        for k in range(4):
            if r < w[k]:
                return k
            r -= w[k]
        return NONE

    def creature_act(self):
        if self.loses_turn(1):
            return
        k = self.choose_move()
        if k == NONE:
            self.e(EV_WATCH, 1)
            return
        self.last_move = k
        mv = self.moves[k]
        self.e(EV_USE, 1, USE_MOVE, self.mid[k])
        ef = self.mv_ef(k)
        if ef == "DANO":
            self.attack(1, mv["pot"], _ref(mv["dtype"]), mv["acc"], 0, _ref(mv["st"]), mv["stp"], 8, 0, 0)
            if not self.p.pv:
                self.result = B_FAINTED
        elif ef == "ESTADO":
            if mv["acc"] != 255 and self.rng.next() >= mv["acc"]:
                self.e(EV_MISS, 1)
            elif self.rng.next() < mv["stp"]:
                self.apply_status(0, _ref(mv["st"]))
            else:
                self.e(EV_MISS, 1)
        elif ef == "DEFENSA":
            self.def_t, self.def_sh = mv["turnos"], mv["val"]
            self.e(EV_DEFUP, 1)
        elif ef == "DEBUFF":
            self.pdeb_t, self.pdeb_sh = mv["turnos"], mv["val"]
            self.e(EV_DEBUFF, 0)
        elif ef == "CURA":
            h = self.cpv_max >> mv["val"]
            self.cpv = min(self.cpv_max, self.cpv + h)
            self.e(EV_HEAL, 1, h)
        elif ef == "HUIR":
            if self.rng.next() < mv["stp"]:
                self.e(EV_FLEE, 1, 1)
                self.result = B_ESCAPED
            else:
                self.e(EV_FLEE, 1, 0)
        elif ef == "ROBAR":
            if self.rng.next() >= mv["acc"]:
                self.e(EV_MISS, 1)
                return
            comida = _enum("items", "bolsa", "COMIDA")
            for i in range(len(T["items"].rows)):
                if self.p.inv[i] and T["items"].rows[i]["bolsa"] == comida:
                    self.p.inv[i] -= 1
                    self.e(EV_STEAL, 1, i)
                    return
            self.e(EV_MISS, 1)

    # ---- end of turn
    def tick_status(self, target):
        st = self.cst if target else self.p.st
        mx = self.cpv_max if target else self.p.pv_max
        if st == NONE:
            return
        r = self.st_row(st)
        if r["dot"]:
            d = max(1, mx >> r["dot"])
            if target:
                self.cpv -= min(d, self.cpv)
                if not self.cpv:
                    self.creature_down()
            else:
                self.p.pv -= min(d, self.p.pv)
                if not self.p.pv:
                    self.result = B_FAINTED
            self.e(EV_DOT, target, d, st)
        if target == 0 and st == ST["ENVENENADO"]:
            return
        if r["tmin"] and (self.cst_t if target else self.p.st_t):
            if target:
                self.cst_t -= 1
                if not self.cst_t:
                    self.end_status(1)
            else:
                self.p.st_t -= 1
                if not self.p.st_t:
                    self.end_status(0)

    def tick_flag(self, attr, st):
        v = getattr(self, attr)
        if v:
            v -= 1
            setattr(self, attr, v)
            if not v:
                self.e(EV_STATUS_END, 1, ST[st])

    def end_turn(self):
        self.tick_status(0)
        if self.result == B_ONGOING:
            self.tick_status(1)
        self.tick_flag("ent_t", "ENREDADO")
        self.tick_flag("calm_t", "CALMADO")
        self.tick_flag("lit_t", "ILUMINADO")
        if self.def_t:
            self.def_t -= 1
        if self.pdeb_t:
            self.pdeb_t -= 1
        if self.cdeb_t:
            self.cdeb_t -= 1
            if not self.cdeb_t:
                self.catk = self.cstat(4, self.sp["tat"])
        self.turn += 1

    def open_turn(self):
        self.ev = []
        if self.free == 2:
            self.creature_act()
            self.free = 0

    def do_turn(self, kind, iid, weapon=NONE):
        self.ev = []
        if self.free == 1:
            self.free = 0
            self.player_act(kind, iid, weapon)
        else:
            rp = self.rng.next() & RULE["INIT_RND"]
            rc = self.rng.next() & RULE["INIT_RND"]
            if self.p_agi() + rp >= self.c_agi() + rc:
                self.player_act(kind, iid, weapon)
                if self.result == B_ONGOING:
                    self.creature_act()
            else:
                self.creature_act()
                if self.result == B_ONGOING:
                    self.player_act(kind, iid, weapon)
        if self.result == B_ONGOING:
            self.end_turn()
        if self.result == B_HUNTED:
            self.give_xp(0)
            self.roll_loot()
            self.p.kills[self.species] = min(255, self.p.kills[self.species] + 1)
        if self.result in (B_HUNTED, B_CAPTURED):
            self.levelups = self.p.gain_xp(self.xp)
        if self.result != B_ONGOING:
            self.e(EV_END, self.result)
