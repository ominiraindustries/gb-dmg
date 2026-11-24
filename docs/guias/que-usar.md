# Qué usar en cada caso

Guía corta orientada a tareas: "quiero X → uso Y → mira cómo lo hace el juego Z". Cada módulo de gbe tiene su página
generada en [`docs/api/<módulo>.md`](../api/README.md) (nombres, comentarios, cabecera y juegos que lo usan); las cifras
vienen de `harness/common/README.md`. Todas las funciones citadas existen en `harness/common/src/gbe.h` (comprobado con
`grep`). Si no aparece en `docs/api/`, **no la inventes**: busca en la API de GBDK (`docs/ref/gbdk/api/`) o escríbela en el
juego y, si un segundo juego la necesita, extráela a gbe (regla de `harness/common/README.md` "Adding to the library").

Un juego activa cada módulo con `"common_src": ["gbe_frame.c", ...]` en `game.json` y define tamaños en
`src/gbe_config.h`. Banco de pruebas de la biblioteca: `games/gbe_lab` (peor caso sintético + autoprueba asm == C).

## Bucle, medición y vídeo

| Necesito | Uso | Lo usa (mirar aquí) | Nota |
|---|---|---|---|
| Bucle de frame, flancos de botones (`pressed`), medir líneas por frame | `gbe_frame`: `frame_begin()`, `frame_vram_check()`, `frame_end()`, `keys/pressed`, `max_frame_lines`, `vram_late` | todos menos tetris/breakout/hello; ejemplo canónico `games/platformer/src/main.c` | `vram_late` debe ser 0 y `max_frame_lines` < 120 en los tests |
| Escribir sprites barato | `gbe_oam`: `oam16()`, `oam8()` (shadow OAM directa) | platformer, shmup, faro | ~3x menos que `set_sprite_tile` + `move_sprite` |
| Scroll, paletas, fundidos y temblor sin pelearme con la ISR | `gbe_video`: `video_init()`, `scx_shadow/scy_shadow/bgp_shadow`, `set_fade()`, `set_fade_dark()`, `shake_x/y` | platformer, shmup, dungeon, faro | el build **para** si un juego con gbe_video escribe `SCX_REG`/`BGP_REG` a pelo |
| HUD arriba con ventana y juego debajo (corte por LYC) | `gbe_video` con `hud_cut = 1` y `video_init(cut_line, ...)`; `bgp_below` para destellar solo el campo | platformer (HUD de 2 filas), shmup | ficha [HR1](../tecnicas/hud-y-raster.md) |
| Parallax o pista curva: cambiar SCX en varias líneas | `gbe_raster`: `raster_line[]/raster_scx[]/raster_n`, `raster_commit()` | ningún juego versionado lo usa todavía | no a la vez que `hud_cut`; ficha [HR4](../tecnicas/hud-y-raster.md) |
| Transición entre pantallas (fundido, construir con LCD apagado, fundido) | `gbe_screen`: `transition(next)`, `transition_update()`, el juego define `screen_build()` | platformer, shmup, dungeon, faro, happyvalley, mazmorra | |
| Pantallas fijas (título, resultados) dibujadas por el ui-designer | maquetas `design/screens/*.screen` → `"screens"` en game.json (`harness/screens.py`) | faro, happyvalley | lo que se diseña es exactamente lo que sale |

## VRAM: copiar a tiempo

