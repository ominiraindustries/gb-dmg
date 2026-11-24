"""SessionStart hook: a few lines of context for a new Claude Code session (never blocks, always exit 0).

Prints the findings-inbox line (kb.py inbox status), the Beads summary (in progress / ready to work) and the
active board claims. Run by hand:  python -I harness/scripts/session_start.py
"""
import json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "harness" / "scripts"


def run(args, timeout=20):
    try:
        p = subprocess.run([sys.executable, "-I", *args], cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return p.returncode, p.stdout
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    out = []
    rc, txt = run([str(SCRIPTS / "kb.py"), "inbox", "status"])
    if rc == 0 and txt.strip():
        out.append(txt.strip())
    rc, txt = run([str(SCRIPTS / "beads.py"), "list", "--status", "in_progress", "--json"])
    doing = json.loads(txt) if rc == 0 and txt.strip().startswith("[") else []
    rc, txt = run([str(SCRIPTS / "beads.py"), "ready", "--json"])
    ready = json.loads(txt) if rc == 0 and txt.strip().startswith("[") else []
    if doing or ready:
        line = f"Beads: {len(doing)} en curso, {len(ready)} listas (beads.py ready --json)"
        if doing:
            line += "; en curso: " + ", ".join(f"{i['id']} {i['title'][:50]}" for i in doing[:3])
        out.append(line)
    board = ROOT / ".claude" / "board.json"
    try:
        claims = json.loads(board.read_text(encoding="utf-8")) if board.exists() else {}
    except ValueError:
        claims = {}
    if claims:
        out.append("Reservas activas (board.py list): " + ", ".join(f"{n} [{c.get('bead', '?')}]" for n, c in claims.items()))
    out.append("Inicio de tarea: python -I harness/scripts/kb.py brief --role <rol> --task \"<tarea>\"")
    print("\n".join(out))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001  never block the session
        print(f"session_start: {e}", file=sys.stderr)
    sys.exit(0)
