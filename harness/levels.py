"""Convert ASCII level files (res/*.lvl) into C arrays at build time.

Level file:
    ; comment
    @ time 300                 metadata -> #define <STEM>_TIME 300  (keys uppercased)
    @ checkpoint 100
    grid:
    ........?.......           H lines (all the same width N): one char per map cell
    ..x.....w.......
    ################

The meaning of each char comes from game.json (symbolic names, defined by the game's C code):
    "levels": {
      "height": 8,
      "include": "metatiles.h",                  header that defines the names below
      "cells":   {".": "MT_SKY", "#": "MT_GROUND", "?": "MT_Q_COIN"},
      "objects": {"x": "OBJ_START", "w": "OBJ_WALKER"},
      "object_cell": "."                         cell stored under an object (default ".")
    }

Output build/gen/<stem>.c/.h:
    const uint8_t <stem>_map[N * H];      column-major: map[col * H + row]
    const uint8_t <stem>_obj_col[], <stem>_obj_row[], <stem>_obj_type[];   sorted by column
    #define <STEM>_WIDTH N, <STEM>_HEIGHT H, <STEM>_OBJ_COUNT n, <STEM>_<KEY> value

Vertical levels (shmups): "order": "rows" and "width": W in the levels config.
    - map is row-major from the BOTTOM text line up: map[row * W + col], row 0 = last grid line
      (the first one the player sees). obj_row counts the same way; objects sorted by row, then col.
    - Object layer: a grid line may carry a second block of W chars after spaces, objects only
      ('.' = none), so objects do not punch holes in the terrain and object letters may reuse
      terrain letters (vertical levels read objects ONLY from this layer):
          ,,~~~~~~,,   ..d.......
    - Lines are split by position (W cells first): ' ' can be a cell, but editors strip trailing
      spaces, so do not give a cell the ' ' char in vertical levels.

Top-down grids (crawlers, puzzles): "order": "grid" and "width": W. Same two-block lines (cells,
then the object layer); map[y * W + x] with y = text line from the top; objects as
<stem>_obj_x[], _obj_y[], _obj_type[] sorted by y then x; "@ key value" metadata as usual.
    - "object_cells": {"t": "MT_TURRET_D"}  per-object stored cell (a C name), e.g. a turret
      object that also draws its metatile.

`parse()` is also used by pure-Python level lint tests.
"""
from pathlib import Path


class Level:
    def __init__(self, path, rows, meta, layer=None):
        self.path, self.rows, self.meta = Path(path), rows, meta
        self.layer = layer          # object layer lines (same size as rows) or None
        self.height = len(rows)
        self.width = len(rows[0]) if rows else 0

    def cell(self, col, row):
        return self.rows[row][col]

    def column(self, col):
        return "".join(r[col] for r in self.rows)


def parse(path, height=None, layered=None):
    """layered=W: a grid line is W cells, optionally followed by spaces and a W-char object
    layer (vertical levels; split by position because ' ' can be a cell)."""
    rows, layer, meta, in_grid = [], [], {}, False
    for n, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not in_grid:
            line = raw.split(";", 1)[0].strip()
            if not line:
                continue
            if line.startswith("@"):
                key, _, value = line[1:].strip().partition(" ")
                meta[key.strip().upper()] = value.strip()
            elif line.lower() == "grid:":
                in_grid = True
            else:
                raise ValueError(f"{path}:{n}: expected '@ key value' or 'grid:'")
        else:
            line = raw.rstrip("\r\n")
            if not line.strip() or line.lstrip().startswith(";"):
                continue
            if layered:
                rows.append(line[:layered].ljust(layered))
                layer.append(line[layered:].strip())
            else:
                rows.append(line)
    if not rows:
        raise ValueError(f"{path}: no grid")
    width = len(rows[0])
    for i, r in enumerate(rows):
        if len(r) != width:
            raise ValueError(f"{path}: grid row {i} has {len(r)} chars, row 0 has {width}")
        if layered and layer[i] and len(layer[i]) != width:
            raise ValueError(f"{path}: object layer of grid row {i} has {len(layer[i])} chars, "
                             f"expected {width}")
    if height is not None and len(rows) != height:
        raise ValueError(f"{path}: grid has {len(rows)} rows, expected {height}")
    if layered:
        layer = [l or "." * width for l in layer]
    return Level(path, rows, meta, layer if layered else None)


def objects_of(lvl, objects):
    """Vertical level objects as (col, row_from_bottom, char), sorted by row then col."""
    out = []
    h = lvl.height
    for i in range(h):
        row = h - 1 - i
        for col in range(lvl.width):
            ch = lvl.layer[i][col]
            if ch in objects:
                out.append((col, row, ch))
    return sorted(out, key=lambda o: (o[1], o[0]))


