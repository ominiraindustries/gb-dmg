"""Generate .claude/skills/gb-asm/opcodes.md from reference/opcodes.json (gbdev opcode table).

Usage:
    python harness/scripts/gen_opcodes.py           write opcodes.md
    python harness/scripts/gen_opcodes.py --check   also assemble every listed form with GBDK's
                                                    sdasgb and verify it encodes to the listed opcode

Instructions are written in sdasgb syntax (the GBDK assembler), not RGBDS syntax.
"""
import json
import re
import subprocess
import sys
import tempfile
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "reference" / "opcodes.json"
DST = ROOT / ".claude" / "skills" / "gb-asm" / "opcodes.md"
SDASGB = ROOT / "tools" / "gbdk" / "bin" / "sdasgb.exe"

R8 = {"A", "B", "C", "D", "E", "H", "L"}
CONDS = {"NZ", "Z", "NC", "C"}
ALU = {"ADD", "ADC", "SUB", "SBC", "AND", "XOR", "OR", "CP"}
BRANCH = {"JP", "JR", "CALL", "RET"}

GROUPS = [
    ("8-bit loads", lambda m, ops: m == "LDH" or (m == "LD" and not is16(ops))),
    ("16-bit loads and stack", lambda m, ops: m in ("PUSH", "POP") or (m == "LD" and is16(ops))),
    ("8-bit arithmetic and logic", lambda m, ops: (m in ALU and not is16(ops))
        or (m in ("INC", "DEC") and not is16(ops)) or m in ("DAA", "CPL", "SCF", "CCF")),
    ("16-bit arithmetic", lambda m, ops: m in ("ADD", "INC", "DEC") and is16(ops)),
    ("Rotates on A (unprefixed, Z always 0)", lambda m, ops: m in ("RLCA", "RRCA", "RLA", "RRA")),
    ("Jumps, calls, returns", lambda m, ops: m in BRANCH or m in ("RETI", "RST")),
    ("Control", lambda m, ops: m in ("NOP", "HALT", "STOP", "DI", "EI", "PREFIX")),
]


def is16(ops):
    names = [o["name"] for o in ops]
    if any(o["name"] in ("BC", "DE") and o.get("immediate", True) for o in ops):
        return True
    if any(n in ("SP", "n16", "AF") for n in names):
        return True
    if "HL" in names:
        # HL used as a pointer [(hl), (hl+), (hl-)] is an 8-bit access
        return any(o["name"] == "HL" and o.get("immediate", True)
                   and not o.get("increment") and not o.get("decrement") for o in ops)
    return False


def operand(m, o, idx, ops):
    """One operand in sdasgb syntax."""
    n, imm = o["name"], o.get("immediate", True)
    if m in BRANCH and n in CONDS and idx == 0 and len(ops) > 1 or (m == "RET" and n in CONDS):
        return n.lower()
    if n == "HL" and o.get("increment"):
        return "(hl+)"
    if n == "HL" and o.get("decrement"):
        return "(hl-)"
    if n.startswith("$"):
        return "0x" + n[1:]
    if n in ("n8", "n16"):
        return "#" + n
    if n == "e8":
        return "label" if m == "JR" else "#e8"
    if n == "a16" and imm:
        return "label"
    if n in ("a16", "a8"):
        return f"({n})"
    s = n.lower()
    return s if imm else f"({s})"


def render(m, ops):
    if m == "LD" and len(ops) == 3:          # F8: LD HL, SP+e8
        return "ldhl sp, #e8"
    if m == "JP" and len(ops) == 1 and ops[0]["name"] == "HL":
        return "jp (hl)"
    if m == "STOP":
        return "stop"
    if m == "PREFIX":
        return "(CB prefix byte)"
    args = [operand(m, o, i, ops) for i, o in enumerate(ops)]
    return m.lower() + (" " + ", ".join(args) if args else "")


def generic(m, ops):
    """Pattern with variable 8-bit registers replaced by r (operand 0 of ALU ops stays 'a')."""
    out = []
    for i, o in enumerate(ops):
        var = (m in ALU or m in ("LD", "INC", "DEC")) and o["name"] in R8             and o.get("immediate", True) and not (m in ALU and i == 0)
        out.append("r" if var else None)
    return out


def flags(f):
    return " ".join(f[k] for k in "ZNHC")


