#!/usr/bin/env python3
"""apidoc.py - API reference of the gbe engine library (harness/common/src), no external deps.

Adapted from the SNES workspace's tools/scripts/apidoc.py. Reads harness/common/src/gbe.h (one section per
module, headed '// ----...---- gbe_<module>.c[ / .s]'), bcd.h, the top comment of every gbe_*.c / *.s file
and the module table of harness/common/README.md, and writes:

    docs/api/README.md        index: module, what, functions, games that use it
    docs/api/<module>.md      one page per module: what it is, what the game must provide, origin and
                              numbers, a table of every name with its comment, the header section
                              verbatim, the implementation notes of its .c/.s files and the games using it

    python -I harness/scripts/apidoc.py            # regenerate docs/api
    python -I harness/scripts/apidoc.py --check    # exit 1 if docs/api is out of date

Games = tracked games/*/game.json ("common_src"); untracked games are left out. Deterministic: no dates, LF.
"""
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "harness" / "common" / "src"
README = ROOT / "harness" / "common" / "README.md"
OUT = ROOT / "docs" / "api"
EXTRA_FILES = {"gbe_text": ["gbe_log.c"]}   # files whose names are declared in another module's section
SECTION = re.compile(r"^// -{8,}\s+(.+?)\s*$")


def tracked_games():
    try:
        out = subprocess.run(["git", "ls-files", "games/*/game.json"], cwd=ROOT, capture_output=True,
                             text=True, check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        out = [p.relative_to(ROOT).as_posix() for p in ROOT.glob("games/*/game.json")]
    games = {}
    for rel in sorted(out):
        cfg = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        games[Path(rel).parent.name] = set(cfg.get("common_src", []))
    return games


def readme_rows():
    """Files cell -> (what, needs, origin) from the README module table."""
    rows = []
    for line in README.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 4 and line.startswith("| `") or (len(cells) == 4 and line.startswith("|  |")):
            rows.append(cells)
    return rows


def top_comment(path):
    """Leading // or ; comment lines of a source file (the module's own description)."""
    lines = []
    for l in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = l.strip()
        if s.startswith("//") or s.startswith(";"):
            lines.append(re.sub(r"^(//|;+)\s?", "", s))
        elif s == "" and not lines:
            continue
        else:
            break
    return lines


def names_of(code):
    """Public names declared on one header line."""
    s = re.sub(r"//.*", "", code).strip()
    if not s or s.startswith(("#if", "#endif", "#else", "#include", "#pragma")):
        return []
    m = re.match(r"#define\s+(\w+)", s)
    if m:
        return [m.group(1)]
    m = re.match(r"}\s*(\w+)\s*;", s)
    if m:
        return [m.group(1)]
    if "(" in s and not s.startswith("extern"):
        m = re.match(r"[\w\s\*]*?\b(\w+)\s*\(", s)
        return [m.group(1)] if m else []
    m = re.match(r"extern\s+(?:const\s+)?(?:volatile\s+)?(?:unsigned\s+|signed\s+)?\w+\s*\**\s*(.*);", s)
    if m:
        return [re.sub(r"[\[\]\d\s\*]|=.*", "", n) for n in m.group(1).split(",") if n.strip()]
    return []


def parse_header(path):
    """-> intro lines, list of (section title, [lines])"""
    intro, sections, cur = [], [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = SECTION.match(line)
        if m:
            cur = (m.group(1), [])
            sections.append(cur)
        elif cur is not None:
            cur[1].append(line)
        else:
            intro.append(line)
    return intro, sections


def items_of(lines):
    """(name, comment) for every declared name; comment = trailing // or the comment block above."""
    out, above = [], []
    for line in lines:
        s = line.strip()
        if s.startswith("//"):
            above.append(s[2:].strip())
            continue
        trail = s.split("//", 1)[1].strip() if "//" in s else ""
        ns = names_of(s)
        for k, n in enumerate(ns):
            if n and n not in [o[0] for o in out]:
                c = trail or " ".join(above)
                c = c if len(c) <= 200 else c[:197].rsplit(" ", 1)[0] + "..."
                out.append((n, c if k == 0 else f"(ver `{ns[0]}`)" if c else ""))
        if not s or ns:
            above = [] if not s or not s.endswith(",") else above
    return out


def esc(s):
    return s.replace("|", "\\|")


def module_files(title):
    """'gbe_map.c / .s' -> ['gbe_map.c', 'gbe_map.s']"""
    first = title.split()[0]
    stem = first.rsplit(".", 1)[0]
    files = [first] + [stem + ext for ext in re.findall(r"/\s*(\.\w+)", title)]
    files += EXTRA_FILES.get(stem, [])
    return [f for f in files if (SRC / f).exists()]


def render(mod, title, lines, files, row, users):
    items = items_of(lines)
    out = [f"# `{mod}` — {title}", ""]
    if row:
        out += [f"**Qué hace:** {row[1]}", "", f"**Lo que pone el juego:** {row[2] or '-'}", "",
                f"**Origen y cifras:** {row[3] or '-'}", ""]
    out += [f"**Ficheros:** " + ", ".join(f"`harness/common/src/{f}`" for f in files) +
            f" — en game.json: `\"common_src\": [{', '.join(repr(f).replace(chr(39), chr(34)) for f in files)}]`", "",
            "**Juegos que lo usan:** " + (", ".join(f"`games/{g}`" for g in users) or "ninguno todavía"), ""]
    if items:
        out += ["## Nombres", "", "| Nombre | Comentario |", "|---|---|"]
        out += [f"| `{n}` | {esc(c)} |" for n, c in items] + [""]
    body = "\n".join(lines).strip("\n")
    hdr = "bcd.h" if mod == "bcd" else "gbe.h"
    out += [f"## Cabecera (`{hdr}`)", "", "```c", body, "```", ""]
    notes = [(f, top_comment(SRC / f)) for f in files]
    notes = [(f, c) for f, c in notes if c]
    if notes:
        out += ["## Notas de implementación", ""]
        for f, c in notes:
            out += [f"`{f}`:", "", "> " + "\n> ".join(c), ""]
    return "\n".join(out), items


def generate():
    games = tracked_games()
    rows = readme_rows()
    intro, sections = parse_header(SRC / "gbe.h")
    bcd = (SRC / "bcd.h").read_text(encoding="utf-8").splitlines()
    sections = [("bcd.s", [l for l in bcd if not l.startswith("#pragma")])] + sections
    pages, index = {}, []
    for title, lines in sections:
        files = module_files(title)
        if not files:
            continue
        mod = files[0].rsplit(".", 1)[0]
        row = next((r for r in rows if any(f"`{f}`" in r[0] for f in files)), None)
        users = sorted(g for g, used in games.items() if used & set(files))
        text, items = render(mod, title, lines, files, row, users)
        pages[f"{mod}.md"] = text
        what = row[1] if row else next((l[2:].strip() for l in lines if l.startswith("//")), "")
        index.append(f"| [`{mod}`]({mod}.md) | {esc(what)} | {len(items)} | {', '.join(users) or '-'} |")
    head = [l[2:].strip() if l.startswith("//") else "" for l in intro if l.startswith("//")]
    readme = ["# API de gbe (generada)", "",
              "Generado por `python -I harness/scripts/apidoc.py` desde `harness/common/src/gbe.h` (+ `bcd.h`), las",
              "cabeceras de cada `.c`/`.s` y la tabla de `harness/common/README.md`. **No se edita**: se corrige la",
              "fuente y se regenera (`--check` en las pruebas). Qué usar para cada necesidad: `docs/guias/que-usar.md`.", "",
              "> " + "\n> ".join(h for h in head if h), "",
              "| Módulo | Qué hace | Nombres | Juegos que lo usan |", "|---|---|---|---|"] + index + [
              "", "## Uso por juego", "", "| Juego | Módulos |", "|---|---|"]
    for g, used in games.items():
        mods = sorted({f.rsplit(".", 1)[0] for f in used})
        readme.append(f"| `games/{g}` | {', '.join(mods) or '- (sin gbe)'} |")
    pages["README.md"] = "\n".join(readme)
    return {k: v.rstrip("\n") + "\n" for k, v in pages.items()}


def main(argv):
    pages = generate()
    check = "--check" in argv
    stale = []
    for name, text in sorted(pages.items()):
        p = OUT / name
        old = p.read_text(encoding="utf-8").replace("\r\n", "\n") if p.exists() else None
        if old != text:
            stale.append(name)
            if not check:
                OUT.mkdir(parents=True, exist_ok=True)
                p.write_text(text, encoding="utf-8", newline="\n")
    extra = sorted(p.name for p in OUT.glob("*.md") if p.name not in pages) if OUT.exists() else []
    if extra and not check:
        for n in extra:
            (OUT / n).unlink()
    print(f"docs/api: {len(pages)} pages, {len(stale)} {'out of date' if check else 'written'}"
          + (f", {len(extra)} stale: {', '.join(extra)}" if extra else ""))
    return 1 if check and (stale or extra) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
