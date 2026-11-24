"""Tests of the harness scripts ported from SNES (2026-11-24): beads.py rules, inbox_hook extraction, board.py
conflicts, worktree.py link removal and kb.py search. bd is never called: beads.issue() is replaced by a fake.

  python -m pytest harness/scripts/tests -q
"""
import os
import pathlib
import subprocess
import sys

import pytest

SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import beads  # noqa: E402
import board  # noqa: E402
import inbox_hook  # noqa: E402

FAKE = {
    "GB-has": {"notes": "Evidence (2026-11-21): old", "status": "open", "acceptance_criteria": "x"},
    "GB-empty": {"notes": "", "status": "open", "acceptance_criteria": "x"},
    "GB-conf": {"notes": "", "status": "confirmed", "acceptance_criteria": "x"},
    "GB-noacc": {"notes": "", "status": "open", "acceptance_criteria": ""},
    "GB-res": {"notes": "", "status": "resolved", "acceptance_criteria": "x"},
}


@pytest.fixture(autouse=True)
def fake_issue(monkeypatch):
    monkeypatch.setattr(beads, "issue", lambda issue_id: FAKE[issue_id])


# ---- beads.py: notes are never wiped
@pytest.mark.parametrize("args,want", [
    (["update", "GB-has", "--notes", "x"], ["update", "GB-has", "--append-notes", "x"]),
    (["update", "GB-has", "--notes=x", "--status", "resolved"], ["update", "GB-has", "--append-notes=x", "--status", "resolved"]),
    (["update", "GB-empty", "--notes", "x"], ["update", "GB-empty", "--notes", "x"]),
    (["update", "GB-has", "--replace-notes", "x"], ["update", "GB-has", "--notes", "x"]),
    (["update", "GB-has", "--replace-notes=x"], ["update", "GB-has", "--notes=x"]),
    (["show", "GB-has"], ["show", "GB-has"]),
])
def test_protect_notes(args, want):
    assert beads.protect_notes(list(args)) == want


# ---- beads.py: the lifecycle is enforced
@pytest.mark.parametrize("args,msg", [
    (["create", "t", "-l", "area:gbe"], "--acceptance"),
    (["create", "t", "--acceptance", "a", "-l", "kind:bug"], "area:"),
    (["update", "GB-empty", "--status", "confirmed", "--append-notes", "seen it"], "dated Evidence"),
    (["update", "GB-noacc", "--status", "confirmed", "--append-notes", "Evidence (2026-11-24): x"], "acceptance"),
    (["update", "GB-empty", "--claim"], "confirm GB-empty"),
    (["close", "GB-res"], "--reason"),
    (["close", "GB-res", "--reason", "done"], "Verification"),
    (["close", "GB-conf", "--reason", "Verification (2026-11-24): pytest ok"], "resolve GB-conf"),
])
def test_workflow_refuses(args, msg):
    with pytest.raises(SystemExit, match=msg):
        beads.enforce_workflow(args)


@pytest.mark.parametrize("args", [
    ["create", "t", "--acceptance", "a", "-l", "area:juego:faro,kind:bug"],
    ["update", "GB-empty", "--status", "confirmed", "--append-notes", "Evidence (2026-11-24): reproduced"],
    ["update", "GB-conf", "--claim"],
    ["close", "GB-res", "--reason", "Verification (2026-11-24): gb.py test faro: 40 passed"],
    ["close", "GB-empty", "--reason", "Discarded (2026-11-24): the original does the same"],
])
def test_workflow_accepts(args):
    beads.enforce_workflow(args)


# ---- inbox_hook: sections of a final report become inbox items
REPORT = """Hecho: el HUD ya usa gbe_tbox.

## Lecciones para mi rol
- lessons.py add --id hud-lyc-early --text "El corte LYC del HUD se arma antes del VBlank" --evidence "faro 2026-11-24"

## Huecos de gbe
- gbe_vq: la cola no avisa cuando se llena y pierde filas en silencio

## Bugs encontrados
- Ninguno nuevo
"""


def test_extract_sections():
    got = inbox_hook.extract(REPORT)
    kinds = [k for k, _, _ in got]
    assert kinds == ["lesson", "gap"]          # "Ninguno nuevo" is an empty note, not a finding
    items = inbox_hook.items_from_report(REPORT, "gb-game-dev #a1", "2026-11-24")
    assert items[0]["evidence"].endswith("(proposed id hud-lyc-early)")
    assert items[1]["module"] == "vq"
    assert inbox_hook.item_id("x #a1", "Texto") == inbox_hook.item_id("y #a1", "texto")   # stable per agent + text


# ---- board.py: gbe modules and the games that use them
def test_board_modules_and_conflicts():
    assert board.module_of("harness/common/src/gbe_vq.s") == "vq"
    assert board.module_of("gbe/sfx") == "sfx"
    assert board.module_of("harness/common/src/gbe_sfx_asm.s") == "sfx"
    assert board.module_of("games/faro/src/main.c") is None
    claims = {"a": {"owns": ["games/mazmorra"], "task": "t"}}
    assert any("DEPENDENCY" in c for c in board.conflicts(["harness/common/src/gbe_world.c"], claims))
    assert any("DIRECT" in c for c in board.conflicts(["games/mazmorra/src"], claims))
    assert not board.conflicts(["docs/guias/x.md"], claims)
    assert any("DEPENDENCY" in c for c in board.conflicts(["harness/gb.py"], claims))     # every game builds with it


# ---- worktree.py: a junction is removed as a link, never followed
@pytest.mark.skipif(os.name != "nt", reason="junctions are a Windows feature")
def test_remove_link_keeps_target(tmp_path):
    import worktree
    target = tmp_path / "real"
    target.mkdir()
    (target / "keep.txt").write_text("x", encoding="utf-8")
    link = tmp_path / "wt" / "tools"
    link.parent.mkdir()
    worktree.make_junction(link, target)
    assert worktree.is_reparse(link)
    assert [pathlib.Path(p) for p in worktree.reparse_points(tmp_path / "wt")] == [link]
    worktree.remove_link(link)
    assert not os.path.lexists(link)
    assert (target / "keep.txt").exists()
    with pytest.raises(OSError):
        worktree.remove_link(target)           # a real directory is refused


# ---- kb.py: the queries in kb_tests.json hit their expected results
def test_kb_queries():
    p = subprocess.run([sys.executable, "-I", str(SCRIPTS / "kb.py"), "test"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300)
    assert p.returncode == 0, p.stdout[-2000:]


def test_kb_brief_platformer():
    p = subprocess.run([sys.executable, "-I", str(SCRIPTS / "kb.py"), "brief", "--role", "gb-game-dev",
                        "--task", "plataformas con scroll"], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300)
    assert p.returncode == 0
    assert "## API gbe" in p.stdout and "## Lessons" in p.stdout
    assert len(p.stdout.splitlines()) < 60
