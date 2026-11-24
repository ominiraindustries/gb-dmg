"""Run a Game Boy ROM headless in Mesen 2 (accuracy runner) and collect screenshots / memory / checks.

PyBoy (harness/gbtest.py) is the fast test driver: pytest, bots, profiler, thousands of frames.
gbrun is the accuracy check: Mesen 2 passes the timing test ROMs PyBoy does not (mid-frame STAT/LYC
effects, OAM DMA timing, VRAM access in mode 3, APU edge cases). Use it to confirm a raster split,
a mid-frame palette change or a VBlank-budget question before trusting a PyBoy result
(docs/guias/pruebas.md).

Usage:
  python -I harness/gbrun.py games/hello/build/hello.gb [options]
  python -I harness/gbrun.py hello [options]          # a game name = games/<name>/build/<name>.gb

Options:
  --frames N            total frames to run (default 120)
  --shot F[,F...]       frames to screenshot (default: the last frame); each F in 1..--frames
  --input SPEC          joypad script, ';'-separated "F[-F2]:btn+btn", e.g. "30-40:start;60-90:right+a"
                        buttons: a b start select up down left right
  --dump SPEC[,SPEC]    memory dumps at the last frame: name[:start:len] (start/len hex 0x.. or decimal)
                        names: wram vram oam hram sram rom bus (bus = the CPU address space $0000-$FFFF)
  --watch LOC[,LOC]     sample values every --every N frames (default 60) into watch.csv
  --check SPEC[,SPEC]   checks at the last frame: [mem:]loc[.w] OP value, OP in == != <= >= < >
                        loc = a number (CPU address for bus, offset otherwise) or a symbol of <rom>.noi
                        (GBDK: 'DEF _player_x 0xC0A2'; the leading _ is optional) or <rom>.sym (rgbds
                        'bb:aaaa name'), with an optional +/-offset; .w = 16 bits little-endian.
                        e.g.  max_frame_lines<120  vram_late==0  bus:0xFF40==0x91  hram:0==0x3E
  --check-at "F:SPEC[,SPEC];F2:..."   the same checks at intermediate frames of the same run
  --expect "LOC OP VALUE@F1-F2[,...]" sampled EVERY frame in [F1,F2]; reports first failure, min, max
  --nonblank            fail if any screenshot is one solid colour (LCD off, fade stuck...)
  --golden DIR          compare each shot with DIR/shot_NNNN.png (pixel exact; a missing reference fails)
  --update-golden       write/rewrite the references in DIR (the only way to create them)
  --ram zeros|ones|random   power-on WRAM/HRAM/VRAM state (default zeros, deterministic; real DMG = random)
  --boot                count frames from power-on: frame 1 is the first frame of Mesen's built-in boot ROM
                        (~84 frames of logo on DMG). Default: frame 1 is the first whole frame after the boot
                        ROM unmaps itself, the same frame 1 as PyBoy (which runs no boot ROM)
  --model dmg|cgb|sgb   console (default dmg: Mesen's own setting may favour GBC; it is always forced)
  --sram-in FILE|fresh  cartridge RAM before frame 1 (FILE's bytes, the rest 0xFF; fresh = all 0xFF)
  --sram-out FILE       write the whole cartridge RAM at the last frame (feed it to --sram-in: power cycle)
  --out DIR             output dir (default: <rom dir>/mesen)
  --timeout S           seconds before Mesen is killed (default GBRUN_TIMEOUT, else 60)
  --mesen PATH          Mesen.exe (default GBRUN_MESEN, else tools/mesen/Mesen.exe, else the SNES workspace copy)

Writes DIR/shot_NNNN.png (160x144, the 4 DMG shades as Mesen's grey palette), DIR/<name>.bin,
DIR/watch.csv, DIR/result.json. Exit 0 = all checks passed, 1 = a check failed, 2 = Mesen produced
no result, 3 = bad arguments (reported before Mesen starts).
"""
import argparse, contextlib, json, os, pathlib, re, subprocess, sys, tempfile, textwrap, time

