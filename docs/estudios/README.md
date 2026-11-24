# Estudios

Estudios con números medidos: de juegos comerciales de Game Boy (cómo lo hacían) y de nuestras propias herramientas.
Alimentan el libro de técnicas (`docs/tecnicas/`): cada estudio aparece como fuente de alguna ficha (lección
study-feeds-book del proyecto SNES).

## Reglas

- **Nunca se descargan ROMs.** Un estudio de un juego comercial usa una ROM que aporte el usuario, fuera del repositorio
  (no se versiona ni se copia a `reference/`).
- Solo números y técnicas con nuestras palabras: nada de código, datos, gráficos ni desensamblado del juego.
- Cada cifra dice cómo se midió (orden exacta de `gbrun`, frames, símbolos o direcciones) para que se pueda repetir.
- Formato: `docs/estudios/<tema>.md`, una sección por pregunta, con la fecha y lo que **no** se pudo medir.

## Cómo medir un juego en Mesen (sin código propio en la ROM)

`harness/gbrun.py` sirve también para ROMs ajenas: sin `.noi` no hay símbolos, pero se leen direcciones y registros.

```sh
# registros de vídeo y la OAM cada frame de un tramo, a CSV
python -I harness/gbrun.py C:/ruta/juego.gb --frames 600 --input "120:start" \
    --watch "bus:0xFF40,bus:0xFF42,bus:0xFF43,bus:0xFF45,bus:0xFF47" --every 1 --dump oam,vram,wram --shot 300,600
```

Lo que no se ve al final del frame (un SCX que cambia a mitad de pantalla, un corte de LYC) no sale en `--watch`:
se deduce de las capturas fila a fila o se añade una sonda Lua (callback de escritura en el registro) a `gbrun.py`.

## Estudios

| Estudio | Qué mide |
|---|---|
| [pyboy-vs-mesen.md](pyboy-vs-mesen.md) | si los dos ejecutores dan los mismos números en un juego real (platformer, 900 frames) |
