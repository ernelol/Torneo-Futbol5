-- =====================================================================
-- 02_datos.sql: datos maestros y datos de prueba
-- =====================================================================
-- Contenido: 1 torneo en curso, 6 equipos, 3 fechas jugadas (9 partidos),
-- una fecha 4 mixta (pendiente de planilla / postergado / cancelado) y
-- fechas 5 y 6 programadas. Alcanza para que los 12 reportes devuelvan datos.
--
-- Los datos cumplen TODAS las reglas del torneo (por ejemplo: ningún
-- suspendido figura en una planilla de las fechas que abarca su sanción).
--
-- Usuarios de la aplicación (contraseña guardada como SHA-256):
--   admin@ucu.edu.uy       / admin123       (administrador)
--   planillero@ucu.edu.uy  / planillero123  (planillero)
-- =====================================================================

SET NAMES utf8mb4;
USE torneo_f5;

INSERT INTO login (correo, contrasena, rol) VALUES
  ('admin@ucu.edu.uy',      SHA2('admin123', 256),      'administrador'),
  ('planillero@ucu.edu.uy', SHA2('planillero123', 256), 'planillero');

-- Turnos de una hora entre las 18:00 y las 23:00
INSERT INTO turno (id_turno, hora_inicio, hora_fin) VALUES
  (1, '18:00:00', '19:00:00'), (2, '19:00:00', '20:00:00'), (3, '20:00:00', '21:00:00'),
  (4, '21:00:00', '22:00:00'), (5, '22:00:00', '23:00:00');

INSERT INTO facultad (id_facultad, nombre) VALUES
  (1, 'Ingeniería y Tecnologías'),
  (2, 'Ciencias Empresariales'),
  (3, 'Derecho'),
  (4, 'Ciencias Humanas'),
  (5, 'Psicología'),
  (6, 'Ciencias de la Salud');

INSERT INTO complejo (id_complejo, nombre, direccion, departamento) VALUES
  (1, 'Complejo Fútbol 5 Cordón',   'Av. Italia 1234',  'Montevideo'),
  (2, 'Arena Pocitos',              'Bulevar España 2200', 'Montevideo'),
  (3, 'Complejo Costa Azul',        'Rambla 1500',      'Canelones');

INSERT INTO cancha (nombre_cancha, id_complejo, superficie, techada) VALUES
  ('Cancha 1', 1, 'sintetico', FALSE),
  ('Cancha 2', 1, 'sintetico', FALSE),
  ('Cancha A', 2, 'parquet',   TRUE),
  ('Cancha B', 2, 'sintetico', FALSE),
  ('Cancha 1', 3, 'sintetico', TRUE);

INSERT INTO torneo (id_torneo, nombre, anio, semestre, fecha_inicio, fecha_fin, estado) VALUES
  (1, 'Torneo Interfacultades de Fútbol 5 2026-2', 2026, 2, '2026-09-01', '2026-12-15', 'en_curso');

