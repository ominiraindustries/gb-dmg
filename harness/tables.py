"""Data tables: res/data/<name>.tbl -> build/gen/tbl_<name>.c/.h (array of structs in a bank) and a
Python loader for tests and bots. All balance numbers live here, never in C (games/faro GDD 2.0).

    ; comment
    @ table items                         C names: <name>_t, tbl_<name>[], <NAME>_COUNT, ids <PREFIX>_<ID>
    @ prefix ITEM                         id prefix (default: the table name in capitals)
    @ col name   text 14                  fixed-size zero-padded text (no accents / n-tilde)
    @ col cat    enum FOOD TOOL KEY       enum: CAT_FOOD... ids by order (prefix = column name)
    @ col price  u16
    @ col heal   u8
    @ col bonus  s8
    @ col ability flags CUT LIGHT FISH    bitmask, '-' = none, several joined with '+': CUT+LIGHT
    @ col perece bool                     0/1, yes/no
    @ col drop   ref items                id of a row of another table (or this one); '-' = 0xFF
    POCION   "Pocion"   FOOD   40  20  0  -  no  -
    SAL      "Sal"      FOOD    5   0  0  -  no  -

A row: ID then one value per column (text in quotes). The C struct has the columns in order
(text n -> char[n + 1]); code copies one row to WRAM with bank_memcpy(BANK(tbl_items), &r,
&tbl_items[id], sizeof r). Enum/flag names become #defines in the header so code can test
roles without content ids (ability & ITEMS_ABILITY_CUT: <TABLE>_<COLUMN>_<NAME>; the build stops on
any clash - moves and skills both had EFECTO_ESTADO, and items' id CEBO_DULCE met column cebo's
DULCE), and every table gets
#define <PREFIX>_<ID> id for the content side (scripts, maps).
"""
import re
from pathlib import Path

TEXT_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 !?:-./,'¡¿{}")   # {S} {O} {N}: placeholders the code fills
SIZES = {"u8": 1, "s8": 1, "u16": 2, "bool": 1, "ref": 1}


class Table:
    def __init__(self, name, prefix, cols, rows, path):
        self.name, self.prefix, self.cols, self.rows, self.path = name, prefix, cols, rows, Path(path)
        self.ids = {r["id"]: i for i, r in enumerate(rows)}

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, key):
        return self.rows[self.ids[key] if isinstance(key, str) else key]


def _cols(spec, where):
    p = spec.split()
    name, kind = p[0], p[1]
    col = {"name": name, "kind": kind}
    if kind == "text":
        col["size"] = int(p[2])
    elif kind in ("enum", "flags"):
        col["values"] = p[2:]
        if kind == "flags" and len(col["values"]) > 16:
            raise ValueError(f"{where}: flags column {name} has more than 16 names")
    elif kind == "ref":
        col["table"] = p[2]
    elif kind not in SIZES:
        raise ValueError(f"{where}: unknown column type '{kind}'")
    return col


def parse(path):
    path = Path(path)
    name, prefix, cols, rows = path.stem, None, [], []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = _strip(raw)
        if not line:
            continue
        where = f"{path}:{n}"
        if line.startswith("@"):
            p = line.split(None, 2)
            key = p[1].lower()
            if key == "table":
                name = p[2].strip()
            elif key == "prefix":
                prefix = p[2].strip()
            elif key == "col":
                cols.append(_cols(p[2], where))
            else:
                raise ValueError(f"{where}: unknown '@ {key}'")
            continue
        toks = re.findall(r'"[^"]*"|\S+', line)
        if len(toks) != len(cols) + 1:
            raise ValueError(f"{where}: {len(toks) - 1} values for {len(cols)} columns")
        row = {"id": toks[0].upper(), "_where": where}
        for c, t in zip(cols, toks[1:]):
            row[c["name"]] = _value(c, t, where)
        rows.append(row)
    ids = [r["id"] for r in rows]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise ValueError(f"{path}: ids repeated: {sorted(dup)}")
    if len(rows) > 255:
        raise ValueError(f"{path}: {len(rows)} rows, max 255 (ids are u8, 0xFF = none)")
    return Table(name, (prefix or name).upper(), cols, rows, path)


def _strip(raw):
    out, q = "", False
    for ch in raw:
        if ch == '"':
            q = not q
        if ch == ";" and not q:
            break
        out += ch
    return out.strip()


def _value(c, t, where):
    k = c["kind"]
    if k == "text":
        if not (t.startswith('"') and t.endswith('"')):
            raise ValueError(f"{where}: column {c['name']} wants \"text\"")
        s = t[1:-1]
        if len(s) > c["size"]:
            raise ValueError(f"{where}: '{s}' longer than {c['size']} ({c['name']})")
        bad = [ch for ch in s if ch not in TEXT_CHARS]
        if bad:
            raise ValueError(f"{where}: {bad} not in the font (no accents or n-tilde)")
        return s
    if k == "enum":
        if t.upper() not in c["values"]:
            raise ValueError(f"{where}: '{t}' not one of {c['values']} ({c['name']})")
        return c["values"].index(t.upper())
    if k == "flags":
        if t == "-":
            return 0
        v = 0
        for part in t.upper().split("+"):
            if part not in c["values"]:
                raise ValueError(f"{where}: '{part}' not one of {c['values']} ({c['name']})")
            v |= 1 << c["values"].index(part)
        return v
    if k == "bool":
        if t.lower() in ("1", "yes", "si", "true"):
            return 1
        if t.lower() in ("0", "no", "false", "-"):
            return 0
        raise ValueError(f"{where}: '{t}' is not a bool")
    if k == "ref":
        return None if t == "-" else t.upper()    # resolved against the other table later
    v = int(t, 0)
    lo, hi = {"u8": (0, 255), "s8": (-128, 127), "u16": (0, 65535)}[k]
    if not lo <= v <= hi:
        raise ValueError(f"{where}: {v} out of range for {k} ({c['name']})")
    return v


