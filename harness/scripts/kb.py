"""kb - the GBDMG harness knowledge base: ONE entry point over every place the harness keeps knowledge
(ported from the SNES harness, 2026-11-24; sources and writing conventions: docs/harness/kb.md).

Sources (kind):
  tecnica   docs/tecnicas/*.md cards (## ID · title)          lesson   docs/datos/lessons.jsonl (via lessons.py)
  study     docs/estudios/*.md sections                       api      harness/common/src/*.h (gbe.h), docs/api/*.md
  backlog   live Beads/Dolt tasks (via backlog.py)             tool     docs/guias, docs/harness, docs/normas, gbe README
  doc       docs/diseno, docs/auditorias                       game     games/*/design/*.md
  project   games/*/README.md, games/*/INFORME.md              ref      docs/ref/**, reference/pandocs/src/** (Pan Docs)
Usage (always python -I):
  kb.py brief --role R --task "..."            # start EVERY agent task with this (target: < 60 lines)
  kb.py brief --role R --task "..." --broad    # wider research brief (studies + hardware references)
  kb.py query "free text" [--kind K[,K]] [--n 5] [--full]   # ranked BM25 search (FTS5 + synonyms), Spanish or English
  kb.py card SC1                               # a technique card in full (also a lesson id or a Beads id: GB-xxxx)
  kb.py sql "SELECT ..." [--json] [--max N]    # read-only SQL: backlog, lessons, cards, inbox, symbols (no query: help)
  kb.py index [--write-tecnicas] [--force]     # rebuild the index (automatic when a source changes);
                                               # --write-tecnicas also writes docs/tecnicas/index.json
  kb.py check                                  # validate the knowledge base (exit 1 on errors)
  kb.py test                                   # run harness/scripts/kb_tests.json (expected top-3 hits)
  kb.py inbox add --kind gap|lesson|technique|bug|idea --text "..." --source "agent/game" [--module m] [--evidence ..]
  kb.py inbox list [--status new] [--kind K] [--module m] [--to lesson|backlog|tecnica|discard]
  kb.py inbox triage ID --to lesson|backlog|tecnica|discard [--ref ...]   # --to lesson links an existing id
                                               # or runs lessons.py add when the id is new;
                                               # --to backlog without --ref creates the Beads task (--area --bkind)
  kb.py inbox apply FILE                       # many decisions at once, JSONL: {"id", "to", "ref", "title", "area", ...}
  kb.py inbox status                           # the line the SessionStart hook prints
  kb.py inbox match [--apply] [-v]             # mark findings already in lessons / Beads (fuzzy)
  (the SubagentStop hook harness/scripts/inbox_hook.py files optional findings in docs/datos/inbox.jsonl and logs
   agents that skipped kb.py brief in .claude/kb_compliance.log)
Index: .cache/kb/kb.sqlite (SQLite + FTS5; self-ignored by .cache/.gitignore), rebuilt per changed file.
"""
import argparse, glob, hashlib, json, math, os, pathlib, re, sqlite3, sys, time, unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / ".cache" / "kb"
DB_PATH = CACHE_DIR / "kb.sqlite"
CACHE_VERSION = 1
TEC_DIR = ROOT / "docs" / "tecnicas"
TESTS = ROOT / "harness" / "scripts" / "kb_tests.json"
BEADS_REL = ".beads/metadata.json"   # stands for the live Beads backlog in the file list
BACKLOG_SNAPSHOT = None

sys.path.insert(0, str(ROOT / "harness" / "scripts"))
import lessons as lessons_db  # noqa: E402  (the lessons data and its role logic live there)
import backlog as backlog_db  # noqa: E402  (the live Beads backlog, normalised)
import datetime  # noqa: E402
import inbox_hook  # noqa: E402  (the findings inbox: docs/datos/inbox.jsonl)

# ---- sources -------------------------------------------------------------------------------------------------------
SOURCES = [  # (glob, kind)
    ("docs/tecnicas/*.md", "tecnica"),
    ("docs/datos/lessons.jsonl", "lesson"),
    ("docs/estudios/*.md", "study"),
    ("docs/estudios/*/*.md", "study"),
    (BEADS_REL, "backlog"),
    ("docs/guias/*.md", "tool"),
    ("docs/harness/*.md", "tool"),
    ("docs/normas/*.md", "tool"),
    ("harness/common/README.md", "tool"),
    ("docs/diseno/*.md", "doc"),
    ("docs/auditorias/*.md", "doc"),
    ("games/*/design/*.md", "game"),
    ("games/*/README.md", "project"),
    ("games/*/INFORME.md", "project"),
    ("harness/common/src/*.h", "api"),
    ("docs/api/*.md", "api"),
    ("docs/ref/**/*.md", "ref"),
    ("docs/ref/**/*.txt", "ref"),
    ("reference/pandocs/src/**/*.md", "ref"),
]
SKIP = {"docs/INDEX.md", "docs/tecnicas/index.json", "docs/api/README.md"}
SKIP_DIRS = ("games/urbe/",)   # the user's untracked work in progress: never indexed
KINDS = ["tecnica", "lesson", "study", "api", "backlog", "tool", "doc", "game", "project", "ref"]
KIND_ALIAS = {"pendiente": "backlog", "hecho": "backlog"}
KIND_WEIGHT = {"ref": 0.6, "project": 0.85, "doc": 0.9, "backlog": 0.9, "game": 0.8}

# ---- text normalisation --------------------------------------------------------------------------------------------
STOP = set("""
a al algo and are as at be but by de del el en es esta este esto for from has have how if in into is it its la las le
lo los mas más no not o of on or para pero por que qué se si sin so su sus than that the their them then there these
this to un una uno unos unas was we what when where which while who why will with y ya you your como cómo cuando donde
hay muy entre sobre con les nos me mi tu te sea son esa ese eso esas esos aqui alli ni tambien tiene ser son fue era hace hacer cada otro otra otros otras the via vs etc e i u
""".split())


