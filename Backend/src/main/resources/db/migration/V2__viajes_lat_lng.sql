-- =============================================================================
-- V2__viajes_lat_lng.sql
-- Migración: reemplaza idBarrioOrigen/idBarrioDestino por coordenadas reales
-- Compatible con Flyway (colocar en src/main/resources/db/migration/)
-- =============================================================================

-- Agregar columnas de coordenadas y nombres de lugar
ALTER TABLE viajes
    ADD COLUMN IF NOT EXISTS lat_origen      DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS lng_origen      DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS lat_destino     DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS lng_destino     DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS nombre_origen   VARCHAR(255),
    ADD COLUMN IF NOT EXISTS nombre_destino  VARCHAR(255),
    ADD COLUMN IF NOT EXISTS distancia_metros INTEGER;

-- NOTA: Las columnas id_barrio_origen e id_barrio_destino se mantienen
-- por compatibilidad histórica. Se pueden eliminar en V3 una vez que
-- se haya migrado todo el historial existente y regenerado JOOQ.
--
-- Para eliminarlas en el futuro:
--   ALTER TABLE viajes
--       DROP COLUMN IF EXISTS id_barrio_origen,
--       DROP COLUMN IF EXISTS id_barrio_destino;

-- Índice para consultas de historial por usuario ordenado por fecha
CREATE INDEX IF NOT EXISTS idx_viajes_usuario_hora
    ON viajes (id_usuario, hora_inicio DESC);

-- Comentarios de columna para documentación de BD
COMMENT ON COLUMN viajes.lat_origen      IS 'Latitud del punto de origen (Google Places/GPS)';
COMMENT ON COLUMN viajes.lng_origen      IS 'Longitud del punto de origen';
COMMENT ON COLUMN viajes.lat_destino     IS 'Latitud del punto de destino';
COMMENT ON COLUMN viajes.lng_destino     IS 'Longitud del punto de destino';
COMMENT ON COLUMN viajes.nombre_origen   IS 'Nombre legible del origen (ej: Aeropuerto Rionegro)';
COMMENT ON COLUMN viajes.nombre_destino  IS 'Nombre legible del destino';
COMMENT ON COLUMN viajes.distancia_metros IS 'Distancia de la ruta en metros (Google Directions)';
