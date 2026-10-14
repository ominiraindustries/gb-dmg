# GDD template (copy to games/<game>/design/gdd.md and fill; write it in Spanish for the user)

```markdown
# <Nombre> — Documento de diseño

Estado: borrador | aprobado (fecha)    Versión: 0.1

## 1. Pitch
- Género:
- Fantasía (en una frase: "eres..."):
- Bucle principal (una frase):
- Qué lo hace distinto:
- Duración de partida objetivo:
- Referencias (juegos de GB que se parecen y qué tomamos de cada uno):

## 2. Mecánicas
Para cada mecánica: descripción, parámetros con números (px, frames, px/frame en 8.8),
casos límite, y cómo se prueba.

| Parámetro | Valor | Unidad | Notas |
|---|---|---|---|

## 3. Controles
| Botón | En juego | En menús |
|---|---|---|

## 4. Pantallas y flujo
Diagrama de estados (texto) y una maqueta `.screen` por pantalla en `design/screens/`.
TITLE -> PLAY -> PAUSE ...

## 5. HUD e interfaz
Qué se muestra, dónde (filas/columnas de la rejilla 20x18), cuándo se actualiza.

## 6. Progresión y dificultad
Tabla de niveles/oleadas con los parámetros que cambian.

## 7. Contenido y assets
| Asset | Tipo (bg/sprite) | Tiles | Frames | Notas |
|---|---|---|---|---|
Totales: tiles de fondo __/128 (+128 compartidos), tiles de sprite __, sprites en pantalla peor caso __/40,
sprites por línea peor caso __/10.

## 8. Sonido
Música (pistas, duración, canales) y efectos (lista, canal, prioridad).

## 9. Técnica
- Cartucho: sin MBC (32 KB) | MBC5 + RAM + batería (guardado)
- Estimación de ROM y RAM
- Riesgos técnicos (scroll, muchos sprites, actualizaciones grandes de VRAM) y cómo se mitigan

## 10. Hitos
- M1 slice jugable: ...
- M2 contenido: ...
- M3 pulido: ...
- M4 prueba en hardware real

## 11. Plan de pruebas
| Qué | Cómo (test automático / bot / playtest humano) |
|---|---|

## 12. Decisiones pendientes (para el usuario)
- [ ] ...
```