def fold(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def stem(w):
    if len(w) > 4 and w.endswith("s") and not w.endswith(("ss", "us", "is")) and not w.isdigit():
        return w[:-1]
    return w


_HEX = re.compile(r"^\$?([0-9a-f]{4})h?$")
_TOK = re.compile(r"[A-Za-z0-9_$À-ɏ]+")
_CAMEL = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+")


def tokens(text):
    """Words of text: folded, stemmed, camelCase / snake_case split (whole identifier kept), $2105 / 2105h -> 2105."""
    out = []
    for raw in _TOK.findall(text):
        w = fold(raw).strip("_$")
        if not w:
            continue
        m = _HEX.match(w)
        if m and any(ch.isdigit() for ch in w):
            out.append(m.group(1)); continue
        parts = []
        if "_" in raw or (any(c.isupper() for c in raw[1:]) and any(c.islower() for c in raw)):
            for p in re.split(r"_+", raw):
                parts += [fold(x) for x in _CAMEL.findall(p)]
        if len(w) > 1 and w not in STOP:
            out.append(stem(w))
        for p in parts:
            if p != w and len(p) > 1 and p not in STOP:
                out.append(stem(p))
    return out


# Spanish / English domain words: a query word expands to its whole group. Keep groups small and specific.
SYNONYMS = [
    "adelanto lookahead lead",
    "correr corre run running",
    "formato format printf",
    "direccion direction sentido",
    "sprite sprites obj oam objeto",
    "parpadeo flicker rotar rotation rotacion",
    "paleta palette bgp obp0 obp1 colores color",
    "fondo background bg",
    "ventana window wx wy",
    "pantalla screen lcd",
    "linea line scanline scanlines lineas ly",
    "raster lyc stat",
    "compresion compression comprimir compress",
    "carga loading load cargar",
    "mapa map tilemap",
    "nivel level niveles levels",
    "camara camera",
    "scroll desplazamiento scx scy",
    "salto jump saltar",
    "gravedad gravity",
    "enemigo enemy enemies enemigos",
    "disparo shot bullet bala proyectil projectile",
    "jefe boss",
    "musica music cancion song hugedriver",
    "sonido sound sfx efecto apu canal channel",
    "fundido fade",
    "velocidad speed",
    "rendimiento performance cpu coste cost presupuesto budget",
    "lento slow ralentizacion slowdown lag",
    "memoria memory ram wram",
    "guardar save partida sram bateria battery",
    "contrasena password",
    "texto text fuente font vwf",
    "marcador hud score",
    "menu menus",
    "mando pad joypad input boton button",
    "jugador player heroe hero",
    "frame fotograma",
    "animacion animation anim",
    "pendiente todo gap hueco",
    "hecho done",
    "tile tiles tesela",
    "plataforma plataformas platform platformer",
    "colision collision",
    "prueba test tests pytest",
    "captura screenshot shot",
    "banco bank bancos banks mbc mbc5 mbc1",
    "interrupcion interrupt irq isr",
    "vblank nmi",
    "ensamblador asm assembly",
    "ciclo ciclos cycle cycles",
    "temporizador timer div tima",
    "dma oam_dma",
    "cartucho cartridge cart",
    "agente agent subagente subagent",
    "tarea task bead beads",
    "reserva claim board",
]
SYN = {}
for _g in SYNONYMS:
    _ws = [stem(fold(w)) for w in _g.split()]
    for _w in _ws:
        SYN.setdefault(_w, set()).update(_ws)


def expand(qtoks):
    """{term: weight}: the query words at 1.0, their synonyms at 0.7."""
    out = {}
    for t in qtoks:
        out[t] = max(out.get(t, 0), 1.0)
        for s in SYN.get(t, ()):
            if s != t:
                out[s] = max(out.get(s, 0), 0.7)
    return out


# ---- chunkers: each returns [(line, title, text, meta)] -------------------------------------------------------------
CARD_RE = re.compile(r"^## ([A-Z]{2,3}\d+) · (.+)$")
MD_HEAD = re.compile(r"^(#{1,4}) +(.+?)\s*#*$")


def chunk_markdown(lines, maxlevel=3):
    out, cur, title, start, stack = [], [], None, 1, []
    infence = False
    for i, l in enumerate(lines, 1):
        if l.startswith("```"):
            infence = not infence
        m = None if infence else MD_HEAD.match(l)
        if m and len(m.group(1)) <= maxlevel:
            if cur and any(x.strip() for x in cur):
                out.append((start, title or "", "\n".join(cur), {}))
            lvl = len(m.group(1))
            stack = [s for s in stack if s[0] < lvl] + [(lvl, m.group(2).strip())]
            title = " > ".join(s[1] for s in stack if s[0] > 1) or stack[-1][1]
            cur, start = [l], i
        else:
            cur.append(l)
    if cur and any(x.strip() for x in cur):
        out.append((start, title or "", "\n".join(cur), {}))
    # split very long sections into windows so BM25 lengths stay sane
    res = []
    for (s, t, txt, meta) in out:
        ls = txt.split("\n")
        if len(ls) <= 90:
            res.append((s, t, txt, meta)); continue
        for k in range(0, len(ls), 60):
            res.append((s + k, t + ("" if k == 0 else " (cont.)"), "\n".join(ls[k:k + 60]), meta))
    return res


def chunk_tecnica(lines):
    out, cur, start, cid, title = [], [], None, None, None
    for i, l in enumerate(lines, 1):
        m = CARD_RE.match(l)
        if m or (l.startswith("## ") and cid):
            if cid:
                out.append((start, f"{cid} · {title}", "\n".join(cur), {"id": cid}))
            cid, title, start, cur = (m.group(1), m.group(2), i, [l]) if m else (None, None, None, [])
        elif l.startswith("---") and cid and not l.strip("-"):
            out.append((start, f"{cid} · {title}", "\n".join(cur), {"id": cid}))
            cid, cur = None, []
        elif cid:
            cur.append(l)
    if cid:
        out.append((start, f"{cid} · {title}", "\n".join(cur), {"id": cid}))
    # the chapter intro (before the first card) as a doc chunk
    first = next((c[0] for c in out), len(lines) + 1)
    intro = "\n".join(lines[:first - 1]).strip()
    if intro:
        out.insert(0, (1, (lines[0].lstrip("# ").strip() if lines else "") + " (capítulo)", intro, {}))
    return out


def chunk_lessons(path):
    out = []
    for n, l in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not l.strip():
            continue
        try:
            o = json.loads(l)
        except ValueError:
            continue
        text = f"{o.get('text', '')}\nevidence: {o.get('evidence', '')}\ntopics: {' '.join(o.get('topics', []))}"
        out.append((n, f"lesson {o['id']}", text, {"id": o["id"], "roles": roles_of(o)}))
    return out


def chunk_backlog():
    """One chunk per live Beads item, titled 'ID [status area] title'."""
    out = []
    items = BACKLOG_SNAPSHOT if BACKLOG_SNAPSHOT is not None else backlog_db.load()
    for n, o in enumerate(items, 1):
        st = "" if o["status"] == "open" else o["status"] + " "
        title = f"{o['id']} [{st}{o['area']} P{o['priority']}] {o['title']}"
        text = "\n".join(x for x in (
            o["title"], o.get("notes") or "", o.get("evidence") or "",
            o.get("acceptance") or "", o.get("verification") or "",
            o.get("legacy") or "", o.get("done_ref") or ""
        ) if x)
        out.append((n, title, text, {"id": o["id"], "status": o["status"], "area": o["area"]}))
    return out


def chunk_pendiente(lines):
    """One chunk per top-level bullet / numbered item, titled by its section; plus each section's prose."""
    out, sec, cur, start = [], "", [], None

    def flush():
        if cur and any(x.strip() for x in cur):
            head = re.sub(r"[*`]", "", cur[0]).strip(" -0123456789.")[:70]
            out.append((start, f"{sec} :: {head}", "\n".join(cur), {}))

    for i, l in enumerate(lines, 1):
        if l.startswith("#"):
            flush(); cur = []
            sec = l.lstrip("# ").strip(); start = i; cur = [l]
        elif re.match(r"^(- |\d+\. |\*\*[a-z0-9_ ]+\*\*\s*$)", l):
            flush(); cur, start = [l], i
        else:
            if start is None:
                start = i
            cur.append(l)
    flush()
    return out


DECL = re.compile(r"^\s*(?:extern\s+)?(?:static\s+inline\s+|inline\s+)?(?:const\s+)?(?:unsigned\s+|signed\s+)?"
                  r"(?:struct\s+)?[A-Za-z_]\w*[\s\*]+\**([A-Za-z_]\w*)\s*\(([^;{]*)\)\s*[;{]")
MACRO = re.compile(r"^\s*#define\s+([A-Za-z_]\w*)\(")
EXTERN = re.compile(r"^\s*extern\s+[^;(]*?([A-Za-z_]\w*)\s*(?:\[[^\]]*\])?\s*;")
SECTION = re.compile(r"^\s*(?:/\*|//)\s*[-=]{3,}\s*(.*?)\s*[-=]*\s*(\*/)?\s*$")


def header_symbols(lines):
    """[(line, name, decl_text)] for functions, function-like macros and externs."""
    syms = []
    for i, l in enumerate(lines, 1):
        m = DECL.match(l) or MACRO.match(l)
        if m and not l.lstrip().startswith(("return", "if", "while", "else", "*", "//")):
            name = m.group(1)
            if name not in ("if", "while", "for", "switch", "sizeof", "return"):
                syms.append((i, name, l.strip()))
                continue
        m = EXTERN.match(l)
        if m:
            syms.append((i, m.group(1), l.strip()))
    return syms


def chunk_header(lines, rel):
    """Section chunks (a /* ---- title ---- block and what follows) + one small chunk per function."""
    out, syms = [], header_symbols(lines)
    bounds = [1] + [i for i, l in enumerate(lines, 1) if SECTION.match(l) and i > 1] + [len(lines) + 1]
    base = os.path.basename(rel)
    for a, b in zip(bounds, bounds[1:]):
        seg = lines[a - 1:b - 1]
        if not any(s.strip() for s in seg):
            continue
        m = SECTION.match(seg[0])
        stitle = (m.group(1).rstrip("-= ") if m and m.group(1) else "") or (
            "header" if a == 1 else seg[0].strip()[:60])
        names = [s[1] for s in syms if a <= s[0] < b and not s[2].startswith("extern") and not s[1].startswith("_")]
        title = f"{base}: {stitle[:90]}" + (f" [{', '.join(names[:6])}{'…' if len(names) > 6 else ''}]" if names else "")
        if len(seg) > 120:
            for k in range(0, len(seg), 80):
                out.append((a + k, title + ("" if k == 0 else " (cont.)"), "\n".join(seg[k:k + 80]), {"section": 1}))
        else:
            out.append((a, title, "\n".join(seg), {"section": 1}))
        for (ln, name, decl) in syms:
            if not (a <= ln < b) or decl.startswith("extern") or name.startswith("_"):
                continue
            # the function's own comment: preceding comment lines, and continuation comment lines after it
            pre, k = [], ln - 2
            while k >= a - 1 and k >= 0 and lines[k].strip().startswith(("/*", "*", "//")) and len(pre) < 6:
                pre.insert(0, lines[k]); k -= 1
            post, k = [], ln
            while k < len(lines) and len(post) < 6 and re.match(r"^\s{8,}(/\*|\*|[a-z(])", lines[k]) and \
                    not DECL.match(lines[k]):
                post.append(lines[k]); k += 1
            text = "\n".join(pre + [decl] + post) + f"\n(section: {stitle})"
            out.append((ln, f"{name}  ({base})", text, {"symbol": name, "decl": decl}))
    return out, syms


def chunk_window(lines, title, size=45):
    return [(k + 1, title, "\n".join(lines[k:k + size]), {}) for k in range(0, len(lines), size)
            if any(x.strip() for x in lines[k:k + size])]


def roles_of(lesson):
    out = []
    for r in lesson.get("roles", []):
        out += [norm_role(x) for x in r.split(",") if x.strip()]
    return out


def chunk_file(path, kind):
    rel = path.relative_to(ROOT).as_posix()
    if kind == "lesson":
        return chunk_lessons(path), []
    if kind == "backlog":
        return chunk_backlog(), []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if kind == "tecnica":
        if path.name == "README.md":
            return [(s, "Libro de técnicas: " + t, x, m) for (s, t, x, m) in chunk_markdown(lines, 2)], []
        return chunk_tecnica(lines), []
    if kind == "api" and path.suffix == ".h":
        return chunk_header(lines, rel)
    if kind == "ref":
        if path.suffix == ".txt":
            return chunk_window(lines, path.stem.replace("_", " ")), []
        pre = "pandocs: " if rel.startswith("reference/pandocs/") else "ref: "
        return [(s, pre + t, x, m) for (s, t, x, m) in chunk_markdown(lines, 3)], []
    if kind in ("project", "game"):
        game = rel.split("/")[1]
        return [(s, f"{game}: {t}", x, m) for (s, t, x, m) in chunk_markdown(lines, 3)], []
    return chunk_markdown(lines, 3), []


def source_files():
    seen, out = set(), []
    for g, kind in SOURCES:
        for p in sorted(ROOT.glob(g)):
            rel = p.relative_to(ROOT).as_posix()
            if rel in seen or rel in SKIP or rel.startswith(SKIP_DIRS) or not p.is_file():
                continue
            if rel.startswith("reference/pandocs/") and (ROOT / "docs" / "ref" / "pandocs").is_dir():
                continue     # docs/ref/pandocs is the tracked copy: index one of the two
            seen.add(rel); out.append((rel, kind))
    return out


# ---- index (SQLite + FTS5: .cache/kb/kb.sqlite) ----------------------------------------------------------------------
# chunks: every searchable piece (path, line, kind, title, text, meta JSON, len, toks = folded/stemmed tokens with the
#   title's tokens x3); chunks_fts: FTS5 over toks (candidate generation, bm25); chunks_vocab: document frequencies.
# lessons / cards / backlog / inbox / symbols: structured tables for `kb.py sql`. Rebuilt per changed source file.
SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, kind TEXT, mtime INTEGER, size INTEGER);
CREATE TABLE IF NOT EXISTS chunks(id INTEGER PRIMARY KEY, path TEXT, kind TEXT, line INTEGER, title TEXT, text TEXT,
    meta TEXT, len INTEGER, toks TEXT);
