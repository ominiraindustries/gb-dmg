# `gbe_gact` — gbe_gact.c

**Qué hace:** grid actors on gbe_world: 24-byte records, walking at N frames per cell (8.8), both cells taken, generic behaviours (STILL LOOK WANDER CHASE FLEE HOME FOLLOW), one thinker per frame, 16x16 drawing with the PRIO cell bit cached per cell; asm move/draw/`gact_at`

**Lo que pone el juego:** `gact_terrain_ok()` from the game, `gact_px/py/px2/py2`, `GBE_GACT_MAX`

**Origen y cifras:** world_lab, 12 actors: move 2.6k T, draw 11.9k T (~950 T each: to optimise), think 4-8k; C was 51k

**Ficheros:** `harness/common/src/gbe_gact.c` — en game.json: `"common_src": ["gbe_gact.c"]`

**Juegos que lo usan:** `games/faro`, `games/mazmorra`, `games/world_lab`

## Nombres

| Nombre | Comentario |
|---|---|
| `GBE_GACT_MAX` | Grid actors on gbe_world (NPCs, creatures): cell-by-cell walking at N frames per cell, generic behaviours, one thinker per frame, 16x16 drawing (2 OAM per slot) with the PRIO cell bit. The game... |
| `GACT_ANIM2` | 2 frames 0/4 facing right (creatures) |
| `GACT_ANIMF` | down 0, up 4, side 8 + step 12; down/up step = flip X (faro NPCs) |
| `GACT_PRIO_DIRTY` |  |
| `gact_t` |  |
| `gact` |  |
| `gact_count` |  |
| `gact_npc_frame` |  |
| `gact_px` |  |
| `gact_py` |  |
| `gact_prio_mask` |  |
| `gact_rng` |  |
| `gact_think_every` | 2 = think every other frame (frame parity) |
| `gact_think_frame` | (ver `gact_think_every`) |
| `gact_terrain_ok` | provided by the game |
| `gact_spawn` | 0xFF = full |
| `gact_free` |  |
| `gact_speed` |  |
| `gact_at` | asm: actor on/entering a cell, 0xFF |
| `gact_at_c` |  |
| `gact_free_cell` |  |
| `gact_try_move` |  |
| `gact_step_toward` |  |
| `gact_update` | gact_move_all + one thinker |
| `gact_move_all` | asm |
| `gact_move_all_c` |  |
| `gact_draw` | asm |
| `gact_draw_c` |  |
| `gact_wx` |  |
| `gact_wy` |  |

## Cabecera (`gbe.h`)

```c
// Grid actors on gbe_world (NPCs, creatures): cell-by-cell walking at N frames per cell, generic
// behaviours, one thinker per frame, 16x16 drawing (2 OAM per slot) with the PRIO cell bit.
// The game implements gact_terrain_ok(i, x, y) and keeps gact_px/py (+ px2/py2 while stepping).
// Config: GBE_GACT_MAX (default 12). gact_type: 0 = free, any id; | GACT_ANIM2 = 2-frame layout.
#ifndef GBE_GACT_MAX
#define GBE_GACT_MAX 12
#endif
#define GACT_ANIM2 0x80                  // 2 frames 0/4 facing right (creatures)
#define GACT_ANIMF 0x40                  // down 0, up 4, side 8 + step 12; down/up step = flip X (faro NPCs)
#define GACT_PRIO_DIRTY 0xFF
enum { GACT_STILL, GACT_LOOK, GACT_WANDER, GACT_CHASE, GACT_FLEE, GACT_HOME, GACT_FOLLOW };
typedef struct {                       // 24 bytes; offsets 0-15 are fixed in gbe_gact.s
    uint8_t type, x, y, tx, ty, dir, step, sub, rate_lo, rate_hi, moving, timer, anim, tile, prop, prio;
    uint8_t beh, hx, hy, ox, oy, radius, leader, bumped;
} gact_t;
extern gact_t gact[];
extern uint8_t gact_count, gact_npc_frame[4];
extern uint8_t gact_px, gact_py, gact_px2, gact_py2, gact_prio_mask, gact_rng;
extern uint8_t gact_think_every, gact_think_frame;   // 2 = think every other frame (frame parity)
uint8_t gact_terrain_ok(uint8_t i, uint8_t x, uint8_t y);    // provided by the game
uint8_t gact_spawn(uint8_t type, uint8_t x, uint8_t y, uint8_t tile, uint8_t beh) GBE_FAR;   // 0xFF = full
void gact_free(uint8_t i) GBE_FAR;
void gact_speed(uint8_t i, uint8_t frames_per_cell) GBE_FAR;
uint8_t gact_at(uint8_t x, uint8_t y);                         // asm: actor on/entering a cell, 0xFF
uint8_t gact_at_c(uint8_t x, uint8_t y);
uint8_t gact_free_cell(uint8_t i, uint8_t x, uint8_t y) GBE_FAR;
uint8_t gact_try_move(uint8_t i, uint8_t dir) GBE_FAR;
uint8_t gact_step_toward(uint8_t i, uint8_t x, uint8_t y, uint8_t away) GBE_FAR;
void gact_update(void) GBE_FAR;                // gact_move_all + one thinker
void gact_move_all(void);              // asm
void gact_move_all_c(void);
void gact_draw(uint8_t first_oam);     // asm
void gact_draw_c(uint8_t first_oam);
int16_t gact_wx(uint8_t i) GBE_FAR;
int16_t gact_wy(uint8_t i) GBE_FAR;
```

## Notas de implementación

`gbe_gact.c`:

> gbe: grid actors for top-down games on gbe_world - NPCs and creatures that walk cell by cell.
> 
> Records of 24 bytes (gact_t, offsets fixed in gbe_gact.s), GBE_GACT_MAX slots. An actor stands on
> (x, y); while moving it goes to (tx, ty) and step counts the pixels done (0-15) at a speed given
> in frames per cell (8.8 rate). Both cells are taken (gact_at), as are the player's cells
> (gact_px/py and gact_px2/py2, set by the game). Terrain is the game's: it implements
> gact_terrain_ok(i, x, y) (solid cells, water for swimmers...).
> Behaviours are generic and parameterised (STILL, LOOK, WANDER around home, CHASE / FLEE the
> player, HOME, FOLLOW a leader's trail); game logic (sight, alerts, emotes) changes beh.
> At most one actor thinks per frame (round robin; the rule of games/dungeon and the platformer).
> Moving, drawing and gact_at are asm (gbe_gact.s); their C references live in gbe_selftest.c
> (section GBE_SELFTEST_GACT), which can sit in a switchable bank. Measured in world_lab with 12 actors: C 51k T, asm see README.
