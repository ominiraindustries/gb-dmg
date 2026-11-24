# Depurar a mano con Emulicious (y desde VS Code con el código C)

Emulicious es el depurador interactivo del repositorio: puntos de ruptura, paso a paso, visor de VRAM/OAM/tiles,
memoria con los nombres del `.sym` y, con el `.cdb` de SDCC, depuración **en el código C** desde VS Code. No sustituye a
los tests: los tests van en PyBoy y la firma de exactitud en SameBoy ([pruebas.md](pruebas.md)). Emulicious es para
cuando hay que mirar qué pasa dentro.

## Instalación (ya hecha el 2026-11-24)

- Copia en `tools/emulicious/app/` (ignorada por git), descargada de la web oficial (https://emulicious.net/downloads/,
  paquete "Emulicious (with 64-bit Java for Windows)", versión del 2026-03-27, zip SHA-256
  `0a6737b4c709fe54dd88fb507bdf9d491205f240d68e83593e24f8414e0378b5`; el zip original queda en `tools/emulicious/dl/`).
- **Java**: el sistema no tiene Java (`java -version` falla). Este paquete trae su propio Java 8 en
  `tools/emulicious/app/java/` y `Emulicious.exe` lo usa; no hace falta instalar un JDK. Si algún día se quiere el
  `Emulicious.jar` suelto o la extensión de VS Code pide Java del sistema, instalar un JDK es decisión del usuario.
- Licencia: freeware para uso personal y no comercial, sin fuentes (`tools/emulicious/app/License.txt`). Se puede usar
  aquí; no se redistribuye dentro del repositorio.
- Otra ruta: variable `GB_EMULICIOUS` con la ruta de `Emulicious.exe`.

## Abrir un juego

```sh
python -I harness/gb.py debug hello            # compila y abre build/hello.gb; Emulicious carga hello.sym
python -I harness/gb.py debug hello --source   # compila con lcc -debug: además hello.cdb (depuración en C)
```

`gb.py debug` compila como `build` (con `-debug` sólo si se pide `--source`; el código generado no cambia, sólo se
añade información de depuración) y lanza Emulicious separado de la terminal. El `.sym` lo genera ya el build normal
(`-Wm-yS`, formato no$gmb que leen Emulicious y BGB), así que en el desensamblado y en la memoria se ven `_player_x`,
`_update`… Los `static` no aparecen (igual que en los tests).

En Emulicious: menú **Tools → Debugger** (o `F1`). Útiles: *Breakpoints* sobre direcciones o símbolos (`_update`),
*Watchpoints* de escritura sobre una global, *Memory Editor* con salto a símbolo, *Tile Viewer*, *Tilemap Viewer* y
*Sprite Viewer* para ver qué hay en VRAM, y el perfilador (*Tools → Profiler*). Para el modelo: *Emulation → Game Boy →
System = Game Boy* (DMG); si no, puede arrancar como GBC.

## Depurar el código C desde VS Code, paso a paso

1. Instalar VS Code y la extensión **Emulicious Debugger** (`emulicious.emulicious-debugger`,
   https://marketplace.visualstudio.com/items?itemName=emulicious.emulicious-debugger): `Ctrl+Shift+X`, buscar
   "Emulicious Debugger", *Install*.
2. Decirle dónde está Emulicious: `Ctrl+,` → buscar `emulicious` → **Emulicious Debugger: Emulicious Path** =
   `C:\Users\David\Desktop\GBDMG\tools\emulicious\app` (la carpeta; también vale la ruta de `Emulicious.exe`).
3. Abrir la carpeta `C:\Users\David\Desktop\GBDMG` en VS Code (*File → Open Folder*).
4. Compilar con información de depuración: `python -I harness/gb.py build` no basta; usar
   `python -I harness/gb.py debug <juego> --source` una vez (deja `games/<juego>/build/<juego>.cdb` junto al `.gb`) y
   cerrar la ventana de Emulicious que abre, o dejarla para el paso 6 en modo *attach*.
5. Crear `.vscode/launch.json` (VS Code: *Run → Add Configuration… → Emulicious Debugger*), con esta configuración:

   ```json
   {
     "version": "0.2.0",
     "configurations": [
       {
         "type": "emulicious-debugger",
         "request": "launch",
         "name": "Emulicious: hello",
         "program": "${workspaceFolder}/games/hello/build/hello.gb",
         "port": 58870,
         "stopOnEntry": true
       },
       {
         "type": "emulicious-debugger",
         "request": "attach",
         "name": "Emulicious: attach",
         "port": 58870
       }
     ]
   }
   ```

   `.vscode/` no está versionado: es configuración local del usuario. Para otro juego se cambia `program`.
6. `F5`. Con `launch`, la extensión arranca Emulicious con la ROM y para en la entrada. Con `attach`, primero en
   Emulicious *Tools → Remote Debugging → Enabled* (puerto 58870) y luego `F5` en VS Code.
7. Abrir `games/<juego>/src/main.c`, poner un punto de ruptura con clic en el margen (o `F9`) y continuar (`F5`). Paso a
   paso: `F10` (por encima), `F11` (entrar), `Shift+F11` (salir). Las variables locales y globales salen en *Variables*;
   en *Watch* se pueden escribir expresiones (`player_x`, `*(uint8_t*)0xFF44`). El desensamblado está en la paleta de
   comandos (*Emulicious: Open Disassembly*) por si una línea de C oculta lo que hace el SDCC.
8. Si los puntos de ruptura salen grises ("unverified"): el `.cdb` no está o es de otra compilación. Repetir el paso 4
   después de cada cambio de código (el build de los tests no genera `.cdb`).

Limitaciones: Emulicious no es tan exacto como SameBoy en timing fino; un fallo de raster o de VBlank se confirma con
`sbrun`/`gbrun`, no en el depurador. Los agentes no abren Emulicious (abre una ventana): es una herramienta del usuario.
