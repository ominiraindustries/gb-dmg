"""GBDMG harness adapter for Beads (ported from the SNES harness, 2026-11-24).

Passes ordinary arguments to ``bd`` and turns the documented lifecycle into executable rules
(docs/harness/beads.md):

  create   needs --acceptance and an area:<name> label
  confirmed  needs acceptance criteria and dated Evidence (YYYY-MM-DD) in --append-notes
  --claim  only from confirmed (native bd --claim only accepts open)
  close    needs --reason "Verification|Discarded|Duplicate|Superseded ... YYYY-MM-DD";
           a verified close needs status resolved first
  --notes  on an issue that already has notes becomes --append-notes (--replace-notes overwrites)

  python -I harness/scripts/beads.py check     # active tasks without acceptance / area label

The wrapper finds the native executable on Windows: PowerShell may pick npm's bd.ps1 shim and
reject it when script execution is disabled.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import re


ROOT = Path(__file__).resolve().parents[2]


def bd_command() -> list[str]:
    override = os.environ.get("BEADS_BIN")
    if override:
        return [override]
    for name in ("bd.exe", "bd.cmd", "bd"):
        found = shutil.which(name)
        if found and not found.lower().endswith(".ps1"):
            return [found]
    npm_native = (
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Programs/nodejs/node_modules/@beads/bd/bin/bd.exe"
    )
    if npm_native.is_file():
        return [str(npm_native)]
    raise SystemExit("beads: bd not found; install with `npm.cmd install -g @beads/bd`")


def run(args: list[str], *, input_text: str | None = None, capture: bool = False):
    return subprocess.run(
        bd_command() + args,
        cwd=ROOT,
        input=input_text,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=capture,
        check=False,
    )


def flag_value(args: list[str], *names: str) -> str | None:
    for n, arg in enumerate(args):
        if arg in names and n + 1 < len(args):
            return args[n + 1]
        for name in names:
            if arg.startswith(name + "="):
                return arg.split("=", 1)[1]
    return None


def issue(issue_id: str) -> dict:
    result = run(["show", issue_id, "--json"], capture=True)
    if result.returncode:
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    rows = json.loads(result.stdout)
    if not rows:
        raise SystemExit(f"beads: no issue {issue_id}")
    return rows[0]


def claim_confirmed(args: list[str]) -> int:
    """Claim a custom-status task atomically (native --claim only accepts open)."""
    ids = [arg for arg in args[1:] if not arg.startswith("-")]
    if len(ids) != 1:
        raise SystemExit("beads: claim requires exactly one explicit issue ID")
    issue_id = ids[0]
    current = issue(issue_id)
    if current.get("status") == "in_progress":
        print(f"already in progress: {issue_id}")
        return 0
    actor = os.environ.get("BEADS_ACTOR")
    if not actor:
        who = subprocess.run(
            ["git", "config", "user.name"], cwd=ROOT, capture_output=True, text=True
        )
        actor = who.stdout.strip() if who.returncode == 0 else ""
    command = ["update", issue_id, "--status", "in_progress", "--if-status", "confirmed"]
    if actor:
        command += ["--assignee", actor]
    return run(command).returncode


def enforce_workflow(args: list[str]) -> None:
    """Make the documented lifecycle an executable rule, not a suggestion."""
    if not args or any(arg in ("-h", "--help") for arg in args):
        return
    command = args[0]
    if command in ("create", "new") and "--dry-run" not in args:
        if not flag_value(args, "--acceptance"):
            raise SystemExit("beads: create requires --acceptance with a verifiable result")
        labels = [args[n + 1] for n, arg in enumerate(args[:-1]) if arg in ("-l", "--labels")]
        labels += [arg.split("=", 1)[1] for arg in args if arg.startswith("--labels=")]
        if not any(part.startswith("area:") for value in labels for part in value.split(",")):
            raise SystemExit("beads: create requires an area:<name> label")
    if command == "update" and flag_value(args, "-s", "--status") == "confirmed":
        ids = [arg for arg in args[1:] if not arg.startswith("-")]
        if not ids:
            raise SystemExit("beads: confirmation requires an explicit issue ID")
        current = issue(ids[0])
        acceptance = flag_value(args, "--acceptance") or current.get("acceptance_criteria", "")
        evidence = flag_value(args, "--append-notes", "--notes") or ""
        if not acceptance.strip():
            raise SystemExit("beads: confirmation requires acceptance criteria")
        if not re.search(r"(?i)\bevidence\b.*\b\d{4}-\d{2}-\d{2}\b", evidence):
            raise SystemExit("beads: confirmation requires dated Evidence (YYYY-MM-DD) in notes")
    if command == "update" and "--claim" in args:
        ids = [arg for arg in args[1:] if not arg.startswith("-")]
        if not ids:
            raise SystemExit("beads: claim requires an explicit issue ID")
        current = issue(ids[0])
        if current.get("status") not in ("confirmed", "in_progress"):
            raise SystemExit(
                f"beads: confirm {ids[0]} with evidence before claiming (status={current.get('status')})"
            )
        if not current.get("acceptance_criteria", "").strip():
            raise SystemExit(f"beads: add acceptance criteria to {ids[0]} before claiming")
    if command in ("close", "done"):
        ids = [arg for arg in args[1:] if not arg.startswith("-")]
        if not ids:
            raise SystemExit("beads: close requires an explicit issue ID")
        reason = flag_value(args, "-r", "--reason")
        reason_file = flag_value(args, "--reason-file")
        if not reason and not reason_file:
            raise SystemExit("beads: close requires --reason with dated verification or discard rationale")
        if reason_file:
            try:
                reason = Path(reason_file).read_text(encoding="utf-8").strip()
            except OSError as exc:
                raise SystemExit(f"beads: cannot read reason file: {exc}") from exc
        if reason and not re.search(
            r"(?i)\b(verification|verified|discarded|duplicate|superseded)\b.*\b\d{4}-\d{2}-\d{2}\b",
            reason,
        ):
            raise SystemExit(
                "beads: close reason must name Verification/Discarded/Duplicate/Superseded and YYYY-MM-DD"
            )
        current = issue(ids[0])
        discard = bool(reason and re.search(r"(?i)\b(discarded|duplicate|superseded)\b", reason))
        if not discard and current.get("status") != "resolved":
            raise SystemExit(
                f"beads: resolve {ids[0]} before verified close (status={current.get('status')})"
            )


def protect_notes(args: list[str]) -> list[str]:
    """`update --notes` replaces the whole notes field in bd; two agents wiped earlier evidence that way
    (SNES BL-c3hx.1, BL-c3hx.4, 2026-11-21). On an issue that already has notes, --notes becomes --append-notes;
    an intentional overwrite is spelled --replace-notes."""
    if not args or args[0] != "update":
        return args
    out = []
    for arg in args:
        if arg == "--replace-notes":
            out.append("--notes")
        elif arg.startswith("--replace-notes="):
            out.append("--notes=" + arg.split("=", 1)[1])
        else:
            out.append(arg)
    if "--replace-notes" in args or any(a.startswith("--replace-notes=") for a in args):
        return out
    if "--notes" not in out and not any(a.startswith("--notes=") for a in out):
        return out
    ids = [arg for n, arg in enumerate(out[1:], 1) if not arg.startswith("-") and not out[n - 1].startswith("-")]
    if any((issue(i).get("notes") or "").strip() for i in ids):
        sys.stderr.write("beads: --notes would erase existing notes; appending instead (use --replace-notes to overwrite)\n")
        out = ["--append-notes" if a == "--notes" else
               ("--append-notes=" + a.split("=", 1)[1] if a.startswith("--notes=") else a) for a in out]
    return out


def check() -> int:
    """Quality check of the live backlog: active tasks without acceptance or area label."""
    result = run(["list", "--all", "--limit", "0", "--json"], capture=True)
    if result.returncode:
        sys.stderr.write(result.stderr)
        return result.returncode
    beads = json.loads(result.stdout)
    active = [item for item in beads if item.get("status") not in ("closed", "tombstone")]
    no_acc = [item["id"] for item in active if not (item.get("acceptance_criteria") or "").strip()]
    no_area = [item["id"] for item in active
               if not any(str(label).startswith("area:") for label in item.get("labels") or [])]
    print(f"beads: {len(beads)} task(s), {len(active)} active")
    if no_acc:
        print(f"beads: quality warning: {len(no_acc)} active task(s) lack acceptance (first: {' '.join(no_acc[:10])})")
    if no_area:
        print(f"beads: quality warning: {len(no_area)} active task(s) lack an area: label (first: {' '.join(no_area[:10])})")
    return 1 if (no_acc or no_area) else 0


def main() -> int:
    if sys.argv[1:] == ["check"]:
        return check()
    args = protect_notes(sys.argv[1:])
    enforce_workflow(args)
    if args[:1] == ["update"] and "--claim" in args[1:]:
        return claim_confirmed(args)
    return run(args).returncode


if __name__ == "__main__":
    raise SystemExit(main())
