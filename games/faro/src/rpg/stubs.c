// FARO kit - placeholders of modules that do not exist yet (each one is replaced by its real
// module; delete the stub when that happens). Bank 1.
#pragma bank 255
#include "rpg.h"

void survival_step(void) BANKED { }
void creatures_sector(uint8_t sx, uint8_t sy) BANKED { (void)sx; (void)sy; }
void creatures_update(void) BANKED { }
uint8_t creature_touch(uint8_t act) BANKED { (void)act; return 0; }
void item_pickup(uint8_t item, uint8_t n) BANKED { (void)item; (void)n; sfx(SFX_PICK); }
void forage(uint8_t table, uint8_t x, uint8_t y) BANKED { (void)table; (void)x; (void)y; }
void menu_open_panel(void) BANKED { }
uint8_t save_exists(void) BANKED { return 0; }
