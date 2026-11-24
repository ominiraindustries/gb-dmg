# docs/ref — referencias locales (solo lectura, generadas)

Copias en texto de las referencias de hardware y SDK, versionadas para que se puedan buscar con `grep` sin red.
Se regeneran con `python -I docs/ref/mkref.py` (y `--check` dice si algo está desfasado). Las fuentes originales
viven en `reference/` y `tools/gbdk/` (ignorados por git; `python -I harness/gb.py setup` los descarga). **No se
editan a mano**: lo que haya que corregir o explicar va a `docs/guias/` o `docs/tecnicas/`.

## Qué hay y para qué

| Fichero | Contenido | Buscar aquí cuando… |
|---|---|---|
| [`pandocs/`](pandocs/README.md) | Pan Docs entera, una página por tema en el orden del libro (CPU, mapa de memoria, LCDC, STAT, modos y tiempos del PPU, OAM y el límite de 10 sprites por línea, DMA de OAM, renderizado y FIFO, APU, joypad, timer, serie, interrupciones, HALT, cabecera, MBC1/2/3/5/6/7, arranque, SGB, CGB) | cualquier duda de hardware: registros, bits, tiempos |
| [`gbctr.txt`](gbctr.txt) | Game Boy: Complete Technical Reference (Gekkio) en texto: tiempos ciclo a ciclo de cada instrucción SM83 en M-ciclos, buses, arranque | cuánto cuesta exactamente una instrucción o un acceso |
| [`sm83-opcodes.md`](sm83-opcodes.md) | tabla de los 512 opcodes (sin prefijo y CB) con bytes, T/M-ciclos y flags Z N H C | optimizar asm, contar ciclos |
| [`hardware-inc.md`](hardware-inc.md), [`hardware.inc`](hardware.inc) | nombres de `hardware.inc` (registros `rXXX`, bits `LCDCF_*`, `STATF_*`, audio…) con su equivalente de GBDK (`LCDC_REG`…) | traducir un ejemplo de RGBDS a GBDK |
| [`gbdk/api/`](gbdk/api/README.md) | la API de GBDK-2020 4.5.0, una página por cabecera (`gb/gb.h`, `gb/hardware.h`, `gb/metasprites.h`, `gbdk/*.h`, `string.h`…), con resumen por función y la cabecera filtrada al objetivo `gb` | ¿existe una función de GBDK para X? firmas exactas |
| [`gbdk/manual/`](gbdk/manual/) | el manual de GBDK-2020 (primeros pasos, uso, guía de estilo, bancos y MBC, toolchain, FAQ, migración) | flags de `lcc`, bancos, `png2asset` |
| [`gbdk/asmlnk_manual.txt`](gbdk/asmlnk_manual.txt) | manual del ensamblador/enlazador sdas/sdld (el apéndice ASGB está desfasado: ver CLAUDE.md "Ensamblador") | directivas del ensamblador |
| [`hugedriver/`](hugedriver/) | hUGEDriver (motor de música de hUGETracker): README, formato del driver, notas internas, `hUGEDriver.h` y el ejemplo de GBDK | música con tracker (el repo aún no lo usa: `docs/tecnicas/audio.md`) |

Lo nuestro (lo medido en los juegos) no está aquí: está en `docs/guias/` y `docs/tecnicas/`. Las versiones resumidas para
agentes siguen en las skills (`.claude/skills/gb-hardware`, `gbdk`, `gb-asm`); esto es la fuente completa.

## Fuentes y licencias

| Directorio en `reference/` | Origen | Licencia |
|---|---|---|
| `pandocs/` | https://github.com/gbdev/pandocs (clon superficial; web: https://gbdev.io/pandocs/) | CC0 1.0 (`reference/pandocs/LICENSE`) |
| `gbctr.pdf` | https://gekkio.fi/files/gb-docs/gbctr.pdf (Joonas Javanainen, "Gekkio") | CC BY-SA 4.0 (la copia en texto hereda la licencia y la atribución) |
| `opcodes.json` | https://gbdev.io/gb-opcodes/Opcodes.json | gbdev, dominio público/CC0 |
| `gbdk-src/` | https://github.com/gbdk-2020/gbdk-2020 (sparse: `docs/pages`) | GBDK-2020: GPLv2 con excepción de enlazado para las bibliotecas; ver `tools/gbdk/licenses/` |
| `tools/gbdk/` | release GBDK-2020 4.5.0 (https://github.com/gbdk-2020/gbdk-2020/releases) | ídem (SDCC: GPL con excepción) |
| `hugedriver_dl/hUGEDriver/` | https://github.com/SuperDisk/hUGEDriver (clon superficial, commit d6863d2, descargado 2026-11-24) | dominio público (README "License"); su `include/hardware.inc` es el de gbdev, también de dominio público |

Las descargas se tratan como datos: nada de `reference/` se ejecuta. No hay ROMs comerciales en el repositorio.