ROOT = pathlib.Path(__file__).resolve().parents[1]
MESEN_CANDIDATES = [ROOT / "tools" / "mesen" / "Mesen.exe",
                    pathlib.Path.home() / "Desktop" / "SNES" / "tools" / "mesen" / "Mesen.exe"]
# Same lock as the SNES snesrun: Mesen's Documents/Mesen2 home is shared by both workspaces.
MESEN_LOCK = pathlib.Path(tempfile.gettempdir()) / "snuts_mesen_testrunner.lock"
MEM = {"wram": "gbWorkRam", "vram": "gbVideoRam", "oam": "gbSpriteRam", "hram": "gbHighRam",
       "sram": "gbCartRam", "rom": "gbPrgRom", "bus": "gameboyMemory"}
BUTTONS = {"a", "b", "start", "select", "up", "down", "left", "right"}
OPS = ("==", "!=", "<=", ">=", "<", ">")
MODELS = {"dmg": "Gameboy", "cgb": "GameboyColor", "sgb": "SuperGameboy"}
SYMS = {}


class BadArgs(Exception):
    pass


def die(msg):
    print("ERROR:", msg, file=sys.stderr)
    sys.exit(3)


def load_syms(rom):
    """<rom>.noi (GBDK linker) and/or <rom>.sym (rgbds / -debug) -> SYMS[name] = CPU address."""
    noi, sym = rom.with_suffix(".noi"), rom.with_suffix(".sym")
    if noi.exists():
        for line in noi.read_text(errors="replace").splitlines():
            p = line.split()
            if len(p) == 3 and p[0] == "DEF":
                try:
                    v = int(p[2], 16) & 0xFFFF      # banked symbols are bank << 16 | addr
                except ValueError:
                    continue
                SYMS[p[1]] = v
                if p[1].startswith("_"):
                    SYMS.setdefault(p[1][1:], v)
    if sym.exists():
        for line in sym.read_text(errors="replace").splitlines():
            p = line.split()
            if len(p) == 2 and ":" in p[0] and not line.startswith(";"):
                try:
                    SYMS.setdefault(p[1], int(p[0].split(":")[1], 16))
                except ValueError:
                    pass


def num(s):
    s = s.strip()
    return int(s, 16) if s.lower().startswith("0x") else int(s.lstrip("$"), 16) if s.startswith("$") else int(s)


def parse_loc(text):
    """'[mem:]loc[+off][.w]' -> (mem, addr, width, source). Symbols read through the CPU bus."""
    src = text.strip()
    width = 1
    if src.endswith(".w"):
        width, src = 2, src[:-2]
    mem = None
    m = re.match(r"^(wram|vram|oam|hram|sram|rom|bus):(.+)$", src)
    if m:
        mem, src = m.group(1), m.group(2)
    m = re.match(r"^([A-Za-z_.$][\w.$]*|0x[0-9a-fA-F]+|\$[0-9a-fA-F]+|\d+)\s*([+-]\s*(?:0x[0-9a-fA-F]+|\d+))?$", src)
    if not m:
        raise BadArgs(f"bad location {text!r}")
    base, off = m.group(1), m.group(2)
    if re.match(r"^(0x[0-9a-fA-F]+|\$[0-9a-fA-F]+|\d+)$", base):
        addr = num(base)
    else:
        if base not in SYMS:
            raise BadArgs(f"unknown symbol {base!r} (no .noi/.sym entry; static globals are not exported)")
        addr = SYMS[base]
        mem = mem or "bus"
    if off:
        addr += num(off.replace(" ", "").lstrip("+")) if off.strip()[0] == "+" else -num(off.replace(" ", "")[1:])
    return mem or "bus", addr, width, text.strip()


def parse_check(text):
    m = re.match(r"^(.+?)\s*(==|!=|<=|>=|<|>)\s*(-?(?:0x[0-9a-fA-F]+|\d+))\s*$", text.strip())
    if not m:
        raise BadArgs(f"bad check {text!r} (expected loc OP value)")
    mem, addr, width, _ = parse_loc(m.group(1))
    return mem, addr, width, num(m.group(3)), text.strip(), "~=" if m.group(2) == "!=" else m.group(2)


