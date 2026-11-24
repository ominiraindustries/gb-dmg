"""Run a Game Boy ROM headless in SameBoy (accuracy sign-off runner), with the same interface as gbrun.py.

SameBoy is the most accurate Game Boy emulator we have (it passes the whole Mooneye acceptance suite, dmg-acid2 and
the timing ROMs). sbrun drives the SameBoy core through harness/sameboy/sbheadless.c, a small C driver that sbrun
builds on first use against tools/sameboy/src (gcc from MSYS2/WinLibs). Tiers: PyBoy for logic tests and bots,
gbrun (Mesen 2) for daily timing checks, sbrun for the sign-off before something is called done
(docs/guias/pruebas.md).

Usage:
  python -I harness/sbrun.py hello [options]          # a game name = games/<name>/build/<name>.gb
  python -I harness/sbrun.py path/to/rom.gb [options]

Options (same meaning as gbrun.py):
  --frames N  --shot F[,F]  --input SPEC  --dump SPEC  --watch LOC --every N  --check SPEC  --check-at "F:SPEC;.."
  --expect "LOC OP V@F1-F2"  --nonblank  --golden DIR [--update-golden]  --ram zeros|ones|random  --boot
  --model dmg|cgb|sgb  --sram-in FILE|fresh  --sram-out FILE  --out DIR (default <rom dir>/sameboy)  --timeout S
SameBoy-only:
  --regs "REG OP V,..."  checks on CPU registers at the last frame (a f b c d e h l af bc de hl sp pc),
                         e.g. the Mooneye pass signature "b==3,c==5,d==8,e==13,h==21,l==34"
  --rebuild              rebuild the driver (after updating tools/sameboy)

Not available here (vs gbrun): --mesen (n/a). Model dmg = DMG-B with SameBoy's own open-source boot ROM
(tools/sameboy/bin/dmg_boot.bin); frame 1 is the first whole frame after it unmaps, as in gbrun and PyBoy.
Exit 0 = all checks passed, 1 = a check failed, 2 = SameBoy produced no result, 3 = bad arguments.
"""
import argparse, json, os, pathlib, re, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gbrun  # noqa: E402  (parsers, symbols, golden compare: one implementation for both runners)
from gbrun import BadArgs, parse_check, parse_input, parse_loc, num  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
SB = ROOT / "tools" / "sameboy"
DRIVER_SRC = ROOT / "harness" / "sameboy"
DRIVER = SB / "build" / "sbheadless.exe"
BUTTON_BITS = {"right": 0, "left": 1, "up": 2, "down": 3, "a": 4, "b": 5, "select": 6, "start": 7}
REGS = ("af", "bc", "de", "hl", "sp", "pc")
REG8 = {"a": ("af", 8), "f": ("af", 0), "b": ("bc", 8), "c": ("bc", 0), "d": ("de", 8), "e": ("de", 0),
        "h": ("hl", 8), "l": ("hl", 0)}


def die(msg):
    print("ERROR:", msg, file=sys.stderr)
    sys.exit(3)


def core_dir():
    found = sorted(p for p in (SB / "src").glob("SameBoy-*") if (p / "Core" / "gb.c").exists()) if (SB / "src").exists() else []
    return found[-1] if found else None


def build_driver(force=False):
    """Compile the SameBoy core + sbheadless.c into tools/sameboy/build (once; ~30 s)."""
    srcs = [DRIVER_SRC / "sbheadless.c", DRIVER_SRC / "sb_compat.c"]
    if DRIVER.exists() and not force and all(DRIVER.stat().st_mtime >= s.stat().st_mtime for s in srcs):
        return DRIVER
    core = core_dir()
    if not core:
        print("FAIL: SameBoy source not found in tools/sameboy/src (docs/guias/pruebas.md, 'Instalar SameBoy')")
        sys.exit(2)
    obj = SB / "build" / "obj"
    obj.mkdir(parents=True, exist_ok=True)
    flags = ["-std=gnu11", "-O2", "-D_GNU_SOURCE", "-DGB_INTERNAL", "-DNDEBUG", "-D_USE_MATH_DEFINES", "-w",
             f"-DGB_VERSION=\"{core.name.split('-', 1)[1]}\"", "-DGB_COPYRIGHT_YEAR=\"2026\"", f"-I{core}",
             "-include", str(DRIVER_SRC / "sb_compat.h")]
    objs = []
    for c in sorted((core / "Core").glob("*.c")) + srcs:
        o = obj / (c.stem + ".o")
        if force or not o.exists() or o.stat().st_mtime < c.stat().st_mtime:
            p = subprocess.run(["gcc", *flags, "-c", str(c), "-o", str(o)], capture_output=True, text=True)
            if p.returncode:
                print(f"FAIL: building the SameBoy driver ({c.name}):\n{p.stderr[-1500:]}")
                sys.exit(2)
        objs.append(str(o))
    p = subprocess.run(["gcc", "-o", str(DRIVER), *objs, "-lm"], capture_output=True, text=True)
    if p.returncode:
        print(f"FAIL: linking the SameBoy driver:\n{p.stderr[-1500:]}")
        sys.exit(2)
    return DRIVER


