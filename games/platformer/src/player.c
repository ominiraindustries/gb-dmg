// Teo: movement, jump, forms and map collision (GDD §2.1, §2.2, §2.3, §2.4, §2.6)
#include "game.h"

// GDD §2.1 / §2.2 - all "ajustar en playtest"
#define WALK_MAX        0x0140
#define RUN_MAX         0x0200
#define ACCEL           0x0020
#define DECEL           0x0030
#define CROUCH_DECEL    0x0020
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
// GDD §2.3 / §2.4
#define GROW_FRAMES     48
#define SHOT_FRAMES     32
#define INV_FRAMES      90
#define SHOT_COOLDOWN   8
#define THROW_FRAMES    8

enum { FREEZE_NONE, FREEZE_GROW, FREEZE_SHOT, FREEZE_SHRINK, FREEZE_UNSHOT };

uint16_t player_x;              // box top-left, world px (box is 16x16 small, 16x32 big)
uint8_t player_xs;              // x sub-pixel
uint8_t player_y, player_ys;    // y with Y_BIAS, sub-pixel
int16_t player_vx, player_vy;   // 8.8 px/frame
int16_t player_air_max;
uint8_t player_form, player_on_ground, player_facing;   // facing: 0 right, 1 left
uint8_t player_coyote, player_jump_buf, player_jump_hold, player_skid, player_crouch;
uint8_t player_anim, player_frame, player_frame_bot;
uint8_t player_freeze, player_freeze_kind, player_inv;
uint8_t player_shot_cd, player_throw;
uint8_t player_dead;            // 1 = fell in a pit, 2 = killed (main.c handles it)
uint8_t hb_y, hb_h;             // hitbox y offset and height for the current form/pose
uint16_t coin_x;                // last position checked for map coins
uint8_t coin_y;

static int16_t abs16(int16_t v) { return v < 0 ? -v : v; }

void set_hitbox(void) {
    if (player_form == FORM_SMALL) { hb_y = 2; hb_h = 14; }
    else if (player_crouch) { hb_y = 18; hb_h = 14; }
    else { hb_y = 4; hb_h = 28; }
}

static void set_form(uint8_t f) {
    player_form = f;
    player_crouch = 0;
    set_hitbox();
}

void player_spawn(uint16_t x, uint8_t y) {
    player_x = x;
    player_y = y;
    player_xs = player_ys = 0;
    player_vx = player_vy = 0;
    player_facing = 0;
    player_on_ground = 0;
    player_coyote = player_jump_buf = player_jump_hold = 0;
    player_freeze = player_inv = player_shot_cd = player_throw = 0;
    player_dead = 0;
    set_form(FORM_SMALL);
}

// ---------------------------------------------------------------- power-ups and damage

static void grow(void) {
    set_form(FORM_BIG);
    player_y -= 16;                                 // same feet, taller box
    player_freeze = GROW_FRAMES;
    player_freeze_kind = FREEZE_GROW;
}

void player_power_up(uint8_t item) {
    sfx(SFX_POWER_GET);
    if (item == T_ITEM_1UP) {
        add_life();
        return;
    }
    add_score(PTS_1000);
    if (player_form == FORM_SMALL) {
        grow();                                     // GROW or SHOT item: small -> big
    } else if (item == T_ITEM_SHOT && player_form == FORM_BIG) {
        set_form(FORM_SHOT);
        player_freeze = SHOT_FRAMES;
        player_freeze_kind = FREEZE_SHOT;
    }
}

void player_hurt(void) {
    if (player_inv || player_freeze || (cheat_flags & CHEAT_INVINCIBLE)) return;
    sfx(SFX_HURT);
    if (player_form == FORM_SHOT) {                 // decided: SHOT -> BIG (GDD §12)
        set_form(FORM_BIG);
        player_freeze = SHOT_FRAMES;
        player_freeze_kind = FREEZE_UNSHOT;
    } else if (player_form == FORM_BIG) {
        set_form(FORM_SMALL);
        player_y += 16;
        player_freeze = GROW_FRAMES;
        player_freeze_kind = FREEZE_SHRINK;
    } else {
        player_dead = 2;
        return;
    }
    player_inv = INV_FRAMES;
}

void player_bounce(void) {
    player_vy = (keys & J_A) ? -0x0380 : -0x0280;   // higher bounce with A held (GDD §2.2)
    player_jump_hold = (keys & J_A) ? 1 : 0;
    player_on_ground = 0;
}

void player_kill(void) {
    player_dead = 2;
}

// ---------------------------------------------------------------- movement

// Speed above the limit decays by DECEL (e.g. releasing B while running) instead of snapping
int16_t limit(int16_t v, int16_t max) {
    if (v > max) return (v - DECEL > max) ? v - DECEL : max;
    if (v < -max) return (v + DECEL < -max) ? v + DECEL : -max;
    return v;
}

