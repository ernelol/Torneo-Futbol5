"""Acceso a la base de datos (sin ORM: SQL escrito a mano con mysql-connector).

Idea clave de seguridad: la aplicación se conecta a MySQL con un usuario
distinto según el rol de quien inició sesión (ver sql/01_schema.sql):
    sin sesión   -> auth_db       (solo puede leer la tabla login)
    administrador-> admin_db      (CRUD de todo el torneo)
    planillero   -> planillero_db (solo planilla, goles y tarjetas)
"""
import os
from contextlib import contextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

import mysql.connector
from flask import g, session

HOST = os.getenv("DB_HOST", "localhost")
PUERTO = int(os.getenv("DB_PORT", "3306"))
NOMBRE_BD = os.getenv("DB_NAME", "torneo_f5")

# rol -> (usuario de MySQL, contraseña)
USUARIOS = {
    "auth":          (os.getenv("DB_AUTH_USER", "auth_db"),           os.getenv("DB_AUTH_PASS", "auth_pass_2026")),
    "administrador": (os.getenv("DB_ADMIN_USER", "admin_db"),         os.getenv("DB_ADMIN_PASS", "admin_pass_2026")),
    "planillero":    (os.getenv("DB_PLANILLERO_USER", "planillero_db"), os.getenv("DB_PLANILLERO_PASS", "planillero_pass_2026")),
}


class ReglaError(Exception):
    """Error de validación o de regla de negocio. El mensaje se muestra al usuario."""


def ahora():
    """Hora actual de Uruguay (sin zona horaria, igual que los DATE/TIME de MySQL)."""
    return datetime.now(ZoneInfo("America/Montevideo")).replace(tzinfo=None)


def get_db():
    """Una conexión por pedido HTTP, con el usuario de MySQL que corresponde al rol."""
    if "db" not in g:
        usuario, clave = USUARIOS[session.get("rol", "auth")]
        g.db = mysql.connector.connect(host=HOST, port=PUERTO, user=usuario, password=clave,
                                       database=NOMBRE_BD, charset="utf8mb4", autocommit=False)
    return g.db


def cerrar_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def consultar(sql, params=None):
    """SELECT: devuelve una lista de diccionarios. Siempre con parámetros (%s) -> evita SQL injection."""
    cur = get_db().cursor(dictionary=True)
    cur.execute(sql, params or ())
    filas = cur.fetchall()
    cur.close()
    return filas


def consultar_uno(sql, params=None):
    filas = consultar(sql, params)
    return filas[0] if filas else None


def ejecutar(sql, params=None):
    """INSERT / UPDATE / DELETE. Devuelve el id autogenerado (si hubo)."""
    cur = get_db().cursor()
    cur.execute(sql, params or ())
    nuevo_id = cur.lastrowid
    cur.close()
    return nuevo_id


@contextmanager
def transaccion():
    """Todo lo que ocurre dentro del bloque se guarda junto (COMMIT) o no se guarda nada (ROLLBACK)."""
    try:
        yield
        get_db().commit()
    except Exception:
        get_db().rollback()
        raise


def mensaje_error(e):
    """Convierte un error en un mensaje entendible para el usuario."""
    if isinstance(e, ReglaError):
        return str(e)
    if isinstance(e, mysql.connector.Error):
        causas = {
            1062: "Ya existe un registro con esos datos (valor repetido).",
            1451: "No se puede eliminar: tiene registros asociados.",
            1452: "Hay una referencia a un dato que no existe.",
            3819: "Un dato no cumple una restricción de la base de datos.",
            4025: "Un dato no cumple una restricción de la base de datos.",
            1142: "Permiso denegado: tu rol no puede hacer esta operación en la base de datos.",
            1143: "Permiso denegado: tu rol no puede hacer esta operación en la base de datos.",
        }
        return causas.get(e.errno, f"Error de base de datos: {e.msg}")
    raise e
