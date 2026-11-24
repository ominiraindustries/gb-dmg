# `gbe_vwf` — gbe_vwf.c

**Ficheros:** `harness/common/src/gbe_vwf.c` — en game.json: `"common_src": ["gbe_vwf.c"]`

**Juegos que lo usan:** `games/happyvalley`, `games/mazmorra`, `games/world_lab`

## Nombres

| Nombre | Comentario |
|---|---|
| `vwf_space` | Proportional text drawn into a strip of tiles (reference + test decoder: harness/vwf.py). Register the fonts once: vwf_font(0, BANK(font), font_tiles, font_vwf), 1 = font_lower, 2 = font_es.... |
| `vwf_font` |  |
| `vwf_width` |  |
| `vwf_clear` |  |
| `vwf_draw` |  |

## Cabecera (`gbe.h`)

```c
// Proportional text drawn into a strip of tiles (reference + test decoder: harness/vwf.py). Register
// the fonts once: vwf_font(0, BANK(font), font_tiles, font_vwf), 1 = font_lower, 2 = font_es.
// Strips up to 31 tiles (the pen is 8-bit). ~2k T per glyph: draw outside VBlank, copy with gbe_tiles.
extern uint8_t vwf_space;
void vwf_font(uint8_t k, uint8_t bank, const uint8_t *tiles, const uint8_t *metrics) GBE_FAR;
uint8_t vwf_width(const char *s) GBE_FAR;
void vwf_clear(uint8_t *buf, uint8_t ntiles) GBE_FAR;
uint8_t vwf_draw(uint8_t *buf, uint8_t ntiles, uint8_t x, const char *s) GBE_FAR;
```

## Notas de implementación

`gbe_vwf.c`:

> gbe: proportional (variable-width) text. Each glyph is drawn at its ink width plus a 1 px gap into
> a strip of tiles in WRAM (one 8 px row of text); the game copies the strip to VRAM (tiles_push or
> LCD off) and points map cells at it. Reference and test decoder: harness/vwf.py (the ROM's strip
> must equal vwf.render byte for byte). Glyph metrics are generated per font: <font>_vwf[] =
> (first ink column << 4) | ink width (harness/asciitiles.py).
> The game registers its fonts once: vwf_font(0, BANK(font), font_tiles, font_vwf) for digits, A-Z
> and - ! . : ? /; 1 = font_lower (a-z); 2 = font_es (, ' ¡ ¿). Any font with the same labels works
> (font_mini...). Cost: ~1.5-2.5k T per glyph in C: draw outside VBlank (a typewriter: 1-2 per frame).