def cycles(c):
    return str(c[0]) if len(c) == 1 else f"{c[0]}/{c[1]}"


def collapse(entries):
    """Merge rows that differ only by an r8 register (ld r, r / inc r / add a, r ...)."""
    rows = OrderedDict()
    for code, op in entries:
        m, ops = op["mnemonic"], op["operands"]
        pat = generic(m, ops)
        if m == "RST":
            text = "rst n"
        elif "r" in pat:
            parts = [("r" if pat[i] else operand(m, o, i, ops)) for i, o in enumerate(ops)]
            text = m.lower() + " " + ", ".join(parts)
        else:
            text = render(m, ops)
        key = (text, op["bytes"], tuple(op["cycles"]), flags(op["flags"]))
        rows.setdefault(key, []).append(code)
    out = []
    by_code = dict(entries)
    for (text, nbytes, cyc, fl), codes in rows.items():
        if len(codes) == 1:
            oc = f"{codes[0]:02X}"
            op = by_code[codes[0]]
            text = render(op["mnemonic"], op["operands"])
        elif text == "rst n":
            text = "rst n"   # n = 0x00, 0x08, ... 0x38; opcode = 0xC7 + n
            oc = f"C7 + n ({len(codes)})"
        else:
            oc = f"{min(codes):02X}..{max(codes):02X} ({len(codes)})"
        out.append((text, oc, nbytes, cycles(cyc), fl, codes))
    return sorted(out, key=lambda r: (r[0].split()[0], r[5][0]))


def all_forms(entries):
    """(asm text, opcode) for every single opcode, for the --check self test."""
    for code, op in entries:
        m, ops = op["mnemonic"], op["operands"]
        if m in ("PREFIX",) or m.startswith("ILLEGAL"):
            continue
        yield render(m, ops), [code]


def cb_table(cb):
    ops = OrderedDict()
    for k, op in cb.items():
        code = int(k, 16)
        m = op["mnemonic"]
        o = op["operands"]
        is_bit = m in ("BIT", "RES", "SET")
        target = o[-1]
        kind = "(hl)" if (target["name"] == "HL" and not target.get("immediate", True)) else "r"
        ent = ops.setdefault(m, {"r": set(), "(hl)": set(), "flags": set(), "bytes": set(), "codes": []})
        ent[kind].add(tuple(op["cycles"]))
        ent["flags"].add(flags(op["flags"]))
        ent["bytes"].add(op["bytes"])
        ent["codes"].append(code)
        ent["bit"] = is_bit
    rows = []
    for m, e in ops.items():
        for key in ("r", "(hl)", "flags", "bytes"):
            assert len(e[key]) == 1, f"CB {m}: non-uniform {key}: {e[key]}"
        form = f"{m.lower()} n, r" if e["bit"] else f"{m.lower()} r"
        rows.append((form, f"{min(e['codes']):02X}..{max(e['codes']):02X}", e["bytes"].pop(),
                     cycles(e["r"].pop()), cycles(e["(hl)"].pop()), e["flags"].pop()))
    return rows


def cb_forms(cb):
    for k, op in cb.items():
        m, o = op["mnemonic"], op["operands"]
        args = []
        for x in o:
            n = x["name"]
            if n.isdigit():
                args.append(n)
            elif n == "HL":
                args.append("(hl)")
            else:
                args.append(n.lower())
        yield f"{m.lower()} {', '.join(args)}", [0xCB, int(k, 16)]


