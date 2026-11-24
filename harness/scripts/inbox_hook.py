"""SubagentStop safety net (ported from the SNES harness, 2026-11-24): put an agent's findings (lessons, gbe gaps,
bugs, notes for the technique book / coordinator)
into the findings inbox docs/datos/inbox.jsonl, so nothing a game or a study taught us gets lost.

As a hook (stdin = the hook's JSON: transcript_path / agent_transcript_path, agent_id, agent_type):
  python -I harness/scripts/inbox_hook.py
By hand / backfill (one or more JSONL transcripts):
  python -I harness/scripts/inbox_hook.py --transcript FILE [FILE...] [--dry-run]
It takes the agent's FINAL report (its SubagentHandback message, else its last text), finds the sections whose heading
is one of HEADINGS (es/en, any case: "## Lecciones para mi rol", "**gbe gaps:**", "Huecos de gbe:"...) and appends
each bullet as an inbox item (status new; kb.py inbox list / triage). Idempotent (the id is a hash of source + text).
Never blocks: always exit 0, errors go to stderr; reads only the transcript's tail.
"""
import argparse, hashlib, json, os, pathlib, re, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
INBOX = ROOT / "docs" / "datos" / "inbox.jsonl"
COMPLIANCE = ROOT / ".claude" / "kb_compliance.log"   # one line per agent that skipped the rules (kb.py check sums it)

# heading regex (folded: lower case, no accents) -> kind
HEADINGS = [
    (r"lecciones|lessons? for my role|lessons? learn", "lesson"),
    (r"huecos (de|del|en) (gbe|la lib|la biblioteca|el arnes|harness)|huecos del (sdk|motor|arnes)|gbe gaps?|"
     r"gaps? (in|of) (gbe|the harness)|harness gaps?|problem(a)?s (de|en) gbe|para gbe|sdk gaps?|engine gaps?", "gap"),
    (r"bugs? (found|encontrados?)|fallos encontrados|errores encontrados", "bug"),
    (r"(for|para) (the )?(technique|techniques) book|para el libro|libro de tecnicas", "technique"),
    (r"problems? for the coordinator|para el coordinador|for the coordinator", "idea"),
]
# gbe modules (harness/common/src/gbe_<m>.c) + harness tools: the inbox's and the backlog's module names
MODULES = ("frame oam video vq tiles map vmap world view bgbuf actors gact aim pool spr list raster sfx save bank "
           "text vwf tbox menu script screen flags log rng selftest util vram gbe harness gbtest pyboy kb beads "
           "board worktree").split()