CREATE INDEX IF NOT EXISTS chunks_path ON chunks(path);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(toks, tokenize="unicode61 remove_diacritics 0 tokenchars '_$'");
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_vocab USING fts5vocab(chunks_fts, 'row');
CREATE TABLE IF NOT EXISTS symbols(name TEXT, path TEXT, line INTEGER, decl TEXT);
CREATE INDEX IF NOT EXISTS symbols_name ON symbols(name);
CREATE TABLE IF NOT EXISTS lessons(id TEXT PRIMARY KEY, text TEXT, evidence TEXT, roles TEXT, topics TEXT,
    created TEXT, auto INTEGER, line INTEGER);
CREATE TABLE IF NOT EXISTS cards(id TEXT PRIMARY KEY, title TEXT, chapter TEXT, file TEXT, line INTEGER, status TEXT,
    problem TEXT, gbe TEXT, games TEXT, tags TEXT);
CREATE TABLE IF NOT EXISTS backlog(id TEXT PRIMARY KEY, title TEXT, area TEXT, kind TEXT, status TEXT, priority INTEGER,
    source TEXT, created TEXT, done_ref TEXT, notes TEXT, size TEXT, legacy TEXT, updated TEXT);
CREATE TABLE IF NOT EXISTS inbox(id TEXT PRIMARY KEY, date TEXT, status TEXT, kind TEXT, module TEXT, text TEXT,
    source TEXT, dest TEXT, ref TEXT);
"""
STRUCT = {"docs/datos/lessons.jsonl": "lessons", BEADS_REL: "backlog", "docs/datos/inbox.jsonl": "inbox"}


def file_sig(rel):
    st = os.stat(ROOT / rel)
    return (st.st_mtime_ns, st.st_size)


def _connect():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    gi = ROOT / ".cache" / ".gitignore"
    if not gi.exists():
        gi.write_text("*\n", encoding="utf-8")
    db = sqlite3.connect(str(DB_PATH), timeout=60)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    return db


def _fill_struct(db, changed):
    """Rebuild the structured tables whose source changed (cards: when any tecnica file changed)."""
    if "docs/datos/lessons.jsonl" in changed:
        db.execute("DELETE FROM lessons")
        p = ROOT / "docs/datos/lessons.jsonl"
        for n, l in enumerate(p.read_text(encoding="utf-8").splitlines(), 1) if p.exists() else []:
            if l.strip():
                o = json.loads(l)
                db.execute("INSERT OR REPLACE INTO lessons VALUES(?,?,?,?,?,?,?,?)",
                           (o["id"], o.get("text", ""), o.get("evidence", ""), ",".join(roles_of(o)),
                            ",".join(o.get("topics", [])), o.get("created", ""), 1 if o.get("check") else 0, n))
    if BEADS_REL in changed:
        db.execute("DELETE FROM backlog")
        items = BACKLOG_SNAPSHOT if BACKLOG_SNAPSHOT is not None else backlog_db.load()
        for o in items:
            db.execute("INSERT OR REPLACE INTO backlog VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       tuple(o.get(k) for k in ("id", "title", "area", "kind", "status", "priority", "source", "created",
                                                "done_ref", "notes", "size", "legacy", "updated")))
    if "docs/datos/inbox.jsonl" in changed:
        db.execute("DELETE FROM inbox")
        for o in inbox_hook.load_inbox():
            db.execute("INSERT OR REPLACE INTO inbox VALUES(?,?,?,?,?,?,?,?,?)",
                       (o["id"], o.get("date"), o.get("status"), o.get("kind"), o.get("module"), o.get("text"),
                        o.get("source"), o.get("to"), o.get("ref")))
    if any(c.startswith("docs/tecnicas/") for c in changed):
        db.execute("DELETE FROM cards")
        for c in parse_cards():
            db.execute("INSERT OR REPLACE INTO cards VALUES(?,?,?,?,?,?,?,?,?,?)",
                       (c["id"], c["title"], c["chapter"], c["file"], c["line"], c["status"], c["problem"],
                        c.get("gbe", ""), ",".join(c.get("sources", [])), ",".join(c.get("tags", []))))


def build(db, verbose=False, force=False):
    """Bring the index up to date with the sources; returns the number of files re-read."""
    global BACKLOG_SNAPSHOT
    t0 = time.time()
    db.executescript(SCHEMA)
    # The task source is Beads/Dolt, not the legacy JSONL.  Its database is
    # outside SQLite's source-file list, so fingerprint the normalized live
    # records and use that revision to invalidate only the backlog chunks and
    # structured table.  Documentation, APIs and lessons stay warm.
    BACKLOG_SNAPSHOT = backlog_db.load()
    backlog_revision = hashlib.sha256(json.dumps(
        BACKLOG_SNAPSHOT, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    indexed_backlog_revision = db.execute(
        "SELECT value FROM meta WHERE key='beads_revision'"
    ).fetchone()
    beads_changed = force or not indexed_backlog_revision or indexed_backlog_revision[0] != backlog_revision
    ver = db.execute("SELECT value FROM meta WHERE key='version'").fetchone()
    if force or not ver or ver[0] != str(CACHE_VERSION):
        for t in ("files", "chunks", "chunks_fts", "symbols", "lessons", "cards", "backlog", "inbox"):
            db.execute(f"DELETE FROM {t}")
    files = source_files() + [(r, "struct") for r in ("docs/datos/inbox.jsonl",) if (ROOT / r).exists()]
    have = {p: (k, m, s) for p, k, m, s in db.execute("SELECT path, kind, mtime, size FROM files")}
    want = {rel for rel, _ in files}
    changed = []
    with db:
        for rel in set(have) - want:
            _drop_file(db, rel); changed.append(rel)
        for rel, kind in files:
            sig = file_sig(rel)
            if (rel in have and have[rel] == (kind, sig[0], sig[1])
                    and not (rel == BEADS_REL and beads_changed)):
                continue
            changed.append(rel)
            _drop_file(db, rel)
            db.execute("INSERT OR REPLACE INTO files VALUES(?,?,?,?)", (rel, kind, sig[0], sig[1]))
            if kind == "struct":
                continue
            chunks, syms = chunk_file(ROOT / rel, kind)
            for (line, title, text, meta) in chunks:
                tt = tokens(text) + tokens(title) * 3
                cur = db.execute("INSERT INTO chunks(path, kind, line, title, text, meta, len, toks) VALUES(?,?,?,?,?,?,?,?)",
                                 (rel, kind, line, title, text, json.dumps(meta, ensure_ascii=False), len(tt), " ".join(tt)))
                db.execute("INSERT INTO chunks_fts(rowid, toks) VALUES(?,?)", (cur.lastrowid, " ".join(tt)))
            db.executemany("INSERT INTO symbols VALUES(?,?,?,?)", [(name, rel, ln, decl) for (ln, name, decl) in syms])
        if changed:
            _fill_struct(db, set(changed))
            avg = {k: v for k, v in db.execute("SELECT kind, AVG(len) FROM chunks GROUP BY kind")}
            db.execute("INSERT OR REPLACE INTO meta VALUES('avg', ?)", (json.dumps(avg),))
            db.execute("INSERT OR REPLACE INTO meta VALUES('version', ?)", (str(CACHE_VERSION),))
            db.execute("INSERT OR REPLACE INTO meta VALUES('built', ?)", (str(time.time()),))
        if beads_changed:
            db.execute("INSERT OR REPLACE INTO meta VALUES('beads_revision', ?)", (backlog_revision,))
    if verbose:
        n = db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        nt = db.execute("SELECT COUNT(*) FROM chunks_vocab").fetchone()[0]
        ns = db.execute("SELECT COUNT(DISTINCT name) FROM symbols").fetchone()[0]
        print(f"kb index: {len(files)} files ({len(files) - len(changed)} unchanged), {n} chunks, {nt} terms, "
              f"{ns} symbols, {time.time() - t0:.2f} s -> {DB_PATH.relative_to(ROOT).as_posix()}")
    return len(changed)


def _drop_file(db, rel):
    ids = [r[0] for r in db.execute("SELECT id FROM chunks WHERE path=?", (rel,))]
    if ids:
        db.executemany("DELETE FROM chunks_fts WHERE rowid=?", [(i,) for i in ids])
        db.execute("DELETE FROM chunks WHERE path=?", (rel,))
    db.execute("DELETE FROM symbols WHERE path=?", (rel,))
    db.execute("DELETE FROM files WHERE path=?", (rel,))


class _Docs:
    """idx["docs"][did] -> (rel, kind, line, title, text, meta, len), fetched from SQLite on demand."""
    def __init__(self, db):
        self.db, self.cache = db, {}

    def __getitem__(self, did):
        d = self.cache.get(did)
        if d is None:
            r = self.db.execute("SELECT path, kind, line, title, text, meta, len FROM chunks WHERE id=?", (did,)).fetchone()
            d = (r[0], r[1], r[2], r[3], r[4], json.loads(r[5]), r[6])
            self.cache[did] = d
        return d


class _Symbols:
    def __init__(self, db):
        self.db = db

    def __contains__(self, name):
        return self.db.execute("SELECT 1 FROM symbols WHERE name=? LIMIT 1", (name,)).fetchone() is not None

    def __getitem__(self, name):
        return [tuple(r) for r in self.db.execute("SELECT path, line, decl FROM symbols WHERE name=?", (name,))]


def load(force=False, verbose=False):
    db = _connect()
    try:
        build(db, verbose=verbose, force=force)
    except sqlite3.OperationalError as e:      # a broken or foreign cache: start again
        if "locked" in str(e):
            raise
        db.close(); DB_PATH.unlink(missing_ok=True)
        db = _connect(); build(db, verbose=verbose, force=True)
    avg = json.loads((db.execute("SELECT value FROM meta WHERE key='avg'").fetchone() or ["{}"])[0])
    N = db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    return {"db": db, "docs": _Docs(db), "symbols": _Symbols(db), "avg": avg, "N": N}


# ---- search --------------------------------------------------------------------------------------------------------
CANDIDATES = 1500   # FTS5 bm25 picks the candidates; the final score is the old weighted BM25 (synonyms, coverage)


def search(idx, query, kinds=None, n=5, exclude=()):
    q = expand(tokens(query))
    db, docs = idx["db"], idx["docs"]
    if not q:
        return [], q
    terms = list(q)
    match = " OR ".join('"' + t.replace('"', '') + '"' for t in terms)
    sql = "SELECT c.id, c.path, c.kind, c.line, c.len, c.toks, c.meta FROM chunks_fts f JOIN chunks c ON c.id = f.rowid " \
          "WHERE chunks_fts MATCH ?"
    par = [match]
    if kinds:
        sql += f" AND c.kind IN ({','.join('?' * len(kinds))})"
        par += sorted(kinds)
    sql += " ORDER BY f.rank LIMIT ?"
    par.append(CANDIDATES)
    rows = db.execute(sql, par).fetchall()
    df = {t: d for t, d in db.execute(f"SELECT term, doc FROM chunks_vocab WHERE term IN ({','.join('?' * len(terms))})",
                                      terms)}
    N = idx["N"]
    k1, b = 1.2, 0.5
    qwords = [t for t in dict.fromkeys(tokens(query))]
    groups = [set([t]) | SYN.get(t, set()) for t in qwords] if len(qwords) > 1 else []
    raw = [w for w in re.findall(r"[A-Za-z_][A-Za-z0-9_\-]*", query)]
    ids = {w.upper() for w in raw if re.fullmatch(r"[A-Za-z]{1,3}-?\d+|GB-[0-9a-z.]+", w, re.I)}
    syms = {w for w in raw if w in idx["symbols"]}
    lowsyms = {w.lower() for w in raw}
    scored = []
    for did, rel, kind, line, ln, toks, meta in rows:
        tf = {}
        for t in toks.split():
            if t in q:
                tf[t] = tf.get(t, 0) + 1
        dl = ln / idx["avg"].get(kind, 1.0)
        s = 0.0
        for t, f in tf.items():
            nd = df.get(t, 1)
            idf = math.log(1 + (N - nd + 0.5) / (nd + 0.5))
            s += q[t] * idf * f * (k1 + 1) / (f + k1 * (1 - b + b * dl))
        if groups:
            hit = sum(1 for g in groups if any(t in tf for t in g))
            s *= (0.5 + 0.5 * hit / len(groups)) ** 1.5
        m = json.loads(meta) if ('"id"' in meta or '"symbol"' in meta) else {}
        if m.get("id") and m["id"].upper() in ids:
            s += 50
        if m.get("symbol") and (m["symbol"] in syms or m["symbol"].lower() in lowsyms):
            s += 20
        s *= KIND_WEIGHT.get(kind, 1.0) if not (kinds and kind in kinds and len(kinds) == 1) else 1.0
        if (rel, line) not in exclude:
            scored.append((s, did))
    scored.sort(key=lambda x: -x[0])
    return scored[:n], q


def snippet(text, q, nlines=3, width=150):
    """The nlines lines of text with the most query words (numbers break ties), in file order."""
    lines = [l for l in text.split("\n")]
    scored = []
    for i, l in enumerate(lines):
        s = l.strip()
        if not s or set(s) <= set("-=|`#* ") or (i == 0 and s.startswith("#")):
            continue
        tk = set(tokens(s))
        hit = sum(q.get(t, 0) for t in tk)
        digits = 0.3 if re.search(r"\d", s) else 0
        scored.append((hit + digits + (0.01 if i < 3 else 0), i))
    best = sorted(scored, key=lambda x: (-x[0], x[1]))[:nlines]
    out = []
    for _, i in sorted(best, key=lambda x: x[1]):
        s = re.sub(r"\s+", " ", lines[i].strip())
        out.append(s if len(s) <= width else s[:width - 1] + "…")
    return out


def fmt_hit(idx, did, q, nlines=3, score=None):
    rel, kind, line, title, text, meta, _ = idx["docs"][did]
    head = (f"[{kind}] {title}  (beads.py show {meta.get('id', '')})" if kind == "backlog"
            else f"[{kind}] {rel}:{line}  {title}")
    if score is not None:
        head += f"  ({score:.1f})"
    return [head] + ["    " + s for s in snippet(text, q, nlines)]


# ---- technique cards -----------------------------------------------------------------------------------------------
def readme_table():
    """{id: {status, chapter_short, sources}} from the README's "Todas las técnicas" table."""
    out = {}
    p = TEC_DIR / "README.md"
    for l in p.read_text(encoding="utf-8").splitlines() if p.exists() else []:
        m = re.match(r"^\| ([A-Z]{2,3}\d+) \| (.*) \| (.*) \| (.*) \| (.*) \|\s*$", l)
        if m:
            out[m.group(1)] = {"title": m.group(2).strip(), "chapter_short": m.group(3).strip(),
                               "status": m.group(4).strip(), "sources": [s.strip() for s in m.group(5).split(",")]}
    return out


