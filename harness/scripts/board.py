"""Agent coordination board: who owns which paths, and dependency conflicts between them
(ported from the SNES harness, 2026-11-24).

The coordinator runs this BEFORE launching an agent. It catches two kinds of clashes:
  1. direct: two active claims own overlapping paths;
  2. dependency: one claim modifies a gbe module (harness/common/src/gbe_<m>.c/.s, or the module written as
     `gbe/<m>`) while another claim owns a game whose game.json lists that module in "common_src", or a harness
     file every build or test runs (harness/gb.py, harness/gbtest.py, gbe.h, conftest.py ...).
     (SNES lesson 2026-10-17: measuring a game on a module another agent was rewriting.)

Usage:
  python -I harness/scripts/board.py check  --owns PATH [PATH...] [--uses MOD...]   # what would conflict?
  python -I harness/scripts/board.py claim  NAME --bead ID --task "..." --owns PATH... [--uses MOD...] [--force]
  python -I harness/scripts/board.py release NAME [--remove-worktree [--worktree WT] [--into BRANCH] [--force-untracked]]
  python -I harness/scripts/board.py list
  python -I harness/scripts/board.py busy      # games that must not be built/tested right now
  python -I harness/scripts/board.py doctor    # stale claims and orphan/dirty worktrees (read-only)
Paths are repo-relative (games/faro, harness/common/src/gbe_vq.c, harness/screens.py); a path owns everything
under it, and the module path `gbe/vq` covers harness/common/src/gbe_vq.c and gbe_vq.s.
`--uses` names gbe modules (vq, world, ...) or `*` for the whole harness.
State: .claude/board.json (one board for the main checkout and every worktree). claim needs a Beads task in
confirmed (it is claimed here) or in_progress. release --remove-worktree then runs `worktree.py remove`.
"""
import argparse, datetime, json, pathlib, re, subprocess, sys, time

def _main_checkout():
    """The main checkout, also when board.py runs from a worktree: one board for every agent."""
    here = pathlib.Path(__file__).resolve().parents[2]
    p = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=here,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return pathlib.Path(p.stdout.strip()).resolve().parent if p.returncode == 0 and p.stdout.strip() else here


ROOT = _main_checkout()
BOARD = ROOT / ".claude" / "board.json"
BEADS = ROOT / "harness" / "scripts" / "beads.py"
GBE_SRC = ROOT / "harness" / "common" / "src"
WORKTREE = pathlib.Path(__file__).resolve().parent / "worktree.py"
# harness files that every game build / test runs: owning them affects every game ("*") or one module's users
TOOL_MODULES = {"harness/gb.py": "*", "harness/gbtest.py": "*", "conftest.py": "*", "pytest.ini": "*",
                "harness/common/src/gbe.h": "*", "harness/vramcheck.py": "*", "harness/templates": "*",
                "harness/screens.py": "screen", "harness/world.py": "world", "harness/levels.py": "map",
                "harness/metatiles.py": "map", "harness/vwf.py": "vwf", "harness/script.py": "script",
                "harness/tables.py": "*", "harness/common/font.tiles": "*"}


def load():
    return json.loads(BOARD.read_text(encoding="utf-8")) if BOARD.exists() else {}


def save(b):
    BOARD.parent.mkdir(exist_ok=True)
    tmp = BOARD.with_suffix(".tmp")
    tmp.write_text(json.dumps(b, indent=1), encoding="utf-8")
    tmp.replace(BOARD)


def bead_command(*args):
    return subprocess.run(
        [sys.executable, "-I", str(BEADS), *args], cwd=ROOT, capture_output=True,
        text=True, encoding="utf-8", errors="replace"
    )


def bead(issue_id):
    proc = bead_command("show", issue_id, "--json")
    if proc.returncode:
        sys.stderr.write(proc.stderr or proc.stdout)
        sys.exit(f"cannot read Beads task {issue_id}")
    try:
        rows = json.loads(proc.stdout)
        return rows[0]
    except (json.JSONDecodeError, IndexError, TypeError):
        sys.exit(f"invalid response for Beads task {issue_id}")


def norm(p):
    return p.replace("\\", "/").strip("/")


def gbe_modules():
    """The gbe modules: harness/common/src/gbe_<m>.c / .s -> {m}."""
    out = set()
    for p in GBE_SRC.glob("gbe_*.*") if GBE_SRC.exists() else []:
        if p.suffix in (".c", ".s"):
            out.add(p.stem[4:].removesuffix("_asm"))
    return out


