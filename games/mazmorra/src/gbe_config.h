// MADRIGUERA engine config (harness/common/src/gbe.h)
#pragma once
#define GBE_WORLD_MT     32     // metatile slots (metatiles.mt has 24 in M1)
#define GBE_GACT_MAX     6      // 4 enemies + 1 NPC + 1 spare (GDD 2.2)
#define GBE_SELFTEST_WORLD 1
#define GBE_SELFTEST_GACT  1
#define GBE_BANKED         1    // tbox/menu/save/gact C/vwf in banks (bank 0 overflowed in M1)
#define GBE_SELFTEST_BANKED 1
