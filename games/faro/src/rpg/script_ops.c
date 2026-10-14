// FARO kit - game ops of the scripts (res/scripts/ops.txt) and ability checks. Bank 0: gbe_script
// calls script_game_op() near; the handlers of long ops live in banked modules.
#include "rpg.h"

uint8_t player_has_ability(uint16_t mask) {
    return player_has_ability_b(mask);
}

extern uint8_t warp_map, warp_x, warp_y, warp_dir, warp_pending;

uint8_t script_game_op(uint8_t op) {
    switch (op) {
#ifdef OP_WARP
    case OP_WARP:
        warp_map = script_args[0]; warp_x = script_args[1]; warp_y = script_args[2]; warp_dir = script_args[3];
        if (state == ST_FIELD) { warp_pending = 1; transition(ST_FIELD); }
        return 0;
#endif
    }
    return 0;
}