def parse_regs(spec):
    out = []
    for part in filter(None, (p.strip() for p in (spec or "").split(","))):
        m = re.match(r"^([a-z]{1,2})\s*(==|!=|<=|>=|<|>)\s*(-?(?:0x[0-9a-fA-F]+|\d+))$", part.lower())
        if not m or (m.group(1) not in REGS and m.group(1) not in REG8):
            raise BadArgs(f"bad --regs {part!r} (REG OP VALUE, REG in a f b c d e h l {' '.join(REGS)})")
        out.append((m.group(1), m.group(2), num(m.group(3)), part))
    return out


def build_plan(a, out):
    """argparse namespace -> (plan lines, check specs). Raises BadArgs before SameBoy starts."""
    shots = sorted({int(s) for s in a.shot.split(",")}) if a.shot else [a.frames]
    if any(not 1 <= s <= a.frames for s in shots):
        raise BadArgs(f"--shot frames must be in 1..{a.frames}")
    inputs = parse_input(a.input, a.frames)
    checks = [parse_check(c) for c in filter(None, (a.check or "").split(","))]
    check_at = {}
    for part in filter(None, (p.strip() for p in (a.check_at or "").split(";"))):
        f, _, specs = part.partition(":")
        if not f.strip().isdigit() or not 1 <= int(f) <= a.frames:
            raise BadArgs(f"bad --check-at frame in {part!r}")
        check_at.setdefault(int(f), []).extend(parse_check(c) for c in specs.split(",") if c.strip())
    expects = []
    for part in filter(None, (p.strip() for p in (a.expect or "").split(","))):
        spec, _, rng = part.rpartition("@")
        m = re.match(r"^(\d+)(?:-(\d+))?$", rng.strip())
        if not spec or not m:
            raise BadArgs(f"bad --expect {part!r} (expected LOC OP VALUE@F1-F2)")
        f1, f2 = int(m.group(1)), int(m.group(2) or m.group(1))
        if not 1 <= f1 <= f2 <= a.frames:
            raise BadArgs(f"--expect range {rng} outside 1..{a.frames}")
        expects.append((parse_check(spec), f1, f2, part))
    watches = [parse_loc(w) for w in filter(None, (a.watch or "").split(","))]
    regs = parse_regs(a.regs)
    dumps, seen = [], {}
    for d in filter(None, (a.dump or "").split(",")):
        p = d.strip().split(":")
        if p[0] not in gbrun.MEM or len(p) not in (1, 3):
            raise BadArgs(f"bad --dump {d!r} (name[:start:len], names {sorted(gbrun.MEM)})")
        start, ln = (num(p[1]), num(p[2])) if len(p) == 3 else (0, -1)
        seen[p[0]] = seen.get(p[0], 0) + 1
        dumps.append((p[0] if seen[p[0]] == 1 else f"{p[0]}_{seen[p[0]]}", p[0], start, ln))
    if a.sram_in and a.sram_in != "fresh" and not pathlib.Path(a.sram_in).exists():
        raise BadArgs(f"--sram-in {a.sram_in} not found")
    if a.every < 1:
        raise BadArgs("--every must be >= 1")

    plan, last = [], 0
    for f in range(1, a.frames + 1):          # joypad mask per frame, emitted only when it changes
        mask = 0
        for f1, f2, btns in inputs:
            if f1 <= f <= f2:
                for b in btns:
                    mask |= 1 << BUTTON_BITS[b]
        if mask != last or (f == 1 and mask):
            plan.append(f"K {f} {mask}")
            last = mask
    plan += [f"S {s}" for s in shots]
    reads = set()
    for mem, addr, width, *_ in checks:
        reads.add((a.frames, mem, addr, width))
    for f, lst in check_at.items():
        reads.update((f, c[0], c[1], c[2]) for c in lst)
    for (mem, addr, width, *_), f1, f2, _ in expects:
        reads.update((f, mem, addr, width) for f in range(f1, f2 + 1))
    wframes = sorted({f for f in range(a.every, a.frames + 1, a.every)} | {a.frames}) if watches else []
    for f in wframes:
        reads.update((f, m, ad, w) for m, ad, w, _ in watches)
    plan += [f"R {f} {m} {ad} {w}" for f, m, ad, w in sorted(reads)]
    plan += [f"D {a.frames} {name} {start} {ln} {fname}" for fname, name, start, ln in dumps]
    if a.sram_in:
        plan.append("I sram " + ("-" if a.sram_in == "fresh" else str(pathlib.Path(a.sram_in).resolve())))
    if a.sram_out:
        plan.append("O sram " + str(pathlib.Path(a.sram_out).resolve()))
    spec = {"checks": checks, "check_at": check_at, "expects": expects, "watches": watches, "wframes": wframes,
            "regs": regs}
    return plan, spec


