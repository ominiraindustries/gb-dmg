// FARO kit - placeholders of modules that do not exist yet (each one is replaced by its real
// module; delete the stub when that happens). Bank 1.
#pragma bank 255
#include "rpg.h"

void survival_step(void) BANKED { }
void item_pickup(uint8_t item, uint8_t n) BANKED { (void)item; (void)n; sfx(SFX_PICK); }
void forage(uint8_t table, uint8_t x, uint8_t y) BANKED { (void)table; (void)x; (void)y; }
void menu_open_panel(void) BANKED { }
