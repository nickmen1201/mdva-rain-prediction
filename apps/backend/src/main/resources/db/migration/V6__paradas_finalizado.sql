-- =============================================================================
-- V6__paradas_finalizado.sql
-- Sprint 5.3 — completa la tabla paradas_viaje con los campos que el plan
-- contemplaba para "auto-finalizar parada al acercarse" (PATCH /finalizar).
-- =============================================================================

ALTER TABLE paradas_viaje
    ADD COLUMN IF NOT EXISTS finalizado        BOOLEAN     NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS hora_llegada_real TIMESTAMPTZ;

COMMENT ON COLUMN paradas_viaje.finalizado        IS 'True cuando el conductor pasó por la parada (manual o auto a <100m)';
COMMENT ON COLUMN paradas_viaje.hora_llegada_real IS 'Timestamp del momento en que se marcó la parada como finalizada';
