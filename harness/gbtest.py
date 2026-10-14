"""Headless Game Boy driver for automated tests (wraps PyBoy).

Lets tests press buttons, advance frames, read game variables by their C name
and save screenshots that Claude (or you) can look at.

Consistent reads: a PyBoy tick ends at LY 0, which can fall in the middle of the game's update()
(the frame's work starts at LY ~146 after vsync()). So the driver hooks the game's vsync() entry -
the point where a frame's logic is complete - and during the last frame of each frames() call
snapshots WRAM there. u8/u16/bytes read WRAM from that snapshot; writes go to both.
"""
import io
from pathlib import Path

from pyboy import PyBoy

BOOT_FRAMES = 180  # PyBoy's boot animation + game init
WRAM_LO, WRAM_HI = 0xC000, 0xE000


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
    def __init__(self, rom, shots_dir=None, ram=None):
        """ram: cartridge SRAM bytes to boot with (from power_off()), for save/continue tests."""
        rom = Path(rom)
        extra = {"ram_file": io.BytesIO(ram)} if ram is not None else {}
        self.pyboy = PyBoy(str(rom), window="null", sound_emulated=False, **extra)
        self.pyboy.set_emulation_speed(0)
        self.syms = load_noi(rom.with_suffix(".noi"))
        self.shots_dir = Path(shots_dir or rom.parent / "shots")
        self._snap, self._want_snap = None, False
        if "vsync" in self.syms:
            self.pyboy.hook_register(0, self.syms["vsync"], self._on_vsync, None)
        self.frames(BOOT_FRAMES)

    def close(self):
        self.pyboy.stop(save=False)

    def power_off(self):
        """Stop and return the battery-backed cartridge RAM (boot again with GB(rom, ram=...))."""
        buf = io.BytesIO()
        self.pyboy.stop(save=True, ram_file=buf)
        return buf.getvalue()

    # --- time ---
    def _on_vsync(self, _):
        if self._want_snap:
            mem = self.pyboy.memory
            self._snap = mem[WRAM_LO:WRAM_HI]
            # BG maps and video registers at the same moment: what is on screen this frame
            # (VRAM written in the last VBlank, SCX/SCY/LCDC as the VBlank ISR set them)
            self._snap_maps = mem[0x9800:0xA000]
            self._snap_io = mem[0xFF40:0xFF4C]
            self._want_snap = False

    def _tick(self, n, render):
        if n > 1:
            self.pyboy.tick(n - 1, False)
        self._snap, self._want_snap = None, True   # no vsync this frame -> live reads
        self.pyboy.tick(1, render)
        self._want_snap = False

    def frames(self, n=1):
        self._tick(n, False)

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

    def _read(self, a):
        if self._snap is not None and WRAM_LO <= a < WRAM_HI:
            return self._snap[a - WRAM_LO]
        return self.pyboy.memory[a]

    def _write(self, a, v):
        self.pyboy.memory[a] = v
        if self._snap is not None and WRAM_LO <= a < WRAM_HI:
            self._snap[a - WRAM_LO] = v

    def u8(self, name):
        return self._read(self.addr(name))

    def s8(self, name):
        v = self.u8(name)
        return v - 256 if v > 127 else v

    def write_u8(self, name, value):
        self._write(self.addr(name), value & 0xFF)

    def u16(self, name):
        a = self.addr(name)
        return self._read(a) | (self._read(a + 1) << 8)

    def write_u16(self, name, value):
        a = self.addr(name)
        self._write(a, value & 0xFF)
        self._write(a + 1, (value >> 8) & 0xFF)

    def write_bytes(self, name, values, offset=0):
        """Write consecutive bytes at a global + offset (e.g. a pool record: offset = i * 16)."""
        a = self.addr(name) + offset
        for i, v in enumerate(values):
            self._write(a + i, v & 0xFF)

    def bytes(self, name, n):
        a = self.addr(name)
        return [self._read(a + i) for i in range(n)]

    # --- background (BG map and video registers, from the same vsync snapshot) ---
    def io(self, addr):
        """Video register 0xFF40-0xFF4B (LCDC STAT SCY SCX LY LYC DMA BGP OBP0 OBP1 WY WX)."""
        if self._snap is not None:
            return self._snap_io[addr - 0xFF40]
        return self.pyboy.memory[addr]

    def bg_map(self, window=False, map=None):
        """32 rows of 32 tile indices: map=0 $9800, map=1 $9C00 (window=True is map 1)."""
        base = 0x400 if (window or map == 1) else 0
        raw = self._snap_maps if self._snap is not None else self.pyboy.memory[0x9800:0xA000]
        return [list(raw[base + r * 32:base + r * 32 + 32]) for r in range(32)]

    def active_bg(self):
        """The BG map on screen (LCDC bit 3): 0 = $9800, 1 = $9C00 (double buffers)."""
        return 1 if self.io(0xFF40) & 0x08 else 0

    @staticmethod
    def rng_next(state):
        """gbe_rng.c xorshift16 (7, 9, 8): returns (new_state, byte) to predict the game's rolls."""
        s = state
        s ^= (s << 7) & 0xFFFF
        s ^= s >> 9
        s ^= (s << 8) & 0xFFFF
        return s, s & 0xFF

    FONT_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-!.:?/"     # harness/common/font.tiles order

    @staticmethod
    def tile_text(tiles, font, lower=None, es=None):
        """Map tile numbers back to text: `font` = VRAM base of font.tiles, `lower` = base of
        font_lower.tiles (a..z) or None, `es` = base of font_es.tiles (, ' ¡ ¿) or None; any other
        tile reads as a space."""
        out = ""
        for t in tiles:
            if 0 <= t - font < len(GB.FONT_CHARS):
                out += GB.FONT_CHARS[t - font]
            elif lower is not None and 0 <= t - lower < 26:
                out += chr(97 + t - lower)
            elif es is not None and 0 <= t - es < 4:
                out += ",'¡¿"[t - es]
            else:
                out += " "
        return out

    def bg_rows(self, first_line=0, last_line=143):
        """The BG map rows the screen shows between two lines with the current SCY: a list of
        (bg_row, map_row_tiles) top to bottom (each row covering any of those lines once)."""
        scy, rows, out = self.io(0xFF42), self.bg_map(), []
        for line in range(first_line, last_line + 1):
            r = ((scy + line) & 255) >> 3
            if not out or out[-1][0] != r:
                out.append((r, rows[r]))
        return out

    # --- sprites (OAM) ---
    def oam(self):
        """The 40 OAM entries as (y, x, tile, prop) from the shadow OAM (what GBDK DMAs next VBlank)."""
        raw = self.bytes("shadow_OAM", 160)
        return [tuple(raw[i * 4:i * 4 + 4]) for i in range(40)]

    def line_sprites(self, first=0, last=143, tall=None):
        """Per screen line: (requested, drawn) lists of OAM indices, emulating the DMG rule: the first
        10 sprites in OAM order that cover the line are drawn, the rest are not. tall=None reads the
        sprite size from LCDC bit 2 (8x8 or 8x16). Returns {line: (requested, drawn)}."""
        if tall is None:
            tall = 16 if self.io(0xFF40) & 0x04 else 8
        oam = self.oam()
        out = {}
        for line in range(first, last + 1):
            req = [i for i, (y, x, t, p) in enumerate(oam) if y - 16 <= line < y - 16 + tall]
            out[line] = (req, req[:10])
        return out

    def max_line_sprites(self, first=0, last=143):
        return max(len(r) for r, _ in self.line_sprites(first, last).values())

    # --- bots ---
    def run_bot(self, step, progress, frames, stuck_limit=240, on_stuck=None, done=None):
        """Play up to `frames` frames. Each frame: step(gb, f) presses/releases buttons, then one
        frame runs. progress(gb) -> number that should grow (player x, distance, lines cleared).
        When it has not grown for stuck_limit frames, on_stuck(gb) may help (counted as an
        assist) or the bot gives up. done(gb) -> True ends early (level clear).
        Returns a dict: frames, progress, assists, gave_up, worst_lines, vram_late.
        Budget numbers from a bot that did not move mean nothing: assert on 'progress' too."""
        self.write_u8("max_frame_lines", 0) if "max_frame_lines" in self.syms else None
        best, last_gain, assists, gave_up, f = progress(self), 0, 0, False, 0
        for f in range(frames):
            step(self, f)
            self.frames(1)
            p = progress(self)
            if p > best:
                best, last_gain = p, f
            elif f - last_gain >= stuck_limit:
                if on_stuck is None:
                    gave_up = True
                    break
                on_stuck(self)
                assists += 1
                last_gain = f
            if done is not None and done(self):
                break
        for b in ("up", "down", "left", "right", "a", "b", "start", "select"):
            self.pyboy.button_release(b)
        return {"frames": f + 1, "progress": best, "assists": assists, "gave_up": gave_up,
                "worst_lines": self.u8("max_frame_lines") if "max_frame_lines" in self.syms else None,
                "vram_late": self.u8("vram_late") if "vram_late" in self.syms else None}

    BUTTONS = ("up", "down", "left", "right", "a", "b", "start", "select")
    SKILL = {"expert": (8, 0.0), "average": (14, 0.05), "novice": (22, 0.12)}   # (reaction f, miss)

    @staticmethod
    def human(policy, reaction=14, miss=0.05, seed=0):
        """Human-like step for run_bot (playtests). policy(gb, f) -> set of buttons the player wants
        now ({"right", "a"}); the buttons actually held are that decision `reaction` frames late,
        and each new press is missed with probability `miss` (until the policy re-decides).
        GB.SKILL has presets: GB.human(policy, *GB.SKILL["novice"], seed=3). Compare outcomes over
        several seeds and skills to estimate difficulty: one perfect bot says nothing about players."""
        import random
        rnd, queue, held, missed = random.Random(seed), [], set(), set()

        def step(gb, f):
            want = set(policy(gb, f))
            queue.append(want)
            now = queue.pop(0) if len(queue) > reaction else set()
            missed.intersection_update(now)              # a released button can be pressed again
            for b in now - held - missed:
                if rnd.random() < miss:
                    missed.add(b)
            now = now - missed
            for b in GB.BUTTONS:
                if b in now and b not in held:
                    gb.pyboy.button_press(b)
                elif b in held and b not in now:
                    gb.pyboy.button_release(b)
            held.clear()
            held.update(now)
        return step

    # --- gbe engine selftest ---
    def selftest(self, max_frames=60000):
        """Run the gbe library's asm-vs-C equivalence checks inside the ROM (gbe_selftest.c; the
        game calls gbe_selftest() when gbe_eq_request is set). Returns (mismatches, cases)."""
        self.write_u8("gbe_eq_done", 0)
        self.write_u8("gbe_eq_request", 1)
        for _ in range(max_frames // 100):
            self.frames(100)
            if self.u8("gbe_eq_done"):
                break
        assert self.u8("gbe_eq_done"), "gbe selftest did not finish"
        return self.u16("gbe_eq_mismatch"), self.u16("gbe_eq_count")

    # --- profiling ---
    def profile(self, funcs):
        """Start measuring T-cycles per call of the given C functions (by name).
        Returns a Profiler; call .report() later. Includes time spent in callees and in
        interrupts that fire during the call. Uses PyBoy's private _cycles() (PyBoy 2.8)."""
        return Profiler(self, funcs)

    def worst_frames(self, funcs, frames, step=None, top=3, var="frame_lines"):
        """Play `frames` frames (step(gb, f) presses buttons) and return the `top` frames with the
        highest `var` (scanlines), each as (lines, frame, [(T, func, calls), ...]) sorted by cost.
        The question it answers: what exactly is in the worst frame (games/shmup: the peak was 4
        medium costs at once, not one hot spot; per-call averages hid it)."""
        p = self.profile(funcs)
        prev, out = {}, []
        for f in range(frames):
            if step:
                step(self, f)
            self.frames(1)
            cur = {k: (s["total"], s["calls"]) for k, s in p.stats.items()}
            d = [(cur[k][0] - prev.get(k, (0, 0))[0], k, cur[k][1] - prev.get(k, (0, 0))[1])
                 for k in cur]
            prev = cur
            out.append((self.u8(var), f, sorted((x for x in d if x[0]), reverse=True)))
        p.stop()
        return sorted(out, key=lambda x: -x[0])[:top]

    # --- screen ---
    def screenshot(self, name):
        """Render and save shots/<name>.png. Returns the path. Advances 2 frames: PyBoy draws the
        window one line off on the first rendered frame after unrendered ticks (QA finding)."""
        self._tick(1, True)
        self._tick(1, True)
        self.shots_dir.mkdir(parents=True, exist_ok=True)
        path = self.shots_dir / f"{name}.png"
        self.pyboy.screen.image.save(path)
        return path


def _bank(addr):
    """.noi addresses of banked symbols are bank << 16 | address (games/faro); flat ROMs: 0 / 1."""
    if addr >> 16:
        return addr >> 16
    return 0 if addr < 0x4000 else 1


class Profiler:
    """Hooks function entries; on entry reads the return address from the stack and hooks it
    to catch the return. Stats per function: calls, total, max, and the state of
    `context_var` (a game global, e.g. "state") at the slowest call."""

    def __init__(self, gb, funcs, context_var=None):
        self.gb, self.pb = gb, gb.pyboy
        funcs = list(dict.fromkeys(funcs))   # one hook per address: ignore repeated names
        self.missing = [f for f in funcs if f not in gb.syms]   # renamed/static: reported, not fatal
        funcs = [f for f in funcs if f in gb.syms]
        self.stats = {f: {"calls": 0, "total": 0, "max": 0, "ctx": None} for f in funcs}
        self.pending = {}      # return address -> list of (func, start cycles, context)
        self.ret_hooks = set()
        self.context_var = context_var or ("state" if "state" in gb.syms else None)
        self.cur_bank = gb.syms.get("_current_bank")   # GBDK's copy of the mapped ROM bank
        for f in funcs:
            addr = gb.addr(f)
            self.pb.hook_register(_bank(addr), addr & 0xFFFF, self._on_entry, f)

    def _ctx(self):
        return self.gb.u8(self.context_var) if self.context_var else None

    def _on_entry(self, func):
        pb = self.pb
        sp = pb.register_file.SP
        ret = pb.memory[sp] | (pb.memory[sp + 1] << 8)
        if func not in self.stats:
            return
        self.pending.setdefault(ret, []).append((func, pb._cycles(), self._ctx()))
        # a return into 0x4000-0x7FFF belongs to the bank mapped now (the caller's)
        bank = 0 if ret < 0x4000 else (pb.memory[self.cur_bank] if self.cur_bank and ret < 0x8000 else 1)
        key = (bank << 16) | ret
        if ret >= 0x8000:
            return                                  # code in RAM (no hook possible)
        if key not in self.ret_hooks:
            self.ret_hooks.add(key)
            pb.hook_register(bank, ret, self._on_return, ret)

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
            self.pb.hook_deregister(_bank(addr), addr & 0xFFFF)
        for key in self.ret_hooks:
            self.pb.hook_deregister(key >> 16, key & 0xFFFF)
        self.ret_hooks.clear()

    def report(self):
        """Text table sorted by worst case. 70224 T = 1 frame, 456 T = 1 scanline."""
        lines = [f"{'function':<20}{'calls':>7}{'avg T':>9}{'max T':>9}{'max lines':>11}  ctx"]
        for f, s in sorted(self.stats.items(), key=lambda kv: -kv[1]["max"]):
            avg = s["total"] // s["calls"] if s["calls"] else 0
            lines.append(f"{f:<20}{s['calls']:>7}{avg:>9}{s['max']:>9}{s['max'] / 456:>11.1f}  {s['ctx']}")
        if self.missing:
            lines.append(f"(not found, skipped: {', '.join(self.missing)})")
        return "\n".join(lines)