| Necesito | Uso | Lo usa | Nota |
|---|---|---|---|
| Encolar escrituras de mapa (texto, HUD, celdas) con presupuesto por VBlank | `gbe_vq`: `vq_push()`, `vq_push_fill()`, `vq_draw_vram()`, `vq_budget` | dungeon, faro, happyvalley, mazmorra, world_lab | ~20 T/tile; filas enteras, nunca columnas de 1 tile |
| Subir datos de tiles (gráficos) desde cualquier banco | `gbe_tiles`: cola de tiles + `tile_copy16` asm, `tiles_budget` | faro, happyvalley, mazmorra, world_lab | 2 tiles por VBlank por defecto |
| Columna de 16 tiles / metatiles 2x2 en cola | `gbe_vram`: `vram_col16`, `vram_mt4_list` | platformer, shmup, dungeon, faro | lo usan gbe_map y gbe_vmap |
| Redibujar media pantalla sin que se vea a medias | `gbe_bgbuf`: doble búfer en los dos mapas de fondo, cambio del bit 3 de LCDC | dungeon | 4 filas = 2,6k T por VBlank |
| Leer gráficos o datos de un banco desde cualquier código | `gbe_bank`: `bank_set_bkg_data()`, `bank_set_sprite_data()`, `bank_memcpy()`, `bank_read8()` + `"banked_res"` | dungeon, faro, gbe_lab, happyvalley, mazmorra | guía [bancos.md](bancos.md) |
| Fila de mapa × 32 sin el fallo de SDCC | `gbe_util`: `gbe_row32(r)` | happyvalley | ver [sdcc-c.md](sdcc-c.md) |

## Mundos, mapas y cámara

| Necesito | Uso | Lo usa | Nota |
|---|---|---|---|
| Plataformas con scroll horizontal (8 filas de metatiles) | `gbe_map`: `map_load()`, `map_follow()`, `map_set()`, `mt_at`/`solid_at` asm, `map_draw_vram()` | platformer | niveles `res/*.lvl` (`harness/levels.py`), física medida con `harness/physics.py` |
| Shmup vertical (anillo de 16 filas) | `gbe_vmap`: `vmap_load()`, `vmap_scroll()`, `vmap_get/set()`, `vmap_draw_vram()` | shmup | `"order": "rows"` en `levels` |
| Mundo con scroll en 4 direcciones (RPG cenital) | `gbe_world`: `world_load()`, `world_update()`, `wmt_at` asm; mapas `res/maps/*.map` (`harness/world.py`) | world_lab, faro, mazmorra | peor frame ~10k T |
| Vista en primera persona (dungeon crawler) | `gbe_view` (+ `res/view.pcs`, `harness/fpview.py`) | dungeon | ~35k T por vista |
| Metatiles como datos | `res/metatiles.mt` (`harness/metatiles.py`) → `mt_tiles[][4]`, `mt_attr[]` | platformer, shmup, world_lab | bit 7 de `mt_attr` = sólido |

## Objetos y sprites

| Necesito | Uso | Lo usa | Nota |
|---|---|---|---|
| Pocos actores con física 8.8 (plataformas) | `gbe_actors`: arrays SoA, `act_spawn()`, `act_move()` asm | platformer | 240 T frente a 1500 en C |
| Muchos objetos (balas, disparos, enemigos de shmup) | `gbe_pool`: `pool_alloc()`, `pool_move()` asm, `hit_first()` asm | shmup, gbe_lab | registros de 16 B; ~250 T mover, ~100 T colisión por objeto |
| Más de 10 sprites en una línea sin que desaparezcan siempre los mismos | `gbe_spr`: `spr_group()` + `spr_rot` (rotación por grupos) | shmup, gbe_lab | ficha [SP2](../tecnicas/sprites.md) |
| Disparar en 32 direcciones / apuntar al jugador | `gbe_aim`: `aim_dir()`, `fire()` asm, `fire_fan()` | shmup | |
| Actores en rejilla (RPG): andar por casillas, comportamientos | `gbe_gact` sobre gbe_world | world_lab, faro, mazmorra | dibujo ~950 T por actor: pendiente de optimizar |
| Comprobar \|d\| < n en 8 bits sin el fallo asimétrico | macro `GBE_WITHIN(d, n)` de `gbe.h` | platformer | |

## Texto, menús, diálogos

