// Metatiles of the stage tileset (res/bg.tiles header is the source; ids fixed there).
// Tile indices are bg.tiles indices + BG_BASE (VRAM order ui, font, bg: design/ui.md 0.2).
#pragma once
#include <stdint.h>

#define BG_BASE 65
#define MT_COUNT 58

enum {
    MT_FOG = 0,
    MT_GRASS = 1,
    MT_GRASS2 = 2,
    MT_FLOWERS = 3,
    MT_BUSH = 4,
    MT_PATH = 5,
    MT_TREE = 6,
    MT_FOREST = 7,
    MT_FOREST_N = 8,
    MT_FOREST_S = 9,
    MT_FOREST_W = 10,
    MT_FOREST_E = 11,
    MT_FOREST_NW = 12,
    MT_FOREST_NE = 13,
    MT_FOREST_SW = 14,
    MT_FOREST_SE = 15,
    MT_WATER = 16,
    MT_SHORE_W = 17,
    MT_SHORE_E = 18,
    MT_SHORE_N = 19,
    MT_SHORE_S = 20,
    MT_SHORE_NW = 21,
    MT_SHORE_NE = 22,
    MT_SHORE_SW = 23,
    MT_SHORE_SE = 24,
    MT_BRIDGE_W = 25,
    MT_BRIDGE = 26,
    MT_BRIDGE_E = 27,
    MT_COBBLE = 28,
    MT_WALL_TOP = 29,
    MT_WALL_FACE = 30,
    MT_GATE = 31,
    MT_WALL_V = 32,
    MT_ROOF_W = 33,
    MT_ROOF_E = 34,
    MT_TOWER_NW = 35,
    MT_TOWER_NE = 36,
    MT_TOWER_SW = 37,
    MT_TOWER_SE = 38,
    MT_CONE = 39,
    MT_FOG_LO = 40,
    MT_FOG_HI = 41,
    MT_TURRET_L = 42,
    MT_TURRET_D = 43,
    MT_TURRET_R = 44,
    MT_CRATER = 45,
    MT_BOSS_0 = 46,
    MT_BOSS_1 = 47,
    MT_BOSS_2 = 48,
    MT_BOSS_3 = 49,
    MT_BOSS_4 = 50,
    MT_BOSS_5 = 51,
    MT_BOSS_6 = 52,
    MT_BOSS_7 = 53,
    MT_BOSS_8 = 54,
    MT_BOSS_9 = 55,
    MT_BOSS_10 = 56,
    MT_BOSS_11 = 57,
};

#define ATTR_SOLID   0x80
#define ATTR_GROUND  0x01   // a turret may stand here (level lint)
extern const uint8_t mt_tiles[][4];
extern const uint8_t mt_attr[];
