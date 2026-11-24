"""mkref.py - rebuild docs/ref/ (greppable local references) from reference/ and tools/gbdk/ (both ignored).

    python -I docs/ref/mkref.py          # rewrite everything it generates
    python -I docs/ref/mkref.py --check  # exit 1 if a generated file would change

Inputs (see docs/ref/README.md for sources and licences):
  reference/pandocs/src/*.md            Pan Docs (mdBook source)       -> docs/ref/pandocs/NN_<page>.md
  reference/gbctr.pdf                   Gekkio's GB CTR (pdftotext)    -> docs/ref/gbctr.txt
  reference/opcodes.json                gbdev opcode table             -> docs/ref/sm83-opcodes.md
  tools/gbdk/include/**/*.h             GBDK-2020 headers (gb target)  -> docs/ref/gbdk/api/<path>.md
  reference/gbdk-src/docs/pages/*.md    GBDK-2020 manual               -> docs/ref/gbdk/manual/*.md
  reference/hugedriver_dl/hUGEDriver    hUGEDriver docs + hardware.inc -> docs/ref/hugedriver/, hardware-inc.md
Deterministic: no dates, LF endings, sorted where order is not the book's.
"""
import json, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "reference"
OUT = ROOT / "docs" / "ref"
GBDK = ROOT / "tools" / "gbdk"
HUGE = REF / "hugedriver_dl" / "hUGEDriver"
FILES = {}   # relative path -> text


def emit(rel, text):
    FILES[rel] = text.replace("\r\n", "\n").rstrip("\n") + "\n"


# ------------------------------------------------------------------ Pan Docs
def bits_table(body):
    """{{#bits 8 > ""  6:"LYC int select" ...; }} -> markdown table (bit | name), one row per field."""
    rows = []
    for line in body.strip().split(";"):
        line = line.strip()
        if not line:
            continue
        m = re.match(r'^"([^"]*)"\s*(.*)$', line)
        reg, rest = (m.group(1), m.group(2)) if m else ("", line)
        fields = re.findall(r'(\d+(?:-\d+)?):"([^"]*)"', rest)
        if fields:
            rows.append((reg, fields))
    out = []
    for reg, fields in rows:
        out.append(f"| {reg or 'Bit'} | " + " | ".join(f for f, _ in fields) + " |")
        out.append("|---|" + "---|" * len(fields))
        out.append("| | " + " | ".join(n for _, n in fields) + " |")
        out.append("")
    return "\n".join(out)


def pandocs():
    src = REF / "pandocs" / "src"
    order = re.findall(r"\]\(\./([^)]+\.md)\)", (src / "SUMMARY.md").read_text(encoding="utf-8"))
    index = ["# Pan Docs (local copy, text only)", "",
             "Converted by `docs/ref/mkref.py` from the mdBook source (gbdev/pandocs, CC0). `{{#bits}}` register",
             "diagrams are tables here; images are not copied (see the online version at https://gbdev.io/pandocs/).", "",
             "| # | Page | File |", "|---|---|---|"]
    for i, name in enumerate(order, 1):
        text = (src / name).read_text(encoding="utf-8")

        def inc(m):
            p = (src / m.group(1).strip()).resolve()
            p = Path(str(p).split(":")[0]) if not p.exists() else p
            return p.read_text(encoding="utf-8") if p.exists() and p.is_file() else f"(include {m.group(1)} not found)"
        text = re.sub(r"\{\{#include\s+([^}]+?)\}\}", inc, text)
        text = re.sub(r"\{\{#bits\s+\d+\s*[<>]?(.*?)\}\}", lambda m: bits_table(m.group(1)), text, flags=re.S)
        text = re.sub(r"<img[^>]*>", "(image: see the online Pan Docs)", text)
        text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"(image: \1)", text)
        stem = Path(name).stem
        fn = f"{i:02d}_{re.sub(r'[^A-Za-z0-9_]+', '_', stem).strip('_')}.md"
        title = re.search(r"^#\s+(.+)$", text, re.M)
        emit(f"pandocs/{fn}", f"<!-- Pan Docs: {name} (gbdev/pandocs, CC0) -->\n" + text)
        index.append(f"| {i} | {title.group(1).strip() if title else stem} | [{fn}]({fn}) |")
    emit("pandocs/README.md", "\n".join(index))


# ------------------------------------------------------------------ GB CTR
def gbctr():
    txt = subprocess.run(["pdftotext", "-enc", "UTF-8", "-layout", str(REF / "gbctr.pdf"), "-"],
                         capture_output=True, check=True).stdout.decode("utf-8", errors="replace")
    txt = "\n".join(l.rstrip() for l in txt.replace("\f", "\n").splitlines())
    emit("gbctr.txt", "Game Boy: Complete Technical Reference (Gekkio), CC BY-SA 4.0.\n"
         "Text extracted with pdftotext -layout by docs/ref/mkref.py from reference/gbctr.pdf.\n"
         "Instruction timings are in M-cycles (1 M = 4 T).\n\n" + re.sub(r"\n{3,}", "\n\n", txt))


