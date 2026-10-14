// FARO kit - game ops of the scripts (res/scripts/ops.txt: the contract with the content) and the
// ability check. Bank 0: gbe_script calls script_game_op() near; the bodies that are not tiny live
// in banked modules. Ops that take time return 1 and call script_resume() when done.
#include "rpg.h"

extern uint8_t warp_map, warp_x, warp_y, warp_dir, warp_pending;

uint8_t player_has_ability(uint16_t mask) {
    return player_has_ability_b(mask);
}

uint8_t script_game_op(uint8_t op) {
    uint8_t *a = script_args;
    uint16_t v;
    switch (op) {
    case OP_GIVE: script_answer = ops_give(a[0], a[1]); return 0;
    case OP_TAKE: inv_take(a[0], a[1]); return 0;
    case OP_HAS: script_answer = inv[a[0]] >= a[1]; return 0;
    case OP_PAY:
        v = a[0] | ((uint16_t)a[1] << 8);
        script_answer = money >= v;
        if (script_answer) money -= v;
        return 0;
    case OP_EARN:
        v = a[0] | ((uint16_t)a[1] << 8);
        money = (uint16_t)(money + v) > RULE(RULE_MONEY_MAX) || money + v < money ? RULE(RULE_MONEY_MAX) : money + v;
        return 0;
    case OP_HEAL: ops_heal(1); return 0;
    case OP_INN: ops_heal(0); return 0;
    case OP_LEARN_RECIPE: recipe_known[a[0] >> 3] |= 1 << (a[0] & 7); return 0;
    case OP_LEARN_SKILL: skills_known |= 1u << a[0]; return 0;
    case OP_REG_COUNT: script_answer = ops_reg_count() >= a[0]; return 0;
    case OP_LAMP_RING: lamp_ring = a[0]; return 0;
    case OP_SAVE_PROMPT: game_save(); return 0;
    case OP_FACE_PLAYER: field_face_player(); return 0;
    case OP_WALK: return field_npc_walk(a[0], a[1]);
    case OP_PWALK: return field_auto_walk(a[0], a[1]);
    case OP_EMOTE: field_emote(a[0], a[1]); return 0;
    case OP_WARP:
        warp_map = a[0]; warp_x = a[1]; warp_y = a[2]; warp_dir = a[3];
        if (state == ST_FIELD) { warp_pending = 1; transition(ST_FIELD); }
        return 0;
    case OP_SET_CELL: world_set_cell(a[0], a[1], a[2]); return 0;
    case OP_DEMO_END: demo_end_request = 1; return 0;
    // screens of later steps (shop, kitchen, fades, name): no-ops until they exist
    }
    return 0;
}
