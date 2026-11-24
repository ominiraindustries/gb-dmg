# Estructura del repositorio y formatos de recursos

Movido sin cambios desde CLAUDE.md el 2026-11-24 (CLAUDE.md conserva el mapa mínimo y enlaza aquí).

- `harness/` — herramientas comunes a todos los juegos (no meter código de un juego aquí)
  - `gb.py` — CLI: `setup`, `new`, `build`, `run`, `test`
  - `gbtest.py` — driver headless (PyBoy) para tests: botones, frames, leer variables, capturas
  - `templates/<tipo>/` — plantillas de `gb.py new <juego> [tipo]` (hoy: `basic`, sobre gbe)
- `games/<juego>/` — `src/` (.c/.s), `res/` (assets), `tests/` (pytest), `game.json` (título, flags de lcc)
  - `res/*.tiles`: tiles en arte ASCII 8x8 (`.` `-` `+` `#` = colores 0-3, `@ NOMBRE` etiqueta el
    siguiente tile). Se convierten al compilar a `build/gen/<nombre>.c/.h` (`#include "bg.h"`).
  - Assets compartidos en `harness/common/*.tiles` (p. ej. la fuente): `"common_res": ["font"]` en game.json.
    Texto en mayúscula y minúscula: `font_lower` (a..z) + `txt_lower`; en tests `GB.tile_text(tiles, font, lower)`.
  - Pantallas fijas (título, resultados...): las maquetas `design/screens/<nombre>.screen` del
    ui-designer se convierten al compilar en mapas de tiles (`screen_<nombre>_map[360]` + sprites) con
    `"screens": [...]` y `"vram_order": ["bg", "font", "ui"]` (bases de VRAM; `["a", "b"]` = dos tilesets
    que se turnan en el mismo hueco) en game.json. El build genera `vram.h` (`VRAM_<TILESET>`) y
    `@ base auto` en `metatiles.mt`/`view.pcs`: nada de bases escritas a mano
    (`harness/screens.py`). Lo que diseña el agente es exactamente lo que sale en el juego.
  - **Librería de motor `gbe`** (`harness/common/src/gbe*.c/.s`, ver `harness/common/README.md`):
    bucle de frame y medición, OAM directo, fundidos/transiciones, HUD con corte LYC, actores con
    `act_move` asm, mapa con scroll y consultas asm, SFX con prioridad, autoprueba asm-vs-C
    (`gb.selftest()`). Juegos nuevos parten de ella en vez de reescribirla.
  - Código compartido en `harness/common/src/` (p. ej. `bcd.s` + `bcd.h`, suma BCD con `daa`):
    `"common_src": ["bcd.s"]` en game.json; sus headers están en el include path.
  - `res/*.lvl`: niveles en ASCII (rejilla + `@ clave valor`), convertidos a `build/gen/<nivel>.c/.h`
    (mapa por columnas + lista de objetos). Qué significa cada carácter va en game.json `"levels"`
    con nombres simbólicos que define el C del juego (formato al principio de `harness/levels.py`;
    `levels.parse()` sirve para tests de lint en Python puro). Niveles verticales (shmup):
    `"order": "rows"` + capa de objetos al lado de la rejilla (games/shmup/res/stage1.lvl).
  - `res/maps/*.map`: mundos con scroll en 4 direcciones (sectores de 16x16 casillas, `harness/world.py`)
    para `gbe_world`; banco de pruebas `games/world_lab` (pantalla == modelo en cada frame).
  - `res/data/*.tbl`: tablas de datos (columnas con tipo: texto, enum, flags, ref a otra tabla) →
    `tbl_<nombre>[]` en un banco + ids `<PREFIJO>_<ID>` para guiones y mapas (`harness/tables.py`, con
    cargador Python para tests y bots). Los números de equilibrio van ahí, no en C.
  - `res/scripts/*.evs`: guiones y diálogos (`harness/script.py`: texto partido en líneas/páginas al compilar,
    lint de banderas/etiquetas/longitudes) para `gbe_script` + `gbe_tbox`.
  - `res/metatiles.mt`: tabla de metatiles como datos (nombre, 4 tiles, atributos) → `build/gen/metatiles.c/.h`
    (`harness/metatiles.py`); la usan el ROM, la vista previa del nivel y los tests en Python.
- `tools/gbdk/` — SDK, no versionado (`python harness/gb.py setup`)
