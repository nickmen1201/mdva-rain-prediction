-- Remove legacy barrio columns from viajes
ALTER TABLE viajes
  DROP COLUMN IF EXISTS id_barrio_origen,
  DROP COLUMN IF EXISTS id_barrio_destino;