def parse_input(spec, frames):
    out = []
    for part in filter(None, (p.strip() for p in (spec or "").split(";"))):
        m = re.match(r"^(\d+)(?:-(\d+))?:(.+)$", part)
        if not m:
            raise BadArgs(f"bad input {part!r} (expected F[-F2]:btn+btn)")
        f1 = int(m.group(1)); f2 = int(m.group(2) or f1)
        btns = [b.strip().lower() for b in m.group(3).split("+")]
        bad = [b for b in btns if b not in BUTTONS]
        if bad or f2 < f1 or f1 < 1 or f2 > frames:
            raise BadArgs(f"bad input {part!r}: buttons {sorted(BUTTONS)}, frames 1..{frames}")
        out.append((f1, f2, btns))
    return out


def lua_str(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def rd(mem, addr, width):
    f = "emu.read16" if width == 2 else "emu.read"
    return f"{f}({addr}, emu.memType.{MEM[mem]})"


def check_lua(chk, frame=None):
    mem, addr, width, val, src, op = chk
    fr = f', "frame":{frame}' if frame is not None else ""
    return (f"do local v = {rd(mem, addr, width)}; local pass = (v {op} {val}); ok_all = ok_all and pass; "
            f"results[#results+1] = string.format('{{\"check\":%q,\"value\":%d,\"pass\":%s{fr}}}', "
            f"{lua_str(src)}, v, tostring(pass)) end")


def build_lua(a, out):
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
    dumps, seen = [], {}
    for d in filter(None, (a.dump or "").split(",")):
        p = d.strip().split(":")
        if p[0] not in MEM or len(p) not in (1, 3):
            raise BadArgs(f"bad --dump {d!r} (name[:start:len], names {sorted(MEM)})")
        start, ln = (num(p[1]), num(p[2])) if len(p) == 3 else (0, -1)
        seen[p[0]] = seen.get(p[0], 0) + 1
        dumps.append((p[0] if seen[p[0]] == 1 else f"{p[0]}_{seen[p[0]]}", p[0], start, ln))
    sram_in = None
    if a.sram_in:
        if a.sram_in != "fresh" and not pathlib.Path(a.sram_in).exists():
            raise BadArgs(f"--sram-in {a.sram_in} not found")
        sram_in = "" if a.sram_in == "fresh" else pathlib.Path(a.sram_in).resolve().as_posix()

    L = [f"local OUT = {lua_str(out.as_posix())}", f"local LAST = {a.frames}", f"local EVERY = {a.every}",
         "local frame, results, ok_all, csv = 0, {}, true, {}",
         f"local COUNT_BOOT, booted, boot_frames = {'true' if a.boot else 'false'}, false, 0", "local SHOTS = {" + ",".join(f"[{s}]=true" for s in shots) + "}",
         "local INPUTS = {" + ",".join("{%d,%d,{%s}}" % (f1, f2, ",".join(f"{b}=true" for b in bs)) for f1, f2, bs in inputs) + "}",
         "local WATCH = {" + ",".join(f"{{emu.memType.{MEM[m]},{ad},{w}}}" for m, ad, w, _ in watches) + "}"]
    L.append(textwrap.dedent("""
    local function write(path, data, mode)
      local f = assert(io.open(OUT .. "/" .. path, mode or "wb")); f:write(data); f:close()
    end
    local function dump(name, mt, start, len)
      if len < 0 then len = emu.getMemorySize(mt) - start end
      local t = {}
      for i = 0, len - 1 do t[#t + 1] = string.char(emu.read(start + i, mt)) end
      write(name .. ".bin", table.concat(t))
    end
    -- emu.getScreenBuffer() = the PPU frame of this emulated frame (takeScreenshot can lag a frame)
    local function shot(f)
      local buf = emu.getScreenBuffer()
      local parts = {}
      for i = 1, #buf do local v = buf[i]; parts[i] = string.char((v >> 16) & 255, (v >> 8) & 255, v & 255) end
      write(string.format("shot_%04d.rgb", f), table.concat(parts))
    end
    local function sample()
      local row = {tostring(frame)}
      for _, w in ipairs(WATCH) do
        row[#row + 1] = tostring((w[3] == 2) and emu.read16(w[2], w[1]) or emu.read(w[2], w[1]))
      end
      return table.concat(row, ",")
    end
    local EXP = {}
    local function expect_sample(e, v)
      e.n = e.n + 1
      if e.min == nil or v < e.min then e.min = v end
      if e.max == nil or v > e.max then e.max = v end
    end
    """))
    if sram_in is not None:
        L.append(textwrap.dedent(f"""
        do
          local mt = emu.memType.gbCartRam
          local size = emu.getMemorySize(mt)
          local data = ""
          if {lua_str(sram_in)} ~= "" then local f = assert(io.open({lua_str(sram_in)}, "rb")); data = f:read("a"); f:close() end
          for i = 0, size - 1 do emu.write(i, (i < #data) and data:byte(i + 1) or 255, mt) end
          SRAM_SIZE = size
        end"""))
    if watches:
        L.append("csv[1] = " + lua_str("frame," + ",".join(w[3] for w in watches)))
    for i, (chk, f1, f2, src) in enumerate(expects):
        mem, addr, width, val, _, op = chk
        L.append(f"EXP[{i + 1}] = {{f1={f1}, f2={f2}, n=0, src={lua_str(src)}, "
                 f"get=function() return {rd(mem, addr, width)} end, test=function(v) return v {op} {val} end}}")
    L.append("local CHECK_AT = {}")
    for f, lst in sorted(check_at.items()):
        L.append(f"CHECK_AT[{f}] = function()")
        L += ["  " + check_lua(c, f) for c in lst]
        L.append("end")
    L.append(textwrap.dedent("""
    local pending_shot, stop_code = nil, nil
    emu.addEventCallback(function()
      if pending_shot then shot(pending_shot); pending_shot = nil end
      if stop_code then emu.stop(stop_code) end
    end, emu.eventType.startFrame)
    emu.addEventCallback(function()
      local pad = {}
      for _, r in ipairs(INPUTS) do
        if booted and frame + 1 >= r[1] and frame + 1 <= r[2] then for k, v in pairs(r[3]) do pad[k] = v end end
      end
      emu.setInput(pad, 0)
    end, emu.eventType.inputPolled)
    emu.addEventCallback(function()
      if stop_code then return end
      if not booted then       -- frames count from the end of the boot ROM (as PyBoy, which has none)
        boot_frames = boot_frames + 1
        if COUNT_BOOT or emu.getState()["memoryManager.disableBootRom"] then booted = true end
        if not COUNT_BOOT then return end
      end
      frame = frame + 1
      if SHOTS[frame] then pending_shot = frame end
      if #WATCH > 0 and (frame % EVERY == 0 or frame == LAST) then csv[#csv + 1] = sample() end
      if CHECK_AT[frame] then CHECK_AT[frame]() end
      for _, e in ipairs(EXP) do
        if frame >= e.f1 and frame <= e.f2 then
          local v = e.get(); expect_sample(e, v)
          if not e.test(v) and e.ff == nil then e.ff = frame; e.fv = v end
        end
      end
      if frame < LAST then return end
      if #csv > 0 then write("watch.csv", table.concat(csv, "\\n") .. "\\n", "w") end
    """))
    for fname, name, start, ln in dumps:
        L.append(f"  dump({lua_str(fname)}, emu.memType.{MEM[name]}, {start}, {ln})")
    if a.sram_out:
        L.append(f"  do local mt = emu.memType.gbCartRam; local t = {{}}; "
                 f"for i = 0, emu.getMemorySize(mt) - 1 do t[#t + 1] = string.char(emu.read(i, mt)) end; "
                 f"local f = assert(io.open({lua_str(pathlib.Path(a.sram_out).resolve().as_posix())}, 'wb')); "
                 f"f:write(table.concat(t)); f:close() end")
    L += ["  " + check_lua(c) for c in checks]
    L.append(textwrap.dedent("""
      local ex = {}
      for _, e in ipairs(EXP) do
        local pass = e.ff == nil and e.n > 0
        ok_all = ok_all and pass
        ex[#ex + 1] = string.format('{"expect":%q,"samples":%d,"min":%s,"max":%s,"pass":%s,"first_fail_frame":%s,"first_fail_value":%s}',
          e.src, e.n, tostring(e.min or "null"), tostring(e.max or "null"), tostring(pass), tostring(e.ff or "null"), tostring(e.fv or "null"))
      end
      local st = emu.getState()
      write("result.json", '{"frames":' .. frame .. ',"boot_frames":' .. boot_frames .. ',"emu_frames":' .. st.frameCount .. ',"console":"' .. tostring(st.consoleType)
        .. '","sram_size":' .. tostring(SRAM_SIZE or emu.getMemorySize(emu.memType.gbCartRam))
        .. ',"checks":[' .. table.concat(results, ",") .. '],"expects":[' .. table.concat(ex, ",") .. '],"ok":' .. tostring(ok_all) .. '}', "w")
      stop_code = ok_all and 0 or 1
    end, emu.eventType.endFrame)
    """))
    return "\n".join(L)


@contextlib.contextmanager
def mesen_slot(path=MESEN_LOCK):
    """Machine-wide testrunner slot (shared with snesrun); OS locks are released even after a crash."""
    handle = path.open("a+b")
    handle.seek(0, 2)
    if not handle.tell():
        handle.write(b"0"); handle.flush()
    handle.seek(0)
    if os.name == "nt":
        import msvcrt
        while True:
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1); break
            except OSError:
                time.sleep(.02)
        unlock = lambda: msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle, fcntl.LOCK_EX)
        unlock = lambda: fcntl.flock(handle, fcntl.LOCK_UN)
    try:
        yield
    finally:
        handle.seek(0); unlock(); handle.close()


