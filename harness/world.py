"""World maps for 4-way scrolling games (top-down RPGs): res/maps/<name>.map -> build/gen/map_<name>.c/.h,
read by harness/common/src/gbe_world.c. One source for the ROM, the preview and the Python tests.

    ; comment
    @ map VARADERO               name (C symbol map_<lowercase name>, id MAP_<NAME>; default: file name)
    @ metatiles metatiles        the res/<stem>.mt table the grid uses (default "metatiles")
    @ size 2 1                   width and height in SECTORS (a sector = 16x16 cells); max 15 x 15
    @ border WATER               metatile shown outside the map
    legend:
    . GRASS                      char -> metatile name of the .mt (any non-blank char but ';')
    # TREE
    grid:
    ................................     size_h * 16 rows of size_w * 16 chars (1 char = 1 cell)
    objects:                     optional: same size as the grid, '.' = nothing, any other char =
    ......A.........B...........         an object defined by an '@ obj' line (several cells may
                                         share one definition)
    @ obj A npc look=TOMASA face=DOWN beh=STILL script=tomasa_casa
    @ obj B warp map=CASA_INES x=4 y=7 face=UP

Object types and their fields come from game.json "world_objects" (the engine knows no RPG):
    "world_objects": { "npc": ["look sym", "face enum DOWN UP LEFT RIGHT", "beh u8", "script script"],
                       "warp": ["map map", "x u8", "y u8", "face enum DOWN UP LEFT RIGHT"] }
Field kinds: u8, s8, bool, enum A B C, sym (tables/script symbols: ITEM_*, F_*...), flag (u16 id of
res/scripts/flags.txt), script (u16 SID_ of a script), map (u8 MAP_ id). A record is 8 bytes:
x, y (absolute cells), type (order in world_objects), 5 bytes of fields in order.

Output (always in a switchable bank: '#pragma bank 255', BANKREF(map_<name>)):
    const uint8_t map_<name>_sectors[n][256]   unique sectors, row-major 16x16 metatile ids
    const uint8_t map_<name>_grid[w * h]       sector index of each sector of the map, row-major
    const uint8_t map_<name>_events[8 * k]     object records sorted by sector
    const uint16_t map_<name>_evidx[w*h + 1]   first record of each sector (prefix sums)
    const world_map_t map_<name>               { w, h, border, n, mtset, grid, sectors, events, evidx }
    (mtset = index of the map's metatile table among the sorted res/metatiles*.mt names)
and world_index.c/.h: MAP_<NAME> ids and world_maps[] = { bank, address } (world_load_id()).
Identical sectors are stored once (sea, forest fill).
"""
import json
from pathlib import Path

import metatiles

SECTOR = 16
EVENTS_PER_SECTOR = 16          # gbe_world's buffer (GBE_WORLD_EV_MAX)


class Map:
    def __init__(self, name, path, mt_stem, w, h, border, cells, legend, objects=None):
        self.name, self.path, self.mt_stem = name, Path(path), mt_stem
        self.w, self.h, self.border, self.cells, self.legend = w, h, border, cells, legend
        self.objects = objects or []        # [(x, y, char, type, {field: value-string})]

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
    name, mt_stem, size, border, legend = path.stem.upper(), "metatiles", None, None, {}
    rows, orows, defs, section = [], [], {}, None
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        where = f"{path}:{n}"
        if raw.strip().lower() in ("legend:", "grid:", "objects:"):
            section = raw.strip().lower()[:-1]
            continue
        if raw.startswith("@ obj"):
            p = raw.split(";", 1)[0].split()
            if len(p) < 4 or len(p[2]) != 1:
                raise ValueError(f"{where}: '@ obj C type key=value ...'")
            if p[2] in defs:
                raise ValueError(f"{where}: object char {p[2]!r} defined twice")
            fields = {}
            for kv in p[4:]:
                if "=" not in kv:
                    raise ValueError(f"{where}: '{kv}' is not key=value")
                k, v = kv.split("=", 1)
                fields[k.lower()] = v
            defs[p[2]] = (p[3].lower(), fields, where)
            continue
        if section in ("grid", "objects"):
            if raw.strip().startswith(";") or not raw.strip():
                continue
            (rows if section == "grid" else orows).append((n, raw.rstrip()))
            continue
        line = raw.split(";", 1)[0].rstrip()
        if not line.strip():
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
    objects = []
    if orows:
        if len(orows) != h * SECTOR:
            raise ValueError(f"{path}: objects layer has {len(orows)} rows, expected {h * SECTOR}")
        used = set()
        for y, (n, row) in enumerate(orows):
            if len(row) != w * SECTOR:
                raise ValueError(f"{path}:{n}: objects row has {len(row)} chars, expected {w * SECTOR}")
            for x, ch in enumerate(row):
                if ch == ".":
                    continue
                if ch not in defs:
                    raise ValueError(f"{path}:{n}: object {ch!r} at column {x} has no '@ obj {ch}' line")
                used.add(ch)
                t, fields, _ = defs[ch]
                objects.append((x, y, ch, t, fields))
        unused = set(defs) - used
        if unused:
            raise ValueError(f"{path}: objects defined but not placed: {sorted(unused)}")
    elif defs:
        raise ValueError(f"{path}: '@ obj' lines but no 'objects:' layer")
    m = Map(name, path, mt_stem, w, h, mt.ids[border], cells, legend, objects)
    m.mt_attrs = mt.attrs                   # attribute names per metatile (lints)
    return m


