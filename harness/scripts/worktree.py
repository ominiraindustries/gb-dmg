"""Agent worktrees: create them (full checkout + junctions to the untracked tool dirs) and remove them safely.

Ported from the SNES harness (BL-lop5, 2026-11-24). GBDMG is small (a full checkout is a few MB), so worktrees are
plain full checkouts; the only shared, big, untracked dirs (tools/ with GBDK, reference/) are linked with
junctions into the main checkout. Deleting a worktree recursively THROUGH a junction destroys the real tools (it
happened in SNES), so `remove` unlinks every reparse point first (non-recursively), checks none is left, and
never walks into one.

Usage (from the main checkout or any worktree; always python -I):
  worktree.py add NAME --base BRANCH [--branch B] [--no-junctions]
  worktree.py remove NAME [--into BRANCH] [--force-untracked] [--force-unmerged] [--delete-branch]
  worktree.py list [--into BRANCH] [--no-size]
  worktree.py prune --merged-into BRANCH [--older-than DAYS] [--match GLOB] (--dry-run | --yes) [--force-untracked]

add: .claude/worktrees/NAME on a new branch from BASE, then junctions for JUNCTIONS that exist in the main
  checkout and are not tracked by git, verified. The base branch is remembered in git config
  (branch.NAME.gbWorktreeBase) and is the default merge target of remove/list.
remove: refuses with tracked changes (always), untracked files (unless --force-untracked), a branch not merged into
  the target (unless --force-unmerged), or an active board claim with the same name. Archives built ROMs (*.gb) to
  .claude/rom_archive/NAME/, deletes every reparse point (links only), checks none remains, runs git worktree remove
  and reports the MB freed.
State is git's (worktree list, branch config); board claims are read from .claude/board.json.
"""
import argparse, fnmatch, json, os, pathlib, re, shutil, stat, subprocess, sys, time


