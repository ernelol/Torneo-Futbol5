# Torneo Interfacultades de Fútbol 5 – UCU

Sistema para gestionar el torneo: equipos y planteles, fixture, planillas (goles y tarjetas), sanciones y reportes.
Obligatorio de Base de Datos 1 – Segundo semestre 2026.

**Stack:** Python 3 + Flask (HTML renderizado en el servidor) · MySQL 8 · `mysql-connector-python` con SQL escrito a mano (sin ORM) · Docker Compose.

## Estructura

```
sql/01_schema.sql      Tablas, restricciones, vistas y usuarios de MySQL con permisos
sql/02_datos.sql       Datos maestros y de prueba (6 equipos, 3 fechas jugadas, etc.)
app/app.py             Rutas (pantallas) de la aplicación
app/reglas.py          Reglas de negocio del torneo
app/reportes.py        Las consultas SQL de los 12 reportes
app/db.py              Conexión a MySQL, transacciones, manejo de errores
app/validaciones.py    Validación de campos en el back-end
app/templates/         Pantallas HTML
docker-compose.yml     Servicios: db (MySQL) y app (Flask)
docs/INFORME.md        Informe del trabajo
```

## Cómo correrlo con Docker (recomendado)

Requisitos: Docker Desktop (o Docker Engine + plugin Compose).

```bash
docker compose up --build
```

La primera vez MySQL ejecuta solo `sql/01_schema.sql` y `sql/02_datos.sql`. Cuando termine de levantar, abrí:

**http://localhost:5000**

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | `admin@ucu.edu.uy` | `admin123` |
| Planillero | `planillero@ucu.edu.uy` | `planillero123` |

Comandos útiles:

```bash
docker compose down        # apaga (conserva los datos)
docker compose down -v     # apaga y BORRA los datos: la próxima vez se vuelve a cargar todo desde cero
docker compose logs app    # ver los errores de la aplicación
```

> Los scripts de `sql/` solo se ejecutan cuando el volumen de datos está vacío. Si modificás un `.sql`, corré `docker compose down -v` y levantá de nuevo.

MySQL también queda accesible desde tu máquina en el puerto **3307** (usuario `root`, contraseña `root_pass_2026`) por si querés mirar las tablas con Workbench o DBeaver.

## Cómo correrlo sin Docker

1. Instalar MySQL 8 y Python 3.11 o superior.
2. Cargar la base (como root de MySQL):
   ```bash
   mysql -u root -p < sql/01_schema.sql
   mysql -u root -p < sql/02_datos.sql
   ```
3. Instalar dependencias y arrancar:
   ```bash
   python -m venv .venv
   source .venv/bin/activate          # en Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   cd app
   python app.py                      # http://localhost:5000
   ```
   Por defecto la aplicación se conecta a `localhost:3306`. Si tu MySQL está en otro lado, definí las variables `DB_HOST` y `DB_PORT`.

## Usuarios de base de datos (seguridad)

Los crea `sql/01_schema.sql`. La aplicación elige uno según el rol de quien inició sesión:

| Usuario MySQL | Para qué | Permisos |
|---|---|---|
| `auth_db` | Iniciar sesión | Solo `SELECT` sobre `login` |
| `admin_db` | Administrador | `SELECT/INSERT/UPDATE/DELETE` sobre las tablas del torneo (sin `DROP`/`ALTER`, sin ver `login`) |
| `planillero_db` | Planillero | Lee datos de referencia; escribe planilla, goles, tarjetas y sanciones; de `partido` solo puede cambiar `estado` |

Las contraseñas de estos usuarios son de desarrollo y están en `sql/01_schema.sql` y `docker-compose.yml`.

## Qué probar rápido

1. Entrar como administrador → **Reportes**: los 12 reportes ya traen datos.
2. **Partidos** → partido de la fecha 4 *Humanas Club vs Empresariales FC* (27/10): está pendiente de planilla. Entrá a **Planilla**: el jugador sancionado de Humanas aparece bloqueado.
3. Entrar como planillero: solo ve **Partidos** y las planillas.
