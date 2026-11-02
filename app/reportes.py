"""Reportes. Cada reporte tiene un título, una descripción y una o más consultas SQL.
Todas reciben el parámetro %(torneo)s (id de la edición elegida).
Los alias entre `comillas` son los títulos de las columnas que ve el usuario.
"""

# Resultado de un partido desde la perspectiva de cada equipo (se usa en la tabla de posiciones):
# cada partido jugado aparece dos veces, una por equipo, con sus goles a favor (gf) y en contra (gc).
_PARTIDOS_POR_EQUIPO = """
    SELECT id_equipo_local AS id_equipo, goles_local AS gf, goles_visitante AS gc
      FROM v_resultado_partido WHERE id_torneo = %(torneo)s AND estado = 'jugado'
    UNION ALL
    SELECT id_equipo_visitante, goles_visitante, goles_local
      FROM v_resultado_partido WHERE id_torneo = %(torneo)s AND estado = 'jugado'
"""

REPORTES = [
    {
        "slug": "posiciones",
        "titulo": "Tabla de posiciones",
        "descripcion": "Ordenada por puntos, luego diferencia de goles y luego goles a favor.",
        "consultas": [("", f"""
            SELECT e.nombre AS `Equipo`,
                   COUNT(r.gf) AS `PJ`,
                   COALESCE(SUM(r.gf > r.gc), 0) AS `PG`,
                   COALESCE(SUM(r.gf = r.gc), 0) AS `PE`,
                   COALESCE(SUM(r.gf < r.gc), 0) AS `PP`,
                   COALESCE(SUM(r.gf), 0) AS `GF`,
                   COALESCE(SUM(r.gc), 0) AS `GC`,
                   COALESCE(SUM(r.gf - r.gc), 0) AS `DG`,
                   COALESCE(SUM(CASE WHEN r.gf > r.gc THEN 3 WHEN r.gf = r.gc THEN 1 ELSE 0 END), 0) AS `Puntos`
              FROM equipo e
              LEFT JOIN ({_PARTIDOS_POR_EQUIPO}) r ON r.id_equipo = e.id_equipo
             WHERE e.id_torneo = %(torneo)s
             GROUP BY e.id_equipo, e.nombre
             ORDER BY `Puntos` DESC, `DG` DESC, `GF` DESC, e.nombre""")],
    },
    {
        "slug": "goleadores",
        "titulo": "Tabla de goleadores (top 10)",
        "descripcion": "Los autogoles no cuentan para el goleador.",
        "consultas": [("", """
            SELECT j.nombre AS `Nombre`, j.apellido AS `Apellido`, e.nombre AS `Equipo`, COUNT(*) AS `Goles`
              FROM gol g
              JOIN partido p          ON p.id_partido = g.id_partido
              JOIN planilla_partido pl ON pl.id_partido = g.id_partido AND pl.ci_jugador = g.ci_jugador
              JOIN equipo e           ON e.id_equipo = pl.id_equipo
              JOIN jugador j          ON j.ci = g.ci_jugador
             WHERE p.id_torneo = %(torneo)s AND g.autogol = 0
             GROUP BY j.ci, j.nombre, j.apellido, e.nombre
             ORDER BY `Goles` DESC, j.apellido
             LIMIT 10""")],
    },
    {
        "slug": "fairplay",
        "titulo": "Fair play por equipo",
        "descripcion": "1 punto por amarilla y 3 por roja. Gana el de menor puntaje.",
        "consultas": [("", """
            SELECT e.nombre AS `Equipo`,
                   COALESCE(SUM(t.color = 'amarilla'), 0) AS `Amarillas`,
                   COALESCE(SUM(t.color = 'roja'), 0) AS `Rojas`,
                   COALESCE(SUM(t.color = 'amarilla'), 0) + 3 * COALESCE(SUM(t.color = 'roja'), 0) AS `Puntaje`
              FROM equipo e
              LEFT JOIN planilla_partido pl ON pl.id_equipo = e.id_equipo
              LEFT JOIN tarjeta t ON t.id_partido = pl.id_partido AND t.ci_jugador = pl.ci_jugador
             WHERE e.id_torneo = %(torneo)s
             GROUP BY e.id_equipo, e.nombre
             ORDER BY `Puntaje`, e.nombre""")],
    },
    {
        "slug": "promedio-goles",
        "titulo": "Promedio de goles por partido",
        "descripcion": "Solo partidos jugados: por fecha y en toda la edición.",
        "consultas": [
            ("Por fecha", """
                SELECT numero_fecha AS `Fecha`, COUNT(*) AS `Partidos`,
                       SUM(goles_local + goles_visitante) AS `Goles`,
                       ROUND(AVG(goles_local + goles_visitante), 2) AS `Promedio`
                  FROM v_resultado_partido
                 WHERE id_torneo = %(torneo)s AND estado = 'jugado'
                 GROUP BY numero_fecha ORDER BY numero_fecha"""),
            ("En toda la edición", """
                SELECT COUNT(*) AS `Partidos`,
                       COALESCE(SUM(goles_local + goles_visitante), 0) AS `Goles`,
                       ROUND(AVG(goles_local + goles_visitante), 2) AS `Promedio`
                  FROM v_resultado_partido
                 WHERE id_torneo = %(torneo)s AND estado = 'jugado'"""),
        ],
    },
    {
        "slug": "canchas-turnos",
        "titulo": "Canchas y turnos más utilizados",
        "descripcion": "Cuenta los partidos jugados y programados (no los cancelados ni postergados).",
        "consultas": [
            ("Canchas", """
                SELECT c.nombre AS `Complejo`, p.nombre_cancha AS `Cancha`, COUNT(*) AS `Partidos`
                  FROM partido p JOIN complejo c ON c.id_complejo = p.id_complejo
                 WHERE p.id_torneo = %(torneo)s AND p.estado IN ('jugado','programado')
                 GROUP BY c.id_complejo, c.nombre, p.nombre_cancha
                 ORDER BY `Partidos` DESC, c.nombre, p.nombre_cancha"""),
            ("Turnos", """
                SELECT LEFT(t.hora_inicio, 5) AS `Desde`, LEFT(t.hora_fin, 5) AS `Hasta`,
                       COUNT(*) AS `Partidos`
                  FROM partido p JOIN turno t ON t.id_turno = p.id_turno
                 WHERE p.id_torneo = %(torneo)s AND p.estado IN ('jugado','programado')
                 GROUP BY t.id_turno, t.hora_inicio, t.hora_fin
                 ORDER BY `Partidos` DESC, t.hora_inicio"""),
        ],
    },
    {
        "slug": "jugadores-facultad-tipo",
        "titulo": "Jugadores por facultad y tipo",
        "descripcion": "Todos los jugadores registrados (no depende de la edición).",
        "consultas": [("", """
            SELECT f.nombre AS `Facultad`,
                   COALESCE(SUM(j.tipo = 'grado'), 0) AS `Grado`,
                   COALESCE(SUM(j.tipo = 'posgrado'), 0) AS `Posgrado`,
                   COALESCE(SUM(j.tipo = 'docente'), 0) AS `Docente`,
                   COALESCE(SUM(j.tipo = 'funcionario'), 0) AS `Funcionario`,
                   COUNT(j.ci) AS `Total`
              FROM facultad f LEFT JOIN jugador j ON j.id_facultad = f.id_facultad
             GROUP BY f.id_facultad, f.nombre
             ORDER BY f.nombre""")],
    },
    {
        "slug": "sin-planilla",
        "titulo": "Inscriptos que nunca figuraron en una planilla",
        "descripcion": "Jugadores del plantel que no jugaron ningún partido de la edición.",
        "consultas": [("", """
            SELECT j.ci AS `Cédula`, j.nombre AS `Nombre`, j.apellido AS `Apellido`, e.nombre AS `Equipo`
              FROM equipo_jugador_torneo ejt
              JOIN jugador j ON j.ci = ejt.ci_jugador
              JOIN equipo e  ON e.id_equipo = ejt.id_equipo
             WHERE ejt.id_torneo = %(torneo)s
               AND NOT EXISTS (SELECT 1 FROM planilla_partido pl
                                 JOIN partido p ON p.id_partido = pl.id_partido
                                WHERE pl.ci_jugador = ejt.ci_jugador AND p.id_torneo = ejt.id_torneo)
             ORDER BY e.nombre, j.apellido""")],
    },
    {
        "slug": "sanciones",
        "titulo": "Sanciones por equipo y motivo",
        "descripcion": "Cantidad de sanciones de cada equipo, separadas por motivo.",
        "consultas": [("", """
            SELECT e.nombre AS `Equipo`, s.motivo AS `Motivo`, COUNT(*) AS `Sanciones`
              FROM sancion_jugador s
              JOIN equipo_jugador_torneo ejt ON ejt.ci_jugador = s.ci_jugador AND ejt.id_torneo = s.id_torneo
              JOIN equipo e ON e.id_equipo = ejt.id_equipo
             WHERE s.id_torneo = %(torneo)s
             GROUP BY e.id_equipo, e.nombre, s.motivo
             ORDER BY e.nombre, s.motivo""")],
    },
    {
        "slug": "estados-partidos",
        "titulo": "Partidos jugados vs. postergados/cancelados",
        "descripcion": "Porcentaje de partidos según su estado.",
        "consultas": [("", """
            SELECT estado AS `Estado`, COUNT(*) AS `Cantidad`,
                   ROUND(100 * COUNT(*) / (SELECT COUNT(*) FROM partido WHERE id_torneo = %(torneo)s), 1) AS `Porcentaje`
              FROM partido WHERE id_torneo = %(torneo)s
             GROUP BY estado ORDER BY `Cantidad` DESC""")],
    },
    # ---- Las 3 consultas sugeridas por nosotros ----
    {
        "slug": "fixture",
        "titulo": "Fixture con resultados (propia 1)",
        "descripcion": "Todos los partidos por fecha, con día, horario, cancha y resultado.",
        "consultas": [("", """
            SELECT r.numero_fecha AS `Fecha`, r.dia AS `Día`, LEFT(t.hora_inicio, 5) AS `Hora`,
                   el.nombre AS `Local`,
                   CASE WHEN r.estado = 'jugado' THEN CONCAT(r.goles_local, ' - ', r.goles_visitante) ELSE 'vs' END AS `Resultado`,
                   ev.nombre AS `Visitante`,
                   CONCAT(c.nombre, ' / ', r.nombre_cancha) AS `Cancha`, r.estado AS `Estado`
              FROM v_resultado_partido r
              JOIN equipo el  ON el.id_equipo = r.id_equipo_local
              JOIN equipo ev  ON ev.id_equipo = r.id_equipo_visitante
              JOIN turno t    ON t.id_turno = r.id_turno
              JOIN complejo c ON c.id_complejo = r.id_complejo
             WHERE r.id_torneo = %(torneo)s
             ORDER BY r.numero_fecha, r.dia, t.hora_inicio""")],
    },
    {
        "slug": "goleadas",
        "titulo": "Mayores goleadas (propia 2)",
        "descripcion": "Los 5 partidos jugados con mayor diferencia de goles.",
        "consultas": [("", """
            SELECT r.numero_fecha AS `Fecha`, el.nombre AS `Local`,
                   CONCAT(r.goles_local, ' - ', r.goles_visitante) AS `Resultado`, ev.nombre AS `Visitante`,
                   ABS(r.goles_local - r.goles_visitante) AS `Diferencia`
              FROM v_resultado_partido r
              JOIN equipo el ON el.id_equipo = r.id_equipo_local
              JOIN equipo ev ON ev.id_equipo = r.id_equipo_visitante
             WHERE r.id_torneo = %(torneo)s AND r.estado = 'jugado'
             ORDER BY `Diferencia` DESC, r.numero_fecha
             LIMIT 5""")],
    },
    {
        "slug": "tarjetas-jugador",
        "titulo": "Jugadores con más tarjetas (propia 3)",
        "descripcion": "Jugadores con al menos una tarjeta, de más a menos.",
        "consultas": [("", """
            SELECT j.nombre AS `Nombre`, j.apellido AS `Apellido`, e.nombre AS `Equipo`,
                   SUM(t.color = 'amarilla') AS `Amarillas`, SUM(t.color = 'roja') AS `Rojas`
              FROM tarjeta t
              JOIN partido p           ON p.id_partido = t.id_partido
              JOIN planilla_partido pl ON pl.id_partido = t.id_partido AND pl.ci_jugador = t.ci_jugador
              JOIN equipo e            ON e.id_equipo = pl.id_equipo
              JOIN jugador j           ON j.ci = t.ci_jugador
             WHERE p.id_torneo = %(torneo)s
             GROUP BY j.ci, j.nombre, j.apellido, e.nombre
             ORDER BY (SUM(t.color = 'amarilla') + 3 * SUM(t.color = 'roja')) DESC, j.apellido""")],
    },
]

POR_SLUG = {r["slug"]: r for r in REPORTES}
