# `gbe_tbox` — gbe_tbox.c

**Qué hace:** dialogue box in the window: typewriter (1-2 chars/f, A finishes the page), pages with a blinking arrow, speaker tab, yes/no, 2x2 choice; all through gbe_vq

**Lo que pone el juego:** `tbox_frame[9]`, `tbox_arrow`, `tbox_cursor`; the game shows the window while `tbox_visible`

**Origen y cifras:** world_lab: conversation test

**Ficheros:** `harness/common/src/gbe_tbox.c` — en game.json: `"common_src": ["gbe_tbox.c"]`

**Juegos que lo usan:** `games/faro`, `games/world_lab`

## Nombres

| Nombre | Comentario |
|---|---|
| `tbox_win` | Dialogue box in the window (typewriter, pages, speaker tab, yes/no, 2x2 choice) through gbe_vq. The game sets tbox_frame[9], tbox_arrow, tbox_cursor, tbox_row (and tbox_win) and shows the window... |
| `tbox_row` |  |
| `tbox_frame` |  |
| `tbox_arrow` |  |
| `tbox_cursor` |  |
| `tbox_speed` |  |
| `tbox_yes_col` |  |
| `tbox_no_col` |  |
| `tbox_auto` | > 0: the last page closes alone after that many frames (battle) |
| `tbox_name` |  |
| `tbox_text` |  |
| `tbox_speaker` |  |
| `tbox_state` |  |
| `tbox_visible` |  |
| `tbox_answer` |  |
| `tbox_nchoices` |  |
| `tbox_start` | shows tbox_text: TB_SAY, TB_ASK (one line), TB_CHOICE |
| `tbox_speaker_set` | "" = no tab |
| `tbox_close` |  |
| `tbox_draw_choices` |  |
| `tbox_update` | 1 while it needs the player |

## Cabecera (`gbe.h`)

```c
// Dialogue box in the window (typewriter, pages, speaker tab, yes/no, 2x2 choice) through gbe_vq.
// The game sets tbox_frame[9], tbox_arrow, tbox_cursor, tbox_row (and tbox_win) and shows the window
// while tbox_visible. tbox_update() once per frame before script_update().
enum { TB_CLOSED, TB_OPEN, TB_SAY, TB_ASK, TB_PAGE, TB_END, TB_YESNO, TB_CHOOSE, TB_CHOICE };
extern uint8_t *tbox_win;
extern uint8_t tbox_row, tbox_frame[9], tbox_arrow, tbox_cursor, tbox_speed, tbox_yes_col, tbox_no_col;
extern uint8_t tbox_auto;               // > 0: the last page closes alone after that many frames (battle)
extern char tbox_name[8], tbox_text[256], tbox_speaker[13];
extern uint8_t tbox_state, tbox_visible, tbox_answer, tbox_nchoices;
void tbox_start(uint8_t kind) GBE_FAR;          // shows tbox_text: TB_SAY, TB_ASK (one line), TB_CHOICE
void tbox_speaker_set(const char *s) GBE_FAR;   // "" = no tab
void tbox_close(void) GBE_FAR;
void tbox_draw_choices(void) GBE_FAR;
uint8_t tbox_update(void) GBE_FAR;              // 1 while it needs the player
```

## Notas de implementación

`gbe_tbox.c`:

> gbe: dialogue box in the window - typewriter, pages with a blinking 'more' arrow, speaker tab,
> yes/no question and a 2x2 choice. Text comes from gbe_script (bytes of harness/script.py: lines
> already wrapped, 0x0A new line, 0x0C new page, 0x01 player name, 0 end).
> 
> Layout (defaults = games/faro ui.md 4, a 20x6 box at window rows tbox_row..+5): frame pieces
> tbox_frame[9] (TL T TR L blank R BL B BR), text lines at rows +2 and +4 from column 1, speaker tab
> at row 0 from column 3 (blank before and after), arrow at row +5 column 17, yes/no on line 2 at
> columns tbox_yes_col / tbox_no_col, choices at columns 2 and 11 of lines 1-2 (cursor one column
> before). All tiles go through gbe_vq (1-2 per frame while typing, 8 when A finishes a page).
> The game shows the window while tbox_visible (WY = 96 in VBlank) and sets the tile variables.