def generate(data):
    un = sorted(((int(k, 16), v) for k, v in data["unprefixed"].items()), key=lambda t: t[0])
    lines = [
        "# SM83 opcode table (generated)",
        "",
        "<!-- GENERATED by harness/scripts/gen_opcodes.py from reference/opcodes.json. Do not edit. -->",
        "",
        "- Syntax is **sdasgb** (GBDK): `#` before immediates, `(x)` for memory, `ldh`, `(hl+)`/`(hl-)`,",
        "  `ldhl sp, #e8`, `jp (hl)`. Every form below was assembled with sdasgb and checked against",
        "  its opcode (`gen_opcodes.py --check`).",
        "- **cycles** are T-states (4.194304 MHz clock; 1 M-cycle = 4 T). `a/b` = branch taken / not taken.",
        "- **flags Z N H C**: `-` unchanged, `0`/`1` forced, letter = set according to the result.",
        "- `r` = any of a b c d e h l; `rst n`: n = 0x00, 0x08 .. 0x38.",
        "- `#n8`/`#n16` immediate, `(a16)` absolute address,",
        "  `(a8)` = address 0xFF00+a8 (sdasgb also accepts the full 0xFFxx address or an HRAM symbol),",
        "  `label` = jump target (JR range is -128..+127 from the next instruction), `#e8` signed byte.",
        "",
    ]
    used = set()
    for title, pred in GROUPS:
        group = [(c, op) for c, op in un if c not in used and pred(op["mnemonic"], op["operands"])]
        used.update(c for c, _ in group)
        lines += [f"## {title}", "", "| instruction | opcode | bytes | cycles | Z N H C |",
                  "|---|---|---|---|---|"]
        for text, oc, nb, cyc, fl, _ in collapse(group):
            lines.append(f"| `{text}` | {oc} | {nb} | {cyc} | {fl} |")
        lines.append("")
    rest = [c for c, op in un if c not in used]
    illegal = [c for c in rest if data["unprefixed"][f"0x{c:02X}"]["mnemonic"].startswith("ILLEGAL")]
    unknown = [c for c in rest if c not in illegal]
    assert not unknown, f"ungrouped opcodes: {[hex(c) for c in unknown]}"
    lines += ["## Illegal opcodes (lock up the CPU)", "",
              ", ".join(f"{c:02X}" for c in illegal), ""]
    lines += [
        "## CB-prefixed (2 bytes: CB xx)", "",
        "Regular encoding: `xx = op*8 + reg` with reg order b c d e h l (hl) a (0..7); for bit ops",
        "`xx = base + bit*8 + reg`. `(hl)` forms are slower.", "",
        "| instruction | CB xx | bytes | cycles r | cycles (hl) | Z N H C |",
        "|---|---|---|---|---|---|",
    ]
    for form, rng, nb, cr, ch, fl in cb_table(data["cbprefixed"]):
        lines.append(f"| `{form}` | {rng} | {nb} | {cr} | {ch} | {fl} |")
    lines += ["",
              "Note: `swap r` (CB 30..37) replaces the Z80's SLL. `bit` sets Z when the tested bit is 0.",
              ""]
    return "\n".join(lines)


def check(data):
    """Assemble every form with sdasgb, compare listing bytes with the opcode."""
    un = sorted(((int(k, 16), v) for k, v in data["unprefixed"].items()), key=lambda t: t[0])
    forms = list(all_forms(un)) + list(cb_forms(data["cbprefixed"]))
    subst = {"#n8": "#0x12", "#n16": "#0x1234", "(a16)": "(0xC123)", "(a8)": "(0x80)",
             "#e8": "#2", "label": "lbl"}
    src = ["\t.module chk", "\t.area CHK (ABS)", "\t.org 0x100", "lbl:"]
    for text, _ in forms:
        for k, v in subst.items():
            text = text.replace(k, v)
        src.append("\t" + text)
    with tempfile.TemporaryDirectory() as td:
        s = Path(td) / "chk.s"
        s.write_text("\n".join(src) + "\n")
        res = subprocess.run([str(SDASGB), "-plosgff", str(s)], capture_output=True, text=True, cwd=td)
        if res.returncode != 0:
            print(res.stdout + res.stderr)
            sys.exit("sdasgb failed")
        lst = (Path(td) / "chk.lst").read_text().splitlines()
    got = []
    for line in lst:
        mm = re.match(r"\s+[0-9A-F]{8} ((?:[0-9A-F]{2}[ rs]?)+)\s+\[", line)
        if mm:
            got.append([int(b, 16) for b in re.findall(r"[0-9A-F]{2}", mm.group(1))])
    assert len(got) == len(forms), f"listing has {len(got)} instructions, expected {len(forms)}"
    bad = [(t, exp, g) for (t, exp), g in zip(forms, got) if g[:len(exp)] != exp]
    for t, exp, g in bad:
        print(f"MISMATCH {t}: expected {exp} got {g}")
    if bad:
        sys.exit(1)
    print(f"check OK: {len(forms)} forms assemble to their opcodes")


def main():
    data = json.loads(SRC.read_text())
    if "--check" in sys.argv:
        check(data)
    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text(generate(data), encoding="utf-8")
    print(f"wrote {DST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
