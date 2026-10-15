"""Convert ASCII-art tile files (res/*.tiles) into GBDK C sources.

Format (one file = one tileset, array named after the file stem):
    ; comment
    @ LABEL        optional: next tile gets  #define <STEM>_<LABEL> <index>
    ..####..       8 rows of 8 chars per tile:
    .#----#.         .  color 0 (white / transparent for sprites)
    #------#         -  color 1 (light gray)
    ...              +  color 2 (dark gray)
                     #  color 3 (black)
Blank lines and comments are ignored.

Usage: python asciitiles.py <in.tiles> <out_dir>   -> <out_dir>/<stem>.c and <stem>.h
"""
import sys
from pathlib import Path

COLORS = {".": 0, "-": 1, "+": 2, "#": 3}


def parse(path):
    tiles, labels, rows, pending = [], {}, [], None
    for n, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split(";", 1)[0].strip()
        if not line:
            continue
        if line.startswith("@"):
            if rows:
                raise ValueError(f"{path}:{n}: label inside a tile")
            pending = line[1:].strip().upper()
            continue
        if len(line) != 8 or any(c not in COLORS for c in line):
            raise ValueError(f"{path}:{n}: expected 8 chars of '.-+#', got {raw!r}")
        rows.append(line)
        if len(rows) == 8:
            if pending:
                labels[pending] = len(tiles)
                pending = None
            tiles.append(rows)
            rows = []
    if rows:
        raise ValueError(f"{path}: last tile has {len(rows)} rows, expected 8")
    return tiles, labels


def encode(rows):
    out = []
    for row in rows:
        lo = hi = 0
        for c in row:
            v = COLORS[c]
            lo = (lo << 1) | (v & 1)
            hi = (hi << 1) | (v >> 1)
        out += [lo, hi]
    return out


def metrics(rows):
    """(first ink column, ink width) of a glyph tile; (0, 0) for a blank one."""
    cols = [x for x in range(8) if any(COLORS[r[x]] for r in rows)]
    return (cols[0], cols[-1] - cols[0] + 1) if cols else (0, 0)


def convert(src, out_dir):
    src, out_dir = Path(src), Path(out_dir)
    stem = src.stem
    tiles, labels = parse(src)
    out_dir.mkdir(parents=True, exist_ok=True)
    body = ",\n".join("    " + ",".join(f"0x{b:02X}" for b in encode(t)) for t in tiles)
    vwf = ""
    if stem.startswith("font"):                 # fonts: glyph metrics for gbe_vwf (proportional text)
        m = ", ".join(f"0x{(f << 4) | w:02X}" for f, w in (metrics(t) for t in tiles))
        vwf = (f"// per glyph: (first ink column << 4) | ink width (0 = blank), for gbe_vwf\n"
               f"const uint8_t {stem}_vwf[] = {{ {m} }};\n")
    (out_dir / f"{stem}.c").write_text(encoding="utf-8", data=
        f"// Generated from {src.name} by harness/asciitiles.py - do not edit\n"
        f"#include <stdint.h>\n\nconst uint8_t {stem}_tiles[] = {{\n{body}\n}};\n{vwf}")
    defines = "\n".join(f"#define {stem.upper()}_{k} {v}" for k, v in labels.items())
    (out_dir / f"{stem}.h").write_text(encoding="utf-8", data=
        f"// Generated from {src.name} by harness/asciitiles.py - do not edit\n"
        f"#pragma once\n#include <stdint.h>\n\n"
        f"extern const uint8_t {stem}_tiles[];\n#define {stem.upper()}_COUNT {len(tiles)}\n{defines}\n"
        + (f"extern const uint8_t {stem}_vwf[];\n" if stem.startswith("font") else ""))
    return out_dir / f"{stem}.c"


if __name__ == "__main__":
    print(convert(sys.argv[1], sys.argv[2]))
