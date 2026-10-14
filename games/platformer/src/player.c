// Teo: movement, jump and map collision (GDD §2.1, §2.2, §2.3, §2.6)
#include "game.h"

// GDD §2.1 / §2.2 - all "ajustar en playtest"
#define WALK_MAX        0x0140
#define RUN_MAX         0x0200
#define ACCEL           0x0020
#define DECEL           0x0030
#define SKID_DECEL      0x0060
#define AIR_ACCEL       0x0018
#define JUMP_V          (-0x0380)
#define JUMP_V_RUN      (-0x0400)
#define RUN_JUMP_SPEED  0x0180
#define GRAV_HOLD       0x0020
#define GRAV            0x0050
#define FALL_MAX        0x0400
#define COYOTE_FRAMES   5
#define BUFFER_FRAMES   5
#define CORNER_PUSH     4

#define HB_X 3                  // hitbox x offset and width (all forms)
#define HB_W 10

enum { FORM_SMALL, FORM_BIG, FORM_SHOT };

uint16_t player_x;              // box top-left, world px
uint8_t player_xs;              // x sub-pixel
uint8_t player_y, player_ys;    // y with Y_BIAS, sub-pixel
int16_t player_vx, player_vy;   // 8.8 px/frame
int16_t player_air_max;
uint8_t player_form, player_on_ground, player_facing;   // facing: 0 right, 1 left
uint8_t player_coyote, player_jump_buf, player_jump_hold, player_skid;
uint8_t player_anim, player_frame;
uint8_t player_dead;            // set when falling into a pit (main.c handles it)
uint8_t hb_y, hb_h;             // hitbox y offset and height for the current form

static int16_t abs16(int16_t v) { return v < 0 ? -v : v; }

void player_set_form(uint8_t f) {
    player_form = f;
    if (f == FORM_SMALL) { hb_y = 2; hb_h = 14; }
    else { hb_y = 4; hb_h = 28; }
}

void player_spawn(uint16_t x, uint8_t y) {
    player_x = x;
    player_y = y;
    player_xs = player_ys = 0;
    player_vx = player_vy = 0;
    player_facing = 0;
    player_on_ground = 0;
    player_coyote = player_jump_buf = player_jump_hold = 0;
    player_dead = 0;
    player_set_form(FORM_SMALL);
}

// Speed above the limit decays by DECEL (e.g. releasing B while running) instead of snapping
static int16_t limit(int16_t v, int16_t max) {
    if (v > max) return (v - DECEL > max) ? v - DECEL : max;
    if (v < -max) return (v + DECEL < -max) ? v + DECEL : -max;
    return v;
}

static void horizontal_input(void) {
    uint8_t dir = keys & (J_LEFT | J_RIGHT);
    int16_t vx = player_vx, max = (keys & J_B) ? RUN_MAX : WALK_MAX;
    player_skid = 0;
    if (player_on_ground) {
        if (dir == J_RIGHT) {
            player_facing = 0;
            if (vx < 0) { vx += SKID_DECEL; player_skid = 1; if (vx > 0) vx = 0; }
            else if (vx < max) vx += ACCEL;      // above max (B released): only decay, below
        } else if (dir == J_LEFT) {
            player_facing = 1;
            if (vx > 0) { vx -= SKID_DECEL; player_skid = 1; if (vx < 0) vx = 0; }
            else if (vx > -max) vx -= ACCEL;
        } else if (vx > 0) {
            vx = (vx > DECEL) ? vx - DECEL : 0;
        } else if (vx < 0) {
            vx = (vx < -DECEL) ? vx + DECEL : 0;
        }
        vx = limit(vx, max);
    } else {
        if (dir == J_RIGHT) vx += AIR_ACCEL;
        else if (dir == J_LEFT) vx -= AIR_ACCEL;
        vx = limit(vx, player_air_max);   // no air drag without input (SMB inertia)
    }
    player_vx = vx;
}

static void set_air_max(void) {
    player_air_max = (abs16(player_vx) > WALK_MAX || (keys & J_B)) ? RUN_MAX : WALK_MAX;
}

static void jump_input(void) {
    if (pressed & J_A) player_jump_buf = BUFFER_FRAMES;
    else if (player_jump_buf) player_jump_buf--;
    if (player_jump_buf && (player_on_ground || player_coyote)) {
        player_vy = abs16(player_vx) > RUN_JUMP_SPEED ? JUMP_V_RUN : JUMP_V;
        player_jump_hold = 1;
        player_jump_buf = player_coyote = 0;
        player_on_ground = 0;
        set_air_max();
    }
    if (!(keys & J_A)) player_jump_hold = 0;
}