-- Jugadores (ci sin puntos ni guión)
INSERT INTO jugador (ci, nombre, apellido, email, fecha_nacimiento, id_facultad, tipo) VALUES
  (4501011, 'Mateo', 'Rodríguez', 'Mateo.Rodríguez@correo.ucu.edu.uy', '1999-01-03', 1, 'grado'),
  (4501048, 'Santiago', 'Techera', 'Santiago.Techera@correo.ucu.edu.uy', '2000-02-04', 1, 'grado'),
  (4501085, 'Valentina', 'Olivera', 'Valentina.Olivera@correo.ucu.edu.uy', '2001-03-05', 1, 'grado'),
  (4501122, 'Lucía', 'Duarte', 'Lucía.Duarte@correo.ucu.edu.uy', '2002-04-06', 1, 'posgrado'),
  (4501159, 'Martín', 'Cardozo', 'Martín.Cardozo@correo.ucu.edu.uy', '2003-05-07', 1, 'grado'),
  (4501196, 'Camila', 'Haedo', 'Camila.Haedo@ucu.edu.uy', '1980-06-08', 1, 'funcionario'),
  (4501233, 'Joaquín', 'Fernández', 'Joaquín.Fernández@ucu.edu.uy', '1981-07-09', 1, 'docente'),
  (4502011, 'Sofía', 'Ferreira', 'Sofía.Ferreira@correo.ucu.edu.uy', '2006-08-10', 2, 'grado'),
  (4502048, 'Nicolás', 'Rivero', 'Nicolás.Rivero@correo.ucu.edu.uy', '1999-09-11', 2, 'grado'),
  (4502085, 'Agustina', 'Pereira', 'Agustina.Pereira@correo.ucu.edu.uy', '2000-10-12', 2, 'grado'),
  (4502122, 'Tomás', 'Esteves', 'Tomás.Esteves@correo.ucu.edu.uy', '2001-11-13', 2, 'grado'),
  (4502159, 'Florencia', 'Brum', 'Florencia.Brum@correo.ucu.edu.uy', '2002-12-14', 2, 'posgrado'),
  (4502196, 'Facundo', 'Silva', 'Facundo.Silva@correo.ucu.edu.uy', '2003-01-15', 2, 'grado'),
  (4503011, 'Micaela', 'Núñez', 'Micaela.Núñez@correo.ucu.edu.uy', '2004-02-16', 3, 'grado'),
  (4503048, 'Bruno', 'Sosa', 'Bruno.Sosa@correo.ucu.edu.uy', '2005-03-17', 3, 'grado'),
  (4503085, 'Julieta', 'Castro', 'Julieta.Castro@correo.ucu.edu.uy', '2006-04-18', 3, 'grado'),
  (4503122, 'Emiliano', 'Rocha', 'Emiliano.Rocha@correo.ucu.edu.uy', '1999-05-19', 3, 'grado'),
  (4503159, 'Carolina', 'Zeballos', 'Carolina.Zeballos@correo.ucu.edu.uy', '2000-06-20', 3, 'grado'),
  (4503196, 'Diego', 'Martínez', 'Diego.Martínez@correo.ucu.edu.uy', '2001-07-21', 3, 'grado'),
  (4503233, 'Paula', 'Píriz', 'Paula.Píriz@ucu.edu.uy', '1982-08-22', 3, 'docente'),
  (4504011, 'Rodrigo', 'Vázquez', 'Rodrigo.Vázquez@correo.ucu.edu.uy', '2003-09-03', 4, 'grado'),
  (4504048, 'Natalia', 'Mendoza', 'Natalia.Mendoza@correo.ucu.edu.uy', '2004-10-04', 4, 'grado'),
  (4504085, 'Gonzalo', 'Márquez', 'Gonzalo.Márquez@correo.ucu.edu.uy', '2005-11-05', 4, 'grado'),
  (4504122, 'Romina', 'González', 'Romina.González@correo.ucu.edu.uy', '2006-12-06', 4, 'posgrado'),
  (4504159, 'Federico', 'Cabrera', 'Federico.Cabrera@correo.ucu.edu.uy', '1999-01-07', 4, 'grado'),
  (4504196, 'Belén', 'Machado', 'Belén.Machado@ucu.edu.uy', '1976-02-08', 4, 'docente'),
  (4505011, 'Sebastián', 'Barrios', 'Sebastián.Barrios@correo.ucu.edu.uy', '2001-03-09', 5, 'grado'),
  (4505048, 'Daniela', 'Ibarra', 'Daniela.Ibarra@correo.ucu.edu.uy', '2002-04-10', 5, 'grado'),
  (4505085, 'Ignacio', 'Cuello', 'Ignacio.Cuello@correo.ucu.edu.uy', '2003-05-11', 5, 'grado'),
  (4505122, 'Victoria', 'Pérez', 'Victoria.Pérez@correo.ucu.edu.uy', '2004-06-12', 5, 'grado'),
  (4505159, 'Andrés', 'Acosta', 'Andrés.Acosta@correo.ucu.edu.uy', '2005-07-13', 5, 'grado'),
  (4505196, 'Lorena', 'Correa', 'Lorena.Correa@ucu.edu.uy', '1982-08-14', 5, 'funcionario'),
  (4506011, 'Maximiliano', 'Gómez', 'Maximiliano.Gómez@correo.ucu.edu.uy', '1999-09-15', 6, 'grado'),
  (4506048, 'Pilar', 'Lemos', 'Pilar.Lemos@correo.ucu.edu.uy', '2000-10-16', 6, 'grado'),
  (4506085, 'Ramiro', 'Aguirre', 'Ramiro.Aguirre@correo.ucu.edu.uy', '2001-11-17', 6, 'posgrado'),
  (4506122, 'Cecilia', 'López', 'Cecilia.López@correo.ucu.edu.uy', '2002-12-18', 6, 'grado'),
  (4506159, 'Leandro', 'Suárez', 'Leandro.Suárez@correo.ucu.edu.uy', '2003-01-19', 6, 'grado'),
  (4506196, 'Mariana', 'Bentancor', 'Mariana.Bentancor@correo.ucu.edu.uy', '2004-02-20', 6, 'grado');

