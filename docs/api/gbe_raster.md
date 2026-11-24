# `gbe_raster` — gbe_raster.c / .s

**Ficheros:** `harness/common/src/gbe_raster.c`, `harness/common/src/gbe_raster.s` — en game.json: `"common_src": ["gbe_raster.c", "gbe_raster.s"]`

**Juegos que lo usan:** ninguno todavía

## Nombres

| Nombre | Comentario |
|---|---|
| `RASTER_MAX` | Up to RASTER_MAX SCX changes per frame at chosen lines (parallax, curving tracks). Fill raster_line[] (ascending, >= 1) / raster_scx[] / raster_n, then raster_commit(); taken at the next VBlank.... |
| `raster_n` |  |
| `raster_line` |  |
| `raster_scx` |  |
| `raster_init` |  |
| `raster_commit` |  |
| `raster_isr` | asm (gbe_raster.s), installed by raster_init |

## Cabecera (`gbe.h`)

```c
// Up to RASTER_MAX SCX changes per frame at chosen lines (parallax, curving tracks). Fill raster_line[]
// (ascending, >= 1) / raster_scx[] / raster_n, then raster_commit(); taken at the next VBlank. Line 0
// keeps scx_shadow. raster_init() after video_init(); not together with gbe_video's hud_cut.
#ifndef RASTER_MAX
#define RASTER_MAX 10
#endif
extern uint8_t raster_n, raster_line[], raster_scx[];
void raster_init(void);
void raster_commit(void);
void raster_isr(void);                  // asm (gbe_raster.s), installed by raster_init
```

## Notas de implementación

`gbe_raster.c`:

> gbe: raster SCX splits - up to RASTER_MAX horizontal scroll changes per frame at chosen lines
> (parallax bands, a track that curves away, wavy water). The game fills raster_line[] / raster_scx[]
> (lines ascending, >= 1) and raster_n in its update, then raster_commit(); the VBlank handler takes
> the new table at the start of the next frame (double buffer: the ISR never reads a half-written one).
> Line 0's SCX stays gbe_video's scx_shadow (+ shake_x). Each entry costs one LYC interrupt (~150 T,
> the handler in gbe_raster.s waits for HBlank before writing SCX, so the split is clean).
> Needs video_init() first (it enables the LYC interrupt); call raster_init() after it. The HUD cut of
> gbe_video (hud_cut) and the raster both use LYC: a game uses one or the other.
> PyBoy draws mid-frame SCX changes, so tests see the bands; real-hardware timing: check on a device.

`gbe_raster.s`:

> gbe: the raster LCD handler (see gbe_raster.c). Called at LYC = line - 1 of the next split: waits
> for that line's HBlank, writes SCX (taking effect on `line`), arms the next split.
