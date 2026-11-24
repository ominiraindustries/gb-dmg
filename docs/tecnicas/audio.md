# Audio

Cuatro canales (2 pulsos, onda, ruido) compartidos entre música y efectos. Fuentes: Pan Docs (`docs/ref/pandocs/19_Audio.md`,
`20_Audio_Registers.md`, `21_Audio_details.md`), `harness/common/src/gbe_sfx.c`, `gbe_sfx_asm.s`, hUGEDriver
(`docs/ref/hugedriver/`), skill `gb-hardware` (`audio.md`).

---

## AU1 · Prioridad de efectos de sonido por canal
<!-- tags: audio, sfx, prioridad -->

**Problema** · Con cuatro canales, un efecto frecuente (disparo) no debe cortar uno importante (muerte, objeto), y un
efecto que suena encima de la música debe devolver el canal al acabar.

**Cómo lo resolvían** · Cada efecto tiene canal, prioridad y duración; uno nuevo solo entra si su prioridad es mayor o
igual que la del efecto que suena en ese canal; el canal queda reservado esos frames (la música no lo toca) y luego se
libera. Los efectos se escriben directamente en los registros NRxx (Pan Docs: escribir el bit 7 de NRx4 dispara el canal).

**En gbe** · `gbe_sfx`: el juego define `sfx_table[]` con `{ canal (1, 2 o 4), prio, frames, { NR10..NR14 } }`;
`sound_init()`, `sfx(id)` (asm), `sound_update()` una vez por frame. `sfx_c` documenta la versión C.

**Medido en nuestros juegos** · shmup: ~1000 → ~300 T por efecto con la versión asm. Usado en 7 juegos.

**Estado** · hecho (`gbe_sfx`)

---

## AU2 · Música con un driver de tracker (hUGEDriver)
<!-- tags: audio, music, driver -->

**Problema** · La música necesita un secuenciador (patrones, instrumentos, efectos) que cueste poco por frame y que el
compositor pueda editar con una herramienta, y que conviva con `gbe_sfx`.

**Cómo lo resolvían** · hUGETracker + hUGEDriver (dominio público): el tracker exporta la canción a asm/C, el driver se
llama una vez por frame (`hUGE_dosound()`), y permite silenciar canales para los efectos (`hUGE_mute_channel()`). Tiene
ejemplo para GBDK. Documentación local: `docs/ref/hugedriver/` (README, formato del driver, notas internas, `hUGEDriver.h`).

**En gbe** · Falta: ningún juego tiene música con driver todavía. Para integrarlo: convertir el `.asm` RGBDS del driver a
sdas: el ejemplo de GBDK del repo ensambla el driver con RGBDS y lo pasa a objeto sdas con `tools/rgb2sdas.py`
(RGBDS no está instalado aquí; sin comprobar si las releases de hUGEDriver traen un objeto ya listo para GBDK); coordinar `hUGE_mute_channel` con
la reserva de canales de `gbe_sfx` y medir su coste por frame con `gb.profile`.

**Medido en nuestros juegos** · sin medir.

**Estado** · pendiente (sin tarea en Beads todavía)
