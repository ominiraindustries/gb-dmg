; FARO exterior metatiles (16x16) - tile indices of res/overworld.tiles, ids = line order (MT_<NAME>).
; attr byte = SOLID 0x80 | CAMP 0x40 | PRIO 0x20 | kind (5 bits, GDD 2.2). The K_* names are kind VALUES,
; not bits: test them with (attr & 0x1F) == ATTR_K_WATER, never with &.
; @ base 84 = fonts 72 + UI 12 (GDD 7.2). When game.json gets "vram_order", switch to '@ base auto'.
; Properties the format cannot express yet (needed by E16 / world.py):
;   - anim groups: WATER* and SEA tiles WATER_TL/WATER_TR <-> overworld_anim WATER_A1/WATER_B1;
;     FLOWERS_TL/FLOWERS_TR <-> FLOWER_A1/FLOWER_B1 (2 frames, 24 f each).
;   - change-to: BRAMBLE -> GRASS when cut; BERRY -> BUSH when picked (respawns at 512 steps);
;     LENS* is in the interior set.
;   - groups placed as a block: TREE_00..11 (2x2), BOAT_00..01 (2x1), LIGHTHOUSE_00..41 (2x5; door at
;     LIGHTHOUSE_40/41 bottom centre = put the WARP event on LIGHTHOUSE_41's cell or the one below).
;   - edge sets PATH_* and WATER_*: N/S/W/E = the side where the land is; NW..SE outer corners;
;     INW..ISE inner corners; H/V 1-wide strips, END_*, TURN_*, CROSS for 1-wide paths/streams.
@ tileset overworld
@ base 84
@ attr SOLID      0x80
@ attr CAMP       0x40
@ attr PRIO       0x20
@ attr K_GRASS    0x01
@ attr K_WATER    0x02
@ attr K_DEEP     0x03
@ attr K_LEDGE_D  0x04
@ attr K_LEDGE_L  0x05
@ attr K_LEDGE_R  0x06
@ attr K_BRAMBLE  0x07
@ attr K_GAP      0x08
@ attr K_HOOKPOST 0x09
@ attr K_SLOPE    0x0A
@ attr K_DARKDOOR 0x0B
@ attr K_BRUMA    0x0C
@ attr K_COUNTER  0x0D
@ attr K_FORAGE   0x0E
@ attr K_WARP     0x0F
@ attr K_FISHSPOT 0x10

GRASS              1   0   0   2                             ; plain ground with tufts (CAMP allowed on route maps: use GRASS_CAMP)
GROUND             0   0   0   0                             ; plain light ground (plazas)
GRASS_CAMP         1   0   0   2   CAMP
SAND               3   3   3   3   CAMP
FLOWERS            4   5   5   4                             ; animated: FLOWER_A/B <-> overworld_anim FLOWER_A1/B1
TALLGRASS          0   0   6   7   PRIO K_GRASS
PATH               8   8   8   8
PATH_N             9   9   8   8
PATH_S             8   8  10  10
PATH_W            11   8  11   8
PATH_E             8  12   8  12
PATH_NW           13   9  11   8
PATH_NE            9  14   8  12
PATH_SW           11   8  15  10
PATH_SE            8  12  10  16
PATH_INW          17   8   8   8
PATH_INE           8  18   8   8
PATH_ISW           8   8  19   8
PATH_ISE           8   8   8  20
PATH_H             9   9  10  10
PATH_V            11  12  11  12
PATH_END_W        13   9  15  10
PATH_END_E         9  14  10  16
PATH_END_N        13  14  11  12
PATH_END_S        11  12  15  16
PATH_TURN_SE      13   9  11  20
PATH_TURN_SW       9  14  19  12
PATH_TURN_NE      11  18  15  10
PATH_TURN_NW      17  12  10  16
PATH_CROSS        17  18  19  20
WATER             21  22  22  21   SOLID K_WATER
WATER_N           23  23   8   8   SOLID K_WATER
WATER_S            8   8  24  24   SOLID K_WATER
WATER_W           25   8  25   8   SOLID K_WATER
WATER_E            8  26   8  26   SOLID K_WATER
WATER_NW          27  23  25   8   SOLID K_WATER
WATER_NE          23  28   8  26   SOLID K_WATER
WATER_SW          25   8  29  24   SOLID K_WATER
WATER_SE           8  26  24  30   SOLID K_WATER
WATER_INW         31   8   8   8   SOLID K_WATER
WATER_INE          8  32   8   8   SOLID K_WATER
WATER_ISW          8   8  33   8   SOLID K_WATER
WATER_ISE          8   8   8  34   SOLID K_WATER
WATER_H           23  23  24  24   SOLID K_WATER
WATER_V           25  26  25  26   SOLID K_WATER
WATER_END_W       27  23  29  24   SOLID K_WATER
WATER_END_E       23  28  24  30   SOLID K_WATER
WATER_END_N       27  28  25  26   SOLID K_WATER
WATER_END_S       25  26  29  30   SOLID K_WATER
WATER_TURN_SE     27  23  25  34   SOLID K_WATER
WATER_TURN_SW     23  28  33  26   SOLID K_WATER
WATER_TURN_NE     25  32  29  24   SOLID K_WATER
WATER_TURN_NW     31  26  24  30   SOLID K_WATER
WATER_CROSS       31  32  33  34   SOLID K_WATER
SEA               21  22  22  21   SOLID K_DEEP              ; same art as WATER, kind DEEP (boat)
TREE_00           35  36  37  38   SOLID
TREE_01           39  40  41  42   SOLID
TREE_10           43  44   0  45   SOLID
TREE_11           46  47  48  49   SOLID
BUSH              50  51  52  53   SOLID
BERRY             54  55  56  53   SOLID K_FORAGE            ; FORAGE ready; when picked -> BUSH
BRAMBLE           57  58  59  60   SOLID K_BRAMBLE           ; cut with CUT -> GRASS
BOULDER           61  62  63  64   SOLID
CLIFF_S           65  66  67  68   SOLID                     ; 1-high cliff face (plateau above)
CLIFF_SW          69  66  70  68   SOLID
CLIFF_SE          65  71  67  72   SOLID
CLIFF_TOP         65  66  73  74   SOLID                     ; 2-high cliff: TOP above BASE (FACE between for 3+)
CLIFF_FACE        74  73  73  74   SOLID
CLIFF_BASE        74  73  67  68   SOLID
CLIFF_W           75   1  75   0   SOLID                     ; plateau west edge (rim on the left half)
CLIFF_E            2  76   0  76   SOLID
CLIFF_N            0   1  77  77   SOLID                     ; plateau north edge (rim on the lower half)
CLIFF_NW           0   0  78  77   SOLID
CLIFF_NE           0   0  77  79   SOLID
LEDGE_D            1   2  80  80   K_LEDGE_D                 ; jump down (M2); LEDGE_L/R not drawn yet
STAIRS            81  82  81  82                             ; stone steps up a cliff
CAMPSITE          83  84  85  86   CAMP                      ; old fire ring: marks good camp spots
SIGN              87  88  89  90   SOLID                     ; SIGN event
FENCE_H            1   2  91  91   SOLID
FENCE_V           92   2  92   1   SOLID
BARREL            93  94  95  96   SOLID
PIER_V            97  98  97  98                             ; jetty over water, 1 wide
PIER_H            99  99 100 100                             ; quay planks; lower edge drops to water
BOAT_00          101 102 103 104   SOLID
BOAT_01          105 106 104 107   SOLID
FOG              108 109 110 111   SOLID K_BRUMA             ; BRUMA wall: solid while lamp_ring < the ring of its event
ROOF_TOP_L       112 113 114 115   SOLID
ROOF_TOP_M       113 113 115 115   SOLID
ROOF_TOP_R       113 116 115 117   SOLID
ROOF_CHIMNEY     113 118 115 115   SOLID
ROOF_BOT_L       114 115 119 120   SOLID
ROOF_BOT_M       115 115 120 120   SOLID
ROOF_BOT_R       115 117 120 121   SOLID
WALL_L           122 123 124 125   SOLID
WALL_M           123 123 125 125   SOLID
WALL_R           123 126 125 127   SOLID
WALL_WIN         128 129 125 125   SOLID
WALL_DOOR        130 131 132 133   K_WARP                    ; door: WARP event
WALL_SHOP        134 135 125 125   SOLID                     ; shop sign (sack)
WALL_CLINIC      136 137 125 125   SOLID                     ; enfermeria sign (heart)
WALL_INN         138 139 125 125   SOLID                     ; posada sign (steaming bowl)
LIGHTHOUSE_00      0 140   0 141   SOLID
LIGHTHOUSE_01    142   0 143   0   SOLID
LIGHTHOUSE_10    144 145 146 147   SOLID
LIGHTHOUSE_11    148 149 150 151   SOLID
LIGHTHOUSE_20    152 153 152 154   SOLID
LIGHTHOUSE_21    155 156 157 156   SOLID
LIGHTHOUSE_30    152 153 152   0   SOLID
LIGHTHOUSE_31    155 156 158 156   SOLID
LIGHTHOUSE_40    159 160 161 162   SOLID
LIGHTHOUSE_41    163 164 165 166   SOLID
DRYBUSH          167 168 169 170   SOLID K_FORAGE            ; FORAGE_RAMAS (dry twigs); appended to keep ids stable
