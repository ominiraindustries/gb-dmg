// Screens, transitions and the goal sequence (design/ui.md §1-§10, GDD §2.11, §4)
#include <string.h>
#include "game.h"
#include "level1_1.h"
#include "screen_title.h"
#include "screen_clear.h"
#include "screen_gameover.h"

#define BG_MAP  ((uint8_t *)0x9800u)
#define WIN_MAP ((uint8_t *)0x9C00u)
#define T_BLANK  (TILE_UI + UI_BLANK)
#define T_DIGIT0 (TILE_FONT + FONT_DIGIT0)

uint8_t record[3];                       // packed BCD like score (RAM only in M1)
uint8_t blink60;                         // 0..59, the 30/30 f blink of screen texts
uint8_t new_record;
uint8_t screen_timer;

// ---------------------------------------------------------------- small VRAM jobs for blinking text
// Prepared outside VBlank, copied by ui_draw_vram() (called from draw_vram)

uint8_t *job_dst;
const uint8_t *job_src;
uint8_t job_len;

static void queue_job(uint8_t *dst, const uint8_t *src, uint8_t len) {
    job_dst = dst; job_src = src; job_len = len;
}

void ui_draw_vram(void) {
    uint8_t n = job_len;
    uint8_t *d = job_dst;
    const uint8_t *s = job_src;
    if (!n) return;
    do *d++ = *s++; while (--n);
    job_len = 0;
}

static const uint8_t blanks[20] = {
    T_BLANK, T_BLANK, T_BLANK, T_BLANK, T_BLANK, T_BLANK, T_BLANK, T_BLANK, T_BLANK, T_BLANK,
    T_BLANK, T_BLANK, T_BLANK, T_BLANK, T_BLANK, T_BLANK, T_BLANK, T_BLANK, T_BLANK, T_BLANK };

// ---------------------------------------------------------------- helpers (LCD off)

static void put_screen(const uint8_t *map) {
    uint8_t r, *d = BG_MAP;
    for (r = 0; r < 18; r++, d += 32, map += 20) memcpy(d, map, 20);
}

static void put_bcd6(uint8_t *d, const uint8_t *bcd) {
    d[0] = T_DIGIT0 + (bcd[2] >> 4); d[1] = T_DIGIT0 + (bcd[2] & 15);
    d[2] = T_DIGIT0 + (bcd[1] >> 4); d[3] = T_DIGIT0 + (bcd[1] & 15);
    d[4] = T_DIGIT0 + (bcd[0] >> 4); d[5] = T_DIGIT0 + (bcd[0] & 15);
}

void put_text(uint8_t *dst, const char *s);  // hud.c

static void update_record(void) {
    new_record = 0;
    if (score[2] > record[2] || (score[2] == record[2] && (score[1] > record[1]
        || (score[1] == record[1] && score[0] > record[0])))) {
        memcpy(record, score, 3);
        new_record = 1;
    }
}

// ---------------------------------------------------------------- TITLE (ui.md §8)

uint8_t press_tiles[11];

static void build_title(void) {
    lcd_off_redraw_begin();
    put_screen(screen_title_map);
    put_bcd6(BG_MAP + 12 * 32 + 10, record);
    memcpy(press_tiles, screen_title_map + 10 * 20 + 4, 11);   // "PULSA START" as drawn
    // Teo on the battlements (mockup: x 24, y 105 screen px)
    oam16(0, screen_title_spr[0] + 8, screen_title_spr[1] + 16, SPR_TEO_SMALL_IDLE, 0);
    SHOW_SPRITES;
    state = STATE_TITLE;
    screen_timer = 0;
    DISPLAY_ON;
}

uint8_t title_pressed;

static void update_title(void) {
    uint8_t t = ++screen_timer, on;
    if (!title_pressed && (pressed & (J_START | J_A))) {
        title_pressed = 1;
        screen_timer = 0;
        sfx(SFX_POWER_GET);
        return;
    }
    if (title_pressed) {                      // fast blink 4/4 for 32 f, then go
        on = (t & 4) == 0;
        if (t >= 32) {
            title_pressed = 0;
            new_game();
            return;
        }
    } else {
        if (++blink60 == 60) blink60 = 0;
        on = blink60 < 30;
    }
    if ((t & 3) == 0 || t == 1) queue_job(BG_MAP + 10 * 32 + 4, on ? (const uint8_t *)press_tiles : blanks, 11);
}

