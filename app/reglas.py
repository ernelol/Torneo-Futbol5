"""Reglas de negocio del torneo (la 2da capa de validación: Python).

Las reglas "de forma" (claves únicas, rangos, referencias) las garantiza además
la base de datos; acá van las que dependen de consultar otras filas
(por ejemplo: "un equipo no juega dos veces en la misma fecha").

Todas las funciones lanzan ReglaError con un mensaje claro si algo no se cumple.
"""
from datetime import datetime, timedelta

from db import ReglaError, ahora, consultar, consultar_uno, ejecutar


# ---------------------------------------------------------------- búsquedas
def get_torneo(id_torneo):
    torneo = consultar_uno("SELECT * FROM torneo WHERE id_torneo = %s", (id_torneo,))
    if torneo is None:
        raise ReglaError("El torneo no existe.")
    return torneo


def get_equipo(id_equipo):
    equipo = consultar_uno("SELECT * FROM equipo WHERE id_equipo = %s", (id_equipo,))
    if equipo is None:
        raise ReglaError("El equipo no existe.")
    return equipo


def get_partido(id_partido):
    """Partido con el estado de su torneo y la hora de fin de su turno."""
    partido = consultar_uno(
        """SELECT p.*, t.estado AS estado_torneo, tu.hora_fin
             FROM partido p
             JOIN torneo t  ON t.id_torneo = p.id_torneo
             JOIN turno  tu ON tu.id_turno = p.id_turno
            WHERE p.id_partido = %s""", (id_partido,))
    if partido is None:
        raise ReglaError("El partido no existe.")
    return partido


# ------------------------------------------------------------------- torneo
def iniciar_torneo(id_torneo):
    """inscripción -> en curso. Exige equipos completos (5 a 10 jugadores) y con capitán."""
    torneo = get_torneo(id_torneo)
    if torneo["estado"] != "inscripcion":
        raise ReglaError("Solo se puede iniciar un torneo que está en inscripción.")
    equipos = consultar(
        """SELECT e.nombre, e.ci_capitan, COUNT(ejt.ci_jugador) AS jugadores
             FROM equipo e
             LEFT JOIN equipo_jugador_torneo ejt ON ejt.id_equipo = e.id_equipo
            WHERE e.id_torneo = %s
            GROUP BY e.id_equipo, e.nombre, e.ci_capitan""", (id_torneo,))
    if len(equipos) < 2:
        raise ReglaError("Se necesitan al menos 2 equipos para iniciar el torneo.")
    for e in equipos:
        if e["jugadores"] < 5:
            raise ReglaError(f"{e['nombre']} tiene menos de 5 jugadores.")
        if e["ci_capitan"] is None:
            raise ReglaError(f"{e['nombre']} no tiene capitán designado.")
    ejecutar("UPDATE torneo SET estado = 'en_curso' WHERE id_torneo = %s", (id_torneo,))


def finalizar_torneo(id_torneo):
    """en curso -> finalizado. No puede quedar ningún partido pendiente."""
    torneo = get_torneo(id_torneo)
    if torneo["estado"] != "en_curso":
        raise ReglaError("Solo se puede finalizar un torneo que está en curso.")
    pendientes = consultar_uno(
        "SELECT COUNT(*) AS n FROM partido WHERE id_torneo = %s AND estado IN ('programado','postergado')",
        (id_torneo,))["n"]
    if pendientes:
        raise ReglaError(f"Quedan {pendientes} partidos programados o postergados sin jugar/cancelar.")
    ejecutar("UPDATE torneo SET estado = 'finalizado' WHERE id_torneo = %s", (id_torneo,))


# ------------------------------------------------------------ equipo y plantel
def exigir_inscripcion(id_torneo):
    if get_torneo(id_torneo)["estado"] != "inscripcion":
        raise ReglaError("Equipos y planteles solo se modifican mientras el torneo está en inscripción.")


