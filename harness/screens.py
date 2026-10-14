"""Convert .screen mockups (design/screens/*.screen, made by the ui-designer) into C tile maps,
so what the UI agent designs is exactly what the game shows.

game.json:
    "screens": ["title", "clear"],          mockups to convert (design/screens/<name>.screen)
    "vram_order": ["bg", "font", "ui"]       BG tilesets in VRAM order: base = sum of previous counts;
                                             a list ["uiscreens", "bg"] = tilesets loaded in turn
                                             into the same slot (size = the largest)
The build also writes build/gen/vram.h: #define VRAM_<NAME> <base> for every tileset of vram_order,
and "@ base auto" in metatiles.mt / view.pcs takes the base from there (hand-written bases broke the
shmup's screens when the shared font grew by one glyph).

Output build/gen/screen_<name>.c/.h:
    const uint8_t screen_<name>_map[18 * 20];        VRAM tile indices, row-major
    const uint8_t screen_<name>_spr[n * 4];          x, y, tile, flags (bit0 flipx, bit1 flipy);
    #define SCREEN_<NAME>_SPR_COUNT n                 sprite tiles are not offset (sprite VRAM)
    #define SCREEN_<NAME>_AT_<TEXT> (row * 32 + col)  every text run of the mockup: offset in a
    #define SCREEN_<NAME>_LEN_<TEXT> n                32-wide BG/window map, and its length

Text runs: font characters (letters, digits, ! ? : -) without a legend entry; words separated by
one blank stay in one run. <TEXT> = the run with non-alphanumerics as '_' (repeats get _2, _3).
Code that rewrites or blinks a text uses these instead of hand coordinates: in games/shmup the
code wrote "NUEVO RECORD!" one column off the mockup (ui.md and the .screen disagreed).
"""
import re
from pathlib import Path

import preview


TEXT_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!?:-/,'¡¿")


def text_runs(path):
    """[(name, row, col, length, text)] of the text in a .screen grid (see the module doc)."""
    legend, grid, section = set(), [], None
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.split(";", 1)[0].rstrip() if section != "grid" else raw.rstrip("\n")
        if section == "grid" and raw.strip().startswith(";"):
            continue
        key = line.strip().lower()
        if key.startswith("tilesets:"):
            section = None
        elif key in ("legend:", "grid:", "sprites:"):
            section = key[:-1]
        elif section == "legend" and line.strip():
            ref = line[2:].strip().upper().split(":")[-1]
            if ref not in ("DASH", "EXCLAM", "DOT", "COLON", "QUESTION", "SLASH",   # font punctuation is text
                           "COMMA", "APOSTROPHE", "EXCL_OPEN", "QUEST_OPEN"):        # (font_es)
                legend.add(line[0])
        elif section == "grid" and line.strip():
            grid.append(line.ljust(20)[:20])
    runs, seen = [], {}
    for r, line in enumerate(grid):
        c = 0
        while c < 20:
            if line[c] in TEXT_CHARS and line[c] not in legend:
                start, end = c, c
                while c < 20:
                    if line[c] in TEXT_CHARS and line[c] not in legend:
                        end = c
                        c += 1
                    elif c + 1 < 20 and line[c + 1] in TEXT_CHARS and line[c + 1] not in legend \
                            and line[c] not in TEXT_CHARS:
                        c += 1                          # one blank inside a run
                    else:
                        break
                text = line[start:end + 1]
                name = re.sub(r"[^A-Z0-9]+", "_", text.upper()).strip("_") or "T"
                seen[name] = seen.get(name, 0) + 1
                if seen[name] > 1:
                    name = f"{name}_{seen[name]}"
                runs.append((name, r, start, end - start + 1, text))
            else:
                c += 1
    return runs


def vram_bases(vram_order, sets):
    """{tileset: VRAM base index} from game.json vram_order (see the module doc)."""
    bases, base = {}, 0
    for slot in vram_order:
        group = slot if isinstance(slot, list) else [slot]
        for ts_name in group:
            if ts_name not in sets:
                raise ValueError(f"vram_order: tileset '{ts_name}' not found")
            bases[ts_name] = base
        base += max(len(sets[n].tiles) for n in group)
    if base > 256:
        raise ValueError(f"vram_order: {base} BG tiles, more than 256")
    return bases


def write_vram_h(vram_order, sets, out_dir):
    bases = vram_bases(vram_order, sets)
    lines = "\n".join(f"#define VRAM_{n.upper()} {b}" for n, b in bases.items())
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    (Path(out_dir) / "vram.h").write_text(
        "// Generated from game.json vram_order by harness/screens.py - do not edit\n"
        f"#pragma once\n{lines}\n", encoding="utf-8")
    return bases


def convert(src, out_dir, sets, vram_order):
    src, out_dir = Path(src), Path(out_dir)
    name = src.stem
    bases = vram_bases(vram_order, sets)
    cells, sprs = preview.parse_screen(src, sets)
    tiles = []
    for row in cells:
        for ts, i in row:
            if ts.name not in bases:
                raise ValueError(f"{src}: tileset '{ts.name}' is not in game.json vram_order")
            tiles.append(bases[ts.name] + i)
    rows = ",\n".join("    " + ", ".join(str(t) for t in tiles[r * 20:(r + 1) * 20]) for r in range(18))
    spr = ", ".join(f"{x}, {y}, {i}, {int(fx) | (int(fy) << 1)}" for ts, i, x, y, fx, fy in sprs) or "0"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"screen_{name}.c").write_text(
        f"// Generated from {src.name} by harness/screens.py - do not edit\n#include <stdint.h>\n\n"
        f"const uint8_t screen_{name}_map[] = {{\n{rows}\n}};\n"
        f"const uint8_t screen_{name}_spr[] = {{ {spr} }};\n", encoding="utf-8")
    (out_dir / f"screen_{name}.h").write_text(
        f"// Generated from {src.name} by harness/screens.py - do not edit\n#pragma once\n#include <stdint.h>\n\n"
        f"extern const uint8_t screen_{name}_map[];\nextern const uint8_t screen_{name}_spr[];\n"
        f"#define SCREEN_{name.upper()}_SPR_COUNT {len(sprs)}\n"
        + "".join(f"#define SCREEN_{name.upper()}_AT_{t} ({r} * 32 + {c})   // \"{txt}\"\n"
                  f"#define SCREEN_{name.upper()}_LEN_{t} {n}\n" for t, r, c, n, txt in text_runs(src)),
        encoding="utf-8")
    return out_dir / f"screen_{name}.c"
