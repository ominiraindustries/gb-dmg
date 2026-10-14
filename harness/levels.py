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

`parse()` is also used by pure-Python level lint tests.
"""
from pathlib import Path


class Level:
    def __init__(self, path, rows, meta):
        self.path, self.rows, self.meta = Path(path), rows, meta
        self.height = len(rows)
        self.width = len(rows[0]) if rows else 0

    def cell(self, col, row):
        return self.rows[row][col]

    def column(self, col):
        return "".join(r[col] for r in self.rows)


def parse(path, height=None):
    rows, meta, in_grid = [], {}, False
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
            rows.append(line)
    if not rows:
        raise ValueError(f"{path}: no grid")
    width = len(rows[0])
    for i, r in enumerate(rows):
        if len(r) != width:
            raise ValueError(f"{path}: grid row {i} has {len(r)} chars, row 0 has {width}")
    if height is not None and len(rows) != height:
        raise ValueError(f"{path}: grid has {len(rows)} rows, expected {height}")
    return Level(path, rows, meta)


def convert(src, out_dir, cfg):
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
