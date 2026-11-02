# Guía para entender y defender el obligatorio

Está escrita para que puedas explicar cada pieza con tus palabras. Leela en orden una vez, y después usá las secciones 8 (preguntas) y 9 (demo) como repaso.

---

## 1. La idea general en 30 segundos

> "Es una aplicación web en Flask que se conecta a MySQL con SQL escrito a mano. Las reglas del torneo se controlan en tres capas: el formulario HTML, Python y la base de datos. La base de datos además restringe qué puede hacer cada rol con usuarios de MySQL distintos. El resultado de un partido no se guarda: se calcula desde los goles con una vista."

Recorrido de un pedido, por ejemplo "registrar una tarjeta":

```
Navegador (formulario HTML, valida required/min/max)
   → app.py (ruta: lee el formulario, llama a validaciones.py)
   → reglas.py (reglas del torneo: ¿se puede? ¿está en planilla?)
   → db.py (ejecuta el INSERT con el usuario de MySQL del rol)
   → MySQL (PK, FK, CHECK, UNIQUE: última barrera)
   → mensaje "Tarjeta registrada" o el error en pantalla
```

## 2. Qué hace cada archivo

| Archivo | Qué hace | Cómo explicarlo |
|---|---|---|
| `sql/01_schema.sql` | Crea tablas, restricciones, 2 vistas y los usuarios de MySQL | "Acá vive el modelo y la seguridad de la base" |
| `sql/02_datos.sql` | Datos de prueba que cumplen todas las reglas | "Alcanza para que los 12 reportes devuelvan datos" |
| `app/db.py` | Conexión, `consultar`, `ejecutar`, `transaccion` | "Toda la comunicación con MySQL pasa por acá" |
| `app/validaciones.py` | Funciones que validan un campo (cédula, email, entero…) | "Segunda capa de validación de campos" |
| `app/reglas.py` | Reglas del torneo (plantel, partidos, planilla, sanciones) | "Las reglas que dependen de otras filas" |
| `app/reportes.py` | Los 12 SQL de reportes | "Cada reporte es una consulta con JOIN y GROUP BY" |
| `app/app.py` | Las rutas: qué pasa al entrar a cada pantalla | "Conecta todo: valida, aplica reglas, guarda y avisa" |
| `app/templates/` | Las pantallas HTML (Jinja) | "Generan el HTML con los datos" |

## 3. Las tres capas de validación (ejemplo: la cédula del jugador)

| Capa | Dónde | Qué hace con la cédula |
|---|---|---|
| 1. Front-end | `form.html` (atributo `pattern="\d{6,8}"`, `required`) | El navegador no deja enviar si no son 6 a 8 dígitos |
| 2. Back-end | `validaciones.ci()` | Repite el control en Python (porque alguien puede saltarse el HTML) |
| 3. Base de datos | `CHECK (ci BETWEEN 100000 AND 99999999)` y `PRIMARY KEY` | Aunque falle todo lo anterior, la base no acepta el dato |

Por qué las tres: el front-end es comodidad, el back-end es seguridad real, la base de datos es la garantía final (también protege si otro programa escribe en la base).

## 4. Seguridad en la base de datos

Hay **tres usuarios de MySQL** (los crea `01_schema.sql` con `CREATE USER` y `GRANT`, tema "Seguridad" del curso):

- `auth_db`: solo `SELECT` en `login`. Se usa únicamente para verificar el correo y la contraseña.
- `admin_db`: `SELECT/INSERT/UPDATE/DELETE` en las tablas del torneo. No puede `DROP` ni `ALTER`, ni leer `login`.
- `planillero_db`: lee datos de referencia; escribe `planilla_partido`, `gol`, `tarjeta`, `sancion_jugador`; de `partido` solo puede hacer `UPDATE (estado)`.

La aplicación elige el usuario en `db.get_db()` según `session["rol"]`. Entonces, aunque hubiera un error en Python, un planillero **no puede** borrar jugadores: MySQL le responde "permiso denegado" (lo probé).

Otras medidas:
- Las contraseñas de la aplicación se guardan como hash SHA-256, no en claro.
- Todas las consultas usan parámetros (`%s`), nunca se concatenan textos: eso evita **SQL injection**.
- Cada pantalla de gestión está protegida con el decorador `@solo_admin`.

