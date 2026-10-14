// CABALLERITO - main loop, interrupts, game states
#include "game.h"
#include "level1_1.h"

uint8_t state;
uint8_t keys, prev_keys, pressed;
uint8_t frame_start, frame_lines, max_frame_lines, skip_measure, vram_late;
uint8_t cheat_flags;
uint8_t hud_cut;                // 1: the LYC ISR cuts the window at line 15 (HUD on top)
uint8_t time_tick;
uint8_t checkpoint, checkpoint_col;
uint8_t dying_timer, pause_timer;
uint8_t death_y, death_ys;
int16_t death_vy;

#define TIME_START 300
#define TIME_HURRY 100
#define FRAMES_PER_TIME_UNIT 24
#define DYING_FREEZE 30
#define PIT_WAIT 60

// Line 15 (LYC): wait for HBlank, then window off and sprites on in a single write (ui.md §2)
void lcd_isr(void) {
    if (!hud_cut) return;
    while (STAT_REG & STATF_BUSY) ;
    LCDC_REG = (LCDC_REG & ~LCDCF_WINON) | LCDCF_OBJON;
}

// Start of VBlank: same moment GBDK DMAs the shadow OAM, so BG and sprites move together.
// Palettes from the fade shadows; the window comes back on for the HUD.
void vbl_isr(void) {
    SCX_REG = scx_shadow;
    BGP_REG = bgp_shadow;
    OBP0_REG = obp0_shadow;
    OBP1_REG = obp1_shadow;
    if (hud_cut) LCDC_REG = (LCDC_REG | LCDCF_WINON) & ~LCDCF_OBJON;
}

void draw_vram(void) {
    level_draw_vram();
    hud_draw_vram();
    ui_draw_vram();
    if (LY_REG < 144) vram_late++;
}

// LCD off (called by the INTRO screen): level, enemies and Teo at the start or the checkpoint
void load_level(void) {
    uint8_t i, start_col = 0, start_row = 6;
    uint16_t cam = 0;
    checkpoint_col = 0;
    for (i = 0; i < LEVEL1_1_OBJ_COUNT; i++) {
        if (level1_1_obj_type[i] == OBJ_START) {
            start_col = level1_1_obj_col[i];
            start_row = level1_1_obj_row[i];
        } else if (level1_1_obj_type[i] == OBJ_CHECKPOINT) {
            checkpoint_col = level1_1_obj_col[i];
        }
    }
    if (checkpoint) {
        start_col = checkpoint_col;
        start_row = 6;
        cam = ((uint16_t)start_col << 4) - 64;
    }
    level_load(cam);
    actors_clear();
    enemies_reset(camera_x);
    goal_reset();
    player_spawn((uint16_t)start_col << 4, Y_BIAS + (start_row << 4));
    time_units = TIME_START;
    time_tick = 0;
    hud_pause(0);
    hud_init();
}

void new_game(void) {
    uint8_t i;
    for (i = 0; i < 3; i++) score[i] = 0;
    lives = 3;
    coins = 0;
    checkpoint = 0;
    transition(SCR_INTRO);
}

uint8_t blink_tick;

void update_timer(void) {
    if (time_units <= TIME_HURRY) hud_time_icon(!((++blink_tick) & 16));   // blink every 16 f
    if (cheat_flags & CHEAT_NO_TIMER) return;
    if (++time_tick >= FRAMES_PER_TIME_UNIT) {
        time_tick = 0;
        if (time_units) {
            time_units--;
            hud_set_time(time_units);
            if (time_units == TIME_HURRY) sfx(SFX_HURRY);
            if (time_units == 0) player_kill();
        }
    }
}

void start_dying(void) {
    state = STATE_DYING;
    hud_time_icon(1);
    sfx(SFX_DEATH);
    if (player_dead == 1) {                       // pit: no animation, just wait
        dying_timer = PIT_WAIT;
        hide_sprites_range(0, 4);
    } else {
        dying_timer = DYING_FREEZE + 90;
        death_y = player_y + (player_form == FORM_SMALL ? 0 : 16);
        death_ys = 0;
        death_vy = -0x0400;
    }
}

