# TORRE HUNDIDA — UI spec (ui-designer)

Source of positions: the mockups in `design/screens/*.screen`. The build turns every text run into
`SCREEN_<NAME>_AT_<TEXT>` (= `row * 32 + col`) and `SCREEN_<NAME>_LEN_<TEXT>` (`harness/screens.py`).
**The code uses these defines, never hand coordinates.** Icons and frame pieces are not text, so
they are given here relative to a text define. `row = AT >> 5`, `col = AT & 31`.

Previews: `python harness/gb.py preview dungeon` → `build/preview/screen_*.png`, `tiles_ui.png`,
`tiles_uiscreens.png`.

| Screen | Mockup | How it is drawn |
|---|---|---|
| TITLE | `title.screen` | LCD off (`transition` / `show_screen_now`), BG `$9800`, SCX = SCY = 0, window and sprites off |
| PLAY | `play.screen` | view in BG (double buffer), HUD in the window |
| MENU (PAUSA) | `pause.screen` | overlay in the view canvas, copied by the double buffer |
| OBJETOS | `objetos.screen` | overlay, same |
| ESTADO | `estado.screen` | overlay, same |
| MAPA | `mapa.screen` | 18-row back buffer, window off |
| GAMEOVER | `gameover.screen` | LCD off, like TITLE |
| CLEAR | `clear.screen` | LCD off, like TITLE, + numbers |

The view inside `play/pause/objetos/estado.screen` is a **placeholder** made of automap tiles (the
real pieces are the pixel-artist's `walls.tiles` + `view.pcs`). The HUD rows 12-17 repeated in the
overlay mockups are context only: take HUD defines from `SCREEN_PLAY_*`.

---

## 1. Tiles and VRAM

### 1.1 Tilesets (BG, LCDC.4 = 0)

`"vram_order": ["ui", "font", "font_lower", ["walls", "uiscreens"]]` (current game.json; the real
bases are in the generated `vram.h`, the table below predates `font_lower` (26 tiles, right after font)
and the shared walls/uiscreens slot)

| Set | File | Tiles | BG indices (walls = 166) | Loaded |
|---|---|---|---|---|
| ui | `res/ui.tiles` | **24** | 0-23 (`$9000-$917F`) | boot, with the LCD off; never changes |
| font | `harness/common/font.tiles` | 41 today, **42 with SLASH (E14)** | 24-65 | boot |
| walls | `res/walls.tiles` (pixel-artist) | ≤ 166 | 66-231 | floor load |
| uiscreens | `res/uiscreens.tiles` | **24** | 232-255 (`$8E80-$8FFF`) | boot |

- Base of a set = sum of the counts before it: `UI_COUNT + FONT_COUNT + WALLS_COUNT` for uiscreens
  (headers from `asciitiles.py`). If walls ends up smaller, uiscreens simply moves down; the
  generated screen maps use the same bases.
- uiscreens lives in the GDD's free margin (232-255). Sprites use 0-123 (`$8000-$87BF`), so there is
  no overlap with sprite tiles 232-255 (unused). If the walls ever need that margin, uiscreens can be
  loaded only for TITLE/GAMEOVER/CLEAR over the walls range (needs a per-screen base in
  `screens.py`) — see open questions.
- In C: ui tiles are their label defines as-is (`UI_BLANK` = 0, `UI_CURSOR`...). Font tile for a
  character = `UI_COUNT + FONT_<...>` (gbe_text table, E6).
- Data stays in banks: add `"ui"`, `"uiscreens"` and every `screen_<name>` to `"banked_res"`.

### 1.2 ui.tiles (24)

| Index | Label | Use |
|---|---|---|
| 0 | `BLANK` | empty, box fill, automap "not seen" |
| 1-8 | `FRAME_TL FRAME_T FRAME_TR FRAME_L FRAME_R FRAME_BL FRAME_B FRAME_BR` | box frame (9th piece = BLANK). Run in this order |
| 9 | `CURSOR` | menu cursor (BG tile) |
| 10 | `ICON_HP` | heart, HUD |
| 11 | `ICON_DAGGER` | weapon DAGA (`weapon == 0`) |
| 12 | `ICON_STAFF` | weapon BACULO (`weapon == 1`) |
| 13 | `ICON_AMULET` | amulet owned |
| 14 | `ICON_KEY` | keys |
| 15 | `ICON_POTION` | potions |
| 16 | `ICON_COMPASS` | facing |
| 17-23 | `AM_WALL AM_FLOOR AM_DOOR AM_LOCKED AM_DOWN AM_UP AM_OPEN` | automap cells. Not in `dmap` order: use the 7-entry table `am_tile[type]` of 7.2 |

No separator tile: the HUD has a blank row instead (user preference, CABALLERITO/GRIFO).

### 1.3 uiscreens.tiles (24)

`EARTH, EARTH_EDGE_A, EARTH_EDGE_B, BRICK, MERLON_DOWN, STAFF_ORB, STAFF_SHAFT, STAFF_END,
LOGO_00..LOGO_15`. Used only through the screen maps (TITLE, GAMEOVER, CLEAR); the code never
names them except to load them.

### 1.4 Sprites used by the UI

Only the automap hero arrow (OAM 0, the arrow tiles of `spr.tiles`, pixel-artist). The menu cursor
is a BG tile (see 2.1). Every other sprite (monster OAM 7-18, item 5-6, slash 1-2, claw 3-4, side
warning arrow 0) is hidden (Y = 0) while a menu, the map, or a full screen is shown.

---

## 2. Menus (generic, gbe_menu E7)

### 2.1 Cursor

- `UI_CURSOR` is a **BG tile** placed in the column left of the selected option
  (`col(AT_option) - 1`, same row). The mockups show it on the default option.
- Move = 2 tile writes: `UI_BLANK` on the old cell, `UI_CURSOR` on the new one, through the VRAM
  queue to the **visible** map (`bg_front`; overlay rows are at map row `8 + screen row`, full
  screens at map row `screen row`). Write the same change into the canvas (`view_buf`) so a later
  copy of the canvas stays consistent.
- No blink (0 tile writes while idle).
- Why BG and not the GDD's sprite: it is drawn by the same code that draws the box (canvas and
  `.screen`), it needs no sprite tiles on TITLE (sprites are loaded with the floor), it does not
  fight the side-attack arrow for OAM 0, and 8x16 sprite mode would need a half-empty sprite. Cost:
  2 tiles per move. (Open question 1 if the sprite is preferred.)

