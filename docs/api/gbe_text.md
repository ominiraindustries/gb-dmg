# `gbe_text` — gbe_text.c

**Qué hace:** shared-font text (`txt_tiles`, `txt_u16`) and a 4-line message log typed through gbe_vq

**Lo que pone el juego:** `txt_font`, `txt_blank`, `txt_lower` (0 = lowercase prints as capitals), "font" in common_res

**Origen y cifras:** dungeon

**Ficheros:** `harness/common/src/gbe_text.c`, `harness/common/src/gbe_log.c` — en game.json: `"common_src": ["gbe_text.c", "gbe_log.c"]`

**Juegos que lo usan:** `games/dungeon`, `games/faro`, `games/happyvalley`, `games/mazmorra`, `games/world_lab`

## Nombres

| Nombre | Comentario |
|---|---|
| `txt_font` | txt_es: VRAM_FONT_ES if "font_es" (¡ ¿ , ') is loaded |
| `txt_blank` | (ver `txt_font`) |
| `txt_lower` | (ver `txt_font`) |
| `txt_es` | (ver `txt_font`) |
| `txt_char` |  |
| `txt_tiles` | pads with blanks |
| `txt_u16` |  |
| `log_lines` |  |
| `log_pending` |  |
| `log_typing` |  |
| `log_speed` |  |
| `log_w` |  |
| `log_init` | 4 lines of width (<= 20) at dst (rows 32 apart) |
| `log_push` | <= 20 chars, up to 4 waiting |
| `log_update` | per frame (outside VBlank) |

## Cabecera (`gbe.h`)

```c
// Shared font text (0-9 A-Z - ! . : ? /, a-z with font_lower) + a 4-line message log through gbe_vq.
// The game sets txt_font = VRAM_FONT, txt_blank = its blank tile, txt_lower = VRAM_FONT_LOWER when
// it loads "font_lower" (common_res); without it lowercase prints as uppercase.
extern uint8_t txt_font, txt_blank, txt_lower, txt_es;   // txt_es: VRAM_FONT_ES if "font_es" (¡ ¿ , ') is loaded
uint8_t txt_char(char c);
uint8_t txt_tiles(uint8_t *dst, const char *s, uint8_t n);       // pads with blanks
void txt_u16(uint8_t *dst, uint16_t v, uint8_t width, uint8_t zero_pad);
extern uint8_t log_lines[4][20], log_pending, log_typing, log_speed, log_w;
void log_init(uint8_t *dst, uint8_t width);     // 4 lines of width (<= 20) at dst (rows 32 apart)
void log_push(const char *s);                   // <= 20 chars, up to 4 waiting
void log_update(void);                          // per frame (outside VBlank)
```

## Notas de implementación

`gbe_text.c`:

> gbe: text with the shared font (harness/common/font.tiles: 0-9, A-Z, - ! . : ? /) and a
> message log typed into a window/BG area through the VRAM queue (gbe_vq).
> The game sets txt_font = VRAM_FONT and txt_blank = its blank tile.

`gbe_log.c`:

> gbe: 4-line message log typed through gbe_vq (games/dungeon). Split from gbe_text.c so games
> without a log do not carry it in bank 0. Needs gbe_text.c.
