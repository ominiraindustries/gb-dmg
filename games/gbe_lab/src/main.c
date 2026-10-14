// gbe_lab - test bench for harness/common/src (not a game). Each scenario exercises engine
// modules under a known load so tests can measure cost and check behaviour.
// Scenario 1 (shmup peak, games/shmup GDD 9.3): 8 shots + 12 enemy bullets + 6 enemies (16x16)
// moving, shots x enemies and bullets/enemies x player collisions, OAM built by priority groups.
#include "gbe.h"
#include "bank0.h"
#include "bank1.h"
#include "bank2.h"
#include "bg.h"
#include "spr.h"

#define P_SHOT    0                // 8 player shots
#define P_BULLET  8                // 12 enemy bullets
#define P_ENEMY   20               // 6 enemies
#define N_SHOT    8
#define N_BULLET  12
#define N_ENEMY   6

uint8_t player_x = 84, player_y = 130;   // OAM space
uint8_t hits, player_hits, frame;
uint8_t rng = 0x5A;

static uint8_t rnd(void) {                // xorshift8: deterministic load for tests
    rng ^= rng << 3; rng ^= rng >> 5; rng ^= rng << 1;
    return rng;
}

static pool_obj_t *new_obj(uint8_t first, uint8_t n) {
    uint8_t i = pool_alloc(first, n);
    pool_obj_t *o;
    if (i == 0xFF) return 0;
    o = &pool[i];
    o->t = 1; o->xs = o->ys = 0; o->tile = SPR_PLAYER; o->prop = 0;
    return o;
}

static void spawn(void) {
    pool_obj_t *o;
    if ((frame & 3) == 0 && (o = new_obj(P_SHOT, N_SHOT))) {
        o->x = player_x + 4; o->y = player_y - 8; o->vx = 0; o->vy = -0x0400;
    }
    if ((o = new_obj(P_BULLET, N_BULLET))) {
        o->x = 16 + (rnd() & 127); o->y = 20;
        o->vx = (int8_t)(rnd() & 0x7F) - 0x40; o->vy = 0x0100 + (rnd() & 0x7F);
    }
    if ((o = new_obj(P_ENEMY, N_ENEMY))) {
        o->x = 16 + (rnd() & 127); o->y = 10;
        o->vx = (rnd() & 1) ? 0x0040 : -0x0040; o->vy = 0x0080;
    }
}

static void collide(void) {
    uint8_t s, e;
    hit_ox = 2; hit_oy = 2; hit_ow = 12; hit_oh = 12;          // enemy box
    // Shots vs enemies: each shot every other frame (even shots on even frames). Shots move 4 px/f,
    // enemy boxes are 12 px: 8 px between checks cannot tunnel. Halves the pairs (48 -> 24).
    pool_obj_t *o = &pool[P_SHOT + (frame & 1)];
    for (s = frame & 1; s < N_SHOT; s += 2, o += 2) {
        if (!o->t) continue;
        hit_qx = o->x + 2; hit_qy = o->y; hit_qw = 4; hit_qh = 8;
        if ((e = hit_first(P_ENEMY, N_ENEMY)) != 0xFF) { o->t = 0; pool[e].t = 0; hits++; }
    }
    hit_qx = player_x + 6; hit_qy = player_y + 6; hit_qw = 4; hit_qh = 4;   // 4x4 core
    hit_ox = 1; hit_oy = 1; hit_ow = 6; hit_oh = 6;            // 6x6 bullets
    if ((e = hit_first(P_BULLET, N_BULLET)) != 0xFF) { pool[e].t = 0; player_hits++; }
    hit_ox = 2; hit_oy = 2; hit_ow = 12; hit_oh = 12;
    if (hit_first(P_ENEMY, N_ENEMY) != 0xFF) player_hits++;
}

void update(void) {
    if ((keys & J_LEFT) && player_x > 8) player_x--;
    if ((keys & J_RIGHT) && player_x < 152) player_x++;
    frame++;
    spawn();
    pool_move(P_SHOT, N_SHOT);
    pool_move(P_BULLET, N_BULLET);
    pool_move(P_ENEMY, N_ENEMY);
    collide();
}

void draw_sprites(void) {
    oam16(0, player_x, player_y, SPR_PLAYER, 0);               // player: slots 0-1, never flickers
    spr_group(2, 12, P_BULLET, N_BULLET, 1);                    // enemy bullets: priority 2
    spr_group(14, 12, P_ENEMY, N_ENEMY, 2);                     // enemies
    spr_group(26, 8, P_SHOT, N_SHOT, 1);                        // player shots: lowest priority
    if (++spr_rot == 48) spr_rot = 0;
}

uint8_t bank_ids[3];

void main(void) {
    DISPLAY_OFF;
    set_bkg_data(0, BG_COUNT, bg_tiles);
    // banking test (tests/test_game.py): three banked tilesets into VRAM 0x8800.. (BG 128+)
    bank_set_bkg_data(BANK(bank0), 128, 32, bank0_tiles);
    bank_set_bkg_data(BANK(bank1), 160, 32, bank1_tiles);
    bank_set_bkg_data(BANK(bank2), 192, 32, bank2_tiles);
    bank_ids[0] = BANK(bank0); bank_ids[1] = BANK(bank1); bank_ids[2] = BANK(bank2);
    set_sprite_data(0, SPR_COUNT, spr_tiles);
    init_bkg(BG_DOT);
    SPRITES_8x16;
    video_init(0, 0xE4, 0xE4, 0xE4);
    SHOW_BKG; SHOW_SPRITES; DISPLAY_ON;
    while (1) {
        vsync();
        frame_begin();
        frame_vram_check();
        if (gbe_eq_request) { gbe_eq_request = 0; gbe_selftest(); skip_measure = 1; }
        update();
        draw_sprites();
        frame_end();
    }
}
