"""Aplicación Flask del Torneo Interfacultades de Fútbol 5.

Estructura (todo en este archivo, ordenado por secciones):
  1. Configuración y utilidades (login, permisos, mensajes)
  2. Login / inicio
  3. ABMs del administrador: facultades, jugadores, complejos/canchas, torneos, equipos/planteles, sanciones
  4. Partidos y planilla (admin y planillero)
  5. Reportes

Patrón de cada ABM:  validar (validaciones.py) -> aplicar reglas (reglas.py) -> SQL (db.py) -> mensaje.
"""
import hashlib
import os
from datetime import date, timedelta
from functools import wraps

import mysql.connector
from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for)

import reglas
import reportes
import validaciones as v
from db import (ReglaError, cerrar_db, consultar, consultar_uno, ejecutar,
                get_db, mensaje_error, transaccion)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "clave-de-desarrollo-cambiar")
app.teardown_appcontext(cerrar_db)

ERRORES = (ReglaError, mysql.connector.Error)


# ====================================================================
# 1. UTILIDADES
# ====================================================================
@app.template_filter("fmt")
def formatear(valor):
    """Cómo se muestra cada tipo de dato en las tablas."""
    if valor is None:
        return "—"
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    if isinstance(valor, bytes):
        return valor.decode("utf-8")
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, timedelta):  # las columnas TIME llegan como timedelta
        minutos = int(valor.total_seconds() // 60)
        return f"{minutos // 60:02d}:{minutos % 60:02d}"
    return valor


def login_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if "rol" not in session:
            return redirect(url_for("login"))
        return vista(*args, **kwargs)
    return envoltura


def solo_admin(vista):
    """Las pantallas de gestión solo las ve el administrador."""
    @wraps(vista)
    @login_requerido
    def envoltura(*args, **kwargs):
        if session["rol"] != "administrador":
            flash("No tenés permiso para entrar a esa pantalla.", "error")
            return redirect(url_for("inicio"))
        return vista(*args, **kwargs)
    return envoltura


def intentar(accion, mensaje_ok):
    """Ejecuta `accion` en una transacción y deja un mensaje de éxito o de error. Devuelve True si salió bien."""
    try:
        with transaccion():
            accion()
        flash(mensaje_ok, "ok")
        return True
    except ERRORES as e:
        flash(mensaje_error(e), "error")
        return False


def elegir_torneo():
    """Torneo seleccionado con ?torneo=ID (por defecto el más reciente)."""
    torneos = consultar("SELECT * FROM torneo ORDER BY anio DESC, semestre DESC")
    pedido = request.args.get("torneo", type=int)
    elegido = next((t for t in torneos if t["id_torneo"] == pedido), torneos[0] if torneos else None)
    return torneos, elegido


@app.context_processor
def variables_globales():
    return {"rol": session.get("rol"), "usuario": session.get("correo")}


# ====================================================================
# 2. LOGIN E INICIO
# ====================================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            correo = v.email(request.form.get("correo"), "Correo")
            clave = v.texto(request.form.get("contrasena"), "Contraseña", 100)
            hash_clave = hashlib.sha256(clave.encode("utf-8")).hexdigest()
            fila = consultar_uno("SELECT correo, rol FROM login WHERE correo = %s AND contrasena = %s",
                                 (correo, hash_clave))
            if fila is None:
                raise ReglaError("Correo o contraseña incorrectos.")
            session.clear()
            session["correo"], session["rol"] = fila["correo"], fila["rol"]
            return redirect(url_for("inicio"))
        except ERRORES as e:
            flash(mensaje_error(e), "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_requerido
def inicio():
    return render_template("inicio.html")


# ====================================================================
# 3. ABMs DEL ADMINISTRADOR
# ====================================================================
# ---------- Facultades ----------
@app.route("/facultades")
@solo_admin
def facultades():
    filas = consultar("SELECT * FROM facultad ORDER BY nombre")
    return render_template("facultades.html", filas=filas)


@app.route("/facultades/nueva", methods=["GET", "POST"])
@solo_admin
def facultad_nueva():
    if request.method == "POST":
        def guardar():
            ejecutar("INSERT INTO facultad (nombre) VALUES (%s)", (v.texto(request.form.get("nombre"), "Nombre"),))
        if intentar(guardar, "Facultad creada."):
            return redirect(url_for("facultades"))
    return render_template("facultad_form.html", titulo="Nueva facultad", f=request.form)


@app.route("/facultades/<int:id_facultad>/editar", methods=["GET", "POST"])
@solo_admin
def facultad_editar(id_facultad):
    fila = consultar_uno("SELECT * FROM facultad WHERE id_facultad = %s", (id_facultad,)) or abort(404)
    if request.method == "POST":
        def guardar():
            ejecutar("UPDATE facultad SET nombre = %s WHERE id_facultad = %s",
                     (v.texto(request.form.get("nombre"), "Nombre"), id_facultad))
        if intentar(guardar, "Facultad modificada."):
            return redirect(url_for("facultades"))
    return render_template("facultad_form.html", titulo="Editar facultad",
                           f=request.form if request.method == "POST" else fila)


@app.route("/facultades/<int:id_facultad>/eliminar", methods=["POST"])
@solo_admin
def facultad_eliminar(id_facultad):
    intentar(lambda: ejecutar("DELETE FROM facultad WHERE id_facultad = %s", (id_facultad,)), "Facultad eliminada.")
    return redirect(url_for("facultades"))


# ---------- Jugadores ----------
TIPOS_JUGADOR = ["grado", "posgrado", "docente", "funcionario"]


@app.route("/jugadores")
@solo_admin
def jugadores():
    filas = consultar("""SELECT j.*, f.nombre AS facultad FROM jugador j
                           JOIN facultad f ON f.id_facultad = j.id_facultad
                          ORDER BY j.apellido, j.nombre""")
    return render_template("jugadores.html", filas=filas)


def lista_facultades():
    return consultar("SELECT id_facultad, nombre FROM facultad ORDER BY nombre")


def leer_jugador():
    """Valida el formulario de jugador y devuelve los datos ya convertidos."""
    nacimiento = v.fecha(request.form.get("fecha_nacimiento"), "Fecha de nacimiento")
    if nacimiento > date.today():
        raise ReglaError("Fecha de nacimiento: no puede ser futura.")
    facultades_ids = [str(f["id_facultad"]) for f in consultar("SELECT id_facultad FROM facultad")]
    return dict(
        ci=v.ci(request.form.get("ci")),
        nombre=v.texto(request.form.get("nombre"), "Nombre", 60),
        apellido=v.texto(request.form.get("apellido"), "Apellido", 60),
        email=v.email(request.form.get("email")),
        nacimiento=nacimiento,
        id_facultad=int(v.opcion(request.form.get("id_facultad"), "Facultad", facultades_ids)),
        tipo=v.opcion(request.form.get("tipo"), "Tipo", TIPOS_JUGADOR))


@app.route("/jugadores/nuevo", methods=["GET", "POST"])
@solo_admin
def jugador_nuevo():
    if request.method == "POST":
        def guardar():
            d = leer_jugador()
            ejecutar("""INSERT INTO jugador (ci, nombre, apellido, email, fecha_nacimiento, id_facultad, tipo)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                     (d["ci"], d["nombre"], d["apellido"], d["email"], d["nacimiento"], d["id_facultad"], d["tipo"]))
        if intentar(guardar, "Jugador creado."):
            return redirect(url_for("jugadores"))
    return render_template("jugador_form.html", titulo="Nuevo jugador", f=request.form, editando=False,
                           facultades=lista_facultades(), tipos=TIPOS_JUGADOR, hoy=date.today().isoformat())


@app.route("/jugadores/<int:ci>/editar", methods=["GET", "POST"])
@solo_admin
def jugador_editar(ci):
    fila = consultar_uno("SELECT * FROM jugador WHERE ci = %s", (ci,)) or abort(404)
    if request.method == "POST":
        def guardar():
            d = leer_jugador()
            d["ci"] = ci  # la cédula es la clave: no se cambia
            reglas.validar_cambio_jugador(ci, d["id_facultad"], d["tipo"])
            ejecutar("""UPDATE jugador SET nombre=%s, apellido=%s, email=%s, fecha_nacimiento=%s,
                               id_facultad=%s, tipo=%s WHERE ci=%s""",
                     (d["nombre"], d["apellido"], d["email"], d["nacimiento"], d["id_facultad"], d["tipo"], ci))
        if intentar(guardar, "Jugador modificado."):
            return redirect(url_for("jugadores"))
    datos = request.form.to_dict() if request.method == "POST" else fila
    datos["ci"] = ci
    return render_template("jugador_form.html", titulo="Editar jugador", f=datos, editando=True,
                           facultades=lista_facultades(), tipos=TIPOS_JUGADOR, hoy=date.today().isoformat())


@app.route("/jugadores/<int:ci>/eliminar", methods=["POST"])
@solo_admin
def jugador_eliminar(ci):
    intentar(lambda: ejecutar("DELETE FROM jugador WHERE ci = %s", (ci,)), "Jugador eliminado.")
    return redirect(url_for("jugadores"))


# ---------- Complejos y canchas ----------
@app.route("/complejos")
@solo_admin
def complejos():
    filas = consultar("SELECT * FROM complejo ORDER BY nombre")
    return render_template("complejos.html", filas=filas)


def leer_complejo():
    return (v.texto(request.form.get("nombre"), "Nombre", 80),
            v.texto(request.form.get("direccion"), "Dirección", 120),
            v.texto(request.form.get("departamento"), "Departamento", 40))


@app.route("/complejos/nuevo", methods=["GET", "POST"])
@solo_admin
def complejo_nuevo():
    if request.method == "POST":
        def guardar():
            ejecutar("INSERT INTO complejo (nombre, direccion, departamento) VALUES (%s, %s, %s)", leer_complejo())
        if intentar(guardar, "Complejo creado."):
            return redirect(url_for("complejos"))
    return render_template("complejo_form.html", titulo="Nuevo complejo", f=request.form)


@app.route("/complejos/<int:id_complejo>/editar", methods=["GET", "POST"])
@solo_admin
def complejo_editar(id_complejo):
    fila = consultar_uno("SELECT * FROM complejo WHERE id_complejo = %s", (id_complejo,)) or abort(404)
    if request.method == "POST":
        def guardar():
            ejecutar("UPDATE complejo SET nombre=%s, direccion=%s, departamento=%s WHERE id_complejo=%s",
                     leer_complejo() + (id_complejo,))
        if intentar(guardar, "Complejo modificado."):
            return redirect(url_for("complejos"))
    return render_template("complejo_form.html", titulo="Editar complejo",
                           f=request.form if request.method == "POST" else fila)


@app.route("/complejos/<int:id_complejo>/eliminar", methods=["POST"])
@solo_admin
def complejo_eliminar(id_complejo):
    intentar(lambda: ejecutar("DELETE FROM complejo WHERE id_complejo = %s", (id_complejo,)), "Complejo eliminado.")
    return redirect(url_for("complejos"))


@app.route("/complejos/<int:id_complejo>/canchas", methods=["GET", "POST"])
@solo_admin
def canchas(id_complejo):
    complejo = consultar_uno("SELECT * FROM complejo WHERE id_complejo = %s", (id_complejo,)) or abort(404)
    if request.method == "POST":  # alta de cancha
        def guardar():
            nombre = v.texto(request.form.get("nombre_cancha"), "Nombre de la cancha", 40)
            superficie = v.opcion(request.form.get("superficie"), "Superficie", ["sintetico", "parquet"])
            techada = request.form.get("techada") == "1"
            ejecutar("INSERT INTO cancha (nombre_cancha, id_complejo, superficie, techada) VALUES (%s, %s, %s, %s)",
                     (nombre, id_complejo, superficie, techada))
        if intentar(guardar, "Cancha creada."):
            return redirect(url_for("canchas", id_complejo=id_complejo))
    filas = consultar("SELECT * FROM cancha WHERE id_complejo = %s ORDER BY nombre_cancha", (id_complejo,))
    return render_template("canchas.html", complejo=complejo, filas=filas)


@app.route("/complejos/<int:id_complejo>/canchas/eliminar", methods=["POST"])
@solo_admin
def cancha_eliminar(id_complejo):
    intentar(lambda: ejecutar("DELETE FROM cancha WHERE nombre_cancha = %s AND id_complejo = %s",
                              (request.form.get("nombre_cancha"), id_complejo)), "Cancha eliminada.")
    return redirect(url_for("canchas", id_complejo=id_complejo))


@app.route("/complejos/<int:id_complejo>/canchas/modificar", methods=["POST"])
@solo_admin
def cancha_modificar(id_complejo):
    def guardar():
        superficie = v.opcion(request.form.get("superficie"), "Superficie", ["sintetico", "parquet"])
        ejecutar("UPDATE cancha SET superficie = %s, techada = %s WHERE nombre_cancha = %s AND id_complejo = %s",
                 (superficie, request.form.get("techada") == "1", request.form.get("nombre_cancha"), id_complejo))
    intentar(guardar, "Cancha modificada.")
    return redirect(url_for("canchas", id_complejo=id_complejo))


# ---------- Torneos ----------
@app.route("/torneos")
@solo_admin
def torneos():
    filas = consultar("SELECT * FROM torneo ORDER BY anio DESC, semestre DESC")
    return render_template("torneos.html", filas=filas)


def leer_torneo():
    inicio = v.fecha(request.form.get("fecha_inicio"), "Fecha de inicio")
    fin = v.fecha(request.form.get("fecha_fin"), "Fecha de fin")
    if fin < inicio:
        raise ReglaError("La fecha de fin no puede ser anterior a la de inicio.")
    return (v.texto(request.form.get("nombre"), "Nombre", 100),
            v.entero(request.form.get("anio"), "Año", 2000, 2100),
            int(v.opcion(request.form.get("semestre"), "Semestre", ["1", "2"])), inicio, fin)


@app.route("/torneos/nuevo", methods=["GET", "POST"])
@solo_admin
def torneo_nuevo():
    if request.method == "POST":
        def guardar():
            ejecutar("""INSERT INTO torneo (nombre, anio, semestre, fecha_inicio, fecha_fin, estado)
                        VALUES (%s, %s, %s, %s, %s, 'inscripcion')""", leer_torneo())
        if intentar(guardar, "Torneo creado en etapa de inscripción."):
            return redirect(url_for("torneos"))
    return render_template("torneo_form.html", titulo="Nuevo torneo", f=request.form)


@app.route("/torneos/<int:id_torneo>/editar", methods=["GET", "POST"])
@solo_admin
def torneo_editar(id_torneo):
    fila = consultar_uno("SELECT * FROM torneo WHERE id_torneo = %s", (id_torneo,)) or abort(404)
    if request.method == "POST":
        def guardar():
            ejecutar("""UPDATE torneo SET nombre=%s, anio=%s, semestre=%s, fecha_inicio=%s, fecha_fin=%s
                         WHERE id_torneo=%s""", leer_torneo() + (id_torneo,))
        if intentar(guardar, "Torneo modificado."):
            return redirect(url_for("torneos"))
    return render_template("torneo_form.html", titulo="Editar torneo",
                           f=request.form if request.method == "POST" else fila)


@app.route("/torneos/<int:id_torneo>/eliminar", methods=["POST"])
@solo_admin
def torneo_eliminar(id_torneo):
    intentar(lambda: ejecutar("DELETE FROM torneo WHERE id_torneo = %s", (id_torneo,)), "Torneo eliminado.")
    return redirect(url_for("torneos"))


@app.route("/torneos/<int:id_torneo>/iniciar", methods=["POST"])
@solo_admin
def torneo_iniciar(id_torneo):
    intentar(lambda: reglas.iniciar_torneo(id_torneo), "Torneo iniciado: ya se pueden programar partidos.")
    return redirect(url_for("torneos"))


@app.route("/torneos/<int:id_torneo>/finalizar", methods=["POST"])
@solo_admin
def torneo_finalizar(id_torneo):
    intentar(lambda: reglas.finalizar_torneo(id_torneo), "Torneo finalizado.")
    return redirect(url_for("torneos"))


# ---------- Equipos y planteles ----------
@app.route("/equipos")
@solo_admin
def equipos():
    lista_torneos, torneo = elegir_torneo()
    filas = []
    if torneo:
        filas = consultar("""SELECT e.id_equipo, e.nombre, f.nombre AS facultad,
                                    CONCAT(j.nombre, ' ', j.apellido) AS capitan,
                                    (SELECT COUNT(*) FROM equipo_jugador_torneo x WHERE x.id_equipo = e.id_equipo) AS jugadores
                               FROM equipo e JOIN facultad f ON f.id_facultad = e.id_facultad
                               LEFT JOIN jugador j ON j.ci = e.ci_capitan
                              WHERE e.id_torneo = %s ORDER BY e.nombre""", (torneo["id_torneo"],))
    return render_template("equipos.html", filas=filas, torneos=lista_torneos, torneo=torneo)


@app.route("/equipos/nuevo", methods=["GET", "POST"])
@solo_admin
def equipo_nuevo():
    id_torneo = request.values.get("torneo", type=int) or abort(404)
    facultades_ = lista_facultades()
    if request.method == "POST":
        def guardar():
            reglas.exigir_inscripcion(id_torneo)
            nombre = v.texto(request.form.get("nombre"), "Nombre del equipo", 80)
            id_facultad = int(v.opcion(request.form.get("id_facultad"), "Facultad",
                                       [str(f["id_facultad"]) for f in facultades_]))
            ejecutar("INSERT INTO equipo (nombre, id_torneo, id_facultad) VALUES (%s, %s, %s)",
                     (nombre, id_torneo, id_facultad))
        if intentar(guardar, "Equipo creado. Ahora armá su plantel y designá al capitán."):
            return redirect(url_for("equipos", torneo=id_torneo))
    return render_template("equipo_form.html", titulo="Nuevo equipo", f=request.form, nuevo=True,
                           facultades=facultades_, id_torneo=id_torneo)


@app.route("/equipos/<int:id_equipo>/editar", methods=["GET", "POST"])
@solo_admin
def equipo_editar(id_equipo):
    equipo = consultar_uno("SELECT * FROM equipo WHERE id_equipo = %s", (id_equipo,)) or abort(404)
    if request.method == "POST":
        def guardar():
            reglas.exigir_inscripcion(equipo["id_torneo"])
            ejecutar("UPDATE equipo SET nombre = %s WHERE id_equipo = %s",
                     (v.texto(request.form.get("nombre"), "Nombre del equipo", 80), id_equipo))
        if intentar(guardar, "Equipo modificado."):
            return redirect(url_for("equipos", torneo=equipo["id_torneo"]))
    return render_template("equipo_form.html", titulo="Editar equipo", nuevo=False, id_torneo=equipo["id_torneo"],
                           f=request.form if request.method == "POST" else equipo)


@app.route("/equipos/<int:id_equipo>/eliminar", methods=["POST"])
@solo_admin
def equipo_eliminar(id_equipo):
    equipo = reglas.get_equipo(id_equipo)

    def borrar():
        reglas.exigir_inscripcion(equipo["id_torneo"])
        ejecutar("DELETE FROM equipo WHERE id_equipo = %s", (id_equipo,))
    intentar(borrar, "Equipo eliminado.")
    return redirect(url_for("equipos", torneo=equipo["id_torneo"]))


@app.route("/equipos/<int:id_equipo>/plantel", methods=["GET", "POST"])
@solo_admin
def plantel(id_equipo):
    equipo = consultar_uno("""SELECT e.*, f.nombre AS facultad, t.estado AS estado_torneo
                                FROM equipo e JOIN facultad f ON f.id_facultad = e.id_facultad
                                JOIN torneo t ON t.id_torneo = e.id_torneo
                               WHERE e.id_equipo = %s""", (id_equipo,)) or abort(404)
    if request.method == "POST":  # agregar jugador al plantel
        def agregar():
            ci = v.ci(request.form.get("ci"))
            camiseta = v.entero(request.form.get("numero_camiseta"), "Camiseta", 1, 99)
            reglas.agregar_a_plantel(id_equipo, ci, camiseta)
        if intentar(agregar, "Jugador agregado al plantel."):
            return redirect(url_for("plantel", id_equipo=id_equipo))
    jugadores_plantel = consultar(
        """SELECT j.ci, j.nombre, j.apellido, j.tipo, ejt.numero_camiseta
             FROM equipo_jugador_torneo ejt JOIN jugador j ON j.ci = ejt.ci_jugador
            WHERE ejt.id_equipo = %s ORDER BY ejt.numero_camiseta""", (id_equipo,))
    # candidatos: jugadores de la misma facultad que todavía no están en ningún equipo de esta edición
    candidatos = consultar(
        """SELECT j.ci, j.nombre, j.apellido, j.tipo FROM jugador j
            WHERE j.id_facultad = %s
              AND NOT EXISTS (SELECT 1 FROM equipo_jugador_torneo x
                               WHERE x.ci_jugador = j.ci AND x.id_torneo = %s)
            ORDER BY j.apellido""", (equipo["id_facultad"], equipo["id_torneo"]))
    return render_template("plantel.html", equipo=equipo, plantel=jugadores_plantel, candidatos=candidatos)


@app.route("/equipos/<int:id_equipo>/plantel/quitar", methods=["POST"])
@solo_admin
def plantel_quitar(id_equipo):
    intentar(lambda: reglas.quitar_de_plantel(id_equipo, v.ci(request.form.get("ci"))), "Jugador quitado del plantel.")
    return redirect(url_for("plantel", id_equipo=id_equipo))


@app.route("/equipos/<int:id_equipo>/plantel/capitan", methods=["POST"])
@solo_admin
def plantel_capitan(id_equipo):
    intentar(lambda: reglas.designar_capitan(id_equipo, v.ci(request.form.get("ci"))), "Capitán designado.")
    return redirect(url_for("plantel", id_equipo=id_equipo))


# ---------- Sanciones disciplinarias (las automáticas se generan solas) ----------
@app.route("/sanciones")
@solo_admin
def sanciones():
    lista_torneos, torneo = elegir_torneo()
    filas = []
    if torneo:
        filas = consultar("""SELECT s.id_sancion, s.id_tarjeta, CONCAT(j.nombre, ' ', j.apellido) AS jugador,
                                    e.nombre AS equipo, s.motivo, s.numero_fecha_inicio,
                                    s.cantidad_fechas,
                                    s.numero_fecha_inicio + s.cantidad_fechas - 1 AS ultima_fecha
                               FROM sancion_jugador s
                               JOIN jugador j ON j.ci = s.ci_jugador
                               LEFT JOIN equipo_jugador_torneo ejt ON ejt.ci_jugador = s.ci_jugador AND ejt.id_torneo = s.id_torneo
                               LEFT JOIN equipo e ON e.id_equipo = ejt.id_equipo
                              WHERE s.id_torneo = %s ORDER BY s.numero_fecha_inicio, j.apellido""",
                         (torneo["id_torneo"],))
    return render_template("sanciones.html", filas=filas, torneos=lista_torneos, torneo=torneo)


def jugadores_del_torneo(id_torneo):
    return consultar(
        """SELECT j.ci, j.nombre, j.apellido FROM equipo_jugador_torneo ejt
             JOIN jugador j ON j.ci = ejt.ci_jugador WHERE ejt.id_torneo = %s ORDER BY j.apellido""", (id_torneo,))


@app.route("/sanciones/nueva", methods=["GET", "POST"])
@solo_admin
def sancion_nueva():
    id_torneo = request.values.get("torneo", type=int) or abort(404)
    if request.method == "POST":
        def guardar():
            ci = v.ci(request.form.get("ci"))
            inicio = v.entero(request.form.get("inicio"), "Desde la fecha", 1, 99)
            cantidad = v.entero(request.form.get("cantidad"), "Cantidad de fechas", 1, 50)
            reglas.validar_sancion_disciplinaria(id_torneo, ci)
            ejecutar("""INSERT INTO sancion_jugador (ci_jugador, id_torneo, motivo, numero_fecha_inicio, cantidad_fechas)
                        VALUES (%s, %s, 'disciplinaria', %s, %s)""", (ci, id_torneo, inicio, cantidad))
        if intentar(guardar, "Sanción cargada."):
            return redirect(url_for("sanciones", torneo=id_torneo))
    return render_template("sancion_form.html", titulo="Nueva sanción disciplinaria", f=request.form, nueva=True,
                           jugadores=jugadores_del_torneo(id_torneo), id_torneo=id_torneo)


@app.route("/sanciones/<int:id_sancion>/editar", methods=["GET", "POST"])
@solo_admin
def sancion_editar(id_sancion):
    s = consultar_uno("SELECT * FROM sancion_jugador WHERE id_sancion = %s", (id_sancion,)) or abort(404)
    if request.method == "POST":
        def guardar():
            reglas.exigir_sancion_disciplinaria(id_sancion)
            inicio = v.entero(request.form.get("inicio"), "Desde la fecha", 1, 99)
            cantidad = v.entero(request.form.get("cantidad"), "Cantidad de fechas", 1, 50)
            ejecutar("UPDATE sancion_jugador SET numero_fecha_inicio=%s, cantidad_fechas=%s WHERE id_sancion=%s",
                     (inicio, cantidad, id_sancion))
        if intentar(guardar, "Sanción modificada."):
            return redirect(url_for("sanciones", torneo=s["id_torneo"]))
    # el jugador no se cambia: si hace falta, se elimina la sanción y se crea otra
    datos = request.form if request.method == "POST" else {"inicio": s["numero_fecha_inicio"], "cantidad": s["cantidad_fechas"]}
    return render_template("sancion_form.html", titulo="Editar sanción", f=datos, nueva=False, id_torneo=s["id_torneo"])


@app.route("/sanciones/<int:id_sancion>/eliminar", methods=["POST"])
@solo_admin
def sancion_eliminar(id_sancion):
    s = consultar_uno("SELECT id_torneo FROM sancion_jugador WHERE id_sancion = %s", (id_sancion,)) or abort(404)

    def borrar():
        reglas.exigir_sancion_disciplinaria(id_sancion)
        ejecutar("DELETE FROM sancion_jugador WHERE id_sancion = %s", (id_sancion,))
    intentar(borrar, "Sanción eliminada.")
    return redirect(url_for("sanciones", torneo=s["id_torneo"]))


# ====================================================================
# 4. PARTIDOS Y PLANILLA
# ====================================================================
@app.route("/partidos")
@login_requerido
def partidos():
    lista_torneos, torneo = elegir_torneo()
    filas = []
    if torneo:
        filas = consultar("""SELECT r.id_partido, r.numero_fecha, r.dia, LEFT(t.hora_inicio, 5) AS hora, r.estado,
                                    el.nombre AS local, ev.nombre AS visitante,
                                    CONCAT(c.nombre, ' / ', r.nombre_cancha) AS cancha,
                                    CASE WHEN r.estado = 'jugado'
                                         THEN CONCAT(r.goles_local, ' - ', r.goles_visitante) END AS resultado
                               FROM v_resultado_partido r
                               JOIN equipo el  ON el.id_equipo = r.id_equipo_local
                               JOIN equipo ev  ON ev.id_equipo = r.id_equipo_visitante
                               JOIN turno t    ON t.id_turno = r.id_turno
                               JOIN complejo c ON c.id_complejo = r.id_complejo
                              WHERE r.id_torneo = %s ORDER BY r.numero_fecha, r.dia, t.hora_inicio""",
                         (torneo["id_torneo"],))
    return render_template("partidos.html", filas=filas, torneos=lista_torneos, torneo=torneo)


def opciones_partido(id_torneo):
    """Listas para los desplegables del formulario de partido."""
    equipos_ = consultar("SELECT id_equipo, nombre FROM equipo WHERE id_torneo = %s ORDER BY nombre", (id_torneo,))
    turnos = consultar("SELECT id_turno, LEFT(hora_inicio, 5) AS desde, LEFT(hora_fin, 5) AS hasta FROM turno ORDER BY id_turno")
    canchas_ = consultar("""SELECT c.nombre_cancha, c.id_complejo, x.nombre AS complejo FROM cancha c
                              JOIN complejo x ON x.id_complejo = c.id_complejo ORDER BY x.nombre, c.nombre_cancha""")
    return equipos_, turnos, canchas_


def leer_partido(id_torneo, con_estado=False):
    equipos_, turnos, canchas_ = opciones_partido(id_torneo)
    ids_equipos = [str(e["id_equipo"]) for e in equipos_]
    cancha = v.opcion(request.form.get("cancha"), "Cancha", [f"{c['id_complejo']}|{c['nombre_cancha']}" for c in canchas_])
    id_complejo, nombre_cancha = cancha.split("|", 1)
    return dict(
        id_torneo=id_torneo,
        numero_fecha=v.entero(request.form.get("numero_fecha"), "Fecha del torneo", 1, 99),
        local=int(v.opcion(request.form.get("local"), "Equipo local", ids_equipos)),
        visitante=int(v.opcion(request.form.get("visitante"), "Equipo visitante", ids_equipos)),
        dia=v.fecha(request.form.get("dia"), "Día"),
        id_turno=int(v.opcion(request.form.get("id_turno"), "Turno", [str(t["id_turno"]) for t in turnos])),
        nombre_cancha=nombre_cancha, id_complejo=int(id_complejo),
        estado=v.opcion(request.form.get("estado"), "Estado", ["programado", "postergado", "cancelado"]) if con_estado else "programado")


@app.route("/partidos/nuevo", methods=["GET", "POST"])
@solo_admin
def partido_nuevo():
    id_torneo = request.values.get("torneo", type=int) or abort(404)
    if request.method == "POST":
        if intentar(lambda: reglas.crear_partido(leer_partido(id_torneo)), "Partido programado."):
            return redirect(url_for("partidos", torneo=id_torneo))
    equipos_, turnos, canchas_ = opciones_partido(id_torneo)
    return render_template("partido_form.html", titulo="Nuevo partido", f=request.form, nuevo=True,
                           equipos=equipos_, turnos=turnos, canchas=canchas_, id_torneo=id_torneo)


@app.route("/partidos/<int:id_partido>/editar", methods=["GET", "POST"])
@solo_admin
def partido_editar(id_partido):
    p = consultar_uno("SELECT * FROM partido WHERE id_partido = %s", (id_partido,)) or abort(404)
    if request.method == "POST":
        if intentar(lambda: reglas.editar_partido(id_partido, leer_partido(p["id_torneo"], con_estado=True)),
                    "Partido modificado."):
            return redirect(url_for("partidos", torneo=p["id_torneo"]))
    if request.method == "POST":
        datos = request.form
    else:  # los nombres de los campos del formulario difieren de las columnas
        datos = dict(p, local=p["id_equipo_local"], visitante=p["id_equipo_visitante"],
                     cancha=f"{p['id_complejo']}|{p['nombre_cancha']}")
    equipos_, turnos, canchas_ = opciones_partido(p["id_torneo"])
    return render_template("partido_form.html", titulo="Editar partido", f=datos, nuevo=False,
                           equipos=equipos_, turnos=turnos, canchas=canchas_, id_torneo=p["id_torneo"])


@app.route("/partidos/<int:id_partido>/eliminar", methods=["POST"])
@solo_admin
def partido_eliminar(id_partido):
    p = reglas.get_partido(id_partido)
    intentar(lambda: reglas.eliminar_partido(id_partido), "Partido eliminado.")
    return redirect(url_for("partidos", torneo=p["id_torneo"]))


@app.route("/partidos/<int:id_partido>/estado", methods=["POST"])
@solo_admin
def partido_estado(id_partido):
    p = reglas.get_partido(id_partido)
    nuevo = request.form.get("estado")
    intentar(lambda: reglas.cambiar_estado_partido(id_partido, v.opcion(nuevo, "Estado", ["postergado", "cancelado"])),
             f"Partido {nuevo}.")
    return redirect(url_for("partidos", torneo=p["id_torneo"]))


@app.route("/partidos/<int:id_partido>/planilla")
@login_requerido
def planilla(id_partido):
    p = consultar_uno(
        """SELECT r.*, p.estado, el.nombre AS local, ev.nombre AS visitante,
                  t.estado AS estado_torneo, tu.hora_fin
             FROM v_resultado_partido r
             JOIN partido p  ON p.id_partido = r.id_partido
             JOIN equipo el  ON el.id_equipo = r.id_equipo_local
             JOIN equipo ev  ON ev.id_equipo = r.id_equipo_visitante
             JOIN torneo t   ON t.id_torneo = r.id_torneo
             JOIN turno tu   ON tu.id_turno = r.id_turno
            WHERE r.id_partido = %s""", (id_partido,)) or abort(404)
    motivo = reglas.motivo_no_modificable(p)  # None = se puede editar

    # plantel de ambos equipos, marcando quién ya está en la planilla y quién está suspendido
    plantel_ = consultar(
        """SELECT ejt.id_equipo, j.ci, j.nombre, j.apellido, ejt.numero_camiseta,
                  (pl.ci_jugador IS NOT NULL) AS en_planilla,
                  EXISTS (SELECT 1 FROM sancion_jugador s
                           WHERE s.ci_jugador = j.ci AND s.id_torneo = %s
                             AND %s BETWEEN s.numero_fecha_inicio AND s.numero_fecha_inicio + s.cantidad_fechas - 1) AS suspendido
             FROM equipo_jugador_torneo ejt
             JOIN jugador j ON j.ci = ejt.ci_jugador
             LEFT JOIN planilla_partido pl ON pl.id_partido = %s AND pl.ci_jugador = ejt.ci_jugador
            WHERE ejt.id_equipo IN (%s, %s) ORDER BY ejt.id_equipo, ejt.numero_camiseta""",
        (p["id_torneo"], p["numero_fecha"], id_partido, p["id_equipo_local"], p["id_equipo_visitante"]))
    en_planilla = [j for j in plantel_ if j["en_planilla"]]
    goles = consultar("""SELECT g.id_gol, g.minuto, g.autogol, CONCAT(j.nombre, ' ', j.apellido) AS jugador
                           FROM gol g JOIN jugador j ON j.ci = g.ci_jugador
                          WHERE g.id_partido = %s ORDER BY g.minuto""", (id_partido,))
    tarjetas = consultar("""SELECT t.id_tarjeta, t.minuto, t.color, CONCAT(j.nombre, ' ', j.apellido) AS jugador
                              FROM tarjeta t JOIN jugador j ON j.ci = t.ci_jugador
                             WHERE t.id_partido = %s ORDER BY t.minuto""", (id_partido,))
    return render_template("planilla.html", p=p, motivo=motivo, plantel=plantel_, en_planilla=en_planilla,
                           goles=goles, tarjetas=tarjetas)


@app.route("/partidos/<int:id_partido>/planilla/guardar", methods=["POST"])
@login_requerido
def planilla_guardar(id_partido):
    def guardar():
        cis = [v.ci(c) for c in request.form.getlist("jugadores")]
        reglas.guardar_planilla(id_partido, cis)
    intentar(guardar, "Planilla guardada.")
    return redirect(url_for("planilla", id_partido=id_partido))


@app.route("/partidos/<int:id_partido>/gol", methods=["POST"])
@login_requerido
def gol_agregar(id_partido):
    def guardar():
        reglas.agregar_gol(id_partido, v.ci(request.form.get("ci")),
                           v.entero(request.form.get("minuto"), "Minuto", 1, 60),
                           request.form.get("autogol") == "1")
    intentar(guardar, "Gol registrado.")
    return redirect(url_for("planilla", id_partido=id_partido))


@app.route("/partidos/<int:id_partido>/gol/<int:id_gol>/eliminar", methods=["POST"])
@login_requerido
def gol_eliminar(id_partido, id_gol):
    intentar(lambda: reglas.eliminar_gol(id_gol), "Gol eliminado.")
    return redirect(url_for("planilla", id_partido=id_partido))


@app.route("/partidos/<int:id_partido>/tarjeta", methods=["POST"])
@login_requerido
def tarjeta_agregar(id_partido):
    def guardar():
        reglas.agregar_tarjeta(id_partido, v.ci(request.form.get("ci")),
                               v.entero(request.form.get("minuto"), "Minuto", 1, 60),
                               v.opcion(request.form.get("color"), "Color", ["amarilla", "roja"]))
    intentar(guardar, "Tarjeta registrada (si corresponde, la sanción se generó automáticamente).")
    return redirect(url_for("planilla", id_partido=id_partido))


@app.route("/partidos/<int:id_partido>/tarjeta/<int:id_tarjeta>/eliminar", methods=["POST"])
@login_requerido
def tarjeta_eliminar(id_partido, id_tarjeta):
    intentar(lambda: reglas.eliminar_tarjeta(id_tarjeta), "Tarjeta eliminada.")
    return redirect(url_for("planilla", id_partido=id_partido))


@app.route("/partidos/<int:id_partido>/cerrar", methods=["POST"])
@login_requerido
def partido_cerrar(id_partido):
    intentar(lambda: reglas.cerrar_partido(id_partido), "Partido marcado como jugado.")
    return redirect(url_for("planilla", id_partido=id_partido))


# ====================================================================
# 5. REPORTES
# ====================================================================
@app.route("/reportes")
@solo_admin
def reportes_menu():
    lista_torneos, torneo = elegir_torneo()
    return render_template("reportes.html", reportes=reportes.REPORTES, torneos=lista_torneos, torneo=torneo)


@app.route("/reportes/<slug>")
@solo_admin
def reporte(slug):
    definicion = reportes.POR_SLUG.get(slug) or abort(404)
    lista_torneos, torneo = elegir_torneo()
    resultados = []
    if torneo:
        for subtitulo, sql in definicion["consultas"]:
            # cursor propio para conocer el orden de las columnas (cur.column_names)
            cur = get_db().cursor(dictionary=True)
            cur.execute(sql, {"torneo": torneo["id_torneo"]})
            filas = cur.fetchall()
            resultados.append((subtitulo, cur.column_names, filas))
            cur.close()
    return render_template("reporte.html", r=definicion, resultados=resultados, torneos=lista_torneos, torneo=torneo)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=os.getenv("FLASK_DEBUG") == "1")
