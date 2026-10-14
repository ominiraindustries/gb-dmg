// gbe: event script VM - runs the bytecode of harness/script.py (res/scripts/*.evs) from any bank.
//
// This file is bank-0 code: script_update() maps the script's bank, runs ops until one has to
// wait (text box, frames, a game op that takes time) and restores the bank. Text and operands are
// copied to WRAM BEFORE anything else runs (tbox_text, script_args), so the game ops may live in
// any bank (BANKED). Game ops (opcode >= 0x40, res/scripts/ops.txt) go to the game's
// script_game_op(op) with their operands in script_args (sizes: script_game_argn[], generated);
// it returns 1 when the op takes time: the script waits until the game calls script_resume().
// Jumps are relative (s16 after the operand), so a script needs no base address.
#include <string.h>
#include "gbe.h"

#define SC_STACK 8
#define SC_STEPS 64                         // ops per frame at most (a 'goto self' cannot hang)

uint8_t script_bank, script_active, script_state, script_wait, script_answer, script_lock;
const uint8_t *script_pc;
const uint8_t *script_stack[SC_STACK];
uint8_t script_sp;
uint8_t script_args[8];
uint8_t script_trace[16], script_trace_n;   // last opcodes run (tests)
uint16_t script_steps;                      // ops run since boot (tests)

static uint8_t rd8(void) { return *script_pc++; }
static uint16_t rd16(void) { uint16_t v = script_pc[0] | ((uint16_t)script_pc[1] << 8); script_pc += 2; return v; }
static void jump(void) { int16_t rel = (int16_t)rd16(); script_pc += rel; }
static void skip16(void) { script_pc += 2; }

// copy zero-terminated text at pc into tbox_text (several strings for a choice)
static void copy_text(uint8_t n) {
    uint8_t i = 0;
    char c;
    while (n--) {
        do { c = (char)*script_pc++; if (i < sizeof(tbox_text) - 1) tbox_text[i++] = c; } while (c);
    }
    tbox_text[i] = 0;
}

void script_run(uint8_t bank, const uint8_t *code) {
    script_bank = bank;
    script_pc = code;
    script_sp = 0;
    script_active = 1;
    script_state = SS_RUN;
}

void script_resume(void) {
    if (script_state == SS_GAME) script_state = SS_RUN;
}

static void finish(void) {
    script_active = 0;
    script_lock = 0;
    tbox_close();
}

static void step(void) {
    uint8_t op = rd8(), v, n;
    script_trace[script_trace_n++ & 15] = op;
    script_steps++;
    switch (op) {
    case 0x00: finish(); break;                                    // end
    case 0x01: jump(); break;                                      // goto
    case 0x02:                                                     // call
        if (script_sp < SC_STACK) script_stack[script_sp++] = script_pc + 2;
        jump();
        break;
    case 0x03:                                                     // ret
        if (script_sp) script_pc = script_stack[--script_sp]; else finish();
        break;
    case 0x04:                                                     // if_flag f L
    case 0x05:                                                     // ifn_flag f L
        v = flag_get(rd16()) ? 1 : 0;
        if (v == (op == 0x04)) jump(); else skip16();
        break;
    case 0x06: flag_set(rd16()); break;                            // set
    case 0x07: flag_clr(rd16()); break;                            // clr
    case 0x08: v = rd8(); vars[v] = rd8(); break;                  // vset
    case 0x09: v = rd8(); vars[v] += rd8(); break;                 // vadd (s8, wraps)
    case 0x0A:                                                     // if_var v cmp n L
        v = vars[rd8()];
        op = rd8();
        n = rd8();
        if ((op == 0 && v == n) || (op == 1 && v != n) || (op == 2 && v < n) || (op == 3 && v >= n)) jump();
        else skip16();
        break;
    case 0x0B:                                                     // say text
        copy_text(1);
        tbox_start(TB_SAY);
        script_state = SS_TBOX;
        break;
    case 0x0C:                                                     // ask text default
        copy_text(1);
        v = rd8();
        tbox_start(TB_ASK);
        tbox_answer = v;
        script_state = SS_TBOX;
        break;
    case 0x0D:                                                     // if_answer n L
        if (script_answer == rd8()) jump(); else skip16();
        break;
    case 0x0E:                                                     // choice n texts
        tbox_nchoices = rd8();
        copy_text(tbox_nchoices);
        tbox_start(TB_CHOICE);
        script_state = SS_TBOX;
        break;
    case 0x0F:                                                     // wait n
        script_wait = rd8();
        if (script_wait) script_state = SS_WAIT;
        break;
    case 0x10: sfx(rd8()); break;                                  // sfx
    case 0x11: copy_text(1); tbox_speaker_set(tbox_text); break;   // speaker
    case 0x12: v = rd8(); vars[v] = rng_range(rd8()); break;       // rand v n
    case 0x13: script_lock = 1; break;                             // lock
    case 0x14: script_lock = 0; break;                             // unlock
    case 0x15: tbox_close(); break;                                // close
    case 0x16: vars[rd8()] = script_answer; break;                 // vans v
    default:                                                       // game op
        if (op >= 0x40) {
            op -= 0x40;
            n = script_game_argn[op];
            memcpy(script_args, script_pc, n);
            script_pc += n;
            if (script_game_op(op)) script_state = SS_GAME;
        } else finish();                                           // bad opcode: stop
    }
}

// Once per frame (outside VBlank), after tbox_update()
void script_update(void) {
    uint8_t saved, k;
    if (!script_active) return;
    if (script_state == SS_WAIT) { if (--script_wait) return; script_state = SS_RUN; }
    else if (script_state == SS_TBOX) {
        if (tbox_state != TB_OPEN) return;
        script_answer = tbox_answer;
        script_state = SS_RUN;
    } else if (script_state == SS_GAME) return;
    saved = CURRENT_BANK;
    SWITCH_ROM(script_bank);
    for (k = 0; k < SC_STEPS && script_active && script_state == SS_RUN; k++) step();
    SWITCH_ROM(saved);
}
