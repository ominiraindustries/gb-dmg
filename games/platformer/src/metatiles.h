// Metatiles (16x16 = 4 BG tiles) and their collision classes. IDs are used by the level
// files (via game.json "levels") and by level[] in WRAM.
#pragma once
#include <stdint.h>

enum {
    MT_SKY, MT_GROUND, MT_BRICK, MT_Q_COIN, MT_Q_POWER, MT_HIDDEN_1UP, MT_USED, MT_HARD,
    MT_TURRET_TOP_L, MT_TURRET_TOP_R, MT_TURRET_L, MT_TURRET_R, MT_COIN, MT_SPEAR, MT_POLE,
    MT_CLOUD_L, MT_CLOUD_R, MT_BUSH_L, MT_BUSH_R,
    MT_HILL_TOP_L, MT_HILL_TOP, MT_HILL_TOP_R, MT_HILL_L, MT_HILL_MID, MT_HILL_R,
    MT_CASTLE_TOP, MT_CASTLE_WALL, MT_CASTLE_WINDOW, MT_CASTLE_DOOR_TOP, MT_CASTLE_DOOR,
    MT_CASTLE_PENNANT, MT_RUNE_GLOW, MT_GROUND_FILL,
    MT_COUNT
};

// Level objects (lowercase chars in .lvl files)
enum { OBJ_START, OBJ_WALKER, OBJ_SHELL, OBJ_CHECKPOINT, OBJ_PLANT, OBJ_HOPPER };

// Collision class in the low bits, ATTR_SOLID set when it blocks movement (GDD §2.6)
#define ATTR_SOLID   0x80
#define CLS_MASK     0x0F
enum { CLS_EMPTY, CLS_SOLID, CLS_BRICK, CLS_Q_COIN, CLS_Q_POWER, CLS_HIDDEN_1UP, CLS_COIN, CLS_POLE };

extern const uint8_t mt_tiles[MT_COUNT][4];   // TL TR BL BR tile indices
extern const uint8_t mt_attr[MT_COUNT];