# ------------------------------------------------------------------ opcodes
def opcodes():
    d = json.loads((REF / "opcodes.json").read_text(encoding="utf-8"))

    def operand(o):
        n = o["name"]
        if o.get("increment"):
            n += "+"
        if o.get("decrement"):
            n += "-"
        return n if o.get("immediate", True) else f"[{n}]"

    def table(ops, prefix):
        rows = ["| Op | Instruction | Bytes | T-cycles | M-cycles | Z N H C |", "|---|---|---|---|---|---|"]
        for code in sorted(ops, key=lambda k: int(k, 16)):
            o = ops[code]
            ins = o["mnemonic"] + (" " + ", ".join(operand(x) for x in o["operands"]) if o["operands"] else "")
            t = "/".join(str(c) for c in o["cycles"])
            m = "/".join(str(c // 4) for c in o["cycles"])
            f = " ".join(o["flags"][k] for k in "ZNHC")
            rows.append(f"| {prefix}{code[2:].upper()} | `{ins}` | {o['bytes']} | {t} | {m} | {f} |")
        return "\n".join(rows)
    emit("sm83-opcodes.md", "\n".join([
        "# SM83 (Game Boy CPU) opcode table", "",
        "Generated by `docs/ref/mkref.py` from `reference/opcodes.json` (gbdev gb-opcodes, https://gbdev.io/gb-opcodes/).",
        "Mnemonics in RGBDS/Pan Docs syntax: `[HL+]` = `ld a,(hl+)` in sdasgb (GBDK). The sdasgb version with",
        "verified encodings is `.claude/skills/gb-asm/opcodes.md`. Two cycle values = branch taken / not taken.",
        "Flags: `-` unchanged, `0`/`1` forced, letter = set by the result. 1 frame = 70224 T = 17556 M.", "",
        "## Unprefixed", "", table(d["unprefixed"], ""), "",
        "## CB-prefixed", "", table(d["cbprefixed"], "CB "), ""]))


# ------------------------------------------------------------------ GBDK headers
def target_filter(text, target="gb"):
    """Keep only the #if defined(__TARGET_x) branches that apply to `target` (other #ifs are kept as-is)."""
    out, stack = [], []   # stack: [is_target_if, branch_taken, active]
    def active():
        return all(s[2] for s in stack)
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r"#\s*(if|elif)\b(.*)", s)
        if m and "__TARGET_" in m.group(2):
            names = re.findall(r"__TARGET_(\w+)", m.group(2))
            neg = "!" in m.group(2).split("__TARGET_")[0][-3:]
            hit = (target in names) != neg
            if m.group(1) == "if":
                stack.append([True, hit, hit])
            elif stack and stack[-1][0]:
                stack[-1][2] = hit and not stack[-1][1]
                stack[-1][1] |= hit
            continue
        if re.match(r"#\s*if", s):
            stack.append([False, True, True])
        elif re.match(r"#\s*else\b", s) and stack and stack[-1][0]:
            stack[-1][2] = not stack[-1][1]; stack[-1][1] = True
            continue
        elif re.match(r"#\s*endif\b", s) and stack:
            if stack.pop()[0]:
                continue
        if active():
            out.append(line)
    return "\n".join(out)


def gbdk_api():
    inc = GBDK / "include"
    hdrs = sorted(list(inc.glob("*.h")) + list((inc / "gb").glob("*.h")) + list((inc / "gbdk").glob("*.h"))
                  + list((inc / "asm" / "sm83").glob("*.h")))
    index = ["# GBDK-2020 API (headers, gb target)", "",
             f"Generated by `docs/ref/mkref.py` from `tools/gbdk/include` ({version()}): each page lists the functions,",
             "macros and variables of one header with the first line of their doxygen comment, then the header itself",
             "with the other targets' `#if defined(__TARGET_x)` branches removed. Manual: [manual/](manual/).", "",
             "| Header | Functions | What |", "|---|---|---|"]
    for h in hdrs:
        rel = h.relative_to(inc).as_posix()
        text = target_filter(h.read_text(encoding="utf-8", errors="replace"))
        top = re.search(r"/\*\*\s*@file[^\n]*\n(.*?)\*/", text, re.S)
        what = re.sub(r"\s+", " ", top.group(1)).strip()[:110] if top else ""
        items = []
        for m in re.finditer(r"/\*\*(?!<)(.*?)\*/\s*\n((?:[^\n]*\n){1,3})", text, re.S):
            doc, code = m.group(1), m.group(2)
            nm = re.search(r"^\s*(?:#define\s+(\w+)|[\w\s\*]*?\b(\w+)\s*\(|(?:extern\s+)?[\w\s\*]+?\b(\w+)\s*(?:\[.*?\])?\s*;)", code, re.M)
            if not nm or "@file" in doc:
                continue
            name = next(g for g in nm.groups() if g)
            brief = re.sub(r"\s+", " ", re.sub(r"@\w+\s*", "", doc.strip().lstrip("*"))).strip()
            items.append((name, brief.split(". ")[0][:140]))
        lines = [f"# `{rel}` (GBDK-2020, gb target)", "", what, ""]
        if items:
            lines += ["| Name | Summary |", "|---|---|"] + [f"| `{n}` | {b.replace('|', '/')} |" for n, b in items] + [""]
        lines += ["## Header", "", "```c", text.strip(), "```"]
        out = "gbdk/api/" + rel.replace("/", "_").replace(".h", ".md")
        emit(out, "\n".join(lines))
        index.append(f"| [`{rel}`]({out.split('/', 2)[2]}) | {len(items)} | {what.replace('|', '/')} |")
    emit("gbdk/api/README.md", "\n".join(index))
    pages = REF / "gbdk-src" / "docs" / "pages"
    for p in sorted(pages.glob("*.md")):
        emit(f"gbdk/manual/{p.name}", f"<!-- GBDK-2020 manual page {p.name} (gbdk-2020/docs/pages) -->\n"
             + p.read_text(encoding="utf-8", errors="replace"))
    for t in ("asmlnk_manual.txt",):
        if (GBDK / t).exists():
            emit(f"gbdk/{t}", (GBDK / t).read_text(encoding="utf-8", errors="replace"))


def version():
    cl = GBDK / "ChangeLog"
    return cl.read_text(errors="replace").split("\n", 1)[0].strip() if cl.exists() else "unknown version"


# ------------------------------------------------------------------ hardware.inc + hUGEDriver
def hardware_inc():
    hw = (HUGE / "include" / "hardware.inc").read_text(encoding="utf-8", errors="replace")
    gb = target_filter((GBDK / "include" / "gb" / "hardware.h").read_text(encoding="utf-8", errors="replace"))
    alias = dict(re.findall(r"#define\s+(r\w+)\s+(\w+_REG)\b", gb))
    regs = dict(re.findall(r"__(?:REG|BYTE_REG)\s+(\w+);\s*/\*\*<\s*(.*?)\s*\*/", gb))
    rows = ["# hardware.inc names (with GBDK equivalents)", "",
            "From the gbdev `hardware.inc` bundled with hUGEDriver (`reference/hugedriver_dl/hUGEDriver/include/hardware.inc`,",
            "public domain) and GBDK's `gb/hardware.h` (gb target). `rXXX` names exist in both; GBDK C code usually",
            "writes `XXX_REG` (column GBDK). Bit names (`LCDCF_*`, `STATF_*`...) are the hardware.inc ones; GBDK",
            "defines the same `LCDCF_*`/`STATF_*` macros for the gb target. `%` = binary, `$` = hex.", "",
            "| Name | Value | GBDK | Comment |", "|---|---|---|---|"]
    for m in re.finditer(r"^\s*(?:DEF\s+)?(\w+)\s+(?:EQU|=)\s+([^;\n]+?)\s*(?:;\s*(.*))?$", hw, re.M):
        name, val, com = m.group(1), m.group(2).strip(), (m.group(3) or "").strip()
        g = alias.get(name, "")
        if g and regs.get(g):
            com = com or regs[g]
        rows.append(f"| `{name}` | `{val}` | {('`' + g + '`') if g else ''} | {com.replace('|', '/')} |")
    emit("hardware-inc.md", "\n".join(rows))
    emit("hardware.inc", hw)
    for rel in ("README.md", "doc/driver-format.txt", "doc/internals.md", "include/hUGEDriver.h",
                "gbdk_example/README.md"):
        p = HUGE / rel
        if p.exists():
            emit("hugedriver/" + rel.replace("/", "_"), p.read_text(encoding="utf-8", errors="replace"))


def main(argv):
    pandocs(); gbctr(); opcodes(); gbdk_api(); hardware_inc()
    check = "--check" in argv
    changed = []
    for rel, text in sorted(FILES.items()):
        p = OUT / rel
        old = p.read_text(encoding="utf-8") if p.exists() else None
        if old != text:
            changed.append(rel)
            if not check:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text, encoding="utf-8", newline="\n")
    print(f"{len(FILES)} files, {len(changed)} {'out of date' if check else 'written'}")
    return 1 if check and changed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
