// FARO kit - the camp (GDD 2.7): where it can be set up (a CAMP cell under Leo, the cell in front
// free for the fire, no alert creature near, firewood in the bag). Towns simply have no CAMP cells
// (map data). Bank 1.
#pragma bank 255
#include "rpg.h"
#include "tbl_msgs.h"

extern uint8_t role_item[];

// MSG_* of the refusal, or 0xFF if Leo can camp here
uint8_t camp_check(void) BANKED {
    uint8_t fx = px + dir_dx[pdir], fy = py + dir_dy[pdir], wood = role_item[ITEMS_ROLE_LENA];
    if (!(wattr_at(px, py) & ATTR_CAMP)) return MSG_PANEL_NOHERE;
    if ((wattr_at(fx, fy) & ATTR_SOLID) || gact_at(fx, fy) != 0xFF) return MSG_PANEL_NOHERE;
    if (creatures_alert_near((uint8_t)RULE(RULE_CAMP_SAFE_DIST))) return MSG_PANEL_UNSAFE;
    if (wood == 0xFF || inv[wood] < (uint8_t)RULE(RULE_CAMP_FUEL)) return MSG_PANEL_NOWOOD;
    return 0xFF;
}
