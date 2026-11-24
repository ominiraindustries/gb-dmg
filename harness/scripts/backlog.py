"""Read-only view of the live Beads backlog for kb.py (ported from the SNES harness, 2026-11-24).

Beads/Dolt is the source of truth (docs/harness/beads.md); this module only normalises `bd list --all --json`
into flat dicts {id, title, area, kind, status, priority, created, updated, notes, evidence, acceptance,
verification, done_ref} and validates them. Status names: open, confirmed, doing (= in_progress), resolved,
done (= closed), discarded (closed with label outcome:discarded).

  python -I harness/scripts/backlog.py list [--area A] [--status S]
  python -I harness/scripts/backlog.py audit
"""
import argparse, datetime, json, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
BEADS = ROOT / ".beads" / "metadata.json"
BEADS_ADAPTER = ROOT / "harness" / "scripts" / "beads.py"
KINDS = ["gap", "bug", "idea", "game", "tool", "doc", "art", "engine", "harness", "design", "audio"]
STATUS = ["open", "confirmed", "doing", "resolved", "done", "discarded"]
PENDING = ("open", "confirmed", "doing", "resolved")


def today():
    return datetime.date.today().isoformat()


def _label_value(labels, prefix, default=""):
    for label in labels:
        if label.startswith(prefix):
            return label[len(prefix):]
    return default


def _load_beads():
    proc = subprocess.run(
        [sys.executable, "-I", str(BEADS_ADAPTER), "list", "--all", "--limit", "0", "--json"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode:
        raise RuntimeError("beads list failed: " + proc.stderr.strip())
    rows = json.loads(proc.stdout or "[]")
    rows.sort(key=lambda row: row.get("created_at") or "")
    out = []
    for bead in rows:
        labels = bead.get("labels") or []
        bstatus = bead.get("status", "open")
        status = {"in_progress": "doing", "closed": "done"}.get(bstatus, bstatus)
        if bstatus == "closed" and "outcome:discarded" in labels:
            status = "discarded"
        item = {
            "id": bead["id"],
            "title": bead["title"],
            "area": _label_value(labels, "area:", "harness"),
            "kind": _label_value(labels, "kind:", "gap"),
            "status": status,
            "priority": bead.get("priority", 2),
            "source": _label_value(labels, "source:", ""),
            "created": (bead.get("created_at") or today())[:10],
            "updated": (bead.get("updated_at") or today())[:10],
            "notes": bead.get("description") or "",
            "evidence": bead.get("notes") or "",
            "acceptance": bead.get("acceptance_criteria") or "",
            "type": bead.get("issue_type") or "",
            "parent": bead.get("parent") or "",
            "size": _label_value(labels, "size:", ""),
            "legacy": "",
            "done_ref": "",
        }
        if status in ("done", "discarded"):
            item["done_ref"] = bead.get("close_reason") or "Beads: closed"
            item["verification"] = bead.get("close_reason") or ""
        out.append(item)
    return out


def load():
    if BEADS.exists() and BEADS_ADAPTER.exists():
        return _load_beads()
    return []


def validate(items):
    errs, seen = [], set()
    for i in items:
        for f in ("id", "title", "area", "status", "created"):
            if i.get(f) in (None, ""):
                errs.append(f"{i.get('id', '?')}: missing {f}")
        if i.get("id") in seen:
            errs.append(f"{i['id']}: duplicate id")
        seen.add(i.get("id"))
        if i.get("status") not in STATUS:
            errs.append(f"{i.get('id')}: status {i.get('status')!r} not in {STATUS}")
    return errs


def audit(items):
    """(errors, warnings): contradictory states and tasks that cannot be closed as written."""
    errors, warnings = [], []
    for i in items:
        iid, status = i.get("id", "?"), i.get("status")
        if status in PENDING and not i.get("acceptance"):
            warnings.append(f"{iid}: pending item has no acceptance criteria")
        if status == "confirmed" and not re.search(r"(?i)evidence.*\d{4}-\d{2}-\d{2}", i.get("evidence", "")):
            errors.append(f"{iid}: confirmed without dated evidence")
        if status in PENDING and re.search(r"\b(HECH[OA]|DONE|CERRAD[OA])\b", i.get("title", "")):
            warnings.append(f"{iid}: title says done but status is {status}")
    return errors, warnings


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ls = sub.add_parser("list"); ls.add_argument("--area"); ls.add_argument("--status")
    sub.add_parser("audit")
    a = ap.parse_args()
    items = load()
    if a.cmd == "list":
        for i in items:
            if (a.area and i["area"] != a.area) or (a.status and i["status"] != a.status):
                continue
            print(f"{i['id']:12} [{i['status']:9} {i['area']} P{i['priority']}] {i['title']}")
        return
    errs, warns = audit(items)
    errs += validate(items)
    for w in warns:
        print("warn:", w)
    for e in errs:
        print("ERROR:", e)
    print(f"backlog: {len(items)} item(s), {len(errs)} error(s), {len(warns)} warning(s)")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