| Necesito | Uso | Lo usa | Nota |
|---|---|---|---|
| Texto con la fuente común (mayúsculas, números, minúsculas, ¡¿) | `gbe_text`: `txt_tiles()`, `txt_u16()`, `txt_char()` + `"common_res": ["font", "font_lower", "font_es"]` | dungeon, faro, happyvalley, mazmorra, world_lab | en tests: `GB.tile_text()` |
| Registro de mensajes de 4 líneas | `gbe_log.c` (sección de `gbe_text`): `log_init()`, `log_push()` | dungeon | |
| Texto proporcional (VWF) | `gbe_vwf`: `vwf_font()`, `vwf_draw()`, `vwf_width()` (+ `gbe_vwf_blit.s`; modelo `harness/vwf.py`) | happyvalley, mazmorra, world_lab | ficha [TX1](../tecnicas/texto.md) |
| Menú vertical con cursor y repetición | `gbe_menu`: `menu_open()`, `menu_update()` | dungeon, faro, happyvalley, world_lab | |
| Lista con scroll (inventario, tienda) | `gbe_list` | faro, happyvalley, world_lab | |
| Caja de diálogo con máquina de escribir, sí/no, elección | `gbe_tbox` (en la ventana) | faro, world_lab | |
| Guiones de eventos y diálogos | `gbe_script` + `res/scripts/*.evs` (`harness/script.py`, lint de banderas y longitudes) | faro, world_lab | |
| Banderas de historia y variables | `gbe_flags` (ids de `res/scripts/flags.txt`) | faro, world_lab | |

## Sonido, azar, guardado, datos

| Necesito | Uso | Lo usa | Nota |
|---|---|---|---|
| Efectos de sonido con prioridad por canal | `gbe_sfx`: `sfx(id)` asm, `sfx_table[]` del juego | platformer, shmup, dungeon, faro, happyvalley, mazmorra, world_lab | ficha [AU1](../tecnicas/audio.md); música: aún no hay driver (hUGEDriver documentado en `docs/ref/hugedriver/`) |
| Números aleatorios reproducibles en tests | `gbe_rng`: `rng_next()`, `rng_range()`; `gb.rng_next(state)` lo predice | dungeon, faro, happyvalley, mazmorra, world_lab | |
| Guardar partida en SRAM a prueba de cortes | `gbe_save`: `save_store()`, `save_load()` (o `save_begin/put/end` por trozos) | dungeon, faro, gbe_lab, happyvalley, mazmorra | MBC con RAM+pila; ficha [CA3](../tecnicas/cartucho.md) |
| Puntuación de 6 cifras | `bcd`: `bcd_add3()` (`daa`) | platformer, shmup, tetris | ~100 T frente a ~2000 en C |
| Números de equilibrio (enemigos, objetos, tiendas) | tablas `res/data/*.tbl` (`harness/tables.py`) → `tbl_<nombre>[]` en un banco | faro | los números van ahí, no en C |
| Comprobar que el asm hace lo mismo que su versión C | `gbe_selftest` + `gb.selftest()` en un test | platformer, shmup, dungeon, faro, gbe_lab, mazmorra, world_lab | toda rutina asm de gbe tiene referencia C |

## Pruebas y herramientas

| Necesito | Uso |
|---|---|
| Test de lógica rápido, bots, perfil por función | PyBoy: `python -I harness/gb.py test <juego>` (`harness/gbtest.py`: `gb.hold`, `gb.u8`, `gb.run_bot`, `gb.profile`, `gb.worst_frames`) |
| Confirmar algo de timing (raster, LYC, VBlank) en un emulador exacto | Mesen 2: `python -I harness/gbrun.py <juego> --frames N --input ... --check ...` — guía [pruebas.md](pruebas.md) |
| Ver lo que hay en pantalla de verdad | `gb.vram_errors(escena)`, `gb.mockup_errors()`, `gb.screen_tiles()`; capturas en `build/shots/` |
| Vista previa de tiles, maquetas y niveles sin compilar | `python -I harness/gb.py preview <juego>` → `build/preview/*.png` |
| Saltos, fosos y escalones exactos | `python -I harness/physics.py --game <juego>` |
| Hardware, registros, tiempos | [hardware-dmg.md](hardware-dmg.md) y `docs/ref/pandocs/` |
