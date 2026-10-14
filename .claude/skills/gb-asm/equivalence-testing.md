# Equivalence testing C vs asm (and measuring cycles) with our harness

Everything here was built and run in a throwaway copy of `harness/template` (pytest via the
repo's `conftest.py` `gb` fixture, PyBoy 2.8.1). The `eqtest.c` and `test_asm.py` below were
extracted verbatim from this file into such a game and passed; a larger 5-function version
passed too, and an injected bug
(`ld b, #7` instead of `#8` in `mul8x8`) was caught with the first failing input reported
(`fn 2 a=1 b=1 C=0x0001 asm=0x0000`).

## Design

- The game keeps **both** versions with the same prototype: `foo_c` (C, the spec) and `foo`
  (asm). The game itself calls `foo`.
- `src/eqtest.c` has `eq_run()`: it calls both over many inputs inside the ROM (so the real
  compiler-generated calling code is exercised) and writes counters to **non-static globals**.
- The main loop runs `eq_run()` only when the test sets `eq_request = 1` through PyBoy's
  memory, so normal play and other tests are unaffected (cost: one byte test per frame).
- pytest triggers it, waits for `eq_done`, asserts `eq_mismatch == 0`, prints the first
  failing input, and re-computes a checksum in Python as an **independent oracle** (C and asm
  could be wrong in the same way).
- Inputs: exhaustive when the input space is 2^16 or less (all 8-bit x 8-bit pairs = 65536
  cases: about 1 s of wall time in PyBoy for 3 functions), otherwise a seeded xorshift PRNG
  (reproducible) plus explicit edge cases: 0, 1, 0x7F, 0x80, 0xFF, 0xFFFF, length 0, max
  length, buffers crossing a 256-byte page.
- **Read results only after a done flag.** A global sampled at an arbitrary frame boundary may
  be mid-update (PyBoy's frame ends at VBlank, right where the main loop restarts).

## 1. Shared header `src/fast.h`

```c
#include <stdint.h>
uint16_t mul8x8_c(uint8_t a, uint8_t b);              // C reference (fast_c.c)
uint16_t mul8x8(uint8_t a, uint8_t b);                // asm port (fast.s)
uint16_t sum_bytes_c(const uint8_t *p, uint8_t n);
uint16_t sum_bytes(const uint8_t *p, uint8_t n);
```
(The verified example with five functions, the `.s` file and the C references is in
calling-convention.md.)

## 2. `src/eqtest.c`

```c
// eqtest.c - equivalence check C vs asm, triggered by the test (eq_request = 1)
#include "fast.h"

// Results, read by tests through the .noi file (must be non-static)
uint8_t  eq_request;     // test writes 1 -> main loop calls eq_run()
uint8_t  eq_done;        // 1 when finished
uint16_t eq_checked;     // number of comparisons (wraps at 65536: compare modulo)
uint16_t eq_mismatch;    // must be 0
uint8_t  eq_fail_id;     // which function failed first (0 = none)
uint8_t  eq_fail_a, eq_fail_b;   // inputs of the first failure
uint16_t eq_fail_c, eq_fail_asm; // C result vs asm result of the first failure
uint16_t eq_chk_mul;     // checksums of asm results, re-computed in Python
uint16_t eq_chk_sum;

static uint8_t buf[256];
static uint16_t rng = 0xACE1;   // fixed seed -> reproducible inputs

static uint8_t rnd8(void) {     // 16-bit xorshift (7, 9, 8); mirrored in Python
    rng ^= rng << 7;
    rng ^= rng >> 9;
    rng ^= rng << 8;
    return (uint8_t)rng;
}

static void check(uint8_t id, uint8_t a, uint8_t b, uint16_t c_res, uint16_t asm_res) {
    eq_checked++;
    if (c_res != asm_res) {
        if (!eq_mismatch) {
            eq_fail_id = id; eq_fail_a = a; eq_fail_b = b;
            eq_fail_c = c_res; eq_fail_asm = asm_res;
        }
        eq_mismatch++;
    }
}

void eq_run(void) {
    uint8_t a, b, n;
    uint16_t r;
    eq_checked = eq_mismatch = 0; eq_fail_id = 0;
    eq_chk_mul = eq_chk_sum = 0;

    // exhaustive: all 65536 (a, b) pairs (do/while so 255 is included)
    a = 0;
    do {
        b = 0;
        do {
            r = mul8x8(a, b);
            check(1, a, b, mul8x8_c(a, b), r);
            eq_chk_mul += r;
        } while (++b);
    } while (++a);

    // random buffers + edge lengths
    for (b = 0; b != 64; b++) {
        for (n = 0; n != 255; n++) buf[n] = rnd8();
        buf[255] = rnd8();
        a = rnd8();                          // length
        if (b == 0) a = 0;                   // edge: empty
        if (b == 1) a = 255;                 // edge: max
        r = sum_bytes(buf, a);
        check(2, a, b, sum_bytes_c(buf, a), r);
        eq_chk_sum += r;
    }
    eq_done = 1;
}

// One call of each version with fixed args, for cycle measurement from Python
volatile uint16_t bench_sink;
void bench_run(void) {
    bench_sink = mul8x8_c(200, 123);
    bench_sink = mul8x8(200, 123);
    bench_sink = sum_bytes_c(buf, 100);
    bench_sink = sum_bytes(buf, 100);
}
```

## 3. Hook into the game's main loop (`src/main.c`)

```c
extern uint8_t eq_request;
void eq_run(void);
uint8_t bench_request;
void bench_run(void);
...
    while (1) {
        ... game logic ...
        if (eq_request) { eq_request = 0; eq_run(); }
        if (bench_request) { bench_request = 0; bench_run(); }
        vsync();
    }
```
`eq_run()` takes many frames; the game simply freezes meanwhile (fine for a test).

## 4. `tests/test_asm.py`

```python
"""Equivalence and cycle checks for the asm ports in src/*.s."""


def run_request(gb, flag, done=None, max_frames=3000):
    """Write 1 to a request global; the main loop runs the job on its next iteration.
    Waits until `done` becomes non-zero (or, without `done`, until the flag is cleared)."""
    gb.pyboy.memory[gb.addr(flag)] = 1
    for _ in range(max_frames // 10):
        gb.frames(10)
        if done is None and gb.u8(flag) == 0:
            return
        if done is not None and gb.u8(done):
            return
    raise AssertionError(f"{flag}: job did not finish in {max_frames} frames")


def rom_bank(addr):
    return 0 if addr < 0x4000 else 1   # verified for no-MBC ROMs; with an MBC use the code's bank


def measure_cycles(gb, func, trigger, max_frames=10):
    """T-cycles from the first instruction of `func` until execution is back in the caller
    (includes func's ret, excludes the call: add 24 T for the call itself).
    Measures the first call after `trigger()` makes the game call it. Uses PyBoy hooks and
    the private PyBoy._cycles() (PyBoy 2.8.1). An interrupt inside func adds its cost:
    re-measure or disable interrupts in the bench if numbers look noisy."""
    pb, res = gb.pyboy, {}
    entry = gb.addr(func)

    def on_ret(_):
        if "end" not in res:
            res["end"] = pb._cycles()

    def on_entry(_):
        if "start" in res:
            return
        res["start"] = pb._cycles()
        sp = pb.register_file.SP
        ret = pb.memory[sp] | (pb.memory[sp + 1] << 8)   # return address on the stack
        res["ret"] = ret
        pb.hook_register(rom_bank(ret), ret, on_ret, None)

    pb.hook_register(rom_bank(entry), entry, on_entry, None)
    try:
        trigger()
        gb.frames(max_frames)
    finally:
        pb.hook_deregister(rom_bank(entry), entry)
        if "ret" in res:
            pb.hook_deregister(rom_bank(res["ret"]), res["ret"])
    assert "end" in res, f"{func} was not called/returned"
    return res["end"] - res["start"]


def xorshift_stream(seed=0xACE1):
    """Same generator as rnd8() in eqtest.c."""
    r = seed
    while True:
        r ^= (r << 7) & 0xFFFF
        r ^= r >> 9
        r ^= (r << 8) & 0xFFFF
        yield r & 0xFF


def test_asm_matches_c(gb):
    run_request(gb, "eq_request", done="eq_done")
    assert gb.u16("eq_checked") == (65536 + 64) & 0xFFFF
    assert gb.u16("eq_mismatch") == 0, (
        f"fn {gb.u8('eq_fail_id')} a={gb.u8('eq_fail_a')} b={gb.u8('eq_fail_b')} "
        f"C={gb.u16('eq_fail_c'):#06x} asm={gb.u16('eq_fail_asm'):#06x}")
    # Independent oracle
    assert gb.u16("eq_chk_mul") == (sum(range(256)) ** 2) & 0xFFFF
    rnd = xorshift_stream()
    chk = 0
    for b in range(64):
        buf = [next(rnd) for _ in range(256)]
        n = next(rnd)
        n = 0 if b == 0 else 255 if b == 1 else n
        chk += sum(buf[:n])
    assert gb.u16("eq_chk_sum") == chk & 0xFFFF


def test_asm_is_faster(gb):
    trig = lambda: gb.pyboy.memory.__setitem__(gb.addr("bench_request"), 1)
    c = measure_cycles(gb, "mul8x8_c", trig)
    asm = measure_cycles(gb, "mul8x8", trig)
    print(f"\nmul8x8(200,123): C {c} T, asm {asm} T")   # see with pytest -s
    assert asm < c
```

Run: `python harness/gb.py test <game>` (add `-s` after the game name to see the printed
cycle numbers: `python harness/gb.py test <game> -s`).

Measured in the verified build: `add_u8` 20 T (= `add a,e` 4 + `ret` 16, exact),
`mul8x8(200,123)` C 468 T / asm 404 T (asm matches the hand count from opcodes.json exactly),
`sum_bytes(buf,100)` C 7648 T / asm 4472 T.

## Adapting the template

- **Function with pointer output** (e.g. `void decode(uint8_t *dst, const uint8_t *src)`):
  give each version its own output buffer (`out_c[]`, `out_asm[]`), run both on the same
  input, compare buffers byte by byte; also fill both outputs with a canary (0xA5) first and
  check bytes beyond the expected length stay 0xA5 (catches overruns).
- **Function with side effects on globals**: snapshot the globals, run C, save results,
  restore the snapshot, run asm, compare.
- **16-bit inputs**: 2^32 is too many; use edge values (0, 1, 0x00FF, 0x0100, 0x7FFF, 0x8000,
  0xFFFF) crossed with each other plus a few thousand PRNG pairs.
- **Signed types**: include -128, -1, 0, 1, 127 and check the sign extension of the result.
- **Several functions**: one `check(id, ...)` call per function; `eq_fail_id` tells which.
- Exhaustive loops over 65536 cases take ~1 s per handful of functions; more is fine but keep
  `max_frames` in `run_request` large enough (3 functions x 65536 cases finished within the
  default 3000).
- Keep `eq_run()` and `bench_run()` in the ROM permanently; they are the regression test for
  every later change to the asm.

## Measuring without PyBoy hooks

- Static count: `tools/gbdk/bin/lcc.exe -Wa-l -c -o x.o src/fast.s` writes `x.lst` with
  `[cycles]` per instruction (taken value for conditionals). Same with a `.c` file to see
  the compiled C.
- Frame-level: count how many frames a job takes, or read `LY` (0xFF44) before and after
  in the ROM (one line = 456 T) for a rough in-game profiler.
