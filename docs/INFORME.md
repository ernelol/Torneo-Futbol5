# Informe – Sistema de Gestión del Torneo Interfacultades de Fútbol 5

**Base de Datos 1 – Universidad Católica del Uruguay – Segundo semestre 2026**
**Autor:** Ernesto Santos

---

## 1. Introducción

La UCU organiza cada semestre el Torneo Interfacultades de Fútbol 5. Hasta ahora la inscripción, el fixture y los resultados se llevaban en planillas de cálculo y grupos de mensajería, lo que producía errores en la tabla de posiciones, partidos superpuestos en una cancha y jugadores suspendidos que igualmente jugaban.

Este trabajo implementa un sistema de información que centraliza equipos, jugadores, partidos, planillas, sanciones y reportes de cada edición, y que **hace cumplir las reglas del torneo automáticamente**.

El repositorio incluye el script SQL (`sql/01_schema.sql` y `sql/02_datos.sql`), la aplicación (`app/`), la dockerización (`Dockerfile`, `docker-compose.yml`) y el instructivo (`README.md`).

## 2. Decisiones de implementación

### 2.1 Tecnologías

| Elemento | Elección | Fundamento |
|---|---|---|
| Backend | Python 3 con Flask | Requisito de la letra. Flask es mínimo y no impone ORM, por lo que el SQL queda visible en el código |
| Acceso a datos | `mysql-connector-python` con SQL escrito a mano | La letra prohíbe ORM. Todas las consultas son parametrizadas |
| Base de datos | MySQL 8.0 | Requisito de la letra. Soporta `CHECK` (desde 8.0.16), claves foráneas compuestas y vistas |
| Frontend | HTML renderizado en el servidor (Jinja) + un CSS | Libre elección. Se evitó JavaScript complejo para mantener el sistema simple y centrar el trabajo en la base de datos |
| Despliegue | Docker Compose (servicios `db` y `app`) | Se valora en la letra. Un solo comando levanta todo y carga los datos |

### 2.2 Arquitectura

Una aplicación de tres capas en pocos archivos:

- **Rutas** (`app.py`): reciben el formulario, validan, llaman a las reglas y muestran el resultado.
- **Reglas de negocio** (`reglas.py`): las reglas del torneo que dependen de otras filas.
- **Acceso a datos** (`db.py`): conexión, consultas, transacciones y traducción de errores de MySQL a mensajes legibles.

Los reportes están separados en `reportes.py` (una consulta SQL por reporte).

### 2.3 Validación en todas las capas

| Capa | Mecanismo | Ejemplos |
|---|---|---|
| Front-end | Atributos HTML (`required`, `maxlength`, `pattern`, `min`, `max`, `type=email`, `type=date`) | Cédula de 6 a 8 dígitos; minuto entre 1 y 60 |
| Back-end | `validaciones.py` y `reglas.py` | Formato de email, fecha de nacimiento no futura, máximo 2 docentes/funcionarios por plantel |
| Base de datos | `PRIMARY KEY`, `FOREIGN KEY`, `UNIQUE`, `CHECK`, `ENUM`, `NOT NULL` | `CHECK (id_equipo_local <> id_equipo_visitante)`, `UNIQUE (dia, id_turno, cancha)` |

Los errores que detecta la base (clave repetida, restricción violada, permiso denegado) se capturan en `db.mensaje_error` y se muestran con un mensaje claro.

### 2.4 Seguridad a nivel de base de datos

Se crearon tres usuarios de MySQL con privilegios mínimos, y la aplicación elige uno según el rol de quien inició sesión:

- `auth_db`: solo lee la tabla `login`.
- `admin_db`: operaciones de datos (`SELECT/INSERT/UPDATE/DELETE`) sobre las tablas del torneo, sin permisos estructurales (`DROP`, `ALTER`) ni acceso a `login`.
- `planillero_db`: lectura de datos de referencia; escritura de planilla, goles, tarjetas y sanciones; de `partido` únicamente la columna `estado`.

Además: contraseñas almacenadas como hash SHA-256; consultas parametrizadas contra SQL injection; control de acceso por rol en cada ruta.

### 2.5 Reglas del torneo

La mayoría de las reglas se aplican **dos veces** (en Python y en la base) para que no puedan violarse aunque se escriba directamente en la base. La relación completa de reglas y dónde se cumple cada una está en `docs/GUIA_DEFENSA.md`, sección 6. Las decisiones más relevantes:

