"""Event scripts and dialogue: res/scripts/*.evs -> bytecode for gbe_script (harness/common/src).

    ; comment
    script tomasa_casa                 a script (C: SCRIPT_TOMASA_CASA = bank, address)
      if flag F_DIARIO goto ya          core ops below; game ops from res/scripts/ops.txt
      speaker "Tomasa"
      say "{N}! Tu abuela me dejo esto para ti."
      give DIARIO 1
      set F_DIARIO
      end
    ya:                                 label (local to its script)
      ask "Cocinamos algo?" no=fin
      cook
    fin:
      end

Text: wrapped at compile time to the box (TEXT_W chars per line, TEXT_LINES lines per page);
"|" forces a new page, {N} = player name (counted as NAME_W chars), "¡" "¿" "," "'" allowed.
No accents or n-tilde (the font has none: the lint says so).
Files next to the scripts:
    flags.txt   one flag name per line (F_...): id = line order. Stable ids = compatible saves.
    vars.txt    one variable name per line (V_...), up to 16.
    ops.txt     game ops: NAME arg arg ... with arg types u8 s8 u16 flag var sym (sym: a name of
                symbols.txt or of the game's data tables) - each becomes opcode 0x40 + line order.
    symbols.txt NAME = value (item ids, actor ids...) until harness/tables.py provides them.

Bytecode (gbe_script.c reads it): opcode byte, operands little-endian, jumps relative to the byte
after the operand (s16), text zero-terminated (0x0A new line, 0x0C new page, 0x01 player name).
"""
import re
from pathlib import Path

TEXT_W, TEXT_LINES, NAME_W, ASK_W, CHOICE_W, SPEAKER_W = 18, 2, 5, 18, 8, 12

# core ops: name -> (opcode, operand types). Types: u8 s8 u16 flag var label text cmp
CORE = {
    "end": (0x00, []),
    "goto": (0x01, ["label"]),
    "call": (0x02, ["label"]),
    "ret": (0x03, []),
    "if_flag": (0x04, ["flag", "label"]),
    "ifn_flag": (0x05, ["flag", "label"]),
    "set": (0x06, ["flag"]),
    "clr": (0x07, ["flag"]),
    "vset": (0x08, ["var", "u8"]),
    "vadd": (0x09, ["var", "s8"]),
    "if_var": (0x0A, ["var", "cmp", "u8", "label"]),
    "say": (0x0B, ["text"]),
    "ask": (0x0C, ["ask", "u8"]),
    "if_answer": (0x0D, ["u8", "label"]),
    "choice": (0x0E, ["choices"]),
    "wait": (0x0F, ["u8"]),
    "sfx": (0x10, ["u8"]),
    "speaker": (0x11, ["speaker"]),
    "rand": (0x12, ["var", "u8"]),
    "lock": (0x13, []),
    "unlock": (0x14, []),
    "close": (0x15, []),
    "vans": (0x16, ["var"]),
}
CMP = {"==": 0, "!=": 1, "<": 2, ">=": 3}
GAME_BASE = 0x40
CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 !?:-./,'¡¿")


class ScriptError(ValueError):
    pass


def _names(path, prefix, limit=None):
    if not path.exists():
        return {}
    out = {}
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        name = raw.split(";", 1)[0].strip()
        if not name:
            continue
        if not name.startswith(prefix):
            raise ScriptError(f"{path}:{n}: '{name}' must start with {prefix}")
        if name in out:
            raise ScriptError(f"{path}:{n}: '{name}' listed twice")
        out[name] = len(out)
    if limit and len(out) > limit:
        raise ScriptError(f"{path}: {len(out)} names, max {limit}")
    return out


