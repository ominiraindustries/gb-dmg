"""Metatile tables (16x16 blocks of 4 tiles) as data: res/metatiles.mt -> build/gen/metatiles.c/.h.

One source for the ROM (mt_tiles / mt_attr), the level preview and Python tests.

    ; comment
    @ tileset bg              tileset the tile indices refer to (res/bg.tiles)
    @ base 65                 VRAM index of that tileset's tile 0 (added to every tile in the C table);
                              "@ base auto" = from game.json vram_order (build/gen/vram.h)
    @ attr SOLID 0x80         attribute names -> bits (any number, up to 8 bits)
    @ attr GROUND 0x01
    FOG       0   0   0   0
    GRASS     1   2   3   4   GROUND          TL TR BL BR (indices or labels of the tileset) + attrs
    WALL      WALL_TL WALL_TR WALL_BL WALL_BR SOLID

Output: enum MT_<NAME> = id (line order, first = 0), MT_COUNT, MT_BASE, ATTR_<NAME> bits,
const uint8_t mt_tiles[MT_COUNT][4], mt_attr[MT_COUNT].
More tables: res/metatiles_<set>.mt -> metatiles_<set>.c/.h with mt_<set>_tiles / mt_<set>_attr,
MT_<SET>_<NAME>, MT_<SET>_COUNT (interiors, caves: one table per tileset; gbe_world copies the
current one to WRAM with world_metatiles()).
Attributes named K_* are exclusive KIND values (games/faro: attr = flags | kind in the low bits):
a metatile with two K_ names is an error (their values would add up to a third kind).
"""
from pathlib import Path


class Metatiles:
    def __init__(self, path, names, tiles, attrs, attr_bits, tileset, base):
        self.path, self.names, self.tiles, self.attrs = Path(path), names, tiles, attrs
        self.attr_bits, self.tileset, self.base = attr_bits, tileset, base
        self.ids = {n: i for i, n in enumerate(names)}

    def vram_tiles(self, mt):
        return [self.base + t for t in self.tiles[mt]]

    def has(self, mt, attr):
        return attr in self.attrs[mt]


def parse(path, labels=None, bases=None):
    """labels: {LABEL: index} of the tileset, needed only when the table uses tile labels."""
    names, tiles, attrs, bits, tileset, base = [], [], [], {}, None, 0
    for n, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split(";", 1)[0].split()
        if not line:
            continue
        where = f"{path}:{n}"
        if line[0] == "@":
            key = line[1].lower()
            if key == "tileset":
                tileset = line[2]
            elif key == "base":
                if line[2] == "auto":
                    if not bases or tileset not in bases:
                        raise ValueError(f"{where}: '@ base auto' needs '{tileset}' in game.json vram_order")
                    base = bases[tileset]
                else:
                    base = int(line[2], 0)
            elif key == "attr":
                bits[line[2].upper()] = int(line[3], 0)
            else:
                raise ValueError(f"{where}: unknown '@ {key}'")
            continue
        if len(line) < 5:
            raise ValueError(f"{where}: expected NAME TL TR BL BR [ATTR...]")
        name = line[0].upper()
        if name in names:
            raise ValueError(f"{where}: metatile {name} defined twice")
        t = []
        for ref in line[1:5]:
            if ref.isdigit():
                t.append(int(ref))
            elif labels and ref.upper() in labels:
                t.append(labels[ref.upper()])
            else:
                raise ValueError(f"{where}: tile '{ref}' is not an index or a label of {tileset}")
        a = [x.upper() for x in line[5:]]
        for x in a:
            if x not in bits:
                raise ValueError(f"{where}: attribute {x} not declared with '@ attr {x} <bit>'")
        if sum(x.startswith("K_") for x in a) > 1:
            raise ValueError(f"{where}: {name} has two kinds {[x for x in a if x.startswith('K_')]} (K_* are values)")
        names.append(name)
        tiles.append(t)
        attrs.append(a)
    return Metatiles(path, names, tiles, attrs, bits, tileset, base)


def convert(src, out_dir, labels=None, bases=None):
    mt = parse(src, labels, bases)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(src).stem                               # metatiles or metatiles_<set>
    tag = stem[len("metatiles"):].lstrip("_")
    P = f"MT_{tag.upper()}_" if tag else "MT_"          # enum prefix
    c = f"mt_{tag}_" if tag else "mt_"                  # C prefix
    enum = "\n".join(f"    {P}{n} = {i}," for i, n in enumerate(mt.names))
    attrs = "\n".join(f"#ifndef ATTR_{k}\n#define ATTR_{k} 0x{v:02X}\n#endif" for k, v in mt.attr_bits.items())
    (out_dir / f"{stem}.h").write_text(
        f"// Generated from {Path(src).name} by harness/metatiles.py - do not edit\n"
        f"#pragma once\n#include <stdint.h>\n\n"
        f"#define {P}BASE {mt.base}\n#define {P}COUNT {len(mt.names)}\n{attrs}\n\n"
        f"enum {{\n{enum}\n}};\n\n"
        f"extern const uint8_t {c}tiles[][4];\nextern const uint8_t {c}attr[];\n",
        encoding="utf-8")
    rows = ",\n".join(f"    {{ {', '.join(str(mt.base + t) for t in tl)} }}   /* {i:2d} {n} */"
                      for i, (n, tl) in enumerate(zip(mt.names, mt.tiles)))
    attr_vals = ", ".join(
        f"0x{sum(mt.attr_bits[x] for x in a):02X}" for a in mt.attrs)
    (out_dir / f"{stem}.c").write_text(
        f"// Generated from {Path(src).name} by harness/metatiles.py - do not edit\n"
        f'#include "{stem}.h"\n\n'
        f"const uint8_t {c}tiles[{P}COUNT][4] = {{\n{rows}\n}};\n\n"
        f"const uint8_t {c}attr[{P}COUNT] = {{ {attr_vals} }};\n",
        encoding="utf-8")
    return out_dir / f"{stem}.c"
