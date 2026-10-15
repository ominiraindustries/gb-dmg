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

Proportional text (game.json "vwf": {"fonts": ["font_mini", "font_mini_lower", "font_mini_es"],
"slot": "text"} + a reserved slot {"text": 64} in vram_order): every text of a mockup (its letters,
digits and font punctuation, also punctuation given through the legend) is drawn at its real width
(harness/vwf.py) into its own tiles, allocated in the slot from the mockup's "text: <offset>" line
(default 0; overlays such as a dialogue over the play screen take another offset). Texts are
left-aligned in their cells; "center: PULSA_START TITULO" (text names) centres those on the screen,
shifting the drawing inside the text's cells (a guess from the position centred "Continuar" and not
"Salir" in the same menu; centring in its own cells left odd-length texts 4 px off). The fonts need not be in
VRAM. Extra output:
    const uint8_t screen_<name>_text[];          the text tiles (16 bytes each), in VRAM order
    #define SCREEN_<NAME>_TEXT_FIRST t            VRAM tile of the first one; _TEXT_COUNT n
    #define SCREEN_<NAME>_TILE_<TEXT> t           first tile of that text, _TILES_<TEXT> its cells
The game loads screen_<name>_text at SCREEN_<NAME>_TEXT_FIRST with the screen; code that rewrites a
text redraws its _TILES_ tiles with gbe_vwf (vwf_clear + vwf_draw + tiles_push).
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
        if isinstance(slot, dict):                     # {"text": 64}: a reserved slot (proportional text)
            (name, size), = slot.items()
            bases[name] = base
            base += size
            continue
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
    for slot in vram_order:                             # reserved slots: their size too
        if isinstance(slot, dict):
            (name, size), = slot.items()
            lines += f"\n#define VRAM_{name.upper()}_COUNT {size}"
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    (Path(out_dir) / "vram.h").write_text(
        "// Generated from game.json vram_order by harness/screens.py - do not edit\n"
        f"#pragma once\n{lines}\n", encoding="utf-8")
    return bases


FONT_PUNCT = {"DOT": ".", "COLON": ":", "DASH": "-", "EXCLAM": "!", "QUESTION": "?", "SLASH": "/",
              "COMMA": ",", "APOSTROPHE": "'", "EXCL_OPEN": "\u00a1", "QUEST_OPEN": "\u00bf"}


def _read(path):
    """(legend {char: ref}, 18 grid rows, text offset) of a .screen mockup."""
    legend, grid, section, offset, centre = {}, [], None, 0, set()
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.split(";", 1)[0].rstrip() if section != "grid" else raw.rstrip("\n")
        if section == "grid" and raw.strip().startswith(";"):
            continue
        key = line.strip().lower()
        if key.startswith("tilesets:"):
            section = None
        elif key.startswith("text:") and section != "grid":
            offset = int(key.split(":", 1)[1])
        elif key.startswith("center:") and section != "grid":
            centre |= set(line.split(":", 1)[1].upper().split())
        elif key in ("legend:", "grid:", "sprites:"):
            section = key[:-1]
        elif section == "legend" and line.strip():
            legend[line[0]] = line[2:].strip()
        elif section == "grid" and line.strip():
            grid.append(line.ljust(20)[:20])
    return legend, grid, offset, centre