def agregar_a_plantel(id_equipo, ci, camiseta):
    equipo = get_equipo(id_equipo)
    exigir_inscripcion(equipo["id_torneo"])

    jugador = consultar_uno("SELECT * FROM jugador WHERE ci = %s", (ci,))
    if jugador is None:
        raise ReglaError("El jugador no existe.")
    if jugador["id_facultad"] != equipo["id_facultad"]:
        raise ReglaError("El jugador debe pertenecer a la facultad que representa el equipo.")

    otro = consultar_uno(
        """SELECT e.nombre FROM equipo_jugador_torneo ejt
             JOIN equipo e ON e.id_equipo = ejt.id_equipo
            WHERE ejt.ci_jugador = %s AND ejt.id_torneo = %s""", (ci, equipo["id_torneo"]))
    if otro:
        raise ReglaError(f"El jugador ya integra el equipo {otro['nombre']} en esta edición.")

    cuenta = consultar_uno(
        """SELECT COUNT(*) AS total,
                  COALESCE(SUM(j.tipo IN ('docente','funcionario')), 0) AS especiales
             FROM equipo_jugador_torneo ejt JOIN jugador j ON j.ci = ejt.ci_jugador
            WHERE ejt.id_equipo = %s""", (id_equipo,))
    if cuenta["total"] >= 10:
        raise ReglaError("El plantel ya tiene el máximo de 10 jugadores.")
    if jugador["tipo"] in ("docente", "funcionario") and cuenta["especiales"] >= 2:
        raise ReglaError("Cada plantel admite como máximo 2 docentes/funcionarios.")

    ejecutar("INSERT INTO equipo_jugador_torneo (id_equipo, ci_jugador, id_torneo, numero_camiseta) "
             "VALUES (%s, %s, %s, %s)", (id_equipo, ci, equipo["id_torneo"], camiseta))


def quitar_de_plantel(id_equipo, ci):
    equipo = get_equipo(id_equipo)
    exigir_inscripcion(equipo["id_torneo"])
    if equipo["ci_capitan"] == ci:
        raise ReglaError("No se puede quitar al capitán: designá a otro jugador como capitán primero.")
    ejecutar("DELETE FROM equipo_jugador_torneo WHERE id_equipo = %s AND ci_jugador = %s", (id_equipo, ci))


def designar_capitan(id_equipo, ci):
    equipo = get_equipo(id_equipo)
    exigir_inscripcion(equipo["id_torneo"])
    esta = consultar_uno("SELECT 1 AS x FROM equipo_jugador_torneo WHERE id_equipo = %s AND ci_jugador = %s",
                         (id_equipo, ci))
    if esta is None:
        raise ReglaError("El capitán debe ser uno de los jugadores del plantel.")
    ejecutar("UPDATE equipo SET ci_capitan = %s WHERE id_equipo = %s", (ci, id_equipo))