class Context:
    """Flags, vars, game ops and symbols of a game's res/scripts folder."""

    def __init__(self, folder, symbols=None):
        folder = Path(folder)
        self.flags = _names(folder / "flags.txt", "F_")
        self.vars = _names(folder / "vars.txt", "V_", 16)
        self.symbols = dict(symbols or {})
        sym_file = folder / "symbols.txt"
        if sym_file.exists():
            for n, raw in enumerate(sym_file.read_text(encoding="utf-8").splitlines(), 1):
                line = raw.split(";", 1)[0].strip()
                if line:
                    k, v = [p.strip() for p in line.split("=")]
                    self.symbols[k] = int(v, 0)
        self.game_ops = {}
        ops_file = folder / "ops.txt"
        if ops_file.exists():
            for raw in ops_file.read_text(encoding="utf-8").splitlines():
                p = raw.split(";", 1)[0].split()
                if p:
                    name = p[0].lower()
                    if name in CORE or name in ("if",):
                        raise ScriptError(f"{ops_file}: game op '{name}' clashes with a core op")
                    self.game_ops[name] = (GAME_BASE + len(self.game_ops), p[1:])

    def argn(self, types):
        return sum(2 if t in ("u16", "flag") else 1 for t in types)


def wrap(text, width=TEXT_W, lines=TEXT_LINES, where=""):
    """-> list of pages, each a list of lines. '|' forces a page; {N} counts NAME_W chars."""
    for ch in text.replace("{N}", ""):
        if ch not in CHARS and ch != "|":
            raise ScriptError(f"{where}: character {ch!r} is not in the font (no accents or n-tilde)")
    pages = []
    for chunk in text.split("|"):
        out, cur, cur_len = [], "", 0
        for word in chunk.split():
            wl = len(word.replace("{N}", "")) + word.count("{N}") * NAME_W
            if wl > width:
                raise ScriptError(f"{where}: word '{word}' longer than {width}")
            if cur and cur_len + 1 + wl > width:
                out.append(cur)
                cur, cur_len = word, wl
            else:
                cur, cur_len = (cur + " " + word if cur else word), cur_len + (1 if cur else 0) + wl
        if cur:
            out.append(cur)
        for i in range(0, len(out), lines):
            pages.append(out[i:i + lines])
    return pages


def encode_text(pages):
    b = bytearray()
    for pi, page in enumerate(pages):
        if pi:
            b.append(0x0C)
        for li, line in enumerate(page):
            if li:
                b.append(0x0A)
            for part in re.split(r"(\{N\})", line):
                if part == "{N}":
                    b.append(0x01)
                else:
                    b += part.replace("¡", "\xa1").replace("¿", "\xbf").encode("latin-1")
    b.append(0)
    return bytes(b)


def _tokens(line):
    return re.findall(r'"[^"]*"|\S+', line)


def compile_file(path, ctx):
    """-> (bytes, {script_name: offset}, lines_of_text) for one .evs file."""
    path = Path(path)
    scripts, cur, items = {}, None, []          # items: (kind, ...) per script
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split(";", 1)[0].strip() if '"' not in raw else _strip_comment(raw)
        if not line:
            continue
        where = f"{path}:{n}"
        if line.startswith("script "):
            cur = line.split()[1].lower()
            if cur in scripts:
                raise ScriptError(f"{where}: script '{cur}' defined twice")
            scripts[cur] = []
            continue
        if cur is None:
            raise ScriptError(f"{where}: code before the first 'script NAME'")
        if re.fullmatch(r"[A-Za-z_]\w*:", line):
            scripts[cur].append(("label", line[:-1].lower(), where))
            continue
        scripts[cur].append(("op", _tokens(line), where))
    blob, offsets = bytearray(), {}
    for name, body in scripts.items():
        offsets[name] = len(blob)
        labels, fixups = {}, []
        for item in body:
            if item[0] == "label":
                if item[1] in labels:
                    raise ScriptError(f"{item[2]}: label '{item[1]}' defined twice")
                labels[item[1]] = len(blob)
                continue
            _emit(blob, item[1], item[2], ctx, fixups)
        for pos, label, where in fixups:
            if label not in labels:
                raise ScriptError(f"{where}: label '{label}' not defined in script '{name}'")
            rel = labels[label] - (pos + 2)
            blob[pos:pos + 2] = (rel & 0xFFFF).to_bytes(2, "little")
        if not body or body[-1][0] != "op" or body[-1][1][0].lower() not in ("end", "goto", "ret"):
            raise ScriptError(f"{path}: script '{name}' must finish with end, goto or ret")
    return bytes(blob), offsets


def _strip_comment(raw):
    out, q = "", False
    for ch in raw:
        if ch == '"':
            q = not q
        if ch == ";" and not q:
            break
        out += ch
    return out.strip()


