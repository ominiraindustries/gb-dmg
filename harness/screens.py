"""Convert .screen mockups (design/screens/*.screen, made by the ui-designer) into C tile maps,
so what the UI agent designs is exactly what the game shows.

game.json:
    "screens": ["title", "clear"],          mockups to convert (design/screens/<name>.screen)
    "vram_order": ["bg", "font", "ui"]       BG tilesets in VRAM order: base = sum of previous counts

Output build/gen/screen_<name>.c/.h:
    const uint8_t screen_<name>_map[18 * 20];        VRAM tile indices, row-major
    const uint8_t screen_<name>_spr[n * 4];          x, y, tile, flags (bit0 flipx, bit1 flipy);
    #define SCREEN_<NAME>_SPR_COUNT n                 sprite tiles are not offset (sprite VRAM)
"""
from pathlib import Path

import preview


def convert(src, out_dir, sets, vram_order):
    src, out_dir = Path(src), Path(out_dir)
    name = src.stem
    bases, base = {}, 0
    for ts_name in vram_order:
        bases[ts_name] = base
        base += len(sets[ts_name].tiles)
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
        f"#define SCREEN_{name.upper()}_SPR_COUNT {len(sprs)}\n", encoding="utf-8")
    return out_dir / f"screen_{name}.c"
