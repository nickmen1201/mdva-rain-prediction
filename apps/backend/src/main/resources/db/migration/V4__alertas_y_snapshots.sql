-- =============================================================================
-- V4__alertas_y_snapshots.sql
-- Sprint 5.2A: Condiciones snapshot al planificar + tabla de alertas en ruta
-- =============================================================================

-- Snapshot de condiciones al momento de planificar el viaje (base de comparación)
CREATE TABLE IF NOT EXISTS condiciones_snapshot (
    id_viaje              INTEGER         NOT NULL,
    probabilidad_rf       DOUBLE PRECISION,
    probabilidad_rl       DOUBLE PRECISION,
    temperatura_c         DOUBLE PRECISION,
    humedad_pct           DOUBLE PRECISION,
    cobertura_nubosa_pct  DOUBLE PRECISION,
    velocidad_viento_ms   DOUBLE PRECISION,
    alerta_nivel_inicio   VARCHAR(10),
    timestamp_snapshot    TIMESTAMPTZ     NOT NULL DEFAULT now(),
    timestamp_dato_weather TIMESTAMPTZ,
    CONSTRAINT condiciones_snapshot_pkey       PRIMARY KEY (id_viaje),
    CONSTRAINT condiciones_snapshot_viaje_fkey FOREIGN KEY (id_viaje) REFERENCES viajes (id_viaje) ON DELETE CASCADE
);

-- Alertas generadas durante el trayecto activo
CREATE TABLE IF NOT EXISTS alertas_viaje (
    id_alerta              SERIAL          NOT NULL,
    id_viaje               INTEGER         NOT NULL,
    tipo_alerta            VARCHAR(30),
    nivel_severidad        VARCHAR(15),
    accion_sugerida        VARCHAR(20),
    mensaje                TEXT,
    detalle_recomendacion  TEXT,
    lat_posicion           DOUBLE PRECISION,
    lng_posicion           DOUBLE PRECISION,
    probabilidad_rf_actual DOUBLE PRECISION,
    dato_con_latencia      BOOLEAN         DEFAULT FALSE,
    timestamp_generacion   TIMESTAMPTZ     NOT NULL DEFAULT now(),
    leida                  BOOLEAN         DEFAULT FALSE,
    CONSTRAINT alertas_viaje_pkey       PRIMARY KEY (id_alerta),
    CONSTRAINT alertas_viaje_viaje_fkey FOREIGN KEY (id_viaje) REFERENCES viajes (id_viaje) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_alertas_viaje_id
    ON alertas_viaje (id_viaje, timestamp_generacion DESC);
