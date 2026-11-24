@echo off
rem Graba un juego en la Flash Boy (lector Tengu "GBX", GBX Driver 2.8-ARM).
rem Uso: grabar.bat <juego>      (p. ej. grabar.bat platformer)
rem Compila el juego, copia la ruta de la ROM al portapapeles y abre GBX Driver.
rem En GBX Driver: Info -> mira "Volt" y pon el interruptor del aparato en esa tension ->
rem Write Flash -> pega la ruta (Ctrl+V) en el dialogo de abrir.
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Uso: grabar.bat ^<juego^>
  dir /b games
  pause
  exit /b 1
)
set "GAME=%~1"
python harness\gb.py build %GAME%
if errorlevel 1 (
  echo Fallo al compilar %GAME%.
  pause
  exit /b 1
)
set "ROM=%~dp0games\%GAME%\build\%GAME%.gb"
if not exist "%ROM%" (
  echo No encuentro %ROM%
  pause
  exit /b 1
)
set "DRV=%~dp0tools\flashboy_sw\epsp401\GBX DRIVER 2.8-ARM.exe"
if not exist "%DRV%" (
  echo No encuentro GBX Driver en tools\flashboy_sw\epsp401\
  pause
  exit /b 1
)
echo|set /p="%ROM%"| clip
echo ROM: %ROM%
echo (ruta copiada al portapapeles)
start "" "%DRV%"
start "" explorer /select,"%ROM%"
endlocal