def load_all(folder):
    """{table name: Table} with refs resolved to ids (None = 0xFF)."""
    tables = {}
    for p in sorted(Path(folder).glob("*.tbl")):
        t = parse(p)
        tables[t.name] = t
    for t in tables.values():
        for c in t.cols:
            if c["kind"] != "ref":
                continue
            if c["table"] not in tables:
                raise ValueError(f"{t.path}: column {c['name']} refers to unknown table '{c['table']}'")
            other = tables[c["table"]]
            for r in t.rows:
                v = r[c["name"]]
                if v is not None:
                    if v not in other.ids:
                        raise ValueError(f"{r['_where']}: '{v}' is not an id of {other.name}")
                    r[c["name"]] = other.ids[v]
    return tables


def symbols(tables):
    """{<PREFIX>_<ID>: id} of every table (for scripts and maps)."""
    out = {}
    for t in tables.values():
        for i, r in enumerate(t.rows):
            out[f"{t.prefix}_{r['id']}"] = i
    return out


def _ctype(c):
    return {"u8": "uint8_t", "s8": "int8_t", "u16": "uint16_t", "bool": "uint8_t", "ref": "uint8_t",
            "enum": "uint8_t"}.get(c["kind"], "uint16_t" if c["kind"] == "flags" and len(c["values"]) > 8 else "uint8_t")


def _cval(c, v):
    if c["kind"] == "text":
        return '"' + v.replace("¡", "\\xa1").replace("¿", "\\xbf") + '"'
    if c["kind"] == "ref":
        return "0xFF" if v is None else str(v)
    return str(v)


def convert(folder, out_dir):
    """Every res/data/*.tbl -> tbl_<name>.c/.h (banked). Returns the .c files."""
    tables = load_all(folder)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    outs, seen = [], {}
    for t in tables.values():
        sym = f"tbl_{t.name}"
        fields = "".join(f"    char {c['name']}[{c['size'] + 1}];\n" if c["kind"] == "text"
                         else f"    {_ctype(c)} {c['name']};\n" for c in t.cols)
        defs = [f"#define {t.prefix}_{r['id']} {i}" for i, r in enumerate(t.rows)]
        defs.append(f"#define {t.prefix}_COUNT {len(t.rows)}")
        tn = t.name.upper()                         # column values: <TABLE>_<COLUMN>_<VALUE>
        for c in t.cols:
            if c["kind"] == "enum":
                defs += [f"#define {tn}_{c['name'].upper()}_{v} {i}" for i, v in enumerate(c["values"])]
                defs.append(f"#define {tn}_{c['name'].upper()}_COUNT {len(c['values'])}")   # array sizes
            elif c["kind"] == "flags":
                defs += [f"#define {tn}_{c['name'].upper()}_{v} 0x{1 << i:X}" for i, v in enumerate(c["values"])]
        for d in defs:                              # a clash would silently redefine a value
            name = d.split()[1]
            if name in seen and seen[name] != t.name:
                raise ValueError(f"{t.path}: #define {name} also comes from table {seen[name]}: rename the id, "
                                 "the column or the value (or use a different @ prefix)")
            if name in seen and d not in defs[:defs.index(d)]:
                raise ValueError(f"{t.path}: #define {name} defined twice in this table (id vs column value?)")
            seen[name] = t.name
        (out_dir / f"{sym}.h").write_text(
            f"// Generated from {t.path.name} by harness/tables.py - do not edit\n#pragma once\n"
            f"#include <gb/gb.h>\n#include <stdint.h>\n\n" + "\n".join(dict.fromkeys(defs)) + "\n\n"
            f"typedef struct {{\n{fields}}} {t.name}_t;\n\nextern const {t.name}_t {sym}[];\nBANKREF_EXTERN({sym})\n",
            encoding="utf-8")
        rows = "\n".join("    { " + ", ".join(_cval(c, r[c["name"]]) for c in t.cols) + f" }},   // {i} {r['id']}"
                         for i, r in enumerate(t.rows))
        (out_dir / f"{sym}.c").write_text(
            f"// Generated from {t.path.name} by harness/tables.py - do not edit\n#pragma bank 255\n"
            f'#include "{sym}.h"\n\nconst {t.name}_t {sym}[{max(1, len(t.rows))}] = {{\n{rows}\n}};\n\nBANKREF({sym})\n',
            encoding="utf-8")
        outs.append(out_dir / f"{sym}.c")
    return outs, tables