def find_mesen(arg):
    for c in [arg, os.environ.get("GBRUN_MESEN")] + MESEN_CANDIDATES:
        if c and pathlib.Path(c).exists():
            return pathlib.Path(c)
    die("Mesen.exe not found: copy it to tools/mesen/ (ignored) or pass --mesen / GBRUN_MESEN")


def rgb_to_png(out):
    from PIL import Image
    for raw in sorted(out.glob("shot_*.rgb")):
        data = raw.read_bytes()
        if len(data) == 160 * 144 * 3:
            Image.frombytes("RGB", (160, 144), data).save(raw.with_suffix(".png"))
        raw.unlink()


def golden_compare(out, gdir, update, data):
    from PIL import Image, ImageChops
    shots = sorted(out.glob("shot_*.png"))
    data["golden"] = []
    if update:
        gdir.mkdir(parents=True, exist_ok=True)
        for s in shots:
            (gdir / s.name).write_bytes(s.read_bytes())
        for stale in set(p.name for p in gdir.glob("shot_*.png")) - set(s.name for s in shots):
            (gdir / stale).unlink(); print("golden: removed stale", stale)
        print(f"golden: wrote {len(shots)} references to {gdir}")
        return
    for s in shots:
        ref = gdir / s.name
        if not ref.exists():
            data["ok"] = False; data["golden"].append({"shot": s.name, "missing": True})
            print(f"FAIL: golden reference missing: {ref} (create with --update-golden)"); continue
        a, b = Image.open(s).convert("RGB"), Image.open(ref).convert("RGB")
        if a.size != b.size:
            data["ok"] = False; print(f"FAIL: golden {s.name}: size {a.size} != {b.size}"); continue
        diff = ImageChops.difference(a, b)
        n = sum(1 for p in diff.getdata() if p != (0, 0, 0))
        data["golden"].append({"shot": s.name, "diff_pixels": n})
        if n:
            data["ok"] = False
            diff.point(lambda v: 255 if v else 0).save(out / ("diff_" + s.name))
            print(f"FAIL: golden {s.name}: {n} pixels differ (diff_{s.name})")


