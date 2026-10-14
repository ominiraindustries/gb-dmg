// Generated once from the res/bg.tiles METATILE TABLE; keep in sync with it.
#include "metatiles.h"

#define T(a, b, c, d) { (uint8_t)(BG_BASE + a), (uint8_t)(BG_BASE + b), (uint8_t)(BG_BASE + c), (uint8_t)(BG_BASE + d) }
const uint8_t mt_tiles[MT_COUNT][4] = {
    T(  0,   0,   0,   0),   //  0 FOG
    T(  1,   2,   3,   4),   //  1 GRASS
    T(  5,   0,   0,   0),   //  2 GRASS2
    T(  6,   7,   8,   9),   //  3 FLOWERS
    T( 10,  11,  12,  13),   //  4 BUSH
    T( 14,  15,  16,  17),   //  5 PATH
    T( 18,  19,  20,  21),   //  6 TREE
    T( 22,  23,  24,  25),   //  7 FOREST
    T( 26,  27,  24,  25),   //  8 FOREST_N
    T( 28,  29,  30,  31),   //  9 FOREST_S
    T( 32,  23,  33,  25),   // 10 FOREST_W
    T( 22,  34,  24,  35),   // 11 FOREST_E
    T( 36,  27,  33,  25),   // 12 FOREST_NW
    T( 26,  37,  24,  35),   // 13 FOREST_NE
    T( 38,  29,  39,  31),   // 14 FOREST_SW
    T( 28,  40,  30,  41),   // 15 FOREST_SE
    T( 42,  43,  43,  42),   // 16 WATER
    T( 44,  43,  45,  42),   // 17 SHORE_W
    T( 42,  46,  43,  47),   // 18 SHORE_E
    T( 48,  49,  43,  42),   // 19 SHORE_N
    T( 42,  43,  50,  51),   // 20 SHORE_S
    T( 52,  49,  45,  42),   // 21 SHORE_NW
    T( 48,  53,  43,  47),   // 22 SHORE_NE
    T( 44,  43,  54,  51),   // 23 SHORE_SW
    T( 42,  46,  50,  55),   // 24 SHORE_SE
    T( 56,  57,  58,  59),   // 25 BRIDGE_W
    T( 60,  57,  61,  59),   // 26 BRIDGE
    T( 60,  62,  61,  63),   // 27 BRIDGE_E
    T( 64,  65,  66,  67),   // 28 COBBLE
    T( 68,  69,  70,  71),   // 29 WALL_TOP
    T( 72,  73,  74,  74),   // 30 WALL_FACE
    T( 75,  76,  77,  78),   // 31 GATE
    T( 79,  80,  79,  80),   // 32 WALL_V
    T( 81,  82,  83,  84),   // 33 ROOF_W
    T( 85,  86,  87,  88),   // 34 ROOF_E
    T( 89,  90,  91,  92),   // 35 TOWER_NW
    T( 93,  94,  95,  96),   // 36 TOWER_NE
    T( 97,  98,  99, 100),   // 37 TOWER_SW
    T(101, 102, 103, 104),   // 38 TOWER_SE
    T(105, 106, 107, 108),   // 39 CONE
    T(109, 109, 110, 110),   // 40 FOG_LO
    T(111,   0, 112, 112),   // 41 FOG_HI
    T(113, 114, 115, 116),   // 42 TURRET_L
    T(117, 118, 119, 120),   // 43 TURRET_D
    T(121, 122, 123, 124),   // 44 TURRET_R
    T(125, 126, 127, 128),   // 45 CRATER
    T(129, 130, 131, 132),   // 46 BOSS_0
    T(133, 134, 135, 136),   // 47 BOSS_1
    T(137, 138, 139, 140),   // 48 BOSS_2
    T(141, 142, 143, 144),   // 49 BOSS_3
    T(145, 146, 147, 148),   // 50 BOSS_4
    T(149, 150, 151, 152),   // 51 BOSS_5
    T(153, 154, 155, 156),   // 52 BOSS_6
    T(157, 158, 159, 160),   // 53 BOSS_7
    T(161, 162,   0,   0),   // 54 BOSS_8
    T(163, 164,   0, 165),   // 55 BOSS_9
    T(166, 167, 168,   0),   // 56 BOSS_10
    T(169, 170,   0,   0),   // 57 BOSS_11
};

const uint8_t mt_attr[MT_COUNT] = {
    0, ATTR_GROUND, ATTR_GROUND, ATTR_GROUND, ATTR_GROUND, ATTR_GROUND, ATTR_GROUND, ATTR_GROUND, ATTR_GROUND, ATTR_GROUND, ATTR_GROUND, ATTR_GROUND, ATTR_GROUND, ATTR_GROUND, ATTR_GROUND, ATTR_GROUND, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ATTR_GROUND, ATTR_GROUND, 0, 0, ATTR_GROUND, 0, 0, 0, 0, 0, 0, 0, ATTR_GROUND, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
};