def _num(tok, where, lo, hi, ctx):
    if tok in ctx.symbols:
        v = ctx.symbols[tok]
    else:
        try:
            v = int(tok, 0)
        except ValueError:
            raise ScriptError(f"{where}: '{tok}' is not a number or a known symbol") from None
    if not lo <= v <= hi:
        raise ScriptError(f"{where}: {v} out of range {lo}..{hi}")
    return v


def _emit(blob, toks, where, ctx, fixups):
    op = toks[0].lower()
    args = toks[1:]
    # sugar: "if flag F goto L" / "if not flag F goto L" / "if V >= 3 goto L" / "ask ... no=L"
    if op == "if":
        if args[:1] == ["flag"] and len(args) == 4 and args[2] == "goto":
            op, args = "if_flag", [args[1], args[3]]
        elif args[:2] == ["not", "flag"] and len(args) == 5 and args[3] == "goto":
            op, args = "ifn_flag", [args[2], args[4]]
        elif len(args) == 5 and args[3] == "goto" and args[1] in CMP:
            op, args = "if_var", [args[0], args[1], args[2], args[4]]
        else:
            raise ScriptError(f"{where}: use 'if flag F goto L', 'if not flag F goto L' or 'if V >= n goto L'")
    jump_no = None
    if op == "ask":
        default = 0
        rest = []
        for a in args[1:]:
            if a.startswith("no="):
                jump_no = a[3:].lower()
            elif a == "default=no":
                default = 1
            else:
                rest.append(a)
        if rest:
            raise ScriptError(f"{where}: ask takes a question, no=LABEL and default=no")
        args = [args[0], str(default)]
    if op in CORE:
        code, types = CORE[op]
    elif op in ctx.game_ops:
        code, types = ctx.game_ops[op]
    else:
        raise ScriptError(f"{where}: unknown op '{op}'")
    if op == "choice":
        if not 2 <= len(args) <= 4:
            raise ScriptError(f"{where}: choice takes 2-4 options")
    elif len(args) != len(types):
        raise ScriptError(f"{where}: '{op}' takes {len(types)} operands ({' '.join(types)}), got {len(args)}")
    blob.append(code)
    if op == "choice":
        blob.append(len(args))
        for a in args:
            t = _text_arg(a, where)
            if len(t) > CHOICE_W:
                raise ScriptError(f"{where}: option '{t}' longer than {CHOICE_W}")
            blob += encode_text([[t]])
        return
    for t, a in zip(types, args):
        if t == "u8":
            blob.append(_num(a, where, 0, 255, ctx))
        elif t == "s8":
            blob.append(_num(a, where, -128, 127, ctx) & 0xFF)
        elif t == "u16":
            blob += _num(a, where, 0, 0xFFFF, ctx).to_bytes(2, "little")
        elif t == "flag":
            if a not in ctx.flags:
                raise ScriptError(f"{where}: flag '{a}' not in flags.txt")
            blob += ctx.flags[a].to_bytes(2, "little")
        elif t == "var":
            if a not in ctx.vars:
                raise ScriptError(f"{where}: variable '{a}' not in vars.txt")
            blob.append(ctx.vars[a])
        elif t == "cmp":
            blob.append(CMP[a])
        elif t == "label":
            fixups.append((len(blob), a.lower(), where))
            blob += b"\0\0"
        elif t == "sym":
            blob.append(_num(a, where, 0, 255, ctx))
        elif t == "text":
            blob += encode_text(wrap(_text_arg(a, where), where=where))
        elif t == "ask":
            q = _text_arg(a, where)
            if len(q.replace("{N}", "")) + q.count("{N}") * NAME_W > ASK_W:
                raise ScriptError(f"{where}: question longer than {ASK_W} (one line)")
            blob += encode_text([[q]])
        elif t == "speaker":
            s = _text_arg(a, where)
            if len(s) > SPEAKER_W:
                raise ScriptError(f"{where}: speaker name longer than {SPEAKER_W}")
            blob += encode_text([[s]] if s else [[""]])
        else:
            raise ScriptError(f"{where}: unknown operand type {t}")
    if jump_no is not None:                 # ask ... no=L  ==  ask ... ; if_answer 1 L
        blob.append(CORE["if_answer"][0])
        blob.append(1)
        fixups.append((len(blob), jump_no, where))
        blob += b"\0\0"


