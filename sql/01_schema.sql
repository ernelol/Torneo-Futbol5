-- =====================================================================
-- Torneo Interfacultades de Fútbol 5 - UCU
-- 01_schema.sql: base de datos, tablas, restricciones, vistas y usuarios
-- =====================================================================
-- Este script se ejecuta solo, la primera vez que levanta el contenedor
-- de MySQL (carpeta /docker-entrypoint-initdb.d). Corre ANTES que
-- 02_datos.sql porque los archivos se ejecutan en orden alfabético.
-- =====================================================================

SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS torneo_f5
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE torneo_f5;

-- ---------------------------------------------------------------------
-- LOGIN: usuarios de la aplicación (no son usuarios de MySQL)
-- La contraseña se guarda como hash SHA-256 (64 caracteres hex), nunca en claro.
-- ---------------------------------------------------------------------
CREATE TABLE login (
    correo      VARCHAR(100) NOT NULL,
    contrasena  CHAR(64)     NOT NULL,
    rol         ENUM('administrador','planillero') NOT NULL,
    PRIMARY KEY (correo),
    CONSTRAINT ck_login_correo CHECK (correo LIKE '%_@_%._%')
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- FACULTAD
-- ---------------------------------------------------------------------
CREATE TABLE facultad (
    id_facultad INT          NOT NULL AUTO_INCREMENT,
    nombre      VARCHAR(80)  NOT NULL,
    PRIMARY KEY (id_facultad),
    UNIQUE KEY uq_facultad_nombre (nombre),
    CONSTRAINT ck_facultad_nombre CHECK (CHAR_LENGTH(TRIM(nombre)) > 0)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- JUGADOR
-- ci se guarda como número sin puntos ni guión (6 a 8 dígitos).
-- ---------------------------------------------------------------------
CREATE TABLE jugador (
    ci               INT          NOT NULL,
    nombre           VARCHAR(60)  NOT NULL,
    apellido         VARCHAR(60)  NOT NULL,
    email            VARCHAR(100) NOT NULL,
    fecha_nacimiento DATE         NOT NULL,
    id_facultad      INT          NOT NULL,
    tipo             ENUM('grado','posgrado','docente','funcionario') NOT NULL,
    PRIMARY KEY (ci),
    UNIQUE KEY uq_jugador_email (email),
    CONSTRAINT fk_jugador_facultad FOREIGN KEY (id_facultad)
        REFERENCES facultad (id_facultad),
    CONSTRAINT ck_jugador_ci     CHECK (ci BETWEEN 100000 AND 99999999),
    CONSTRAINT ck_jugador_email  CHECK (email LIKE '%_@_%._%'),
    CONSTRAINT ck_jugador_nac    CHECK (fecha_nacimiento >= '1920-01-01')
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- TORNEO (una edición por semestre)
-- ---------------------------------------------------------------------
CREATE TABLE torneo (
    id_torneo    INT          NOT NULL AUTO_INCREMENT,
    nombre       VARCHAR(100) NOT NULL,
    anio         SMALLINT     NOT NULL,
    semestre     TINYINT      NOT NULL,
    fecha_inicio DATE         NOT NULL,
    fecha_fin    DATE         NOT NULL,
    estado       ENUM('inscripcion','en_curso','finalizado') NOT NULL DEFAULT 'inscripcion',
    PRIMARY KEY (id_torneo),
    UNIQUE KEY uq_torneo_edicion (anio, semestre),
    CONSTRAINT ck_torneo_anio     CHECK (anio BETWEEN 2000 AND 2100),
    CONSTRAINT ck_torneo_semestre CHECK (semestre IN (1, 2)),
    CONSTRAINT ck_torneo_fechas   CHECK (fecha_fin >= fecha_inicio)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- EQUIPO
-- ci_capitan puede ser NULL al crear el equipo (todavía no tiene plantel);
-- la aplicación exige que esté definido antes de iniciar el torneo.
-- UNIQUE (id_equipo, id_torneo) existe para poder armar claves foráneas
-- compuestas que garanticen que todo lo que cuelga de un equipo es de su torneo.
-- ---------------------------------------------------------------------
CREATE TABLE equipo (
    id_equipo   INT          NOT NULL AUTO_INCREMENT,
    nombre      VARCHAR(80)  NOT NULL,
    id_torneo   INT          NOT NULL,
    id_facultad INT          NOT NULL,
    ci_capitan  INT          NULL,
    PRIMARY KEY (id_equipo),
    UNIQUE KEY uq_equipo_torneo (id_equipo, id_torneo),
    UNIQUE KEY uq_equipo_nombre (id_torneo, nombre),
    CONSTRAINT fk_equipo_torneo   FOREIGN KEY (id_torneo)   REFERENCES torneo (id_torneo),
    CONSTRAINT fk_equipo_facultad FOREIGN KEY (id_facultad) REFERENCES facultad (id_facultad),
    CONSTRAINT fk_equipo_capitan  FOREIGN KEY (ci_capitan)  REFERENCES jugador (ci),
    CONSTRAINT ck_equipo_nombre   CHECK (CHAR_LENGTH(TRIM(nombre)) > 0)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- EQUIPO_JUGADOR_TORNEO (plantel)
-- UNIQUE (ci_jugador, id_torneo): un jugador no puede estar en dos equipos
-- de la misma edición. UNIQUE (id_equipo, numero_camiseta): camisetas únicas.
-- ---------------------------------------------------------------------
CREATE TABLE equipo_jugador_torneo (
    id_equipo       INT     NOT NULL,
    ci_jugador      INT     NOT NULL,
    id_torneo       INT     NOT NULL,
    numero_camiseta TINYINT NOT NULL,
    PRIMARY KEY (id_equipo, ci_jugador),
    UNIQUE KEY uq_plantel_jugador_torneo (ci_jugador, id_torneo),
    UNIQUE KEY uq_plantel_camiseta (id_equipo, numero_camiseta),
    CONSTRAINT fk_plantel_equipo  FOREIGN KEY (id_equipo, id_torneo)
        REFERENCES equipo (id_equipo, id_torneo) ON DELETE CASCADE,
    CONSTRAINT fk_plantel_jugador FOREIGN KEY (ci_jugador) REFERENCES jugador (ci),
    CONSTRAINT ck_plantel_camiseta CHECK (numero_camiseta BETWEEN 1 AND 99)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- COMPLEJO y CANCHA
-- ---------------------------------------------------------------------
CREATE TABLE complejo (
    id_complejo  INT          NOT NULL AUTO_INCREMENT,
    nombre       VARCHAR(80)  NOT NULL,
    direccion    VARCHAR(120) NOT NULL,
    departamento VARCHAR(40)  NOT NULL,
    PRIMARY KEY (id_complejo),
    UNIQUE KEY uq_complejo_nombre (nombre)
) ENGINE=InnoDB;

CREATE TABLE cancha (
    nombre_cancha VARCHAR(40) NOT NULL,
    id_complejo   INT         NOT NULL,
    superficie    ENUM('sintetico','parquet') NOT NULL,
    techada       BOOLEAN     NOT NULL DEFAULT FALSE,
    PRIMARY KEY (nombre_cancha, id_complejo),
    CONSTRAINT fk_cancha_complejo FOREIGN KEY (id_complejo)
        REFERENCES complejo (id_complejo)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- TURNO (bloques de una hora entre las 18:00 y las 23:00)
-- ---------------------------------------------------------------------
CREATE TABLE turno (
    id_turno    INT  NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin    TIME NOT NULL,
    PRIMARY KEY (id_turno),
    UNIQUE KEY uq_turno_inicio (hora_inicio),
    -- turnos de exactamente una hora, entre las 18:00 y las 23:00
    CONSTRAINT ck_turno_horas CHECK (hora_inicio >= '18:00:00' AND hora_fin <= '23:00:00'
                                     AND TIME_TO_SEC(hora_fin) - TIME_TO_SEC(hora_inicio) = 3600)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- PARTIDO
-- UNIQUE (dia, id_turno, cancha): una cancha no puede tener dos partidos
-- el mismo día y turno (regla garantizada también por la base).
-- Las FK compuestas con id_torneo garantizan que ambos equipos son de
-- la misma edición que el partido.
-- ---------------------------------------------------------------------
CREATE TABLE partido (
    id_partido          INT  NOT NULL AUTO_INCREMENT,
    id_torneo           INT  NOT NULL,
    numero_fecha        INT  NOT NULL,
    id_equipo_local     INT  NOT NULL,
    id_equipo_visitante INT  NOT NULL,
    dia                 DATE NOT NULL,
    id_turno            INT  NOT NULL,
    nombre_cancha       VARCHAR(40) NOT NULL,
    id_complejo         INT  NOT NULL,
    estado ENUM('programado','jugado','postergado','cancelado') NOT NULL DEFAULT 'programado',
    PRIMARY KEY (id_partido),
    UNIQUE KEY uq_partido_cancha_turno (dia, id_turno, nombre_cancha, id_complejo),
    CONSTRAINT fk_partido_torneo    FOREIGN KEY (id_torneo) REFERENCES torneo (id_torneo),
    CONSTRAINT fk_partido_local     FOREIGN KEY (id_equipo_local, id_torneo)
        REFERENCES equipo (id_equipo, id_torneo),
    CONSTRAINT fk_partido_visitante FOREIGN KEY (id_equipo_visitante, id_torneo)
        REFERENCES equipo (id_equipo, id_torneo),
    CONSTRAINT fk_partido_turno     FOREIGN KEY (id_turno) REFERENCES turno (id_turno),
    CONSTRAINT fk_partido_cancha    FOREIGN KEY (nombre_cancha, id_complejo)
        REFERENCES cancha (nombre_cancha, id_complejo),
    CONSTRAINT ck_partido_fecha     CHECK (numero_fecha >= 1),
    CONSTRAINT ck_partido_distintos CHECK (id_equipo_local <> id_equipo_visitante)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- PLANILLA_PARTIDO: jugadores que participaron de un partido.
-- La FK compuesta (id_equipo, ci_jugador) garantiza que el jugador
-- pertenece al plantel del equipo con el que figura en la planilla.
-- ---------------------------------------------------------------------
CREATE TABLE planilla_partido (
    id_partido INT NOT NULL,
    ci_jugador INT NOT NULL,
    id_equipo  INT NOT NULL,
    PRIMARY KEY (id_partido, ci_jugador),
    CONSTRAINT fk_planilla_partido FOREIGN KEY (id_partido) REFERENCES partido (id_partido),
    CONSTRAINT fk_planilla_plantel FOREIGN KEY (id_equipo, ci_jugador)
        REFERENCES equipo_jugador_torneo (id_equipo, ci_jugador)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- GOL y TARJETA: solo pueden existir para jugadores que figuran en la
-- planilla del partido (FK compuesta contra planilla_partido).
-- autogol = 1 significa que el gol se acredita al equipo rival.
-- ---------------------------------------------------------------------
CREATE TABLE gol (
    id_gol     INT     NOT NULL AUTO_INCREMENT,
    id_partido INT     NOT NULL,
    ci_jugador INT     NOT NULL,
    minuto     TINYINT NOT NULL,
    autogol    BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (id_gol),
    CONSTRAINT fk_gol_planilla FOREIGN KEY (id_partido, ci_jugador)
        REFERENCES planilla_partido (id_partido, ci_jugador),
    CONSTRAINT ck_gol_minuto CHECK (minuto BETWEEN 1 AND 60)
) ENGINE=InnoDB;

CREATE TABLE tarjeta (
    id_tarjeta INT     NOT NULL AUTO_INCREMENT,
    id_partido INT     NOT NULL,
    ci_jugador INT     NOT NULL,
    minuto     TINYINT NOT NULL,
    color      ENUM('amarilla','roja') NOT NULL,
    PRIMARY KEY (id_tarjeta),
    CONSTRAINT fk_tarjeta_planilla FOREIGN KEY (id_partido, ci_jugador)
        REFERENCES planilla_partido (id_partido, ci_jugador),
    CONSTRAINT ck_tarjeta_minuto CHECK (minuto BETWEEN 1 AND 60)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- SANCION_JUGADOR
-- Un jugador está suspendido en las fechas numero_fecha_inicio ...
-- numero_fecha_inicio + cantidad_fechas - 1.
-- id_tarjeta (campo agregado): tarjeta que originó una sanción automática.
-- Es NULL en las sanciones disciplinarias cargadas a mano.
-- ---------------------------------------------------------------------
CREATE TABLE sancion_jugador (
    id_sancion          INT NOT NULL AUTO_INCREMENT,
    ci_jugador          INT NOT NULL,
    id_torneo           INT NOT NULL,
    motivo ENUM('roja','acumulacion_amarillas','disciplinaria') NOT NULL,
    numero_fecha_inicio INT NOT NULL,
    cantidad_fechas     INT NOT NULL,
    id_tarjeta          INT NULL,
    PRIMARY KEY (id_sancion),
    UNIQUE KEY uq_sancion_tarjeta (id_tarjeta),
    CONSTRAINT fk_sancion_jugador FOREIGN KEY (ci_jugador) REFERENCES jugador (ci),
    CONSTRAINT fk_sancion_torneo  FOREIGN KEY (id_torneo)  REFERENCES torneo (id_torneo),
    CONSTRAINT fk_sancion_tarjeta FOREIGN KEY (id_tarjeta) REFERENCES tarjeta (id_tarjeta)
        ON DELETE CASCADE,
    CONSTRAINT ck_sancion_inicio   CHECK (numero_fecha_inicio >= 1),
    CONSTRAINT ck_sancion_cantidad CHECK (cantidad_fechas BETWEEN 1 AND 50)
) ENGINE=InnoDB;

-- =====================================================================
-- VISTAS: el resultado de un partido NO se guarda, se calcula a partir
-- de los goles (así nunca puede quedar inconsistente con ellos).
-- =====================================================================

-- A qué equipo se acredita cada gol:
--   gol normal -> al equipo del jugador que lo convirtió
--   autogol    -> al equipo rival
CREATE VIEW v_goles_acreditados AS
SELECT g.id_gol,
       g.id_partido,
       g.ci_jugador,
       CASE
           WHEN g.autogol = 0                       THEN pl.id_equipo
           WHEN pl.id_equipo = p.id_equipo_local    THEN p.id_equipo_visitante
           ELSE p.id_equipo_local
       END AS id_equipo_acreditado
FROM gol g
JOIN planilla_partido pl ON pl.id_partido = g.id_partido AND pl.ci_jugador = g.ci_jugador
JOIN partido p           ON p.id_partido  = g.id_partido;

-- Resultado de cada partido (goles local y visitante).
CREATE VIEW v_resultado_partido AS
SELECT p.id_partido, p.id_torneo, p.numero_fecha,
       p.id_equipo_local, p.id_equipo_visitante,
       p.dia, p.id_turno, p.nombre_cancha, p.id_complejo, p.estado,
       (SELECT COUNT(*) FROM v_goles_acreditados v
         WHERE v.id_partido = p.id_partido
           AND v.id_equipo_acreditado = p.id_equipo_local)     AS goles_local,
       (SELECT COUNT(*) FROM v_goles_acreditados v
         WHERE v.id_partido = p.id_partido
           AND v.id_equipo_acreditado = p.id_equipo_visitante) AS goles_visitante
FROM partido p;

-- =====================================================================
-- SEGURIDAD A NIVEL DE BASE DE DATOS
-- Tres usuarios de MySQL con privilegios mínimos (principio de
-- "menor privilegio"). La aplicación se conecta con uno u otro según
-- el rol del usuario logueado.
-- NOTA: contraseñas de desarrollo; en producción irían en variables
-- de entorno / secretos y serían distintas.
-- =====================================================================

CREATE USER IF NOT EXISTS 'auth_db'@'%'       IDENTIFIED BY 'auth_pass_2026';
CREATE USER IF NOT EXISTS 'admin_db'@'%'      IDENTIFIED BY 'admin_pass_2026';
CREATE USER IF NOT EXISTS 'planillero_db'@'%' IDENTIFIED BY 'planillero_pass_2026';

-- auth_db: solo puede leer la tabla login (se usa únicamente para iniciar sesión).
GRANT SELECT ON torneo_f5.login TO 'auth_db'@'%';

-- admin_db: gestiona todos los datos del torneo (CRUD), pero no puede
-- alterar la estructura (sin DROP/ALTER) ni ver la tabla login.
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_f5.facultad              TO 'admin_db'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_f5.jugador               TO 'admin_db'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_f5.torneo                TO 'admin_db'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_f5.equipo                TO 'admin_db'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_f5.equipo_jugador_torneo TO 'admin_db'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_f5.complejo              TO 'admin_db'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_f5.cancha                TO 'admin_db'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_f5.turno                 TO 'admin_db'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_f5.partido               TO 'admin_db'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_f5.planilla_partido      TO 'admin_db'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_f5.gol                   TO 'admin_db'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_f5.tarjeta               TO 'admin_db'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON torneo_f5.sancion_jugador       TO 'admin_db'@'%';
GRANT SELECT ON torneo_f5.v_goles_acreditados TO 'admin_db'@'%';
GRANT SELECT ON torneo_f5.v_resultado_partido TO 'admin_db'@'%';

-- planillero_db: solo lee datos de referencia y escribe planilla, goles
-- y tarjetas. Del partido solo puede modificar la columna "estado"
-- (para marcarlo como jugado). Sobre sanciones necesita INSERT/DELETE
-- porque las sanciones automáticas (roja / 3 amarillas) se generan y
-- recalculan al registrar o corregir tarjetas.
GRANT SELECT ON torneo_f5.facultad              TO 'planillero_db'@'%';
GRANT SELECT ON torneo_f5.jugador               TO 'planillero_db'@'%';
GRANT SELECT ON torneo_f5.torneo                TO 'planillero_db'@'%';
GRANT SELECT ON torneo_f5.equipo                TO 'planillero_db'@'%';
GRANT SELECT ON torneo_f5.equipo_jugador_torneo TO 'planillero_db'@'%';
GRANT SELECT ON torneo_f5.complejo              TO 'planillero_db'@'%';
GRANT SELECT ON torneo_f5.cancha                TO 'planillero_db'@'%';
GRANT SELECT ON torneo_f5.turno                 TO 'planillero_db'@'%';
GRANT SELECT ON torneo_f5.partido               TO 'planillero_db'@'%';
GRANT UPDATE (estado) ON torneo_f5.partido      TO 'planillero_db'@'%';
GRANT SELECT, INSERT, DELETE ON torneo_f5.planilla_partido TO 'planillero_db'@'%';
GRANT SELECT, INSERT, DELETE ON torneo_f5.gol              TO 'planillero_db'@'%';
GRANT SELECT, INSERT, DELETE ON torneo_f5.tarjeta          TO 'planillero_db'@'%';
GRANT SELECT, INSERT, DELETE ON torneo_f5.sancion_jugador  TO 'planillero_db'@'%';
GRANT SELECT ON torneo_f5.v_goles_acreditados TO 'planillero_db'@'%';
GRANT SELECT ON torneo_f5.v_resultado_partido TO 'planillero_db'@'%';

FLUSH PRIVILEGES;