**Punto débil que conviene decir vos primero:** el planillero tiene `INSERT/DELETE` sobre `sancion_jugador` porque las sanciones automáticas se generan al registrar tarjetas. La alternativa más estricta sería un procedimiento almacenado o un trigger (no se vieron en el curso).

## 5. El modelo de datos: decisiones clave

Se respetaron las tablas del enunciado y se agregó solo lo necesario:

1. **Claves foráneas compuestas** (lo más importante para defender):
   - `planilla_partido (id_equipo, ci_jugador)` → `equipo_jugador_torneo`: un jugador solo puede figurar en una planilla con el equipo al que pertenece.
   - `gol` y `tarjeta (id_partido, ci_jugador)` → `planilla_partido`: **solo convierte goles o recibe tarjetas quien figura en la planilla**. Es una regla del enunciado resuelta sin código.
   - `partido (id_equipo_local, id_torneo)` → `equipo (id_equipo, id_torneo)`: ambos equipos son de la misma edición que el partido.
2. **Claves únicas que implementan reglas:**
   - `UNIQUE (ci_jugador, id_torneo)` en el plantel: un jugador no integra dos equipos en la misma edición.
   - `UNIQUE (dia, id_turno, nombre_cancha, id_complejo)` en `partido`: una cancha no tiene dos partidos el mismo día y turno.
   - `UNIQUE (id_equipo, numero_camiseta)`: camisetas no repetidas.
3. **El resultado no se guarda**: la vista `v_resultado_partido` lo calcula contando goles. Así nunca puede quedar inconsistente con los goles (si corrigen un gol, el resultado cambia solo). Un autogol se acredita al equipo rival (vista `v_goles_acreditados`).
4. **Campo agregado `sancion_jugador.id_tarjeta`**: guarda qué tarjeta originó una sanción automática. Vale `NULL` para las disciplinarias. Permite distinguir automáticas de manuales.
5. **`equipo.ci_capitan` puede ser NULL** al crear el equipo (todavía no tiene jugadores). La app exige capitán para poder iniciar el torneo, y el capitán se elige solo entre los jugadores del plantel.
6. **Estados en `ENUM`** sin tildes ni espacios (`inscripcion`, `en_curso`, `acumulacion_amarillas`) para evitar problemas de codificación.

## 6. Dónde se cumple cada regla del enunciado

| Regla | Dónde |
|---|---|
| Plantel de 5 a 10 jugadores | Máximo 10: `reglas.agregar_a_plantel`. Mínimo 5: `reglas.iniciar_torneo` y `reglas.validar_partido` |
| Máximo 2 docentes/funcionarios por plantel | `reglas.agregar_a_plantel` |
| Jugadores de la facultad del equipo | `reglas.agregar_a_plantel` |
| Un jugador en un solo equipo por edición | `reglas.agregar_a_plantel` **y** `UNIQUE` en la base |
| Planteles solo se modifican en inscripción | `reglas.exigir_inscripcion` |
| Capitán es uno de sus jugadores | `reglas.designar_capitan` |
| Ambos equipos de la misma edición | `reglas.validar_partido` **y** FK compuesta |
| Equipo no juega contra sí mismo | `reglas.validar_partido` **y** `CHECK` |
| No repetir rival (salvo cancelado) | `reglas.validar_partido` (ignora partidos cancelados) |
| Un partido por fecha por equipo | `reglas.validar_partido` |
| Cancha libre en ese día y turno | `reglas.validar_partido` **y** `UNIQUE` |
| Solo jugadores del plantel en la planilla | FK compuesta **y** `reglas.guardar_planilla` |
| Suspendidos no pueden figurar | `reglas.guardar_planilla` (usa `esta_suspendido`) |
| Goles/tarjetas solo de la planilla | FK compuesta **y** `reglas.exigir_en_planilla` |
| Resultado desde los goles | Vista `v_resultado_partido` |
| Marcar jugado solo si el turno ya pasó | `reglas.cerrar_partido` → `motivo_no_modificable` |
| Partido jugado no se elimina | `reglas.eliminar_partido` |
| Corrección dentro de 48 horas | `reglas.motivo_no_modificable` |
| 3 / 1 / 0 puntos y desempate | Reporte "Tabla de posiciones" (`ORDER BY Puntos, DG, GF`) |
| Roja o 3 amarillas = 1 fecha de suspensión | `reglas.recalcular_sanciones` |
| Sanciones disciplinarias de varias fechas | ABM de sanciones (`cantidad_fechas`) |
| Dos tipos de usuario | `@solo_admin` + usuarios de MySQL distintos |

