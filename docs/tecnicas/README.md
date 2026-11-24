# Libro de técnicas de la Game Boy DMG

Cómo se resuelve cada problema típico de la DMG, con cifras, y qué pieza del repositorio lo hace. Cada ficha dice si es
**función** de gbe, **patrón** a seguir o algo **pendiente**. Formato (para `kb.py`, `docs/harness/kb.md`): capítulos con
fichas `## ID · título` separadas por `---`, con los campos **Problema** · **Cómo lo resolvían** · **En gbe** ·
**Medido en nuestros juegos** · **Estado**.

Fuentes generales: Pan Docs y GB CTR (`docs/ref/`), lo medido en nuestros juegos (`docs/guias/rendimiento-vram.md`,
`harness/common/README.md`) y la API de gbe (`docs/api/`). Regla legal: solo técnicas y números con nuestras palabras;
nada de código, datos ni gráficos de juegos comerciales. Los estudios de juegos comerciales irán a `docs/estudios/`.

## Capítulos

| Capítulo | Fichas | De qué va |
|---|---|---|
| [Sprites y OAM](sprites.md) | 5 | 10 por línea, parpadeo por rotación, DMA de OAM en HRAM, metasprites, OAM sombra directa |
| [HUD, ventana y raster](hud-y-raster.md) | 4 | corte LYC/STAT, ventana como HUD, fundidos con BGP, paralaje por SCX |
| [VBlank y copias a VRAM](vblank.md) | 4 | presupuesto del VBlank, colas, copiar fuera del VBlank, guardia `vram_late` |
| [Cartucho: bancos y guardado](cartucho.md) | 3 | patrones de banco, datos en banco, SRAM con MBC |
| [Texto](texto.md) | 2 | VWF, fuente común y números |
| [Audio](audio.md) | 2 | prioridad de SFX por canal, música con hUGEDriver |
| [CPU y muchos objetos](cpu.md) | 4 | registros frente a SoA, colisiones en 8 bits relativas a cámara, repartir entre frames, listas de activos |

## Todas las fichas

| ID | Título | Capítulo | Estado | Fuentes |
|---|---|---|---|---|
| SP1 | El límite de 10 sprites por línea | [Sprites y OAM](sprites.md) | patrón | Pan Docs OAM, Pan Docs Rendering, shmup, gbe_lab |
| SP2 | Parpadeo controlado: rotar la OAM por grupos | [Sprites y OAM](sprites.md) | hecho | gbe_spr, shmup, gbe_lab |
| SP3 | DMA de OAM desde HRAM | [Sprites y OAM](sprites.md) | hecho | Pan Docs OAM DMA Transfer, Pan Docs OAM Corruption Bug, GBDK |
| SP4 | Metasprites: un objeto de varias piezas | [Sprites y OAM](sprites.md) | hecho | gbe_oam, GBDK gb/metasprites.h, platformer |
| SP5 | Escribir la OAM sombra directamente | [Sprites y OAM](sprites.md) | hecho | gbe_oam, platformer |
| HR1 | Corte LYC/STAT a mitad de frame para el HUD | [HUD, ventana y raster](hud-y-raster.md) | hecho | Pan Docs STAT, Pan Docs Interrupt Sources, gbe_video, platformer, shmup |
| HR2 | La ventana como HUD | [HUD, ventana y raster](hud-y-raster.md) | hecho | Pan Docs Window, gbe_video, gbe_tbox, faro |
| HR3 | Fundidos con las paletas (BGP/OBP0/OBP1) | [HUD, ventana y raster](hud-y-raster.md) | hecho | Pan Docs Palettes, gbe_video, gbe_screen |
| HR4 | Paralaje y curvas cambiando SCX por líneas | [HUD, ventana y raster](hud-y-raster.md) | hecho | Pan Docs Scrolling, gbe_raster |
| VB1 | El presupuesto del VBlank con GBDK | [VBlank y copias a VRAM](vblank.md) | patrón | Pan Docs Rendering, tetris, rendimiento-vram.md |
| VB2 | Preparar fuera del VBlank, copiar dentro con colas | [VBlank y copias a VRAM](vblank.md) | hecho | gbe_vq, gbe_tiles, faro, world_lab |
| VB3 | Copiar tiles fuera del VBlank | [VBlank y copias a VRAM](vblank.md) | hecho | Pan Docs Accessing VRAM and OAM, gbe_bgbuf, gbe_screen, dungeon |
| VB4 | Guardia: las copias que se salen del VBlank se cuentan | [VBlank y copias a VRAM](vblank.md) | hecho | gbe_frame, world_lab, faro |
| CA1 | Patrones de cambio de banco | [Cartucho: bancos y guardado](cartucho.md) | hecho | Pan Docs MBCs, manual GBDK, bancos.md, faro, world_lab |
| CA2 | Leer datos de un banco desde cualquier código | [Cartucho: bancos y guardado](cartucho.md) | hecho | gbe_bank, gbe_lab |
| CA3 | Guardado en SRAM con MBC | [Cartucho: bancos y guardado](cartucho.md) | hecho | Pan Docs MBC1/MBC5, gbe_save, gbe_lab |
| TX1 | Texto proporcional (VWF) dibujado en una tira de tiles | [Texto](texto.md) | hecho | gbe_vwf, harness/vwf.py, happyvalley |
| TX2 | Fuente común en tiles y números sin componer cadenas | [Texto](texto.md) | hecho | gbe_text, bcd, tetris |
| AU1 | Prioridad de efectos de sonido por canal | [Audio](audio.md) | hecho | Pan Docs Audio, gbe_sfx, shmup |
| AU2 | Música con un driver de tracker (hUGEDriver) | [Audio](audio.md) | pendiente | hUGEDriver, Pan Docs Audio |
| CP1 | Registros recorridos con un puntero (mejor que arrays por campo) | [CPU y muchos objetos](cpu.md) | hecho | gbe_pool, shmup, gbe_lab |
| CP2 | Colisiones y dibujo en 8 bits relativos a la cámara | [CPU y muchos objetos](cpu.md) | hecho | GBE_WITHIN, gbe_actors, platformer |
| CP3 | Repartir el trabajo entre frames | [CPU y muchos objetos](cpu.md) | patrón | shmup, platformer, gbe_gact |
| CP4 | Listas compactas de lo activo y comprobar que lo creado se crea | [CPU y muchos objetos](cpu.md) | patrón | faro |