def module_of(path):
    """The gbe module a path belongs to, or None."""
    p = norm(path)
    m = re.match(r"(?:gbe/|harness/common/src/gbe_)([a-z0-9_]+?)(?:_asm)?(?:\.[a-z]+)?$", p)
    if m and m.group(1) in gbe_modules():
        return m.group(1)
    return None


def overlaps(a, b):
    a, b = norm(a), norm(b)
    ma, mb = module_of(a), module_of(b)
    if ma and ma == mb:
        return True
    # games/faro also matches games/faro/src/main.c ...
    def covers(x, y):
        return y == x or y.startswith(x + "/") or y.startswith(x + ".")
    return covers(a, b) or covers(b, a)


def project_modules(proj):
    """gbe modules a game uses: its game.json "common_src" (gbe_vq.c, gbe_vq.s -> vq)."""
    gj = ROOT / norm(proj) / "game.json"
    if not gj.exists():
        return set()
    try:
        data = json.loads(gj.read_text(encoding="utf-8"))
    except ValueError:
        return set()
    mods = set()
    for f in data.get("common_src", []):
        m = re.match(r"gbe_([a-z0-9_]+?)(?:_asm)?\.[cs]$", f)
        if m:
            mods.add(m.group(1))
    return mods


def affected_modules(path):
    p = norm(path)
    m = module_of(p)
    if m:
        return {m}
    for tool, mod in TOOL_MODULES.items():
        if overlaps(tool, p):
            return {mod}
    return set()


