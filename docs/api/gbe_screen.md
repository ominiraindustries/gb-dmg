# `gbe_screen` — gbe_screen.c

**Qué hace:** transitions: fade out -> `screen_build(which)` with LCD off -> fade in

**Lo que pone el juego:** `screen_build()`

**Origen y cifras:** platformer

**Ficheros:** `harness/common/src/gbe_screen.c` — en game.json: `"common_src": ["gbe_screen.c"]`

**Juegos que lo usan:** `games/dungeon`, `games/faro`, `games/happyvalley`, `games/mazmorra`, `games/platformer`, `games/shmup`

## Nombres

| Nombre | Comentario |
|---|---|
| `trans_own_fadein` | Transitions: fade out 16 f -> screen_build(next) with the LCD off -> fade in 16 f. The game defines:  void screen_build(uint8_t which); A build that runs its own fade-in sets trans_own_fadein = 1. |
| `transition` |  |
| `show_screen_now` | boot: build + fade in |
| `transition_update` | 1 while a transition owns the frame (freeze logic) |
| `screen_build` | provided by the game |
| `lcd_off_redraw_begin` | DISPLAY_OFF, white, window/sprites off, skip_measure |

## Cabecera (`gbe.h`)

```c
// Transitions: fade out 16 f -> screen_build(next) with the LCD off -> fade in 16 f.
// The game defines:  void screen_build(uint8_t which);
// A build that runs its own fade-in sets trans_own_fadein = 1.
extern uint8_t trans_own_fadein;
void transition(uint8_t next);
void show_screen_now(uint8_t which);   // boot: build + fade in
uint8_t transition_update(void);       // 1 while a transition owns the frame (freeze logic)
void screen_build(uint8_t which);      // provided by the game
void lcd_off_redraw_begin(void);       // DISPLAY_OFF, white, window/sprites off, skip_measure
```

## Notas de implementación

`gbe_screen.c`:

> gbe: screen transitions (fade out -> LCD-off rebuild -> fade in), 16 + 16 frames