# ------------------------------------------------------------------ partidos
def validar_partido(d, id_actual=0):
    """d = dict con id_torneo, numero_fecha, local, visitante, dia, id_turno,
    nombre_cancha, id_complejo, estado. id_actual = partido que se está editando (0 si es nuevo)."""
    torneo = get_torneo(d["id_torneo"])
    if torneo["estado"] != "en_curso":
        raise ReglaError("Los partidos solo se programan con el torneo en curso.")
    if d["local"] == d["visitante"]:
        raise ReglaError("Un equipo no puede enfrentarse a sí mismo.")

    # ambos equipos de la misma edición y con al menos 5 jugadores
    for id_equipo in (d["local"], d["visitante"]):
        equipo = get_equipo(id_equipo)
        if equipo["id_torneo"] != d["id_torneo"]:
            raise ReglaError("Ambos equipos deben pertenecer a la misma edición del torneo.")
        n = consultar_uno("SELECT COUNT(*) AS n FROM equipo_jugador_torneo WHERE id_equipo = %s",
                          (id_equipo,))["n"]
        if n < 5:
            raise ReglaError(f"{equipo['nombre']} tiene menos de 5 jugadores en su plantel.")

    # una cancha no puede tener dos partidos el mismo día y turno
    ocupada = consultar_uno(
        """SELECT id_partido FROM partido
            WHERE dia = %s AND id_turno = %s AND nombre_cancha = %s AND id_complejo = %s
              AND id_partido <> %s""",
        (d["dia"], d["id_turno"], d["nombre_cancha"], d["id_complejo"], id_actual))
    if ocupada:
        raise ReglaError("Esa cancha ya tiene un partido asignado en ese día y turno.")

    if d["estado"] == "cancelado":
        return  # un partido cancelado no cuenta para las dos reglas siguientes

    # no repetir rival (salvo que el partido anterior haya sido cancelado)
    repetido = consultar_uno(
        """SELECT id_partido FROM partido
            WHERE id_torneo = %s AND estado <> 'cancelado' AND id_partido <> %s
              AND ((id_equipo_local = %s AND id_equipo_visitante = %s)
                OR (id_equipo_local = %s AND id_equipo_visitante = %s))""",
        (d["id_torneo"], id_actual, d["local"], d["visitante"], d["visitante"], d["local"]))
    if repetido:
        raise ReglaError("Esos equipos ya tienen un partido en esta edición (liga a una sola rueda).")

    # un equipo no juega más de un partido por fecha
    for id_equipo in (d["local"], d["visitante"]):
        ya_juega = consultar_uno(
            """SELECT id_partido FROM partido
                WHERE id_torneo = %s AND numero_fecha = %s AND estado <> 'cancelado'
                  AND id_partido <> %s AND (id_equipo_local = %s OR id_equipo_visitante = %s)""",
            (d["id_torneo"], d["numero_fecha"], id_actual, id_equipo, id_equipo))
        if ya_juega:
            nombre = get_equipo(id_equipo)["nombre"]
            raise ReglaError(f"{nombre} ya tiene un partido en la fecha {d['numero_fecha']}.")


def crear_partido(d):
    d["estado"] = "programado"
    validar_partido(d)
    ejecutar(
        """INSERT INTO partido (id_torneo, numero_fecha, id_equipo_local, id_equipo_visitante,
                                dia, id_turno, nombre_cancha, id_complejo, estado)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'programado')""",
        (d["id_torneo"], d["numero_fecha"], d["local"], d["visitante"],
         d["dia"], d["id_turno"], d["nombre_cancha"], d["id_complejo"]))


def editar_partido(id_partido, d):
    partido = get_partido(id_partido)
    if partido["estado"] == "jugado":
        raise ReglaError("Un partido jugado no se puede modificar (solo corregir su planilla en 48 horas).")
    d["id_torneo"] = partido["id_torneo"]
    validar_partido(d, id_partido)
    ejecutar(
        """UPDATE partido SET numero_fecha=%s, id_equipo_local=%s, id_equipo_visitante=%s,
                  dia=%s, id_turno=%s, nombre_cancha=%s, id_complejo=%s, estado=%s
            WHERE id_partido=%s""",
        (d["numero_fecha"], d["local"], d["visitante"], d["dia"], d["id_turno"],
         d["nombre_cancha"], d["id_complejo"], d["estado"], id_partido))


def eliminar_partido(id_partido):
    if get_partido(id_partido)["estado"] == "jugado":
        raise ReglaError("Un partido jugado no puede eliminarse.")
    ejecutar("DELETE FROM partido WHERE id_partido = %s", (id_partido,))


def cambiar_estado_partido(id_partido, nuevo_estado):
    """Postergar o cancelar un partido que todavía no se jugó."""
    if get_partido(id_partido)["estado"] == "jugado":
        raise ReglaError("Un partido jugado no puede postergarse ni cancelarse.")
    ejecutar("UPDATE partido SET estado = %s WHERE id_partido = %s", (nuevo_estado, id_partido))


# ------------------------------------------------------------------- planilla
def motivo_no_modificable(partido):
    """Devuelve None si se puede registrar/corregir la planilla, o el motivo por el que no."""
    if partido["estado_torneo"] != "en_curso":
        return "El torneo no está en curso."
    if partido["estado"] in ("postergado", "cancelado"):
        return f"El partido está {partido['estado']}."
    fin = datetime.combine(partido["dia"], datetime.min.time()) + partido["hora_fin"]
    if ahora() < fin:
        return f"El partido todavía no se disputó (su turno termina {fin:%d/%m/%Y %H:%M})."
    if partido["estado"] == "jugado" and ahora() > fin + timedelta(hours=48):
        return "Pasaron más de 48 horas desde que se disputó: el resultado ya no se puede corregir."
    return None


