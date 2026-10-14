// GRIFO - PLAY state: vertical scroll, level objects, player, collisions, sprites (GDD 2).
// Everything flying lives in 8-bit OAM space (GDD 2.0); only the BG and the turrets scroll.
#include <string.h>
#include "game.h"
#include "stage1.h"
#include "screen_continuar.h"

#define STOP_SCROLL    ((uint16_t)STAGE1_STOP_ROW * 16 - 112)   // top of the boss at line 16

uint16_t scroll_speed, cheat_scroll;
uint8_t aim_req, aim_dx, aim_dy, aim_out;     // test hook: aim_out = aim_dir(aim_dx, aim_dy)
static uint8_t peligro_done;

// ---------------------------------------------------------------- build (LCD off)
void play_build(void) {
    lcd_off_redraw_begin();
    set_bkg_data(BG_BASE, BG_COUNT, bg_tiles);              // the screens load theirs over it
    init_bkg(T_BLANK);                                      // columns 20-31 = fog for the boss
    memset((uint8_t *)0x9C00, T_BLANK, 32 * 18);            // window
    set_win_tiles(0, 1, 20, 17, screen_continuar_map + 20); // CONTINUAR panel, hidden by the cut
    vmap_load(stage1_map, STAGE1_HEIGHT, 0, STOP_SCROLL);
    scx_shadow = 0;
    shake_x = shake_y = 0;
    pool_clear(0, P_GAME_END);
    player_reset();
    enemies_reset();
    boss_reset();
    peligro_done = 0;
    scroll_speed = SCROLL_SPEED;
    hud_init();
    hud_message(MSG_FASE, 120);
    WX_REG = 7;
    WY_REG = 0;
    hud_cut = 1;
    SHOW_BKG; SHOW_WIN; SHOW_SPRITES;
    state = ST_PLAY;
    play_sub = PS_NORMAL;
    DISPLAY_ON;
}

// ---------------------------------------------------------------- stress (frame budget tests)
// CHEAT_STRESS keeps every pool full: bullets fanned at the player from the top, enemies drifting
// down, so the budget test measures the GDD 9.3 peak without depending on the wave script.
static void stress_spawn(void) {
    uint8_t i;
    pool_obj_t *o;
    bullets_setup(SPR_EBULLET);
    if ((frame & 7) == 0) {
        uint8_t x = 24 + (frame & 0x70);
        fire_fan(x, 24, aim_at(x, 24), 3, 2, 1);
    }
    if ((i = pool_alloc(P_ENEMY, N_ENEMY)) != 0xFF) {
        o = &pool[i];
        o->t = OBJ_DART; o->x = 16 + ((frame * 37) & 127); o->xs = 0; o->y = 8; o->ys = 0;
        o->vx = (frame & 1) ? 0x0040 : -0x0040; o->vy = 0x0080;
        o->s = o->tm = o->pad = 0; o->aux2 = 1; o->tile = SPR_DART_0; o->prop = 0;
    }
}

void play_update(void) {
    uint16_t speed = (cheat_flags & CHEAT_SCROLL) ? cheat_scroll : scroll_speed;
    vmap_scroll(speed);
    if (aim_req) { aim_out = aim_dir((int8_t)aim_dx, (int8_t)aim_dy); aim_req = 0; }
    if (no_fire) no_fire--;
    fire_busy = 0;
    if ((pressed & J_START) && play_sub != PS_DYING && play_sub != PS_OUTRO &&
        boss_state < BOSS_DEAD) {
        pause_toggle();
        return;
    }
    player_update();
    if (state != ST_PLAY) return;                           // death -> CONTINUAR / GAMEOVER
    if (!peligro_done && ((uint16_t)180 << 4) <= scroll_y + 144) {     // GDD 2.10: row 180
        peligro_done = 1;
        hud_message(MSG_PELIGRO, 180);
    }
    if (hud_msg == MSG_PELIGRO && (frame & 31) == 0) sfx(SFX_WARN);
    hud_message_update();
    boss_update();
    if (cheat_flags & CHEAT_STRESS) stress_spawn();
    else if (!(cheat_flags & (CHEAT_NO_LEVEL | CHEAT_FREEZE))) objects_update();
    if (!(cheat_flags & CHEAT_FREEZE)) {
        enemies_update();
        turrets_update();
        effects_update();
        pool_move(P_BULLET, N_BULLET);
        pool_move(P_ENEMY, N_ENEMY);
        pool_move(P_ITEM, N_ITEM);
        pool_move(P_SHOT, N_SHOT);
    }
    player_collide();
    hud_update();
}

void play_sprites(void) {
    player_sprites();
    spr_group(OAM_BULLET, 12, P_BULLET, N_BULLET, 1);
    spr_group(OAM_ENEMY, 12, P_ENEMY, N_ENEMY, 2);
    // tiny groups: when empty just hide their slots (a spr_group call has ~400 T of setup)
    if (pool[P_ITEM].t) spr_group(OAM_ITEM, 2, P_ITEM, N_ITEM, 2);
    else shadow_OAM[OAM_ITEM].y = shadow_OAM[OAM_ITEM + 1].y = 0;
    spr_group(OAM_SHOT, 8, P_SHOT, N_SHOT, 1);
    if (pool[P_EXPLO].t | pool[P_EXPLO + 1].t) spr_group(OAM_EXPLO, 4, P_EXPLO, N_EXPLO, 2);
    else shadow_OAM[OAM_EXPLO].y = shadow_OAM[OAM_EXPLO + 1].y =
         shadow_OAM[OAM_EXPLO + 2].y = shadow_OAM[OAM_EXPLO + 3].y = 0;
    if (++spr_rot == 48) spr_rot = 0;                // groups of 12, 6, 1, 8, 2 slots: 2 x 24
}

void play_draw_vram(void) {
    vmap_draw_vram();
    hud_draw_vram();
}
