// CABALLERITO - main loop, interrupts, screen setup
#include "game.h"
#include "level1_1.h"

uint8_t state;
uint8_t keys, prev_keys, pressed;
uint8_t frame_start, frame_lines, max_frame_lines, skip_measure, vram_late;
uint8_t cheat_flags;
uint8_t hud_cut;                // 1: the LYC ISR cuts the window at line 15 (HUD on top)
uint8_t time_tick;

extern uint8_t player_dead;

#define TIME_START 300
#define FRAMES_PER_TIME_UNIT 24

// Line 15 (LYC): wait for HBlank, then window off and sprites on in a single write (ui.md §2)
void lcd_isr(void) {
    if (!hud_cut) return;
    while (STAT_REG & STATF_BUSY) ;
    LCDC_REG = (LCDC_REG & ~LCDCF_WINON) | LCDCF_OBJON;
}

// Start of VBlank: same moment GBDK DMAs the shadow OAM, so BG and sprites move together
void vbl_isr(void) {
    SCX_REG = scx_shadow;
    if (hud_cut) LCDC_REG = (LCDC_REG | LCDCF_WINON) & ~LCDCF_OBJON;
}

void draw_vram(void) {
    level_draw_vram();
    hud_draw_vram();
    if (LY_REG < 144) vram_late++;
}

// LCD off: load everything for the level and place Teo at the 'x' object
void start_level(void) {
    uint8_t i;
    DISPLAY_OFF;
    hide_sprites_range(0, 40);
    level_load();
    actors_clear();
    time_units = TIME_START;
    time_tick = 0;
    hud_init();
    for (i = 0; i < LEVEL1_1_OBJ_COUNT; i++) {
        if (level1_1_obj_type[i] == OBJ_START) {
            player_spawn((uint16_t)level1_1_obj_col[i] << 4,
                         Y_BIAS + (level1_1_obj_row[i] << 4));
        }
    }
    SCY_REG = 0xF0;             // level row 0 at screen line 16, below the HUD
    SCX_REG = 0;
    WX_REG = 7;
    WY_REG = 0;
    hud_cut = 1;
    state = STATE_PLAY;
    skip_measure = 1;
    DISPLAY_ON;
}

void update_timer(void) {
    if (cheat_flags & CHEAT_NO_TIMER) return;
    if (++time_tick >= FRAMES_PER_TIME_UNIT) {
        time_tick = 0;
        if (time_units) {
            time_units--;
            hud_set_time(time_units);
        }
    }
}

// Scanlines used since vsync() returned (VBlank starts at LY 144). 255 = missed a frame.
void measure_frame(void) {
    uint8_t ly = LY_REG;
    if (skip_measure) {
        skip_measure = 0;
        return;
    }
    if ((uint8_t)sys_time != frame_start) frame_lines = 255;
    else frame_lines = ly >= 144 ? ly - 144 : ly + 10;
    if (frame_lines > max_frame_lines) max_frame_lines = frame_lines;
}

void init(void) {
    DISPLAY_OFF;
    BGP_REG = 0xE4;
    OBP0_REG = 0xE4;
    OBP1_REG = 0xD8;            // SHOT form: shades 1 and 2 swapped (spr.tiles notes)
    set_bkg_data(0, BG_COUNT, bg_tiles);
    set_bkg_data(TILE_FONT, FONT_COUNT, font_tiles);
    set_bkg_data(TILE_UI, UI_ICON_TIMES + 1, ui_tiles);   // HUD group only during play
    set_sprite_data(0, SPR_COUNT, spr_tiles);
    SPRITES_8x16;
    SHOW_BKG;
    SHOW_WIN;
    CRITICAL {
        STAT_REG = STATF_LYC;
        LYC_REG = 15;
        add_LCD(lcd_isr);
        add_LCD(nowait_int_handler);
        add_VBL(vbl_isr);
    }
    set_interrupts(VBL_IFLAG | LCD_IFLAG);
    sound_init();
    world = 1;
    stage = 1;
    lives = 3;
    coins = 0;
}

void main(void) {
    init();
    start_level();
    while (1) {
        vsync();
        frame_start = (uint8_t)sys_time;
        draw_vram();
        prev_keys = keys;
        keys = joypad();
        pressed = keys & ~prev_keys;
        if (state == STATE_PLAY) {
            if (player_freeze) {
                player_update();            // power-up / damage animation: everything else waits
            } else {
                player_update();
                actors_update();
                level_update_camera();
                update_timer();
            }
            if (player_dead) start_level();   // DYING/lives come in step 3
        }
        sound_update();
        player_draw();
        actors_draw();
        measure_frame();
    }
}