def exigir_modificable(id_partido):
    partido = get_partido(id_partido)
    motivo = motivo_no_modificable(partido)
    if motivo:
        raise ReglaError(motivo)
    return partido


def esta_suspendido(ci, id_torneo, numero_fecha):
    fila = consultar_uno(
        """SELECT id_sancion FROM sancion_jugador
            WHERE ci_jugador = %s AND id_torneo = %s
              AND %s BETWEEN numero_fecha_inicio AND numero_fecha_inicio + cantidad_fechas - 1""",
        (ci, id_torneo, numero_fecha))
    return fila is not None


def guardar_planilla(id_partido, cis):
    """Deja la planilla del partido exactamente con los jugadores de la lista `cis`."""
    partido = exigir_modificable(id_partido)
    plantel = {f["ci_jugador"]: f["id_equipo"] for f in consultar(
        "SELECT ci_jugador, id_equipo FROM equipo_jugador_torneo WHERE id_equipo IN (%s, %s)",
        (partido["id_equipo_local"], partido["id_equipo_visitante"]))}
    actuales = {f["ci_jugador"] for f in consultar(
        "SELECT ci_jugador FROM planilla_partido WHERE id_partido = %s", (id_partido,))}
    nuevos = set(cis)

    for ci in nuevos - actuales:
        if ci not in plantel:
            raise ReglaError("Solo pueden figurar jugadores del plantel de alguno de los dos equipos.")
        if esta_suspendido(ci, partido["id_torneo"], partido["numero_fecha"]):
            raise ReglaError(f"El jugador {ci} está suspendido en la fecha {partido['numero_fecha']}.")

    for ci in actuales - nuevos:
        usado = consultar_uno(
            """SELECT 1 AS x FROM gol WHERE id_partido = %s AND ci_jugador = %s
               UNION SELECT 1 FROM tarjeta WHERE id_partido = %s AND ci_jugador = %s""",
            (id_partido, ci, id_partido, ci))
        if usado:
            raise ReglaError(f"El jugador {ci} tiene goles o tarjetas en este partido: borralos primero.")
        ejecutar("DELETE FROM planilla_partido WHERE id_partido = %s AND ci_jugador = %s", (id_partido, ci))

    for ci in nuevos - actuales:
        ejecutar("INSERT INTO planilla_partido (id_partido, ci_jugador, id_equipo) VALUES (%s, %s, %s)",
                 (id_partido, ci, plantel[ci]))


def exigir_en_planilla(id_partido, ci):
    fila = consultar_uno("SELECT 1 AS x FROM planilla_partido WHERE id_partido = %s AND ci_jugador = %s",
                         (id_partido, ci))
    if fila is None:
        raise ReglaError("Solo pueden convertir goles o recibir tarjetas los jugadores que figuran en la planilla.")


def agregar_gol(id_partido, ci, minuto, autogol):
    exigir_modificable(id_partido)
    exigir_en_planilla(id_partido, ci)
    ejecutar("INSERT INTO gol (id_partido, ci_jugador, minuto, autogol) VALUES (%s, %s, %s, %s)",
             (id_partido, ci, minuto, autogol))


def eliminar_gol(id_gol):
    gol = consultar_uno("SELECT id_partido FROM gol WHERE id_gol = %s", (id_gol,))
    if gol is None:
        raise ReglaError("El gol no existe.")
    exigir_modificable(gol["id_partido"])
    ejecutar("DELETE FROM gol WHERE id_gol = %s", (id_gol,))


def agregar_tarjeta(id_partido, ci, minuto, color):
    partido = exigir_modificable(id_partido)
    exigir_en_planilla(id_partido, ci)
    ejecutar("INSERT INTO tarjeta (id_partido, ci_jugador, minuto, color) VALUES (%s, %s, %s, %s)",
             (id_partido, ci, minuto, color))
    recalcular_sanciones(ci, partido["id_torneo"])