def vwf_runs(path, gdir, vwf_cfg, base, size):
    """Proportional texts of a mockup: [{name, r, c, n, text, x0, tile, data}] (see the module doc)."""
    import vwf
    legend, grid, offset, centre = _read(path)
    names = {(r, c): t for t, r, c, n, _ in text_runs(path)}
    fonts = tuple(vwf_cfg["fonts"])
    runs, tile = [], base + offset
    for r, row in enumerate(grid):
        chars = []
        for ch in row:
            if ch in legend:
                ref = legend[ch].split(":")[-1].upper()
                chars.append(FONT_PUNCT.get(ref))
            elif ch in TEXT_CHARS:
                chars.append(ch)
            elif ch in " .":
                chars.append(" ")
            else:
                chars.append(None)
        c = 0
        while c < 20:
            if chars[c] in (None, " "):
                c += 1
                continue
            start = end = c
            while c < 20:
                if chars[c] not in (None, " "):
                    end = c
                    c += 1
                elif chars[c] == " " and c + 1 < 20 and chars[c + 1] not in (None, " "):
                    c += 1
                else:
                    break
            n = end - start + 1
            text = "".join(chars[start:end + 1])
            w = vwf.width(gdir, text, fonts)
            if w > n * 8:
                raise ValueError(f"{path}: row {r} text {text!r} is {w} px, wider than its {n} cells")
            name = names.get((r, start), f"R{r}C{start}")
            centred = name in centre                # centred on the SCREEN, moving the drawing
            x0 = min(max((160 - w) // 2 - start * 8, 0), n * 8 - w) if centred else 0   # inside its cells
            data = vwf.render(gdir, text, n, x0, fonts)
            runs.append({"name": name, "r": r, "c": start, "n": n,
                         "text": text, "x0": x0, "tile": tile, "data": data})
            tile += n
    if tile > base + size:
        raise ValueError(f"{path}: proportional text needs {tile - base} tiles of the text slot, it has {size}")
    return runs


def screen_map(src, sets, vram_order, vwf_cfg=None, gdir=None):
    """(18x20 VRAM tile numbers, sprites, vwf runs) of a mockup, as the build converts it."""
    bases = vram_bases(vram_order, sets)
    cells, sprs = preview.parse_screen(src, sets)
    runs, text_cell = [], {}
    if vwf_cfg:
        slot = vwf_cfg["slot"]
        size = next(next(iter(e.values())) for e in vram_order if isinstance(e, dict) and slot in e)
        runs = vwf_runs(src, gdir, vwf_cfg, bases[slot], size)
        text_cell = {(run["r"], run["c"] + k): run["tile"] + k for run in runs for k in range(run["n"])}
    grid = []
    for r, row in enumerate(cells):
        out = []
        for c, (ts, i) in enumerate(row):
            if (r, c) in text_cell:
                out.append(text_cell[(r, c)])
                continue
            if ts.name not in bases:
                raise ValueError(f"{src}: tileset '{ts.name}' is not in game.json vram_order")
            out.append(bases[ts.name] + i)
        grid.append(out)
    return grid, sprs, runs


def convert(src, out_dir, sets, vram_order, vwf_cfg=None, gdir=None):
    src, out_dir = Path(src), Path(out_dir)
    name = src.stem
    grid, sprs, runs = screen_map(src, sets, vram_order, vwf_cfg, gdir)
    tiles = [t for row in grid for t in row]
    rows = ",\n".join("    " + ", ".join(str(t) for t in tiles[r * 20:(r + 1) * 20]) for r in range(18))
    spr = ", ".join(f"{x}, {y}, {i}, {int(fx) | (int(fy) << 1)}" for ts, i, x, y, fx, fy in sprs) or "0"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"screen_{name}.c").write_text(
        f"// Generated from {src.name} by harness/screens.py - do not edit\n#include <stdint.h>\n\n"
        f"const uint8_t screen_{name}_map[] = {{\n{rows}\n}};\n"
        f"const uint8_t screen_{name}_spr[] = {{ {spr} }};\n"
        + (f"const uint8_t screen_{name}_text[] = {{\n"
           + ",\n".join("    " + ", ".join(f"0x{b:02X}" for b in t) for run in runs for t in run["data"])
           + "\n};\n" if runs else ""), encoding="utf-8")
    (out_dir / f"screen_{name}.h").write_text(
        f"// Generated from {src.name} by harness/screens.py - do not edit\n#pragma once\n#include <stdint.h>\n\n"
        f"extern const uint8_t screen_{name}_map[];\nextern const uint8_t screen_{name}_spr[];\n"
        f"#define SCREEN_{name.upper()}_SPR_COUNT {len(sprs)}\n"
        + "".join(f"#define SCREEN_{name.upper()}_AT_{t} ({r} * 32 + {c})   // \"{txt}\"\n"
                  f"#define SCREEN_{name.upper()}_LEN_{t} {n}\n" for t, r, c, n, txt in text_runs(src))
        + (f"extern const uint8_t screen_{name}_text[];\n"
           f"#define SCREEN_{name.upper()}_TEXT_FIRST {runs[0]['tile']}\n"
           f"#define SCREEN_{name.upper()}_TEXT_COUNT {sum(run['n'] for run in runs)}\n"
           + "".join(f"#define SCREEN_{name.upper()}_TILE_{run['name']} {run['tile']}   // \"{run['text']}\"\n"
                     f"#define SCREEN_{name.upper()}_TILES_{run['name']} {run['n']}\n" for run in runs)
           if runs else ""),
        encoding="utf-8")
    return out_dir / f"screen_{name}.c"
