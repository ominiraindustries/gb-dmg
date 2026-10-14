// TORRE HUNDIDA - shared declarations (design/gdd.md is the spec; section numbers refer to it)
#pragma once
#include "gbe.h"
#include "vram.h"               // VRAM_<TILESET> bases from game.json vram_order
#include "walls.h"
#include "spr.h"
#include "ui.h"
#include "font.h"
#include "view.h"

// ---------------------------------------------------------------- map (GDD 2.0)
enum { CELL_FLOOR, CELL_WALL, CELL_DOOR, CELL_LOCKED, CELL_DOOR_OPEN, CELL_UP, CELL_DOWN };
enum { OBJ_NONE, OBJ_START, OBJ_FAST, OBJ_GUARD, OBJ_GUARD_KEY, OBJ_SLOW, OBJ_POTION, OBJ_STAFF,
       OBJ_AMULET, OBJ_KEY };
#define MAP_W 16

extern uint8_t dmap[256];
extern uint8_t px, py, pf;

// ---------------------------------------------------------------- screen layout (GDD 9.5)
#define VIEW_ROW   8            // the view lives in BG map rows 8-19 of both maps
#define SCY_BASE   64           // ... shown at screen lines 0-95
#define HUD_WY     96           // window (HUD) from line 96, rows 0-5 of $9C00
