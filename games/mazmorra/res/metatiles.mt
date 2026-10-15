; MADRIGUERA metatiles (16x16) on res/dungeon.tiles. M1 set: walls, open doors, entrance
; stairs, stump pillar (BLOCK), puddle (WATER), sign, EARTH fill for cells outside rooms.
; M2 appends LOCK_*, SHUT_*, CRACK_*, BOSS_*, ROCK_CRACKED, CHEST, CHEST_OPEN at the END
; (ids are line order; the map and code use MT_<NAME>).
; Door blocks: 2 cells per room side, 16 px passage in the middle, timber jambs outside.
; Open door cells are NOT solid (both cells of the block): Tilo's 10 px feet can brush the
; 4 px timber jambs drawn on their outer halves (GDD 2.1 corner push guides him to the middle).
; Generated together with dungeon.tiles; edit both together.
@ tileset dungeon
@ base auto
@ attr SOLID 0x80

FLOOR      FLOOR_BLANK  FLOOR_BLANK  FLOOR_BLANK  FLOOR_BLANK 
FLOOR2     FLOOR_BLANK  FLOOR2_TR    FLOOR2_BL    FLOOR_BLANK 
WALL_T     WALL_T_TL    WALL_T_TR    WALL_T_BL    WALL_T_BR   SOLID
WALL_B     WALL_B_TL    WALL_B_TL    EARTH        EARTH       SOLID
WALL_L     EARTH        WALL_L_TR    EARTH        WALL_L_BR   SOLID
WALL_R     WALL_R_TL    EARTH        WALL_R_BL    EARTH       SOLID
WALL_TL    EARTH        WALL_TL_TR   EARTH        WALL_TL_BR  SOLID
WALL_TR    WALL_TR_TL   EARTH        WALL_TR_BL   EARTH       SOLID
WALL_BL    EARTH        WALL_BL_TR   EARTH        EARTH       SOLID
WALL_BR    WALL_BR_TL   EARTH        EARTH        EARTH       SOLID
DOOR_T_L   DOOR_T_L_TL  DOOR_T_L_TR  DOOR_T_L_BL  DOOR_T_L_BR 
DOOR_T_R   DOOR_T_L_TR  DOOR_T_R_TR  DOOR_T_L_BR  DOOR_T_R_BR 
DOOR_B_L   DOOR_B_L_TL  PASSAGE      DOOR_B_L_BL  PASSAGE     
DOOR_B_R   PASSAGE      DOOR_B_R_TR  PASSAGE      DOOR_B_R_BR 
DOOR_L_U   DOOR_L_U_TL  DOOR_L_U_TR  PASSAGE      PASSAGE     
DOOR_L_D   PASSAGE      PASSAGE      DOOR_L_D_BL  DOOR_L_D_BR 
DOOR_R_U   DOOR_R_U_TL  DOOR_L_U_TL  PASSAGE      PASSAGE     
DOOR_R_D   PASSAGE      PASSAGE      DOOR_R_D_BL  DOOR_L_D_BL 
STAIRS_L   DOOR_B_L_TL  STAIRS_L_TR  DOOR_B_L_BL  STAIRS_L_BR SOLID
STAIRS_R   STAIRS_L_TR  DOOR_B_R_TR  STAIRS_L_BR  DOOR_B_R_BR SOLID
BLOCK      BLOCK_TL     BLOCK_TR     BLOCK_BL     BLOCK_BR    SOLID
WATER      WATER_TL     WATER_TR     WATER_BL     WATER_BR    SOLID
SIGN       SIGN_TL      SIGN_TR      SIGN_BL      SIGN_BR     SOLID
EARTH      EARTH        EARTH        EARTH        EARTH       SOLID
