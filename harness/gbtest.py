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
    for line in Path(path).read_text().splitlines():
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

    # --- screen ---
    def screenshot(self, name):
        """Render the current frame and save it as shots/<name>.png. Returns the path."""
        self.pyboy.tick(1, True)
        self.shots_dir.mkdir(parents=True, exist_ok=True)
        path = self.shots_dir / f"{name}.png"
        self.pyboy.screen.image.save(path)
        return path
