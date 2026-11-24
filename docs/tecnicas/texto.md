# Texto

Texto legible en 160x144 con 384 tiles. Fuentes: `harness/common/README.md`, `harness/common/src/gbe_text.c`,
`gbe_vwf.c`, `gbe_vwf_blit.s`, `harness/vwf.py`, juegos `dungeon`, `faro`, `happyvalley`, `mazmorra`, `world_lab`.

---

## TX1 · Texto proporcional (VWF) dibujado en una tira de tiles
<!-- tags: text, vwf, font -->

**Problema** · Con una fuente de 8 px por letra caben 20 caracteres por línea; los diálogos y menús con frases reales no
caben, y la "i" ocupa lo mismo que la "m".

**Cómo lo resolvían** · Fuente de ancho variable: cada glifo tiene su anchura y se dibuja desplazado en bits sobre una
tira de tiles reservada en VRAM; el mapa apunta una vez a esa tira y luego solo cambian los datos de tile. Coste: un
desplazamiento por glifo y fila, más la subida de los tiles tocados.

**En gbe** · `gbe_vwf`: `vwf_font(k, BANK(font), font_tiles, font_vwf)` registra hasta 3 fuentes (0 = mayúsculas y
dígitos, 1 = `font_lower`, 2 = `font_es`); `vwf_clear()`, `vwf_draw(buf, ntiles, x, s)`, `vwf_width(s)`; tiras de hasta 31
tiles. El bucle interno es asm (`gbe_vwf_blit.s`, listarlo junto a `gbe_vwf.c`). Dibujar fuera del VBlank (1-2 letras por
frame en una máquina de escribir) y subir con `gbe_tiles`. Modelo y decodificador de prueba: `harness/vwf.py` (la tira de
la ROM debe ser igual byte a byte a `vwf.render`).

**Medido en nuestros juegos** · ~1,5-2,5k T por glifo en C; con el blit en asm, de ~20k a ~3k T por letra en el peor caso
(commit 1461fa3). Usado en happyvalley, mazmorra y world_lab.

**Estado** · hecho (`gbe_vwf`)

---

## TX2 · Fuente común en tiles y números sin componer cadenas
<!-- tags: text, font, hud -->

**Problema** · Cada juego que dibuja su propio alfabeto gasta tiles y tiempo, y un HUD que reconstruye cadenas cada frame
gasta el VBlank.

**Cómo lo resolvían** · Una fuente 8x8 en un rango fijo de tiles, la etiqueta escrita una vez y solo los dígitos que
cambian copiados cuando cambian.

**En gbe** · Fuentes comunes `harness/common/font.tiles` (dígitos, A-Z, signos; 42 tiles), `font_lower.tiles` (a-z) y
`font_es.tiles` (¡ ¿ , ') con `"common_res"` + `vram_order`; `gbe_text`: `txt_tiles()`, `txt_u16()`, `txt_char()`, escritos
por `gbe_vq`. Puntuaciones: `bcd_add3()` (BCD empaquetado con `daa`). En tests: `GB.tile_text()` lee el texto de pantalla.

**Medido en nuestros juegos** · `bcd_add3` ~100 T frente a ~2000 T en C (tetris).

**Estado** · hecho (`gbe_text`, `bcd`)
