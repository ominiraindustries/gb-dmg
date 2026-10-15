"""Checks that what the player SEES is drawn with the right graphics (games/faro: NPCs showed the title's
beam tiles because the title loaded them over the NPC slots and nobody reloaded them; the HUD icons
and the world tileset shared tiles 252-254; every test passed because they checked positions and tile
numbers, never the pixels behind them).

VRAM ownership, per scene, in game.json:

    "vram_scenes": {
      "field": {
        "spr": [[0, "leo"], [32, "npc"], [80, 32, "critters", "any"], [112, "fx", 0, 16], [252, 4, "uispr", "any"]],
        "bg":  [[128, 49, "battle_pinzarro", "any"]]          (optional, besides vram_order)
      }
    }

Entry forms (tile numbers are sprite tiles for "spr", BG tile numbers for "bg"):
    [first, "set"]                  the whole tileset copied from its tile 0
    [first, "set", start, count]    tiles start..start+count-1 of the set, in order
    [first, count, "set", "any"]    a slot refilled at run time: each tile equals SOME tile of the set
BG regions also come from game.json vram_order (a shared slot = any one of its tilesets, in order).

gb.vram_errors("field") checks every visible sprite (8x16 aware) and every BG/window tile on screen
(gb.screen_tiles()) against those regions: a tile outside every region, or whose 16 bytes differ
from what its region says, is an error. gb.mockup_errors("panel", region, ignore) compares the screen
with a design/screens mockup (ignore = dynamic texts by their SCREEN_*_AT_ name, or (row, col, len)).
"""
import json
from pathlib import Path

import asciitiles
import preview
import screens


def tile_addr(n, sprite, lcdc):
    """VRAM address of tile n: sprites always $8000-based; BG per LCDC bit 4 ($8000 or signed $9000)."""
    if sprite or lcdc & 0x10:
        return 0x8000 + n * 16
    return 0x9000 + n * 16 if n < 128 else 0x8800 + (n - 128) * 16


class Scene:
    def __init__(self, gdir, name):
        cfg = json.loads((Path(gdir) / "game.json").read_text(encoding="utf-8"))
        scenes = cfg.get("vram_scenes", {})
        if name not in scenes:
            raise KeyError(f"game.json vram_scenes has no scene '{name}' (have {sorted(scenes)})")
        self.sets = preview.find_tilesets(Path(gdir))
        self.enc = {}
        sc = scenes[name]
        self.spr = [self._region(e) for e in sc.get("spr", [])]
        self.bg = [self._region(e) for e in sc.get("bg", [])]
        base = 0
        for slot in cfg.get("vram_order", []):           # vram_order slots (screens.vram_bases rules)
            group = slot if isinstance(slot, list) else [slot]
            size = max(len(self.sets[g].tiles) for g in group)
            self.bg.append((base, size, [self._tiles(g) for g in group], "slot"))
            base += size

    def _tiles(self, name):
        if name not in self.enc:
            if name not in self.sets:
                raise KeyError(f"vram_scenes: tileset '{name}' not found")
            self.enc[name] = [tuple(asciitiles.encode(t)) for t in self.sets[name].tiles]
        return self.enc[name]

    def _region(self, e):
        if len(e) == 4 and e[3] == "any":
            return (e[0], e[1], [self._tiles(e[2])], "any")
        tiles = self._tiles(e[1])
        start, count = (e[2], e[3]) if len(e) == 4 else (0, len(tiles))
        return (e[0], count, [tiles[start:start + count]], "exact")

    @staticmethod
    def check(regions, n, data):
        """None if tile n holding data is right, else the reason."""
        for first, count, groups, mode in regions:
            if not first <= n < first + count:
                continue
            k = n - first
            if mode == "any":
                return None if data in set(groups[0]) else f"not a tile of its slot's tileset"
            if any(k < len(g) and g[k] == data for g in groups):
                return None
            if mode == "slot" and all(k >= len(g) for g in groups):
                continue                                    # past the shorter sets of a shared slot
            return "bytes differ from its tileset"
        return "outside every declared region"


def vram_errors(gb, gdir, scene):
    sc = Scene(gdir, scene)
    mem = gb.pyboy.memory
    lcdc = gb.io(0xFF40)
    tall = bool(lcdc & 0x04)
    errs, seen = [], set()

    def data(n, sprite):
        a = tile_addr(n, sprite, lcdc)
        return tuple(mem[a:a + 16])

    if lcdc & 0x02:                                         # sprites on
        for i in range(40):
            y, x, t, _ = mem[0xFE00 + i * 4:0xFE04 + i * 4]
            if not (0 < y < 160 and 0 < x < 168):
                continue
            for n in ((t & 0xFE, t | 1) if tall else (t,)):
                if ("s", n) in seen:
                    continue
                seen.add(("s", n))
                why = Scene.check(sc.spr, n, data(n, True))
                if why:
                    errs.append(f"sprite OAM {i} at ({x - 8},{y - 16}) tile {n}: {why}")
    for r, row in enumerate(gb.screen_tiles()):
        for c, n in enumerate(row):
            if ("b", n) in seen:
                continue
            seen.add(("b", n))
            why = Scene.check(sc.bg, n, data(n, False))
            if why:
                errs.append(f"BG tile {n} (first seen at row {r} col {c}): {why}")
    return errs


def mockup_errors(gb, gdir, name, region=None, ignore=()):
    """Cells of the screen that differ from design/screens/<name>.screen. region = (col0, row0, col1,
    row1) end-exclusive (default the whole screen); ignore: text names of the mockup (dynamic values,
    the 'FASE' of "SCREEN_X_AT_FASE") or (row, col, len) tuples. Returns [(row, col, want, got)]."""
    gdir = Path(gdir)
    cfg = json.loads((gdir / "game.json").read_text(encoding="utf-8"))
    sets = preview.find_tilesets(gdir)
    bases = screens.vram_bases(cfg["vram_order"], sets)
    path = gdir / "design" / "screens" / f"{name}.screen"
    cells, _ = preview.parse_screen(path, sets)
    skip = set()
    runs = {t: (r, c, n) for t, r, c, n, _ in screens.text_runs(path)}
    for item in ignore:
        r, c, n = runs[item] if isinstance(item, str) else item
        skip |= {(r, c + k) for k in range(n)}
    c0, r0, c1, r1 = region or (0, 0, 20, 18)
    got = gb.screen_tiles()
    out = []
    for r in range(r0, r1):
        for c in range(c0, c1):
            if (r, c) in skip:
                continue
            ts, i = cells[r][c]
            want = bases[ts.name] + i
            if got[r][c] != want:
                out.append((r, c, want, got[r][c]))
    return out