// ---------------------------------------------------------------- INTRO (ui.md §3)

#define INTRO_FRAMES 120

static void build_intro(void) {
    uint8_t *w = WIN_MAP;
    uint8_t r;
    lcd_off_redraw_begin();
    load_level();                             // level + HUD rows 0-1 (main.c)
    for (r = 2; r < 18; r++) memcpy(w + r * 32, blanks, 20);
    put_text(w + 6 * 32 + 5, "MUNDO 1-1");
    put_text(w + 8 * 32 + 6, "PRADERA");
    w[11 * 32 + 7] = TILE_UI + UI_ICON_HEAD;
    w[11 * 32 + 9] = (uint8_t)(TILE_UI + UI_ICON_TIMES);
    w[11 * 32 + 11] = T_DIGIT0 + lives / 10;
    w[11 * 32 + 12] = T_DIGIT0 + lives % 10;
    WX_REG = 7;
    WY_REG = 0;
    SHOW_WIN;                                 // full-screen card, no cut, no sprites
    scy_shadow = SCY_REG = 0xF0;               // gbe_video writes SCY every VBlank
    state = STATE_INTRO;
    screen_timer = 0;
    DISPLAY_ON;
}

static void update_intro(void) {
    uint8_t t = ++screen_timer, k;
    if (t <= 16) {                                          // fade in: 3, 2, 1, 0
        k = (t - 1) >> 2;
        set_fade(k >= 3 ? 0 : 3 - k);
    }
    if (t >= INTRO_FRAMES - 16 && t < INTRO_FRAMES) {      // fade out: k = 1, 2, 3, 3
        k = 1 + ((t - (INTRO_FRAMES - 16)) >> 2);
        set_fade(k > 3 ? 3 : k);
    }
    if (t == INTRO_FRAMES) {                  // white screen: switch to the HUD cut, show Teo
        hud_cut = 1;
        SCX_REG = scx_shadow;
        player_draw();
    }
    if (t > INTRO_FRAMES) {
        k = (t - INTRO_FRAMES) >> 2;                         // fade in: 3, 2, 1, 0
        set_fade(k >= 3 ? 0 : 3 - k);
        if (t >= INTRO_FRAMES + 16) {
            set_fade(0);
            state = STATE_PLAY;
        }
    }
}

// ---------------------------------------------------------------- CLEAR / GAMEOVER (ui.md §9-10)

uint8_t nr_tiles[13];

static void build_result(uint8_t clear) {
    lcd_off_redraw_begin();
    update_record();
    if (clear) {
        put_screen(screen_clear_map);
        put_bcd6(BG_MAP + 8 * 32 + 11, score);
        put_bcd6(BG_MAP + 10 * 32 + 11, record);
        memcpy(nr_tiles, screen_clear_map + 12 * 20 + 4, 13);
        if (!new_record) memcpy(BG_MAP + 12 * 32 + 4, blanks, 13);
        state = STATE_CLEAR;
    } else {
        put_screen(screen_gameover_map);
        put_bcd6(BG_MAP + 10 * 32 + 11, score);
        state = STATE_GAMEOVER;
    }
    screen_timer = 0;
    DISPLAY_ON;
}

static void update_result(void) {
    uint8_t t = ++screen_timer;
    if (++blink60 == 60) blink60 = 0;
    if (state == STATE_CLEAR && new_record && (blink60 == 0 || blink60 == 30))
        queue_job(BG_MAP + 12 * 32 + 4, blink60 < 30 ? (const uint8_t *)nr_tiles : blanks, 13);
    if (t >= 180 || (t >= 30 && (pressed & (J_START | J_A)))) transition(SCR_TITLE);
}

// ---------------------------------------------------------------- screens for gbe_screen