def conflicts(owns, board, me=None, uses=()):
    out = []
    for name, c in board.items():
        if name == me:
            continue
        for a in owns:
            for b in c["owns"]:
                if overlaps(a, b):
                    out.append(f"DIRECT: {a} overlaps {b} (claimed by {name}: {c['task']})")
        # declared future dependencies (--uses): a project being ported to a module doesn't list it yet
        for mine_uses, their_owns, who in ((set(uses), c["owns"], name), (set(c.get("uses", [])), owns, None)):
            for q in their_owns:
                for mod in affected_modules(q):
                    if mod in mine_uses or mod == "*":
                        out.append(f"DEPENDENCY: {'you declared --uses' if who else name + ' declared --uses'} {mod} "
                                   f"while {(name + ' modifies ') if who else 'you modify '}{q}")
        # dependency both ways (from the projects' Makefiles)
        for mine, theirs, who in ((owns, c["owns"], name), (c["owns"], owns, None)):
            for p in mine:
                for mod in affected_modules(p):
                    for q in theirs:
                        if norm(q).startswith("games/"):
                            deps = project_modules(q)
                            if mod == "*" or mod in deps:
                                side = f"you modify {p}" if who else f"{name} modifies {p}"
                                tgt = f"{name}'s {q}" if who else f"your {q}"
                                out.append(f"DEPENDENCY: {side} (module {mod}) while {tgt} uses it")
    return sorted(set(out))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("--owns", nargs="+", required=True)
    c.add_argument("--uses", nargs="*", default=[], help="gbe modules the work will depend on")
    cl = sub.add_parser("claim"); cl.add_argument("name"); cl.add_argument("--bead", required=True)
    cl.add_argument("--task", required=True)
    cl.add_argument("--owns", nargs="+", required=True); cl.add_argument("--force", action="store_true")
    cl.add_argument("--uses", nargs="*", default=[], help="gbe modules the work will depend on")
    r = sub.add_parser("release"); r.add_argument("name")
    r.add_argument("--remove-worktree", action="store_true", help="then worktree.py remove the agent's worktree")
    r.add_argument("--worktree", help="worktree name when it differs from the claim name")
    r.add_argument("--into", help="merge target for the worktree check (default: its base branch)")
    r.add_argument("--force-untracked", action="store_true")
    sub.add_parser("list")
    sub.add_parser("busy", help="games that must not be built/tested now (claimed, or using a module being modified)")
    d = sub.add_parser("doctor", help="report stale claims and worktree hygiene; never deletes")
    d.add_argument("--stale-hours", type=int, default=24)
    a = ap.parse_args()
    b = load()
    if a.cmd == "doctor":
        problems = []
        now = datetime.datetime.now()
        for name, c in b.items():
            try:
                age = (now - datetime.datetime.strptime(c["since"], "%Y-%m-%d %H:%M")).total_seconds() / 3600
                if age > a.stale_hours:
                    problems.append(f"STALE CLAIM {name}: {age:.0f} h, {c['task']}")
            except (KeyError, ValueError):
                problems.append(f"BAD CLAIM {name}: invalid or missing 'since'")
            issue_id = c.get("bead")
            if not issue_id:
                problems.append(f"UNTRACKED CLAIM {name}: missing Beads task ID")
            else:
                proc = bead_command("show", issue_id, "--json")
                if proc.returncode:
                    problems.append(f"BAD BEAD {name}: cannot read {issue_id}")
                else:
                    try:
                        state = json.loads(proc.stdout)[0]["status"]
                        if state in ("resolved", "closed"):
                            problems.append(f"STALE CLAIM {name}: Beads task {issue_id} is {state}")
                    except (json.JSONDecodeError, IndexError, KeyError, TypeError):
                        problems.append(f"BAD BEAD {name}: invalid response for {issue_id}")
        wtroot = ROOT / ".claude" / "worktrees"
        dirs = {p.resolve() for p in wtroot.iterdir() if p.is_dir()} if wtroot.exists() else set()
        proc = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=ROOT, capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
        registered = {pathlib.Path(x).resolve() for x in re.findall(r"^worktree (.+)$", proc.stdout, re.M)}
        for p in sorted(dirs - registered, key=str):
            problems.append(f"ORPHAN DIR {p.relative_to(ROOT)}: not registered by git; inspect before removing")
        for p in sorted((registered - {ROOT.resolve()}), key=str):
            if not p.exists():
                problems.append(f"MISSING WORKTREE {p}: registered by git but directory is absent")
                continue
            st = subprocess.run(["git", "-C", str(p), "status", "--porcelain"], capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
            state = "dirty" if st.stdout.strip() else "clean"
            print(f"WORKTREE {p.relative_to(ROOT) if p.is_relative_to(ROOT) else p}: {state}")
        for p in problems:
            print(p)
        print(f"doctor: {len(b)} claim(s), {len(dirs)} local worktree dir(s), {len(problems)} problem(s)")
        sys.exit(1 if problems else 0)
    if a.cmd == "list":
        if not b:
            print("board empty")
        for n, c in b.items():
            tracked = c.get("bead", "UNTRACKED")
            print(f"{n:22} since {c['since']}  [{tracked}] {c['task']}\n{'':22} owns: {' '.join(c['owns'])}")
            if c.get("uses"):
                print(f"{'':22} uses: {' '.join(c['uses'])}")
        return
    if a.cmd == "busy":
        for d in sorted((ROOT / "games").iterdir()):
            if d.is_dir():
                proj = f"games/{d.name}"
                why = conflicts([proj], b)
                if why:
                    print(d.name, "|", why[0])
        return
    if a.cmd == "release":
        if b.pop(a.name, None) is None:
            sys.exit(f"no claim named {a.name}")
        save(b); print("released", a.name, flush=True)
        if a.remove_worktree:
            cmd = [sys.executable, "-I", str(WORKTREE), "remove", a.worktree or a.name]
            cmd += (["--into", a.into] if a.into else []) + (["--force-untracked"] if a.force_untracked else [])
            rc = subprocess.run(cmd).returncode
            if rc:
                sys.exit(f"claim released, worktree kept (worktree.py remove exit {rc})")
        return
    found = conflicts(a.owns, b, me=getattr(a, "name", None), uses=a.uses)
    for f in found:
        print(f)
    if a.cmd == "check":
        print("OK: no conflicts" if not found else f"{len(found)} conflict(s)")
        sys.exit(1 if found else 0)
    if found and not a.force:
        sys.exit("claim refused (use --force only if the conflict is understood and harmless)")
    tracked = bead(a.bead)
    if tracked.get("status") not in ("confirmed", "in_progress"):
        sys.exit(f"Beads task {a.bead} must be confirmed before claiming (status={tracked.get('status')})")
    if tracked.get("status") == "confirmed":
        proc = bead_command("update", a.bead, "--claim")
        if proc.returncode:
            sys.stderr.write(proc.stderr or proc.stdout)
            sys.exit(f"could not claim Beads task {a.bead}")
    b[a.name] = {"bead": a.bead, "task": a.task, "owns": [norm(p) for p in a.owns], "uses": a.uses,
                 "since": time.strftime("%Y-%m-%d %H:%M")}
    save(b); print("claimed", a.name)


if __name__ == "__main__":
    main()
