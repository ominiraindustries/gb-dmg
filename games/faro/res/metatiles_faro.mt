; FARO lighthouse metatiles - indices of res/faro.tiles. Not compiled yet (see metatiles_interior.mt).
@ tileset faro
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

VOID               0   0   0   0   SOLID                     ; outside the room (map border)
STONE              1   1   1   1                             ; stone flags (lighthouse, enfermeria)
DOORMAT            2   3   4   5   K_WARP                    ; exit: WARP event
WALL_WIN           6   7   8   8   SOLID
WALL_STONE         9  10  11  12   SOLID                     ; lighthouse wall
BOOKS_00          13  14  15  16   SOLID                     ; 2 high bookcase
BOOKS_10          17  18  19  20   SOLID
BED_00            21  22  23  24   SOLID                     ; 2 high (pillow on top)
BED_10            25  26  27  28   SOLID
TABLE_00          29  30  31  32   SOLID                     ; 2 wide
TABLE_01          33  34  35  36   SOLID
CHAIR             37  38  39  40   SOLID
STAIRS_UP         41  42  43  44   K_WARP
STAIRS_DOWN       45  46  47  48   K_WARP
LENS_00           49  50  51  52   SOLID                     ; 3x3 great lens, unlit (6 dark rings)
LENS_01           53  54  55  56   SOLID
LENS_02           57  49  58  59   SOLID
LENS_10           60  61  62  63   SOLID
LENS_11           64  65  66  67   SOLID
LENS_12           68  69  70  71   SOLID
LENS_20           72  73  49  74   SOLID
LENS_21           75  76  77  78   SOLID
LENS_22           79  80  81  49   SOLID
LENSLIT_00        49  82  83  84   SOLID                     ; 3x3 lens with ring 1 lit (LAMP scene patches LENS -> LENSLIT)
LENSLIT_01        85  86  55  56   SOLID
LENSLIT_02        87  49  88  89   SOLID
LENSLIT_10        90  61  91  63   SOLID
LENSLIT_11        64  65  66  67   SOLID
LENSLIT_12        68  92  70  93   SOLID
LENSLIT_20        94  95  49  96   SOLID
LENSLIT_21        75  76  97  98   SOLID
LENSLIT_22        99 100 101  49   SOLID
