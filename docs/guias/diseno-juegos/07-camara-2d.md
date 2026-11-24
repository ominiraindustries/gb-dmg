# 7. Cámara en juegos de desplazamiento lateral

Fuente principal: Itay Keren, "Scroll Back: The Theory and Practice of Cameras in Side-Scrollers" (GDC 2015, artículo en
Game Developer), https://www.gamedeveloper.com/design/scroll-back-the-theory-and-practice-of-cameras-in-side-scrollers

## Los tres objetivos

- **Atención:** mostrar lo que importa (personaje, peligro próximo, meta).
- **Interacción:** que la cámara refleje lo que el jugador hace y quiere hacer.
- **Comodidad:** nada de movimientos bruscos o imprevisibles; el desajuste entre lo que se ve y lo que siente el cuerpo
  marea incluso en 2D.

## Técnicas (de más simple a más elaborada)

| Técnica | Qué hace | Ejemplos | Cuándo |
|---|---|---|---|
| Bloqueo de posición | La cámara sigue al personaje centrado | Kung-Fu Master, Terraria | personajes pequeños, saltos cortos |
| Tope en los bordes | Se para en los límites del nivel | casi todos | siempre |
| Ventana de cámara | No se mueve mientras el personaje está dentro de un rectángulo | Rastan, Streets of Rage | evita temblores; ve poco por delante |
| Ajuste a plataforma | En vertical no sigue el salto; se recoloca al aterrizar | Super Mario World, Rayman | **la vertical por defecto en plataformas** |
| Zona de aceleración | Al salir de la ventana acelera para alcanzarle | Super Mario Bros., Metroid | movimientos rápidos |
| Suavizado lerp | Cubre un porcentaje de la distancia cada fotograma | Donkey Kong Country | suave; se queda atrás con personajes muy rápidos |
| Suavizado físico | La cámara acelera y frena como un objeto | Pac-Land | ease-in-out |
| Foco adelantado | Coloca más pantalla en la dirección de marcha | Pac-Land, Defender (~25 %) | ver lo que viene |
| Foco adelantado doble | Dos anclas, cambia de lado sólo al cruzar un umbral | Super Mario World, Cave Story | evita bailes al girarse un instante |
| Foco por regiones | Cada zona fija su comportamiento | Donkey Kong Country | salas de puzle, jefes |
| Atractores | Objetos que tiran de la cámara hacia sí | Insanely Twisted Shadow Planet | jefes, puntos de interés |
| Mirar arriba/abajo | El jugador desplaza la vista manteniendo una dirección | Spelunky (agacharse / mirar arriba) | ver bajo un borde antes de bajar |
| Sacudida | Pérdida de control a propósito para dar impacto | desde Mario Bros. (1983) | impactos, con moderación |

## Reglas

**7.1 Vertical: ajuste a plataforma; horizontal: foco adelantado doble con umbral.** Es la combinación de Super Mario
World y la más segura para un plataformas de exploración. *Por qué:* seguir cada salto en vertical marea y no aporta
información; ver por delante en horizontal sí la aporta.

**7.2 Si el jugador cae, la cámara debe adelantarse.** En caídas largas o pozos verticales, desactiva el ajuste a
plataforma y sigue (o adelanta) la caída para que se vea dónde se va a aterrizar.

**7.3 Deja mirar.** Un control para mirar abajo/arriba (como Spelunky) o un encuadre por regiones que muestre el fondo
de un pozo evita los saltos de fe.

**7.4 El jefe y las salas especiales fijan la cámara.** Una arena con cámara fija o encuadrada por región hace legible
el patrón del jefe.

**7.5 La cámara es parte del nivel.** Mide los huecos y las alturas con lo que la cámara muestra realmente, no con el
mapa completo del editor.

## Adaptación Game Boy (DMG)

- La pantalla son 160×144 (10×9 teselas de 16 px). Con foco adelantado, el personaje queda a ~1/3 del borde de atrás;
  en vertical hay muy poco sitio: un HUD de 2 filas de teselas deja 128 px de juego.
- El desplazamiento es por píxel con SCX/SCY; cada columna o fila de teselas que entra se copia en el VBlank (~3400 T
  libres por frame con GBDK). Usa gbe_map / gbe_vmap / gbe_world (`docs/guias/que-usar.md`) antes de escribir uno propio.
- Sacudidas: `shake_x/y` de gbe_video, un desfase de 1-2 px durante pocos fotogramas basta en una pantalla tan pequeña.

## Antipatrones

- Cámara centrada en vertical que sube y baja en cada salto.
- Cámara que se queda atrás en carreras (lerp lento con personaje rápido).
- Cambiar de lado el foco adelantado con cada pulsación corta a izquierda/derecha.
- Peligros que aparecen en el borde de pantalla cuando ya no hay tiempo de reaccionar.
