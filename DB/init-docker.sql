-- =============================================================================
-- MDVA — init-docker.sql
-- Inicialización de BD para el contenedor Docker (entorno dev)
-- =============================================================================
-- Este script refleja el estado POST-migración V2 (viajes con lat/lng).
-- Flyway NO corre init.sql, solo las migraciones V*.sql — por eso este archivo
-- crea directamente la tabla viajes con todas las columnas ya incluidas,
-- evitando el problema de que Flyway intente alterar una tabla ya correcta.
--
-- Ejecutado automáticamente por docker-entrypoint-initdb.d al primer arranque.
-- =============================================================================

-- Limpiar si existe (útil para docker compose down -v + up)
DROP TABLE IF EXISTS viajes    CASCADE;
DROP TABLE IF EXISTS vehiculos CASCADE;
DROP TABLE IF EXISTS usuarios  CASCADE;
DROP TABLE IF EXISTS barrios   CASCADE;
DROP TABLE IF EXISTS comunas   CASCADE;
DROP TABLE IF EXISTS municipios CASCADE;
DROP TABLE IF EXISTS tipos_vehiculo CASCADE;
DROP TABLE IF EXISTS tipos_motor    CASCADE;

-- =============================================================================
-- TABLAS DE REFERENCIA
-- =============================================================================

CREATE TABLE municipios (
    id_municipio VARCHAR(20) PRIMARY KEY,
    nombre       VARCHAR(255) NOT NULL
);

CREATE TABLE comunas (
    id_comuna    VARCHAR(20) PRIMARY KEY,
    nombre       VARCHAR(255) NOT NULL,
    id_municipio VARCHAR(20) NOT NULL REFERENCES municipios(id_municipio)
);

CREATE TABLE barrios (
    id_barrio VARCHAR(20) PRIMARY KEY,
    nombre    VARCHAR(255) NOT NULL,
    id_comuna VARCHAR(20) NOT NULL REFERENCES comunas(id_comuna)
);

