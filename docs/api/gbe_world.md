# `gbe_world` — gbe_world.c

**Qué hace:** 4-way scrolling world of 16x16 metatiles (top-down RPGs): maps of sectors (16x16 cells) from `res/maps/*.map` (`harness/world.py`, banked), 3x3 sector cache in WRAM (half a sector loaded per frame), BG ring with a 13x12-cell drawn region, edge queue of lines drawn 3 metatiles per VBlank, asm `wmt_at`/`wprep_cell`

**Lo que pone el juego:** `GBE_WORLD_MT`, `world_metatiles()` from `mt_tiles`/`mt_attr`

**Origen y cifras:** world_lab: worst ~10k T per frame (C first version 38k), screen == map model every frame of a 7000-frame walk

**Ficheros:** `harness/common/src/gbe_world.c` — en game.json: `"common_src": ["gbe_world.c"]`

**Juegos que lo usan:** `games/faro`, `games/mazmorra`, `games/world_lab`

## Nombres

| Nombre | Comentario |
|---|---|
| `GBE_WORLD_MT` | 4-way scrolling world of 16x16 metatiles in sectors of 16x16 cells (top-down RPGs). Maps come from res/maps/*.map (harness/world.py: map_<name> in a bank). WRAM caches the 3x3 sectors around the... |
| `world_map_t` |  |
| `GBE_WORLD_EV_MAX` | objects per sector (world.py checks it) |
| `wevGBE_WORLD_EV_MAX` |  |
| `wev_n` | wevq_sx = 0xFF: forget world_event_at's sector copy |
| `wmap_id` | (ver `wev_n`) |
| `wevq_sx` | (ver `wev_n`) |
| `wmap` | header of the current map (w, h in sectors...) |
| `wmt_tilesGBE_WORLD_MT` |  |
| `wmt_attrGBE_WORLD_MT` |  |
| `cam_x` | world px of the screen's top-left |
| `cam_y` | (ver `cam_x`) |
| `reg_x` | top-left cell of the drawn 13x12 region |
| `reg_y` | (ver `reg_x`) |
| `wcache_sector` |  |
| `world_loaded_slot` |  |
| `world_edge_budget` |  |
| `edge_pending` |  |
| `world_loaded_sx` | sector completed this frame (world_loaded_slot != 0xFF) |
| `world_loaded_sy` | (ver `world_loaded_sx`) |
| `world_lost` | edge-queue overflows (must stay 0) |
| `world_metatiles` |  |
| `world_load` |  |
| `world_update` | = focus + camera + prepare |
| `world_focus` |  |
| `world_camera` |  |
| `world_prepare` |  |
| `world_draw_vram` | VBlank |
| `wmt_at` | metatile at a cell (cache; border outside the map) |
| `wmt_at_c` | C reference (gbe_selftest.c, GBE_SELFTEST_WORLD) |
| `wattr_at` |  |
| `world_set_cell` | temporary patch (until the sector reloads) |
| `world_load_id` | MAP_<NAME> |
| `world_map_mtset` | its metatile set: load the tiles + metatiles first |
| `world_events` | copy a sector's objects to wev[] -> wev_n |
| `world_event_at` | object on a cell (0 = none); fills wev[] |

## Cabecera (`gbe.h`)

```c
// 4-way scrolling world of 16x16 metatiles in sectors of 16x16 cells (top-down RPGs). Maps come from
// res/maps/*.map (harness/world.py: map_<name> in a bank). WRAM caches the 3x3 sectors around the
// focus cell; the BG map is a ring (cell x, y at BG metatile x & 15, y & 15; SCX/SCY = camera).
// Loop: world_draw_vram() in VBlank; after the logic world_update(player cell, camera px).
// The camera may move at most 16 px per frame (bigger jumps: world_load with the LCD off).
// Config: GBE_WORLD_MT = metatile slots (default 128). Maps <= 15x15 sectors (u8 cells).
#ifndef GBE_WORLD_MT
#define GBE_WORLD_MT 128
#endif
typedef struct {
    uint8_t w, h, border, nsec;          // size in sectors, metatile outside, unique sectors
    uint8_t mtset;                       // metatile set: index of res/metatiles*.mt (sorted names)
    const uint8_t *grid;                 // w*h unique-sector indices
    const uint8_t *sectors;              // nsec x 256 metatile ids (row-major 16x16)
    const uint8_t *events;               // 8-byte object records sorted by sector (world.py)
    const uint16_t *evidx;               // first record of each sector, w*h + 1 entries
} world_map_t;
#ifndef GBE_WORLD_EV_MAX
#define GBE_WORLD_EV_MAX 16              // objects per sector (world.py checks it)
#endif
typedef struct { uint8_t x, y, type, d[5]; } world_ev_t;   // d: fields in game.json world_objects order
extern world_ev_t wev[GBE_WORLD_EV_MAX];
extern uint8_t wev_n, wmap_id, wevq_sx;   // wevq_sx = 0xFF: forget world_event_at's sector copy
extern world_map_t wmap;                 // header of the current map (w, h in sectors...)
extern uint8_t wmt_tiles[GBE_WORLD_MT][4], wmt_attr[GBE_WORLD_MT];
extern int16_t cam_x, cam_y;            // world px of the screen's top-left
extern uint8_t reg_x, reg_y;            // top-left cell of the drawn 13x12 region
extern uint8_t wcache_sector[9], world_loaded_slot, world_edge_budget, edge_pending;
extern uint8_t world_loaded_sx, world_loaded_sy;   // sector completed this frame (world_loaded_slot != 0xFF)
extern uint16_t world_lost;             // edge-queue overflows (must stay 0)
void world_metatiles(uint8_t bank, const uint8_t *tiles, const uint8_t *attr, uint8_t n);
void world_load(uint8_t bank, const world_map_t *map, uint8_t fx, uint8_t fy, int16_t cx, int16_t cy);
void world_update(uint8_t fx, uint8_t fy, int16_t cx, int16_t cy);   // = focus + camera + prepare
void world_focus(uint8_t x, uint8_t y);
void world_camera(int16_t x, int16_t y);
void world_prepare(void);
void world_draw_vram(void);                                           // VBlank
uint8_t wmt_at(uint8_t x, uint8_t y);    // metatile at a cell (cache; border outside the map)
uint8_t wmt_at_c(uint8_t x, uint8_t y);      // C reference (gbe_selftest.c, GBE_SELFTEST_WORLD)
uint8_t wattr_at(uint8_t x, uint8_t y);
void world_set_cell(uint8_t x, uint8_t y, uint8_t mt);   // temporary patch (until the sector reloads)
void world_load_id(uint8_t map_id, uint8_t fx, uint8_t fy, int16_t cx, int16_t cy);   // MAP_<NAME>
uint8_t world_map_mtset(uint8_t map_id);      // its metatile set: load the tiles + metatiles first
uint8_t world_events(uint8_t sx, uint8_t sy);   // copy a sector's objects to wev[] -> wev_n
world_ev_t *world_event_at(uint8_t x, uint8_t y);   // object on a cell (0 = none); fills wev[]
```

## Notas de implementación

`gbe_world.c`:

> gbe: 4-way scrolling world of 16x16 metatiles (top-down RPGs and adventures).
> 
> A map (harness/world.py, res/maps/*.map) is a grid of sectors of 16x16 cells stored in a ROM bank.
> WRAM keeps the 3x3 sectors around the focus cell (the player): queries never switch banks, and
> one sector is (re)loaded per frame when the focus crosses into another sector.
> The 32x32 BG map is a ring of 16x16 metatiles: cell (x, y) lives at BG metatile (x & 15, y & 15),
> SCX/SCY = camera & 255. The drawn region is 13x12 cells around the camera (screen + 1 cell of
> margin on every side); when the camera crosses a cell boundary the entering column/row is
> queued and drawn at world_edge_budget metatiles per VBlank (vram_mt4_list, ~100 T each).
> Cells are u8: maps up to 15x15 sectors, so coordinates 240-255 are always outside (= border),
> including the "negative" cells the camera shows left of / above cell 0.
