"""Harness CLI for Game Boy DMG projects.

Usage:
    python harness/gb.py setup              Download GBDK-2020 into tools/ and docs into reference/
    python harness/gb.py build <game>       Compile games/<game> -> games/<game>/build/<game>.gb
    python harness/gb.py run <game>         Build and open the ROM in a PyBoy window
    python harness/gb.py test <game> [...]  Build and run games/<game>/tests with pytest
    python harness/gb.py new <game> [type]  Create a new game from harness/templates/<type> (default basic)
    python harness/gb.py preview <game>     Render tilesets and design/screens/*.screen to PNG
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

import asciitiles
import levels
import metatiles

ROOT = Path(__file__).resolve().parent.parent
GBDK_VERSION = "4.5.0"
GBDK_URL = f"https://github.com/gbdk-2020/gbdk-2020/releases/download/{GBDK_VERSION}/gbdk-win64.zip"
GBDK_HOME = Path(os.environ.get("GBDK_HOME", ROOT / "tools" / "gbdk"))
LCC = GBDK_HOME / "bin" / ("lcc.exe" if os.name == "nt" else "lcc")
ROMUSAGE = GBDK_HOME / "bin" / ("romusage.exe" if os.name == "nt" else "romusage")


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def game_dir(name):
    d = ROOT / "games" / name
    if not d.is_dir():
        die(f"game '{name}' not found in {ROOT / 'games'}")
    return d


def load_config(gdir):
    cfg = {"title": gdir.name.upper()[:15], "lcc_flags": []}
    path = gdir / "game.json"
    if path.exists():
        cfg.update(json.loads(path.read_text(encoding="utf-8")))
    return cfg


def rom_path(gdir):
    return gdir / "build" / f"{gdir.name}.gb"


def setup():
    if LCC.exists():
        print(f"GBDK already installed at {GBDK_HOME}")
    else:
        tools = ROOT / "tools"
        tools.mkdir(exist_ok=True)
        zpath = tools / "gbdk.zip"
        print(f"Downloading GBDK-2020 {GBDK_VERSION}...")
        urllib.request.urlretrieve(GBDK_URL, zpath)
        with zipfile.ZipFile(zpath) as z:
            z.extractall(tools)
        zpath.unlink()
        print(f"Installed at {GBDK_HOME}")
    fetch_references()


def fetch_references():
    """Raw docs the skills in .claude/skills point to for full detail."""
    ref = ROOT / "reference"
    ref.mkdir(exist_ok=True)
    clones = {
        "pandocs": ["git", "clone", "-q", "--depth", "1", "https://github.com/gbdev/pandocs.git"],
        "gbdk-src": ["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--sparse",
                     "https://github.com/gbdk-2020/gbdk-2020.git"],
    }
    for name, cmd in clones.items():
        if not (ref / name).exists():
            print(f"Cloning {name}...")
            subprocess.run([*cmd, name], cwd=ref, check=True)
            if name == "gbdk-src":
                subprocess.run(["git", "sparse-checkout", "set", "docs/pages"], cwd=ref / name, check=True)
    files = {
        "opcodes.json": "https://gbdev.io/gb-opcodes/Opcodes.json",
        "gbctr.pdf": "https://gekkio.fi/files/gb-docs/gbctr.pdf",
    }
    for name, url in files.items():
        if not (ref / name).exists():
            print(f"Downloading {name}...")
            urllib.request.urlretrieve(url, ref / name)
    print(f"References in {ref}")


# Functions whose header people forget (gb/gb.h does not include these)
KNOWN_HEADERS = {
    "hide_sprites_range": "gb/metasprites.h", "move_metasprite": "gb/metasprites.h",
    "move_metasprite_ex": "gb/metasprites.h", "move_metasprite_flipx": "gb/metasprites.h",
    "memcpy": "string.h", "memset": "string.h", "strlen": "string.h",
    "rand": "rand.h", "randw": "rand.h", "initrand": "rand.h", "arand": "rand.h",
    "EMU_printf": "gbdk/emu_debug.h",
}


def cart_title(title):
    """Cartridge header title: lcc rebuilds the command line, so a space split the argument and
    broke the build ("GBE LAB"). Uppercase, spaces -> '_', at most 15 chars."""
    return "".join(c if c.isalnum() else "_" for c in title.upper())[:15]


def check_warnings(output):
    """SDCC warnings that compile but are always bugs in our code: turn them into errors."""
    import re
    problems = []
    for m in re.finditer(r"(\S+):(\d+): warning 112: function '(\w+)' implicit declaration", output):
        f = m.group(3)
        hint = f" -> #include <{KNOWN_HEADERS[f]}>" if f in KNOWN_HEADERS else " (missing prototype/#include)"
        problems.append(f"{Path(m.group(1)).name}:{m.group(2)}: {f}() not declared{hint}")
    for m in re.finditer(r"(\S+):(\d+): warning 94: comparison is always (true|false)", output):
        problems.append(f"{Path(m.group(1)).name}:{m.group(2)}: comparison always {m.group(3)} - a variable "
                        "too small for the constant (dungeon: uint8_t timer compared with 300 never fired)")
    for m in re.finditer(r"(\S+):(\d+): warning 84: 'auto' variable '(\w+)' may be used before", output):
        problems.append(f"{Path(m.group(1)).name}:{m.group(2)}: '{m.group(3)}' - if it is a function, "
                        "move its prototype to file scope (SDCC treats block-scope prototypes as variables)")
    return problems


SHADOWED_REGS = {"SCX_REG": "scx_shadow", "SCY_REG": "scy_shadow", "BGP_REG": "bgp_shadow",
                 "OBP0_REG": "obp0_shadow", "OBP1_REG": "obp1_shadow"}


def check_sources(gdir, cfg):
    """Source rules that compile fine but break at run time."""
    import re
    problems = []
    # Banked code must never switch banks: SWITCH_ROM would unmap the code that is running
    # (GBDK docs; gbe_bank.c helpers live in bank 0 and restore the bank)
    for f in sorted((gdir / "src").rglob("*.c")):
        text = f.read_text(encoding="utf-8")
        m = re.search(r"^\s*#pragma\s+bank\s+(\d+)", text, re.M)
        if m and m.group(1) != "0":
            for n, line in enumerate(text.splitlines(), 1):
                if re.search(r"\bSWITCH_ROM", line.split("//", 1)[0]):
                    problems.append(f"{f.name}:{n}: SWITCH_ROM in banked code (#pragma bank {m.group(1)}) "
                                    "unmaps itself: use the gbe_bank.c helpers (bank 0)")
    if "gbe_video.c" in cfg.get("common_src", []):
        # gbe_video rewrites these registers every VBlank from its shadows: a raw write lasts one
        # frame (platformer intro card lost its SCY when the shmup made SCY shadowed).
        for f in sorted((gdir / "src").rglob("*.c")):
            for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                code = line.split("//", 1)[0]
                for reg, shadow in SHADOWED_REGS.items():
                    if re.search(rf"\b{reg}\s*=[^=]", code) and shadow not in code:
                        problems.append(f"{f.name}:{n}: {reg} written directly; gbe_video overwrites "
                                        f"it every VBlank -> set {shadow} (or both on one line)")
    return problems


def bank_generated(c_file):
    """Move a generated asset into a switchable ROM bank: '#pragma bank 255' (bankpack picks the
    bank) + BANKREF(<stem>) in the .c, BANKREF_EXTERN(<stem>) in the .h. Code reads it with
    BANK(<stem>) through the gbe_bank.c helpers (bank 0)."""
    c_file = Path(c_file)
    stem = c_file.stem
    c = c_file.read_text(encoding="utf-8")
    if "#pragma bank" not in c:
        c_file.write_text("#pragma bank 255\n#include <gb/gb.h>\n" + c + f"\nBANKREF({stem})\n",
                          encoding="utf-8")
    h_file = c_file.with_suffix(".h")
    h = h_file.read_text(encoding="utf-8")
    if "BANKREF_EXTERN" not in h:
        h_file.write_text(h + f"#include <gb/gb.h>\nBANKREF_EXTERN({stem})\n", encoding="utf-8")


def check_bank0(map_file, cfg):
    """With banks in use, everything that is not in a switchable bank must end below 0x4000: a flat
    build that runs past it (games/platformer, games/shmup: code up to 0x6DA1) works only until the
    first SWITCH_ROM unmaps the code. Returns (errors, warnings)."""
    import re
    areas = {}
    for m in re.finditer(r"^(_\w+)\s+([0-9A-F]{8})\s+([0-9A-F]{8}) =", map_file.read_text(encoding="utf-8"),
                         re.M):
        name, addr, size = m.group(1), int(m.group(2), 16), int(m.group(3), 16)
        if size:
            areas[name] = (addr, size)
    banked = [n for n, (a, z) in areas.items() if re.match(r"_CODE_[1-9]\d*$", n)]
    fixed = [(n, a + z) for n, (a, z) in areas.items()
             if (a & 0xFFFF) < 0x8000 and not re.match(r"_CODE_[1-9]\d*$", n) and a < 0x10000]
    end = max((e for _, e in fixed), default=0)
    if end <= 0x4000:
        return [], []
    past = ", ".join(f"{n} to 0x{e:04X}" for n, e in fixed if e > 0x4000)
    if banked or "-autobank" in cfg.get("lcc_flags", []):
        return [f"bank 0 overflow ({past}): code/const data past 0x4000 is unmapped by SWITCH_ROM; "
                "move data to banks (game.json \"banked_res\", #pragma bank 255) or code into "
                "BANKED functions"], []
    return [], [f"flat build past 0x4000 ({past}): fine without bank switching; before using banks "
                f"(music, more levels) see CLAUDE.md \"Bancos de ROM\""]


def tileset_labels(gdir, mt_file):
    """{LABEL: index} of the tileset a metatiles.mt names (game res/ first, then harness/common)."""
    ts = None
    for line in mt_file.read_text(encoding="utf-8").splitlines():
        parts = line.split(";", 1)[0].split()
        if parts[:2] == ["@", "tileset"]:
            ts = parts[2]
    if not ts:
        return {}
    for d in (gdir / "res", ROOT / "harness" / "common"):
        if (d / f"{ts}.tiles").exists():
            return asciitiles.parse(d / f"{ts}.tiles")[1]
    die(f"{mt_file}: tileset '{ts}' not found")


def build(name):
    if not LCC.exists():
        die("GBDK not found, run: python harness/gb.py setup")
    gdir = game_dir(name)
    cfg = load_config(gdir)
    sources = sorted((gdir / "src").rglob("*.c")) + sorted((gdir / "src").rglob("*.s"))
    common_src = ROOT / "harness" / "common" / "src"
    for name in cfg.get("common_src", []):
        if not (common_src / name).exists():
            die(f"common_src '{name}' not found in {common_src}")
        sources.append(common_src / name)
    if not sources:
        die(f"no sources in {gdir / 'src'}")
    problems = check_sources(gdir, cfg)
    if problems:
        die("build stopped:\n  " + "\n  ".join(problems))
    out = rom_path(gdir)
    out.parent.mkdir(exist_ok=True)
    gen = out.parent / "gen"
    shared = [ROOT / "harness" / "common" / f"{n}.tiles" for n in cfg.get("common_res", [])]
    for tiles in shared + sorted((gdir / "res").glob("*.tiles")):
        try:
            sources.append(asciitiles.convert(tiles, gen))
        except ValueError as e:
            die(str(e))
    bases = {}
    if cfg.get("vram_order"):
        import preview
        import screens
        try:
            bases = screens.write_vram_h(cfg["vram_order"], preview.find_tilesets(gdir), gen)
        except ValueError as e:
            die(str(e))
    if cfg.get("screens"):
        import preview
        import screens
        sets = preview.find_tilesets(gdir)
        for name in cfg["screens"]:
            try:
                sources.append(screens.convert(gdir / "design" / "screens" / f"{name}.screen", gen,
                                               sets, cfg.get("vram_order", [])))
            except (KeyError, ValueError) as e:
                die(str(e))
    for mt_file in sorted((gdir / "res").glob("metatiles*.mt")):          # metatiles.mt, metatiles_<set>.mt
        try:
            sources.append(metatiles.convert(mt_file, gen, tileset_labels(gdir, mt_file), bases))
        except ValueError as e:
            die(str(e))
    pcs_file = gdir / "res" / "view.pcs"
    if pcs_file.exists():
        import fpview
        try:
            sources.append(fpview.to_c(fpview.parse(pcs_file, tileset_labels(gdir, pcs_file), bases), gen))
        except ValueError as e:
            die(str(e))
    table_syms = {}
    if (gdir / "res" / "data").is_dir():                                 # data tables (tables.py)
        import tables
        try:
            outs, tbls = tables.convert(gdir / "res" / "data", gen)
        except ValueError as e:
            die(str(e))
        sources += outs
        table_syms = tables.symbols(tbls)
    if (gdir / "res" / "scripts").is_dir():                              # event scripts (script.py)
        import script
        try:
            sources += script.convert(gdir / "res" / "scripts", gen, table_syms)
        except ValueError as e:
            die(str(e))
    for map_file in sorted((gdir / "res" / "maps").glob("*.map")):      # 4-way world maps (world.py)
        import world
        try:
            sources.append(world.convert(world.load(gdir, map_file), gen))
        except (KeyError, ValueError) as e:
            die(str(e))
    for lvl in sorted((gdir / "res").glob("*.lvl")):
        try:
            sources.append(levels.convert(lvl, gen, cfg.get("levels", {})))
        except ValueError as e:
            die(str(e))
    banked = cfg.get("banked_res", [])
    for stem in banked:
        c_file = gen / f"{stem}.c"
        if not c_file.exists():
            die(f"banked_res '{stem}': no generated {c_file.name} (tileset, level or screen_<name>)")
        bank_generated(c_file)
    cmd = [
        str(LCC),
        f"-I{gen}",  # generated asset headers
        f"-I{gdir / 'src'}",  # game headers, also for generated level files
        f"-I{common_src}",  # shared code headers (harness/common/src)
        "-Wl-m",  # .map file (memory usage)
        "-Wl-j",  # .noi file (symbols, used by tests)
        "-Wm-yS",  # .sym file (symbols for Emulicious/BGB)
        "-Wf--max-allocs-per-node50000",  # better register allocation, smaller/faster code
        f"-Wm-yn{cart_title(cfg['title'])}",
        *cfg["lcc_flags"],
        "-o", str(out),
        *map(str, sources),
    ]
    res = subprocess.run(cmd, cwd=gdir, capture_output=True, text=True)
    output = (res.stdout + res.stderr).strip()
    if output:
        print(output)
    problems = check_warnings(output)
    if problems:
        die("build stopped on warnings that are always bugs here:\n  " + "\n  ".join(problems))
    if res.returncode != 0 or not out.exists():
        die("build failed")
    errors, warnings = check_bank0(out.with_suffix(".map"), cfg)
    for w in warnings:
        print("warning: " + w)
    if errors:
        die("\n  ".join(errors))
    print(f"OK {out.relative_to(ROOT)} ({out.stat().st_size} bytes)")
    usage = subprocess.run([str(ROMUSAGE), str(out.with_suffix(".map")), "-g"],
                           capture_output=True, text=True)
    print(usage.stdout.strip())
    return out


def run(name):
    out = build(name)
    from pyboy import PyBoy
    pb = PyBoy(str(out), window="SDL2")
    while pb.tick():
        pass
    pb.stop()


def test(name, extra):
    build(name)
    sys.stdout.flush()
    tests = game_dir(name) / "tests"
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", str(tests), "-q", *extra], cwd=ROOT))


def new(name, kind="basic"):
    dst = ROOT / "games" / name
    src = ROOT / "harness" / "templates" / kind
    if dst.exists():
        die(f"{dst} already exists")
    if not src.is_dir():
        kinds = ", ".join(p.name for p in (ROOT / "harness" / "templates").iterdir() if p.is_dir())
        die(f"no template '{kind}' (available: {kinds})")
    shutil.copytree(src, dst)
    cfg = dst / "game.json"
    cfg.write_text(cfg.read_text(encoding="utf-8").replace("TEMPLATE", name.upper()[:15]), encoding="utf-8")
    print(f"Created {dst.relative_to(ROOT)}")


def preview_cmd(name):
    import preview
    try:
        for p in preview.preview(game_dir(name)):
            print(p.relative_to(ROOT))
    except (KeyError, ValueError) as e:
        die(str(e))


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd, rest = args[0], args[1:]
    if cmd == "setup":
        setup()
    elif cmd in ("build", "run", "test", "new", "preview") and rest:
        {"build": lambda: build(rest[0]),
         "run": lambda: run(rest[0]),
         "test": lambda: test(rest[0], rest[1:]),
         "new": lambda: new(rest[0], *rest[1:2]),
         "preview": lambda: preview_cmd(rest[0])}[cmd]()
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