def convert_rows(src, out_dir, cfg):
    src, out_dir = Path(src), Path(out_dir)
    stem, up = src.stem, src.stem.upper()
    cells, objects = cfg.get("cells", {}), cfg.get("objects", {})
    obj_cells = cfg.get("object_cells", {})
    if "width" not in cfg:
        raise ValueError('levels: "order": "rows" needs "width" in game.json levels')
    lvl = parse(src, cfg.get("height"), layered=cfg["width"])
    if lvl.height > 256:
        raise ValueError(f"{src}: {lvl.height} rows; obj_row is 8-bit (max 256)")
    for i, line in enumerate(lvl.layer):
        for col, ch in enumerate(line):
            if ch != "." and ch not in objects:
                raise ValueError(f"{src}: object layer char {ch!r} at grid line {i}, column {col} "
                                 f"is not in game.json levels.objects")
    h, data = lvl.height, []
    for row in range(h):
        line, objl = lvl.rows[h - 1 - row], lvl.layer[h - 1 - row]
        for col in range(lvl.width):
            ch = line[col]
            name = None
            if objl[col] in obj_cells:
                name = obj_cells[objl[col]]
            if name is None:
                if ch not in cells:
                    raise ValueError(f"{src}: char {ch!r} at grid line {h - 1 - row}, column {col} "
                                     f"is not in game.json levels.cells/objects")
                name = cells[ch]
            data.append(name)
    objs = [(c, r, objects[ch]) for c, r, ch in objects_of(lvl, objects)]

    out_dir.mkdir(parents=True, exist_ok=True)
    include = f'#include "{cfg["include"]}"\n' if cfg.get("include") else ""
    w = lvl.width
    body = ",\n".join(f"    /* {r:3d} */ " + ", ".join(data[r * w:(r + 1) * w]) for r in range(h))

    def arr(name, values):
        vals = ", ".join(values) if values else "0"
        return f"const uint8_t {stem}_{name}[] = {{ {vals} }};\n"

    (out_dir / f"{stem}.c").write_text(
        f"// Generated from {src.name} by harness/levels.py - do not edit\n"
        f"#include <stdint.h>\n{include}\n"
        f"// row-major, row 0 = bottom of the level (first on screen)\n"
        f"const uint8_t {stem}_map[] = {{\n{body}\n}};\n\n"
        + arr("obj_col", [str(o[0]) for o in objs])
        + arr("obj_row", [str(o[1]) for o in objs])
        + arr("obj_type", [o[2] for o in objs]),
        encoding="utf-8")
    meta = "\n".join(f"#define {up}_{k} {v}" for k, v in lvl.meta.items())
    (out_dir / f"{stem}.h").write_text(
        f"// Generated from {src.name} by harness/levels.py - do not edit\n"
        f"#pragma once\n#include <stdint.h>\n\n"
        f"#define {up}_WIDTH {lvl.width}\n#define {up}_HEIGHT {lvl.height}\n"
        f"#define {up}_OBJ_COUNT {len(objs)}\n{meta}\n\n"
        f"extern const uint8_t {stem}_map[];\n"
        f"extern const uint8_t {stem}_obj_col[], {stem}_obj_row[], {stem}_obj_type[];\n",
        encoding="utf-8")
    return out_dir / f"{stem}.c"


def grid_objects(lvl, objects):
    """Grid level objects as (x, y, char), y = text line (top-down), sorted by y then x."""
    out = []
    for y in range(lvl.height):
        for x in range(lvl.width):
            ch = lvl.layer[y][x]
            if ch in objects:
                out.append((x, y, ch))
    return out