def resolve_rom(arg):
    p = pathlib.Path(arg)
    if p.suffix.lower() in (".gb", ".gbc"):
        return p.resolve()
    g = ROOT / "games" / arg / "build" / f"{arg}.gb"
    if not g.exists():
        die(f"{arg}: not a .gb file and {g} does not exist (build it: python -I harness/gb.py build {arg})")
    return g


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rom")
    ap.add_argument("--frames", type=int, default=120)
    ap.add_argument("--shot"); ap.add_argument("--input"); ap.add_argument("--dump")
    ap.add_argument("--watch"); ap.add_argument("--every", type=int, default=60)
    ap.add_argument("--check"); ap.add_argument("--check-at"); ap.add_argument("--expect")
    ap.add_argument("--nonblank", action="store_true")
    ap.add_argument("--golden"); ap.add_argument("--update-golden", action="store_true")
    ap.add_argument("--ram", choices=["zeros", "ones", "random"], default="zeros")
    ap.add_argument("--model", choices=sorted(MODELS), default="dmg")
    ap.add_argument("--boot", action="store_true")
    ap.add_argument("--sram-in"); ap.add_argument("--sram-out")
    ap.add_argument("--out"); ap.add_argument("--mesen")
    ap.add_argument("--timeout", type=int, default=int(os.environ.get("GBRUN_TIMEOUT") or 60))
    a = ap.parse_args(argv)
    rom = resolve_rom(a.rom)
    if not rom.exists():
        die(f"{rom} not found")
    load_syms(rom)
    out = pathlib.Path(a.out).resolve() if a.out else rom.parent / "mesen"
    try:
        script = build_lua(a, out)
    except BadArgs as e:
        die(str(e))
    mesen = find_mesen(a.mesen)
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*"):
        if f.suffix in (".png", ".bin", ".json", ".lua", ".csv", ".rgb"):
            f.unlink()
    if a.sram_out:
        pathlib.Path(a.sram_out).resolve().parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.sram_out).unlink(missing_ok=True)
    lua = out / "_run.lua"
    lua.write_text(script, encoding="utf-8")
    ram = {"zeros": "AllZeros", "ones": "AllOnes", "random": "Random"}[a.ram]
    cmd = [str(mesen), "--testrunner", str(rom), str(lua), f"--timeout={a.timeout}",
           "--debug.scriptWindow.allowIoOsAccess=true", "--doNotSaveSettings",
           # the user's Mesen settings favour GBC, blend frames and randomise RAM: force all of them
           f"--gameboy.model={MODELS[a.model]}", "--gameboy.blendFrames=false",
           f"--gameboy.ramPowerOnState={ram}", "--video.videoFilter=None"]
    res = out / "result.json"
    attempts = []
    with mesen_slot():
        for n in (1, 2):    # retry once, only when Mesen produced no result (transient start-up failures)
            p = subprocess.run(cmd, capture_output=True, text=True)
            attempts.append({"attempt": n, "exit": p.returncode, "stdout": p.stdout[-2000:], "stderr": p.stderr[-2000:]})
            if res.exists():
                break
    if not res.exists():
        print("FAIL: Mesen produced no result.json")
        for at in attempts:
            print(json.dumps(at, indent=1))
        sys.exit(2)
    rgb_to_png(out)
    data = json.loads(res.read_text())
    data["mesen_exit"] = attempts[-1]["exit"]
    if data.get("console") != "Gameboy":
        print(f"NOTE: Mesen ran the ROM as {data.get('console')}")
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
        golden_compare(out, pathlib.Path(a.golden).resolve(), a.update_golden, data)
    for c in data["checks"]:
        if not c["pass"]:
            print(f"FAIL: check {c['check']}" + (f" at frame {c['frame']}" if "frame" in c else "") + f" (value {c['value']})")
    for e in data["expects"]:
        if not e["pass"]:
            print(f"FAIL: expect {e['expect']}: first failure frame {e['first_fail_frame']} "
                  f"(value {e['first_fail_value']}), min {e['min']} max {e['max']} over {e['samples']} frames")
    data["files"] = sorted(f.name for f in out.iterdir() if f.suffix in (".png", ".bin", ".csv"))
    res.write_text(json.dumps(data, indent=1))
    print(json.dumps({k: v for k, v in data.items() if k != "files"}, indent=1))
    print("out:", out)
    sys.exit(0 if data["ok"] else 1)


if __name__ == "__main__":
    main()
