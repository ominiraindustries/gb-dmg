# `gbe_frame` — gbe_frame.c

**Qué hace:** input edges, `frame_lines`/`max_frame_lines`, `vram_late` guard, `skip_measure`

**Lo que pone el juego:** -

**Origen y cifras:** tetris, platformer

**Ficheros:** `harness/common/src/gbe_frame.c` — en game.json: `"common_src": ["gbe_frame.c"]`

**Juegos que lo usan:** `games/dungeon`, `games/faro`, `games/gbe_lab`, `games/happyvalley`, `games/mazmorra`, `games/platformer`, `games/shmup`, `games/world_lab`

## Nombres

| Nombre | Comentario |
|---|---|
| `keys` | joypad: held, previous, new this frame |
| `prev_keys` | (ver `keys`) |
| `pressed` | (ver `keys`) |
| `frame_lines` |  |
| `max_frame_lines` |  |
| `skip_measure` |  |
| `vram_late` |  |
| `frame_vsync_ly` | the game sets frame_vsync_ly = LY_REG after vsync() |
| `vram_late_ly` | (ver `frame_vsync_ly`) |
| `frame_begin` | right after vsync(): input + frame start time |
| `frame_vram_check` | right after the VBlank copies: counts writes that ran past VBlank |
| `frame_end` | last thing in the loop: scanlines used (255 = missed a frame) |

## Cabecera (`gbe.h`)

```c
extern uint8_t keys, prev_keys, pressed;                  // joypad: held, previous, new this frame
extern uint8_t frame_lines, max_frame_lines, skip_measure, vram_late;
extern uint8_t frame_vsync_ly, vram_late_ly, vram_late_ly0;   // the game sets frame_vsync_ly = LY_REG after vsync()
void frame_begin(void);       // right after vsync(): input + frame start time
void frame_vram_check(void);  // right after the VBlank copies: counts writes that ran past VBlank
void frame_end(void);         // last thing in the loop: scanlines used (255 = missed a frame)
```

## Notas de implementación

`gbe_frame.c`:

> gbe: frame loop helpers - input edges, frame budget measurement, VRAM-late guard