// Called by gbe_screen with the screen faded to white
void screen_build(uint8_t which) {
    switch (which) {
    case SCR_TITLE: build_title(); break;
    case SCR_INTRO: build_intro(); trans_own_fadein = 1; break;   // the intro has its own timeline
    case SCR_CLEAR: build_result(1); break;
    case SCR_GAMEOVER: build_result(0); break;
    }
}

void update_screens(void) {
    switch (state) {
    case STATE_TITLE: update_title(); break;
    case STATE_INTRO: update_intro(); break;
    case STATE_CLEAR:
    case STATE_GAMEOVER: update_result(); break;
    }
}

// ---------------------------------------------------------------- GOAL (GDD §2.11)

uint8_t pole_col, banner_y, goal_phase, goal_timer;
static const uint8_t goal_pts[7][3] = {
    {0x00,0x50,0}, {0x00,0x50,0}, {0x00,0x20,0}, {0x00,0x08,0}, {0x00,0x04,0}, {0x00,0x01,0}, {0x00,0x01,0} };

#define BANNER_TOP   (Y_BIAS + 16)
#define POLE_BASE    (Y_BIAS + 6 * 16)          // top of the base block
#define DOOR_COL     196

void goal_reset(void) {
    uint8_t c;
    banner_y = BANNER_TOP;
    pole_col = 0;
    for (c = 0; c < level_cols; c++)
        if (level[(uint16_t)c << 3] == MT_SPEAR) pole_col = c;
}

// Touching the pole: the 4 px in the middle of its column (GDD §2.11)
uint8_t goal_check(void) {
    uint16_t right = player_x + HB_X + HB_W - 1, pole_l = ((uint16_t)pole_col << 4) + 6;
    uint8_t row;
    if (!pole_col || right < pole_l || player_x + HB_X > pole_l + 3) return 0;
    row = (uint8_t)(player_y + hb_y + hb_h - 1);
    row = (row < Y_BIAS || row >= 0xC0) ? 0 : (uint8_t)(row - Y_BIAS) >> 4;   // above the level: top
    if (row > 6) row = 6;
    add_score(goal_pts[row]);
    sfx(SFX_POWER_GET);
    // same x as the banner sprite: equal X -> lower OAM index (Teo, 0-3) is drawn in front
    player_x = ((uint16_t)pole_col << 4) - 8;
    player_vx = player_vy = 0;
    player_facing = 0;
    goal_phase = 0;
    hud_time_icon(1);
    state = STATE_GOAL;
    return 1;
}

void update_goal(void) {
    uint8_t feet = player_y + hb_y + hb_h, done = 1;
    switch (goal_phase) {
    case 0:                                       // slide down with the banner
        if (feet < POLE_BASE) { player_y += 2; done = 0; }
        if (banner_y < POLE_BASE - 16) { banner_y += 2; done = 0; }
        if (done) goal_phase = 1;
        break;
    case 1:                                       // walk to the castle door (falls off the base)
        player_x++;
        if (!solid_at(player_x + 8, player_y + hb_y + hb_h)) player_y += 2;
        player_vx = 0x0100;
        player_on_ground = 1;
        if (player_x >= ((uint16_t)DOOR_COL << 4)) {
            goal_phase = 2;
            hide_sprites_range(0, 4);
        }
        break;
    case 2:                                       // time bonus: 1 unit per frame, 50 points each
        if (time_units) {
            time_units--;
            hud_set_time(time_units);
            add_score(PTS_50);
            if ((time_units & 3) == 0) sfx(SFX_TICK);
        } else {
            goal_phase = 3;
            goal_timer = 60;
        }
        break;
    case 3:
        if (--goal_timer == 0) transition(SCR_CLEAR);
        break;
    }
    level_update_camera();
}

void draw_banner(void) {
    uint16_t bx = ((uint16_t)pole_col << 4) - 8;
    if (pole_col && bx + 16 > camera_x && bx < camera_x + 168)
        oam16(24, (uint8_t)(bx - camera_x) + 8, banner_y, SPR_ESTANDARTE, 0);
    else
        hide_sprites_range(24, 26);
}
