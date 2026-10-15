# Estudio de caballos (`horse_study.png`, animado en `horse_study.gif`)

Tres tamaños del mismo caballo con jinete, mismo galope de 8 frames (Muybridge, mano izquierda:
pisan mano trasera derecha, trasera izquierda, delantera derecha, delantera izquierda, y luego la fase en el aire con
las patas recogidas). F0 es la pose estirada de tu referencia. El cuello sube y baja (abajo cuando apoyan las manos),
la cola ondea en 2 posiciones y el jinete se queda casi quieto (1 px) mientras el caballo se mueve debajo.

Estilo: caballo castaño (capa gris oscuro, crin, cola y cascos negros, contorno negro), patas de 2 px (la del
lado cercano en capa con borde negro, la del lado lejano en negro y más fina, para dar profundidad), cabeza en
cuña con ojo y oreja, chaquetilla y mantilla claras y gorra oscura. Los mismos tiles con OBP1 dan tu caballo: capa
gris claro, chaquetilla oscura.

| tamaño | sprites 8x16 por caballo | tiles de sprite (8 frames, únicos) | sprites por línea | caballos lado a lado | caballos en pantalla (OAM 40) | cámara |
|---|---|---|---|---|---|---|
| 16x16 | 2 | 32 | 2 | 5 | 20 | cabe el campo entero (12-14) con calles de 8 px |
| 24x16 | 3 | 44 (48 sin repetidos) | 3 | 3 | 13 | grupo de cabeza de 7-8 (≤ 3 caballos en dos calles vecinas) + mini-óvalo |
| 32x24 | 7 (4 abajo + 3 arriba, mitad de arriba vacía) | 76 (112 sin repetidos) | 4 | 2 | 5 | plano corto de 4-5 caballos; el resto solo en el mini-óvalo |

32x24 en modo 8x16: filas 8-23 = 4 sprites; filas 0-7 (jinete y cabeza) = 3 sprites más, colocados 8 px más arriba
con la mitad superior vacía (esa mitad invisible también cuenta para el límite de 10 por línea). Un caballo ocupa 32 líneas
de sprites: en la recta de 48 px solo caben unos 2 niveles de caballos sin pasar de 10 por línea.

Recomendación: **24x16 para la carrera** (tiene la silueta estirada de la referencia, cuesta 44 tiles, entran 7-8 caballos
y el resto va al mini-óvalo) y **32x24 para los planos cortos** (últimos 200 m, foto finish, paddock, título), donde
2-4 caballos bastan. El 16x16 es el único que enseña el campo entero, pero a ese tamaño el caballo vuelve a parecerse
al del concepto (en la fase aérea parece un pájaro).
