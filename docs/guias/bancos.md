# Bancos de ROM y SRAM

Cómo crece un juego por encima de 32 KB con GBDK y gbe. Hardware de los MBC: `docs/ref/pandocs/48_MBCs.md` y siguientes;
manual de GBDK: `docs/ref/gbdk/manual/05_banking_mbcs.md`; detalle de agente: skill `gbdk` (`banking.md`). Patrones:
[cartucho.md](../tecnicas/cartucho.md).

- `"banked_res": ["walls", "level1", "screen_title"]` en game.json mete esos assets generados en bancos
  conmutables (`#pragma bank 255` + `BANKREF(<stem>)`); con flags MBC5 + `-autobank`
  (`["-autobank", "-Wm-yt0x1B", "-Wm-yo8", "-Wm-ya1"]`). Se leen con `gbe_bank.c`
  (`bank_set_bkg_data(BANK(walls), ...)`, `bank_memcpy`), que vive en el banco 0. Probado en games/gbe_lab.
- El build **para** si un fichero con `#pragma bank N` llama a `SWITCH_ROM` (se desmapearía a sí mismo),
  y si con bancos algo del banco 0 (código, `_HOME`, `_GSINIT`...) pasa de 0x4000
  (SWITCH_ROM lo desmapearía), y **avisa** de las builds planas que lo pasan sin bancos
  (platformer y shmup hoy: funcionan mientras no se conmute). Código grande: funciones `BANKED`.
  Detalle: skill `gbdk` `banking.md`.

## Gotchas de flags (de la sección "Gotchas de GBDK")
- Banking: `-autobank` exige `-Wm-yt<tipo>`; sin `-Wm-ya<N>` la cabecera dice "sin RAM".
  Receta 64 KB MBC1 + save: `["-autobank", "-Wm-yt0x03", "-Wm-yo4", "-Wm-ya1"]`.
  Receta MBC5 + RAM + pila: `["-autobank", "-Wm-yt0x1B", "-Wm-yo8", "-Wm-ya1"]` (MBC5 preferible a MBC1).
- Guardados: `gbe_save` (dos ranuras alternas, firma escrita la última); en PyBoy se prueba apagando y encendiendo
  con la SRAM (`ram = gb.power_off(); GB(rom, ram=ram)`), en Mesen con `gbrun.py --sram-out` / `--sram-in`.

Origen: sección de `CLAUDE.md` movida aquí el 2026-11-24 (CLAUDE.md enlaza esta guía). Las cifras son medidas en los juegos citados.
