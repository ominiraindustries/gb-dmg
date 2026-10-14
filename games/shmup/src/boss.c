// GRIFO - the boss: drawn in the BG by the map (rows 189-191, columns 3-6) and moved with
// SCX/SCY once the scroll stops; everything visible around it is flat fog (GDD 2.10).
// Phases by table-like timers: A (HP 200-101), transition, B (100-1), death, outro.
#include "game.h"
#include "stage1.h"

#define BOSS_X0    56           // OAM X / Y of the boss top-left with boss_dx = boss_dy = 0
#define BOSS_Y0    32
#define BOSS_HP    200
#define BOSS_ROW0  (STAGE1_STOP_ROW - 2)   // bottom metatile row of the boss

uint8_t boss_hp, boss_phase, boss_state, boss_t, boss_flash, boss_flash_cd, boss_hit_cd, boss_spiral;
int8_t boss_dx, boss_dy;
static uint16_t boss_ph;
static uint8_t scy_stop, fan_cd, claw_cd, erase_row;

static const uint8_t score_boss[3] = { 0x00, 0x00, 0x02 };     // 20 000

#define BOSS_X ((uint8_t)(BOSS_X0 + boss_dx))
#define BOSS_Y ((uint8_t)(BOSS_Y0 + boss_dy))

void boss_reset(void) {
    boss_state = BOSS_NONE;
    boss_dx = boss_dy = 0;
    bgp_below_on = 0;
}

static void boss_bullets(void) {
    uint8_t i;
    for (i = 0; i < N_BULLET; i++) pool[P_BULLET + i].t = 0;
}

// sway: wave_ofs (amplitude 24) x 1.625 = +-39 px; boss_ph advances 128 entries per period
static int8_t sway(uint16_t step) {
    int8_t w;
    boss_ph += step;
    w = wave_ofs[(boss_ph >> 8) & 127];
    return w + (w >> 1) + (w >> 3);
}

static void mouth_fan(uint8_t n, uint8_t spd) {
    uint8_t x = BOSS_X + 32 - 4, y = BOSS_Y + 40 - 4;
    bullets_setup(SPR_EBULLET_BOSS);
    fire_fan(x, y, aim_at(x - 4, y - 4), n, 2, spd);
}