def convert_grid(src, out_dir, cfg):
    """Top-down grids (crawlers, puzzles, RPG maps): map[y * W + x], y = text line from the top."""
    src, out_dir = Path(src), Path(out_dir)
    stem, up = src.stem, src.stem.upper()
    cells, objects = cfg.get("cells", {}), cfg.get("objects", {})
    obj_cells = cfg.get("object_cells", {})
    if "width" not in cfg:
        raise ValueError('levels: "order": "grid" needs "width" in game.json levels')
    lvl = parse(src, cfg.get("height"), layered=cfg["width"])
    for i, line in enumerate(lvl.layer):
        for col, ch in enumerate(line):
            if ch != "." and ch not in objects:
                raise ValueError(f"{src}: object layer char {ch!r} at grid line {i}, column {col} "
                                 f"is not in game.json levels.objects")
    data = []
    for y in range(lvl.height):
        for x in range(lvl.width):
            ch, ob = lvl.rows[y][x], lvl.layer[y][x]
            if ob in obj_cells:
                data.append(obj_cells[ob])
            elif ch in cells:
                data.append(cells[ch])
            else:
                raise ValueError(f"{src}: char {ch!r} at line {y}, column {x} is not in game.json levels.cells")
    objs = [(x, y, objects[ch]) for x, y, ch in grid_objects(lvl, objects)]
    out_dir.mkdir(parents=True, exist_ok=True)
    include = f'#include "{cfg["include"]}"\n' if cfg.get("include") else ""
    w = lvl.width
    body = ",\n".join(f"    /* {y:2d} */ " + ", ".join(data[y * w:(y + 1) * w]) for y in range(lvl.height))

    def arr(name, values):
        vals = ", ".join(values) if values else "0"
        return f"const uint8_t {stem}_{name}[] = {{ {vals} }};\n"

    (out_dir / f"{stem}.c").write_text(
        f"// Generated from {src.name} by harness/levels.py - do not edit\n"
        f"#include <stdint.h>\n{include}\n"
        f"// row-major from the top: map[y * {w} + x]\n"
        f"const uint8_t {stem}_map[] = {{\n{body}\n}};\n\n"
        + arr("obj_x", [str(o[0]) for o in objs])
        + arr("obj_y", [str(o[1]) for o in objs])
        + arr("obj_type", [o[2] for o in objs]),
        encoding="utf-8")
    meta = "\n".join(f"#define {up}_{k} {v}" for k, v in lvl.meta.items())
    (out_dir / f"{stem}.h").write_text(
        f"// Generated from {src.name} by harness/levels.py - do not edit\n"
        f"#pragma once\n#include <stdint.h>\n\n"
        f"#define {up}_WIDTH {lvl.width}\n#define {up}_HEIGHT {lvl.height}\n"
        f"#define {up}_OBJ_COUNT {len(objs)}\n{meta}\n\n"
        f"extern const uint8_t {stem}_map[];\n"
        f"extern const uint8_t {stem}_obj_x[], {stem}_obj_y[], {stem}_obj_type[];\n",
        encoding="utf-8")
    return out_dir / f"{stem}.c"


def convert(src, out_dir, cfg):
    if cfg.get("order") == "rows":
        return convert_rows(src, out_dir, cfg)
    if cfg.get("order") == "grid":
        return convert_grid(src, out_dir, cfg)
    src, out_dir = Path(src), Path(out_dir)
    stem = src.stem
    up = stem.upper()
    cells, objects = cfg.get("cells", {}), cfg.get("objects", {})
    under = cfg.get("object_cell", ".")
    lvl = parse(src, cfg.get("height"))

    data, objs = [], []
    for col in range(lvl.width):
        for row in range(lvl.height):
            ch = lvl.cell(col, row)
            if ch in objects:
                objs.append((col, row, objects[ch]))
                ch = under
            if ch not in cells:
                raise ValueError(f"{src}: char {ch!r} at column {col}, row {row} is not in "
                                 f"game.json levels.cells/objects")
            data.append(cells[ch])

    out_dir.mkdir(parents=True, exist_ok=True)
    include = f'#include "{cfg["include"]}"\n' if cfg.get("include") else ""
    body = ",\n".join("    " + ", ".join(data[c * lvl.height:(c + 1) * lvl.height])
                      for c in range(lvl.width))

    def arr(name, values):
        vals = ", ".join(values) if values else "0"
        return f"const uint8_t {stem}_{name}[] = {{ {vals} }};\n"

    (out_dir / f"{stem}.c").write_text(
        f"// Generated from {src.name} by harness/levels.py - do not edit\n"
        f"#include <stdint.h>\n{include}\n"
        f"const uint8_t {stem}_map[] = {{\n{body}\n}};\n\n"
        + arr("obj_col", [str(o[0]) for o in objs])
        + arr("obj_row", [str(o[1]) for o in objs])
        + arr("obj_type", [o[2] for o in objs]),
        encoding="utf-8")
    meta = "\n".join(f"#define {up}_{k} {v}" for k, v in lvl.meta.items())
    (out_dir / f"{stem}.h").write_text(
        f"// Generated from {src.name} by harness/levels.py - do not edit\n"
        f"#pragma once\n#include <stdint.h>\n\n"
        f"#define {up}_WIDTH {lvl.width}\n#define {up}_HEIGHT {lvl.height}\n"
        f"#define {up}_OBJ_COUNT {len(objs)}\n{meta}\n\n"
        f"extern const uint8_t {stem}_map[];\n"
        f"extern const uint8_t {stem}_obj_col[], {stem}_obj_row[], {stem}_obj_type[];\n",
        encoding="utf-8")
    return out_dir / f"{stem}.c"
