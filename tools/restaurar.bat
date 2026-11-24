@echo off
rem Restores the parts of tools\ that are not in git (regenerable or too big).
rem   - Emulicious: unzips tools\emulicious\dl\Emulicious-with-Java64.zip into tools\emulicious\app
rem   - SameBoy headless driver: rebuilt by harness\sbrun.py on first use (nothing to do here)
rem Not in git on purpose: tools\flashboy_backup (a dump of a commercial cartridge).
setlocal
cd /d "%~dp0"
if not exist emulicious\app (
  echo Descomprimiendo Emulicious...
  powershell -NoProfile -Command "Expand-Archive -Force 'emulicious\dl\Emulicious-with-Java64.zip' 'emulicious\app'"
) else (
  echo Emulicious ya esta en emulicious\app
)
echo Listo.
endlocal