def fold(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


HEAD_LINE = re.compile(r"^\s*(?:#{1,6}\s+(?P<h1>.+?)\s*#*|\*\*(?P<h2>[^*]{3,90})\*\*\s*:?\s*(?P<rest>.*)|"
                       r"(?P<h3>[A-ZÁÉÍÓÚa-z][^.:\n]{3,70}):)\s*$")


def heading_of(line):
    """(text, rest) if line is a heading (markdown #, a bold line, or 'Something:' alone), else None."""
    m = HEAD_LINE.match(line)
    if not m:
        return None
    if m.group("h1"):
        return m.group("h1").strip(), ""
    if m.group("h2"):
        rest = (m.group("rest") or "").strip()
        if rest and not line.strip().startswith("**"):
            return None
        return m.group("h2").strip().rstrip(":"), rest
    return m.group("h3").strip(), ""


def kind_of(head):
    h = fold(head)
    for pat, kind in HEADINGS:
        if re.search(pat, h):
            return kind
    return None


# "None new: the task was only art": the section is there, the finding is not (a third of what the triage of 2026-11-02 threw away)
EMPTY_NOTE = re.compile(r"^\W*(ningun[oa]?( nuev[oa])?|nada( nuevo)?|none( new)?|n/?a|no hay (nada|huecos?|hallazgos?)"
                        r"|sin (huecos?|novedad(es)?|hallazgos?|lecciones)|no new)\b")


def extract(report):
    """[(kind, heading, bullet_text)] from a final report."""
    out, kind, head, cur = [], None, None, None
    lines = report.replace("\r\n", "\n").split("\n")

    def flush():
        if cur and kind:
            t = re.sub(r"\s+", " ", " ".join(cur)).strip()
            if len(t) > 12 and not EMPTY_NOTE.match(fold(t)):
                out.append((kind, head, t))

    infence = False
    for l in lines:
        if l.strip().startswith("```"):
            infence = not infence
            if cur is not None and kind:
                cur.append(l.strip("` ")) if l.strip("` ") else None
            continue
        h = None if infence else heading_of(l)
        is_bullet = re.match(r"^(\s{0,3})([-*•]|\d+[.)])\s+(.*)$", l)
        if h and not is_bullet:
            flush(); cur = None
            k = kind_of(h[0])
            kind, head = (k, h[0]) if k else (None, None)
            if k and h[1]:              # "**Lessons:** text on the same line"
                cur = [h[1]]
            continue
        if not kind:
            continue
        if is_bullet:
            flush(); cur = [is_bullet.group(3)]
        elif l.strip() == "":
            flush(); cur = None
        elif cur is not None:
            cur.append(l.strip())
        elif l.strip() and not l.startswith(" "):
            cur = [l.strip()]       # a paragraph item without a bullet
    flush()
    return out


def clean_lesson(text):
    """'lessons.py add --id X --text "..." --evidence "..."' -> (id, text, evidence)."""
    m = re.search(r"--id\s+['\"]?([\w.-]+)", text)
    t = re.search(r"--text\s+(['\"])(.*?)(?<!\\)\1", text)
    e = re.search(r"--evidence\s+(['\"])(.*?)(?<!\\)\1", text)
    if m and t:
        return m.group(1), t.group(2), (e.group(2) if e else "")
    return None, text, ""


PREFIX = [("frame", "frame"), ("oam", "oam"), ("vq", "vq"), ("tile", "tiles"), ("mt", "map"), ("vmap", "vmap"),
          ("world", "world"), ("view", "view"), ("bgbuf", "bgbuf"), ("act", "actors"), ("gact", "gact"),
          ("aim", "aim"), ("pool", "pool"), ("spr", "spr"), ("raster", "raster"), ("sfx", "sfx"), ("save", "save"),
          ("bank", "bank"), ("vwf", "vwf"), ("tbox", "tbox"), ("menu", "menu"), ("script", "script"),
          ("screen", "screen"), ("flag", "flags"), ("log", "log"), ("rng", "rng")]
GENERIC = {"frame", "list", "text", "log", "util", "vram", "flags", "screen", "menu", "save", "view", "world", "map",
           "gbe", "harness"}


def guess_module(text):
    """The gbe module a finding is about: 'mod:' prefix, else the most named file / API prefix / module word."""
    t = fold(text)
    m = re.match(r"^\W*`?([a-z_0-9]+)`?\s*[:(]", t)
    if m and m.group(1).removeprefix("gbe_") in MODULES:
        return m.group(1).removeprefix("gbe_")
    votes = {}
    for mod in MODULES:
        n = len(re.findall(r"(?<![\w/])(?:harness/common/src/|harness/)?(?:gbe_)?" + re.escape(mod) + r"\.(?:h|c|s|py)\b", t))
        if n:
            votes[mod] = votes.get(mod, 0) + 3 * n
    for pre, mod in PREFIX:
        n = len(re.findall(r"\b" + pre + r"_\w+", text))
        if n:
            votes[mod] = votes.get(mod, 0) + 2 * n
    for mod in MODULES:
        if mod in GENERIC:
            continue
        n = len(re.findall(r"(?<![\w/.])(?:gbe_)?" + re.escape(mod) + r"(?![\w])", t))
        if n:
            votes[mod] = votes.get(mod, 0) + n
    return max(votes, key=votes.get) if votes else None


def item_id(source, text):
    """Stable id: the agent id (the part after '#', or the whole source) + the normalised text."""
    norm = re.sub(r"\W+", " ", fold(text)).strip()
    key = source.rsplit("#", 1)[-1]
    return "ib-" + hashlib.sha1((key + "|" + norm).encode("utf-8")).hexdigest()[:10]


def load_inbox():
    if not INBOX.exists():
        return []
    out = []
    for l in INBOX.read_text(encoding="utf-8").splitlines():
        if l.strip():
            try:
                out.append(json.loads(l))
            except ValueError:
                pass
    return out


def append_items(items):
    if not items:
        return 0
    have = {i["id"] for i in load_inbox()}
    new = [i for i in items if i["id"] not in have]
    seen = set()
    new = [i for i in new if not (i["id"] in seen or seen.add(i["id"]))]
    if new:
        with open(INBOX, "a", encoding="utf-8", newline="\n") as fh:
            for i in new:
                fh.write(json.dumps(i, ensure_ascii=False) + "\n")
    return len(new)


# ---- transcripts ---------------------------------------------------------------------------------------------------
def tail_records(path, agent_id=None, max_bytes=64 << 20):
    """JSON records from the end of a JSONL transcript (newest first), reading only what it needs."""
    size = os.path.getsize(path)
    step = 1 << 20
    with open(path, "rb") as fh:
        while True:
            start = max(0, size - step)
            fh.seek(start)
            data = fh.read(size - start)
            lines = data.split(b"\n")
            if start > 0:
                lines = lines[1:]          # a cut line
            recs = []
            for l in reversed(lines):
                if not l.strip():
                    continue
                try:
                    recs.append(json.loads(l))
                except ValueError:
                    continue
            yield_ok = any(_report_of(r, agent_id) for r in recs)
            if yield_ok or start == 0 or step >= max_bytes:
                return recs
            step *= 4


def _report_of(rec, agent_id=None):
    if rec.get("type") != "assistant":
        return None
    if agent_id and rec.get("agentId") and rec.get("agentId") != agent_id:
        return None
    msg = rec.get("message") or {}
    content = msg.get("content") or []
    if isinstance(content, str):
        return content
    for c in content:
        if c.get("type") == "tool_use" and c.get("name") == "SubagentHandback":
            return (c.get("input") or {}).get("message")
    texts = [c.get("text", "") for c in content if c.get("type") == "text"]
    return "\n".join(texts) if any(t.strip() for t in texts) else None


def final_report(path, agent_id=None):
    recs = tail_records(path, agent_id)
    meta = {}
    for r in recs:
        rep = _report_of(r, agent_id)
        if rep:
            meta = {"agent_id": r.get("agentId") or agent_id or "", "agent_type": r.get("attributionAgent") or "",
                    "timestamp": r.get("timestamp", "")}
            return rep, meta
    return None, meta


def items_from_report(report, source, date):
    out = []
    for kind, head, text in extract(report):
        evidence = ""
        if kind == "lesson":
            lid, text, evidence = clean_lesson(text)
            if lid:
                evidence = (evidence + f" (proposed id {lid})").strip()
        it = {"id": item_id(source, text), "date": date, "status": "new", "kind": kind, "text": text,
              "source": source, "heading": head[:80]}
        mod = guess_module(text)
        if mod:
            it["module"] = mod
        if evidence:
            it["evidence"] = evidence
        out.append(it)
    return out


def ran_brief(path):
    """True when the transcript shows the agent RUNNING kb.py brief (a tool call), not just reading the instruction."""
    with open(path, "rb") as fh:
        for raw in fh:
            if b"kb.py brief" not in raw:
                continue
            try:
                rec = json.loads(raw)
            except ValueError:
                continue
            if rec.get("type") != "assistant":
                continue
            for c in (rec.get("message") or {}).get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_use" and "kb.py brief" in json.dumps(c.get("input")):
                    return True
    return False


def compliance(path, source, report, date, dry=False):
    """Append a warning only when the agent skipped kb.py brief; finding sections are optional."""
    probs = []
    if not ran_brief(path):
        probs.append("never ran kb.py brief")
    if probs and not dry:
        line = f"{date}\t{source}\t{'; '.join(probs)}\n"
        old = COMPLIANCE.read_text(encoding="utf-8") if COMPLIANCE.exists() else ""
        if line not in old:
            with open(COMPLIANCE, "a", encoding="utf-8", newline="\n") as fh:
                fh.write(line)
    return probs


def compliance_summary(days=7):
    """'N warnings in the last 7 days (x no brief, y no sections)' from .claude/kb_compliance.log."""
    if not COMPLIANCE.exists():
        return "no compliance warnings logged"
    since = time.strftime("%Y-%m-%d", time.localtime(time.time() - days * 86400))
    rows = [l.split("\t") for l in COMPLIANCE.read_text(encoding="utf-8").splitlines() if l.count("\t") >= 2]
    rows = [r for r in rows if r[0] >= since and "kb.py brief" in r[2]]
    nb = sum("kb.py brief" in r[2] for r in rows)
    return (f"{len(rows)} compliance warning(s) in {days} days ({nb} without kb.py brief; "
            f".claude/kb_compliance.log)")


def process(path, agent_id=None, agent_type=None, dry=False):
    rep, meta = final_report(path, agent_id)
    if not rep:
        return 0, 0
    aid = meta.get("agent_id") or agent_id or pathlib.Path(path).stem.replace("agent-", "")
    atype = agent_type or meta.get("agent_type") or "agent"
    desc = ""
    mpath = pathlib.Path(str(path)[:-len(".jsonl")] + ".meta.json") if str(path).endswith(".jsonl") else None
    if mpath and mpath.exists():       # Claude Code writes agent-<id>.meta.json beside the transcript
        try:
            m = json.loads(mpath.read_text(encoding="utf-8"))
            atype = m.get("agentType") or atype
            desc = m.get("description") or ""
        except ValueError:
            pass
    date = (meta.get("timestamp") or time.strftime("%Y-%m-%d"))[:10]
    source = f"{atype}" + (f" '{desc}'" if desc else "") + f" #{aid}"
    items = items_from_report(rep, source, date)
    try:
        probs = compliance(path, source, rep, date, dry)
        if probs:
            print(f"inbox_hook: {source}: {'; '.join(probs)}", file=sys.stderr)
    except OSError as e:
        print(f"inbox_hook: compliance: {e}", file=sys.stderr)
    if dry:
        for i in items:
            print(f"  [{i['kind']}] {i.get('module') or '-'}: {i['text'][:120]}")
        return len(items), 0
    return len(items), append_items(items)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--transcript", nargs="*")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.transcript:
        tot = new = 0
        for t in args.transcript:
            try:
                a, b = process(t, dry=args.dry_run)
                tot += a; new += b
                if a:
                    print(f"{t}: {a} finding(s), {b} new")
            except Exception as e:  # noqa: BLE001
                print(f"inbox_hook: {t}: {e}", file=sys.stderr)
        print(f"inbox_hook: {tot} finding(s), {new} new in {INBOX.relative_to(ROOT).as_posix()}")
        return
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    # Claude Code gives agent_transcript_path (read below). When a client passes the final text directly
    # (last_assistant_message) and no transcript is readable, file that text instead.
    if data.get("last_assistant_message") and not (data.get("agent_transcript_path") and
                                                   os.path.exists(data["agent_transcript_path"])):
        report = data.get("last_assistant_message")
        if report:
            date = time.strftime("%Y-%m-%d")
            source = f"{data.get('agent_type') or 'agent'} #{data.get('agent_id') or 'unknown'}"
            new = append_items(items_from_report(report, source, date))
            if new:
                print(f"inbox_hook: {new} new finding(s) in docs/datos/inbox.jsonl (kb.py inbox list)", file=sys.stderr)
        return
    path = data.get("agent_transcript_path")
    if not path and data.get("agent_id") and data.get("transcript_path"):
        # <project>/<session>.jsonl -> <project>/<session>/subagents/agent-<id>.jsonl
        t = pathlib.Path(data["transcript_path"])
        cand = t.parent / t.stem / "subagents" / f"agent-{data['agent_id']}.jsonl"
        path = str(cand) if cand.exists() else None
    path = path or data.get("transcript_path")
    if not path or not os.path.exists(path):
        return
    a, b = process(path, data.get("agent_id"), data.get("agent_type"))
    if b:
        print(f"inbox_hook: {b} new finding(s) in docs/datos/inbox.jsonl (kb.py inbox list)", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001  never block the agent
        print(f"inbox_hook: {e}", file=sys.stderr)
    sys.exit(0)
