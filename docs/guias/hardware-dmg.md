# Reglas de hardware de la Game Boy DMG

Lo imprescindible para no romper nada en hardware real. Fuente completa: `docs/ref/pandocs/` (registros y tiempos) y
`docs/ref/gbctr.txt` (ciclos exactos); nombres de registros en `docs/ref/hardware-inc.md`; detalle de agente: skill
`gb-hardware`. Lo que PyBoy no ve se comprueba con Mesen (`docs/guias/pruebas.md`).

Detalle completo: skill `gb-hardware`. Lo imprescindible:
- 70224 dots (T-cycles) por frame = **17556 M-cycles** (las tablas de instrucciones van en M-cycles).
  59.73 Hz, 154 líneas (144 visibles + 10 de VBlank), 456 dots por línea.
- VRAM inaccesible solo en modo 3; OAM inaccesible en modos 2 y 3 (usar DMA desde HRAM).
  Con GBDK: escribir tiles/mapas grandes con la pantalla apagada (`DISPLAY_OFF`) o
  repartir en varios frames; `move_sprite` escribe en shadow OAM (seguro en cualquier momento).
- Nunca escribir OAM directamente desde C (bug de corrupción de OAM en DMG).
- Apagar el LCD solo en VBlank (`DISPLAY_OFF` lo hace bien; escribir `LCDC_REG` a pelo no).
- 40 sprites, máx. 10 por línea. Ocultar sprites con Y=0 / Y≥160, **no** con X fuera de pantalla
  (siguen contando para el límite de 10). Sprites 8x8 u 8x16.
- 384 tiles en VRAM. Con LCDC bit4=1 fondo y sprites comparten los 256 de $8000-$8FFF;
  con bit4=0 el fondo usa $8800-$97FF y comparte 128 con los sprites.
- Mapa de fondo 32x32 tiles, pantalla 20x18. Una paleta de fondo, dos de sprites (color 0 transparente).
  OBP0/OBP1 no se inicializan al arrancar: fijarlas siempre. WRAM y SRAM arrancan con basura.
- WRAM 8 KB, HRAM 127 bytes. ROM 32 KB sin MBC; más con MBC5 (preferible a MBC1).
- Saves: habilitar SRAM solo durante el acceso y validar con firma + checksum: `gbe_save.c` ya lo hace;
  los tests apagan y encienden con la SRAM (`ram = gb.power_off(); GB(rom, ram=ram)`).
- Los tests en PyBoy no detectan bugs exclusivos del hardware real ni de timing a mitad de frame.

## Cifras de referencia

| Cosa | Valor | Fuente |
|---|---|---|
| Reloj | 4 194 304 Hz (T); 1 M-ciclo = 4 T | Pan Docs Specifications |
| Frame | 70224 T = 17556 M; 154 líneas × 456 T; 59,73 Hz | Pan Docs Rendering |
| Modos por línea | modo 2 (OAM scan) 80 T, modo 3 (dibujo) 172-289 T, modo 0 (HBlank) el resto hasta 456 | Pan Docs Rendering |
| VBlank | líneas 144-153 = 4560 T; GBDK gasta ~1100 en su ISR | medido (tetris) |
| OAM DMA | 160 M-ciclos (640 T); durante la copia la CPU solo puede leer HRAM | Pan Docs OAM DMA |
| Sprites | 40 en OAM, 10 por línea (el resto de la línea no se dibuja) | Pan Docs OAM |
| VRAM | 6 KB de tiles (384) + 2 mapas de 32×32 | Pan Docs Tile Data / Tile Maps |
| WRAM / HRAM | 8 KB / 127 B | Pan Docs Memory Map |

Origen: sección de `CLAUDE.md` movida aquí el 2026-11-24 (CLAUDE.md enlaza esta guía). Las cifras son medidas en los juegos citados.