## 7. Conceptos que te van a preguntar

### Transacciones (tema ACID)
`db.transaccion()` envuelve cada operación: si todo sale bien hace `COMMIT`, si algo falla hace `ROLLBACK`. Ejemplo: al registrar una tarjeta se hace el `INSERT` de la tarjeta **y** se recalculan las sanciones. Si falla el segundo paso, la tarjeta tampoco queda guardada: **Atomicidad**. Las restricciones (FK, CHECK) garantizan **Consistencia**. Cada pedido tiene su propia conexión (**Aislamiento**). Un `COMMIT` en InnoDB es **Durable**.

### Cómo se generan las sanciones automáticas (`recalcular_sanciones`)
1. Borra las sanciones automáticas del jugador en esa edición (las que tienen `id_tarjeta`).
2. Recorre todas sus tarjetas en orden cronológico.
3. Cada roja genera 1 fecha; cada 3ª amarilla (3, 6, 9…) genera 1 fecha.
4. La suspensión empieza en la **fecha siguiente** a la del partido de la tarjeta.

Se recalcula todo (en vez de solo agregar) para que quede bien si se corrige o borra una tarjeta en las 48 horas. Las disciplinarias no se tocan. Un jugador está suspendido en la fecha *F* si `F BETWEEN inicio AND inicio + cantidad - 1`.

### La tabla de posiciones (reporte más importante)
Cada partido jugado se "desdobla" en dos filas (una por equipo, con goles a favor y en contra) con `UNION ALL`. Después se hace `LEFT JOIN` desde `equipo` (así aparecen equipos sin partidos jugados), `GROUP BY` equipo, y se suman: partidos, ganados (`gf > gc`), empatados, perdidos, goles y puntos (`CASE WHEN gf>gc THEN 3 WHEN gf=gc THEN 1 ELSE 0 END`). Orden: puntos, diferencia de goles, goles a favor.

### Regla de las 48 horas
`motivo_no_modificable` calcula el fin del partido (`dia` + `hora_fin` del turno). Antes de ese momento no se puede cargar planilla; si el partido está jugado y pasaron más de 48 horas, tampoco se puede corregir.

## 8. Preguntas probables y respuestas cortas

**¿Por qué Flask y no Django u otro?** Es el más simple: sin ORM obligatorio, el SQL se escribe a mano y se ve claramente qué hace cada consulta, que es lo que pide la letra.

**¿Por qué sin ORM?** Lo prohíbe la letra, y además así se controla el SQL (JOIN, GROUP BY, transacciones) que es lo que se vio en el curso.

**¿Por qué validar en tres capas?** Cada una protege contra algo distinto: el HTML mejora la experiencia, Python evita que alguien salte el formulario, y la base garantiza integridad aunque entre otro programa.

**¿Cómo evitás SQL injection?** Con consultas parametrizadas: los datos van separados de la sentencia (`%s`), el driver los escapa. Nunca se arma SQL concatenando texto.

**¿Cómo se protege la base por roles?** Con tres usuarios de MySQL y `GRANT` mínimos. El planillero no puede modificar jugadores ni equipos aunque llegara a ejecutar SQL.

**¿Por qué las contraseñas están con SHA-256 y no bcrypt?** Para mantenerlo simple con lo visto en el curso (`SHA2()` de MySQL). En un sistema real usaría bcrypt o argon2 con sal.

**¿Por qué el resultado no es una columna?** Porque sería un dato derivado: podría contradecir a los goles. Con la vista, es siempre correcto.

**¿Para qué sirven las claves foráneas compuestas?** Para que la base haga cumplir reglas del enunciado (por ejemplo, que solo marque goles quien está en la planilla) sin depender del código.

**¿Por qué las sanciones se hacen en Python y no con trigger?** Los triggers no se vieron en el curso, y en Python quedan dentro de la misma transacción, son más fáciles de leer y de probar. La alternativa sería un trigger `AFTER INSERT` sobre `tarjeta`.