### 2.2 Input

| Button | Action |
|---|---|
| ↑ / ↓ | move; wraps (top ↔ bottom). Held: first repeat after **16 f**, then every **6 f** (tetris). Disabled options are skipped. SFX `MENU_MOVE` |
| A | confirm. SFX `MENU_OK` (or the action's own SFX) |
| B | back one level (or nothing where noted). SFX `MENU_BACK` |
| Start | in game: close every menu and return to PLAY. On TITLE / GAMEOVER / CLEAR: same as A |
| Select | only in PLAY / MAP (automap) |
| ← / → | nothing in M1 |

- Input to an overlay is ignored while its copy is in progress (`bgbuf_busy()`), so the cursor is
  never written to the map that is about to be replaced. A press during those 3 frames is not
  buffered (menus feel instant enough at 50 ms).
- All game timers stop while `state` is MENU or MAP (GDD 2.0). The low-HP heart blink keeps running
  (it is UI).

---

## 3. TITLE (`title.screen`)

| Element | Where | Notes |
|---|---|---|
| Logo "TORRE" | rows 3-4, cols 5-14 | tiles, static |
| `H_U_N_D_I_D_A` | `SCREEN_TITLE_AT_H_U_N_D_I_D_A` | static |
| Staff | row 8, cols 4-16 | static |
| `NUEVA_PARTIDA` | `SCREEN_TITLE_AT_NUEVA_PARTIDA` | option 0 |
| `CONTINUAR` | `SCREEN_TITLE_AT_CONTINUAR` | option 1, only with a valid save |
| Cursor | col `col(AT_NUEVA_PARTIDA) - 1` | the mockup has it on CONTINUAR |
| `2026` | `SCREEN_TITLE_AT_2026` | static |

- Build (LCD off): copy `screen_title_map`. Then `save_load()`:
  - valid save → cursor on CONTINUAR (as in the mockup), `menu_sel = 1`;
  - no save → write `SCREEN_TITLE_LEN_CONTINUAR` BLANKs at `AT_CONTINUAR`, move the cursor tile to
    the NUEVA PARTIDA row, `menu_sel = 0`, CONTINUAR disabled (↑/↓ do nothing).
- A / Start: seed `rng_state` (DIV + frame counter, GDD 2.0), SFX `MENU_OK`, `transition(PLAY)`
  (16 f fade to white → floor load with LCD off → 16 f fade in). CONTINUAR loads the save inside
  `screen_build`. B: nothing.
- NUEVA PARTIDA with a save present does **not** erase it; it is replaced only by GUARDAR.
- The first message of a new game in the log is `Piso 1`; after CONTINUAR, `Partida cargada`
  (new string, see 11).

## 4. PLAY: HUD in the window (`play.screen`, rows 12-17)

Window: `WY = 96`, `WX = 7`, map `$9C00` rows 0-5 (LCDC.6 = 1, LCDC.5 = 1).
**Window offset of a define = `SCREEN_PLAY_AT_x - 12 * 32`** (window row = screen row - 12).

### 4.1 Status row (window row 0)

| Element | Position | Content |
|---|---|---|
| Heart | `AT_18_20 - 1` | `ICON_HP` (blinks, below) |
| HP | `SCREEN_PLAY_AT_18_20`, 5 tiles | `hp` 2 digits with a leading blank (" 8"), `/` (SLASH; DASH until E14), `hp_max` 2 digits |
| Weapon | `AT_18_20 + 6` | `ICON_DAGGER` (weapon 0) / `ICON_STAFF` (weapon 1) |
| Amulet | `AT_18_20 + 7` | `ICON_AMULET` if `amulet`, else BLANK |
| Key icon | `SCREEN_PLAY_AT_1 - 1` | `ICON_KEY` always |
| Keys | `SCREEN_PLAY_AT_1`, 1 tile | digit 0-9 |
| Potion icon | `SCREEN_PLAY_AT_3 - 1` | `ICON_POTION` always |
| Potions | `SCREEN_PLAY_AT_3`, 1 tile | digit 0-9 |
| Compass | `SCREEN_PLAY_AT_N - 1` | `ICON_COMPASS` always |
| Facing | `SCREEN_PLAY_AT_N`, 1 tile | `N E S O` for `pf` 0-3 |

- `update()` renders the whole row into `hud_buf[20]` when a dirty flag is set (hp, hp_max, weapon,
  amulet, keys, potions, pf) and queues **20 tiles once**.
- **Low HP:** while `hp <= hp_max / 4` (≤ 5 of 20) the heart alternates `ICON_HP` / `BLANK` every
  **16 f** (1 tile per toggle, queued). It stops showing BLANK as soon as hp rises. (CABALLERITO's
  blinking hourglass was liked.)
- Window row 1 is blank on purpose (no separator line).

### 4.2 Message log (window rows 2-5)

Lines: `SCREEN_PLAY_AT_PISO_1` (oldest), `AT_ABRES_LA_PUERTA`, `AT_GOLPE_3`, `AT_DIABLILLO_CAE`
(newest, bottom) — use only their **row**; every line is 18 tiles from col 1 (the sample texts are
the code's to blank: start with 4 empty lines).

- `log_lines[4][18]` holds tile indices (rendered in `update()` from the string, blanks to 18).
- New message (from the FIFO `log_pending`, ≤ 4; full → drop the oldest *pending* one):
  1. shift `log_lines` up one line, clear line 3;
  2. queue window rows 2, 3, 4 (lines 0-2, 54 tiles) and row 5 blank (18 tiles) = **72 tiles**;
  3. then "type" line 3: **2 characters per frame** (2 tiles queued per frame; 18 chars = 9 f);
  4. when typing ends, the next pending message starts. A does not speed it up (A attacks).
- Messages stay until pushed out (no timeout).
- Strings longer than 18 are split by the caller into 2 messages ("No puedes" / "llevar mas").

### 4.3 Tiles per frame (VRAM queue, GDD 9.3)

| Frame | Queue budget | Typical use |
|---|---|---|
| with a view copy (3 per step) | 16 | typing 2, status row in 2 frames, scroll in 5 |
| without a view copy | 48 | scroll + clear (72) in 2 frames, status 20 in 1 |

Order in the queue: scroll/clear before typing (FIFO does it); the status row can interleave.

## 5. MENU / PAUSA (`pause.screen`)

- PLAY + Start (only when `play_sub == IDLE`; during BUSY the press is buffered like a step;
  ignored in DYING) → `state = MENU`, `menu_page = 0`, `menu_sel = 0` (always opens on OBJETOS),
  hide sprites, SFX `MENU_OK`.
- Canvas = current view (`view_buf` still holds it) + box rows 2-10, cols 4-15 copied from
  `screen_pause_map` + cursor; `bgbuf_start()` → 3 frames → swap. The HUD window stays.
- Box: frame rows 2 and 10, cols 4 and 15 (= `row(AT_OBJETOS) - 2` .. `row(AT_VOLVER) + 2`,
  `col(AT_OBJETOS) - 3` .. `col(AT_OBJETOS) + 8`). Options: `SCREEN_PAUSE_AT_OBJETOS`, `_ESTADO`,
  `_MAPA`, `_GUARDAR`, `_VOLVER` (col 7, rows 4-8). Cursor col 6.

| Option | A |
|---|---|
| OBJETOS | `menu_page = 1`: OBJETOS box painted over the canvas (it covers the pause box completely), copy 3 f |
| ESTADO | `menu_page = 2`, same |
| MAPA | open the automap (7), returning to this menu on close |
| GUARDAR | save at once (`save_store`, frame marked `skip_measure`), SFX `SAVE`, log `Partida guardada` (or `Error al guardar`); the menu stays open with the cursor on GUARDAR so the log line is seen |
| VOLVER | close |

- B or Start or VOLVER → close: `view_compose()` of the current position into the canvas,
  copy 3 f, sprites shown again **on the swap frame** (from `shown_x/y/f`), timers resume after the
  swap.
- `menu_page 3 (CONFIRMAR)` of the GDD is not used by this design (open question 4).

## 6. OBJETOS (`objetos.screen`) and ESTADO (`estado.screen`)

Box: frame rows 1 and 10, cols 1 and 18; title on row 2 col 3; content from row 4.

### 6.1 OBJETOS

- Title `SCREEN_OBJETOS_AT_OBJETOS`.
- List, packed from the row of `SCREEN_OBJETOS_AT_POCION` (row 4), one entry per row, only owned
  entries, this order: POCION (if `potions > 0`), LLAVE (`keys > 0`), DAGA (always), BACULO (owned),
  AMULETO (`amulet`). Name column = `col(AT_POCION)` (4), cursor column 3.
- Marker column = `col(SCREEN_OBJETOS_AT_X3)` (15), 2 tiles: `x<n>` (lowercase x, as in the mockup) for POCION and LLAVE; `EQ` on
  the equipped weapon and on AMULETO; blank otherwise.
- Cursor starts on the first entry. B → back to PAUSA (recompose view + pause box, 3 f). Start →
  close all.

| Entry | A |
|---|---|
| POCION | `hp < hp_max`: `potions - 1`, `hp = min(hp + 10, hp_max)`, SFX `DRINK`, log `Recuperas # PV` with the **real** amount healed. `hp == hp_max`: log `Ya estas sano`, not used, SFX `LOCKED` |
| DAGA / BACULO | equip it (`weapon` 0/1), SFX `MENU_OK`, log `Equipas la daga` / `Equipas el baculo` (new strings); already equipped: nothing |
| LLAVE / AMULETO | nothing, SFX `MENU_BACK` |

- Small changes (count `x3`→`x2`, `EQ` moving: ≤ 4 tiles) go through the VRAM queue to the visible
  map and the canvas. If the list changes length (last potion drunk), re-render the box into the
  canvas and copy it with bgbuf (3 f); the cursor keeps its index, clamped to the new length.
- The HUD status row updates at the same time (hp, potions, weapon icon).
- **Needs a new global:** the code must know the staff is owned when the dagger is equipped
  (`weapon` alone cannot say it). Proposal: `staff_owned` (u8). See open question 5.

### 6.2 ESTADO (read-only)

| Line | Label define | Value | Width |
|---|---|---|---|
| title | `SCREEN_ESTADO_AT_APRENDIZ` | — | — |
| PV | `AT_PV` | `hp/hp_max`, e.g. "18/20", " 8/20" | 5 |
| ATAQUE | `AT_ATAQUE` | weapon damage range "1-2" / "2-4" (DASH) | 3 |
| DEFENSA | `AT_DEFENSA` | 0 / 1 | 1 |
| DERROTADOS | `AT_DERROTADOS` | `kills`, right-aligned | 2 |
| TIEMPO | `AT_TIEMPO` | `play_secs` as mm:ss, caps at 99:59 | 5 |
| PISO | `AT_PISO` | floor number | 1 |

- All values are **right-aligned with their last tile at col 17** (the frame is col 18); the row is
  the row of the label define. Blank the field to its full width before writing.
- A, B → back to PAUSA. Start → close all.

## 7. MAPA (`mapa.screen`)

### 7.1 Open / close

- Open: Select in PLAY (`play_sub == IDLE`, else buffered) or MAPA in PAUSA. `state = MAP`, sprites
  hidden. Canvas of 18 rows built 4 rows per frame (GDD 2.10) and copied to map rows 8-25 of the
  back buffer, 4 rows per VBlank; **on the swap VBlank**: LCDC.5 = 0 (window off), LCDC.3 swap,
  SCX = 0, SCY = 64, hero sprite on. Nothing of the HUD shows (rows 12-17 are map rows 20-25).
- Close: B or Select (Start = close all → PLAY). Recompose the view, refill margin rows 20-25 of that
  buffer with the floor/background pattern, copy, and **on the swap VBlank** LCDC.5 = 1 again.
  Returns to PAUSA (with MAPA selected) if it was opened from there, else to PLAY.

### 7.2 Content

- Title `SCREEN_MAPA_AT_MAPA_PISO_1`: floor digit at `AT + LEN - 1`.
- `SCREEN_MAPA_AT_B_VOLVER` static.
- The `p` of `Mapa` (row 0) drops 1 px onto the top edge of the map at row 1 (dark wall tiles in
  explored maps): a small merge, still readable; see open question in the UI report.
- Cell (x, y) → screen row `1 + y`, col `2 + x` (map 16x16 at rows 1-16, cols 2-17).

| Cell (`dmap`) | not in `seen` | seen |
|---|---|---|
| any | `BLANK` | — |
| 0 FLOOR | | `AM_FLOOR` |
| 1 WALL | | `AM_WALL` |
| 2 DOOR | | `AM_DOOR` |
| 3 LOCKED | | `AM_LOCKED` |
| 4 DOOR_OPEN | | `AM_OPEN` |
| 5 UP | | `AM_UP` |
| 6 DOWN | | `AM_DOWN` |

- Objects and monsters are not shown (the map is for orientation).
- Hero: OAM 0, arrow by `pf` (up / right, flipY for down, flipX for left), screen
  `x = (2 + px) * 8`, `y = (1 + py) * 8` (OAM +8 / +16). 8x16 mode: arrow in the top tile, bottom tile
  blank. Blinks **16 on / 16 off** so it can be found at a glance. The mockup uses `ui:CURSOR` as a
  stand-in for the pixel-artist's arrow.
- Sprites: 1. Tiles: 360 through the double buffer (5 frames); no queue use.

## 8. GAMEOVER (`gameover.screen`)

- `hp == 0` → `play_sub = DYING`: input locked, fade to **black** 32 f (`set_fade_dark` 1, 2, 3 every
  8 f, then BGP = 0xFF for the last 8 f; E2), SFX `DEATH`. Then LCD off, copy
  `screen_gameover_map`, sprites hidden, fade in **from black** 16 f (3, 2, 1, 0 every 4 f).
- `SCREEN_GAMEOVER_AT_HAS_CAIDO` static. Options `AT_CONTINUAR` (default, cursor as in the mockup)
  and `AT_TITULO`, cursor col `col(AT_CONTINUAR) - 1`.
- A / Start on CONTINUAR: `transition(PLAY)` loading the last save; with no valid save, restart the
  floor (same label). TITULO: `transition(TITLE)`. B: nothing.

## 9. CLEAR (`clear.screen`)

- Entering DOWN: log `Bajas la escalera`, SFX `CLEAR`, after **30 f** (the line is typed) →
  `transition(CLEAR)`.
- Build (LCD off): copy `screen_clear_map`, then write the values straight into VRAM (LCD is off):

| Value | Where | Format |
|---|---|---|
| floor | `SCREEN_CLEAR_AT_PISO_1_SUPERADO + 5` | 1 digit |
| time | `AT_04_12`, 5 | `play_secs` mm:ss |
| defeated | right end `AT_6_8 + LEN_6_8 - 1` (col 17), field cols 13-17 | `kills/total` (e.g. " 6/8", "12/12"), right-aligned |
| items | right end `AT_5_6 + LEN_5_6 - 1` (col 17), field cols 13-17 | `picked/total` |

- `AT_FIN_DE_LA_DEMO`: shown in M1; from M2 (more floors) the code blanks it.
- `AT_PULSA_START` blinks **30 on / 30 off** (11 tiles per toggle, queued).
- Start or A → `transition(TITLE)`. B: nothing.

## 10. Transitions and fades

| Change | Sequence | Frames |
|---|---|---|
| TITLE → PLAY, GAMEOVER → PLAY/TITLE, CLEAR → TITLE, PLAY → CLEAR | `transition()`: fade to white 16 f (`set_fade` 1, 2, 3 every 4 f) → `screen_build` with LCD off (`skip_measure`) → fade in 16 f | 32 + build |
| PLAY → DYING → GAMEOVER | fade to black 32 f → build → fade in from black 16 f | 48 + build |
| PLAY ↔ MENU / OBJETOS / ESTADO | no fade: double-buffer copy, instant swap | 3 |
| PLAY / MENU ↔ MAPA | no fade: copy + window toggle on the swap VBlank | 5 (open) / 3 (close) |
| Step / turn in PLAY | GDD 2.1 (bob, slide) | 3 |

Boot: `show_screen_now(TITLE)` (build + fade in). ui, font and uiscreens are loaded once at boot.

## 11. Text strings

Spanish, **sentence case** (upper and lower case), no accents, no Ñ; glyphs `A-Z a-z 0-9 - ! . : ?`
and `/` (E14). `#` = number. Capital only at the start of each label / menu item / log line, in
acronyms (`PV`, `EQ`), button names (`Start`, `B:`) and the compass letters `N E S O`. The title
`H U N D I D A` (and the `TORRE` tile logo) stay in capitals: it is the game's name, drawn as a logo.
Lowercase comes from `harness/common/font_lower.tiles` (loaded after font; `g j p q y` drop 1 px into
row 7 of the tile). Log strings from GDD 2.11 are written in sentence case too ("Abres la puerta").

- **Stacked lines** (the 4-line log in the HUD, the ESTADO list): a descender may touch the line
  below (e.g. `Golpe: 3` over `Diablillo cae`). Accepted: it reads fine at 1x.
- **Mockups:** lowercase letters are text, so legend keys must never be letters (the overlays use
  `#` AM_WALL and `+` AM_UP, the map `# , + & ^ $ %`, the logo Greek letters, MERLON_DOWN `ν`).

**Screens / menus** (in the mockups): `H U N D I D A`, `Nueva partida`, `Continuar`, `2026`,
`Objetos`, `Estado`, `Mapa`, `Guardar`, `Volver`, `Pocion`, `Llave`, `Daga`, `Baculo`, `Amuleto`,
`x#`, `EQ`, `Aprendiz`, `PV`, `Ataque`, `Defensa`, `Derrotados`, `Tiempo`, `Piso`, `Mapa - Piso #`,
`B: Volver`, `Has caido`, `Titulo`, `Piso # superado`, `Fin de la demo`, `Pulsa Start`.

**Log** (≤ 18): GDD 2.11 list, plus three new ones proposed here:

| String | Len | When |
|---|---|---|
| `Partida cargada` | 15 | after CONTINUAR (title or game over) |
| `Equipas la daga` | 15 | OBJETOS, A on DAGA |
| `Equipas el baculo` | 17 | OBJETOS, A on BACULO |

## 12. Checks

- Sprites per line: menus, map and full screens hide everything but the map arrow (1). PLAY is the
  GDD's 9/10.
- Readability: all text is black font on white; boxes have a white outer pixel and a thick black
  edge, so they stand out from any wall texture; automap: unseen white, floor light dither, walls dark,
  specials in black; the goal (`AM_DOWN`) is the heaviest mark.
- VBlank: no screen change writes more than the queue budget per frame; full-screen changes are
  LCD-off (`skip_measure`), overlays use the double buffer. Prohibited: `set_bkg_tiles` in game.
- Tests can read `menu_page`, `menu_sel`, `state`, and compare the visible map against the mockup
  map + the values (e.g. ESTADO values right-aligned at col 17).

## 13. Notes for E14 (SLASH)

`harness/common/font.tiles` gets `@ SLASH` (appended after QUESTION). Also in `harness/screens.py`:
add `/` to `TEXT_CHARS` and `"SLASH"` to the punctuation tuple, and in `harness/preview.py` map the
grid char `/` to SLASH like the letters. Then delete the `/ DASH` legend line from every
`.screen` that has it (play, pause, objetos, estado, clear) (the define names `18_20`, `6_8`, `5_6` stay the same). Until then the
mockups show `-` where `/` goes.
