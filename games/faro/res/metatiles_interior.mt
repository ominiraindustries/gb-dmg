; FARO interior metatiles (houses, shop, enfermeria, posada) - indices of res/interior.tiles.
; Not compiled yet (harness/metatiles.py builds only res/metatiles.mt): E16 should accept metatiles_<set>.mt.
; attr = SOLID 0x80 | CAMP 0x40 | PRIO 0x20 | kind value (GDD 2.2). COUNTER_*: talk to the NPC behind it.
@ tileset interior
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
FLOOR              1   2   3   4                             ; wood planks
STONE              5   5   5   5                             ; stone flags (lighthouse, enfermeria)
DOORMAT            6   7   8   9   K_WARP                    ; exit: WARP event
WALL              10  11  12  12   SOLID                     ; back wall (wallpaper + wainscot)
WALL_WIN          13  14  12  12   SOLID
WALL_PIC          15  16  12  12   SOLID                     ; framed picture of the lighthouse
WALL_CLOCK        17  18  19  20   SOLID
WALL_STONE        21  22  23  24   SOLID                     ; lighthouse wall
SHELF_00          25  26  27  28   SOLID                     ; 2 high: top on the wall row
SHELF_10          29  30  31  32   SOLID
BOOKS_00          33  34  35  36   SOLID                     ; 2 high bookcase
BOOKS_10          37  38  31  32   SOLID
STOVE_00          39  40  41  42   SOLID                     ; 2 high kitchen stove; front = cook spot (event)
STOVE_10          43  44  45  46   SOLID
COUNTER_L         47  48  49  50   SOLID K_COUNTER
COUNTER_M         51  48  50  50   SOLID K_COUNTER
COUNTER_R         51  52  50  53   SOLID K_COUNTER
BED_00            54  55  56  57   SOLID                     ; 2 high (pillow on top)
BED_10            58  59  60  61   SOLID
TABLE_00          62  63  64  65   SOLID                     ; 2 wide
TABLE_01          66  67  68  69   SOLID
CHAIR             70  71  72  73   SOLID
POT               74  75  76  77   SOLID                     ; steaming pot (on the stove or the floor)
PLANT             78  79  80  81   SOLID
STAIRS_UP         82  83  84  85   K_WARP
STAIRS_DOWN       86  87  88  89   K_WARP
RUG_00            90  91  92  93                             ; 3x2 rug
RUG_01            91  91  93  93
RUG_02            91  94  93  95
RUG_10            92  93  96  97
RUG_11            93  93  97  97
RUG_12            93  95  97  98
