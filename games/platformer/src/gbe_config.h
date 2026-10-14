// Sizes for the shared engine library (harness/common/src/gbe.h)
#pragma once
#define GBE_ACT_MAX      14     // actor slots: 5 enemies, item, 2 shots, 4 debris, 2 coins
#define GBE_MAP_MAX_COLS 255    // metatile columns of the largest level (8 bytes each in WRAM)
#define GBE_SELFTEST_MAP    1   // gbe_selftest checks: map lookups and column fill
#define GBE_SELFTEST_ACTORS 1   //   act_move