-- Equipos (el capitán es el jugador 0 de cada plantel)
INSERT INTO equipo (id_equipo, nombre, id_torneo, id_facultad, ci_capitan) VALUES
  (1, 'Ingeniería United', 1, 1, 4501011),
  (2, 'Empresariales FC', 1, 2, 4502011),
  (3, 'Derecho Atlético', 1, 3, 4503011),
  (4, 'Humanas Club', 1, 4, 4504011),
  (5, 'Psicología Sport', 1, 5, 4505011),
  (6, 'Salud Deportivo', 1, 6, 4506011);

-- Planteles (equipo_jugador_torneo)
INSERT INTO equipo_jugador_torneo (id_equipo, ci_jugador, id_torneo, numero_camiseta) VALUES
  (1, 4501011, 1, 10),
  (1, 4501048, 1, 7),
  (1, 4501085, 1, 9),
  (1, 4501122, 1, 5),
  (1, 4501159, 1, 11),
  (1, 4501196, 1, 3),
  (1, 4501233, 1, 4),
  (2, 4502011, 1, 10),
  (2, 4502048, 1, 7),
  (2, 4502085, 1, 9),
  (2, 4502122, 1, 5),
  (2, 4502159, 1, 11),
  (2, 4502196, 1, 3),
  (3, 4503011, 1, 10),
  (3, 4503048, 1, 7),
  (3, 4503085, 1, 9),
  (3, 4503122, 1, 5),
  (3, 4503159, 1, 11),
  (3, 4503196, 1, 3),
  (3, 4503233, 1, 4),
  (4, 4504011, 1, 10),
  (4, 4504048, 1, 7),
  (4, 4504085, 1, 9),
  (4, 4504122, 1, 5),
  (4, 4504159, 1, 11),
  (4, 4504196, 1, 3),
  (5, 4505011, 1, 10),
  (5, 4505048, 1, 7),
  (5, 4505085, 1, 9),
  (5, 4505122, 1, 5),
  (5, 4505159, 1, 11),
  (5, 4505196, 1, 3),
  (6, 4506011, 1, 10),
  (6, 4506048, 1, 7),
  (6, 4506085, 1, 9),
  (6, 4506122, 1, 5),
  (6, 4506159, 1, 11),
  (6, 4506196, 1, 3);