1. **Resultado calculado, no almacenado.** El resultado de un partido se obtiene contando goles en la vista `v_resultado_partido`; un autogol se acredita al rival (`v_goles_acreditados`). Evita inconsistencias entre goles y resultado y simplifica la corrección dentro de las 48 horas.
2. **Claves foráneas compuestas.** `gol` y `tarjeta` referencian a `planilla_partido`, y `planilla_partido` referencia al plantel del equipo; así la base garantiza que solo convierte goles o recibe tarjetas un jugador que figura en la planilla con su equipo.
3. **Sanciones automáticas dentro de la misma transacción.** Al registrar o borrar una tarjeta se recalculan las sanciones automáticas del jugador (1 fecha por roja, 1 fecha por cada 3 amarillas), con inicio en la fecha siguiente al partido. Si algo falla, se deshace todo (`ROLLBACK`).
4. **Control de tiempo.** La planilla solo puede cargarse cuando el turno del partido ya terminó; un partido jugado solo puede corregirse durante las 48 horas posteriores. La hora se toma en la zona horaria de Uruguay.
5. **Etapas del torneo.** Los planteles solo se modifican en *inscripción*; los partidos solo se programan y juegan con el torneo *en curso*; para iniciar el torneo se exigen al menos 2 equipos con 5 jugadores y capitán.

### 2.6 Reportes

Se implementaron los 9 reportes pedidos y 3 consultas propias:

| N° | Reporte |
|---|---|
| 1 | Tabla de posiciones |
| 2 | Tabla de goleadores (top 10) |
| 3 | Fair play por equipo |
| 4 | Promedio de goles por partido (por fecha y total) |
| 5 | Canchas y turnos más utilizados (solo partidos jugados) |
| 6 | Jugadores por facultad y tipo |
| 7 | Inscriptos que nunca figuraron en una planilla |
| 8 | Sanciones por equipo y motivo |
| 9 | Porcentaje de partidos jugados vs. postergados/cancelados |
| 10 | *(propia)* Fixture con resultados: todos los partidos por fecha con horario, cancha y resultado |
| 11 | *(propia)* Mayores goleadas: los 5 partidos con mayor diferencia de goles |
| 12 | *(propia)* Jugadores con más tarjetas |

Se eligieron las tres consultas propias porque cubren necesidades concretas de la organización: ver el calendario completo, destacar partidos llamativos para comunicación, y detectar jugadores problemáticos para decisiones disciplinarias.

### 2.7 Pruebas realizadas

Se probó el sistema de punta a punta contra una base MariaDB 10.11 configurada con el modo SQL estricto de MySQL 8 (`ONLY_FULL_GROUP_BY`, `STRICT_TRANS_TABLES`): login y permisos por rol, ABMs, rechazo de cada regla de programación de partidos, planilla con jugador suspendido, goles y autogoles, generación y borrado de sanciones automáticas, regla de 48 horas, y que el planillero no pueda borrar jugadores ni leer `login` a nivel de base de datos. La tabla de posiciones se verificó contra un cálculo independiente hecho en Python a partir de los datos de prueba; los demás reportes se revisaron manualmente contra esos mismos datos. Además, el sistema se levantó con `docker compose up --build` sobre MySQL 8.0 y los scripts `sql/` se ejecutaron sin errores.

## 3. Modelo de datos

Se implementaron todas las estructuras pedidas (`login`, `facultad`, `jugador`, `torneo`, `equipo`, `equipo_jugador_torneo`, `complejo`, `cancha`, `turno`, `partido`, `planilla_partido`, `gol`, `tarjeta`, `sancion_jugador`).

### 3.1 Cambios y agregados al modelo propuesto