static void move_x(void) {
    uint16_t t = (uint16_t)player_xs + (uint8_t)player_vx;
    uint16_t left, right;
    uint8_t top, bottom;
    player_xs = (uint8_t)t;
    player_x += (int8_t)(player_vx >> 8) + (t >> 8);

    // Left screen edge (camera never goes back); also catches wrap-around below 0
    if (player_x < camera_x || player_x > 0xF000) {
        player_x = camera_x;
        player_xs = 0;
        if (player_vx < 0) player_vx = 0;
    }

    left = player_x + HB_X;
    right = left + HB_W - 1;
    top = player_y + hb_y;
    bottom = top + hb_h - 1;
    if (player_vx > 0) {
        if (solid_at(right, top + 1) || solid_at(right, bottom - 1)
            || (hb_h > 16 && solid_at(right, top + 14))) {
            player_x = (right & 0xFFF0) - HB_W - HB_X;
            player_xs = 0;
            player_vx = 0;
        }
    } else if (player_vx < 0) {
        if (solid_at(left, top + 1) || solid_at(left, bottom - 1)
            || (hb_h > 16 && solid_at(left, top + 14))) {
            player_x = (left & 0xFFF0) + 16 - HB_X;
            player_xs = 0;
            player_vx = 0;
        }
    }
}

static void move_y(void) {
    uint16_t t = (uint16_t)player_ys + (uint8_t)player_vy;
    uint16_t l = player_x + HB_X + 1, r = player_x + HB_X + HB_W - 2;
    uint8_t top, bottom, ls, rs, edge;
    player_ys = (uint8_t)t;
    player_y += (int8_t)(player_vy >> 8) + (t >> 8);
    top = player_y + hb_y;
    bottom = top + hb_h - 1;

    if (player_vy < 0) {
        ls = solid_at(l, top);
        rs = solid_at(r, top);
        if (ls && !rs) {                         // corner correction: slide right past the block
            edge = 16 - (uint8_t)((player_x + HB_X) & 15);
            if (edge <= CORNER_PUSH) { player_x += edge; ls = 0; }
        } else if (rs && !ls) {                  // slide left
            edge = (uint8_t)((player_x + HB_X + HB_W) & 15);
            if (edge <= CORNER_PUSH) { player_x -= edge; rs = 0; }
        }
        if (ls || rs) {                          // head bump
            player_y = (((top - Y_BIAS) & 0xF0) + 16 + Y_BIAS) - hb_y;
            player_ys = 0;
            player_vy = 0;
            player_jump_hold = 0;
        }
    } else if (player_vy > 0 && (solid_at(l, bottom) || solid_at(r, bottom))) {
        player_y = (((bottom - Y_BIAS) & 0xF0) + Y_BIAS) - hb_y - hb_h;   // land on the block top
        player_ys = 0;
        player_vy = 0;
    }

    // Standing support (also keeps on_ground stable while gravity accumulates sub-pixels)
    bottom = player_y + hb_y + hb_h - 1;
    if (player_vy >= 0 && (solid_at(l, bottom + 1) || solid_at(r, bottom + 1))) {
        player_on_ground = 1;
        player_vy = 0;
        player_ys = 0;
    } else {
        if (player_on_ground) set_air_max();     // walked off a ledge
        player_on_ground = 0;
    }
}

static void animate(void) {
    static const uint8_t walk_cycle[4] = {
        SPR_TEO_SMALL_WALK1, SPR_TEO_SMALL_IDLE, SPR_TEO_SMALL_WALK2, SPR_TEO_SMALL_IDLE };
    if (!player_on_ground) player_frame = SPR_TEO_SMALL_JUMP;
    else if (player_skid) player_frame = SPR_TEO_SMALL_SKID;
    else if (player_vx) {
        player_anim += abs16(player_vx) > WALK_MAX ? 2 : 1;
        player_frame = walk_cycle[(player_anim >> 3) & 3];
    } else {
        player_anim = 0;
        player_frame = SPR_TEO_SMALL_IDLE;
    }
}

void player_update(void) {
    horizontal_input();
    jump_input();
    // gravity: low while rising with A held (variable jump height)
    player_vy += (player_vy < 0 && player_jump_hold) ? GRAV_HOLD : GRAV;
    if (player_vy > FALL_MAX) player_vy = FALL_MAX;
    move_x();
    move_y();
    if (player_on_ground) player_coyote = COYOTE_FRAMES;
    else if (player_coyote) player_coyote--;
    if ((uint8_t)(player_y + hb_y) >= PIT_Y) player_dead = 1;
    animate();
}

// Sprites 0-1 (SMALL). OAM y == world y; OAM x = screen x + 8.
void player_draw(void) {
    uint8_t ox = (uint8_t)(player_x - camera_x) + 8;
    uint8_t t = player_frame;
    if (player_facing) {
        set_sprite_tile(0, t + 2); set_sprite_prop(0, S_FLIPX);
        set_sprite_tile(1, t);     set_sprite_prop(1, S_FLIPX);
    } else {
        set_sprite_tile(0, t);     set_sprite_prop(0, 0);
        set_sprite_tile(1, t + 2); set_sprite_prop(1, 0);
    }
    move_sprite(0, ox, player_y);
    move_sprite(1, ox + 8, player_y);
}
