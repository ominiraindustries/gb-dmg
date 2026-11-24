# `gbe_video` — gbe_video.c

**Qué hace:** VBlank shadows (SCX, SCY, palettes) + `shake_x/y`, fades, top-HUD window cut (LYC ISR), `bgp_below` (BG palette under the cut)

**Lo que pone el juego:** `video_init(line, bgp, obp0, obp1)`

**Origen y cifras:** platformer, shmup

**Ficheros:** `harness/common/src/gbe_video.c` — en game.json: `"common_src": ["gbe_video.c"]`

**Juegos que lo usan:** `games/dungeon`, `games/faro`, `games/gbe_lab`, `games/happyvalley`, `games/mazmorra`, `games/platformer`, `games/shmup`, `games/world_lab`

## Nombres

| Nombre | Comentario |
|---|---|
| `scx_shadow` | Register shadows written by the library's VBlank handler (same moment as GBDK's OAM DMA): SCX/SCY, palettes (fades) and, with the HUD cut on, the window/sprites split at line cut_line. shake_x/y... |
| `scy_shadow` | (ver `scx_shadow`) |
| `bgp_shadow` | (ver `scx_shadow`) |
| `obp_shadow` | (ver `scx_shadow`) |
| `shake_x` |  |
| `shake_y` |  |
| `bgp_below` |  |
| `bgp_below_on` |  |
| `hud_cut` | 1: window visible above cut_line, sprites only below it |
| `video_init` | installs ISRs |
| `set_fade` | 0 = normal palettes .. 3 = white (ui.md 1.2 formula) |
| `set_fade_dark` | 0 = normal .. 3 = black |

## Cabecera (`gbe.h`)

```c
// Register shadows written by the library's VBlank handler (same moment as GBDK's OAM DMA):
// SCX/SCY, palettes (fades) and, with the HUD cut on, the window/sprites split at line cut_line.
// shake_x/y are added to the scroll shadows; bgp_below (when bgp_below_on) is the BG palette
// below the cut line (flash the playfield, not the HUD). SCY_REG is written every VBlank.
extern uint8_t scx_shadow, scy_shadow, bgp_shadow, obp0_shadow, obp1_shadow;
extern int8_t shake_x, shake_y;
extern uint8_t bgp_below, bgp_below_on;
extern uint8_t hud_cut;       // 1: window visible above cut_line, sprites only below it
void video_init(uint8_t cut_line, uint8_t bgp, uint8_t obp0, uint8_t obp1);   // installs ISRs
void set_fade(uint8_t k);     // 0 = normal palettes .. 3 = white (ui.md 1.2 formula)
void set_fade_dark(uint8_t k);  // 0 = normal .. 3 = black
```

## Notas de implementación

`gbe_video.c`:

> gbe: VBlank register shadows, palette fades and the top-HUD window cut (LYC interrupt)