**¿Qué pasa si se borra una tarjeta?** Se borra también su sanción (`ON DELETE CASCADE` sobre `id_tarjeta`) y se recalculan las demás sanciones automáticas del jugador.

**¿Se puede cancelar un partido y volver a programar a esos equipos?** Sí: la regla de no repetir rival ignora los partidos cancelados (como pide la letra). Un cancelado no cuenta para "un partido por fecha".

**¿Por qué una cancha cancelada sigue ocupada?** Porque `UNIQUE (dia, turno, cancha)` cuenta cualquier partido. Para liberarla se edita el partido cancelado (otro día/cancha) o se elimina. Es una limitación conocida (ver sección 10).

**¿Qué hace el `LEFT JOIN` en los reportes?** Mantiene a los equipos/facultades aunque no tengan filas relacionadas (por ejemplo, un equipo sin partidos jugados igual aparece con ceros).

**¿Cómo se levanta el sistema?** `docker compose up --build`; MySQL ejecuta solo los scripts de `sql/` y la aplicación queda en el puerto 5000.

**¿Qué mejorarías con más tiempo?** Ver sección 10.

## 9. Guion de demo (unos 8 minutos)

1. **Login**: entrar como `admin@ucu.edu.uy`. Mostrar que un mal usuario da error.
2. **Torneos**: está en curso con 6 equipos. Mostrar los estados (inscripción → en curso → finalizado).
3. **Reportes**: abrir la tabla de posiciones (Empresariales FC, Humanas Club e Ingeniería United tienen 7 puntos; se ordenan por diferencia de goles y, si empatan, por goles a favor) y goleadores (Natalia Mendoza lidera con 4).
4. **Validaciones**: en *Jugadores → Nuevo*, escribir una cédula de 3 dígitos (frena el navegador); quitar el atributo desde el inspector y enviar (frena Python); mostrar el `CHECK` en `01_schema.sql` (frena la base).
5. **Reglas de partidos**: en *Partidos → Nuevo*, intentar repetir un cruce o usar una cancha ocupada y mostrar el mensaje.
6. **Planilla con suspendido**: entrar a la **Planilla** del partido Humanas Club vs Empresariales FC (27/10): Gonzalo Márquez aparece bloqueado ("suspendido en esta fecha").
7. **Tarjeta automática**: cargar planilla (5 jugadores por equipo), un gol, y una **tarjeta roja**. Ir a *Sanciones*: apareció la sanción automática para la fecha siguiente. Borrar la tarjeta: la sanción desaparece.
8. **Marcar como jugado**: el resultado sale de los goles. Intentar corregirlo: dice que pasaron más de 48 horas.
9. **Regla de 48 horas (en vivo)**: *Editar* el partido 13 (Ingeniería United vs Empresariales FC) y ponerle como día **ayer**; abrir su planilla, cargarla y marcarla como jugada: ahora sí se puede corregir.
10. **Roles**: cerrar sesión y entrar como `planillero@ucu.edu.uy`: solo ve Partidos y planillas. Mostrar en `01_schema.sql` los `GRANT` de `planillero_db`.

## 10. Limitaciones (decilas vos antes de que pregunten)

- Un partido cancelado o postergado sigue reservando su cancha y turno (por el `UNIQUE`).
- Contraseñas con SHA-256 sin sal (en producción: bcrypt/argon2).
- Sin protección CSRF en los formularios ni paginación en las listas.
- El planillero necesita `INSERT/DELETE` sobre `sancion_jugador` por las sanciones automáticas.
- Si una persona tiene dos amarillas en un mismo partido, no se convierte en roja (la letra no lo pide).
- La planilla exige al menos un jugador por equipo para marcar el partido como jugado (decisión propia: no se pide 5 porque un equipo podría quedar sin 5 disponibles por suspensiones).
- No hay un ABM de usuarios de la aplicación: los usuarios iniciales se cargan en `02_datos.sql`.

## 11. Antes de entregar

- Completá las fechas reales y el detalle de tu trabajo en la **bitácora** de `docs/INFORME.md`.
- Revisá la política de la UCU sobre el uso de herramientas de IA y declaralo en el informe si corresponde.
- Subí el código a un repositorio **público** de GitHub (se valora).
- Probá `docker compose down -v && docker compose up --build` desde cero una vez antes de la entrega.
- Leé una vez `app/reglas.py` completo: es donde está la lógica que más te van a preguntar.