void update_dying(void) {
    uint8_t ox;
    if (player_dead == 2 && dying_timer <= 90) {  // after the freeze: jump up and fall off
        uint16_t t = (uint16_t)death_ys + (uint8_t)death_vy;
        death_ys = (uint8_t)t;
        death_y += (int8_t)(death_vy >> 8) + (t >> 8);
        death_vy += 0x0040;
    }
    if (player_dead == 2) {
        ox = (uint8_t)(player_x - camera_x) + 8;
        if (death_y > 200 && death_vy > 0) hide_sprites_range(0, 4);
        else {
            oam16(0, ox, death_y, SPR_TEO_SMALL_DEATH, 0);
            hide_sprites_range(2, 4);
        }
    }
    if (--dying_timer == 0) {
        lives--;
        hud_set_lives();
        transition(lives ? SCR_INTRO : SCR_GAMEOVER);
    }
}

void update_play(void) {
    if (pressed & J_START) {                      // pause (ui.md §5)
        state = STATE_PAUSE;
        pause_timer = 0;
        hud_time_icon(1);
        hud_pause(1);
        sfx(SFX_PAUSE);
        return;
    }
    if (player_freeze) {
        player_update();                          // power-up / damage animation: rest waits
    } else {
        player_update();
        if (goal_check()) return;
        enemies_update();
        actors_update();
        level_update_camera();
        update_timer();
        if (!checkpoint && checkpoint_col && player_x >= ((uint16_t)checkpoint_col << 4))
            checkpoint = 1;
    }
    if (player_dead) start_dying();
}

