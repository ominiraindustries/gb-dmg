"""Render tilesets and screen mockups to PNG so art and layouts can be reviewed as images.

    python harness/gb.py preview <game>
      -> games/<game>/build/preview/tiles_<stem>.png    every tileset, scaled, with index + label
      -> games/<game>/build/preview/screen_<name>.png   every games/<game>/design/screens/*.screen

Screen mockup format (.screen):
    ; comment
    tilesets: bg font            tilesets used, in lookup order (game res/ first, then harness/common/)
    legend:
    # WALL                       char -> tile label (searched in tilesets in order)
    b bg:BRICK_A_L               char -> tileset:LABEL
    3 bg:12                      char -> tileset:index
    grid:
    ####################         18 lines x 20 chars (the 160x144 screen, 8x8 tiles)
    ...
    sprites:
    spr:PADDLE_L 56 132          tileset:LABEL x y [flipx] [flipy]   (screen pixels, top-left)

Chars without a legend entry: letters and digits map to the font tileset (if listed); space
and '.' map to the tile labelled BLANK (any listed tileset), else tile 0 of the first non-font one.
The font's punctuation has labels: DASH EXCLAM DOT COLON QUESTION (use them in the legend).
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import asciitiles

ROOT = Path(__file__).resolve().parent.parent
SHADES = [(255, 255, 255), (170, 170, 170), (85, 85, 85), (0, 0, 0)]  # DMG gray palette


def tile_image(rows, transparent=False):
    img = Image.new("RGBA", (8, 8))
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            v = asciitiles.COLORS[c]
            img.putpixel((x, y), (0, 0, 0, 0) if transparent and v == 0 else SHADES[v] + (255,))
    return img


class Tileset:
    def __init__(self, path):
        self.name = path.stem
        self.tiles, self.labels = asciitiles.parse(path)
        self.images = [tile_image(t) for t in self.tiles]
        self.sprites = [tile_image(t, transparent=True) for t in self.tiles]

    def index(self, ref):
        if ref.isdigit():
            return int(ref)
        if ref.upper() not in self.labels:
            raise KeyError(f"tile '{ref}' not in {self.name}")
        return self.labels[ref.upper()]


def find_tilesets(gdir):
    sets = {}
    for p in sorted((ROOT / "harness" / "common").glob("*.tiles")) + sorted((gdir / "res").glob("*.tiles")):
        sets[p.stem] = Tileset(p)
    return sets


def render_sheet(ts, out, scale=4, cols=8):
    cell_w, cell_h = max(8 * scale + 8, 76), 8 * scale + 22
    rows = (len(ts.tiles) + cols - 1) // cols
    img = Image.new("RGB", (cols * cell_w, rows * cell_h), (230, 230, 240))
    draw = ImageDraw.Draw(img)
    names = {v: k for k, v in ts.labels.items()}
    for i, t in enumerate(ts.images):
        x, y = (i % cols) * cell_w + 4, (i // cols) * cell_h + 4
        img.paste(t.resize((8 * scale, 8 * scale), Image.NEAREST), (x, y))
        draw.text((x, y + 8 * scale + 1), f"{i} {names.get(i, '')}"[:10], fill=(0, 0, 0))
    img.save(out)


def parse_screen(path, sets):
    """Read a .screen mockup. Returns (cells, sprites):
    cells: 18 rows x 20 (Tileset, index); sprites: list of (Tileset, index, x, y, flipx, flipy)."""
    tilesets, legend, grid, sprites, section = [], {}, [], [], None
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split(";", 1)[0].rstrip() if section != "grid" else raw.rstrip("\n")
        if section == "grid" and raw.strip().startswith(";"):
            continue
        key = line.strip().lower()
        if key.startswith("tilesets:"):
            tilesets = [sets[s] for s in line.split(":", 1)[1].split()]
            section = None
        elif key in ("legend:", "grid:", "sprites:"):
            section = key[:-1]
        elif not line.strip():
            continue
        elif section == "legend":
            ch, ref = line[0], line[2:].strip()
            legend[ch] = ref
        elif section == "grid":
            grid.append(line.ljust(20)[:20])
        elif section == "sprites":
            sprites.append((n, line.split()))
    if not tilesets:
        raise ValueError(f"{path}: missing 'tilesets:' line")
    if len(grid) != 18:
        raise ValueError(f"{path}: grid has {len(grid)} rows, expected 18")

    def resolve(ref):
        if ":" in ref:
            name, tile = ref.split(":", 1)
            return sets[name], sets[name].index(tile)
        for ts in tilesets:
            if ref.isdigit() or ref.upper() in ts.labels:
                return ts, ts.index(ref)
        raise KeyError(f"{path}: tile '{ref}' not found in {[t.name for t in tilesets]}")

    font = next((t for t in tilesets if "DIGIT0" in t.labels and "LETTER_A" in t.labels), None)
    blank = next(((t, t.labels["BLANK"]) for t in tilesets if "BLANK" in t.labels),
                 next(((t, 0) for t in tilesets if t is not font), (tilesets[0], 0)))
    cells = []
    for ty, row in enumerate(grid):
        out_row = []
        for tx, ch in enumerate(row):
            if ch in legend:
                out_row.append(resolve(legend[ch]))
            elif font and ch.isdigit():
                out_row.append((font, font.labels["DIGIT0"] + int(ch)))
            elif font and ch.isalpha() and ch.isupper():
                out_row.append((font, font.labels["LETTER_A"] + ord(ch) - ord("A")))
            elif ch in " .":
                out_row.append(blank)
            else:
                raise KeyError(f"{path}: char {ch!r} at ({tx},{ty}) has no legend entry")
        cells.append(out_row)
    sprs = []
    for n, parts in sprites:
        ts, i = resolve(parts[0])
        sprs.append((ts, i, int(parts[1]), int(parts[2]), "flipx" in parts[3:], "flipy" in parts[3:]))
    return cells, sprs


def render_screen(path, sets, out, scale=3):
    cells, sprs = parse_screen(path, sets)
    screen = Image.new("RGBA", (160, 144), SHADES[0] + (255,))
    for ty, row in enumerate(cells):
        for tx, (ts, i) in enumerate(row):
            screen.paste(ts.images[i], (tx * 8, ty * 8))
    for ts, i, x, y, fx, fy in sprs:
        spr = ts.sprites[i]
        if fx:
            spr = spr.transpose(Image.FLIP_LEFT_RIGHT)
        if fy:
            spr = spr.transpose(Image.FLIP_TOP_BOTTOM)
        screen.alpha_composite(spr, (x, y))
    screen.convert("RGB").resize((160 * scale, 144 * scale), Image.NEAREST).save(out)


def preview(gdir):
    out = gdir / "build" / "preview"
    out.mkdir(parents=True, exist_ok=True)
    sets = find_tilesets(gdir)
    written = []
    for name, ts in sets.items():
        if (gdir / "res" / f"{name}.tiles").exists() or name in _common_used(gdir):
            p = out / f"tiles_{name}.png"
            render_sheet(ts, p)
            written.append(p)
    for scr in sorted((gdir / "design" / "screens").glob("*.screen")):
        p = out / f"screen_{scr.stem}.png"
        render_screen(scr, sets, p)
        written.append(p)
    return written


def _common_used(gdir):
    import json
    cfg = gdir / "game.json"
    return json.loads(cfg.read_text(encoding="utf-8")).get("common_res", []) if cfg.exists() else []


if __name__ == "__main__":
    for p in preview(ROOT / "games" / sys.argv[1]):
        print(p)
