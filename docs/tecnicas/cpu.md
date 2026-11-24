# CPU y muchos objetos

Cómo caben muchos objetos en 70224 T por frame con SDCC y el SM83. Fuentes: `docs/guias/rendimiento-vram.md`,
`docs/guias/sdcc-c.md`, `harness/common/README.md` ("Conventions baked into the asm"), juegos `platformer`, `shmup`,
`faro`, `gbe_lab`.

---

## CP1 · Registros recorridos con un puntero (mejor que arrays por campo)
<!-- tags: cpu, sm83, pool, asm -->

**Problema** · En C, `arr[i]` con `i` variable recalcula una dirección de 16 bits en cada acceso; un objeto con 10 campos
paga 10 cálculos.

**Cómo lo resolvían** · En el SM83 (sin modos de direccionamiento indexados baratos) gana un registro contiguo por objeto
recorrido con `ld a,(hl+)`: una sola dirección por objeto y los campos en orden de uso.

**En gbe** · `gbe_pool`: registros de 16 B (`pool_obj_t`, desplazamientos fijos en `gbe_pool.s`) con `pool_move`,
`hit_first` en asm. `gbe_actors` (SoA) queda para pocos actores con física 8.8 (`act_move` asm).

**Medido en nuestros juegos** · Pico del shmup (update / draw): C 53,7k / 52k T; asm sobre SoA 32,7k / 19,5k; asm sobre
registros **26,4k / 13,5k**. Contadores de bucle en registros y no en WRAM: ~470 T menos por objeto en `spr_group`.

**Estado** · hecho (`gbe_pool`)

---

## CP2 · Colisiones y dibujo en 8 bits relativos a la cámara
<!-- tags: cpu, colisiones, camara -->

**Problema** · Con el mundo en coordenadas de 16 bits cada resta y comparación entre objetos es aritmética de 16 bits en
C (cara en SDCC).

**Cómo lo resolvían** · Una vez por frame calcular la x de cada objeto relativa a la cámara en 8 bits
(`x - camera_x + 32`; los objetos solo existen cerca de la pantalla) y hacer todas las colisiones y el dibujo en 8 bits.
Solape simétrico |d| < N con `(uint8_t)(d + N - 1) < 2N - 1`.

**En gbe** · Macro `GBE_WITHIN(d, n)` de `gbe.h`; convención de `gbe_actors` (objetos entre cámara − 32 y cámara + 200);
`gbe_pool` ya trabaja en coordenadas de OAM de 8 bits.

**Medido en nuestros juegos** · platformer: 5 enemigos pasaron de ~150 a ~100 líneas por frame. La versión obvia
`(d + N) < 2N` era asimétrica: los enemigos chocaban por un lado y no por el otro.

**Estado** · hecho (patrón + `GBE_WITHIN`)

---

## CP3 · Repartir el trabajo entre frames
<!-- tags: cpu, presupuesto, frames-alternos -->

**Problema** · El peor frame no es una función cara sino varias medianas que coinciden (shmup: 4 costes a la vez).

**Cómo lo resolvían** · Física de enemigos lentos a medio ritmo (la mitad cada frame, paso doble), colisiones disparo-
enemigo de cada disparo cada 2 frames (la mitad de los disparos en cada uno), el jugador contra balas cada frame, como
mucho 1 aparición por frame y un pensador por frame en la IA.

**En gbe** · Patrón; `gbe_gact` piensa un actor por frame. Diagnóstico: `gb.worst_frames(funcs, frames, step)` desglosa
el peor frame; `gb.profile()` por función.

**Medido en nuestros juegos** · shmup: todas las colisiones en un frame daban un pico de 12k T; repartidas, ~10k por
frame. Disparos de 5 px/f contra cajas de 14 px no atraviesan. Platformer: spawn de 4 trozos desenrollado 8900 → 5300 T.

**Estado** · patrón

---

## CP4 · Listas compactas de lo activo y comprobar que lo creado se crea
<!-- tags: cpu, listas, depuracion -->

**Problema** · Un bucle de SDCC sobre todos los huecos cuesta aunque estén vacíos, y un objeto que aparece y desaparece en
bucle come líneas sin que se vea nada.

**Cómo lo resolvían** · Mantener una lista compacta de los índices vivos y recorrer solo esa; contar altas y bajas.

**En gbe** · Patrón (faro: `cr_ids`). Contadores en el juego leídos por los tests.

**Medido en nuestros juegos** · faro (16 actores): 150-300 T por vuelta aunque el hueco esté vacío; un objeto que nacía más
lejos que su distancia de borrado y dos especies robándose un hueco de sprites costaban 25 líneas invisibles.

**Estado** · patrón