def _mt_tileset(mt_file):
    for raw in Path(mt_file).read_text(encoding="utf-8").splitlines():
        p = raw.split(";", 1)[0].split()
        if len(p) >= 3 and p[0] == "@" and p[1].lower() == "tileset":
            return p[2]
    return None


def load(gdir, path):
    """Parse a map with its metatile table from games/<game>/res (labels resolved, bases applied)."""
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
    import screens
    cfg = json.loads((gdir / "game.json").read_text(encoding="utf-8"))
    bases = screens.vram_bases(cfg["vram_order"], sets) if cfg.get("vram_order") else None
    return parse(path, metatiles.parse(mt_file, labels, bases))


def map_ids(gdir):
    """{MAP_<NAME>: id} in file order (the ids world_index.h defines)."""
    out = {}
    for f in sorted((Path(gdir) / "res" / "maps").glob("*.map")):
        name = f.stem.upper()
        for raw in f.read_text(encoding="utf-8").splitlines():
            p = raw.split(";", 1)[0].split()
            if len(p) >= 3 and p[0] == "@" and p[1].lower() == "map":
                name = p[2].upper()
        out[f"MAP_{name}"] = len(out)
    return out


def encode_objects(m, types, symbols):
    """-> (records bytes sorted by sector, evidx list) ; types = game.json world_objects."""
    tnames = list(types)
    per_sector = [[] for _ in range(m.w * m.h)]
    for x, y, ch, t, fields in m.objects:
        where = f"{m.path}: object {ch!r} ({t}) at {x},{y}"
        if t not in types:
            raise ValueError(f"{where}: type '{t}' not in game.json world_objects {tnames}")
        data = bytearray()
        for spec in types[t]:
            p = spec.split()
            fname, kind = p[0], p[1]
            if fname not in fields:
                raise ValueError(f"{where}: missing field {fname}= ({spec})")
            v = fields[fname]
            if kind == "u8":
                data.append(_int(v, 0, 255, where))
            elif kind == "s8":
                data.append(_int(v, -128, 127, where) & 0xFF)
            elif kind == "bool":
                data.append(1 if v.lower() in ("1", "yes", "si", "true") else 0)
            elif kind == "enum":
                if v.upper() not in p[2:]:
                    raise ValueError(f"{where}: {fname}={v} not one of {p[2:]}")
                data.append(p[2:].index(v.upper()))
            elif kind in ("sym", "map"):
                key = v.upper() if kind == "sym" else "MAP_" + v.upper()
                if key not in symbols:
                    raise ValueError(f"{where}: {fname}={v}: unknown symbol {key}")
                data.append(symbols[key] & 0xFF)
            elif kind in ("flag", "script"):
                key = v.upper() if kind == "flag" else "SID_" + v.upper()
                if key not in symbols:
                    raise ValueError(f"{where}: {fname}={v}: unknown {kind} ({key})")
                data += (symbols[key] & 0xFFFF).to_bytes(2, "little")
            else:
                raise ValueError(f"{where}: unknown field kind '{kind}' in world_objects")
            extra = set(fields) - {s.split()[0] for s in types[t]}
            if extra:
                raise ValueError(f"{where}: unknown fields {sorted(extra)} for type {t}")
        if len(data) > 5:
            raise ValueError(f"{where}: fields take {len(data)} bytes, max 5")
        rec = bytes([x, y, tnames.index(t)]) + bytes(data) + bytes(5 - len(data))
        per_sector[(y // SECTOR) * m.w + x // SECTOR].append(rec)
    for i, recs in enumerate(per_sector):
        if len(recs) > EVENTS_PER_SECTOR:
            raise ValueError(f"{m.path}: sector {i % m.w},{i // m.w} has {len(recs)} objects, max {EVENTS_PER_SECTOR}")
    evidx, blob = [0], bytearray()
    for recs in per_sector:
        for r in recs:
            blob += r
        evidx.append(len(blob) // 8)
    return bytes(blob), evidx


def lint_warps(maps, solid_attr="SOLID"):
    """Objects of type 'warp' (fields map, x, y): the target map exists, the arrival cell is inside
    it, walkable, and not a warp itself (world_lab: arriving next to the door and walking on took
    the player straight back in; the arrival goes on the far side of the door). Returns problems."""
    by_name = {m.name: m for m in maps}
    out = []
    for m in maps:
        for x, y, ch, t, f in m.objects:
            if t != "warp" or not {"map", "x", "y"} <= set(f):
                continue
            where = f"{m.path.name}: warp {ch!r} at {x},{y}"
            dst = by_name.get(f["map"].upper())
            if dst is None:
                out.append(f"{where}: map {f['map']} does not exist")
                continue
            tx, ty = int(f["x"], 0), int(f["y"], 0)
            if tx >= dst.width or ty >= dst.height:
                out.append(f"{where}: arrival {tx},{ty} outside {dst.name}")
                continue
            if solid_attr in dst.mt_attrs[dst.cells[ty][tx]]:
                out.append(f"{where}: arrival {tx},{ty} in {dst.name} is {solid_attr}")
            if any(ox == tx and oy == ty and ot == "warp" for ox, oy, _, ot, _ in dst.objects):
                out.append(f"{where}: arrival {tx},{ty} in {dst.name} is another warp (loop)")
    return out


def _int(v, lo, hi, where):
    try:
        n = int(v, 0)
    except ValueError:
        raise ValueError(f"{where}: '{v}' is not a number") from None
    if not lo <= n <= hi:
        raise ValueError(f"{where}: {n} out of range {lo}..{hi}")
    return n


def convert(m, out_dir, types=None, symbols=None, mtset=0):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    sym = f"map_{m.name.lower()}"
    uniq, grid = m.sectors()
    events, evidx = encode_objects(m, types or {}, symbols or {})
    secs = ",\n".join("    {\n" + ",\n".join(
        "        " + ", ".join(f"{v:3d}" for v in s[r * SECTOR:(r + 1) * SECTOR]) for r in range(SECTOR))
        + "\n    }" for s in uniq)
    ev = ",\n".join("    " + ", ".join(f"{b}" for b in events[i:i + 8]) for i in range(0, len(events), 8)) or "    0"
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
        f"const uint8_t {sym}_events[] = {{\n{ev}\n}};\n\n"
        f"const uint16_t {sym}_evidx[{len(evidx)}] = {{ {', '.join(map(str, evidx))} }};\n\n"
        f"const world_map_t {sym} = {{ {m.w}, {m.h}, {m.border}, {len(uniq)}, {mtset}, {sym}_grid, "
        f"(const uint8_t *){sym}_sectors, {sym}_events, {sym}_evidx }};\n\n"
        f"BANKREF({sym})\n", encoding="utf-8")
    return out_dir / f"{sym}.c"


def write_index(maps, out_dir):
    """world_index.c/.h: MAP_<NAME> ids and world_maps[] = { bank, address } (maps in id order)."""
    out_dir = Path(out_dir)
    syms = [f"map_{m.name.lower()}" for m in maps]
    (out_dir / "world_index.h").write_text(
        "// Generated by harness/world.py - do not edit\n#pragma once\n\n"
        + "".join(f"#define MAP_{m.name} {i}\n" for i, m in enumerate(maps))
        + f"#define MAP_COUNT {len(maps)}\n", encoding="utf-8")
    refs = "".join(f"    {{ &__bank_{s}, &{s} }},\n" for s in syms) or "    { 0, 0 }\n"
    (out_dir / "world_index.c").write_text(
        "// Generated by harness/world.py - do not edit\n#pragma bank 255\n#include \"gbe.h\"\n"
        + "".join(f"BANKREF_EXTERN({s})\nextern const world_map_t {s};\n" for s in syms)
        + f"\nconst gbe_ref_t world_maps[] = {{\n{refs}}};\n\nBANKREF(world_maps)\n", encoding="utf-8")
    return out_dir / "world_index.c"


def render(m, mt, sets, out, scale=1):
    """PNG of the whole map (one 16x16 image per cell) for review; objects marked with their char."""
    import preview
    from PIL import Image, ImageDraw
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
    d = ImageDraw.Draw(img)
    for x, y, ch, t, _ in m.objects:
        d.rectangle((x * 16, y * 16, x * 16 + 15, y * 16 + 15), outline=(220, 0, 0))
        d.text((x * 16 + 4, y * 16 + 2), ch, fill=(220, 0, 0))
    if scale != 1:
        img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out
