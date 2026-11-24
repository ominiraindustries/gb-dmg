"""Watchdog for stuck background work (Windows; ported from the SNES harness, 2026-11-24).

Lists, and with --kill ends, processes that outlived their purpose:
  * wait loops: bash -c commands with `until ...; do sleep` / `while ...; do sleep` older than --wait-min;
  * emulators and test runs: Mesen.exe --testrunner, harness/gbrun.py, and pytest/gb.py test runs older than
    --run-min (a headless run never takes that long). An interactive Mesen or `gb.py run` window is the user's.
Default is report-only. Never touches builds (lcc, sdcc), nor anything younger than the limits.

Usage: python -I harness/scripts/bgwatch.py [--wait-min 90] [--run-min 45] [--kill]
"""
import argparse
import re
import subprocess
import sys
import time


def procs():
    ps = ("Get-CimInstance Win32_Process | ForEach-Object { '{0}|{1}|{2}|{3}' -f $_.ProcessId,$_.Name,"
          "[int]((Get-Date)-$_.CreationDate).TotalMinutes,($_.CommandLine -replace '\\s+',' ') }")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout
    for line in out.splitlines():
        p = line.split("|", 3)
        if len(p) == 4 and p[0].isdigit():
            yield int(p[0]), p[1], int(p[2]), p[3]


WAIT = re.compile(r"\b(until|while)\b.*\bdo\s+sleep\b")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wait-min", type=int, default=90)
    ap.add_argument("--run-min", type=int, default=45)
    ap.add_argument("--kill", action="store_true")
    a = ap.parse_args()
    stale = []
    for pid, name, age, cmd in procs():
        n = name.lower()
        if n in ("bash.exe", "sh.exe") and age >= a.wait_min and WAIT.search(cmd):
            stale.append((pid, name, age, "wait loop", cmd[-110:]))
        elif n == "mesen.exe" and age >= a.run_min and "--testrunner" in cmd:   # an interactive Mesen is the user's
            stale.append((pid, name, age, "emulator", cmd[:110]))
        elif n.startswith("python") and age >= a.run_min and "gbrun.py" in cmd:
            stale.append((pid, name, age, "gbrun", cmd[:110]))
        elif n.startswith("python") and age >= a.run_min and ("pytest" in cmd or " gb.py test" in cmd):
            stale.append((pid, name, age, "tests", cmd[:110]))
    if not stale:
        print("bgwatch: nothing stuck")
        return 0
    for pid, name, age, kind, cmd in stale:
        print(f"{pid} {name} {age}min [{kind}] ...{cmd}")
    if a.kill:
        for pid, *_ in stale:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        print(f"bgwatch: ended {len(stale)} process(es)")
    else:
        print(f"bgwatch: {len(stale)} stuck; run again with --kill to end them")
    return 0


if __name__ == "__main__":
    sys.exit(main())