| Cambio | Motivo |
|---|---|
| `sancion_jugador.id_tarjeta` (nullable, único, `ON DELETE CASCADE`) | Vincular la sanción automática con la tarjeta que la originó y distinguirla de las disciplinarias (NULL) |
| `equipo.ci_capitan` admite `NULL` | Un equipo nace sin plantel; el capitán se designa entre los jugadores una vez cargados. La aplicación lo exige al iniciar el torneo |
| `UNIQUE (id_equipo, id_torneo)` en `equipo` | Permite claves foráneas compuestas que garantizan consistencia de edición |
| `UNIQUE (ci_jugador, id_torneo)` en el plantel | Un jugador no integra dos equipos en la misma edición |
| `UNIQUE (dia, id_turno, nombre_cancha, id_complejo)` en `partido` | Una cancha no tiene dos partidos el mismo día y turno |
| `UNIQUE` en `facultad.nombre`, `jugador.email`, `torneo (anio, semestre)`, `equipo (id_torneo, nombre)`, `complejo.nombre` | Evitar duplicados |
| Restricción `CHECK` en `turno` | Garantiza que los turnos sean de una hora entre las 18:00 y las 23:00, como pide la letra |
| Vistas `v_goles_acreditados` y `v_resultado_partido` | Calcular el resultado desde los goles |
| Valores de `ENUM` sin tildes ni espacios | Evitar problemas de codificación y simplificar el código |

### 3.2 Mejoras consideradas y no implementadas

- **Triggers / procedimientos almacenados** para las sanciones automáticas y la validación de planteles: harían cumplir las reglas aún si se escribe directamente en la base; se descartaron por no haber sido vistos en el curso y para mantener la lógica en un solo lugar legible.
- **Liberar la cancha de un partido cancelado**: requeriría una columna generada o un índice parcial; hoy se libera editando o eliminando el partido.
- **Tabla de fechas del torneo** (`fecha_torneo`) con día y estado propio, en lugar de `numero_fecha` dentro de `partido`.
- **Hash de contraseñas con sal** (bcrypt/argon2) y protección CSRF en formularios.
- **Auditoría** (quién y cuándo modificó un resultado), útil para la regla de corrección en 48 horas.
- **Generador automático de fixture** (algoritmo de round-robin).
- **Paginación** en las listas largas.

## 4. Bitácora del trabajo realizado

> Completar con las fechas y horas reales de trabajo.

| Fecha | Actividad | Resultado |
|---|---|---|
| __/__ | Lectura de la letra y repaso del material del curso (SQL, JOIN, Seguridad, Transaccionalidad y ACID) | Lista de requisitos y reglas |
| __/__ | Diseño del modelo de datos y decisiones (claves compuestas, vistas, `id_tarjeta`) | Diagrama y tablas definidas |
| __/__ | Script `01_schema.sql`: tablas, restricciones, vistas, usuarios y permisos | Esquema creado sin errores |
| __/__ | Script `02_datos.sql`: datos de prueba que cumplen todas las reglas | 6 equipos, 3 fechas jugadas, más partidos programados, postergado y cancelado |
| __/__ | Aplicación Flask: login, roles y ABMs | Facultades, jugadores, complejos/canchas, torneos, equipos/planteles, sanciones |
| __/__ | Partidos con validaciones; planilla, goles, tarjetas y sanciones automáticas | Reglas de programación y de planilla funcionando |
| __/__ | Reportes (9 pedidos + 3 propios) | Consultas verificadas contra cálculo independiente |
| __/__ | Dockerización e instructivo | `docker compose up --build` |
| __/__ | Pruebas de punta a punta y correcciones | Todas las pruebas pasan |
| __/__ | Informe y preparación de la defensa | Este documento y `GUIA_DEFENSA.md` |

## 5. Bibliografía

- Material del curso Base de Datos 1 (UCU, 2026): presentaciones de Modelo Relacional, SQL, Tipos de JOIN, Seguridad y Transaccionalidad y ACID; práctico y ejercicios de clase.
- Codd, E. F. (1970). *A Relational Model of Data for Large Shared Data Banks*. Communications of the ACM, 13(6), 377–387.
- Oracle. *MySQL 8.0 Reference Manual*. https://dev.mysql.com/doc/refman/8.0/en/
- Oracle. *MySQL Connector/Python Developer Guide*. https://dev.mysql.com/doc/connector-python/en/
- Pallets Projects. *Flask Documentation*. https://flask.palletsprojects.com/
- Pallets Projects. *Jinja Documentation*. https://jinja.palletsprojects.com/
- Docker Inc. *Docker Compose documentation*. https://docs.docker.com/compose/
- OWASP. *SQL Injection Prevention Cheat Sheet*. https://cheatsheetseries.owasp.org/
- Silberschatz, A., Korth, H. F. y Sudarshan, S. *Fundamentos de Bases de Datos* (McGraw-Hill).