-- Partidos
INSERT INTO partido (id_partido, id_torneo, numero_fecha, id_equipo_local, id_equipo_visitante, dia, id_turno, nombre_cancha, id_complejo, estado) VALUES
  (1, 1, 1, 1, 6, '2026-09-15', 1, 'Cancha 1', 1, 'jugado'),
  (2, 1, 1, 2, 5, '2026-09-15', 1, 'Cancha A', 2, 'jugado'),
  (3, 1, 1, 3, 4, '2026-09-15', 2, 'Cancha 1', 1, 'jugado'),
  (4, 1, 2, 1, 5, '2026-09-29', 2, 'Cancha 1', 1, 'jugado'),
  (5, 1, 2, 6, 4, '2026-09-29', 2, 'Cancha A', 2, 'jugado'),
  (6, 1, 2, 2, 3, '2026-09-29', 3, 'Cancha 2', 1, 'jugado'),
  (7, 1, 3, 1, 4, '2026-10-13', 1, 'Cancha 1', 3, 'jugado'),
  (8, 1, 3, 5, 3, '2026-10-13', 2, 'Cancha B', 2, 'jugado'),
  (9, 1, 3, 6, 2, '2026-10-13', 3, 'Cancha 1', 3, 'jugado'),
  (10, 1, 4, 4, 2, '2026-10-27', 2, 'Cancha 2', 1, 'programado'),
  (11, 1, 4, 5, 6, '2026-10-27', 3, 'Cancha A', 2, 'postergado'),
  (12, 1, 4, 1, 3, '2026-10-27', 1, 'Cancha 1', 1, 'cancelado'),
  (13, 1, 5, 1, 2, '2026-11-17', 1, 'Cancha 1', 1, 'programado'),
  (14, 1, 5, 3, 6, '2026-11-17', 2, 'Cancha A', 2, 'programado'),
  (15, 1, 5, 4, 5, '2026-11-17', 3, 'Cancha 1', 3, 'programado'),
  (16, 1, 6, 1, 3, '2026-11-24', 2, 'Cancha 1', 1, 'programado');

-- Planillas de los partidos jugados
INSERT INTO planilla_partido (id_partido, ci_jugador, id_equipo) VALUES
  (1, 4501011, 1),
  (1, 4501048, 1),
  (1, 4501085, 1),
  (1, 4501122, 1),
  (1, 4501159, 1),
  (1, 4506011, 6),
  (1, 4506048, 6),
  (1, 4506085, 6),
  (1, 4506122, 6),
  (1, 4506159, 6),
  (2, 4502011, 2),
  (2, 4502048, 2),
  (2, 4502085, 2),
  (2, 4502122, 2),
  (2, 4502159, 2),
  (2, 4505011, 5),
  (2, 4505048, 5),
  (2, 4505085, 5),
  (2, 4505122, 5),
  (2, 4505159, 5),
  (3, 4503011, 3),
  (3, 4503048, 3),
  (3, 4503085, 3),
  (3, 4503122, 3),
  (3, 4503159, 3),
  (3, 4504011, 4),
  (3, 4504048, 4),
  (3, 4504085, 4),
  (3, 4504122, 4),
  (3, 4504159, 4),
  (4, 4501011, 1),
  (4, 4501048, 1),
  (4, 4501085, 1),
  (4, 4501122, 1),
  (4, 4501196, 1),
  (4, 4505011, 5),
  (4, 4505048, 5),
  (4, 4505122, 5),
  (4, 4505159, 5),
  (4, 4505196, 5),
  (5, 4506011, 6),
  (5, 4506048, 6),
  (5, 4506085, 6),
  (5, 4506122, 6),
  (5, 4506196, 6),
  (5, 4504011, 4),
  (5, 4504048, 4),
  (5, 4504085, 4),
  (5, 4504122, 4),
  (5, 4504159, 4),
  (6, 4502011, 2),
  (6, 4502048, 2),
  (6, 4502085, 2),
  (6, 4502122, 2),
  (6, 4502159, 2),
  (6, 4503011, 3),
  (6, 4503048, 3),
  (6, 4503085, 3),
  (6, 4503122, 3),
  (6, 4503233, 3),
  (7, 4501011, 1),
  (7, 4501048, 1),
  (7, 4501085, 1),
  (7, 4501122, 1),
  (7, 4501159, 1),
  (7, 4504011, 4),
  (7, 4504048, 4),
  (7, 4504085, 4),
  (7, 4504122, 4),
  (7, 4504159, 4),
  (8, 4505011, 5),
  (8, 4505048, 5),
  (8, 4505085, 5),
  (8, 4505122, 5),
  (8, 4505159, 5),
  (8, 4503011, 3),
  (8, 4503048, 3),
  (8, 4503085, 3),
  (8, 4503122, 3),
  (8, 4503159, 3),
  (9, 4506011, 6),
  (9, 4506048, 6),
  (9, 4506085, 6),
  (9, 4506122, 6),
  (9, 4506159, 6),
  (9, 4502011, 2),
  (9, 4502048, 2),
  (9, 4502085, 2),
  (9, 4502122, 2),
  (9, 4502196, 2);

