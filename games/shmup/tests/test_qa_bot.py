"""GRIFO QA: whole-stage bots for GDD 11 "Sprites por línea y parpadeo" and the informative "fair"
bot. Slow (~11 000 frames each)."""
import pytest

from test_mechanics import CHEAT_INVINCIBLE

ST_CLEAR = 5


def _sweep(g, f):
    if f % 120 == 0:
        g.pyboy.button_release("left")
        g.pyboy.button_release("right")
        g.pyboy.button_press("left" if (f // 120) % 2 else "right")


def _progress(g):
    boss = (200 - g.u8("boss_hp")) if g.u8("boss_state") else 0
    return g.u16("scroll_y") + boss


def _frame_sprites(g):
    """-> (player_lost, crowded, hidden_bullets): DMG rule = first 10 sprites in OAM order per line."""
    oam = g.oam()
    count = [0] * 144
    drawn_on = {}                                   # oam index -> lines where it was dropped
    dropped = set()
    for i, (y, x, t, p) in enumerate(oam):
        top = y - 16
        for line in range(max(8, top), min(144, top + 16)):
            if count[line] >= 10:
                dropped.add(i)
            count[line] += 1
    crowded = any(c > 10 for c in count[8:])
    raw = g.bytes("pool", 12 * 16)
    hidden = set()
    for b in range(12):
        r = raw[b * 16:b * 16 + 16]
        if not r[0] or not (8 + 16 <= r[3] + 8 <= 144 + 16):   # bullet tile (top 8 lines) on screen
            continue
        slots = [i for i in range(2, 14) if oam[i][0] == r[3] and oam[i][1] == r[1]]
        if not slots or slots[0] in dropped:
            hidden.add(b)
    return (0 in dropped or 1 in dropped), crowded, hidden


def test_full_run_flicker_rules(gb):
    """GDD 11 / 7.3: (a) player always drawn; (b) no enemy bullet undrawn 2 frames in a row;
    (c) frames with some line > 10 sprites <= 25 %."""
    gb.write_u8("cheat_flags", CHEAT_INVINCIBLE)
    gb.pyboy.button_press("a")
    stats = {"frames": 0, "player_lost": 0, "crowded": 0, "hidden2": 0, "hidden": 0}
    prev_hidden = set()

    def step(g, f):
        nonlocal prev_hidden
        _sweep(g, f)
        if g.u8("state") != 1 or g.u8("trans_phase"):
            return
        lost, crowded, hidden = _frame_sprites(g)
        stats["frames"] += 1
        stats["player_lost"] += lost
        stats["crowded"] += crowded
        stats["hidden"] += len(hidden)
        stats["hidden2"] += len(hidden & prev_hidden)
        prev_hidden = hidden

    r = gb.run_bot(step, _progress, 12000, stuck_limit=1500, done=lambda g: g.u8("state") == ST_CLEAR)
    print(r, stats, f"crowded {100 * stats['crowded'] / stats['frames']:.1f} %")
    assert gb.u8("state") == ST_CLEAR and not r["gave_up"], r
    assert stats["player_lost"] == 0
    assert stats["crowded"] <= stats["frames"] // 4
    assert stats["hidden2"] == 0, stats


def test_fair_bot_informative(gb):
    """No cheats: dodge the nearest bullet above, autofire, bomb when 8+ bullets are close.
    Prints deaths and the row reached (guide for the playtest, no assert on difficulty)."""
    deaths = 0
    was_dying = False
    gb.pyboy.button_press("a")

    def step(g, f):
        nonlocal deaths, was_dying
        dying = g.u8("play_sub") == 1
        if dying and not was_dying:
            deaths += 1
        was_dying = dying
        if g.u8("state") == 3:                     # CONTINUAR: continue
            if f % 4 == 0:
                g.pyboy.button_press("start")
            else:
                g.pyboy.button_release("start")
            return
        g.pyboy.button_release("start")
        px, py = g.u8("player_x") + 8, g.u8("player_y") + 8
        raw = g.bytes("pool", 12 * 16)
        near, close = None, 0
        for b in range(12):
            r = raw[b * 16:b * 16 + 16]
            if not r[0]:
                continue
            bx, by = r[1] + 4, r[3] + 4
            if py - 48 < by < py + 8 and abs(bx - px) < 24:
                close += 1
                if near is None or by > near[1]:
                    near = (bx, by)
        for k in ("left", "right", "up", "down"):
            g.pyboy.button_release(k)
        if near:
            g.pyboy.button_press("right" if near[0] <= px else "left")
        elif f % 240 < 120:
            g.pyboy.button_press("left" if px > 40 else "right")
        else:
            g.pyboy.button_press("right" if px < 120 else "left")
        if py < 120:
            g.pyboy.button_press("down")
        if close >= 4 and f % 2 == 0:
            g.pyboy.button_press("b")
        else:
            g.pyboy.button_release("b")

    r = gb.run_bot(step, _progress, 14000, stuck_limit=2500,
                   done=lambda g: g.u8("state") in (ST_CLEAR, 4))
    print("fair bot", r, "deaths", deaths, "state", gb.u8("state"), "row",
          (gb.u16("scroll_y") + 144) // 16, "boss_hp", gb.u8("boss_hp"), "continues", gb.u8("continues"))
    assert r["vram_late"] == 0
