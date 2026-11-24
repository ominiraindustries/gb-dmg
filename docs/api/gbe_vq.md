# `gbe_vq` — gbe_vq.c

**Qué hace:** VRAM write queue (byte stream) with a tile budget per VBlank

**Lo que pone el juego:** `vq_budget` (0 while another big copy runs)

**Origen y cifras:** dungeon: ~20 T per tile (an array-of-entries version: ~150)

**Ficheros:** `harness/common/src/gbe_vq.c` — en game.json: `"common_src": ["gbe_vq.c"]`

**Juegos que lo usan:** `games/dungeon`, `games/faro`, `games/happyvalley`, `games/mazmorra`, `games/world_lab`

## Nombres

| Nombre | Comentario |
|---|---|
| `vq_budget` | VRAM write queue with a tile budget per VBlank (bytes are copied in: callers may reuse buffers) |
| `vq_lost` | (ver `vq_budget`) |
| `vq_push` | 0 = no room (vq_lost++) |
| `vq_push_fill` |  |
| `vq_pending` |  |
| `vq_draw_vram` | VBlank (asm, ~20 T per tile) |
| `GBE_FONT_DIGIT0` | Glyph layout shared by every main font (font, font_mini...: asciitiles.py stops the build if a font with a DIGIT0 label differs), so gbe_text / gbe_vwf work with whichever font the game loads |
| `GBE_FONT_LETTER_A` |  |
| `GBE_FONT_DASH` |  |
| `GBE_FONT_EXCLAM` |  |
| `GBE_FONT_DOT` |  |
| `GBE_FONT_COLON` |  |
| `GBE_FONT_QUESTION` |  |
| `GBE_FONT_SLASH` |  |

## Cabecera (`gbe.h`)

```c
// VRAM write queue with a tile budget per VBlank (bytes are copied in: callers may reuse buffers)
extern uint8_t vq_budget, vq_lost;
uint8_t vq_push(uint8_t *dst, const uint8_t *src, uint8_t len);   // 0 = no room (vq_lost++)
uint8_t vq_push_fill(uint8_t *dst, uint8_t tile, uint8_t len);
uint8_t vq_pending(void);
void vq_draw_vram(void);                        // VBlank (asm, ~20 T per tile)

// Glyph layout shared by every main font (font, font_mini...: asciitiles.py stops the build if a font
// with a DIGIT0 label differs), so gbe_text / gbe_vwf work with whichever font the game loads
#define GBE_FONT_DIGIT0    0
#define GBE_FONT_LETTER_A  10
#define GBE_FONT_DASH      36
#define GBE_FONT_EXCLAM    37
#define GBE_FONT_DOT       38
#define GBE_FONT_COLON     39
#define GBE_FONT_QUESTION  40
#define GBE_FONT_SLASH     41
```

## Notas de implementación

`gbe_vq.c`:

> gbe: VRAM write queue with a per-frame tile budget. Text, HUD fields and cursors are composed
> in update() and pushed here (the bytes are copied into the queue, so callers may reuse their
> buffers); vq_draw_vram() (asm, gbe_vq.s) copies FIFO in VBlank, at most vq_budget tiles per
> frame, continuing a long entry in the next frame. Generalizes the HUD queues of platformer/shmup.
> 
> The queue is one byte stream: [len, dst_lo, dst_hi, data[len]] ... between vq_rd and vq_wr.
> (An array-of-entries version cost ~150 T per tile in VBlank, games/dungeon; the stream copies
> at ~20 T per tile.)