def git_raw(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace")


def main_root():
    """The main checkout (parent of the common .git), even when run from inside a worktree."""
    here = pathlib.Path(__file__).resolve().parent
    p = git_raw(["rev-parse", "--path-format=absolute", "--git-common-dir"], here)
    if p.returncode:
        sys.exit("worktree.py: not inside a git repository")
    return pathlib.Path(p.stdout.strip()).resolve().parent


MAIN = main_root()
WT_ROOT = MAIN / ".claude" / "worktrees"
ROM_ARCHIVE = MAIN / ".claude" / "rom_archive"
BOARD = MAIN / ".claude" / "board.json"
CFG_BASE = "gbWorktreeBase"
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
# untracked (gitignored), big, read-only dirs shared with the main checkout through junctions. Never a tracked
# path: git would write through the link into the main checkout.
JUNCTIONS = ["tools", "reference"]
FILE_ATTRIBUTE_REPARSE_POINT = 0x400


def git(args, cwd=MAIN, check=True):
    p = git_raw(args, cwd)
    if check and p.returncode:
        sys.exit(f"git {' '.join(args)} failed:\n{(p.stderr or p.stdout).strip()}")
    return p


def check_name(name):
    if not NAME_RE.match(name):
        sys.exit(f"bad worktree name {name!r}: letters, digits, '.', '_' and '-' only")
    return name


# ---- filesystem walking that never enters a reparse point --------------------------------------------------------

def is_reparse(path_or_entry):
    st = (path_or_entry.stat(follow_symlinks=False) if isinstance(path_or_entry, os.DirEntry)
          else os.lstat(path_or_entry))
    return bool(getattr(st, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT) or stat.S_ISLNK(st.st_mode)


def walk(root):
    """Yield (path, DirEntry, reparse) for every entry under root; reparse points are reported, never entered."""
    stack = [str(root)]
    while stack:
        d = stack.pop()
        try:
            it = os.scandir(d)
        except OSError:
            continue
        with it:
            for e in it:
                try:
                    rp = is_reparse(e)
                    isdir = e.is_dir(follow_symlinks=False)
                except OSError:
                    continue
                yield e.path, e, rp
                if isdir and not rp:
                    stack.append(e.path)


def reparse_points(root):
    return [p for p, _, rp in walk(root) if rp]


def size_mb(root):
    total = 0
    for _, e, rp in walk(root):
        if not rp:
            try:
                st = e.stat(follow_symlinks=False)
                if not stat.S_ISDIR(st.st_mode):
                    total += st.st_size
            except OSError:
                pass
    return total / (1 << 20)


# ---- junctions --------------------------------------------------------------------------------------------------

def junction_target(path):
    try:
        t = os.readlink(path)
    except OSError:
        return None
    t = t[4:] if t.startswith("\\\\?\\") else t
    return os.path.normcase(os.path.abspath(t))


def make_junction(link, target):
    """Create a directory junction link -> target without any shell string: _winapi, else cmd with an argv list."""
    link, target = str(link), str(target)
    try:
        import _winapi
        _winapi.CreateJunction(target, link)
    except (ImportError, AttributeError, OSError):
        p = subprocess.run(["cmd", "/c", "mklink", "/J", link, target], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if p.returncode:
            raise OSError(f"mklink /J {link} failed: {(p.stderr or p.stdout).strip()}")
    if not is_reparse(link) or junction_target(link) != os.path.normcase(os.path.abspath(target)):
        raise OSError(f"junction {link} does not point to {target}")


def remove_link(path):
    """Remove one reparse point itself (junction or symlink), never what it points to."""
    if not is_reparse(path):
        raise OSError(f"refusing to delete {path}: not a reparse point")
    st = os.lstat(path)
    if getattr(st, "st_file_attributes", 0) & 0x10 or stat.S_ISDIR(st.st_mode):   # FILE_ATTRIBUTE_DIRECTORY
        os.rmdir(path)        # RemoveDirectoryW on a junction/dir symlink deletes the link only
    else:
        os.unlink(path)


# ---- git worktree state -----------------------------------------------------------------------------------------

def worktrees():
    """{resolved path: {'branch': name or None, 'locked': bool, 'head': sha}} for the registered worktrees."""
    out, cur = {}, None
    for line in git(["worktree", "list", "--porcelain"]).stdout.splitlines():
        if line.startswith("worktree "):
            cur = {"branch": None, "locked": False, "head": ""}
            out[pathlib.Path(line[9:]).resolve()] = cur
        elif cur is not None and line.startswith("branch "):
            cur["branch"] = line[7:].removeprefix("refs/heads/")
        elif cur is not None and line.startswith("HEAD "):
            cur["head"] = line[5:]
        elif cur is not None and line.startswith("locked"):
            cur["locked"] = True
    return out


def status(path):
    """(tracked changes, untracked files) of a worktree, ignored files excluded."""
    p = git(["-C", str(path), "status", "--porcelain", "--untracked-files=normal"], check=False)
    if p.returncode:
        return ["<git status failed>"], []
    lines = [l for l in p.stdout.splitlines() if l.strip()]
    return [l for l in lines if not l.startswith("??")], [l[3:] for l in lines if l.startswith("??")]


def branch_base(branch):
    p = git(["config", "--get", f"branch.{branch}.{CFG_BASE}"], check=False)
    return p.stdout.strip() or None


def current_branch():
    return git(["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()


def merged(branch, into):
    if not branch:
        return False
    if git(["rev-parse", "--verify", "--quiet", into], check=False).returncode:
        sys.exit(f"unknown target branch {into}")
    return git(["merge-base", "--is-ancestor", branch, into], check=False).returncode == 0


def age_days(path, branch):
    """Days since the last activity: the later of the branch's last commit and the worktree index."""
    t = 0.0
    if branch:
        p = git(["log", "-1", "--format=%ct", branch], check=False)
        if p.stdout.strip().isdigit():
            t = float(p.stdout.strip())
    g = git(["-C", str(path), "rev-parse", "--path-format=absolute", "--git-dir"], check=False).stdout.strip()
    if g and (pathlib.Path(g) / "index").exists():
        t = max(t, (pathlib.Path(g) / "index").stat().st_mtime)
    return (time.time() - t) / 86400 if t else float("inf")


def board_claims():
    try:
        return json.loads(BOARD.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


# ---- add --------------------------------------------------------------------------------------------------------

def cmd_add(a):
    name = check_name(a.name)
    branch = a.branch or name
    path = WT_ROOT / name
    if os.path.lexists(path):
        sys.exit(f"{path} already exists")
    if git(["rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"], check=False).returncode == 0:
        sys.exit(f"branch {branch} already exists (use --branch for another name)")
    if git(["rev-parse", "--verify", "--quiet", a.base], check=False).returncode:
        sys.exit(f"unknown base {a.base}")
    WT_ROOT.mkdir(parents=True, exist_ok=True)
    git(["worktree", "add", "-b", branch, str(path), a.base])
    made = []
    try:
        git(["config", f"branch.{branch}.{CFG_BASE}", a.base])
        for rel in [] if a.no_junctions else JUNCTIONS:
            src, dst = MAIN / rel, path / rel
            if not src.is_dir() or is_reparse(src):
                continue
            if git(["ls-files", "--", rel]).stdout.strip():
                print(f"skip junction {rel}: tracked by git"); continue
            if os.path.lexists(dst):
                print(f"skip junction {rel}: already present"); continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            make_junction(dst, src)
            made.append(rel)
    except (OSError, SystemExit) as e:
        print(f"add failed ({e}); undoing", file=sys.stderr)
        undo(path, branch)
        sys.exit(1)
    for rel in made:                                  # verify after the fact
        if junction_target(path / rel) != os.path.normcase(str(MAIN / rel)):
            sys.exit(f"junction {rel} verification failed")
    print(f"junctions: {', '.join(made) or 'none'}")
    print(f"created {path} on {branch} from {a.base}, {size_mb(path):.1f} MB")


def undo(path, branch):
    for rp in reparse_points(path) if path.exists() else []:
        remove_link(rp)
    if reparse_points(path) if path.exists() else []:
        print(f"reparse points remain in {path}; left in place", file=sys.stderr); return
    git(["worktree", "remove", "--force", str(path)], check=False)
    git(["branch", "-D", branch], check=False)


# ---- remove -----------------------------------------------------------------------------------------------------

def remove_one(name, into=None, force_untracked=False, force_unmerged=False, delete_branch=False, quiet=False):
    """Return MB freed; raise RuntimeError with the reason when refused."""
    check_name(name)
    path = (WT_ROOT / name).resolve()
    wts = worktrees()
    if path not in wts:
        raise RuntimeError(f"{path} is not a registered worktree")
    info = wts[path]
    if info["locked"]:
        raise RuntimeError(f"{name} is locked (git worktree unlock first)")
    cwd = pathlib.Path.cwd().resolve()
    if cwd == path or path in cwd.parents:
        raise RuntimeError(f"cannot remove {name}: the current directory is inside it")
    if name in board_claims():
        raise RuntimeError(f"board claim {name} is active: board.py release {name} --remove-worktree")
    tracked, untracked = status(path)
    if tracked:
        raise RuntimeError(f"{name} has {len(tracked)} uncommitted tracked change(s), e.g. {tracked[0]}")
    if untracked and not force_untracked:
        raise RuntimeError(f"{name} has {len(untracked)} untracked file(s), e.g. {untracked[0]} "
                           "(--force-untracked deletes them)")
    branch = info["branch"]
    target = into or branch_base(branch or "") or current_branch()
    if not force_unmerged and not merged(branch, target):
        raise RuntimeError(f"branch {branch or '(detached)'} is not merged into {target} (--force-unmerged)")
    before = size_mb(path)
    tracked_roms = {os.path.normcase(str(path / f)) for f in
                    git(["-C", str(path), "ls-files", "-z", "--", "*.gb"], check=False).stdout.split(chr(0)) if f}
    roms = [p for p, e, rp in walk(path) if not rp and p.lower().endswith(".gb")
            and e.is_file(follow_symlinks=False) and os.path.normcase(p) not in tracked_roms]   # built, not in git
    for r in roms:
        dst = ROM_ARCHIVE / name / os.path.relpath(r, path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(r, dst)
    links = reparse_points(path)
    for lp in links:
        remove_link(lp)
    left = reparse_points(path)
    if left:
        raise RuntimeError(f"reparse points still present, nothing deleted: {left[:3]}")
    p = git(["worktree", "remove", *(["--force"] if untracked else []), str(path)], check=False)
    if p.returncode:
        raise RuntimeError(f"git worktree remove failed (links already removed): {(p.stderr or p.stdout).strip()}")
    if path.exists():
        print(f"warning: {path} still on disk (a file in use?)")
    if delete_branch and branch:
        d = git(["branch", "-D" if force_unmerged else "-d", branch], check=False)
        print(f"branch {branch}: {'deleted' if d.returncode == 0 else 'kept: ' + d.stderr.strip()}")
    if not quiet:
        print(f"removed {name} ({branch}, merged into {target}{' [forced]' if force_unmerged else ''}): "
              f"{len(links)} link(s) unlinked, {len(roms)} ROM(s) archived"
              f"{' to ' + str(ROM_ARCHIVE / name) if roms else ''}, {before:.1f} MB freed")
    return before


def cmd_remove(a):
    try:
        remove_one(a.name, a.into, a.force_untracked, a.force_unmerged, a.delete_branch)
    except RuntimeError as e:
        sys.exit(f"refused: {e}")


# ---- list / prune -----------------------------------------------------------------------------------------------

def rows(into, sizes=True):
    out = []
    for path, info in sorted(worktrees().items(), key=lambda kv: str(kv[0])):
        if WT_ROOT.resolve() not in path.parents:
            continue
        br = info["branch"]
        target = into or branch_base(br or "") or current_branch()
        tracked, untracked = status(path) if path.exists() else (["<missing>"], [])
        out.append({"name": path.name, "path": path, "branch": br, "target": target,
                    "merged": merged(br, target) if br else False, "tracked": len(tracked),
                    "untracked": len(untracked), "age": age_days(path, br), "locked": info["locked"],
                    "exists": path.exists(),
                    "sparse": False,
                    "mb": size_mb(path) if sizes and path.exists() else None})
    return out


def cmd_list(a):
    rs = rows(a.into, not a.no_size)
    total = 0.0
    print(f"{'name':28} {'MB':>7} {'age d':>6}  {'branch':28} merged  dirty   kind")
    for r in rs:
        total += r["mb"] or 0
        dirty = f"{r['tracked']}t/{r['untracked']}u" if r["tracked"] or r["untracked"] else "clean"
        mb = "-" if r["mb"] is None else f"{r['mb']:.0f}"
        print(f"{r['name']:28} {mb:>7} {r['age']:6.1f}  {(r['branch'] or '(detached)'):28} "
              f"{('yes' if r['merged'] else 'no'):6}  {dirty:7} {'sparse' if r['sparse'] else 'full'}"
              f"{' LOCKED' if r['locked'] else ''}{' MISSING' if not r['exists'] else ''}")
    registered = {r["path"] for r in rs}
    for d in sorted(WT_ROOT.iterdir()) if WT_ROOT.exists() else []:
        if d.is_dir() and d.resolve() not in registered:
            print(f"{d.name:28} {'?':>7}  ORPHAN DIR (not registered by git; inspect by hand)")
    print(f"{len(rs)} worktree(s)" + (f", {total:.0f} MB" if not a.no_size else ""))


def cmd_prune(a):
    claims = board_claims()
    cands, skipped = [], 0
    for r in rows(a.merged_into, sizes=False):
        why = None
        if a.match and not fnmatch.fnmatch(r["name"], a.match):
            continue
        if not r["exists"]:
            why = "missing"
        elif r["locked"]:
            why = "locked"
        elif r["name"] in claims:
            why = "board claim"
        elif not r["merged"]:
            why = f"not merged into {a.merged_into}"
        elif r["tracked"]:
            why = "tracked changes"
        elif r["untracked"] and not a.force_untracked:
            why = "untracked files"
        elif r["age"] < a.older_than:
            why = f"age {r['age']:.1f} d"
        if why:
            skipped += 1
            if a.verbose:
                print(f"keep   {r['name']}: {why}")
        else:
            cands.append(r)
    freed = 0.0
    for r in cands:
        if a.dry_run:
            mb = size_mb(r["path"])
            freed += mb
            print(f"would remove {r['name']:28} {mb:7.0f} MB  {r['branch']}  age {r['age']:.1f} d")
        else:
            try:
                freed += remove_one(r["name"], a.merged_into, a.force_untracked, False, a.delete_branch)
            except RuntimeError as e:
                print(f"skip {r['name']}: {e}")
    print(f"{'would free' if a.dry_run else 'freed'} {freed:.0f} MB in {len(cands)} worktree(s); kept {skipped}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ad = sub.add_parser("add", help="create .claude/worktrees/NAME on a new branch (full checkout + junctions)")
    ad.add_argument("name"); ad.add_argument("--base", required=True)
    ad.add_argument("--branch", help="branch name (default: NAME)")
    ad.add_argument("--no-junctions", action="store_true", help="do not link tools/ and reference/")
    rm = sub.add_parser("remove", help="remove a merged, clean worktree (links first)")
    rm.add_argument("name"); rm.add_argument("--into", help="merge target (default: the base it was created from)")
    rm.add_argument("--force-untracked", action="store_true"); rm.add_argument("--force-unmerged", action="store_true")
    rm.add_argument("--delete-branch", action="store_true", help="also delete the branch (git branch -d)")
    ls = sub.add_parser("list"); ls.add_argument("--into"); ls.add_argument("--no-size", action="store_true")
    pr = sub.add_parser("prune", help="remove every clean worktree merged into a branch")
    pr.add_argument("--merged-into", required=True); pr.add_argument("--older-than", type=float, default=0)
    g = pr.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true"); g.add_argument("--yes", action="store_true")
    pr.add_argument("--force-untracked", action="store_true"); pr.add_argument("--delete-branch", action="store_true")
    pr.add_argument("--match", help="only worktree names matching this glob")
    pr.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    {"add": cmd_add, "remove": cmd_remove, "list": cmd_list, "prune": cmd_prune}[a.cmd](a)


if __name__ == "__main__":
    main()