def eliminar_tarjeta(id_tarjeta):
    tarjeta = consultar_uno(
        """SELECT t.id_partido, t.ci_jugador, p.id_torneo FROM tarjeta t
             JOIN partido p ON p.id_partido = t.id_partido WHERE t.id_tarjeta = %s""", (id_tarjeta,))
    if tarjeta is None:
        raise ReglaError("La tarjeta no existe.")
    exigir_modificable(tarjeta["id_partido"])
    ejecutar("DELETE FROM tarjeta WHERE id_tarjeta = %s", (id_tarjeta,))
    recalcular_sanciones(tarjeta["ci_jugador"], tarjeta["id_torneo"])


def cerrar_partido(id_partido):
    """Marca el partido como jugado (solo si su día y turno ya pasaron)."""
    partido = exigir_modificable(id_partido)
    if partido["estado"] != "programado":
        raise ReglaError("El partido ya está marcado como jugado.")
    for id_equipo in (partido["id_equipo_local"], partido["id_equipo_visitante"]):
        n = consultar_uno("SELECT COUNT(*) AS n FROM planilla_partido WHERE id_partido = %s AND id_equipo = %s",
                          (id_partido, id_equipo))["n"]
        if n == 0:
            raise ReglaError("Cada equipo debe tener al menos un jugador en la planilla.")
    ejecutar("UPDATE partido SET estado = 'jugado' WHERE id_partido = %s", (id_partido,))


# ------------------------------------------------------------------- sanciones
def recalcular_sanciones(ci, id_torneo):
    """Sanciones AUTOMÁTICAS de un jugador, a partir de todas sus tarjetas en la edición:
         - cada roja               -> 1 fecha de suspensión
         - cada 3 amarillas (3, 6) -> 1 fecha de suspensión
       La suspensión rige desde la fecha siguiente a la del partido de la tarjeta.
       Se borran y se vuelven a generar (así quedan bien aunque se corrija una tarjeta).
       Las sanciones disciplinarias (id_tarjeta NULL) no se tocan."""
    ejecutar("DELETE FROM sancion_jugador WHERE ci_jugador = %s AND id_torneo = %s AND id_tarjeta IS NOT NULL",
             (ci, id_torneo))
    tarjetas = consultar(
        """SELECT t.id_tarjeta, t.color, p.numero_fecha
             FROM tarjeta t JOIN partido p ON p.id_partido = t.id_partido
            WHERE t.ci_jugador = %s AND p.id_torneo = %s
            ORDER BY p.numero_fecha, p.dia, p.id_turno, t.minuto, t.id_tarjeta""", (ci, id_torneo))
    amarillas = 0
    for t in tarjetas:
        motivo = None
        if t["color"] == "roja":
            motivo = "roja"
        else:
            amarillas += 1
            if amarillas % 3 == 0:
                motivo = "acumulacion_amarillas"
        if motivo:
            ejecutar(
                """INSERT INTO sancion_jugador (ci_jugador, id_torneo, motivo, numero_fecha_inicio,
                                                cantidad_fechas, id_tarjeta)
                   VALUES (%s, %s, %s, %s, 1, %s)""",
                (ci, id_torneo, motivo, t["numero_fecha"] + 1, t["id_tarjeta"]))


def validar_sancion_disciplinaria(id_torneo, ci):
    if get_torneo(id_torneo)["estado"] == "finalizado":
        raise ReglaError("El torneo está finalizado.")
    en_plantel = consultar_uno(
        "SELECT 1 AS x FROM equipo_jugador_torneo WHERE ci_jugador = %s AND id_torneo = %s", (ci, id_torneo))
    if en_plantel is None:
        raise ReglaError("El jugador no integra ningún plantel de esta edición.")


def exigir_sancion_disciplinaria(id_sancion):
    s = consultar_uno("SELECT * FROM sancion_jugador WHERE id_sancion = %s", (id_sancion,))
    if s is None:
        raise ReglaError("La sanción no existe.")
    if s["id_tarjeta"] is not None:
        raise ReglaError("Las sanciones automáticas se generan solas a partir de las tarjetas: "
                         "para cambiarlas hay que corregir la tarjeta.")
    return s