void horizontal_input(void) {
    uint8_t dir = keys & (J_LEFT | J_RIGHT);
    int16_t vx = player_vx, max = (keys & J_B) ? RUN_MAX : WALK_MAX;
    player_skid = 0;
    if (player_on_ground && player_crouch) {        // slides to a stop, cannot accelerate
        if (vx > 0) vx = (vx > CROUCH_DECEL) ? vx - CROUCH_DECEL : 0;
        else if (vx < 0) vx = (vx < -CROUCH_DECEL) ? vx + CROUCH_DECEL : 0;
    } else if (player_on_ground) {
        if (dir == J_RIGHT) {
            player_facing = 0;
            if (vx < 0) { vx += SKID_DECEL; player_skid = 1; if (vx > 0) vx = 0; }
            else if (vx < max) vx += ACCEL;          // above max (B released): only decay, below
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

void set_air_max(void) {
    player_air_max = (abs16(player_vx) > WALK_MAX || (keys & J_B)) ? RUN_MAX : WALK_MAX;
}

void jump_input(void) {
    if (pressed & J_A) player_jump_buf = BUFFER_FRAMES;
    else if (player_jump_buf) player_jump_buf--;
    if (player_jump_buf && (player_on_ground || player_coyote)) {
        player_vy = abs16(player_vx) > RUN_JUMP_SPEED ? JUMP_V_RUN : JUMP_V;
        player_jump_hold = 1;
        player_jump_buf = player_coyote = 0;
        player_on_ground = 0;
        set_air_max();
        sfx(player_form == FORM_SMALL ? SFX_JUMP_SMALL : SFX_JUMP_BIG);
    }
    if (!(keys & J_A)) player_jump_hold = 0;
}

void crouch_and_shoot(void) {
    uint8_t c = player_form != FORM_SMALL && player_on_ground && (keys & J_DOWN);
    if (c != player_crouch) {
        player_crouch = c;
        set_hitbox();
    }
    if (player_shot_cd) player_shot_cd--;
    if (player_throw) player_throw--;
    if (player_form == FORM_SHOT && (pressed & J_B) && !player_shot_cd && !player_crouch) {
        if (spawn_shot(player_facing ? player_x - 4 : player_x + 12, player_y + 8, player_facing)) {
            player_shot_cd = SHOT_COOLDOWN;
            player_throw = THROW_FRAMES;
            sfx(SFX_SHOOT);
        }
    }
}

void move_x(void) {
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

// Solid for the head: normal solids plus the hidden 1UP block (only solid from below)
uint8_t head_solid(uint16_t x, uint8_t y) {
    uint8_t a = mt_attr[mt_at(x, y)];
    return (a & ATTR_SOLID) || (a & CLS_MASK) == CLS_HIDDEN_1UP;
}

void move_y(void) {
    uint16_t t = (uint16_t)player_ys + (uint8_t)player_vy;
    uint16_t l = player_x + HB_X + 1, r = player_x + HB_X + HB_W - 2, cx;
    uint8_t top, bottom, ls, rs, edge;
    player_ys = (uint8_t)t;
    player_y += (int8_t)(player_vy >> 8) + (t >> 8);
    top = player_y + hb_y;
    bottom = top + hb_h - 1;

    if (player_vy < 0) {
        ls = head_solid(l, top);
        rs = head_solid(r, top);
        if (ls && !rs) {                         // corner correction: slide right past the block
            edge = 16 - (uint8_t)((player_x + HB_X) & 15);
            if (edge <= CORNER_PUSH) { player_x += edge; ls = 0; }
        } else if (rs && !ls) {                  // slide left
            edge = (uint8_t)((player_x + HB_X + HB_W) & 15);
            if (edge <= CORNER_PUSH) { player_x -= edge; rs = 0; }
        }
        if (ls || rs) {                          // head bump: hit the block above the centre
            cx = player_x + 8;
            if (!head_solid(cx, top)) cx = ls ? l : r;
            if (top >= Y_BIAS) block_hit(cx >> 4, (uint8_t)(top - Y_BIAS) >> 4);
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

// Stuck inside blocks after growing / standing up under a low ceiling: push 1 px/f (GDD §2.3)
void unstick(void) {
    uint16_t l = player_x + HB_X, r = l + HB_W - 1;
    uint8_t t = player_y + hb_y + 1;
    if (player_form == FORM_SMALL) return;
    if (solid_at(l, t) || solid_at(r, t) || solid_at(l, t + 14) || solid_at(r, t + 14)) {
        if (player_facing) player_x--; else player_x++;
    }
}

void player_animate(void) {
    static const uint8_t walk_small[4] = {
        SPR_TEO_SMALL_WALK1, SPR_TEO_SMALL_IDLE, SPR_TEO_SMALL_WALK2, SPR_TEO_SMALL_IDLE };
    static const uint8_t walk_big[4] = {
        SPR_TEO_BIG_BOT_WALK1, SPR_TEO_BIG_BOT_IDLE, SPR_TEO_BIG_BOT_WALK2, SPR_TEO_BIG_BOT_IDLE };
    uint8_t k = 0;
    if (player_on_ground && !player_skid && player_vx) {
        player_anim += abs16(player_vx) > WALK_MAX ? 2 : 1;
        k = (player_anim >> 3) & 3;
    } else if (player_on_ground && !player_vx) {
        player_anim = 0;
    }
    if (player_form == FORM_SMALL) {
        if (!player_on_ground) player_frame = SPR_TEO_SMALL_JUMP;
        else if (player_skid) player_frame = SPR_TEO_SMALL_SKID;
        else player_frame = player_vx ? walk_small[k] : SPR_TEO_SMALL_IDLE;
        return;
    }
    if (!player_on_ground) {
        player_frame = SPR_TEO_BIG_TOP_JUMP; player_frame_bot = SPR_TEO_BIG_BOT_JUMP;
    } else if (player_skid) {
        player_frame = SPR_TEO_BIG_TOP_SKID; player_frame_bot = SPR_TEO_BIG_BOT_SKID;
    } else {
        player_frame = SPR_TEO_BIG_TOP;
        player_frame_bot = player_vx ? walk_big[k] : SPR_TEO_BIG_BOT_IDLE;
    }
    if (player_throw) player_frame = SPR_TEO_BIG_TOP_THROW;
}

void player_update(void) {
    if (player_freeze) {                         // power-up / damage animation: logic frozen
        player_freeze--;
        return;
    }
    if (player_inv) player_inv--;
    horizontal_input();
    jump_input();
    // gravity: low while rising with A held (variable jump height)
    player_vy += (player_vy < 0 && player_jump_hold) ? GRAV_HOLD : GRAV;
    if (player_vy > FALL_MAX) player_vy = FALL_MAX;
    move_x();
    move_y();
    crouch_and_shoot();
    unstick();
    if (player_x != coin_x || player_y != coin_y) {   // coins cannot change under a still Teo
        coin_x = player_x;
        coin_y = player_y;
        collect_coins();
    }
    if (player_on_ground) player_coyote = COYOTE_FRAMES;
    else if (player_coyote) player_coyote--;
    // y is u8 with Y_BIAS 32: a high jump from row 1 wraps below 0 to 0xC0-0xFF (above the
    // screen), which must not count as a pit (QA bug: jumping from the top row killed Teo)
    if (player_y < 0xC0 && (uint8_t)(player_y + hb_y) >= PIT_Y) player_dead = 1;
    player_animate();
}

// ---------------------------------------------------------------- drawing (sprites 0-3)

static void draw16(uint8_t s, uint8_t tile, uint8_t ox, uint8_t y, uint8_t prop) {
    oam16(s, ox, y, tile, player_facing ? prop | S_FLIPX : prop);
}

void player_draw(void) {
    uint8_t ox = (uint8_t)(player_x - camera_x) + 8;
    uint8_t pal = player_form == FORM_SHOT ? S_PALETTE : 0;
    uint8_t big = player_form != FORM_SMALL, f = player_freeze;

    // Freeze animations alternate looks every 4 frames; invulnerability blinks 2 on / 2 off
    if (f && (f & 4)) {
        if (player_freeze_kind == FREEZE_GROW || player_freeze_kind == FREEZE_SHRINK) big = !big;
        else pal ^= S_PALETTE;
    }
    if (player_inv && !f && (player_inv & 2)) {
        hide_sprites_range(0, 4);
        return;
    }
    if (!big) {
        uint8_t y = player_form == FORM_SMALL ? player_y : player_y + 16;
        draw16(0, player_form == FORM_SMALL ? player_frame : SPR_TEO_SMALL_IDLE, ox, y, pal);
        hide_sprite(2); hide_sprite(3);
    } else if (player_crouch) {
        draw16(0, SPR_TEO_BIG_CROUCH, ox, player_y + 16, pal);
        hide_sprite(2); hide_sprite(3);
    } else {
        uint8_t y = player_form == FORM_SMALL ? player_y - 16 : player_y;
        draw16(0, big && player_form != FORM_SMALL ? player_frame : SPR_TEO_BIG_TOP, ox, y, pal);
        draw16(2, big && player_form != FORM_SMALL ? player_frame_bot : SPR_TEO_BIG_BOT_IDLE, ox, y + 16, pal);
    }
}
