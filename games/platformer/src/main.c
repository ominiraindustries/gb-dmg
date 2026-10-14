// CABALLERITO - main loop, interrupts, game states
#include "game.h"
#include "level1_1.h"

uint8_t state;
uint8_t cheat_flags;
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

void draw_vram(void) {
    level_draw_vram();
    hud_draw_vram();
    ui_draw_vram();
    frame_vram_check();
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

// ---------------------------------------------------------------- asm equivalence test hook
// Tests set gbe_eq_request = 1 (GB.selftest()): engine routines (gbe_selftest) + walk_on_map.
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
                || act_vx[s] != vx1 || act_vy[s] != vy1) gbe_eq_mismatch++;
            gbe_eq_count++;
        }
    }
    act_type[s] = T_NONE;
}

void eq_run(void) {
    gbe_selftest();
    eq_walk();
}

void init(void) {
    DISPLAY_OFF;
    set_bkg_data(0, BG_COUNT, bg_tiles);
    set_bkg_data(TILE_FONT, FONT_COUNT, font_tiles);
    set_bkg_data(TILE_UI, UI_COUNT, ui_tiles);    // tiles >= 128 live in the shared $8800 area
    set_sprite_data(0, SPR_COUNT, spr_tiles);
    SPRITES_8x16;
    SHOW_BKG;
    video_init(15, 0xE4, 0xE4, 0xD8);             // HUD cut at line 15; OBP1 = SHOT form palette
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
        frame_begin();
        draw_vram();
        if (gbe_eq_request) {
            gbe_eq_request = 0;
            eq_run();
            skip_measure = 1;
        }
        if (!transition_update()) {
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
        frame_end();
    }
}