-- Goles (autogol = 1 se acredita al rival)
INSERT INTO gol (id_gol, id_partido, ci_jugador, minuto, autogol) VALUES
  (1, 1, 4501011, 8, FALSE),
  (2, 1, 4501085, 25, FALSE),
  (3, 1, 4501011, 41, FALSE),
  (4, 1, 4506122, 33, FALSE),
  (5, 2, 4502011, 12, FALSE),
  (6, 2, 4505048, 20, FALSE),
  (7, 2, 4502122, 50, FALSE),
  (8, 2, 4505159, 55, FALSE),
  (9, 3, 4504048, 44, FALSE),
  (10, 4, 4501085, 27, FALSE),
  (11, 5, 4504048, 5, FALSE),
  (12, 5, 4506011, 14, FALSE),
  (13, 5, 4504048, 22, FALSE),
  (14, 5, 4506085, 31, FALSE),
  (15, 5, 4504122, 47, FALSE),
  (16, 5, 4504159, 58, FALSE),
  (17, 6, 4502011, 9, FALSE),
  (18, 6, 4502122, 33, FALSE),
  (19, 6, 4503085, 49, TRUE),
  (20, 6, 4503122, 52, FALSE),
  (21, 7, 4501011, 11, FALSE),
  (22, 7, 4504048, 19, FALSE),
  (23, 7, 4501122, 36, FALSE),
  (24, 7, 4504122, 57, FALSE),
  (25, 8, 4505011, 7, FALSE),
  (26, 8, 4503048, 15, FALSE),
  (27, 8, 4503048, 30, FALSE),
  (28, 8, 4503122, 48, FALSE),
  (29, 9, 4502011, 18, FALSE),
  (30, 9, 4502085, 44, FALSE);

-- Tarjetas
INSERT INTO tarjeta (id_tarjeta, id_partido, ci_jugador, minuto, color) VALUES
  (1, 1, 4506048, 20, 'amarilla'),
  (2, 2, 4505085, 30, 'roja'),
  (3, 2, 4502048, 35, 'amarilla'),
  (4, 3, 4503011, 15, 'amarilla'),
  (5, 4, 4501048, 10, 'amarilla'),
  (6, 4, 4505048, 38, 'amarilla'),
  (7, 5, 4504011, 28, 'amarilla'),
  (8, 5, 4506048, 40, 'amarilla'),
  (9, 6, 4502048, 18, 'amarilla'),
  (10, 6, 4503011, 45, 'amarilla'),
  (11, 7, 4501048, 24, 'amarilla'),
  (12, 7, 4504011, 50, 'amarilla'),
  (13, 8, 4503011, 21, 'amarilla'),
  (14, 8, 4505048, 40, 'roja'),
  (15, 9, 4506048, 33, 'amarilla');

-- Sanciones: las automáticas referencian la tarjeta que las originó;
-- la disciplinaria (última) fue cargada por la organización.
INSERT INTO sancion_jugador (ci_jugador, id_torneo, motivo, numero_fecha_inicio, cantidad_fechas, id_tarjeta) VALUES
  (4505085, 1, 'roja', 2, 1, 2),
  (4503011, 1, 'acumulacion_amarillas', 4, 1, 13),
  (4504085, 1, 'disciplinaria', 4, 2, NULL),
  (4505048, 1, 'roja', 4, 1, 14),
  (4506048, 1, 'acumulacion_amarillas', 4, 1, 15);
