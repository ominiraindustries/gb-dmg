# Cartucho: bancos y guardado

Crecer por encima de 32 KB y guardar partidas. Fuentes: Pan Docs (`docs/ref/pandocs/47_The_Cartridge_Header.md`,
`48_MBCs.md`, `50_MBC1.md`, `52_MBC3.md`, `53_MBC5.md`), manual de GBDK (`docs/ref/gbdk/manual/05_banking_mbcs.md`),
`docs/guias/bancos.md`, juegos `gbe_lab`, `faro`, `dungeon`.

---

## CA1 · Patrones de cambio de banco
<!-- tags: banks, mbc, rom -->

**Problema** · El código y los datos que no caben en los 16 KB del banco 0 viven en bancos conmutables que comparten la
ventana $4000-$7FFF: código de un banco no puede cambiar de banco por debajo de sí mismo.

**Cómo lo resolvían** · Pan Docs: el MBC cambia el banco de $4000-$7FFF escribiendo en $2000-$3FFF (MBC1: 5 bits + 2 altos
en $4000; MBC5: 8 bits + bit 9 en $3000, banco 0 seleccionable). Patrones: (1) todo lo que se llama desde cualquier sitio
y las ISR en el banco 0; (2) llamadas entre bancos por un trampolín en el banco 0 que guarda el banco actual, cambia,
llama y restaura; (3) datos grandes en bancos, leídos desde el banco 0 o copiados a WRAM.

**En gbe** · GBDK: `#pragma bank 255` + `-autobank` coloca ficheros; funciones `BANKED` usan el trampolín de GBDK;
`SWITCH_ROM(n)` a mano solo desde el banco 0. El build **para** si un fichero con `#pragma bank N` llama a `SWITCH_ROM` o si
algo del banco 0 pasa de $4000 con bancos. `GBE_BANKED` manda los módulos fríos de gbe (tbox, menu, save, parte C de gact)
a bancos conmutables. Flags: MBC5 + RAM + pila `["-autobank", "-Wm-yt0x1B", "-Wm-yo8", "-Wm-ya1"]`.

**Medido en nuestros juegos** · faro: el banco 0 se llenaba con el motor → `GBE_BANKED`; world_lab: `GBE_SELFTEST_BANKED`
bajó el banco 0 del 93 % al 81 %. Una llamada BANKED a una tabla en banco ~500 T: lo que se lee cada frame se copia a WRAM.

**Estado** · hecho (build + `GBE_BANKED`)

---

## CA2 · Leer datos de un banco desde cualquier código
<!-- tags: banks, data, tiles -->

**Problema** · Cargar un tileset o un nivel que está en otro banco desde código que también puede estar en un banco.

**Cómo lo resolvían** · Una rutina en el banco 0 que recibe (banco, puntero), cambia, copia y restaura el banco previo.

**En gbe** · `gbe_bank` (en el banco 0): `bank_set_bkg_data()`, `bank_set_sprite_data()`, `bank_memcpy()`, `bank_read8()`;
los recursos van a bancos con `"banked_res": [...]` en game.json (`BANKREF(<stem>)`, `BANK(<stem>)`). Datos de tiles por
VBlank desde cualquier banco: `gbe_tiles`.

**Medido en nuestros juegos** · gbe_lab: 3 tilesets en bancos cargados y comprobados byte a byte. `bank_memcpy` de 128 B
~4,2k T (copias con banco ~30 T/byte).

**Estado** · hecho (`gbe_bank`)

---

## CA3 · Guardado en SRAM con MBC
<!-- tags: sram, save, mbc, battery -->

**Problema** · La SRAM del cartucho arranca con basura, se corrompe si se apaga a mitad de escritura y debe estar
deshabilitada cuando no se usa (protege los datos al quitar el cartucho).

**Cómo lo resolvían** · Pan Docs (MBC1/3/5): habilitar con `$0A` en $0000-$1FFF, escribir en $A000-$BFFF, deshabilitar con
`$00`. Los juegos guardaban dos copias con firma y suma de control y escribían la firma al final.

**En gbe** · `gbe_save`: dos ranuras alternas con firma, versión, secuencia, longitud y Fletcher-16; la firma se escribe la
última, así que un guardado cortado deja intacto el anterior. `save_store()` / `save_load()` o por trozos
`save_begin()` / `save_put()` / `save_end()` y `save_open()` / `save_get()`. Cartucho con RAM y pila
(`-Wm-yt0x1B -Wm-ya1`, o MBC1 `-Wm-yt0x03`).

**Medido en nuestros juegos** · gbe_lab: apagado y encendido, un bit cambiado y la ranura nueva cortada a medias
(`GB(rom, ram=g.power_off())`). En Mesen: `gbrun.py --sram-out f.sav` y `--sram-in f.sav`.

**Estado** · hecho (`gbe_save`)
