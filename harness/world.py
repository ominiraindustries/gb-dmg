"""World maps for 4-way scrolling games (top-down RPGs): res/maps/<name>.map -> build/gen/map_<name>.c/.h,
read by harness/common/src/gbe_world.c. One source for the ROM, the preview and the Python tests.

    ; comment
    @ map VARADERO               name (C symbol map_<lowercase name>; default: the file name)
    @ metatiles metatiles        the res/<stem>.mt table the grid uses (default "metatiles")
    @ size 2 1                   width and height in SECTORS (a sector = 16x16 cells); max 15 x 15
    @ border WATER               metatile shown outside the map
    legend:
    . GRASS                      char -> metatile name of the .mt (any non-blank char but ';')
    # TREE
    grid:
    ................................     size_h * 16 rows of size_w * 16 chars (1 char = 1 cell)

Output (always in a switchable bank: '#pragma bank 255', BANKREF(map_<name>)):
    const uint8_t map_<name>_sectors[n][256]   unique sectors, row-major 16x16 metatile ids
    const uint8_t map_<name>_grid[w * h]       sector index of each sector of the map, row-major
    const world_map_t map_<name>               { w, h, border, n, grid, sectors } (gbe.h)
Identical sectors are stored once (sea, forest fill).
"""
from pathlib import Path

import metatiles

SECTOR = 16


class Map:
    def __init__(self, name, path, mt_stem, w, h, border, cells, legend):
        self.name, self.path, self.mt_stem = name, Path(path), mt_stem
        self.w, self.h, self.border, self.cells, self.legend = w, h, border, cells, legend

    @property
    def width(self):
        return self.w * SECTOR

    @property
    def height(self):
        return self.h * SECTOR

    def at(self, x, y):
        """Metatile id at cell (x, y); x, y are u8 like in the ROM (out of the map = border)."""
        x, y = x & 0xFF, y & 0xFF
        if x >= self.width or y >= self.height:
            return self.border
        return self.cells[y][x]

    def sectors(self):
        """(unique sector list of 256 ids, grid of sector indices)"""
        uniq, index, grid = [], {}, []
        for sy in range(self.h):
            for sx in range(self.w):
                data = tuple(self.cells[sy * SECTOR + r][sx * SECTOR + c]
                             for r in range(SECTOR) for c in range(SECTOR))
                if data not in index:
                    index[data] = len(uniq)
                    uniq.append(data)
                grid.append(index[data])
        return uniq, grid


