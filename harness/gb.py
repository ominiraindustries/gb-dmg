"""Harness CLI for Game Boy DMG projects.

Usage:
    python harness/gb.py setup              Download GBDK-2020 into tools/ and docs into reference/
    python harness/gb.py build <game>       Compile games/<game> -> games/<game>/build/<game>.gb
    python harness/gb.py run <game>         Build and open the ROM in a PyBoy window
    python harness/gb.py test <game> [...]  Build and run games/<game>/tests with pytest
    python harness/gb.py new <game>         Create a new game from the template
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

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
        cfg.update(json.loads(path.read_text()))
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


def build(name):
    if not LCC.exists():
        die("GBDK not found, run: python harness/gb.py setup")
    gdir = game_dir(name)
    cfg = load_config(gdir)
    sources = sorted((gdir / "src").rglob("*.c")) + sorted((gdir / "src").rglob("*.s"))
    if not sources:
        die(f"no sources in {gdir / 'src'}")
    out = rom_path(gdir)
    out.parent.mkdir(exist_ok=True)
    cmd = [
        str(LCC),
        "-Wl-m",  # .map file (memory usage)
        "-Wl-j",  # .noi file (symbols, used by tests)
        "-Wm-yS",  # .sym file (symbols for Emulicious/BGB)
        "-Wf--max-allocs-per-node50000",  # better register allocation, smaller/faster code
        f"-Wm-yn{cfg['title']}",
        *cfg["lcc_flags"],
        "-o", str(out),
        *map(str, sources),
    ]
    res = subprocess.run(cmd, cwd=gdir, capture_output=True, text=True)
    output = (res.stdout + res.stderr).strip()
    if output:
        print(output)
    if res.returncode != 0 or not out.exists():
        die("build failed")
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


def new(name):
    dst = ROOT / "games" / name
    if dst.exists():
        die(f"{dst} already exists")
    shutil.copytree(ROOT / "harness" / "template", dst)
    cfg = dst / "game.json"
    cfg.write_text(cfg.read_text().replace("TEMPLATE", name.upper()[:15]))
    print(f"Created {dst.relative_to(ROOT)}")


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd, rest = args[0], args[1:]
    if cmd == "setup":
        setup()
    elif cmd in ("build", "run", "test", "new") and rest:
        {"build": lambda: build(rest[0]),
         "run": lambda: run(rest[0]),
         "test": lambda: test(rest[0], rest[1:]),
         "new": lambda: new(rest[0])}[cmd]()
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
