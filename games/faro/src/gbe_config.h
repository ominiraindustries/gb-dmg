// FARO - sizes for the shared engine library (harness/common/src/gbe.h)
#pragma once
#define GBE_WORLD_MT        128     // metatile slots (exterior set: 111)
#define GBE_GACT_MAX        12      // actors: NPCs, items, creatures (GDD 7.3: OAM 8-31)
#define GBE_FLAG_BYTES      128     // 1024 story flags (GDD 8.7)
#define GBE_SELFTEST_WORLD  1
#define GBE_SELFTEST_GACT   1
#define GBE_SELFTEST_BANKED 1       // selftest + C references in a switchable bank
#define GBE_BANKED          1       // tbox, menu, save and the C part of gact in switchable banks
