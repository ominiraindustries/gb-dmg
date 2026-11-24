# Sprites y OAM

Cómo caben muchos objetos en 40 sprites, 10 por línea y una OAM que solo se puede tocar por DMA. Fuentes: Pan Docs
(`docs/ref/pandocs/10_OAM.md`, `11_OAM_DMA_Transfer.md`, `17_Rendering.md`, `68_OAM_Corruption_Bug.md`), CLAUDE.md
"Reglas de hardware DMG", `harness/common/README.md`, juegos `platformer`, `shmup`, `gbe_lab`.

---

## SP1 · El límite de 10 sprites por línea
<!-- tags: sprites, oam, hardware -->

**Problema** · En cada línea el PPU elige como mucho 10 sprites; el resto de esa línea no se dibuja. Un enemigo de
16 px son 2 sprites en modo 8x16: con 5 objetos en la misma horizontal la línea está llena.

**Cómo lo resolvían** · Pan Docs (OAM, "Selection priority"): durante el modo 2 (80 T) el PPU recorre la OAM en orden
y se queda con los 10 primeros cuya Y cubre la línea; **la X no cuenta**: un sprite con X = 0 o X ≥ 168 (fuera de
pantalla por los lados) ocupa igual uno de los 10 huecos. Para que no cuente hay que sacarlo por Y (Y = 0 o Y ≥ 160).
Entre los elegidos, en DMG gana el de menor X y, si empatan, el de menor índice de OAM. Cada sprite de la línea alarga
el modo 3 (de 172 a hasta 289 T), lo que acorta el HBlank siguiente. Los juegos comerciales diseñaban formaciones en
diagonal o en columnas y limitaban los objetos por fila (lección de diseño en `docs/guias/diseno-juegos/05-enemigos-y-jefes.md`).

**En gbe** · Patrón: ocultar con Y = 0 (`oam16`/`oam8` con y = 0, o `hide_sprites_range` de GBDK), nunca con X fuera de
pantalla. Reparto de huecos de OAM por prioridad con `gbe_spr` (ficha SP2). En diseño: presupuesto de objetos por fila
en el GDD (skill `gb-game-design`, `budgets.md`).

**Medido en nuestros juegos** · shmup: pico de 26 objetos (gbe_lab reproduce ese peor caso sintético). Sin contar aún
cuántas líneas superan 10 sprites en una partida real.

**Estado** · patrón

---

## SP2 · Parpadeo controlado: rotar la OAM por grupos
<!-- tags: sprites, flicker, multiplexing -->

**Problema** · Cuando una línea pasa de 10 sprites desaparecen siempre los mismos (los de índice alto), y un objeto
puede quedar invisible durante segundos.

**Cómo lo resolvían** · Rotar el orden en que los objetos entran en la OAM cada frame: el sobrante cambia de frame en
frame y se ve parpadear en vez de desaparecer (técnica clásica de NES/Game Boy). Lo importante (jugador, sus balas) va
en un rango fijo de índices bajos, que nunca rota.

**En gbe** · `gbe_spr`: `spr_group(oam_first, oam_n, pool_first, pool_n, size)` una vez por grupo de prioridad (rango
bajo = más prioridad) y `spr_rot` avanzando 1 por frame, en ciclo de 2 × un múltiplo común de los tamaños de grupo
(< 64; p. ej. 48 para grupos de 12, 6, 8 y 2). En frames consecutivos cada grupo empieza medio grupo más allá, así que un
sprite descartado en una línea llena se dibuja el frame siguiente.

**Medido en nuestros juegos** · shmup: ~300 T por objeto dibujado (`spr_group` asm; contadores de bucle en registros en
vez de WRAM ahorraron ~470 T por objeto). Pico del shmup con grupos de OAM ~13k T por frame.

**Estado** · hecho (`gbe_spr`, shmup y gbe_lab)

---

## SP3 · DMA de OAM desde HRAM
<!-- tags: sprites, oam, dma, hram, vblank -->

**Problema** · La OAM solo es accesible en modos 0 y 1, y en DMG escribir o incluso hacer `inc/dec` de 16 bits con un
puntero en $FE00-$FEFF durante el modo 2 corrompe la OAM (OAM corruption bug).

**Cómo lo resolvían** · Pan Docs (OAM DMA Transfer): escribir la página origen en `$FF46` copia 160 bytes de `$XX00` a la
OAM en **160 M-ciclos (640 T)**; mientras dura, la CPU solo puede leer HRAM, así que la rutina vive en HRAM:
`ldh ($46),a` y un bucle de espera de 40 vueltas de 4 M-ciclos. Todos los juegos mantienen una OAM sombra de 160 B
en WRAM y lanzan la DMA al empezar el VBlank.

**En gbe** · Lo hace GBDK: `shadow_OAM` en `$C000` (ver `.noi`) y la DMA en su ISR de VBlank. El juego **nunca escribe la
OAM real desde C** (CLAUDE.md). Si un juego tuviera su propia ISR, la rutina de DMA debe copiarse a HRAM (127 B).

**Medido en nuestros juegos** · Parte de los ~1100 T de la ISR de VBlank de GBDK (medido en tetris).

**Estado** · hecho (GBDK)

---

## SP4 · Metasprites: un objeto de varias piezas
<!-- tags: sprites, metasprites, oam -->

**Problema** · Un personaje de 16x16 o mayor son varios sprites que hay que mover juntos y voltear juntos (al voltear en
X las piezas cambian de lado).

**Cómo lo resolvían** · Tablas de piezas (dy, dx, tile, atributos) por pose, recorridas al construir la OAM; en modo 8x16
un 16x16 son solo 2 piezas. GBDK genera esas tablas con `png2asset` y las dibuja con `move_metasprite_ex()`,
`move_metasprite_flipx()`, `move_metasprite_flipy()` (`gb/metasprites.h`, que `gb/gb.h` no incluye).

**En gbe** · Para el caso común (16x16 en modo 8x16) `oam16(nb, ox, y, tile, prop)`: 2 sprites con tiles (t, t+2) y
`S_FLIPX` intercambia las mitades. Objetos de más piezas: metasprites de GBDK o un bucle propio sobre `shadow_OAM`.

**Medido en nuestros juegos** · `oam16`: ~3x más barato que `set_sprite_tile`/`set_sprite_prop` + `move_sprite` por pieza
(platformer). `move_metasprite_*` de GBDK: sin medir.

**Estado** · hecho para 16x16 (`gbe_oam`); metasprites grandes: patrón con GBDK

---

## SP5 · Escribir la OAM sombra directamente
<!-- tags: sprites, oam, rendimiento -->

**Problema** · Las funciones de sprite de GBDK hacen una llamada por campo y por sprite; con 20-40 sprites por frame el
coste se nota.

**Cómo lo resolvían** · Escribir los 4 bytes de cada entrada (Y, X, tile, atributos) seguidos en la OAM sombra y vaciar
los huecos sobrantes de una vez (Y = 0 con `memset`).

**En gbe** · `oam16`/`oam8` (`gbe_oam`), y para pools `spr_group` (SP2). Vaciar rangos con `memset(shadow_OAM + 4*n, 0, ...)`.

**Medido en nuestros juegos** · platformer: ~3x menos que `set_sprite_tile/prop + move_sprite`.

**Estado** · hecho (`gbe_oam`)