CREATE TABLE tipos_motor (
    id_motorizacion SMALLSERIAL PRIMARY KEY,
    nombre          VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE tipos_vehiculo (
    id_tipo_vehiculo SMALLSERIAL PRIMARY KEY,
    nombre           VARCHAR(100) NOT NULL UNIQUE,
    vulnerabilidad   SMALLINT NOT NULL CHECK (vulnerabilidad >= 0 AND vulnerabilidad <= 100)
);

-- =============================================================================
-- USUARIOS Y VEHICULOS
-- =============================================================================

CREATE TABLE usuarios (
    id               BIGSERIAL PRIMARY KEY,
    nombre           VARCHAR(120) NOT NULL,
    username         VARCHAR(60)  NOT NULL UNIQUE,
    email            VARCHAR(255) NOT NULL UNIQUE,
    fecha_nacimiento DATE,
    creado_en        TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    authhash         VARCHAR(255),
    id_barrio        VARCHAR(20) REFERENCES barrios(id_barrio)
);

CREATE TABLE vehiculos (
    placa            VARCHAR(10) PRIMARY KEY,
    id_usuario       INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    id_tipo_vehiculo SMALLINT NOT NULL REFERENCES tipos_vehiculo(id_tipo_vehiculo),
    id_motorizacion  SMALLINT NOT NULL REFERENCES tipos_motor(id_motorizacion),
    marca            VARCHAR(100) NOT NULL,
    modelo           VARCHAR(100) NOT NULL,
    ano              SMALLINT NOT NULL CHECK (ano >= 1900 AND ano <= EXTRACT(YEAR FROM CURRENT_DATE) + 1)
);

-- =============================================================================
-- VIAJES — Estado post-V2 (incluye lat/lng directamente, sin NOT NULL en barrio)
-- =============================================================================
-- Las columnas id_barrio_origen/destino se mantienen por compatibilidad histórica
-- pero ya NO son NOT NULL ni FK — la referencia geográfica ahora viene de lat/lng.
-- Se eliminarán en V3 cuando se regenere JOOQ definitivamente.

CREATE TABLE viajes (
    id_viaje         SERIAL PRIMARY KEY,
    id_usuario       INTEGER NOT NULL REFERENCES usuarios(id),
    id_vehiculo      VARCHAR(10) REFERENCES vehiculos(placa),

    -- Columnas heredadas (ya sin NOT NULL ni FK para no bloquear el backend actual)
    id_barrio_origen  VARCHAR(255),
    id_barrio_destino VARCHAR(255),

    -- Columnas nuevas de V2
    lat_origen        DOUBLE PRECISION,
    lng_origen        DOUBLE PRECISION,
    lat_destino       DOUBLE PRECISION,
    lng_destino       DOUBLE PRECISION,
    nombre_origen     VARCHAR(255),
    nombre_destino    VARCHAR(255),
    distancia_metros  INTEGER,

    tiempo_estimado_min SMALLINT NOT NULL,
    hora_inicio         TIMESTAMPTZ NOT NULL,
    hora_fin            TIMESTAMPTZ,
    precipitacion_mm    SMALLINT DEFAULT 0,
    finalizado          BOOLEAN DEFAULT FALSE NOT NULL,
    user_rating         SMALLINT CHECK (user_rating >= 1 AND user_rating <= 5)
);

-- =============================================================================
-- ÍNDICES
-- =============================================================================

CREATE INDEX idx_barrios_comuna      ON barrios(id_comuna);
CREATE INDEX idx_comunas_municipio   ON comunas(id_municipio);
CREATE INDEX idx_usuarios_barrio     ON usuarios(id_barrio);
CREATE INDEX idx_vehiculos_usuario   ON vehiculos(id_usuario);
CREATE INDEX idx_viajes_usuario      ON viajes(id_usuario);
CREATE INDEX idx_viajes_fecha        ON viajes(hora_inicio);
CREATE INDEX idx_viajes_usuario_hora ON viajes(id_usuario, hora_inicio DESC);

-- =============================================================================
-- DATOS DE REFERENCIA
-- =============================================================================

INSERT INTO municipios (id_municipio, nombre) VALUES
('MED', 'Medellin'), ('BEL', 'Bello'), ('ITA', 'Itagui'),
('ENV', 'Envigado'), ('SAB', 'Sabaneta'), ('EST', 'La Estrella'),
('CAL', 'Caldas'), ('COP', 'Copacabana'), ('GIR', 'Girardota'), ('BAR', 'Barbosa');

INSERT INTO comunas (id_comuna, nombre, id_municipio) VALUES
('MED01', 'Popular', 'MED'), ('MED02', 'Santa Cruz', 'MED'),
('MED03', 'Manrique', 'MED'), ('MED04', 'Aranjuez', 'MED'),
('MED05', 'Castilla', 'MED'), ('MED06', 'Doce de Octubre', 'MED'),
('MED07', 'Robledo', 'MED'), ('MED08', 'Villa Hermosa', 'MED'),
('MED09', 'Buenos Aires', 'MED'), ('MED10', 'La Candelaria', 'MED'),
('MED11', 'Laureles - Estadio', 'MED'), ('MED12', 'La America', 'MED'),
('MED13', 'San Javier', 'MED'), ('MED14', 'El Poblado', 'MED'),
('MED15', 'Guayabal', 'MED'), ('MED16', 'Belen', 'MED'),
('MEDC01', 'San Sebastian de Palmitas', 'MED'), ('MEDC02', 'San Cristobal', 'MED'),
('MEDC03', 'Altavista', 'MED'), ('MEDC04', 'San Antonio de Prado', 'MED'),
('MEDC05', 'Santa Elena', 'MED');

INSERT INTO barrios (id_barrio, nombre, id_comuna) VALUES
('MED0101', 'Santo Domingo Savio No. 1', 'MED01'),
('MED0102', 'Santo Domingo Savio No. 2', 'MED01'),
('MED0103', 'Popular', 'MED01'), ('MED0104', 'Granizal', 'MED01'),
('MED0201', 'La Isla', 'MED02'), ('MED0206', 'Andalucia', 'MED02'),
('MED0210', 'Santa Cruz', 'MED02'), ('MED0301', 'La Salle', 'MED03'),
('MED0307', 'Manrique Central No.2', 'MED03'), ('MED0405', 'Moravia', 'MED04'),
('MED0413', 'Aranjuez', 'MED04'), ('MED0511', 'Castilla', 'MED05'),
('MED0517', 'Caribe', 'MED05'), ('MED0602', 'Doce de Octubre No.1', 'MED06'),
('MED0604', 'Pedregal', 'MED06'), ('MED0717', 'Robledo', 'MED07'),
('MED0706', 'La Pilarica', 'MED07'), ('MED0801', 'Villa Hermosa', 'MED08'),
('MED0808', 'Enciso', 'MED08'), ('MED0907', 'Buenos Aires', 'MED09'),
('MED0908', 'Miraflores', 'MED09'), ('MED1001', 'Prado', 'MED10'),
('MED1019', 'La Candelaria', 'MED10'), ('MED1016', 'Boston', 'MED10'),
('MED1020', 'San Diego', 'MED10'), ('MED1102', 'Suramericana', 'MED11'),
('MED1108', 'Laureles', 'MED11'), ('MED1113', 'Estadio', 'MED11'),
('MED1204', 'La America', 'MED12'), ('MED1205', 'La Floresta', 'MED12'),
('MED1309', 'San Javier No.1', 'MED13'), ('MED1301', 'El Pesebre', 'MED13'),
('MED1418', 'El Poblado', 'MED14'), ('MED1422', 'La Aguacatala', 'MED14'),
('MED1409', 'El Tesoro', 'MED14'), ('MED1419', 'Manila', 'MED14'),
('MED1510', 'Guayabal', 'MED15'), ('MED1507', 'Campo Amor', 'MED15'),
('MED1603', 'Belen', 'MED16'), ('MED1601', 'Fatima', 'MED16'),
('MED1611', 'La Loma de Los Bernal', 'MED16'),
('MEDC01', 'San Sebastian de Palmitas', 'MEDC01'),
('MEDC02', 'San Cristobal', 'MEDC02'), ('MEDC03', 'Altavista', 'MEDC03'),
('MEDC04', 'San Antonio de Prado', 'MEDC04'), ('MEDC05', 'Santa Elena', 'MEDC05');

INSERT INTO tipos_motor (nombre) VALUES
('Gasolina'), ('Diesel'), ('Electrico'), ('Hibrido'),
('Hibrido enchufable'), ('Gas natural'), ('Hidrogeno');

INSERT INTO tipos_vehiculo (nombre, vulnerabilidad) VALUES
('Bicicleta', 98), ('Bicicleta electrica', 95), ('Motocicleta', 90),
('Automovil', 40), ('Taxi', 40), ('Camioneta', 35), ('SUV', 38),
('Van', 45), ('Camion', 50), ('Bus', 50), ('Tractocamion', 55);

-- Usuario de prueba para desarrollo
INSERT INTO usuarios (nombre, username, email) VALUES
('Dev User', 'devuser', 'dev@mdva.local');

-- Verificación al final del script
SELECT 'Municipios: ' || COUNT(*) FROM municipios
UNION ALL SELECT 'Comunas: '    || COUNT(*) FROM comunas
UNION ALL SELECT 'Barrios: '    || COUNT(*) FROM barrios
UNION ALL SELECT 'Tipos Motor: '|| COUNT(*) FROM tipos_motor
UNION ALL SELECT 'Tipos Vehículo: '|| COUNT(*) FROM tipos_vehiculo
UNION ALL SELECT 'Usuarios dev: '  || COUNT(*) FROM usuarios;
