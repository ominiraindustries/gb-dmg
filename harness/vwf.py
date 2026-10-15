"""Proportional (variable-width) text: the Python reference of gbe_vwf.c, plus a decoder for tests.

The user found monospace text airy ("an 'i' gets the same 8 px as an 'n'"). gbe_vwf draws each glyph
at its ink width with a fixed 1 px gap into a strip of tiles (one 8 px row of text); the game copies
the strip to VRAM and puts the strip's tile numbers in the map. Glyphs come from the shared fonts
(font: digits A-Z - ! . : ? /, font_lower: a-z, font_es: , ' ¡ ¿); asciitiles.metrics() measures
each glyph (first ink column, ink width), so fonts need no width table by hand.

    render(gdir, "Hola, Tilo", ntiles)  -> list of ntiles 16-byte tiles (== what the ROM draws)
    decode(gdir, tiles)                 -> the text read back from tile bytes (tests read the screen)
    width(gdir, text)                   -> pixels
A space is SPACE px (gbe_vwf's vwf_space); every glyph is followed by GAP px.
"""
from pathlib import Path

import asciitiles

SPACE, GAP = 3, 1
ROOT = Path(__file__).resolve().parents[1]
PUNCT = {"-": "DASH", "!": "EXCLAM", ".": "DOT", ":": "COLON", "?": "QUESTION", "/": "SLASH"}
ES = {",": 0, "'": 1, "¡": 2, "¿": 3}
_cache = {}


def _font(gdir, stem):
    for d in (Path(gdir) / "res", ROOT / "harness" / "common"):
        p = d / f"{stem}.tiles"
        if p.exists():
            break
    key = str(p)
    if key not in _cache:
        tiles, labels = asciitiles.parse(p)
        _cache[key] = ([asciitiles.encode(t) for t in tiles], [asciitiles.metrics(t) for t in tiles], labels)
    return _cache[key]


def glyph(gdir, c, fonts=("font", "font_lower", "font_es")):
    """(16 bytes, first, width) of char c, or None for a space / unknown char (as gbe_vwf)."""
    main, lower, es = fonts
    data, met, lab = _font(gdir, main)
    if "A" <= c <= "Z":
        k = lab["LETTER_A"] + ord(c) - ord("A")
    elif "0" <= c <= "9":
        k = lab["DIGIT0"] + ord(c) - ord("0")
    elif c in PUNCT:
        k = lab[PUNCT[c]]
    elif "a" <= c <= "z":
        data, met, lab = _font(gdir, lower)
        k = ord(c) - ord("a")
    elif c in ES:
        data, met, lab = _font(gdir, es)
        k = ES[c]
    else:
        return None
    return data[k], met[k][0], met[k][1]


def width(gdir, text, fonts=("font", "font_lower", "font_es")):
    x = 0
    for c in text:
        g = glyph(gdir, c, fonts)
        x += SPACE if g is None or not g[2] else g[2] + GAP
    return x


def render(gdir, text, ntiles, x=0, fonts=("font", "font_lower", "font_es")):
    buf = [[0] * 16 for _ in range(ntiles)]
    for c in text:
        g = glyph(gdir, c, fonts)
        if g is None or not g[2]:
            x += SPACE
            continue
        data, first, w = g
        t, s = x >> 3, x & 7
        for b in range(16):
            v = (data[b] << first) & 0xFF
            if t < ntiles:
                buf[t][b] |= v >> s
            if s and t + 1 < ntiles:
                buf[t + 1][b] |= (v << (8 - s)) & 0xFF
        x += w + GAP
    return buf


def decode(gdir, tiles, fonts=("font", "font_lower", "font_es")):
    """Read proportional text back from consecutive tiles (one text row). Greedy: at each ink column
    the longest glyph whose pixels match; gaps wider than GAP + 1 px become spaces."""
    cols = []                                   # per pixel column: 8 rows of 2-bit colors
    for t in tiles:
        for x in range(8):
            cols.append(tuple(((t[2 * r] >> (7 - x)) & 1) | (((t[2 * r + 1] >> (7 - x)) & 1) << 1)
                              for r in range(8)))
    chars = [chr(c) for c in range(ord("A"), ord("Z") + 1)] + [chr(c) for c in range(ord("a"), ord("z") + 1)] \
        + [str(d) for d in range(10)] + list(PUNCT) + list(ES)
    shapes = []
    for c in chars:
        g = glyph(gdir, c, fonts)
        if g and g[2]:
            data, first, w = g
            shape = []
            for x in range(first, first + w):
                shape.append(tuple(((data[2 * r] >> (7 - x)) & 1) | (((data[2 * r + 1] >> (7 - x)) & 1) << 1)
                                   for r in range(8)))
            shapes.append((c, shape))
    shapes.sort(key=lambda cs: -len(cs[1]))
    empty = (0,) * 8
    out, x, gap = "", 0, 0
    while x < len(cols):
        if cols[x] == empty:
            gap += 1
            x += 1
            continue
        if out and gap > GAP + 1:
            out += " "
        gap = 0
        for c, shape in shapes:
            if tuple(cols[x:x + len(shape)]) == tuple(shape) and \
                    (x + len(shape) >= len(cols) or cols[x + len(shape)] == empty):
                out += c
                x += len(shape)
                break
        else:
            out += "?"
            x += 1
    return out