def parse(path, mt):
    """mt: metatiles.Metatiles of the table named by '@ metatiles'."""
    path = Path(path)
    name, mt_stem, size, border, legend, rows, section = path.stem.upper(), "metatiles", None, None, {}, [], None
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        where = f"{path}:{n}"
        if section == "grid":
            if raw.strip().startswith(";") or not raw.strip():
                continue
            rows.append((n, raw.rstrip()))
            continue
        line = raw.split(";", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.strip().lower() in ("legend:", "grid:"):
            section = line.strip().lower()[:-1]
            continue
        if line.startswith("@"):
            parts = line.split()
            key = parts[1].lower()
            if key == "map":
                name = parts[2].upper()
            elif key == "metatiles":
                mt_stem = parts[2]
            elif key == "size":
                size = int(parts[2]), int(parts[3])
            elif key == "border":
                border = parts[2].upper()
            else:
                raise ValueError(f"{where}: unknown '@ {key}'")
            continue
        if section == "legend":
            ch, ref = line[0], line[1:].strip().upper()
            if ch in legend:
                raise ValueError(f"{where}: legend char {ch!r} defined twice")
            if ref not in mt.ids:
                raise ValueError(f"{where}: metatile {ref} not in {mt.path.name}")
            legend[ch] = mt.ids[ref]
            continue
        raise ValueError(f"{where}: unexpected line (missing 'legend:' or 'grid:'?)")
    if size is None or border is None:
        raise ValueError(f"{path}: needs '@ size W H' and '@ border NAME'")
    w, h = size
    if not (1 <= w <= 15 and 1 <= h <= 15):
        raise ValueError(f"{path}: size {w}x{h} sectors, max 15x15 (u8 cells, the camera needs room)")
    if border not in mt.ids:
        raise ValueError(f"{path}: border {border} not in {mt.path.name}")
    if len(rows) != h * SECTOR:
        raise ValueError(f"{path}: grid has {len(rows)} rows, expected {h * SECTOR} ({h} sectors)")
    cells = []
    for n, row in rows:
        if len(row) != w * SECTOR:
            raise ValueError(f"{path}:{n}: row has {len(row)} chars, expected {w * SECTOR}")
        out = []
        for c, ch in enumerate(row):
            if ch not in legend:
                raise ValueError(f"{path}:{n}: char {ch!r} at column {c} has no legend entry")
            out.append(legend[ch])
        cells.append(out)
    return Map(name, path, mt_stem, w, h, mt.ids[border], cells, legend)


def load(gdir, path):
    """Parse a map with its metatile table from games/<game>/res (labels resolved, base 0)."""
    gdir = Path(gdir)
    import preview
    stem = "metatiles"
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        p = raw.split(";", 1)[0].split()
        if len(p) >= 3 and p[0] == "@" and p[1].lower() == "metatiles":
            stem = p[2]
    mt_file = gdir / "res" / f"{stem}.mt"
    sets = preview.find_tilesets(gdir)
    ts = _mt_tileset(mt_file)
    labels = sets[ts].labels if ts in sets else None
    import json
    import screens
    cfg = json.loads((gdir / "game.json").read_text(encoding="utf-8"))
    bases = screens.vram_bases(cfg["vram_order"], sets) if cfg.get("vram_order") else None
    return parse(path, metatiles.parse(mt_file, labels, bases))


def _mt_tileset(mt_file):
    for raw in Path(mt_file).read_text(encoding="utf-8").splitlines():
        p = raw.split(";", 1)[0].split()
        if len(p) >= 3 and p[0] == "@" and p[1].lower() == "tileset":
            return p[2]
    return None


def convert(m, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    sym = f"map_{m.name.lower()}"
    uniq, grid = m.sectors()
    secs = ",\n".join("    {\n" + ",\n".join(
        "        " + ", ".join(f"{v:3d}" for v in s[r * SECTOR:(r + 1) * SECTOR]) for r in range(SECTOR))
        + "\n    }" for s in uniq)
    (out_dir / f"{sym}.h").write_text(
        f"// Generated from {m.path.name} by harness/world.py - do not edit\n#pragma once\n"
        f'#include <gb/gb.h>\n#include "gbe.h"\n\n'
        f"#define {sym.upper()}_W {m.w}\n#define {sym.upper()}_H {m.h}\n#define {sym.upper()}_SECTORS {len(uniq)}\n"
        f"extern const world_map_t {sym};\nBANKREF_EXTERN({sym})\n", encoding="utf-8")
    (out_dir / f"{sym}.c").write_text(
        f"// Generated from {m.path.name} by harness/world.py - do not edit\n#pragma bank 255\n"
        f'#include "{sym}.h"\n\n'
        f"const uint8_t {sym}_sectors[{len(uniq)}][256] = {{\n{secs}\n}};\n\n"
        f"const uint8_t {sym}_grid[{len(grid)}] = {{ {', '.join(map(str, grid))} }};\n\n"
        f"const world_map_t {sym} = {{ {m.w}, {m.h}, {m.border}, {len(uniq)}, {sym}_grid, (const uint8_t *){sym}_sectors }};\n\n"
        f"BANKREF({sym})\n", encoding="utf-8")
    return out_dir / f"{sym}.c"


def render(m, mt, sets, out, scale=1):
    """PNG of the whole map (one 16x16 image per cell) for review."""
    import preview
    from PIL import Image
    ts = sets[mt.tileset]
    imgs = {}
    for i, t4 in enumerate(mt.tiles):
        im = Image.new("RGB", (16, 16))
        for k, t in enumerate(t4):
            im.paste(preview.tile_image(ts.tiles[t]), ((k & 1) * 8, (k >> 1) * 8))
        imgs[i] = im
    img = Image.new("RGB", (m.width * 16, m.height * 16))
    for y in range(m.height):
        for x in range(m.width):
            img.paste(imgs[m.cells[y][x]], (x * 16, y * 16))
    if scale != 1:
        img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out