def _text_arg(a, where):
    if not (a.startswith('"') and a.endswith('"')):
        raise ScriptError(f"{where}: expected a \"text\"")
    return a[1:-1]


def convert(folder, out_dir, symbols=None):
    """Compile every res/scripts/*.evs; returns the generated .c files. Writes:
    script_<stem>.c/.h (banked blob + SCRIPT_<NAME> = bank, address), script_ids.h (F_, V_, OP_)
    and script_ops.c (game op operand sizes, bank 0)."""
    folder, out_dir = Path(folder), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ctx = Context(folder, symbols)
    outs, index = [], []                          # index: (sym, offset, name) -> SID_<NAME>
    for evs in sorted(folder.glob("*.evs")):
        blob, offsets = compile_file(evs, ctx)
        sym = f"script_{evs.stem.lower()}"
        for k, v in offsets.items():
            if any(n == k for _, _, n in index):
                raise ScriptError(f"{evs}: script '{k}' also defined in another file")
            index.append((sym, v, k))
        data = ",\n".join("    " + ", ".join(f"0x{b:02X}" for b in blob[i:i + 16]) for i in range(0, len(blob), 16))
        (out_dir / f"{sym}.c").write_text(
            f"// Generated from {evs.name} by harness/script.py - do not edit\n#pragma bank 255\n"
            f"#include <gb/gb.h>\n#include <stdint.h>\n\nconst uint8_t {sym}[{len(blob)}] = {{\n{data}\n}};\n\n"
            f"BANKREF({sym})\n", encoding="utf-8")
        (out_dir / f"{sym}.h").write_text(
            f"// Generated from {evs.name} by harness/script.py - do not edit\n#pragma once\n"
            f"#include <gb/gb.h>\n#include <stdint.h>\n\nextern const uint8_t {sym}[];\nBANKREF_EXTERN({sym})\n"
            + "".join(f"#define SCRIPT_{k.upper()} BANK({sym}), ({sym} + {v})\n" for k, v in offsets.items()),
            encoding="utf-8")
        outs.append(out_dir / f"{sym}.c")
    (out_dir / "script_ids.h").write_text(
        "// Generated by harness/script.py - do not edit\n#pragma once\n\n"
        + "".join(f"#define {k} {v}\n" for k, v in ctx.flags.items())
        + "".join(f"#define {k} {v}\n" for k, v in ctx.vars.items())
        + f"#define SCRIPT_FLAG_COUNT {len(ctx.flags)}\n"
        + "".join(f"#define OP_{k.upper()} {v[0] - GAME_BASE}\n" for k, v in ctx.game_ops.items()),
        encoding="utf-8")
    syms = sorted({sym for sym, _, _ in index})
    refs = "".join(f"    {{ &__bank_{x}, {x} + {v} }},   // {i} {n}\n" for i, (x, v, n) in enumerate(index))
    (out_dir / "script_index.c").write_text(
        "// Generated by harness/script.py - do not edit: SID_<NAME> -> { bank, address }\n"
        "#pragma bank 255\n#include \"gbe.h\"\n"
        + "".join(f"BANKREF_EXTERN({x})\nextern const uint8_t {x}[];\n" for x in syms)
        + "\nconst gbe_ref_t script_index[] = {\n" + (refs or "    { 0, 0 }\n") + "};\n\nBANKREF(script_index)\n",
        encoding="utf-8")
    outs.append(out_dir / "script_index.c")
    with open(out_dir / "script_ids.h", "a", encoding="utf-8") as f:
        f.write("".join(f"#define SID_{n.upper()} {i}\n" for i, (_, _, n) in enumerate(index)))
    argn = [ctx.argn(t) for _, t in ctx.game_ops.values()] or [0]
    (out_dir / "script_ops.c").write_text(
        "// Generated by harness/script.py - do not edit\n#include <stdint.h>\n\n"
        f"const uint8_t script_game_argn[] = {{ {', '.join(map(str, argn))} }};   // operand bytes per game op\n",
        encoding="utf-8")
    outs.append(out_dir / "script_ops.c")
    return outs