FIELD = re.compile(r"^\*\*(Problema|Cómo lo resolvían|En gbe|Medido en nuestros juegos|Estado)\*\*(.*)$")
TAG_LINE = re.compile(r"^<!-- tags: (.*?) -->$")
GAMES = {}   # commercial games the studies cite: {"tag": "Name"}; tags cards that name them
TOPIC_TAGS = {  # tag: words (folded/stemmed) that, present in a card, give it the tag
    "vram": ["vram"], "oam": ["oam", "sprite"], "dma": ["dma"], "raster": ["lyc", "stat", "raster"],
    "window": ["ventana", "window"], "scroll": ["scroll", "scx", "scy"], "camera": ["camara", "camera"],
    "physics": ["gravedad", "gravity", "salto"], "audio": ["audio", "sonido", "musica", "apu", "canal"],
    "cpu": ["linea", "ciclo", "ciclos", "instrucciones"], "wram": ["wram"], "banks": ["banco", "mbc"],
    "hud": ["hud", "marcador"], "text": ["texto", "fuente", "vwf"], "asm": ["asm", "ensamblador"],
    "save": ["sram", "guardar", "guardado"], "level-design": ["nivel", "fosos"],
}


def parse_cards():
    """All technique cards: [{id, title, chapter, file, line, problem, gbe, status, status_text, tags, sources,
    estado (full text)}]."""
    table = readme_table()
    cards = []
    for p in sorted(TEC_DIR.glob("*.md")):
        if p.name == "README.md":
            continue
        lines = p.read_text(encoding="utf-8").splitlines()
        chapter = lines[0].lstrip("# ").strip() if lines else p.stem
        for (line, title, text, meta) in chunk_tecnica(lines):
            if not meta.get("id"):
                continue
            fields, curf = {}, None
            tags_manual = []
            for l in text.split("\n")[1:]:
                m = FIELD.match(l)
                mt = TAG_LINE.match(l.strip())
                if mt:
                    tags_manual += [t.strip() for t in mt.group(1).split(",") if t.strip()]
                    continue
                if m:
                    curf = m.group(1); fields[curf] = re.sub(r"^\s*·\s*", "", m.group(2)).strip()
                elif curf:
                    fields[curf] += "\n" + l
            cid = meta["id"]
            row = table.get(cid, {})
            gbe_txt = fields.get("En gbe", "")
            idents = sorted(set(re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)(?:\([^`]*\))?`", gbe_txt)))
            words = set(tokens(text))
            tags = [p.stem]
            tags += [t for t, ws in TOPIC_TAGS.items() if any(stem(w) in words for w in ws)]
            src = row.get("sources") or []
            src_files = set()
            for f in re.findall(r"(?:docs/estudios/)?([a-z0-9_]+\.md)\b", text):   # `smw.md` §7, docs/estudios/dkc.md
                if (ROOT / "docs" / "estudios" / f).exists():
                    src_files.add("docs/estudios/" + f)
            src_files = sorted(src_files)
            cards.append({
                "id": cid, "title": title.split(" · ", 1)[1], "chapter": chapter, "file": p.relative_to(ROOT).as_posix(),
                "line": line,
                "problem": _oneline(fields.get("Problema", "")),
                "gbe": _oneline(gbe_txt, 300), "gbe_identifiers": idents,
                "status": row.get("status") or _oneline(fields.get("Estado", ""), 120),
                "status_card": _oneline(fields.get("Estado", ""), 300),
                "tags": sorted(set(tags + tags_manual + [GAMES[g] .lower() for g in GAMES
                                                         if GAMES[g] in src or g in words])),
                "sources": src, "source_files": src_files,
                "has": {f: (f in fields) for f in ("Problema", "Cómo lo resolvían", "En gbe", "Estado")},
            })
    return cards


def _oneline(s, n=240):
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[:n - 1] + "…"


def write_tecnicas_json():
    cards = parse_cards()
    data = {"generated_by": "python -I harness/scripts/kb.py index --write-tecnicas",
            "note": "Generated from docs/tecnicas/*.md (cards) and the README table (status, sources): do not edit.",
            "count": len(cards),
            "cards": [{k: c[k] for k in ("id", "title", "chapter", "file", "line", "problem", "gbe",
                                         "gbe_identifiers", "status", "status_card", "tags", "sources",
                                         "source_files")} for c in cards]}
    out = TEC_DIR / "index.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT).as_posix()}: {len(cards)} cards")


# ---- commands ------------------------------------------------------------------------------------------------------
def parse_kinds(s):
    if not s:
        return None
    ks = {KIND_ALIAS.get(k.strip(), k.strip()) for k in s.split(",") if k.strip()}
    bad = ks - set(KINDS)
    if bad:
        sys.exit(f"unknown kind(s) {sorted(bad)}; kinds: {', '.join(KINDS)}")
    return ks


def cmd_query(args):
    idx = load()
    kinds = parse_kinds(args.kind)
    hits, q = search(idx, args.text, kinds, args.n)
    if not hits:
        print("no results (try other words, or --kind ref for hardware docs)"); return
    for s, did in hits:
        print("\n".join(fmt_hit(idx, did, q, 6 if args.full else 3)))


def norm_role(r):
    if not r:
        return None
    r = r.strip()
    return r[3:] if r.startswith("gb-") else r


def cmd_brief(args):
    idx = load()
    role = norm_role(args.role)
    task = args.task or ""
    out = []
    out.append(f"# kb brief  role={role or '-'}  task: {task[:100]}")
    # lessons: lessons.py's data; role filter = lessons.py query --role (plus comma-joined role strings)
    items = lessons_db.load()
    mine = [i for i in items if not role or role in roles_of(i) or "all" in roles_of(i)]
    q = expand(tokens(task))
    hits, _ = search(idx, task, {"lesson"}, 400) if task else ([], q)
    rank = {idx["docs"][d][5]["id"]: s for s, d in hits}
    for i in mine:
        i["_s"] = rank.get(i["id"], 0) + (0.5 if "all" in roles_of(i) and role else 0)
    mine.sort(key=lambda i: (-i["_s"], i.get("created", "")), reverse=False)
    nshow = args.lessons if args.lessons is not None else (15 if args.broad else 5)
    shown = mine[:nshow]
    out.append(f"\n## Lessons ({len(mine)} for role {role or 'any'}; {len(shown)} most relevant; "
               f"all: python -I harness/scripts/lessons.py query --role {role or 'R'})")
    for i in shown:
        tag = " [auto]" if i.get("check") else ""
        out.append(f"- {i['id']}{tag}: {_oneline(i['text'], 230)}")
    reads = []

    def section(name, kinds, n, nlines=2, cards_only=False):
        hs, qq = search(idx, task, kinds, n * 3 if cards_only else n)
        hs = [(s, d) for s, d in hs if s >= args.min_score]
        if hs:              # drop the tail: hits far below the section's best are noise
            hs = [(s, d) for s, d in hs if s >= 0.45 * hs[0][0]]
        if cards_only:      # the book's README / chapter intros are indexes: show the cards themselves
            hs = [(s, d) for s, d in hs if idx["docs"][d][5].get("id")][:n]
        if not hs:
            return
        out.append(f"\n## {name}")
        for s, did in hs:
            rel, kind, line, title, text, meta, _ = idx["docs"][did]
            if kind == "tecnica" and meta.get("id"):
                card = cards_by_id.get(meta["id"])
                st = f" — {card['status'][:90]}" if card else ""
                out.append(f"- {title}{st}  ({rel}:{line}; kb.py card {meta['id']})")
                if card and card["problem"]:
                    out.append(f"    {card['problem'][:200]}")
                continue
            if kind == "backlog":
                bid = meta.get("id", "")
                # The indexed line is a position in the Beads snapshot, not in a file: point at the task instead.
                out.append(f"- {title}  (beads.py show {bid})" if bid else f"- {title}")
                continue
            out.append(f"- {rel}:{line}  {title}")
            for sn in snippet(text, qq, nlines):
                out.append("    " + sn)
            if rel not in reads:
                reads.append(rel)

    cards_by_id = {c["id"]: c for c in parse_cards()} if task else {}
    # A normal brief is deliberately narrow: every emitted token remains in the agent context and is reread on every
    # later model call. `--broad` keeps the old research-oriented coverage when it is actually useful.
    ft = fold(task)
    research_roles = {"docs-writer", "game-designer"}
    hardware_roles = {"hw-reviewer"}
    study_words = ("estudio", "study", "rom", "comercial", "referencia", "zelda", "mario", "kirby", "metroid",
                   "pokemon", "tetris", "wario", "castlevania", "mega man", "megaman")
    hardware_words = ("hardware", "registro", "register", "ppu", "apu", "lcd", "lcdc", "stat", "lyc", "dma",
                      "interrup", "vblank", "hblank", "scanline", "ciclo", "cycle", "sm83", "lr35902", "wram",
                      "vram", "hram", "oam", "banco", "bank", "mbc", "timing", "timer", "pandocs", "canal")
    want_studies = args.broad or role in research_roles or any(w in ft for w in study_words)
    want_refs = args.broad or role in hardware_roles or any(w in ft for w in hardware_words)
    if task:
        section("Technique cards (docs/tecnicas)", {"tecnica"}, 3 if not args.broad else 5, cards_only=True)
        if want_studies:
            section("ROM studies (docs/estudios)", {"study"}, 2 if not args.broad else 3)
        section("Beads: pending / done (beads.py show ID)", {"backlog"},
                3 if not args.broad else 4, 1)
        mods = task_modules(task)
        if mods:
            rows = idx["db"].execute(
                f"SELECT id, area, priority, kind, title FROM backlog WHERE status IN ('open','confirmed','doing','resolved') AND area IN "
                f"({','.join('?' * len(mods))}) ORDER BY priority, id LIMIT 12", sorted(mods)).fetchall()
            tot = idx["db"].execute(f"SELECT COUNT(*) FROM backlog WHERE status IN ('open','confirmed','doing','resolved') AND area IN "
                                    f"({','.join('?' * len(mods))})", sorted(mods)).fetchone()[0]
            if rows:
                out.append(f"\n## Open Beads for {', '.join(sorted(mods))} ({len(rows)} of {tot}; all: "
                           "python -I harness/scripts/beads.py ready --json)")
                for r in rows:
                    out.append(f"- {r[0]} [{r[1]} P{r[2]} {r[3]}] {_oneline(r[4], 150)}")
        # API: functions first, one line each
        hs, qq = search(idx, task, {"api"}, 12)
        fn = [(s, d) for s, d in hs if idx["docs"][d][5].get("symbol") and s >= args.min_score]
        secs = [(s, d) for s, d in hs if idx["docs"][d][5].get("section") and s >= args.min_score]
        fn = fn[:8 if args.broad else 5]
        secs = secs[:2 if args.broad else 1]
        if fn or secs:
            out.append("\n## API gbe (harness/common/src/gbe.h; docs/api is generated from it)")
            for s, did in fn:
                rel, kind, line, title, text, meta, _ = idx["docs"][did]
                out.append(f"- {_oneline(meta['decl'], 110)}  ({rel}:{line})")
            for s, did in secs:
                rel, kind, line, title, text, meta, _ = idx["docs"][did]
                out.append(f"- section {rel}:{line}  {title[:110]}")
        section("Guides, rules, designs, games", {"tool", "doc", "game", "project"},
                5 if args.broad else 3, 1 if not args.broad else 2)
        if want_refs:
            section("Hardware reference (docs/ref, Pan Docs)", {"ref"}, 2 if args.broad else 1, 1)
    # The inbox is intentionally excluded from generic briefs: it contains raw, untriaged findings and was a frequent
    # source of unrelated context. Show it for broad research or when the task names a concrete gbe module.
    named_modules = task_modules(task)
    rel_inbox = inbox_related(task) if args.broad or named_modules else []
    if named_modules and not args.broad:
        rel_inbox = [i for i in rel_inbox if i.get("module") in named_modules]
    if rel_inbox:
        out.append("\n## Open findings in the inbox (docs/datos/inbox.jsonl; kb.py inbox triage ID --to ...)")
        for i in rel_inbox:
            out.append(inbox_line(i, 170))
    if reads and args.broad:
        out.append("\n## Open only the cited section if needed")
        out.append("- " + "\n- ".join(reads[:10]))
    out.append("\n(search more: python -I harness/scripts/kb.py query \"...\" [--kind tecnica|lesson|study|api|backlog|"
               "tool|doc|game|project|ref]; structured: kb.py sql \"SELECT ... FROM backlog|lessons|cards|inbox\")")
    print("\n".join(out))


def cmd_card(args):
    want = args.id.strip()
    for c in parse_cards():
        if c["id"].upper() == want.upper():
            p = ROOT / c["file"]
            lines = p.read_text(encoding="utf-8").splitlines()
            for (line, title, text, meta) in chunk_tecnica(lines):
                if meta.get("id") == c["id"]:
                    print(f"{c['file']}:{line}\n{text.rstrip()}")
                    return
    for i in lessons_db.load():
        if i["id"] == want:
            print(json.dumps(i, ensure_ascii=False, indent=1)); return
    # a Beads id (GB-xxxx)
    for o in backlog_db.load():
        if want.upper() in (o["id"].upper(), (o.get("legacy") or "").upper()):
            print(json.dumps(o, ensure_ascii=False, indent=1)); return
    sys.exit(f"no card, lesson or Beads id {want!r}")


def cmd_index(args):
    load(force=args.force, verbose=True)
    if args.write_tecnicas:
        write_tecnicas_json()


def task_modules(task):
    """Beads areas a task names: gbe modules -> gbe (and the module), harness tools -> harness, a game -> juego:x."""
    f = fold(task)
    mods = {m for m in inbox_hook.MODULES if re.search(r"(?<![\w/])" + re.escape(m) + r"(?![\w])", f)}
    out = set()
    for m in mods:
        if m in ("harness", "gbtest", "pyboy", "kb", "beads", "board", "worktree"):
            out.add("harness")
        else:
            out.add("gbe")
    games = ROOT / "games"
    for d in games.iterdir() if games.exists() else []:
        if d.is_dir() and d.name != "urbe" and re.search(r"(?<![\w])" + re.escape(d.name) + r"(?![\w])", f):
            out.add("juego:" + d.name)
    return out


SQL_HELP = """tables (kb.py sql "SELECT ..."; read-only):
  backlog(id, title, area, kind, status, priority, source, created, done_ref, notes, size, legacy, updated)
  lessons(id, text, evidence, roles, topics, created, auto, line)      roles/topics: comma-joined
  cards(id, title, chapter, file, line, status, problem, gbe, games, tags)
  inbox(id, date, status, kind, module, text, source, dest, ref)
  symbols(name, path, line, decl)      chunks(id, path, kind, line, title, text, meta, len, toks)
  chunks_fts (FTS5 over chunks.toks: tokens are folded+stemmed, use kb.py query for text search)
examples:
  SELECT id, priority, title FROM backlog WHERE status='open' AND area='gbe' ORDER BY priority
  SELECT id, title FROM cards WHERE status LIKE 'pendiente%'
  SELECT id, text FROM lessons WHERE ',' || roles || ',' LIKE '%,game-dev,%'
  SELECT area, COUNT(*) FROM backlog WHERE status='open' GROUP BY area ORDER BY 2 DESC"""


def cmd_sql(args):
    if not args.query:
        print(SQL_HELP); return
    q = args.query.strip().rstrip(";")
    if not re.match(r"(?is)^\s*(select|with|pragma\s+table_info)\b", q):
        sys.exit("kb.py sql: read-only, SELECT / WITH only")
    idx = load()
    db = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True, timeout=60)
    try:
        cur = db.execute(q)
    except sqlite3.Error as e:
        sys.exit(f"kb.py sql: {e}\n\n{SQL_HELP}")
    cols = [d[0] for d in cur.description or []]
    rows = cur.fetchmany(args.max + 1)
    if args.json:
        print(json.dumps([dict(zip(cols, r)) for r in rows[:args.max]], ensure_ascii=False, indent=1))
    else:
        print("\t".join(cols))
        for r in rows[:args.max]:
            print("\t".join("" if v is None else _oneline(str(v), args.width) for v in r))
    if len(rows) > args.max:
        print(f"... more rows (--max N)", file=sys.stderr)
    del idx


INBOX_LIMIT, INBOX_DAYS = 20, 2       # beyond either, the session start asks for a triage


# ---- findings inbox (docs/datos/inbox.jsonl; filled by hand and by the SubagentStop hook harness/scripts/inbox_hook.py) ------

INBOX_KINDS = ["gap", "lesson", "technique", "bug", "idea"]
TRIAGE_TO = ["lesson", "backlog", "tecnica", "discard", "pendiente", "hecho"]   # pendiente/hecho = backlog (old names)
INBOX_TO_BACKLOG_KIND = {"gap": "gap", "bug": "bug", "idea": "idea", "technique": "doc", "lesson": "doc"}


def inbox_save(items):
    tmp = inbox_hook.INBOX.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        for i in items:
            fh.write(json.dumps(i, ensure_ascii=False) + "\n")
    os.replace(tmp, inbox_hook.INBOX)


def inbox_line(i, width=150):
    mod = f" {i['module']}" if i.get("module") else ""
    to = f" -> {i.get('to')} {i.get('ref', '')}".rstrip() if i.get("status") != "new" else ""
    return f"- {i['id']} [{i['kind']}{mod}] {i['date']} {i['status']}{to}: {_oneline(i['text'], width)}  ({i['source']})"


def inbox_related(task, n=6, min_score=0.34):
    """Open (new) inbox items related to a task: shared words (with synonyms) + the modules the task names."""
    items = [i for i in inbox_hook.load_inbox() if i.get("status") == "new"]
    if not items or not task:
        return []
    q = expand(tokens(task))
    tmods = {m for m in inbox_hook.MODULES if re.search(r"(?<![\w/])" + re.escape(m) + r"(?![\w])", fold(task))}
    scored = []
    for i in items:
        it = set(tokens(i["text"]))
        hit = sum(w for t, w in q.items() if t in it)
        s = hit / max(1.0, len(set(tokens(task))))
        if i.get("module") and i["module"] in tmods:
            s += 0.5
        if s >= min_score:
            scored.append((s, i))
    scored.sort(key=lambda x: -x[0])
    return [i for _, i in scored[:n]]


def _content_tokens(text):
    return {t for t in tokens(text) if len(t) > 2 and not t.isdigit()}


def inbox_candidates():
    """(to, ref, token set) for every lesson and every pendiente/hecho entry."""
    out = []
    for l in lessons_db.load():
        out.append(("lesson", l["id"], _content_tokens(l["text"] + " " + l.get("evidence", ""))))
    for o in backlog_db.load():
        out.append(("backlog", o["id"], _content_tokens(o["title"] + " " + (o.get("notes") or ""))))
    return out


def inbox_best_match(item, cands):
    it = _content_tokens(item["text"])
    if len(it) < 4:
        return None
    best = None
    for to, ref, ct in cands:
        if not ct:
            continue
        common = len(it & ct)
        cont = common / len(it)                  # how much of the finding the entry already says
        jac = common / len(it | ct)
        s = cont * 0.8 + jac * 0.2
        if best is None or s > best[0]:
            best = (s, to, ref, common)
    return best


def bead_from_finding(i, title, area, bkind, priority):
    """A task in Beads (the live backlog) from a finding; returns its id."""
    import subprocess
    title = re.sub(r"[*`]", "", title or i["text"]).strip()[:150]
    kind = bkind or INBOX_TO_BACKLOG_KIND.get(i["kind"], "gap")
    labels = f"area:{area or i.get('module') or 'harness'},kind:{kind}"
    cmd = [sys.executable, "-I", str(ROOT / "harness/scripts/beads.py"), "create", title, "-t", "bug" if kind == "bug" else "task",
           "-p", str(priority or 3), "-l", labels, "--description", f"{i['text']}\n\nDel buzón {i['id']}: {i['source'][:90]}",
           "--acceptance", "Confirmar el hallazgo con evidencia actual y definir su prueba de cierre", "--silent"]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    m = re.search(r"(GB-[\w.]+)", r.stdout)
    bid = m.group(1) if m else ""
    if r.returncode or not bid:
        sys.exit(f"beads create failed for {i['id']}: {r.stderr.strip()[:200]} {r.stdout.strip()[:200]}")
    print(f"bead {bid} added")
    return bid


def triage_one(i, to, ref, text, title, area, bkind, priority, roles, topics):
    ref = ref or ""
    if to == "lesson":
        m = re.search(r"proposed id ([\w.-]+)", i.get("evidence", ""))
        lid = ref or (m.group(1) if m else None)
        if not lid:
            sys.exit("--to lesson needs --ref LESSON_ID (the new lesson's id)")
        if lid in {lesson["id"] for lesson in lessons_db.load()}:
            print(f"lesson {lid} already exists; linking inbox item without adding it")
        else:
            tops = topics or ([i["module"]] if i.get("module") else [])
            cmd = [sys.executable, "-I", str(ROOT / "harness/scripts/lessons.py"), "add", "--id", lid,
                   "--text", text or i["text"], "--evidence", i.get("evidence") or i["source"],
                   "--roles", *(roles or ["all"])] + (["--topics", *tops] if tops else [])
            import subprocess
            r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            sys.stdout.write(r.stdout); sys.stderr.write(r.stderr)
            if r.returncode:
                sys.exit("lessons.py add failed: the inbox item is left as it was")
        ref = lid
    to = "backlog" if to in ("pendiente", "hecho") else to
    if to == "backlog" and not ref:
        ref = bead_from_finding(i, title or text, area, bkind, priority)
    if to == "discard" and not ref:
        sys.exit("--to discard needs --ref 'the reason'")
    i.update({"status": "discarded" if to == "discard" else "triaged", "to": to, "ref": ref, "triaged": time.strftime("%Y-%m-%d")})
    print(inbox_line(i))


def cmd_inbox(args):
    items = inbox_hook.load_inbox()
    if args.icmd == "add":
        it = {"id": inbox_hook.item_id(args.source, args.text), "date": time.strftime("%Y-%m-%d"), "status": "new",
              "kind": args.kind, "text": args.text, "source": args.source}
        mod = args.module or inbox_hook.guess_module(args.text)
        if mod:
            it["module"] = mod
        if args.evidence:
            it["evidence"] = args.evidence
        n = inbox_hook.append_items([it])
        print(("added " if n else "already in the inbox: ") + it["id"])
        return
    if args.icmd == "list":
        sel = [i for i in items if (not args.status or i.get("status") == args.status)
               and (not args.kind or i["kind"] == args.kind) and (not args.module or i.get("module") == args.module)
               and (not args.to or i.get("to") == args.to)]
        for i in sel:
            print(inbox_line(i, 400 if args.full else 150))
        st = {}
        for i in items:
            st[i.get("status")] = st.get(i.get("status"), 0) + 1
        print(f"inbox: {len(sel)} shown; " + ", ".join(f"{k} {v}" for k, v in sorted(st.items())))
        return
    if args.icmd == "status":
        new = sorted((i for i in items if i.get("status") == "new"), key=lambda i: i.get("date", ""))
        if new:
            days = (datetime.date.today() - datetime.date.fromisoformat(new[0]["date"])).days
            print(f"Buzón de hallazgos: {len(new)} sin cribar, el más antiguo de hace {days} días. "
                  f"Criba con `kb.py inbox list --status new` y `inbox apply FICHERO`." if len(new) >= INBOX_LIMIT or days > INBOX_DAYS
                  else f"Buzón de hallazgos: {len(new)} sin cribar.")
        return
    if args.icmd == "apply":
        # a JSONL of decisions: {"id", "to", "ref", "text", "title", "area", "bkind", "priority", "roles", "topics"}; a bad line stops
        # nothing already done: the inbox is saved after each decision
        by = {i["id"]: i for i in items}
        done = 0
        for n, line in enumerate(open(args.file, encoding="utf-8"), 1):
            if not line.strip():
                continue
            d = json.loads(line)
            if d["id"] not in by:
                sys.exit(f"line {n}: no inbox item {d['id']}")
            triage_one(by[d["id"]], d["to"], d.get("ref"), d.get("text"), d.get("title"), d.get("area"), d.get("bkind"),
                       d.get("priority", 3), d.get("roles"), d.get("topics"))
            inbox_save(items)
            done += 1
        print(f"inbox apply: {done} decisions")
        return
    if args.icmd == "triage":
        hit = [i for i in items if i["id"] == args.id]
        if not hit:
            sys.exit(f"no inbox item {args.id}")
        i = hit[0]
        triage_one(i, args.to, args.ref, args.text, None, args.area, args.bkind, args.priority, args.roles, args.topics)
        inbox_save(items)
        print(inbox_line(i))
        return
    if args.icmd == "match":       # backfill: mark findings that pendiente / hecho / lessons already hold
        cands = inbox_candidates()
        lesson_ids = {l["id"] for l in lessons_db.load()}
        backlog_refs = {}
        for o in backlog_db.load():
            backlog_refs[o["id"].upper()] = o["id"]
            if o.get("legacy"):
                backlog_refs[o["legacy"].upper()] = o["id"]
        nnew = nmark = 0
        for i in items:
            if i.get("status") != "new":
                continue
            b = inbox_best_match(i, cands)
            # An explicit, unique backlog id in the finding is stronger evidence than fuzzy text similarity.
            # Ignore summaries naming several ids: those still require a human decision.
            text_i = i.get("text", "")
            refs = {backlog_refs[r.upper()] for r in re.findall(r"\bGB-[0-9a-z.]+\b", text_i, re.I)
                    if r.upper() in backlog_refs}
            if len(refs) == 1:
                ref = next(iter(refs))
                rid = re.escape(ref)
                explicit = (re.search(rf"(?i)(?:sigue\s+abierto\s+en|entra(?:r)?\s+en|podr[ií]a\s+entrar\s+en|"
                                      rf"ya\s+est[aá]\s+en)\s+`?{rid}`?", text_i)
                            or re.fullmatch(rf"(?s).{{0,100}}:\s*`?{rid}`?[.]?", text_i.strip())
                            or re.match(rf"^\s*`?{rid}`?\b", text_i, re.I))
                if explicit:
                    b = (1.0, "backlog", ref, 99)
            m = re.search(r"proposed id ([\w.-]+)", i.get("evidence", ""))
            if m and m.group(1) in lesson_ids:          # the agent's own lessons.py add line already went in
                b = (1.0, "lesson", m.group(1), 99)
            thr = args.threshold - (0.1 if i["kind"] == "lesson" and b and b[1] == "lesson" else 0)
            if b and b[0] >= thr and b[3] >= 4:
                nmark += 1
                if args.verbose:
                    print(f"{b[0]:.2f} {i['id']} -> {b[1]} {b[2]}: {_oneline(i['text'], 90)}")
                if args.apply:
                    i.update({"status": "triaged", "to": b[1], "ref": b[2], "triaged": time.strftime("%Y-%m-%d"),
                              "auto": f"kb.py inbox match {b[0]:.2f}"})
            else:
                nnew += 1
                if args.verbose > 1:
                    print(f"  NEW {b[0] if b else 0:.2f} {i['id']}: {_oneline(i['text'], 90)}  ~ {b[2] if b else ''}")
        if args.apply:
            inbox_save(items)
        print(f"inbox match: {nmark} already in lessons/pendiente/hecho{' (marked)' if args.apply else ''}, "
              f"{nnew} left as new")
        return


# ---- check ---------------------------------------------------------------------------------------------------------
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
PATHREF = re.compile(r"(?<![\w/.-])((?:harness|docs|games|\.claude)/[A-Za-z0-9_./*-]*[A-Za-z0-9_*])")


def check_files():
    pats = ["docs/*.md", "docs/*/*.md", "harness/common/README.md", "games/*/README.md",
            ".claude/skills/*/SKILL.md", ".claude/skills/*/*.md", ".claude/agents/*.md", "CLAUDE.md"]
    out = []
    for g in pats:
        for p in sorted(ROOT.glob(g)):
            rel = p.relative_to(ROOT).as_posix()
            if rel.startswith(("docs/ref/", "games/urbe/")):
                continue
            out.append(p)
    return out


def anchors_of(path, cache={}):
    if path in cache:
        return cache[path]
    a = set()
    try:
        for l in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^#{1,6}\s+(.*?)\s*#*$", l)
            if m:
                s = m.group(1).strip().lower()
                s = re.sub(r"[^\w\- ]", "", s, flags=re.U).replace(" ", "-")
                a.add(s)
    except Exception:
        pass
    cache[path] = a
    return a


def cmd_check(args):
    errors, warns = [], []
    # 1. broken links (file part; anchors as warnings)
    for p in check_files():
        rel = p.relative_to(ROOT).as_posix()
        text = p.read_text(encoding="utf-8", errors="replace")
        infence = False
        for n, l in enumerate(text.splitlines(), 1):
            if l.startswith("```"):
                infence = not infence
            if infence:
                continue
            for m in LINK.finditer(re.sub(r"`[^`]*`", "", l)):
                tgt = m.group(1)
                if re.match(r"^[a-z]+:", tgt) or tgt.startswith("#") and not tgt[1:]:
                    continue
                path_part, _, anchor = tgt.partition("#")
                if not path_part:
                    dest = p
                else:
                    dest = (p.parent / path_part.replace("%20", " ")).resolve()
                    if not dest.exists():
                        if "/" not in path_part and "." not in path_part:   # `t[i](h)` text, not a file link
                            warns.append(f"{rel}:{n}: link-like text -> {tgt}")
                            continue
                        errors.append(f"{rel}:{n}: broken link -> {tgt}")
                        continue
                if anchor and dest.is_file() and dest.suffix == ".md":
                    if anchor.lower() not in anchors_of(dest):
                        warns.append(f"{rel}:{n}: anchor not found -> {tgt}")
    # 2. cards: id, status, fields, duplicates, README table
    cards = parse_cards()
    seen = {}
    for c in cards:
        if c["id"] in seen:
            errors.append(f"{c['file']}:{c['line']}: duplicate card id {c['id']} (also {seen[c['id']]})")
        seen[c["id"]] = f"{c['file']}:{c['line']}"
        for f, ok in c["has"].items():
            if not ok:
                errors.append(f"{c['file']}:{c['line']}: card {c['id']} has no **{f}** field")
    for p in sorted(TEC_DIR.glob("*.md")):
        if p.name == "README.md":
            continue
        for n, l in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if l.startswith("## ") and not CARD_RE.match(l):
                errors.append(f"{p.relative_to(ROOT).as_posix()}:{n}: card heading without an id "
                              f"('## XX1 · title'): {l[:60]}")
    table = readme_table()
    for c in cards:
        if c["id"] not in table:
            errors.append(f"{c['file']}:{c['line']}: card {c['id']} missing from the README table")
    for cid in table:
        if cid not in seen:
            errors.append(f"docs/tecnicas/README.md: table row {cid} has no card")
    # 3. "pendiente" cards whose named function already exists
    idx = load()
    syms = idx["symbols"]
    for c in cards:
        st = c["status"].lower()
        if not st.startswith(("pendiente", "idea")):
            continue
        first = re.split(r"(?<=[.)])\s", c["status_card"], maxsplit=1)[0]   # the status claim, not the context after it
        named = set(re.findall(r"`([A-Za-z_]\w*)", c["status"] + " " + first))
        exist = sorted(n for n in named if n in syms)
        if exist:
            errors.append(f"{c['file']}:{c['line']}: card {c['id']} is '{c['status'][:50]}' but names existing "
                          f"API {', '.join(exist)} ({syms[exist[0]][0][0]}:{syms[exist[0]][0][1]}): update its status")
    # 4. lessons: duplicate ids, files they reference
    items = lessons_db.load()
    ids = {}
    for i in items:
        if i["id"] in ids:
            errors.append(f"docs/datos/lessons.jsonl: duplicate lesson id {i['id']}")
        ids[i["id"]] = 1
        for r in i.get("roles", []):
            if "," in r:
                warns.append(f"docs/datos/lessons.jsonl: lesson {i['id']} role {r!r} is one comma-joined string "
                             f"(lessons.py query --role does not split it)")
        for fld in ("text", "evidence"):
            for m in PATHREF.finditer(i.get(fld, "")):
                ref = m.group(1).rstrip(".")
                if "/build/" in ref or ref.endswith("/build") or "<" in ref or "NN" in ref:
                    continue
                if any(ch in ref for ch in "*?["):
                    if not glob.glob(str(ROOT / ref)):
                        errors.append(f"docs/datos/lessons.jsonl: lesson {i['id']} references {ref} (no match)")
                elif not (ROOT / ref).exists() and not _exists_loose(ref):
                    errors.append(f"docs/datos/lessons.jsonl: lesson {i['id']} references missing {ref}")
    # 5. backlog: schema, generated pendiente.md / hecho.md up to date
    bl = backlog_db.load()
    bl_src = "beads"
    for e in backlog_db.validate(bl):
        errors.append(f"{bl_src}: {e}")
    maybe = []
    # A symbol in a title is only a completion hint when the title asks for the symbol itself.  Tasks that explicitly
    # migrate/use/call an existing API, or extend behaviour around it, must not be reported as probably done (BL-206).
    existing_context = re.compile(
        r"cost|cuesta|lento|caro|barat|asm|doc|corta|falla|mantiene|"
        r"(?:usar?|usa|migr|integr|llam|call|use|with|retry|reintento|presupuesto|estado)|(?:-|=)?[>→]",
        re.IGNORECASE,
    )
    for o in bl:     # an open item whose title names a function that exists may be done already: a hint, not an error
        if o["status"] in ("open", "confirmed", "doing", "resolved"):
            ex = [n for n in re.findall(r"`([a-z][a-z0-9]*_[a-z0-9_]+)`", o["title"]) if n in syms]
            if ex and not existing_context.search(o["title"]):
                maybe.append(f"{o['id']} ({', '.join(ex[:3])})")
    if maybe:
        warns.append(f"{bl_src}: {len(maybe)} open item(s) name a function that already exists (done? "
                     f"beads.py show ID, then close): {' '.join(maybe[:25])}")
    audit_errors, audit_warnings = backlog_db.audit(bl)
    errors.extend(f"{bl_src}: {e}" for e in audit_errors)
    warns.extend(f"{bl_src}: {w}" for w in audit_warnings)
    # 6. inbox and agent compliance (the SubagentStop hook writes .claude/kb_compliance.log)
    inbox = inbox_hook.load_inbox()
    new = [i for i in inbox if i.get("status") == "new"]
    old = [i for i in new if i.get("date", "9999") < time.strftime("%Y-%m-%d", time.localtime(time.time() - 2 * 86400))]
    tec = [i for i in inbox if i.get("to") == "tecnica" and not i.get("done")]
    if old:
        warns.insert(0, f"docs/datos/inbox.jsonl: {len(old)} finding(s) still 'new' after 2 days: "
                        f"python -I harness/scripts/kb.py inbox list --status new, then inbox triage ID --to ...")
    comp = inbox_hook.compliance_summary()
    print(f"inbox: {len(new)} new (untriaged), {len(tec)} for the technique writer (inbox list --to tecnica); "
          f"backlog: {sum(o['status'] in ('open', 'confirmed', 'doing', 'resolved') for o in bl)} pending; agents: {comp}")
    for w in warns[: args.max_warn]:
        print("warn:", w)
    if len(warns) > args.max_warn:
        print(f"warn: ... {len(warns) - args.max_warn} more warnings (--max-warn N)")
    for e in errors:
        print("ERROR:", e)
    print(f"kb check: {len(errors)} error(s), {len(warns)} warning(s)")
    sys.exit(1 if errors else 0)


def _exists_loose(ref):
    """A path written without its extension or as a prefix (games/faro/res/maps) still counts."""
    p = ROOT / ref
    return bool(glob.glob(str(p) + ".*")) or bool(glob.glob(str(p) + "*"))


# ---- test ----------------------------------------------------------------------------------------------------------
def cmd_test(args):
    cases = json.loads(TESTS.read_text(encoding="utf-8"))["cases"]
    if not (ROOT / "reference" / "pandocs").exists():
        cases = [c for c in cases if "pandocs" not in " ".join(c["expect"])]   # reference/ is local-only
    idx = load()
    ok1 = ok3 = 0
    for c in cases:
        hits, q = search(idx, c["q"], parse_kinds(c.get("kind")), 3)
        got = []
        for s, did in hits:
            rel, kind, line, title, text, meta, _ = idx["docs"][did]
            got.append(f"{rel}:{line} {title}")
        pos = next((k for k, g in enumerate(got) if any(re.search(e, g) for e in c["expect"])), None)
        ok3 += pos is not None
        ok1 += pos == 0
        mark = "ok " if pos is not None else "MISS"
        print(f"{mark} [{'-' if pos is None else pos + 1}] {c['q']!r}  expect {c['expect']}")
        if pos is None or args.verbose:
            for g in got:
                print("        ", g[:120])
    n = len(cases)
    print(f"kb test: top-1 {ok1}/{n} ({100 * ok1 / n:.0f} %), top-3 {ok3}/{n} ({100 * ok3 / n:.0f} %)")
    sys.exit(0 if ok3 == n else 1)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("query"); q.add_argument("text"); q.add_argument("--kind"); q.add_argument("--n", type=int, default=5)
    q.add_argument("--full", action="store_true", help="6 snippet lines instead of 3")
    b = sub.add_parser("brief"); b.add_argument("--role"); b.add_argument("--task", default="")
    b.add_argument("--lessons", type=int, help="lessons to show (default: 5; --broad: 15)")
    b.add_argument("--min-score", type=float, default=2.5)
    b.add_argument("--broad", action="store_true", help="include wider studies/references and more results")
    c = sub.add_parser("card"); c.add_argument("id")
    i = sub.add_parser("index"); i.add_argument("--write-tecnicas", action="store_true"); i.add_argument("--force", action="store_true")
    k = sub.add_parser("check"); k.add_argument("--max-warn", type=int, default=20)
    t = sub.add_parser("test"); t.add_argument("-v", "--verbose", action="store_true")
    ib = sub.add_parser("inbox", help="findings inbox: add | list | triage | match")
    isub = ib.add_subparsers(dest="icmd", required=True)
    x = isub.add_parser("add"); x.add_argument("--kind", required=True, choices=INBOX_KINDS)
    x.add_argument("--text", required=True); x.add_argument("--source", required=True)
    x.add_argument("--module"); x.add_argument("--evidence")
    x = isub.add_parser("list"); x.add_argument("--status"); x.add_argument("--kind"); x.add_argument("--module")
    x.add_argument("--to", help="where triaged findings went (lesson, backlog, tecnica, discard)")
    x.add_argument("--full", action="store_true")
    isub.add_parser("status", help="one line for a session start: how many findings wait, and since when")
    x = isub.add_parser("apply", help="a JSONL file of triage decisions"); x.add_argument("file")
    x = isub.add_parser("triage"); x.add_argument("id"); x.add_argument("--to", required=True, choices=TRIAGE_TO)
    x.add_argument("--ref", help="where it went: lesson id, backlog id (none = a new item), card id; discard: the reason")
    x.add_argument("--text", help="--to lesson: the lesson text (default: the finding's)")
    x.add_argument("--roles", nargs="+"); x.add_argument("--topics", nargs="+")
    x.add_argument("--area", help="--to backlog: the area (default: the finding's module, else harness)")
    x.add_argument("--bkind", choices=backlog_db.KINDS, help="--to backlog: the item kind")
    x.add_argument("--priority", type=int, default=2, choices=(1, 2, 3))
    x = isub.add_parser("match", help="mark findings already in lessons / the backlog (fuzzy)")
    x.add_argument("--apply", action="store_true"); x.add_argument("--threshold", type=float, default=0.6)
    x.add_argument("-v", "--verbose", action="count", default=0)
    x = sub.add_parser("sql", help="read-only SQL over the index (no query: the tables)")
    x.add_argument("query", nargs="?"); x.add_argument("--max", type=int, default=200)
    x.add_argument("--width", type=int, default=160); x.add_argument("--json", action="store_true")
    args = ap.parse_args()
    {"query": cmd_query, "brief": cmd_brief, "card": cmd_card, "index": cmd_index, "check": cmd_check,
     "test": cmd_test, "inbox": cmd_inbox, "sql": cmd_sql}[args.cmd](args)


if __name__ == "__main__":
    main()