void update_pause(void) {
    if (pressed & J_START) {
        hud_pause(0);
        state = STATE_PLAY;
        return;
    }
    if (++pause_timer == 30) hud_pause(2);        // blink 30 visible / 30 hidden
    else if (pause_timer == 60) { hud_pause(1); pause_timer = 0; }
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

// ---------------------------------------------------------------- asm equivalence test hook
// Tests set eq_request = 1, then read eq_mismatch / eq_done (gb-asm skill procedure)
uint8_t eq_request, eq_done;
uint16_t eq_mismatch, eq_count;
uint8_t mt_at_c(uint16_t x, uint8_t y);
uint8_t solid_at_c(uint16_t x, uint8_t y);
void act_move_c(uint8_t i);
extern uint16_t level_px_w;
extern uint8_t act_xs[], act_ys[];

static void eq_act_move(void) {
    uint8_t s = ACT_MAX - 1, k, xs0, ys0, y0, xs1, ys1, y1;
    uint16_t x0, x1;
    int16_t v;
    for (v = -0x0480; v <= 0x0480; v += 0x0013) {
        for (k = 0; k < 10; k++) {
            xs0 = k * 25;
            x0 = 0xFF80 + (uint16_t)k * 75;
            y0 = 250 - k * 25;
            ys0 = xs0 ^ 0x5A;
            act_x[s] = x0; act_xs[s] = xs0; act_y[s] = y0; act_ys[s] = ys0;
            act_vx[s] = v; act_vy[s] = -v;
            act_move(s);
            x1 = act_x[s]; xs1 = act_xs[s]; y1 = act_y[s]; ys1 = act_ys[s];
            act_x[s] = x0; act_xs[s] = xs0; act_y[s] = y0; act_ys[s] = ys0;
            act_move_c(s);
            if (act_x[s] != x1 || act_xs[s] != xs1 || act_y[s] != y1 || act_ys[s] != ys1) eq_mismatch++;
            eq_count++;
        }
    }
    act_type[s] = T_NONE;
}

void prepare_column(uint16_t tc);
void prepare_column_c(uint16_t tc);
extern uint8_t col_buf[], col_pending;
extern uint8_t level_cols;

// column fill asm vs C over every tile column of the level
static void eq_columns(void) {
    uint16_t tc;
    uint8_t ref[16], r;
    for (tc = 0; tc < (uint16_t)level_cols << 1; tc++) {
        prepare_column_c(tc);
        for (r = 0; r < 16; r++) ref[r] = col_buf[r];
        prepare_column(tc);
        for (r = 0; r < 16; r++) if (col_buf[r] != ref[r]) { eq_mismatch++; break; }
        eq_count++;
    }
    col_pending = 0;
}

// walk_on_map asm vs C on the real level: positions, heights, velocities, single/double step
void walk_on_map(uint8_t i, uint8_t dbl);
void walk_on_map_c(uint8_t i, uint8_t dbl);
static const uint8_t eq_ys[4] = { 64, 112, 120, 127 };
static const int16_t eq_vx[5] = { -0x0300, -0x0080, 0, 0x0080, 0x0300 };
static const int16_t eq_vy[4] = { -0x0100, 0, 0x0040, 0x0280 };

static void eq_walk(void) {
    uint8_t s = A_ENEMY0 + 4, a, b, c, d, xs1, ys1, y1;
    uint16_t x, x1;
    int16_t vx1, vy1;
    for (x = 0; x < level_px_w; x += 7) {
        for (a = 0; a < 4; a++) for (b = 0; b < 5; b++) for (c = 0; c < 4; c++) for (d = 0; d < 2; d++) {
            act_x[s] = x; act_xs[s] = (uint8_t)x; act_y[s] = eq_ys[a]; act_ys[s] = (uint8_t)(x >> 3);
            act_vx[s] = eq_vx[b]; act_vy[s] = eq_vy[c];
            walk_on_map(s, d);
            x1 = act_x[s]; xs1 = act_xs[s]; y1 = act_y[s]; ys1 = act_ys[s]; vx1 = act_vx[s]; vy1 = act_vy[s];
            act_x[s] = x; act_xs[s] = (uint8_t)x; act_y[s] = eq_ys[a]; act_ys[s] = (uint8_t)(x >> 3);
            act_vx[s] = eq_vx[b]; act_vy[s] = eq_vy[c];
            walk_on_map_c(s, d);
            if (act_x[s] != x1 || act_xs[s] != xs1 || act_y[s] != y1 || act_ys[s] != ys1
                || act_vx[s] != vx1 || act_vy[s] != vy1) eq_mismatch++;
            eq_count++;
        }
    }
    act_type[s] = T_NONE;
}

void eq_run(void) {
    uint16_t x;
    uint8_t y;
    eq_mismatch = eq_count = 0;
    for (x = 0; x < level_px_w + 64; x++) {
        y = 0;
        do {
            if (mt_at(x, y) != mt_at_c(x, y) || solid_at(x, y) != solid_at_c(x, y)) eq_mismatch++;
            eq_count++;
        } while (++y);
    }
    eq_act_move();
    eq_columns();
    eq_walk();
    eq_done = 1;
}

void init(void) {
    DISPLAY_OFF;
    set_bkg_data(0, BG_COUNT, bg_tiles);
    set_bkg_data(TILE_FONT, FONT_COUNT, font_tiles);
    set_bkg_data(TILE_UI, UI_COUNT, ui_tiles);    // tiles >= 128 live in the shared $8800 area
    set_sprite_data(0, SPR_COUNT, spr_tiles);
    SPRITES_8x16;
    SHOW_BKG;
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
}

void main(void) {
    init();
    show_screen_now(SCR_TITLE);
    while (1) {
        vsync();
        frame_start = (uint8_t)sys_time;
        draw_vram();
        prev_keys = keys;
        keys = joypad();
        pressed = keys & ~prev_keys;
        if (eq_request) {
            eq_request = 0;
            eq_run();
            skip_measure = 1;
        }
        if (!update_transition()) {
            switch (state) {
            case STATE_PLAY: update_play(); break;
            case STATE_PAUSE: update_pause(); break;
            case STATE_DYING: update_dying(); break;
            case STATE_GOAL: update_goal(); player_animate(); break;
            default: update_screens(); break;
            }
        }
        if (state == STATE_PLAY || state == STATE_GOAL || state == STATE_PAUSE) {
            if (state != STATE_GOAL || player_x < (196 << 4)) player_draw();
            enemies_draw();
            actors_draw();
            draw_banner();
        }
        sound_update();
        measure_frame();
    }
}