void boss_update(void) {
    uint8_t t;
    if (boss_state == BOSS_NONE) {
        if (scroll_y == vmap_stop) {                     // the scroll stopped with the boss at y 16
            boss_state = BOSS_INTRO;
            formations_clear();
            boss_hp = BOSS_HP;
            boss_phase = 0;
            boss_t = 0; boss_ph = 0; fan_cd = 40; claw_cd = 76;
            scy_stop = scy_shadow;
            boss_bar_on = 1;
            hud_bar_px = 0;
        }
        return;
    }
    if (boss_flash) { if (!--boss_flash) bgp_below_on = 0; }
    if (boss_hit_cd) boss_hit_cd--;
    if (boss_flash_cd) boss_flash_cd--;
    t = ++boss_t;
    switch (boss_state) {
    case BOSS_INTRO:                                     // bar fills 1 px/f (ui.md 2.3)
        if (++hud_bar_px >= 24) { boss_state = BOSS_FIGHT; boss_t = 0; }
        break;
    case BOSS_FIGHT:
        if (boss_phase == 0) {                           // A: sway 256 f, mouth fans, claw shots
            boss_dx = sway(0x0080);
            if (!--fan_cd) { fan_cd = 72; if (!no_fire) mouth_fan(5, 1); }
            if (!--claw_cd) {
                claw_cd = 128;
                if (!no_fire) {
                    bullets_setup(SPR_EBULLET_BOSS);
                    fire(BOSS_X + 8 - 4, BOSS_Y + 36 - 4, aim_at(BOSS_X, BOSS_Y + 28), 2);
                    fire(BOSS_X + 56 - 4, BOSS_Y + 36 - 4, aim_at(BOSS_X + 48, BOSS_Y + 28), 2);
                }
            }
        } else if (boss_phase == 1) {                    // transition: still, flashing, roar
            if ((t & 3) == 0) { bgp_below = 0x90; bgp_below_on = 1; boss_flash = 2; }
            if (t == 32) { boss_phase = 2; boss_t = 0; boss_spiral = 0; }
        } else {                                         // B: 240 f cycle
            boss_dx = sway(0x00CD);                      // 160 f period
            if (t < 96) {
                if ((t & 7) == 1 && !no_fire) {     // t = 1, 9 .. 89: 12 bullets
                    bullets_setup(SPR_EBULLET_BOSS);
                    fire(BOSS_X + 28, BOSS_Y + 36, boss_spiral, 0);
                    boss_spiral += 5;
                }
            } else if (t >= 144 && t < 168) {
                boss_dy++;
                if (t == 167 && !no_fire) mouth_fan(7, 1);
            } else if (t >= 168 && t < 216) {
                if (t & 1) boss_dy--;
            } else if (t == 239) {
                boss_t = 0;
            }
        }
        break;
    case BOSS_DEAD:                                      // 150 f of explosions, then erase
        shake_x = (t & 2) ? 1 : -1;
        if ((t & 7) == 0) {
            uint8_t k = pool_alloc(P_EXPLO, N_EXPLO);
            if (k != 0xFF) {
                pool_obj_t *e = &pool[k];
                e->t = OBJ_EXPLO; e->x = BOSS_X + ((t * 37) & 47); e->y = BOSS_Y + 8 + ((t * 13) & 23);
                e->xs = e->ys = 0; e->vx = e->vy = 0; e->tm = 0; e->tile = SPR_EXPLO_0; e->prop = 0;
            }
            sfx(SFX_BOOM);
        }
        if ((t & 15) == 0) { bgp_below = 0x90; bgp_below_on = 1; boss_flash = 2; }
        if (t == 150) {
            shake_x = 0;
            boss_state = BOSS_OUTRO; boss_t = 0; erase_row = 0;
            boss_bar_on = 0;                             // cols 15-19 back to BLANK (ui.md 2.3)
        }
        break;
    case BOSS_OUTRO:                                     // boss rows -> fog, wait, fly away
        if (erase_row < 3) {
            uint8_t c;
            for (c = 3; c < 7; c++) vmap_set(c, BOSS_ROW0 + erase_row, MT_FOG);
            erase_row++;
            if (erase_row == 3) boss_dx = boss_dy = 0;   // all fog: SCX/SCY back without a jump
        }
        if (t > 60) {
            play_sub = PS_OUTRO;
            if ((t & 1) == 0) player_y -= 3;             // 1.5 px/f
            if (player_y < 8 || player_y > 200) { boss_state = BOSS_DONE; stage_clear(); }
        }
        break;
    }
    scx_shadow = (uint8_t)-boss_dx;
    scy_shadow = scy_stop - boss_dy;
    if (boss_state == BOSS_FIGHT || boss_state == BOSS_DEAD) {
        uint8_t px = (uint8_t)(((uint16_t)boss_hp * 31) >> 8);
        hud_bar_px = (boss_hp && !px) ? 1 : px;
    }
}

void boss_damage(uint8_t dmg) {
    if (boss_state != BOSS_FIGHT || boss_phase == 1) return;
    if (!boss_hit_cd) { sfx(SFX_BOSS_HIT); boss_hit_cd = 8; }
    if (!boss_flash_cd) {                            // at most every 8 f (a boss_t & 7 test missed
        bgp_below = 0x90; bgp_below_on = 1;          // every hit of one frame parity, QA bug)
        boss_flash = 2; boss_flash_cd = 8;
    }
    if (boss_hp > dmg) {
        boss_hp -= dmg;
        if (boss_phase == 0 && boss_hp < 101) {
            boss_phase = 1; boss_t = 0; boss_bullets(); sfx(SFX_BOMB);
        }
        return;
    }
    boss_hp = 0;
    boss_state = BOSS_DEAD; boss_t = 0;
    boss_bullets();
    add_score(score_boss);
    sfx(SFX_BIG_BOOM);
}

// Body box 56x32 at (4, 8) of the boss, for shots (damage) and the player's core (death).
uint8_t boss_overlaps(uint8_t x, uint8_t y, uint8_t w, uint8_t h) {
    if (boss_state != BOSS_FIGHT && boss_state != BOSS_INTRO) return 0;
    return (uint8_t)(x - (uint8_t)(BOSS_X + 4 - w + 1)) < (uint8_t)(56 + w - 1) &&
           (uint8_t)(y - (uint8_t)(BOSS_Y + 8 - h + 1)) < (uint8_t)(32 + h - 1);
}
