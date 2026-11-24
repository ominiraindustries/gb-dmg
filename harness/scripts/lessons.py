"""Lessons database (ported from the SNES harness, 2026-11-24): what the harness has been taught, queryable by role/topic and checkable automatically.

Store: docs/datos/lessons.jsonl (one JSON object per line, diffable). Each lesson:
  id, text, evidence, roles [..], topics [..], created, and optionally a `check`:
    {"kind": "forbid",  "glob": "harness/common/src/*.s", "pattern": REGEX, "unless": REGEX?}   pattern must NOT appear
                         (per file; `unless` = file is fine if it also matches this)
    {"kind": "require", "glob": "games/*/game.json", "pattern": REGEX, "if": REGEX?}
                         every matching file (that matches `if`, when given) must contain pattern
    {"kind": "unique",  "glob": "games/*/res/*.lvl", "pattern": REGEX_WITH_GROUP}  group(1) unique per directory
    {"kind": "cmd",     "run": "bash command"}                                        must exit 0
Usage:
  python -I harness/scripts/lessons.py query [--role R] [--topic T] [--text WORD]   # read before working
  python -I harness/scripts/lessons.py check [--id ID] [--paths GLOB...]           # run automatic checks
  python -I harness/scripts/lessons.py add --id ID --text "..." --evidence "..." --roles r1 r2 --topics t1 t2
                                          [--check JSON]
  python -I harness/scripts/lessons.py list
check exits 1 if any lesson is violated (prints file:line + the lesson text).
"""
import argparse, fnmatch, json, pathlib, re, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
DB = ROOT / "docs" / "datos" / "lessons.jsonl"


def load():
    if not DB.exists():
        return []
    return [json.loads(l) for l in DB.read_text(encoding="utf-8").splitlines() if l.strip()]


def save(items):
    tmp = DB.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items), encoding="utf-8")
    tmp.replace(DB)


def files(glob, only=None):
    out = sorted(p for p in ROOT.glob(glob) if p.is_file() and "/build/" not in p.as_posix() and "/games/urbe/" not in p.as_posix())
    if only:
        out = [p for p in out if any(fnmatch.fnmatch(p.relative_to(ROOT).as_posix(), g) for g in only)]
    return out


def run_check(lesson, only=None):
    c = lesson.get("check")
    if not c:
        return None
    bad = []
    if c["kind"] in ("forbid", "require"):
        pat = re.compile(c["pattern"], re.M)
        for f in files(c["glob"], only):
            text = f.read_text(encoding="utf-8", errors="replace")
            rel = f.relative_to(ROOT).as_posix()
            if c["kind"] == "forbid":
                if c.get("unless") and re.search(c["unless"], text, re.M):
                    continue
                for m in pat.finditer(text):
                    bad.append(f"{rel}:{text.count(chr(10), 0, m.start()) + 1}: {m.group(0).strip()[:60]}")
            else:
                if c.get("if") and not re.search(c["if"], text, re.M):
                    continue
                if not pat.search(text):
                    bad.append(f"{rel}: missing /{c['pattern']}/")
    elif c["kind"] == "unique":   # first capture group of pattern must not repeat within one directory
        seen = {}
        for f in files(c["glob"], only):
            for m in re.finditer(c["pattern"], f.read_text(encoding="utf-8", errors="replace"), re.M):
                val = next((g for g in m.groups() if g), m.group(0)); key = (f.parent, val)
                if key in seen and seen[key] != f:
                    bad.append(f"{f.relative_to(ROOT).as_posix()} and {seen[key].name}: both use {val!r}")
                seen.setdefault(key, f)
    elif c["kind"] == "cmd":
        p = subprocess.run(["bash", "-c", c["run"]], cwd=ROOT, capture_output=True, text=True)
        if p.returncode:
            bad.append(f"`{c['run']}` -> exit {p.returncode}: {(p.stdout + p.stderr).strip()[:120]}")
    return bad


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("query"); q.add_argument("--role"); q.add_argument("--topic"); q.add_argument("--text")
    c = sub.add_parser("check"); c.add_argument("--id"); c.add_argument("--paths", nargs="*")
    a = sub.add_parser("add")
    a.add_argument("--id", required=True); a.add_argument("--text", required=True); a.add_argument("--evidence", required=True)
    a.add_argument("--roles", nargs="+", default=["all"]); a.add_argument("--topics", nargs="+", default=[])
    a.add_argument("--check", help="JSON check object")
    sub.add_parser("list")
    args = ap.parse_args()
    items = load()

    if args.cmd == "add":
        if any(i["id"] == args.id for i in items):
            sys.exit(f"lesson {args.id} exists")
        item = {"id": args.id, "text": args.text, "evidence": args.evidence, "roles": [r for x in args.roles for r in x.split(",") if r],
                "topics": [t for x in args.topics for t in x.split(",") if t], "created": time.strftime("%Y-%m-%d")}
        if args.check:
            item["check"] = json.loads(args.check)
            bad = run_check(item)
            print(f"check currently finds {len(bad)} violation(s)")
            for b in bad[:10]:
                print("  ", b)
        items.append(item); save(items); print("added", args.id); return

    if args.cmd in ("query", "list"):
        for i in items:
            if args.cmd == "query":
                if args.role and args.role not in i["roles"] and "all" not in i["roles"]:
                    continue
                if args.topic and args.topic not in i["topics"]:
                    continue
                if args.text and args.text.lower() not in (i["text"] + " ".join(i["topics"])).lower():
                    continue
            tag = " [auto-check]" if i.get("check") else ""
            print(f"- {i['id']}{tag}: {i['text']}\n    evidence: {i['evidence']}")
        return

    # check
    nbad = 0
    for i in items:
        if args.id and i["id"] != args.id:
            continue
        bad = run_check(i, args.paths)
        if bad:
            nbad += 1
            print(f"VIOLATED {i['id']}: {i['text']}")
            for b in bad[:20]:
                print("   ", b)
    print("lessons: all checks pass" if not nbad else f"lessons: {nbad} lesson(s) violated")
    sys.exit(1 if nbad else 0)


if __name__ == "__main__":
    main()