OPS = {"==": lambda x, y: x == y, "~=": lambda x, y: x != y, "!=": lambda x, y: x != y, "<=": lambda x, y: x <= y,
       ">=": lambda x, y: x >= y, "<": lambda x, y: x < y, ">": lambda x, y: x > y}


def evaluate(spec, stdout, frames):
    """Driver stdout -> result dict in gbrun's result.json shape (plus 'regs')."""
    mem = {}
    end = None
    for line in stdout.splitlines():
        p = line.split()
        if p and p[0] == "R" and len(p) == 5:
            mem[(int(p[1]), p[2], int(p[3]))] = bytes.fromhex(p[4]) if "-" not in p[4] else None
        elif p and p[0] == "END":
            end = p
    if end is None:
        return None

    def value(f, m, addr, width):
        b = mem.get((f, m, addr))
        return None if b is None or len(b) < width else (b[0] | (b[1] << 8) if width == 2 else b[0])

    data = {"frames": int(end[1]), "boot_frames": int(end[2]), "console": "SameBoy", "sram_size": int(end[3]),
            "checks": [], "expects": [], "ok": True}
    regs16 = {r: int(v, 16) for r, v in zip(REGS, end[4:10])}
    data["regs"] = {r: f"0x{v:04x}" for r, v in regs16.items()}

    def check(c, f, tag_frame):
        m, addr, width, val, src, op = c
        v = value(f, m, addr, width)
        ok = v is not None and OPS[op](v, val)
        data["ok"] &= ok
        d = {"check": src, "value": -1 if v is None else v, "pass": ok}
        if tag_frame:
            d["frame"] = f
        data["checks"].append(d)

    for f, lst in sorted(spec["check_at"].items()):
        for c in lst:
            check(c, f, True)
    for c in spec["checks"]:
        check(c, frames, False)
    for (m, addr, width, val, _, op), f1, f2, src in spec["expects"]:
        vals = [(f, value(f, m, addr, width)) for f in range(f1, f2 + 1)]
        vs = [v for _, v in vals if v is not None]
        fail = next(((f, v) for f, v in vals if v is None or not OPS[op](v, val)), None)
        ok = fail is None and bool(vs)
        data["ok"] &= ok
        data["expects"].append({"expect": src, "samples": len(vs), "min": min(vs) if vs else None,
                                "max": max(vs) if vs else None, "pass": ok,
                                "first_fail_frame": fail[0] if fail else None,
                                "first_fail_value": fail[1] if fail else None})
    for reg, op, val, src in spec["regs"]:
        r, sh = REG8.get(reg, (reg, None))
        v = regs16[r] if sh is None else (regs16[r] >> sh) & 0xFF
        ok = OPS[op](v, val)
        data["ok"] &= ok
        data["checks"].append({"check": "reg " + src, "value": v, "pass": ok})
    if spec["watches"]:
        rows = ["frame," + ",".join(w[3] for w in spec["watches"])]
        for f in spec["wframes"]:
            rows.append(",".join([str(f)] + [str(value(f, m, ad, w)) for m, ad, w, _ in spec["watches"]]))
        data["_watch_csv"] = "\n".join(rows) + "\n"
    return data


# SameBoy's grey palette (00 55 AA FF) -> Mesen's (00 6B B5 FF): a diff between the runners is then an emulation (or
# frame) difference, not a palette one. sbrun shot N is the image the LCD finished at the end of frame N; gbrun's
# shot N is the previous one (sbrun N == gbrun N+1, measured on hello), so each runner keeps its own goldens.
SHADES = bytes.maketrans(bytes([0x00, 0x55, 0xAA, 0xFF]), bytes([0x00, 0x6B, 0xB5, 0xFF]))


