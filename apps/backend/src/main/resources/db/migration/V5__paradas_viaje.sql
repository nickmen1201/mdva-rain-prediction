-- =============================================================================
-- V5__paradas_viaje.sql
-- Sprint 5.3: Soporte para múltiples paradas (waypoints) en un viaje
-- =============================================================================

CREATE TABLE IF NOT EXISTS paradas_viaje (
    id_parada         SERIAL          NOT NULL,
    id_viaje          INTEGER         NOT NULL,
    orden             INTEGER         NOT NULL,
    lat               DOUBLE PRECISION NOT NULL,
    lng               DOUBLE PRECISION NOT NULL,
    nombre            VARCHAR(255),
    distancia_al_siguiente INTEGER,
    tiempo_al_siguiente    INTEGER,
    CONSTRAINT paradas_viaje_pkey       PRIMARY KEY (id_parada),
    CONSTRAINT paradas_viaje_viaje_fkey FOREIGN KEY (id_viaje) REFERENCES viajes (id_viaje) ON DELETE CASCADE
);

-- Asegurar que el orden de las paradas es único dentro de un viaje
CREATE UNIQUE INDEX IF NOT EXISTS idx_paradas_viaje_orden 
    ON paradas_viaje (id_viaje, orden);
