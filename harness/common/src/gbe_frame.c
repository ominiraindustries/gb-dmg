// gbe: frame loop helpers - input edges, frame budget measurement, VRAM-late guard
#include "gbe.h"

uint8_t keys, prev_keys, pressed;
uint8_t frame_start, frame_lines, max_frame_lines, skip_measure, vram_late;
uint8_t vram_late_ly, vram_late_ly0;     // tests: LY when the copies ended late / when vsync() returned

void frame_begin(void) {
    frame_start = (uint8_t)sys_time;
    prev_keys = keys;
    keys = joypad();
    pressed = keys & ~prev_keys;
}

// VBlank copies must finish before LY wraps to 0: writes in mode 3 are silently lost
uint8_t frame_vsync_ly;
void frame_vram_check(void) {
    if (LY_REG < 144) { vram_late++; vram_late_ly = LY_REG; vram_late_ly0 = frame_vsync_ly; }
}

// Scanlines used since vsync() returned (VBlank starts at LY 144). 255 = missed a frame.
// Frames that redraw with the LCD off on purpose set skip_measure.
void frame_end(void) {
    uint8_t ly = LY_REG;
    if (skip_measure) {
        skip_measure = 0;
        return;
    }
    if ((uint8_t)sys_time != frame_start) frame_lines = 255;
    else frame_lines = ly >= 144 ? ly - 144 : ly + 10;
    if (frame_lines > max_frame_lines) max_frame_lines = frame_lines;
}
