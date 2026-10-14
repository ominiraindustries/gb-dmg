"""Headless Game Boy driver for automated tests (wraps PyBoy).

Lets tests press buttons, advance frames, read game variables by their C name
and save screenshots that Claude (or you) can look at.
"""
from pathlib import Path

from pyboy import PyBoy

BOOT_FRAMES = 180  # PyBoy's boot animation + game init


def load_noi(path):
    """Parse the linker .noi file: 'DEF _player_x 0xC0A2' -> {'player_x': 0xC0A2}."""
    syms = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0] == "DEF":
            name = parts[1][1:] if parts[1].startswith("_") else parts[1]
            syms[name] = int(parts[2], 16)
    return syms


class GB:
    def __init__(self, rom, shots_dir=None):
        rom = Path(rom)
        self.pyboy = PyBoy(str(rom), window="null", sound_emulated=False)
        self.pyboy.set_emulation_speed(0)
        self.syms = load_noi(rom.with_suffix(".noi"))
        self.shots_dir = Path(shots_dir or rom.parent / "shots")
        self.frames(BOOT_FRAMES)

    def close(self):
        self.pyboy.stop(save=False)

    # --- time ---
    def frames(self, n=1):
        self.pyboy.tick(n, False)

    # --- input --- buttons: up down left right a b start select
    def hold(self, button, n):
        """Hold a button for n frames, then release it."""
        self.pyboy.button_press(button)
        self.frames(n)
        self.pyboy.button_release(button)
        self.frames(1)

    def tap(self, button):
        self.hold(button, 2)

    # --- memory ---
    def addr(self, name):
        if name not in self.syms:
            raise KeyError(f"symbol '{name}' not found (is it a non-static global?)")
        return self.syms[name]

    def u8(self, name):
        return self.pyboy.memory[self.addr(name)]

    def s8(self, name):
        v = self.u8(name)
        return v - 256 if v > 127 else v

    def write_u8(self, name, value):
        self.pyboy.memory[self.addr(name)] = value & 0xFF

    def u16(self, name):
        a = self.addr(name)
        return self.pyboy.memory[a] | (self.pyboy.memory[a + 1] << 8)

    def write_u16(self, name, value):
        a = self.addr(name)
        self.pyboy.memory[a] = value & 0xFF
        self.pyboy.memory[a + 1] = (value >> 8) & 0xFF

    def bytes(self, name, n):
        a = self.addr(name)
        return [self.pyboy.memory[a + i] for i in range(n)]

    # --- profiling ---
    def profile(self, funcs):
        """Start measuring T-cycles per call of the given C functions (by name).
        Returns a Profiler; call .report() later. Includes time spent in callees and in
        interrupts that fire during the call. Uses PyBoy's private _cycles() (PyBoy 2.8)."""
        return Profiler(self, funcs)

    # --- screen ---
    def screenshot(self, name):
        """Render the current frame and save it as shots/<name>.png. Returns the path."""
        self.pyboy.tick(1, True)
        self.shots_dir.mkdir(parents=True, exist_ok=True)
        path = self.shots_dir / f"{name}.png"
        self.pyboy.screen.image.save(path)
        return path


def _bank(addr):
    return 0 if addr < 0x4000 else 1  # no-MBC ROMs; banked code would need the active bank


class Profiler:
    """Hooks function entries; on entry reads the return address from the stack and hooks it
    to catch the return. Stats per function: calls, total, max, and the state of
    `context_var` (a game global, e.g. "state") at the slowest call."""

    def __init__(self, gb, funcs, context_var=None):
        self.gb, self.pb = gb, gb.pyboy
        self.stats = {f: {"calls": 0, "total": 0, "max": 0, "ctx": None} for f in funcs}
        self.pending = {}      # return address -> list of (func, start cycles, context)
        self.ret_hooks = set()
        self.context_var = context_var or ("state" if "state" in gb.syms else None)
        for f in funcs:
            addr = gb.addr(f)
            self.pb.hook_register(_bank(addr), addr, self._on_entry, f)

    def _ctx(self):
        return self.gb.u8(self.context_var) if self.context_var else None

    def _on_entry(self, func):
        pb = self.pb
        sp = pb.register_file.SP
        ret = pb.memory[sp] | (pb.memory[sp + 1] << 8)
        if func not in self.stats:
            return
        self.pending.setdefault(ret, []).append((func, pb._cycles(), self._ctx()))
        if ret not in self.ret_hooks:
            self.ret_hooks.add(ret)
            pb.hook_register(_bank(ret), ret, self._on_return, ret)

    def _on_return(self, ret):
        stack = self.pending.get(ret)
        if not stack:
            return
        func, start, ctx = stack.pop()
        s = self.stats[func]
        t = self.pb._cycles() - start
        s["calls"] += 1
        s["total"] += t
        if t > s["max"]:
            s["max"], s["ctx"] = t, ctx

    def stop(self):
        for f in self.stats:
            addr = self.gb.addr(f)
            self.pb.hook_deregister(_bank(addr), addr)
        for ret in self.ret_hooks:
            self.pb.hook_deregister(_bank(ret), ret)
        self.ret_hooks.clear()

    def report(self):
        """Text table sorted by worst case. 70224 T = 1 frame, 456 T = 1 scanline."""
        lines = [f"{'function':<20}{'calls':>7}{'avg T':>9}{'max T':>9}{'max lines':>11}  ctx"]
        for f, s in sorted(self.stats.items(), key=lambda kv: -kv[1]["max"]):
            avg = s["total"] // s["calls"] if s["calls"] else 0
            lines.append(f"{f:<20}{s['calls']:>7}{avg:>9}{s['max']:>9}{s['max'] / 456:>11.1f}  {s['ctx']}")
        return "\n".join(lines)
