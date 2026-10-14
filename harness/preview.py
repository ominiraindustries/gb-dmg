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

Chars without a legend entry: letters and digits map to the font tileset (if listed), lowercase
letters to font_lower (LOWER_A..; harness/common/font_lower.tiles) if listed, else to uppercase; space
and '.' map to the tile labelled BLANK (any listed tileset), else tile 0 of the first non-font one.
The font's punctuation has labels: DASH EXCLAM DOT COLON QUESTION SLASH (use them in the legend).
Legend keys should not be letters: a word that mixes legend letters with text letters is an error
(games/dungeon: key 'u' turned the u of "puerta" into a tile). Use symbols or Greek letters.
"""
import re
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

    # A letter used as a legend key wins over text: in a word it silently becomes that tile
    # (games/dungeon: key 'u' = arrow tile inside "puerta"). Words mixing legend letters and text
    # letters are an error; legend keys should not be letters at all once text has lowercase.
    keys = {c for c in legend if c.isascii() and c.isalpha()}
    for ty, row in enumerate(grid):
        for m in re.finditer(r"[A-Za-z]{2,}", row):
            word = m.group()
            if any(c in keys for c in word) and any(c not in keys for c in word):
                raise ValueError(f"{path}: row {ty} word {word!r} mixes legend keys "
                                 f"{sorted(set(word) & keys)} with text: use a non-letter key")

    def resolve(ref):
        if ":" in ref:
            name, tile = ref.split(":", 1)
            return sets[name], sets[name].index(tile)
        for ts in tilesets:
            if ref.isdigit() or ref.upper() in ts.labels:
                return ts, ts.index(ref)
        raise KeyError(f"{path}: tile '{ref}' not found in {[t.name for t in tilesets]}")

    font = next((t for t in tilesets if "DIGIT0" in t.labels and "LETTER_A" in t.labels), None)
    lower = next((t for t in tilesets if "LOWER_A" in t.labels), None)
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
            elif ch.isalpha() and ch.islower() and ch.isascii() and (lower or font):
                if lower:
                    out_row.append((lower, lower.labels["LOWER_A"] + ord(ch) - ord("a")))
                else:
                    out_row.append((font, font.labels["LETTER_A"] + ord(ch) - ord("a")))
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


def render_level(lvl_path, cfg, mt, ts, out, strip_rows=40):
    """Vertical level (game.json "order": "rows") drawn with its metatiles, in strips of
    strip_rows rows side by side (bottom of the level = bottom-left), row numbers every 10 and
    objects as boxed letters (the object layer)."""
    import levels
    lvl = levels.parse(lvl_path, layered=cfg["width"])
    names = {"MT_" + n: i for n, i in mt.ids.items()}
    obj_cells = cfg.get("object_cells", {})
    w, h = lvl.width, lvl.height
    strips = (h + strip_rows - 1) // strip_rows
    sw, gap = w * 16, 34
    img = Image.new("RGB", (strips * (sw + gap) + gap, strip_rows * 16 + 8), (230, 230, 240))
    draw = ImageDraw.Draw(img)
    for row in range(h):
        line = h - 1 - row
        s, k = divmod(row, strip_rows)
        x0, y0 = gap + s * (sw + gap), 4 + (strip_rows - 1 - k) * 16
        if row % 10 == 0:
            draw.text((x0 - gap + 2, y0 + 3), str(row), fill=(0, 0, 0))
        for col in range(w):
            ch, ob = lvl.rows[line][col], lvl.layer[line][col]
            name = obj_cells.get(ob) or cfg["cells"].get(ch)
            tl = mt.tiles[names[name]] if name in names else [0, 0, 0, 0]
            for q, t in enumerate(tl):
                img.paste(ts.images[t], (x0 + col * 16 + (q & 1) * 8, y0 + (q >> 1) * 8))
            if ob != "." and ob in cfg.get("objects", {}):
                bx, by = x0 + col * 16 + 3, y0 + 2
                draw.rectangle((bx - 1, by - 1, bx + 10, by + 11), fill=(255, 255, 255), outline=(200, 0, 0))
                draw.text((bx + 2, by), ob, fill=(200, 0, 0))
    img.save(out)


GRID_COLORS = [(250, 250, 250), (60, 60, 70), (160, 100, 40), (200, 60, 40), (120, 200, 120),
               (90, 90, 220), (40, 160, 200), (230, 200, 60)]


def render_grid_level(lvl_path, cfg, out, cell=16):
    """Top-down grid level: one color per cell char (legend in the image), object letters on top."""
    import levels
    lvl = levels.parse(lvl_path, layered=cfg["width"])
    chars = list(cfg.get("cells", {}))
    w, h = lvl.width, lvl.height
    img = Image.new("RGB", (w * cell + 160, max(h * cell, 16 * len(chars)) + 8), (235, 235, 240))
    d = ImageDraw.Draw(img)
    for y in range(h):
        for x in range(w):
            ch = lvl.rows[y][x]
            col = GRID_COLORS[chars.index(ch) % len(GRID_COLORS)] if ch in chars else (255, 0, 255)
            d.rectangle((x * cell, y * cell, x * cell + cell - 1, y * cell + cell - 1), fill=col,
                        outline=(200, 200, 200))
            ob = lvl.layer[y][x]
            if ob != ".":
                d.text((x * cell + 4, y * cell + 2), ob, fill=(220, 0, 0))
    for k, ch in enumerate(chars):
        y = 4 + k * 16
        d.rectangle((w * cell + 8, y, w * cell + 20, y + 12), fill=GRID_COLORS[k % len(GRID_COLORS)])
        d.text((w * cell + 26, y), f"'{ch}' {cfg['cells'][ch]}", fill=(0, 0, 0))
    for k, (ch, name) in enumerate(cfg.get("objects", {}).items()):
        d.text((w * cell + 8, 8 + (len(chars) + k) * 16), f"{ch} = {name}", fill=(200, 0, 0))
    img.save(out)


def preview(gdir):
    out = gdir / "build" / "preview"
    out.mkdir(parents=True, exist_ok=True)
    sets = find_tilesets(gdir)
    written = []
    mt_file = gdir / "res" / "metatiles.mt"
    cfg = _config(gdir).get("levels", {})
    if cfg.get("order") == "grid":
        for lvl in sorted((gdir / "res").glob("*.lvl")):
            p = out / f"level_{lvl.stem}.png"
            render_grid_level(lvl, cfg, p)
            written.append(p)
    if mt_file.exists() and cfg.get("order") == "rows":
        import metatiles
        import screens
        bases = screens.vram_bases(_config(gdir)["vram_order"], sets) if _config(gdir).get("vram_order") else None
        mt = metatiles.parse(mt_file, sets[_mt_tileset(mt_file)].labels, bases)   # "@ base auto"
        for lvl in sorted((gdir / "res").glob("*.lvl")):
            p = out / f"level_{lvl.stem}.png"
            render_level(lvl, cfg, mt, sets[mt.tileset], p)
            written.append(p)
    for map_file in sorted((gdir / "res" / "maps").glob("*.map")):   # world maps (world.py)
        import world
        m = world.load(gdir, map_file)
        mt_file = gdir / "res" / f"{m.mt_stem}.mt"
        import metatiles
        import screens
        bases = screens.vram_bases(_config(gdir)["vram_order"], sets) if _config(gdir).get("vram_order") else None
        mt = metatiles.parse(mt_file, sets[_mt_tileset(mt_file)].labels, bases)
        written.append(world.render(m, mt, sets, out / f"map_{m.name.lower()}.png"))
    for name, ts in sets.items():
        if (gdir / "res" / f"{name}.tiles").exists() or name in _common_used(gdir):
            p = out / f"tiles_{name}.png"
            render_sheet(ts, p)
            written.append(p)
    if (gdir / "res" / "view.pcs").exists():          # first-person view pieces (fpview.py)
        import fpview
        written += fpview.preview(gdir, out)
    for scr in sorted((gdir / "design" / "screens").glob("*.screen")):
        p = out / f"screen_{scr.stem}.png"
        render_screen(scr, sets, p)
        written.append(p)
    return written


def _config(gdir):
    import json
    cfg = gdir / "game.json"
    return json.loads(cfg.read_text(encoding="utf-8")) if cfg.exists() else {}


def _common_used(gdir):
    return _config(gdir).get("common_res", [])


def _mt_tileset(mt_file):
    for line in mt_file.read_text(encoding="utf-8").splitlines():
        parts = line.split(";", 1)[0].split()
        if parts[:2] == ["@", "tileset"]:
            return parts[2]
    raise ValueError(f"{mt_file}: missing '@ tileset <name>'")


if __name__ == "__main__":
    for p in preview(ROOT / "games" / sys.argv[1]):
        print(p)