def remap_shades(out):
    for raw in out.glob("shot_*.rgb"):
        raw.write_bytes(raw.read_bytes().translate(SHADES))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rom")
    ap.add_argument("--frames", type=int, default=120)
    ap.add_argument("--shot"); ap.add_argument("--input"); ap.add_argument("--dump")
    ap.add_argument("--watch"); ap.add_argument("--every", type=int, default=60)
    ap.add_argument("--check"); ap.add_argument("--check-at"); ap.add_argument("--expect")
    ap.add_argument("--regs")
    ap.add_argument("--nonblank", action="store_true")
    ap.add_argument("--golden"); ap.add_argument("--update-golden", action="store_true")
    ap.add_argument("--ram", choices=["zeros", "ones", "random"], default="zeros")
    ap.add_argument("--model", choices=["cgb", "dmg", "sgb"], default="dmg")
    ap.add_argument("--boot", action="store_true")
    ap.add_argument("--sram-in"); ap.add_argument("--sram-out")
    ap.add_argument("--out"); ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--timeout", type=int, default=int(os.environ.get("SBRUN_TIMEOUT") or 120))
    a = ap.parse_args(argv)
    if a.frames < 1:
        die("--frames must be >= 1")
    rom = gbrun.resolve_rom(a.rom)
    if not rom.exists():
        die(f"{rom} not found")
    gbrun.SYMS.clear()
    gbrun.load_syms(rom)
    out = pathlib.Path(a.out).resolve() if a.out else rom.parent / "sameboy"
    try:
        plan, spec = build_plan(a, out)
    except BadArgs as e:
        die(str(e))
    driver = build_driver(a.rebuild)
    boot = SB / "bin" / {"dmg": "dmg_boot.bin", "cgb": "cgb_boot.bin", "sgb": "sgb_boot.bin"}[a.model]
    if not boot.exists():
        print(f"FAIL: boot ROM {boot} missing (unzip the SameBoy release into tools/sameboy/bin)")
        sys.exit(2)
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*"):
        if f.suffix in (".png", ".bin", ".json", ".csv", ".rgb", ".plan"):
            f.unlink()
    if a.sram_out:
        pathlib.Path(a.sram_out).resolve().parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.sram_out).unlink(missing_ok=True)
    planf = out / "_run.plan"
    planf.write_text("\n".join(plan) + "\n", encoding="utf-8")
    cmd = [str(driver), str(rom), str(boot), str(planf), str(out), str(a.frames), a.model, a.ram,
           "1" if a.boot else "0"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=a.timeout)
    except subprocess.TimeoutExpired:
        print(f"FAIL: SameBoy did not finish in {a.timeout} s")
        sys.exit(2)
    data = evaluate(spec, p.stdout, a.frames) if p.returncode == 0 else None
    if data is None:
        print(f"FAIL: SameBoy produced no result (exit {p.returncode}): {p.stderr[-1500:]}")
        sys.exit(2)
    csv = data.pop("_watch_csv", None)
    if csv:
        (out / "watch.csv").write_text(csv, encoding="utf-8")
    remap_shades(out)
    gbrun.rgb_to_png(out)
    if a.nonblank:
        from PIL import Image
        blank = [f.name for f in sorted(out.glob("shot_*.png"))
                 if len(Image.open(f).convert("RGB").getcolors(1 << 16) or [0, 0]) <= 1]
        data["blank_shots"] = blank
        if blank:
            data["ok"] = False
            print("FAIL: solid-colour screenshots:", ", ".join(blank))
    if (a.sram_in or a.sram_out) and not data.get("sram_size"):
        data["ok"] = False
        print("FAIL: --sram-in/--sram-out: the cartridge has no RAM (header $0149 = 0)")
    if a.golden:
        gbrun.golden_compare(out, pathlib.Path(a.golden).resolve(), a.update_golden, data)
    for c in data["checks"]:
        if not c["pass"]:
            print(f"FAIL: check {c['check']}" + (f" at frame {c['frame']}" if "frame" in c else "") + f" (value {c['value']})")
    for e in data["expects"]:
        if not e["pass"]:
            print(f"FAIL: expect {e['expect']}: first failure frame {e['first_fail_frame']} "
                  f"(value {e['first_fail_value']}), min {e['min']} max {e['max']} over {e['samples']} frames")
    data["files"] = sorted(f.name for f in out.iterdir() if f.suffix in (".png", ".bin", ".csv"))
    (out / "result.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in data.items() if k != "files"}, indent=1))
    print("out:", out)
    sys.exit(0 if data["ok"] else 1)


if __name__ == "__main__":
    main()
