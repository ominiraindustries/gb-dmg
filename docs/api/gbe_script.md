# `gbe_script` — gbe_script.c

**Qué hace:** event script VM for `harness/script.py` bytecode (`res/scripts/*.evs`): flags, vars, say/ask/choice, wait, call/ret, game ops by table; runs from any bank, copies text and operands to WRAM first so game ops may be BANKED

**Lo que pone el juego:** `script_game_op()` + `res/scripts/ops.txt`

**Origen y cifras:** world_lab: branches, game op that takes time

**Ficheros:** `harness/common/src/gbe_script.c` — en game.json: `"common_src": ["gbe_script.c"]`

**Juegos que lo usan:** `games/faro`, `games/world_lab`

## Nombres

| Nombre | Comentario |
|---|---|
| `script_bank` | Event script VM for harness/script.py bytecode (res/scripts/*.evs): script_run(SCRIPT_NAME). Game ops: the game implements script_game_op(op) (operands in script_args; return 1 = busy until... |
| `script_active` | (ver `script_bank`) |
| `script_state` | (ver `script_bank`) |
| `script_answer` | (ver `script_bank`) |
| `script_lock` | (ver `script_bank`) |
| `script_args` | (ver `script_bank`) |
| `script_trace` |  |
| `script_trace_n` |  |
| `script_pc` |  |
| `script_game_argn` |  |
| `script_game_op` | provided by the game |
| `script_run` |  |
| `script_run_id` | SID_<NAME> (script_ids.h) |
| `script_resume` |  |
| `script_update` |  |

## Cabecera (`gbe.h`)

```c
// Event script VM for harness/script.py bytecode (res/scripts/*.evs): script_run(SCRIPT_NAME).
// Game ops: the game implements script_game_op(op) (operands in script_args; return 1 = busy until
// script_resume()). script_lock = the script asked to freeze the player.
enum { SS_RUN, SS_WAIT, SS_TBOX, SS_GAME };
extern uint8_t script_bank, script_active, script_state, script_answer, script_lock, script_args[8];
extern uint8_t script_trace[16], script_trace_n;
extern const uint8_t *script_pc;
extern const uint8_t script_game_argn[];
uint8_t script_game_op(uint8_t op);     // provided by the game
void script_run(uint8_t bank, const uint8_t *code);
void script_run_id(uint16_t sid);        // SID_<NAME> (script_ids.h)
void script_resume(void);
void script_update(void);
```

## Notas de implementación

`gbe_script.c`:

> gbe: event script VM - runs the bytecode of harness/script.py (res/scripts/*.evs) from any bank.
> 
> This file is bank-0 code: script_update() maps the script's bank, runs ops until one has to
> wait (text box, frames, a game op that takes time) and restores the bank. Text and operands are
> copied to WRAM BEFORE anything else runs (tbox_text, script_args), so the game ops may live in
> any bank (BANKED). Game ops (opcode >= 0x40, res/scripts/ops.txt) go to the game's
> script_game_op(op) with their operands in script_args (sizes: script_game_argn[], generated);
> it returns 1 when the op takes time: the script waits until the game calls script_resume().
> Jumps are relative (s16 after the operand), so a script needs no base address.
